from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw_bts_2025"
OUT = BASE / "results" / "hourly_schedule_pressure"

USECOLS = [
    "FlightDate",
    "Origin",
    "Dest",
    "CRSDepTime",
    "CRSArrTime",
    "Cancelled",
]

PERIOD_ORDER = [
    "stress_20250415_0519",
    "interim_20250520_0615",
    "cap_20250616_1025",
]

PERIOD_LABELS = {
    "stress_20250415_0519": "Stress",
    "interim_20250520_0615": "Interim order",
    "cap_20250616_1025": "Operating limit",
}

SIDE_LABELS = {
    "arr": "Arrivals",
    "dep": "Departures",
}


def period_label(date: pd.Timestamp) -> str | None:
    if pd.Timestamp("2025-04-15") <= date <= pd.Timestamp("2025-05-19"):
        return "stress_20250415_0519"
    if pd.Timestamp("2025-05-20") <= date <= pd.Timestamp("2025-06-15"):
        return "interim_20250520_0615"
    if pd.Timestamp("2025-06-16") <= date <= pd.Timestamp("2025-10-25"):
        return "cap_20250616_1025"
    return None


def period_target(period: str) -> int:
    return 34 if period == "cap_20250616_1025" else 28


def parse_hour(value: object) -> int | None:
    if pd.isna(value):
        return None
    try:
        minute_value = int(float(value))
    except (TypeError, ValueError):
        return None
    if minute_value < 0:
        return None
    hour = minute_value // 100
    minute = minute_value % 100
    if minute >= 60:
        return None
    if hour == 24 and minute == 0:
        return 0
    if 0 <= hour <= 23:
        return hour
    return None


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


def ewr_side_records(df: pd.DataFrame) -> pd.DataFrame:
    dep = df[df["Origin"] == "EWR"][["FlightDate", "CRSDepTime", "Cancelled"]].copy()
    dep["side"] = "dep"
    dep["hour"] = dep["CRSDepTime"].map(parse_hour)

    arr = df[df["Dest"] == "EWR"][["FlightDate", "CRSArrTime", "Cancelled"]].copy()
    arr["side"] = "arr"
    arr["hour"] = arr["CRSArrTime"].map(parse_hour)

    dep = dep.rename(columns={"CRSDepTime": "crs_time"})
    arr = arr.rename(columns={"CRSArrTime": "crs_time"})
    records = pd.concat([dep, arr], ignore_index=True)
    records = records.dropna(subset=["hour"]).copy()
    records["hour"] = records["hour"].astype(int)
    records["period"] = records["FlightDate"].map(period_label)
    records = records.dropna(subset=["period"]).copy()
    records["scheduled_in_facilitated_hours"] = records["hour"].between(6, 22)
    return records


def complete_hour_grid(records: pd.DataFrame) -> pd.DataFrame:
    dates = sorted(records["FlightDate"].unique())
    grid = pd.MultiIndex.from_product(
        [dates, ["arr", "dep"], list(range(6, 23))],
        names=["FlightDate", "side", "hour"],
    ).to_frame(index=False)
    hourly = (
        records[records["scheduled_in_facilitated_hours"]]
        .groupby(["FlightDate", "side", "hour"], as_index=False)
        .agg(scheduled_ops=("Cancelled", "size"), cancelled_ops=("Cancelled", "sum"))
    )
    hourly = grid.merge(hourly, on=["FlightDate", "side", "hour"], how="left")
    hourly["scheduled_ops"] = hourly["scheduled_ops"].fillna(0).astype(int)
    hourly["cancelled_ops"] = hourly["cancelled_ops"].fillna(0).astype(int)
    hourly["period"] = hourly["FlightDate"].map(period_label)
    hourly = hourly.dropna(subset=["period"]).copy()
    hourly["period_target"] = hourly["period"].map(period_target).astype(int)
    hourly["above_28"] = hourly["scheduled_ops"] > 28
    hourly["above_34"] = hourly["scheduled_ops"] > 34
    hourly["above_period_target"] = hourly["scheduled_ops"] > hourly["period_target"]
    return hourly.sort_values(["FlightDate", "side", "hour"]).reset_index(drop=True)


def summarize(hourly: pd.DataFrame) -> pd.DataFrame:
    summary = (
        hourly.groupby(["period", "side"], as_index=False)
        .agg(
            hours=("scheduled_ops", "size"),
            avg_ops_per_hour=("scheduled_ops", "mean"),
            p90_ops_per_hour=("scheduled_ops", lambda x: x.quantile(0.90)),
            p95_ops_per_hour=("scheduled_ops", lambda x: x.quantile(0.95)),
            max_ops_per_hour=("scheduled_ops", "max"),
            share_above_28=("above_28", "mean"),
            share_above_34=("above_34", "mean"),
            share_above_period_target=("above_period_target", "mean"),
        )
    )
    summary["period"] = pd.Categorical(summary["period"], PERIOD_ORDER, ordered=True)
    summary["side"] = pd.Categorical(summary["side"], ["arr", "dep"], ordered=True)
    return summary.sort_values(["period", "side"]).reset_index(drop=True)


def summarize_by_hour(hourly: pd.DataFrame) -> pd.DataFrame:
    by_hour = (
        hourly.groupby(["period", "side", "hour"], as_index=False)
        .agg(
            avg_ops=("scheduled_ops", "mean"),
            p90_ops=("scheduled_ops", lambda x: x.quantile(0.90)),
            share_above_28=("above_28", "mean"),
            share_above_34=("above_34", "mean"),
            share_above_period_target=("above_period_target", "mean"),
        )
    )
    by_hour["period"] = pd.Categorical(by_hour["period"], PERIOD_ORDER, ordered=True)
    by_hour["side"] = pd.Categorical(by_hour["side"], ["arr", "dep"], ordered=True)
    return by_hour.sort_values(["period", "side", "hour"]).reset_index(drop=True)


def write_summary(summary: pd.DataFrame, out_dir: Path, months: list[int]) -> None:
    lines = [
        "# EWR hourly schedule-pressure analysis",
        "",
        f"Months: {', '.join(str(month) for month in months)}.",
        "Hours: 06:00 through 22:59 local scheduled time.",
        "Benchmark targets: 28 operations per hour for stress/interim construction windows and 34 operations per hour for the operating-limit period.",
        "",
        summary.assign(
            period=summary["period"].map(PERIOD_LABELS),
            side=summary["side"].map(SIDE_LABELS),
            share_above_28=summary["share_above_28"] * 100,
            share_above_34=summary["share_above_34"] * 100,
            share_above_period_target=summary["share_above_period_target"] * 100,
        ).to_markdown(index=False, floatfmt=".2f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def build_outputs(months: list[int], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = pd.concat([ewr_side_records(read_month(month)) for month in months], ignore_index=True)
    hourly = complete_hour_grid(records)
    summary = summarize(hourly)
    by_hour = summarize_by_hour(hourly)

    hourly.to_csv(out_dir / "hourly_schedule_pressure.csv", index=False)
    summary.to_csv(out_dir / "hourly_schedule_pressure_summary.csv", index=False)
    by_hour.to_csv(out_dir / "hourly_schedule_pressure_by_hour.csv", index=False)
    write_summary(summary, out_dir, months)

    payload = {
        "months": months,
        "rows": {
            "hourly_schedule_pressure": int(len(hourly)),
            "hourly_schedule_pressure_summary": int(len(summary)),
            "hourly_schedule_pressure_by_hour": int(len(by_hour)),
        },
        "period_targets": {period: period_target(period) for period in PERIOD_ORDER},
        "facilitated_hours": "06:00-22:59",
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
