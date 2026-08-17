from __future__ import annotations

import argparse
import json
import zipfile
from calendar import monthrange
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize


BASE = Path(__file__).resolve().parents[1]
RAW_BTS = BASE / "data" / "raw_bts_2025"
RAW_T100 = BASE / "data" / "t100_domestic_segment"
OUT = BASE / "results" / "tra_policy_experiments"
OUT_SMOKE = BASE / "results" / "tra_policy_experiments_smoke"
TABLES = BASE / "article" / "elsarticle" / "tables"

OTP_USECOLS = [
    "FlightDate",
    "Origin",
    "Dest",
    "DepDel15",
    "ArrDel15",
    "Cancelled",
    "NASDelay",
]

T100_USECOLS = [
    "YEAR",
    "MONTH",
    "ORIGIN",
    "DEST",
    "UNIQUE_CARRIER",
    "UNIQUE_CARRIER_NAME",
    "DEPARTURES_PERFORMED",
    "SEATS",
    "PASSENGERS",
    "DISTANCE",
]

METRICS = {
    "scheduled_ops": ("Scheduled operations", "ops/day"),
    "cancel_rate": ("Cancellation rate", "pp"),
    "delay15_rate": ("Delay-15-plus rate", "pp"),
    "nas_delay_per_scheduled_op": ("NAS delay", "min/op"),
}

LOWER_IS_BETTER = {
    "scheduled_ops": True,
    "cancel_rate": True,
    "delay15_rate": True,
    "nas_delay_per_scheduled_op": True,
}


def period_label(date: pd.Timestamp) -> str:
    if date <= pd.Timestamp("2025-04-14"):
        return "baseline"
    if date <= pd.Timestamp("2025-05-19"):
        return "stress"
    if date <= pd.Timestamp("2025-06-15"):
        return "interim"
    if date <= pd.Timestamp("2025-10-25"):
        return "cap"
    return "extension"


def read_otp_month(month: int) -> pd.DataFrame:
    zip_path = RAW_BTS / f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_{month}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if not names:
            raise RuntimeError(f"No CSV file in {zip_path.name}")
        with zf.open(names[0]) as fh:
            df = pd.read_csv(fh, usecols=OTP_USECOLS, low_memory=False)
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    return df


def airport_side_daily(months: list[int]) -> pd.DataFrame:
    pieces = []
    for month in months:
        df = read_otp_month(month)
        df["Cancelled"] = df["Cancelled"].fillna(0).astype(float)
        df["NASDelay"] = df["NASDelay"].fillna(0).astype(float)
        df["DepDel15"] = df["DepDel15"].fillna(0).astype(float)
        df["ArrDel15"] = df["ArrDel15"].fillna(0).astype(float)

        dep = (
            df.assign(
                airport=df["Origin"],
                side="dep",
                delay15_flag=df["DepDel15"],
                operated_flag=(df["Cancelled"] == 0).astype(int),
                cancelled_flag=df["Cancelled"],
            )
            .groupby(["FlightDate", "airport", "side"], as_index=False)
            .agg(
                scheduled_ops=("airport", "size"),
                operated_ops=("operated_flag", "sum"),
                cancelled_ops=("cancelled_flag", "sum"),
                delay15_ops=("delay15_flag", "sum"),
                nas_delay_minutes=("NASDelay", "sum"),
            )
        )
        arr = (
            df.assign(
                airport=df["Dest"],
                side="arr",
                delay15_flag=df["ArrDel15"],
                operated_flag=(df["Cancelled"] == 0).astype(int),
                cancelled_flag=df["Cancelled"],
            )
            .groupby(["FlightDate", "airport", "side"], as_index=False)
            .agg(
                scheduled_ops=("airport", "size"),
                operated_ops=("operated_flag", "sum"),
                cancelled_ops=("cancelled_flag", "sum"),
                delay15_ops=("delay15_flag", "sum"),
                nas_delay_minutes=("NASDelay", "sum"),
            )
        )
        pieces.extend([arr, dep])

    daily = pd.concat(pieces, ignore_index=True)
    daily["cancel_rate"] = daily["cancelled_ops"] / daily["scheduled_ops"].replace(0, np.nan)
    daily["delay15_rate"] = daily["delay15_ops"] / daily["operated_ops"].replace(0, np.nan)
    daily["nas_delay_per_scheduled_op"] = daily["nas_delay_minutes"] / daily["scheduled_ops"].replace(0, np.nan)
    daily["period"] = daily["FlightDate"].map(period_label)
    return daily.sort_values(["FlightDate", "airport", "side"]).reset_index(drop=True)


