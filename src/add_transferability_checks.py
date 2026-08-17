from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw_bts_2025"
OUT = BASE / "results" / "transferability_checks"
OUT_SMOKE = BASE / "results" / "transferability_checks_smoke"
TABLES = BASE / "results" / "tables"

USECOLS = [
    "FlightDate",
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

SIDE_LABELS = {"arr": "ARR", "dep": "DEP"}


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
            raise RuntimeError(f"No CSV in {zip_path.name}")
        with zf.open(csv_names[0]) as fh:
            df = pd.read_csv(fh, usecols=USECOLS, low_memory=False)
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    return df


def airport_side_records(df: pd.DataFrame) -> pd.DataFrame:
    dep = df.copy()
    dep["airport"] = dep["Origin"]
    dep["counterpart"] = dep["Dest"]
    dep["side"] = "dep"
    dep["delay15"] = dep["DepDel15"]

    arr = df.copy()
    arr["airport"] = arr["Dest"]
    arr["counterpart"] = arr["Origin"]
    arr["side"] = "arr"
    arr["delay15"] = arr["ArrDel15"]

    cols = [
        "FlightDate",
        "airport",
        "counterpart",
        "side",
        "IATA_CODE_Reporting_Airline",
        "delay15",
        "Cancelled",
        "NASDelay",
    ]
    out = pd.concat([dep[cols], arr[cols]], ignore_index=True)
    out["period"] = out["FlightDate"].map(period_label)
    out["cancelled_flag"] = out["Cancelled"].fillna(0).astype(float)
    out["operated_flag"] = (out["cancelled_flag"] == 0).astype(int)
    out["delay15_flag"] = out["delay15"].fillna(0).astype(float)
    out["NASDelay"] = out["NASDelay"].fillna(0).astype(float)
    return out


def safe_rate(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0, np.nan)


def period_days(records: pd.DataFrame) -> pd.DataFrame:
    return records.groupby("period", as_index=False).agg(days=("FlightDate", "nunique"))


def period_summary(records: pd.DataFrame, days: pd.DataFrame) -> pd.DataFrame:
    summary = (
        records.groupby(["airport", "side", "period"], as_index=False)
        .agg(
            scheduled_ops=("operated_flag", "size"),
            operated_ops=("operated_flag", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
        )
        .merge(days, on="period", how="left")
    )
    summary["ops_per_day"] = summary["scheduled_ops"] / summary["days"]
    summary["cancel_rate"] = safe_rate(summary["cancelled_ops"], summary["scheduled_ops"])
    summary["delay15_rate"] = safe_rate(summary["delay15_ops"], summary["operated_ops"])
    summary["nas_delay_per_scheduled_op"] = safe_rate(summary["nas_delay_minutes"], summary["scheduled_ops"])
    return summary


def top_airports(summary: pd.DataFrame, top_n: int) -> list[str]:
    stress = summary[summary["period"] == "stress_20250415_0519"].copy()
    combined = (
        stress.groupby("airport", as_index=False)
        .agg(stress_scheduled_ops=("scheduled_ops", "sum"), stress_days=("days", "max"))
    )
    combined["stress_combined_ops_per_day"] = combined["stress_scheduled_ops"] / combined["stress_days"]
    top = combined.sort_values("stress_combined_ops_per_day", ascending=False).head(top_n)["airport"].tolist()
    if "EWR" not in top:
        top.append("EWR")
    return sorted(top)


def stress_interim_changes(summary: pd.DataFrame, peers: list[str]) -> pd.DataFrame:
    metrics = ["ops_per_day", "cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]
    data = summary[summary["airport"].isin(peers)].copy()
    wide = data.pivot_table(
        index=["airport", "side"],
        columns="period",
        values=metrics,
        aggfunc="first",
        observed=False,
    )
    wide.columns = [f"{metric}_{period}" for metric, period in wide.columns]
    wide = wide.reset_index()
    for metric in metrics:
        wide[f"{metric}_change"] = (
            wide[f"{metric}_interim_20250520_0615"] - wide[f"{metric}_stress_20250415_0519"]
        )
    return wide


def dominant_carrier_share(records: pd.DataFrame, peers: list[str]) -> pd.DataFrame:
    stress = records[
        (records["airport"].isin(peers)) & (records["period"] == "stress_20250415_0519")
    ].copy()
    carrier = (
        stress.groupby(["airport", "side", "IATA_CODE_Reporting_Airline"], as_index=False)
        .agg(carrier_ops=("operated_flag", "size"))
    )
    total = carrier.groupby(["airport", "side"], as_index=False).agg(total_ops=("carrier_ops", "sum"))
    carrier = carrier.merge(total, on=["airport", "side"], how="left")
    carrier["carrier_share"] = carrier["carrier_ops"] / carrier["total_ops"]
    idx = carrier.groupby(["airport", "side"])["carrier_share"].idxmax()
    return carrier.loc[idx, ["airport", "side", "IATA_CODE_Reporting_Airline", "carrier_share"]].rename(
        columns={
            "IATA_CODE_Reporting_Airline": "dominant_carrier",
            "carrier_share": "dominant_carrier_share",
        }
    )


def route_retention(records: pd.DataFrame, days: pd.DataFrame, peers: list[str]) -> pd.DataFrame:
    route = (
        records[records["airport"].isin(peers)]
        .groupby(["airport", "side", "counterpart", "period"], as_index=False)
        .agg(scheduled_ops=("operated_flag", "size"))
        .merge(days, on="period", how="left")
    )
    route["ops_per_day"] = route["scheduled_ops"] / route["days"]
    rows = []
    for (airport, side), group in route.groupby(["airport", "side"]):
        wide = group.pivot_table(
            index="counterpart",
            columns="period",
            values="ops_per_day",
            aggfunc="first",
            fill_value=0,
            observed=False,
        )
        if "stress_20250415_0519" not in wide.columns or "interim_20250520_0615" not in wide.columns:
            continue
        stress_weekly = wide["stress_20250415_0519"] >= (1 / 7)
        retained_weekly = stress_weekly & (wide["interim_20250520_0615"] >= (1 / 7))
        stress_daily = wide["stress_20250415_0519"] >= 1
        retained_daily = stress_daily & (wide["interim_20250520_0615"] >= 1)
        rows.append(
            {
                "airport": airport,
                "side": side,
                "weekly_service_markets_stress": int(stress_weekly.sum()),
                "weekly_retention_rate": float(retained_weekly.sum() / stress_weekly.sum())
                if stress_weekly.sum()
                else np.nan,
                "daily_service_markets_stress": int(stress_daily.sum()),
                "daily_retention_rate": float(retained_daily.sum() / stress_daily.sum())
                if stress_daily.sum()
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def rank_text(values: pd.Series, target_airport: str, ascending: bool) -> str:
    ranks = values.rank(method="min", ascending=ascending)
    return f"{int(ranks.loc[target_airport])}/{int(values.notna().sum())}"


def build_indicator_benchmark(
    changes: pd.DataFrame,
    dom: pd.DataFrame,
    retention: pd.DataFrame,
    peers: list[str],
) -> pd.DataFrame:
    data = changes.merge(dom, on=["airport", "side"], how="left").merge(
        retention, on=["airport", "side"], how="left"
    )
    rows = []
    indicators = [
        ("Stress ops/day", "ops_per_day_stress_20250415_0519", "ops", False),
        ("Dominant carrier share", "dominant_carrier_share", "pct", False),
        ("Weekly market retention", "weekly_retention_rate", "pct", False),
        ("Ops/day change", "ops_per_day_change", "ops", True),
        ("Delay-15+ change", "delay15_rate_change", "pp", True),
        ("NAS min/op change", "nas_delay_per_scheduled_op_change", "min", True),
    ]
    for side in ["arr", "dep"]:
        side_data = data[data["side"] == side].set_index("airport")
        peer_data = side_data.loc[[airport for airport in peers if airport != "EWR"]]
        for label, col, unit, ascending in indicators:
            if col not in side_data.columns or "EWR" not in side_data.index:
                continue
            ewr_value = float(side_data.loc["EWR", col])
            peer_median = float(peer_data[col].median())
            rank = rank_text(side_data[col], "EWR", ascending=ascending)
            rows.append(
                {
                    "side": side,
                    "indicator": label,
                    "unit": unit,
                    "ewr_value": ewr_value,
                    "peer_median": peer_median,
                    "ewr_rank": rank,
                    "rank_direction": "lowest is strongest" if ascending else "highest is strongest",
                }
            )
    return pd.DataFrame(rows)


def fmt(value: float, unit: str) -> str:
    if pd.isna(value):
        return "--"
    if unit == "pct":
        return f"{100 * value:.1f}\\%"
    if unit == "pp":
        return f"{100 * value:.1f} pp"
    return f"{value:.1f}"


def write_latex_table(bench: pd.DataFrame, table_path: Path) -> None:
    keep = bench[
        bench["indicator"].isin(
            [
                "Dominant carrier share",
                "Weekly market retention",
                "Ops/day change",
                "Delay-15+ change",
                "NAS min/op change",
            ]
        )
    ].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Large-airport benchmark for transferability and policy interpretation}",
        r"\label{tab:transferability-benchmark}",
        r"\begin{tabular}{@{}llrrr@{}}",
        r"\toprule",
        r"Side & Indicator & EWR & Peer median & EWR rank \\",
        r"\midrule",
    ]
    for side in ["arr", "dep"]:
        for indicator in [
            "Dominant carrier share",
            "Weekly market retention",
            "Ops/day change",
            "Delay-15+ change",
            "NAS min/op change",
        ]:
            row = keep[(keep["side"] == side) & (keep["indicator"] == indicator)].iloc[0]
            ewr = fmt(row["ewr_value"], row["unit"])
            peer = fmt(row["peer_median"], row["unit"])
            bold = indicator in {
                "Weekly market retention",
                "Ops/day change",
                "Delay-15+ change",
                "NAS min/op change",
            }
            ewr_cell = rf"\textbf{{{ewr}}}" if bold else ewr
            lines.append(
                f"{SIDE_LABELS[side]} & {indicator} & {ewr_cell} & {peer} & {row['ewr_rank']} \\\\"
            )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: The benchmark set is the 50 largest U.S. domestic airports by scheduled operations during April 15--May 19, 2025, EWR is included in this set. Peer median excludes EWR. Bold values mark the policy indicators used in the interpretation.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(out_dir: Path, months: list[int], peers: list[str], bench: pd.DataFrame) -> None:
    lines = [
        "# Transferability checks",
        "",
        f"Months: {', '.join(str(month) for month in months)}.",
        f"Benchmark airports: {len(peers)}.",
        "",
        "## Policy indicator benchmark",
        "",
        bench.assign(
            side=bench["side"].map(SIDE_LABELS),
            ewr_value_text=bench.apply(lambda row: fmt(row["ewr_value"], row["unit"]), axis=1),
            peer_median_text=bench.apply(lambda row: fmt(row["peer_median"], row["unit"]), axis=1),
        )[
            [
                "side",
                "indicator",
                "ewr_value_text",
                "peer_median_text",
                "ewr_rank",
                "rank_direction",
            ]
        ].to_markdown(index=False),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def run(months: list[int], out_dir: Path, top_n: int, write_tables: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = pd.concat([airport_side_records(read_month(month)) for month in months], ignore_index=True)
    days = period_days(records)
    summary = period_summary(records, days)
    peers = top_airports(summary, top_n=top_n)
    changes = stress_interim_changes(summary, peers)
    dom = dominant_carrier_share(records, peers)
    retention = route_retention(records, days, peers)
    benchmark = build_indicator_benchmark(changes, dom, retention, peers)

    summary[summary["airport"].isin(peers)].to_csv(out_dir / "large_airport_period_summary.csv", index=False)
    changes.to_csv(out_dir / "large_airport_stress_interim_changes.csv", index=False)
    dom.to_csv(out_dir / "dominant_carrier_share.csv", index=False)
    retention.to_csv(out_dir / "service_market_retention.csv", index=False)
    benchmark.to_csv(out_dir / "policy_indicator_benchmark.csv", index=False)
    (out_dir / "benchmark_airports.json").write_text(json.dumps(peers, indent=2), encoding="utf-8")
    write_summary(out_dir, months, peers, benchmark)
    if write_tables and TABLES.exists():
        write_latex_table(benchmark, TABLES / "tab_transferability_benchmark.tex")

    print(benchmark.to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--top-n", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.smoke:
        run(months=[4, 5, 6], out_dir=OUT_SMOKE, top_n=args.top_n, write_tables=False)
    else:
        run(months=list(range(1, 13)), out_dir=OUT, top_n=args.top_n, write_tables=True)


if __name__ == "__main__":
    main()


