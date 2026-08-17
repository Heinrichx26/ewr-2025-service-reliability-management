from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw_bts_2025"
TOP50_DAILY = BASE / "results" / "tra_policy_experiments" / "airport_side_daily_top_airports.csv"
OUT = BASE / "results" / "tra_peak_hour_mechanism"
OUT_SMOKE = BASE / "results" / "tra_peak_hour_mechanism_smoke"
TABLES = BASE / "article" / "elsarticle" / "tables"

SMOKE_AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL"]
REFERENCE = ("2025-03-18", "2025-04-14")
PHASES = {
    "stress": ("2025-04-15", "2025-05-19", "Stress"),
    "early_interim": ("2025-05-20", "2025-06-02", "May 20--Jun 2"),
    "late_interim": ("2025-06-03", "2025-06-15", "Jun 3--Jun 15"),
}
USECOLS = [
    "FlightDate",
    "Origin",
    "Dest",
    "CRSDepTime",
    "CRSArrTime",
    "Cancelled",
    "DepDel15",
    "ArrDel15",
    "NASDelay",
]
METRICS = {
    "avg_ops_per_hour": ("Scheduled ops/hour", "ops"),
    "p95_ops_per_hour": ("P95 scheduled ops/hour", "ops"),
    "share_above_28": ("Share above 28/hour", "pp"),
    "share_above_34": ("Share above 34/hour", "pp"),
    "delay15_rate": ("Delay-15-plus rate", "pp"),
    "nas_delay_per_scheduled_op": ("NAS delay", "min/op"),
}


def format_value(value: float, unit: str) -> str:
    if pd.isna(value):
        return "--"
    if unit == "pp":
        return f"{100 * value:.1f} pp"
    return f"{value:.1f}"


def load_airports(smoke: bool) -> list[str]:
    if smoke:
        return SMOKE_AIRPORTS
    daily = pd.read_csv(TOP50_DAILY, usecols=["airport"])
    airports = sorted(daily["airport"].dropna().unique().tolist())
    if "EWR" not in airports:
        airports.append("EWR")
    return airports


def read_month(month: int) -> pd.DataFrame:
    zip_path = RAW / f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_{month}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise RuntimeError(f"No CSV file found in {zip_path.name}")
        with zf.open(csv_names[0]) as fh:
            df = pd.read_csv(fh, usecols=USECOLS, low_memory=False)
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    return df


def parse_hour(value: object) -> int | None:
    if pd.isna(value):
        return None
    try:
        hhmm = int(float(value))
    except (TypeError, ValueError):
        return None
    hour = hhmm // 100
    minute = hhmm % 100
    if hour == 24 and minute == 0:
        return 0
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return hour
    return None


def period_label(date: pd.Timestamp) -> str | None:
    ref_start, ref_end = [pd.Timestamp(x) for x in REFERENCE]
    if ref_start <= date <= ref_end:
        return "reference"
    for key, (start, end, _label) in PHASES.items():
        if pd.Timestamp(start) <= date <= pd.Timestamp(end):
            return key
    return None


def side_records(df: pd.DataFrame, airports: list[str]) -> pd.DataFrame:
    dep = df[df["Origin"].isin(airports)][
        ["FlightDate", "Origin", "CRSDepTime", "Cancelled", "DepDel15", "NASDelay"]
    ].copy()
    dep = dep.rename(columns={"Origin": "airport", "CRSDepTime": "crs_time", "DepDel15": "delay15"})
    dep["side"] = "dep"

    arr = df[df["Dest"].isin(airports)][
        ["FlightDate", "Dest", "CRSArrTime", "Cancelled", "ArrDel15", "NASDelay"]
    ].copy()
    arr = arr.rename(columns={"Dest": "airport", "CRSArrTime": "crs_time", "ArrDel15": "delay15"})
    arr["side"] = "arr"

    records = pd.concat([dep, arr], ignore_index=True)
    records["hour"] = records["crs_time"].map(parse_hour)
    records = records.dropna(subset=["hour"]).copy()
    records["hour"] = records["hour"].astype(int)
    records["period"] = records["FlightDate"].map(period_label)
    records = records.dropna(subset=["period"]).copy()
    records["cancelled_flag"] = records["Cancelled"].fillna(0).astype(float)
    records["operated_flag"] = (records["cancelled_flag"] == 0).astype(float)
    records["delay15_flag"] = records["delay15"].fillna(0).astype(float)
    records["NASDelay"] = records["NASDelay"].fillna(0).astype(float)
    return records