def top_airports(daily: pd.DataFrame, top_n: int) -> list[str]:
    stress = daily[daily["period"] == "stress"].copy()
    combined = (
        stress.groupby("airport", as_index=False)
        .agg(stress_ops=("scheduled_ops", "sum"), days=("FlightDate", "nunique"))
        .assign(stress_ops_per_day=lambda x: x["stress_ops"] / x["days"])
        .sort_values("stress_ops_per_day", ascending=False)
    )
    airports = combined.head(top_n)["airport"].tolist()
    if "EWR" not in airports:
        airports.append("EWR")
    return airports


def solve_weights(y_treated: np.ndarray, y_donors: np.ndarray) -> np.ndarray:
    donor_count = y_donors.shape[1]
    x0 = np.ones(donor_count) / donor_count
    bounds = [(0.0, 1.0)] * donor_count
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def objective(weights: np.ndarray) -> float:
        diff = y_treated - y_donors @ weights
        return float(np.mean(diff**2))

    result = minimize(objective, x0=x0, method="SLSQP", bounds=bounds, constraints=constraints)
    if not result.success:
        return x0
    weights = np.clip(result.x, 0, 1)
    total = weights.sum()
    return weights / total if total else x0


def synthetic_one(
    daily: pd.DataFrame,
    treated_airport: str,
    side: str,
    metric: str,
    airports: list[str],
    intervention_date: str,
    post_end_date: str,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    data = daily[(daily["side"] == side) & (daily["airport"].isin(airports))].copy()
    pivot = data.pivot_table(index="FlightDate", columns="airport", values=metric, aggfunc="first")
    pivot = pivot.dropna(axis=0, how="any")
    if treated_airport not in pivot.columns:
        raise RuntimeError(f"{treated_airport} is missing from the synthetic-control panel.")
    donors = [airport for airport in airports if airport != treated_airport and airport in pivot.columns]
    pre_mask = pivot.index < pd.Timestamp(intervention_date)
    y_treated = pivot.loc[pre_mask, treated_airport].to_numpy(dtype=float)
    y_donors = pivot.loc[pre_mask, donors].to_numpy(dtype=float)
    scale = np.nanstd(y_treated)
    scale = scale if scale > 1e-9 else 1.0
    weights = solve_weights(y_treated / scale, y_donors / scale)
    synthetic = pivot[donors].to_numpy(dtype=float) @ weights
    path = pd.DataFrame(
        {
            "FlightDate": pivot.index,
            "treated_airport": treated_airport,
            "side": side,
            "metric": metric,
            "observed": pivot[treated_airport].to_numpy(dtype=float),
            "synthetic": synthetic,
        }
    )
    path["gap"] = path["observed"] - path["synthetic"]
    post_start = pd.Timestamp(intervention_date)
    post_end = pd.Timestamp(post_end_date)
    path["post"] = path["FlightDate"].between(post_start, post_end)
    weights_df = pd.DataFrame(
        {
            "treated_airport": treated_airport,
            "side": side,
            "metric": metric,
            "donor_airport": donors,
            "weight": weights,
        }
    ).sort_values("weight", ascending=False)
    pre_gap = path.loc[~path["post"], "gap"]
    post_gap = path.loc[path["post"], "gap"]
    stress_mask = path["FlightDate"].between(pd.Timestamp("2025-04-15"), pd.Timestamp("2025-05-19"))
    interim_mask = path["FlightDate"].between(pd.Timestamp("2025-05-20"), pd.Timestamp("2025-06-15"))
    observed_change = float(path.loc[interim_mask, "observed"].mean() - path.loc[stress_mask, "observed"].mean())
    synthetic_change = float(path.loc[interim_mask, "synthetic"].mean() - path.loc[stress_mask, "synthetic"].mean())
    stats = {
        "pre_rmse": float(np.sqrt(np.mean(pre_gap**2))),
        "post_mean_gap": float(post_gap.mean()),
        "post_abs_mean_gap": float(post_gap.abs().mean()),
        "post_days": int(path["post"].sum()),
        "observed_stress_mean": float(path.loc[stress_mask, "observed"].mean()),
        "observed_interim_mean": float(path.loc[interim_mask, "observed"].mean()),
        "synthetic_stress_mean": float(path.loc[stress_mask, "synthetic"].mean()),
        "synthetic_interim_mean": float(path.loc[interim_mask, "synthetic"].mean()),
        "observed_change": observed_change,
        "synthetic_change": synthetic_change,
        "recovery_gap": observed_change - synthetic_change,
    }
    return path, weights_df, stats


def run_synthetic_controls(daily: pd.DataFrame, airports: list[str], intervention_date: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paths = []
    weights = []
    rows = []
    for side in ["arr", "dep"]:
        for metric, (label, unit) in METRICS.items():
            path, weight, stats = synthetic_one(daily, "EWR", side, metric, airports, intervention_date, "2025-06-15")
            paths.append(path)
            weights.append(weight)
            rows.append(
                {
                    "treated_airport": "EWR",
                    "side": side,
                    "metric": metric,
                    "metric_label": label,
                    "unit": unit,
                    **stats,
                }
            )
    return pd.concat(paths, ignore_index=True), pd.concat(weights, ignore_index=True), pd.DataFrame(rows)


def run_synthetic_placebos(
    daily: pd.DataFrame,
    airports: list[str],
    intervention_date: str,
    metrics: list[str],
) -> pd.DataFrame:
    rows = []
    for side in ["arr", "dep"]:
        side_airports = [
            airport
            for airport in airports
            if not daily[(daily["side"] == side) & (daily["airport"] == airport)].empty
        ]
        for metric in metrics:
            for airport in side_airports:
                try:
                    _path, _weights, stats = synthetic_one(
                        daily, airport, side, metric, side_airports, intervention_date, "2025-06-15"
                    )
                except Exception:
                    continue
                rows.append(
                    {
                        "treated_airport": airport,
                        "side": side,
                        "metric": metric,
                        **stats,
                    }
                )
    placebo = pd.DataFrame(rows)
    rank_rows = []
    for (side, metric), group in placebo.groupby(["side", "metric"]):
        group = group.copy()
        group["rank_most_negative"] = group["post_mean_gap"].rank(method="min", ascending=True)
        group["rank_recovery_most_negative"] = group["recovery_gap"].rank(method="min", ascending=True)
        ewr = group[group["treated_airport"] == "EWR"]
        if ewr.empty:
            continue
        rank_rows.append(
            {
                "side": side,
                "metric": metric,
                "ewr_post_mean_gap": float(ewr["post_mean_gap"].iloc[0]),
                "ewr_recovery_gap": float(ewr["recovery_gap"].iloc[0]),
                "ewr_pre_rmse": float(ewr["pre_rmse"].iloc[0]),
                "rank_most_negative": int(ewr["rank_most_negative"].iloc[0]),
                "rank_recovery_most_negative": int(ewr["rank_recovery_most_negative"].iloc[0]),
                "airports": int(group["treated_airport"].nunique()),
                "permutation_p_lower_or_equal": float(
                    (group["post_mean_gap"] <= ewr["post_mean_gap"].iloc[0]).mean()
                ),
                "permutation_p_recovery_lower_or_equal": float(
                    (group["recovery_gap"] <= ewr["recovery_gap"].iloc[0]).mean()
                ),
            }
        )
    return placebo.merge(pd.DataFrame(rank_rows), on=["side", "metric"], how="left", suffixes=("", "_ewr"))


def read_t100_month(month: int) -> pd.DataFrame:
    zip_path = RAW_T100 / f"t100_domestic_segment_all_carriers_2025_{month:02d}.zip"
    if not zip_path.exists():
        zip_path = RAW_T100 / f"t100_domestic_segment_all_carriers_2025_{month}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open("T_T100D_SEGMENT_ALL_CARRIER.csv") as fh:
            df = pd.read_csv(fh, usecols=T100_USECOLS, low_memory=False)
    return df


def t100_exposure(months: list[int]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pieces = []
    for month in months:
        df = read_t100_month(month)
        arr = df[df["DEST"] == "EWR"].copy()
        arr["side"] = "arr"
        arr["counterpart"] = arr["ORIGIN"]
        dep = df[df["ORIGIN"] == "EWR"].copy()
        dep["side"] = "dep"
        dep["counterpart"] = dep["DEST"]
        pieces.append(pd.concat([arr, dep], ignore_index=True))
    records = pd.concat(pieces, ignore_index=True)
    records = records.rename(
        columns={
            "UNIQUE_CARRIER": "carrier",
            "UNIQUE_CARRIER_NAME": "carrier_name",
            "DEPARTURES_PERFORMED": "departures_performed",
            "SEATS": "seats",
            "PASSENGERS": "passengers",
            "DISTANCE": "distance",
            "MONTH": "month",
        }
    )
    records["carrier_group"] = np.where(records["carrier"] == "UA", "United", "Other carriers")
    numeric = ["departures_performed", "seats", "passengers", "distance"]
    records[numeric] = records[numeric].fillna(0)
    route_carrier = (
        records.groupby(["month", "side", "counterpart", "carrier", "carrier_group"], as_index=False)
        .agg(
            departures_performed=("departures_performed", "sum"),
            seats=("seats", "sum"),
            passengers=("passengers", "sum"),
            distance=("distance", "mean"),
        )
        .query("departures_performed > 0 or seats > 0 or passengers > 0")
    )
    monthly = (
        route_carrier.groupby(["month", "side"], as_index=False)
        .agg(
            departures_performed=("departures_performed", "sum"),
            seats=("seats", "sum"),
            passengers=("passengers", "sum"),
            active_routes=("counterpart", "nunique"),
            active_carriers=("carrier", "nunique"),
        )
        .assign(
            days=lambda x: x["month"].map(lambda m: monthrange(2025, int(m))[1]),
            seats_per_day=lambda x: x["seats"] / x["days"],
            passengers_per_day=lambda x: x["passengers"] / x["days"],
            passengers_per_departure=lambda x: x["passengers"] / x["departures_performed"].replace(0, np.nan),
            load_factor=lambda x: x["passengers"] / x["seats"].replace(0, np.nan),
        )
    )
    carrier = (
        route_carrier.groupby(["month", "side", "carrier_group"], as_index=False)
        .agg(
            departures_performed=("departures_performed", "sum"),
            seats=("seats", "sum"),
            passengers=("passengers", "sum"),
            active_routes=("counterpart", "nunique"),
        )
    )
    return route_carrier, monthly, carrier


def t100_policy_summary(monthly: pd.DataFrame, carrier: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for side in ["arr", "dep"]:
        side_monthly = monthly[monthly["side"] == side].set_index("month")
        if not {4, 5, 6}.issubset(side_monthly.index):
            continue
        apr = side_monthly.loc[4]
        jun = side_monthly.loc[6]
        rows.append(
            {
                "side": side,
                "apr_seats_per_day": apr["seats_per_day"],
                "jun_seats_per_day": jun["seats_per_day"],
                "apr_passengers_per_day": apr["passengers_per_day"],
                "jun_passengers_per_day": jun["passengers_per_day"],
                "apr_routes": apr["active_routes"],
                "jun_routes": jun["active_routes"],
                "seat_retention_apr_to_jun": jun["seats_per_day"] / apr["seats_per_day"],
                "passenger_retention_apr_to_jun": jun["passengers_per_day"] / apr["passengers_per_day"],
                "route_retention_apr_to_jun": jun["active_routes"] / apr["active_routes"],
                "jun_passengers_per_departure": jun["passengers_per_departure"],
            }
        )
    carrier_rows = []
    for (side, carrier_group), group in carrier.groupby(["side", "carrier_group"]):
        wide = group.set_index("month")
        if not {4, 6}.issubset(wide.index):
            continue
        carrier_rows.append(
            {
                "side": side,
                "carrier_group": carrier_group,
                "apr_departures": wide.loc[4, "departures_performed"],
                "jun_departures": wide.loc[6, "departures_performed"],
                "apr_seats": wide.loc[4, "seats"],
                "jun_seats": wide.loc[6, "seats"],
                "departure_change_apr_to_jun": wide.loc[6, "departures_performed"]
                - wide.loc[4, "departures_performed"],
                "seat_change_apr_to_jun": wide.loc[6, "seats"] - wide.loc[4, "seats"],
            }
        )
    return pd.DataFrame(rows), pd.DataFrame(carrier_rows)


def externality_accounting(
    daily: pd.DataFrame,
    t100_monthly: pd.DataFrame,
    synthetic_summary: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    ewr = daily[daily["airport"] == "EWR"].copy()
    for side in ["arr", "dep"]:
        stress = ewr[(ewr["side"] == side) & (ewr["period"] == "stress")]
        interim = ewr[(ewr["side"] == side) & (ewr["period"] == "interim")]
        if stress.empty or interim.empty:
            continue
        t100_side = t100_monthly[(t100_monthly["side"] == side) & (t100_monthly["month"].isin([4, 5, 6]))]
        pax_per_dep = float(
            t100_side["passengers"].sum() / t100_side["departures_performed"].sum()
        ) if t100_side["departures_performed"].sum() else np.nan
        observed_nas_min_day_reduction = stress["nas_delay_minutes"].mean() - interim["nas_delay_minutes"].mean()
        passenger_minutes_day = observed_nas_min_day_reduction * pax_per_dep
        scm = synthetic_summary[
            (synthetic_summary["side"] == side) & (synthetic_summary["metric"] == "nas_delay_per_scheduled_op")
        ]
        scm_gap = float(scm["post_mean_gap"].iloc[0]) if not scm.empty else np.nan
        rows.append(
            {
                "side": side,
                "stress_nas_minutes_per_day": stress["nas_delay_minutes"].mean(),
                "interim_nas_minutes_per_day": interim["nas_delay_minutes"].mean(),
                "observed_nas_minutes_per_day_reduction": observed_nas_min_day_reduction,
                "apr_jun_passengers_per_departure": pax_per_dep,
                "passenger_minutes_per_day_reduction": passenger_minutes_day,
                "synthetic_post_gap_nas_min_per_op": scm_gap,
            }
        )
    return pd.DataFrame(rows)


def fmt(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "--"
    return f"{value:.{digits}f}"


def write_policy_tables(
    synthetic_summary: pd.DataFrame,
    synthetic_placebo: pd.DataFrame,
    t100_summary: pd.DataFrame,
    externality: pd.DataFrame,
) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    selected = synthetic_summary[
        synthetic_summary["metric"].isin(["scheduled_ops", "delay15_rate", "nas_delay_per_scheduled_op"])
    ].copy()
    selected["rank"] = selected.apply(
        lambda r: synthetic_placebo[
            (synthetic_placebo["treated_airport"] == "EWR")
            & (synthetic_placebo["side"] == r["side"])
            & (synthetic_placebo["metric"] == r["metric"])
        ]["rank_recovery_most_negative"].iloc[0]
        if not synthetic_placebo[
            (synthetic_placebo["treated_airport"] == "EWR")
            & (synthetic_placebo["side"] == r["side"])
            & (synthetic_placebo["metric"] == r["metric"])
        ].empty
        else np.nan,
        axis=1,
    )
    selected["airports"] = selected.apply(
        lambda r: synthetic_placebo[
            (synthetic_placebo["treated_airport"] == "EWR")
            & (synthetic_placebo["side"] == r["side"])
            & (synthetic_placebo["metric"] == r["metric"])
        ]["airports"].iloc[0]
        if not synthetic_placebo[
            (synthetic_placebo["treated_airport"] == "EWR")
            & (synthetic_placebo["side"] == r["side"])
            & (synthetic_placebo["metric"] == r["metric"])
        ].empty
        else np.nan,
        axis=1,
    )
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{Synthetic-control evidence for the post-intervention window}",
        "\\label{tab:synthetic-control}",
        "\\begin{tabular}{@{}llrrr@{}}",
        "\\toprule",
        "Outcome & Side & Recovery gap & EWR change & Synthetic change \\\\",
        "\\midrule",
    ]
    for _, row in selected.iterrows():
        unit = row["unit"]
        gap = row["recovery_gap"] * 100 if unit == "pp" else row["recovery_gap"]
        gap_text = f"{fmt(gap)} {'pp' if unit == 'pp' else unit}"
        if LOWER_IS_BETTER[row["metric"]] and row["recovery_gap"] < 0:
            gap_text = f"\\textbf{{{gap_text}}}"
        obs = row["observed_change"] * 100 if unit == "pp" else row["observed_change"]
        syn = row["synthetic_change"] * 100 if unit == "pp" else row["synthetic_change"]
        obs_text = f"{fmt(obs)} {'pp' if unit == 'pp' else unit}"
        syn_text = f"{fmt(syn)} {'pp' if unit == 'pp' else unit}"
        lines.append(
            f"{row['metric_label']} & {row['side'].upper()} & {gap_text} & {obs_text} & {syn_text} \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: The recovery gap is the EWR stress-to-interim change minus the synthetic EWR stress-to-interim change. Stress is April 15--May 19, and interim is May 20--June 15, 2025. Bold values mark stronger recovery at EWR than in the synthetic counterfactual.}",
            "\\end{table}",
        ]
    )
    (TABLES / "tab_synthetic_control.tex").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{Monthly passenger and seat exposure around the capacity intervention}",
        "\\label{tab:t100-exposure}",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "Side & Seat retention & Passenger retention & Route retention & Jun passengers/departure \\\\",
        "\\midrule",
    ]
    for _, row in t100_summary.iterrows():
        lines.append(
            f"{row['side'].upper()} & \\textbf{{{fmt(100 * row['seat_retention_apr_to_jun'])}\\%}} & "
            f"\\textbf{{{fmt(100 * row['passenger_retention_apr_to_jun'])}\\%}} & "
            f"\\textbf{{{fmt(100 * row['route_retention_apr_to_jun'])}\\%}} & "
            f"{fmt(row['jun_passengers_per_departure'])} \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: T-100 Domestic Segment data are monthly. Retention compares April with June 2025 for EWR domestic segments. Bold values mark the service-access indicators used in the policy interpretation.}",
            "\\end{table}",
        ]
    )
    (TABLES / "tab_t100_exposure.tex").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{Delay-exposure accounting for the immediate intervention window}",
        "\\label{tab:externality-accounting}",
        "\\begin{tabular}{@{}lrrr@{}}",
        "\\toprule",
        "Side & NAS min/day reduction & Passengers/flight & Passenger-min/day reduction \\\\",
        "\\midrule",
    ]
    for _, row in externality.iterrows():
        lines.append(
            f"{row['side'].upper()} & \\textbf{{{fmt(row['observed_nas_minutes_per_day_reduction'])}}} & "
            f"{fmt(row['apr_jun_passengers_per_departure'])} & "
            f"\\textbf{{{fmt(row['passenger_minutes_per_day_reduction'], 0)}}} \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: NAS means National Airspace System. Passenger-minute exposure multiplies the observed EWR NAS-delay-minute reduction by the April--June 2025 T-100 passengers per performed domestic segment.}",
            "\\end{table}",
        ]
    )
    (TABLES / "tab_externality_accounting.tex").write_text("\n".join(lines), encoding="utf-8")


