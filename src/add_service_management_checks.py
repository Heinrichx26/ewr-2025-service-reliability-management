from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw_bts_2025"
OUT = BASE / "results" / "service_management_checks"

USECOLS = [
    "FlightDate",
    "Reporting_Airline",
    "IATA_CODE_Reporting_Airline",
    "Origin",
    "Dest",
    "DepDel15",
    "ArrDel15",
    "Cancelled",
    "NASDelay",
]

PERIOD_ORDER = [
    "pre_20250101_0414",
    "stress_20250415_0519",
    "interim_20250520_0615",
    "cap_20250616_1025",
    "extension_20251026_1231",
]

PERIOD_LABELS = {
    "pre_20250101_0414": "Baseline",
    "stress_20250415_0519": "Stress",
    "interim_20250520_0615": "Interim order",
    "cap_20250616_1025": "Operating limit",
    "extension_20251026_1231": "Extension",
}

SIDE_LABELS = {"arr": "Arrivals", "dep": "Departures"}


def period_label(date: pd.Timestamp) -> str:
    if date <= pd.Timestamp("2025-04-14"):
        return "pre_20250101_0414"
    if date <= pd.Timestamp("2025-05-19"):
        return "stress_20250415_0519"
    if date <= pd.Timestamp("2025-06-15"):
        return "interim_20250520_0615"
    if date <= pd.Timestamp("2025-10-25"):
        return "cap_20250616_1025"
    return "extension_20251026_1231"


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


def ewr_records(df: pd.DataFrame) -> pd.DataFrame:
    dep = df[df["Origin"] == "EWR"].copy()
    dep["side"] = "dep"
    dep["counterpart"] = dep["Dest"]
    dep["delay15"] = dep["DepDel15"]

    arr = df[df["Dest"] == "EWR"].copy()
    arr["side"] = "arr"
    arr["counterpart"] = arr["Origin"]
    arr["delay15"] = arr["ArrDel15"]

    records = pd.concat([arr, dep], ignore_index=True)
    records["period"] = records["FlightDate"].map(period_label)
    records["operated"] = (records["Cancelled"].fillna(0) == 0).astype(int)
    records["cancelled_flag"] = records["Cancelled"].fillna(0).astype(float)
    records["delay15_flag"] = records["delay15"].fillna(0).astype(float)
    records["NASDelay"] = records["NASDelay"].fillna(0).astype(float)
    records["carrier_group"] = np.where(
        records["IATA_CODE_Reporting_Airline"] == "UA",
        "United",
        "Other carriers",
    )
    return records[
        [
            "FlightDate",
            "period",
            "side",
            "counterpart",
            "Reporting_Airline",
            "IATA_CODE_Reporting_Airline",
            "carrier_group",
            "operated",
            "cancelled_flag",
            "delay15_flag",
            "NASDelay",
        ]
    ].copy()


def safe_rate(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0, np.nan)


def period_days(records: pd.DataFrame) -> pd.DataFrame:
    return (
        records.groupby(["period"], as_index=False)
        .agg(days=("FlightDate", "nunique"))
        .assign(period=lambda x: pd.Categorical(x["period"], PERIOD_ORDER, ordered=True))
        .sort_values("period")
        .reset_index(drop=True)
    )


def add_reliability_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ops_per_day"] = df["scheduled_ops"] / df["days"]
    df["cancelled_ops_per_day"] = df["cancelled_ops"] / df["days"]
    df["delay15_ops_per_day"] = df["delay15_ops"] / df["days"]
    df["nas_delay_minutes_per_day"] = df["nas_delay_minutes"] / df["days"]
    df["cancel_rate"] = safe_rate(df["cancelled_ops"], df["scheduled_ops"])
    df["delay15_rate"] = safe_rate(df["delay15_ops"], df["operated_ops"])
    df["nas_delay_per_scheduled_op"] = safe_rate(df["nas_delay_minutes"], df["scheduled_ops"])
    return df