def complete_hour_grid(records: pd.DataFrame, airports: list[str]) -> pd.DataFrame:
    dates = sorted(records["FlightDate"].unique())
    grid = pd.MultiIndex.from_product(
        [dates, airports, ["arr", "dep"], range(24)],
        names=["FlightDate", "airport", "side", "hour"],
    ).to_frame(index=False)
    hourly = (
        records.groupby(["FlightDate", "airport", "side", "hour"], as_index=False)
        .agg(
            scheduled_ops=("operated_flag", "size"),
            operated_ops=("operated_flag", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
        )
    )
    hourly = grid.merge(hourly, on=["FlightDate", "airport", "side", "hour"], how="left")
    for col in ["scheduled_ops", "operated_ops", "cancelled_ops", "delay15_ops", "nas_delay_minutes"]:
        hourly[col] = hourly[col].fillna(0)
    hourly["scheduled_ops"] = hourly["scheduled_ops"].astype(int)
    hourly["period"] = hourly["FlightDate"].map(period_label)
    hourly = hourly.dropna(subset=["period"]).copy()
    hourly["facilitated_hours"] = hourly["hour"].between(6, 22)
    hourly["hour_group"] = np.where(hourly["facilitated_hours"], "Facilitated hours", "Other hours")
    hourly["above_28"] = hourly["scheduled_ops"] > 28
    hourly["above_34"] = hourly["scheduled_ops"] > 34
    hourly["date_id"] = hourly["FlightDate"].dt.strftime("%Y-%m-%d")
    return hourly.sort_values(["FlightDate", "airport", "side", "hour"]).reset_index(drop=True)


def safe_rate(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0, np.nan)


def summarize_hourly(hourly: pd.DataFrame) -> pd.DataFrame:
    summary = (
        hourly.groupby(["airport", "side", "period", "hour_group"], as_index=False)
        .agg(
            hours=("scheduled_ops", "size"),
            avg_ops_per_hour=("scheduled_ops", "mean"),
            p90_ops_per_hour=("scheduled_ops", lambda x: x.quantile(0.90)),
            p95_ops_per_hour=("scheduled_ops", lambda x: x.quantile(0.95)),
            max_ops_per_hour=("scheduled_ops", "max"),
            share_above_28=("above_28", "mean"),
            share_above_34=("above_34", "mean"),
            scheduled_ops=("scheduled_ops", "sum"),
            operated_ops=("operated_ops", "sum"),
            cancelled_ops=("cancelled_ops", "sum"),
            delay15_ops=("delay15_ops", "sum"),
            nas_delay_minutes=("nas_delay_minutes", "sum"),
        )
    )
    summary["cancel_rate"] = safe_rate(summary["cancelled_ops"], summary["scheduled_ops"])
    summary["delay15_rate"] = safe_rate(summary["delay15_ops"], summary["operated_ops"])
    summary["nas_delay_per_scheduled_op"] = safe_rate(summary["nas_delay_minutes"], summary["scheduled_ops"])
    return summary


def daily_hour_group(hourly: pd.DataFrame) -> pd.DataFrame:
    daily = (
        hourly.groupby(["FlightDate", "date_id", "airport", "side", "hour_group"], as_index=False)
        .agg(
            hours=("scheduled_ops", "size"),
            scheduled_ops=("scheduled_ops", "sum"),
            operated_ops=("operated_ops", "sum"),
            delay15_ops=("delay15_ops", "sum"),
            nas_delay_minutes=("nas_delay_minutes", "sum"),
            p95_ops_per_hour=("scheduled_ops", lambda x: x.quantile(0.95)),
            share_above_28=("above_28", "mean"),
            share_above_34=("above_34", "mean"),
        )
    )
    daily["avg_ops_per_hour"] = daily["scheduled_ops"] / daily["hours"]
    daily["delay15_rate"] = safe_rate(daily["delay15_ops"], daily["operated_ops"])
    daily["nas_delay_per_scheduled_op"] = safe_rate(daily["nas_delay_minutes"], daily["scheduled_ops"])
    data = daily.copy()
    data["ewr_stress"] = (
        (data["airport"] == "EWR")
        & data["FlightDate"].between(pd.Timestamp(PHASES["stress"][0]), pd.Timestamp(PHASES["stress"][1]))
    ).astype(int)
    data["ewr_early_interim"] = (
        (data["airport"] == "EWR")
        & data["FlightDate"].between(pd.Timestamp(PHASES["early_interim"][0]), pd.Timestamp(PHASES["early_interim"][1]))
    ).astype(int)
    data["ewr_late_interim"] = (
        (data["airport"] == "EWR")
        & data["FlightDate"].between(pd.Timestamp(PHASES["late_interim"][0]), pd.Timestamp(PHASES["late_interim"][1]))
    ).astype(int)
    return data


def fit_phase_model(data: pd.DataFrame, outcome: str) -> dict[str, tuple[float, float, float]]:
    model = smf.ols(
        f"{outcome} ~ ewr_stress + ewr_early_interim + ewr_late_interim + C(airport) + C(date_id)",
        data=data.dropna(subset=[outcome]),
    ).fit(cov_type="cluster", cov_kwds={"groups": data.dropna(subset=[outcome])["date_id"]})
    out: dict[str, tuple[float, float, float]] = {}
    for key in ["ewr_stress", "ewr_early_interim", "ewr_late_interim"]:
        coef = float(model.params.get(key, np.nan))
        se = float(model.bse.get(key, np.nan))
        out[key] = (coef, coef - 1.96 * se, coef + 1.96 * se)
    return out


def run_phase_models(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    phase_terms = [
        ("ewr_stress", "Stress"),
        ("ewr_early_interim", "May 20--Jun 2"),
        ("ewr_late_interim", "Jun 3--Jun 15"),
    ]
    for side in ["arr", "dep"]:
        for hour_group in ["Facilitated hours", "Other hours"]:
            subset = daily[(daily["side"] == side) & (daily["hour_group"] == hour_group)].copy()
            for metric, (label, unit) in METRICS.items():
                estimates = fit_phase_model(subset, metric)
                for term, phase in phase_terms:
                    coef, low, high = estimates[term]
                    rows.append(
                        {
                            "side": side,
                            "hour_group": hour_group,
                            "metric": metric,
                            "metric_label": label,
                            "unit": unit,
                            "phase": phase,
                            "coef": coef,
                            "ci_low": low,
                            "ci_high": high,
                        }
                    )
    return pd.DataFrame(rows)


def write_latex_table(summary: pd.DataFrame, table_path: Path) -> None:
    ewr = summary[
        (summary["airport"] == "EWR")
        & (summary["period"].isin(["stress", "early_interim", "late_interim"]))
        & (summary["hour_group"] == "Facilitated hours")
    ].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Facilitated-hour schedule pressure at EWR}",
        r"\label{tab:peak-hour-mechanism}",
        r"\begin{tabular}{@{}llrrrr@{}}",
        r"\toprule",
        r"Phase & Side & Mean & P95 & $>$28 & D15+ \\",
        r"\midrule",
    ]
    phase_order = ["stress", "early_interim", "late_interim"]
    phase_labels = {key: label for key, (_start, _end, label) in PHASES.items()}
    for phase in phase_order:
        for side in ["arr", "dep"]:
            row = ewr[(ewr["period"] == phase) & (ewr["side"] == side)].iloc[0]
            p95 = format_value(row["p95_ops_per_hour"], "ops")
            above_28 = format_value(row["share_above_28"], "pp")
            d15 = format_value(row["delay15_rate"], "pp")
            if phase in ["early_interim", "late_interim"] and row["p95_ops_per_hour"] < ewr[
                (ewr["period"] == "stress") & (ewr["side"] == side)
            ]["p95_ops_per_hour"].iloc[0]:
                p95 = rf"\textbf{{{p95}}}"
            if phase in ["early_interim", "late_interim"] and row["delay15_rate"] < ewr[
                (ewr["period"] == "stress") & (ewr["side"] == side)
            ]["delay15_rate"].iloc[0]:
                d15 = rf"\textbf{{{d15}}}"
            lines.append(
                f"{phase_labels[phase]} & {side.upper()} & "
                f"{format_value(row['avg_ops_per_hour'], 'ops')} & {p95} & {above_28} & {d15} \\\\"
            )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: Facilitated hours are 06:00--22:59 local scheduled time. D15+ means delay-15-plus. The table uses the public BTS domestic scheduled-flight sample, so it measures the reported domestic component of schedule exposure. Bold values mark lower tail pressure or lower delay-15-plus relative to the stress window.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(summary: pd.DataFrame, phase: pd.DataFrame, out_dir: Path, months: list[int], airports: list[str]) -> None:
    ewr = summary[(summary["airport"] == "EWR") & (summary["hour_group"] == "Facilitated hours")].copy()
    lines = [
        "# TRA peak-hour mechanism check",
        "",
        f"Months used: {', '.join(str(m) for m in months)}.",
        f"Airports: {len(airports)}.",
        "Facilitated hours are 06:00-22:59 local scheduled time.",
        "",
        "## EWR facilitated-hour summary",
        "",
        ewr.to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Calendar-date fixed-effect phase estimates",
        "",
        phase.to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--months", nargs="+", type=int, default=[3, 4, 5, 6])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = OUT_SMOKE if args.smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    months = sorted(set(args.months))
    airports = load_airports(args.smoke)
    records = pd.concat([side_records(read_month(month), airports) for month in months], ignore_index=True)
    hourly = complete_hour_grid(records, airports)
    summary = summarize_hourly(hourly)
    daily = daily_hour_group(hourly)
    phase = run_phase_models(daily)
    hourly.to_csv(out_dir / "airport_hour_side.csv", index=False)
    daily.to_csv(out_dir / "airport_day_hour_group.csv", index=False)
    summary.to_csv(out_dir / "peak_hour_phase_summary.csv", index=False)
    phase.to_csv(out_dir / "peak_hour_date_fe.csv", index=False)
    write_summary(summary, phase, out_dir, months, airports)
    if not args.smoke and TABLES.exists():
        write_latex_table(summary, TABLES / "tab_peak_hour_mechanism.tex")
    print("EWR facilitated-hour summary")
    print(summary[(summary["airport"] == "EWR") & (summary["hour_group"] == "Facilitated hours")].to_string(index=False))
    print("\nDate-FE phase estimates")
    print(phase.to_string(index=False))


if __name__ == "__main__":
    main()