def write_summary(out_dir: Path, synthetic_summary: pd.DataFrame, t100_summary: pd.DataFrame, externality: pd.DataFrame) -> None:
    lines = ["# TRA policy experiments", ""]
    lines.append("## Synthetic-control post gaps")
    lines.append("")
    lines.append(synthetic_summary.to_markdown(index=False))
    lines.append("")
    lines.append("## T-100 exposure summary")
    lines.append("")
    lines.append(t100_summary.to_markdown(index=False))
    lines.append("")
    lines.append("## Delay-exposure accounting")
    lines.append("")
    lines.append(externality.to_markdown(index=False))
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--intervention-date", default="2025-05-20")
    args = parser.parse_args()

    months = [4, 5, 6] if args.smoke else list(range(1, 13))
    top_n = 10 if args.smoke else args.top_n
    out_dir = OUT_SMOKE if args.smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    daily = airport_side_daily(months)
    airports = top_airports(daily, top_n)
    daily_top = daily[daily["airport"].isin(airports)].copy()
    daily_top.to_csv(out_dir / "airport_side_daily_top_airports.csv", index=False)
    (out_dir / "synthetic_donor_airports.json").write_text(
        json.dumps({"airports": airports, "months": months}, indent=2),
        encoding="utf-8",
    )

    synthetic_path, synthetic_weights, synthetic_summary = run_synthetic_controls(
        daily_top, airports, args.intervention_date
    )
    placebo_metrics = ["scheduled_ops", "delay15_rate", "nas_delay_per_scheduled_op"]
    synthetic_placebo = run_synthetic_placebos(daily_top, airports, args.intervention_date, placebo_metrics)

    route_carrier, t100_monthly, t100_carrier = t100_exposure(months)
    t100_summary, t100_carrier_summary = t100_policy_summary(t100_monthly, t100_carrier)
    externality = externality_accounting(daily_top, t100_monthly, synthetic_summary)

    synthetic_path.to_csv(out_dir / "synthetic_control_paths.csv", index=False)
    synthetic_weights.to_csv(out_dir / "synthetic_control_weights.csv", index=False)
    synthetic_summary.to_csv(out_dir / "synthetic_control_summary.csv", index=False)
    synthetic_placebo.to_csv(out_dir / "synthetic_control_placebos.csv", index=False)
    route_carrier.to_csv(out_dir / "t100_ewr_route_carrier_month.csv", index=False)
    t100_monthly.to_csv(out_dir / "t100_ewr_monthly_exposure.csv", index=False)
    t100_carrier.to_csv(out_dir / "t100_ewr_carrier_monthly.csv", index=False)
    t100_summary.to_csv(out_dir / "t100_policy_exposure_summary.csv", index=False)
    t100_carrier_summary.to_csv(out_dir / "t100_carrier_policy_summary.csv", index=False)
    externality.to_csv(out_dir / "delay_exposure_accounting.csv", index=False)
    write_summary(out_dir, synthetic_summary, t100_summary, externality)

    if not args.smoke:
        write_policy_tables(synthetic_summary, synthetic_placebo, t100_summary, externality)


if __name__ == "__main__":
    main()