def route_period(records: pd.DataFrame, days: pd.DataFrame) -> pd.DataFrame:
    route = (
        records.groupby(["side", "counterpart", "period"], as_index=False)
        .agg(
            scheduled_ops=("operated", "size"),
            operated_ops=("operated", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
        )
        .merge(days, on="period", how="left")
    )
    return add_reliability_metrics(route)


def route_coverage_summary(records: pd.DataFrame, routes: pd.DataFrame, days: pd.DataFrame) -> pd.DataFrame:
    period_side = (
        records.groupby(["side", "period"], as_index=False)
        .agg(
            scheduled_ops=("operated", "size"),
            operated_ops=("operated", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
            counterpart_airports=("counterpart", "nunique"),
        )
        .merge(days, on="period", how="left")
    )
    period_side = add_reliability_metrics(period_side)

    active_daily = (
        records.groupby(["FlightDate", "side", "period"], as_index=False)
        .agg(active_counterparts=("counterpart", "nunique"))
        .groupby(["side", "period"], as_index=False)
        .agg(avg_daily_active_counterparts=("active_counterparts", "mean"))
    )

    weekly = (
        routes.assign(
            active_weekly=lambda x: x["ops_per_day"] >= (1 / 7),
            active_daily=lambda x: x["ops_per_day"] >= 1,
        )
        .groupby(["side", "period"], as_index=False)
        .agg(
            weekly_service_markets=("active_weekly", "sum"),
            daily_service_markets=("active_daily", "sum"),
        )
    )

    summary = period_side.merge(active_daily, on=["side", "period"], how="left").merge(
        weekly, on=["side", "period"], how="left"
    )
    summary["period"] = pd.Categorical(summary["period"], PERIOD_ORDER, ordered=True)
    return summary.sort_values(["side", "period"]).reset_index(drop=True)


def route_retention(routes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for side in ["arr", "dep"]:
        side_routes = routes[routes["side"] == side].copy()
        wide = side_routes.pivot_table(
            index="counterpart",
            columns="period",
            values="ops_per_day",
            aggfunc="first",
            fill_value=0,
            observed=False,
        )
        if "stress_20250415_0519" not in wide.columns or "interim_20250520_0615" not in wide.columns:
            continue
        for threshold_name, threshold in [("weekly", 1 / 7), ("daily", 1.0)]:
            base = wide[wide["stress_20250415_0519"] >= threshold].copy()
            if base.empty:
                continue
            retained = base["interim_20250520_0615"] >= threshold
            freq_change = base["interim_20250520_0615"] - base["stress_20250415_0519"]
            rows.append(
                {
                    "side": side,
                    "threshold": threshold_name,
                    "stress_markets": int(len(base)),
                    "retained_markets": int(retained.sum()),
                    "retention_rate": float(retained.mean()),
                    "mean_ops_per_day_change": float(freq_change.mean()),
                    "median_ops_per_day_change": float(freq_change.median()),
                    "largest_market_reduction": float(freq_change.min()),
                }
            )
    return pd.DataFrame(rows)


def carrier_group_period(records: pd.DataFrame, days: pd.DataFrame) -> pd.DataFrame:
    carrier = (
        records.groupby(["carrier_group", "side", "period"], as_index=False)
        .agg(
            scheduled_ops=("operated", "size"),
            operated_ops=("operated", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
            counterpart_airports=("counterpart", "nunique"),
        )
        .merge(days, on="period", how="left")
    )
    carrier = add_reliability_metrics(carrier)
    carrier["period"] = pd.Categorical(carrier["period"], PERIOD_ORDER, ordered=True)
    return carrier.sort_values(["carrier_group", "side", "period"]).reset_index(drop=True)


def carrier_group_contrast(carrier: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "ops_per_day",
        "cancel_rate",
        "delay15_rate",
        "nas_delay_per_scheduled_op",
        "counterpart_airports",
    ]
    rows = []
    for (carrier_group, side), group in carrier.groupby(["carrier_group", "side"], observed=False):
        stress = group[group["period"] == "stress_20250415_0519"]
        interim = group[group["period"] == "interim_20250520_0615"]
        if stress.empty or interim.empty:
            continue
        stress = stress.iloc[0]
        interim = interim.iloc[0]
        row = {"carrier_group": carrier_group, "side": side}
        for metric in metrics:
            row[f"stress_{metric}"] = float(stress[metric])
            row[f"interim_{metric}"] = float(interim[metric])
            row[f"delta_{metric}"] = float(interim[metric] - stress[metric])
        rows.append(row)
    return pd.DataFrame(rows)


def top_carrier_contrast(records: pd.DataFrame, days: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    stress = records[records["period"] == "stress_20250415_0519"]
    top = (
        stress.groupby("IATA_CODE_Reporting_Airline")
        .size()
        .sort_values(ascending=False)
        .head(top_n)
        .index.tolist()
    )
    carrier = (
        records[records["IATA_CODE_Reporting_Airline"].isin(top)]
        .groupby(["IATA_CODE_Reporting_Airline", "Reporting_Airline", "side", "period"], as_index=False)
        .agg(
            scheduled_ops=("operated", "size"),
            operated_ops=("operated", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
        )
        .merge(days, on="period", how="left")
    )
    carrier = add_reliability_metrics(carrier)
    rows = []
    for (code, name, side), group in carrier.groupby(
        ["IATA_CODE_Reporting_Airline", "Reporting_Airline", "side"], observed=False
    ):
        stress_row = group[group["period"] == "stress_20250415_0519"]
        interim_row = group[group["period"] == "interim_20250520_0615"]
        if stress_row.empty or interim_row.empty:
            continue
        stress_row = stress_row.iloc[0]
        interim_row = interim_row.iloc[0]
        rows.append(
            {
                "carrier": code,
                "carrier_name": name,
                "side": side,
                "stress_ops_per_day": float(stress_row["ops_per_day"]),
                "interim_ops_per_day": float(interim_row["ops_per_day"]),
                "delta_ops_per_day": float(interim_row["ops_per_day"] - stress_row["ops_per_day"]),
                "delta_cancel_rate": float(interim_row["cancel_rate"] - stress_row["cancel_rate"]),
                "delta_delay15_rate": float(interim_row["delay15_rate"] - stress_row["delay15_rate"]),
                "delta_nas_delay_per_scheduled_op": float(
                    interim_row["nas_delay_per_scheduled_op"]
                    - stress_row["nas_delay_per_scheduled_op"]
                ),
            }
        )
    return pd.DataFrame(rows)


def capacity_reliability_tradeoff(records: pd.DataFrame, days: pd.DataFrame) -> pd.DataFrame:
    period_side = (
        records.groupby(["side", "period"], as_index=False)
        .agg(
            scheduled_ops=("operated", "size"),
            operated_ops=("operated", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
        )
        .merge(days, on="period", how="left")
    )
    period_side = add_reliability_metrics(period_side)
    rows = []
    for side, group in period_side.groupby("side", observed=False):
        stress = group[group["period"] == "stress_20250415_0519"]
        interim = group[group["period"] == "interim_20250520_0615"]
        if stress.empty or interim.empty:
            continue
        stress = stress.iloc[0]
        interim = interim.iloc[0]
        ops_reduction = stress["ops_per_day"] - interim["ops_per_day"]
        row = {
            "side": side,
            "stress_ops_per_day": float(stress["ops_per_day"]),
            "interim_ops_per_day": float(interim["ops_per_day"]),
            "ops_reduction_per_day": float(ops_reduction),
            "cancelled_ops_reduction_per_day": float(
                stress["cancelled_ops_per_day"] - interim["cancelled_ops_per_day"]
            ),
            "delay15_ops_reduction_per_day": float(
                stress["delay15_ops_per_day"] - interim["delay15_ops_per_day"]
            ),
            "nas_minutes_reduction_per_day": float(
                stress["nas_delay_minutes_per_day"] - interim["nas_delay_minutes_per_day"]
            ),
            "cancel_rate_change": float(interim["cancel_rate"] - stress["cancel_rate"]),
            "delay15_rate_change": float(interim["delay15_rate"] - stress["delay15_rate"]),
            "nas_delay_per_op_change": float(
                interim["nas_delay_per_scheduled_op"] - stress["nas_delay_per_scheduled_op"]
            ),
        }
        if ops_reduction > 0:
            row["cancelled_ops_reduction_per_ops_day_reduced"] = (
                row["cancelled_ops_reduction_per_day"] / ops_reduction
            )
            row["delay15_ops_reduction_per_ops_day_reduced"] = (
                row["delay15_ops_reduction_per_day"] / ops_reduction
            )
            row["nas_minutes_reduction_per_ops_day_reduced"] = (
                row["nas_minutes_reduction_per_day"] / ops_reduction
            )
        rows.append(row)
    return pd.DataFrame(rows)


def write_summary(
    out_dir: Path,
    months: list[int],
    coverage: pd.DataFrame,
    retention: pd.DataFrame,
    carrier_contrast: pd.DataFrame,
    tradeoff: pd.DataFrame,
) -> None:
    def pct(x: float) -> str:
        return f"{100 * x:.1f}%"

    lines = [
        "# Business and service-continuity checks",
        "",
        f"Months: {', '.join(str(month) for month in months)}.",
        "Scope: EWR domestic scheduled flights in BTS On-Time Performance records.",
        "",
        "## Route service coverage",
        coverage.assign(
            period=coverage["period"].map(PERIOD_LABELS),
            side=coverage["side"].map(SIDE_LABELS),
        )[
            [
                "side",
                "period",
                "counterpart_airports",
                "weekly_service_markets",
                "daily_service_markets",
                "avg_daily_active_counterparts",
                "ops_per_day",
            ]
        ].to_markdown(index=False, floatfmt=".2f"),
        "",
        "## Stress-to-interim market retention",
        retention.assign(
            side=retention["side"].map(SIDE_LABELS),
            retention_rate_text=retention["retention_rate"].map(pct),
        )[
            [
                "side",
                "threshold",
                "stress_markets",
                "retained_markets",
                "retention_rate_text",
                "mean_ops_per_day_change",
                "median_ops_per_day_change",
            ]
        ].to_markdown(index=False, floatfmt=".2f"),
        "",
        "## United versus other carriers",
        carrier_contrast.assign(side=carrier_contrast["side"].map(SIDE_LABELS))[
            [
                "carrier_group",
                "side",
                "delta_ops_per_day",
                "delta_cancel_rate",
                "delta_delay15_rate",
                "delta_nas_delay_per_scheduled_op",
                "delta_counterpart_airports",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Capacity-reliability trade-off",
        tradeoff.assign(side=tradeoff["side"].map(SIDE_LABELS))[
            [
                "side",
                "ops_reduction_per_day",
                "cancelled_ops_reduction_per_day",
                "delay15_ops_reduction_per_day",
                "nas_minutes_reduction_per_day",
                "cancelled_ops_reduction_per_ops_day_reduced",
                "delay15_ops_reduction_per_ops_day_reduced",
                "nas_minutes_reduction_per_ops_day_reduced",
            ]
        ].to_markdown(index=False, floatfmt=".2f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def build_outputs(months: list[int], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = pd.concat([ewr_records(read_month(month)) for month in months], ignore_index=True)
    days = period_days(records)
    routes = route_period(records, days)
    coverage = route_coverage_summary(records, routes, days)
    retention = route_retention(routes)
    carrier_period = carrier_group_period(records, days)
    carrier_contrast = carrier_group_contrast(carrier_period)
    top_carriers = top_carrier_contrast(records, days)
    tradeoff = capacity_reliability_tradeoff(records, days)

    records.to_csv(out_dir / "ewr_bts_business_records.csv", index=False)
    days.to_csv(out_dir / "period_days.csv", index=False)
    routes.to_csv(out_dir / "route_period_summary.csv", index=False)
    coverage.to_csv(out_dir / "route_service_coverage_summary.csv", index=False)
    retention.to_csv(out_dir / "route_service_retention.csv", index=False)
    carrier_period.to_csv(out_dir / "carrier_group_period_summary.csv", index=False)
    carrier_contrast.to_csv(out_dir / "carrier_group_stress_interim_contrast.csv", index=False)
    top_carriers.to_csv(out_dir / "top_carrier_stress_interim_contrast.csv", index=False)
    tradeoff.to_csv(out_dir / "capacity_reliability_tradeoff.csv", index=False)
    write_summary(out_dir, months, coverage, retention, carrier_contrast, tradeoff)

    usable = {
        "route_retention_weekly_min": float(
            retention[retention["threshold"] == "weekly"]["retention_rate"].min()
        )
        if not retention.empty
        else None,
        "all_tradeoff_positive": bool(
            (tradeoff["ops_reduction_per_day"] > 0).all()
            and (tradeoff["nas_minutes_reduction_per_day"] > 0).all()
        )
        if not tradeoff.empty
        else None,
        "united_and_other_reduce_ops": bool(
            (carrier_contrast["delta_ops_per_day"] < 0).all()
        )
        if not carrier_contrast.empty
        else None,
    }
    payload = {
        "months": months,
        "rows": {
            "records": int(len(records)),
            "route_period_summary": int(len(routes)),
            "route_service_coverage_summary": int(len(coverage)),
            "carrier_group_period_summary": int(len(carrier_period)),
        },
        "result_quality_flags": usable,
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", nargs="+", type=int, default=list(range(1, 13)))
    parser.add_argument("--out", type=Path, default=OUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    months = sorted(set(args.months))
    invalid = [month for month in months if month < 1 or month > 12]
    if invalid:
        raise ValueError(f"Invalid months: {invalid}")
    build_outputs(months, args.out)


if __name__ == "__main__":
    main()

