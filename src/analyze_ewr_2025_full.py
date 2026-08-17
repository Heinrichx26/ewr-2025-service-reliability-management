from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw_bts_2025"
RESULTS = BASE / "results" / "ewr_2025_full"
TABLES = BASE / "results" / "tables"

AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL", "IAD", "DCA", "BWI", "ATL", "ORD"]
CONTROL_AIRPORTS = [airport for airport in AIRPORTS if airport != "EWR"]

USECOLS = [
    "FlightDate",
    "Reporting_Airline",
    "IATA_CODE_Reporting_Airline",
    "Origin",
    "Dest",
    "DepDelayMinutes",
    "ArrDelayMinutes",
    "DepDel15",
    "ArrDel15",
    "Cancelled",
    "Diverted",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "LateAircraftDelay",
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

METRIC_LABELS = {
    "ops_per_day": "Ops/day",
    "cancel_rate": "Cancel. rate",
    "delay15_rate": "Delay-15+ rate",
    "nas_delay_per_scheduled_op": "NAS min/op",
    "weather_delay_per_scheduled_op": "Weather min/op",
}


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


def airport_side_records(df: pd.DataFrame) -> pd.DataFrame:
    dep = df[df["Origin"].isin(AIRPORTS)].copy()
    dep["airport"] = dep["Origin"]
    dep["side"] = "dep"
    dep["delay15"] = dep["DepDel15"]
    dep["delay_minutes"] = dep["DepDelayMinutes"]

    arr = df[df["Dest"].isin(AIRPORTS)].copy()
    arr["airport"] = arr["Dest"]
    arr["side"] = "arr"
    arr["delay15"] = arr["ArrDel15"]
    arr["delay_minutes"] = arr["ArrDelayMinutes"]

    cols = [
        "FlightDate",
        "airport",
        "side",
        "Reporting_Airline",
        "IATA_CODE_Reporting_Airline",
        "delay15",
        "delay_minutes",
        "Cancelled",
        "Diverted",
        "CarrierDelay",
        "WeatherDelay",
        "NASDelay",
        "SecurityDelay",
        "LateAircraftDelay",
    ]
    return pd.concat([dep[cols], arr[cols]], ignore_index=True)


def safe_rate(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0, np.nan)


def add_flags(side: pd.DataFrame) -> pd.DataFrame:
    side = side.copy()
    side["operated"] = (side["Cancelled"].fillna(0) == 0).astype(int)
    side["cancelled_flag"] = side["Cancelled"].fillna(0).astype(float)
    side["diverted_flag"] = side["Diverted"].fillna(0).astype(float)
    side["delay15_flag"] = side["delay15"].fillna(0).astype(float)
    for col in ["CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay", "LateAircraftDelay"]:
        side[col] = side[col].fillna(0).astype(float)
    return side


def summarize_daily(side: pd.DataFrame) -> pd.DataFrame:
    side = add_flags(side)
    daily = (
        side.groupby(["FlightDate", "airport", "side"], as_index=False)
        .agg(
            scheduled_ops=("operated", "size"),
            operated_ops=("operated", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            diverted_ops=("diverted_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            delay_minutes_mean=("delay_minutes", "mean"),
            carrier_delay_minutes=("CarrierDelay", "sum"),
            weather_delay_minutes=("WeatherDelay", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
            security_delay_minutes=("SecurityDelay", "sum"),
            late_aircraft_delay_minutes=("LateAircraftDelay", "sum"),
        )
    )
    daily["cancel_rate"] = safe_rate(daily["cancelled_ops"], daily["scheduled_ops"])
    daily["delay15_rate"] = safe_rate(daily["delay15_ops"], daily["operated_ops"])
    daily["nas_delay_per_scheduled_op"] = safe_rate(daily["nas_delay_minutes"], daily["scheduled_ops"])
    daily["weather_delay_per_scheduled_op"] = safe_rate(daily["weather_delay_minutes"], daily["scheduled_ops"])
    daily["carrier_delay_per_scheduled_op"] = safe_rate(daily["carrier_delay_minutes"], daily["scheduled_ops"])
    daily["late_aircraft_delay_per_scheduled_op"] = safe_rate(daily["late_aircraft_delay_minutes"], daily["scheduled_ops"])
    daily["period"] = daily["FlightDate"].map(period_label)
    daily["dow"] = daily["FlightDate"].dt.day_name()
    return daily


def summarize_carrier_daily(side: pd.DataFrame) -> pd.DataFrame:
    side = add_flags(side)
    ewr = side[side["airport"] == "EWR"].copy()
    daily = (
        ewr.groupby(["FlightDate", "Reporting_Airline", "IATA_CODE_Reporting_Airline", "side"], as_index=False)
        .agg(
            scheduled_ops=("operated", "size"),
            operated_ops=("operated", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
            weather_delay_minutes=("WeatherDelay", "sum"),
        )
    )
    daily["cancel_rate"] = safe_rate(daily["cancelled_ops"], daily["scheduled_ops"])
    daily["delay15_rate"] = safe_rate(daily["delay15_ops"], daily["operated_ops"])
    daily["nas_delay_per_scheduled_op"] = safe_rate(daily["nas_delay_minutes"], daily["scheduled_ops"])
    daily["period"] = daily["FlightDate"].map(period_label)
    return daily


def aggregate_periods(daily: pd.DataFrame) -> pd.DataFrame:
    out = (
        daily.groupby(["airport", "side", "period"], as_index=False)
        .agg(
            days=("FlightDate", "nunique"),
            scheduled_ops=("scheduled_ops", "sum"),
            operated_ops=("operated_ops", "sum"),
            cancelled_ops=("cancelled_ops", "sum"),
            delay15_ops=("delay15_ops", "sum"),
            nas_delay_minutes=("nas_delay_minutes", "sum"),
            weather_delay_minutes=("weather_delay_minutes", "sum"),
        )
    )
    out["ops_per_day"] = out["scheduled_ops"] / out["days"]
    out["cancel_rate"] = safe_rate(out["cancelled_ops"], out["scheduled_ops"])
    out["delay15_rate"] = safe_rate(out["delay15_ops"], out["operated_ops"])
    out["nas_delay_per_scheduled_op"] = safe_rate(out["nas_delay_minutes"], out["scheduled_ops"])
    out["weather_delay_per_scheduled_op"] = safe_rate(out["weather_delay_minutes"], out["scheduled_ops"])
    out["period"] = pd.Categorical(out["period"], categories=PERIOD_ORDER, ordered=True)
    return out.sort_values(["airport", "side", "period"]).reset_index(drop=True)


def carrier_periods(carrier_daily: pd.DataFrame) -> pd.DataFrame:
    out = (
        carrier_daily.groupby(["IATA_CODE_Reporting_Airline", "Reporting_Airline", "side", "period"], as_index=False)
        .agg(
            days=("FlightDate", "nunique"),
            scheduled_ops=("scheduled_ops", "sum"),
            operated_ops=("operated_ops", "sum"),
            cancelled_ops=("cancelled_ops", "sum"),
            delay15_ops=("delay15_ops", "sum"),
            nas_delay_minutes=("nas_delay_minutes", "sum"),
            weather_delay_minutes=("weather_delay_minutes", "sum"),
        )
    )
    out["ops_per_day"] = out["scheduled_ops"] / out["days"]
    out["cancel_rate"] = safe_rate(out["cancelled_ops"], out["scheduled_ops"])
    out["delay15_rate"] = safe_rate(out["delay15_ops"], out["operated_ops"])
    out["nas_delay_per_scheduled_op"] = safe_rate(out["nas_delay_minutes"], out["scheduled_ops"])
    out["period"] = pd.Categorical(out["period"], categories=PERIOD_ORDER, ordered=True)
    return out.sort_values(["IATA_CODE_Reporting_Airline", "side", "period"]).reset_index(drop=True)


def contrast_table(period: pd.DataFrame, base_period: str, compare_period: str) -> pd.DataFrame:
    rows = []
    for metric in METRIC_LABELS:
        wide = period.pivot_table(
            index=["airport", "side"],
            columns="period",
            values=metric,
            aggfunc="first",
            observed=False,
        ).reset_index()
        if base_period not in wide.columns or compare_period not in wide.columns:
            continue
        wide["delta"] = wide[compare_period] - wide[base_period]
        for side in ["arr", "dep"]:
            ewr_delta = float(wide[(wide["airport"] == "EWR") & (wide["side"] == side)]["delta"].iloc[0])
            control_delta = float(wide[(wide["airport"].isin(CONTROL_AIRPORTS)) & (wide["side"] == side)]["delta"].mean())
            rows.append(
                {
                    "metric": metric,
                    "metric_label": METRIC_LABELS[metric],
                    "side": side,
                    "base_period": base_period,
                    "compare_period": compare_period,
                    "ewr_delta": ewr_delta,
                    "control_mean_delta": control_delta,
                    "ewr_minus_control_delta": ewr_delta - control_delta,
                }
            )
    return pd.DataFrame(rows)


def all_contrasts(period: pd.DataFrame) -> pd.DataFrame:
    comparisons = []
    for compare_period in PERIOD_ORDER[1:]:
        comparisons.append(contrast_table(period, "pre_20250101_0414", compare_period))
    for compare_period in PERIOD_ORDER[2:]:
        comparisons.append(contrast_table(period, "stress_20250415_0519", compare_period))
    return pd.concat(comparisons, ignore_index=True)


def leave_one_control(period: pd.DataFrame) -> pd.DataFrame:
    records = []
    base_period = "stress_20250415_0519"
    compare_period = "interim_20250520_0615"
    for metric in ["cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]:
        wide = period.pivot_table(
            index=["airport", "side"],
            columns="period",
            values=metric,
            aggfunc="first",
            observed=False,
        ).reset_index()
        if base_period not in wide.columns or compare_period not in wide.columns:
            continue
        wide["delta"] = wide[compare_period] - wide[base_period]
        for side in ["arr", "dep"]:
            ewr_delta = float(wide[(wide["airport"] == "EWR") & (wide["side"] == side)]["delta"].iloc[0])
            for excluded in CONTROL_AIRPORTS:
                keep = [airport for airport in CONTROL_AIRPORTS if airport != excluded]
                control_delta = float(wide[(wide["airport"].isin(keep)) & (wide["side"] == side)]["delta"].mean())
                records.append(
                    {
                        "metric": metric,
                        "side": side,
                        "excluded_control": excluded,
                        "ewr_delta": ewr_delta,
                        "control_mean_delta": control_delta,
                        "ewr_minus_control_delta": ewr_delta - control_delta,
                    }
                )
    return pd.DataFrame(records)


def placebo_rank(period: pd.DataFrame) -> pd.DataFrame:
    records = []
    base_period = "stress_20250415_0519"
    compare_period = "interim_20250520_0615"
    for metric in ["cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]:
        wide = period.pivot_table(
            index=["airport", "side"],
            columns="period",
            values=metric,
            aggfunc="first",
            observed=False,
        ).reset_index()
        if base_period not in wide.columns or compare_period not in wide.columns:
            continue
        wide["delta"] = wide[compare_period] - wide[base_period]
        for side in ["arr", "dep"]:
            rows = wide[wide["side"] == side].copy()
            for airport in AIRPORTS:
                treated_delta = float(rows[rows["airport"] == airport]["delta"].iloc[0])
                control_delta = float(rows[rows["airport"] != airport]["delta"].mean())
                records.append(
                    {
                        "metric": metric,
                        "side": side,
                        "pseudo_treated_airport": airport,
                        "treated_minus_control_delta": treated_delta - control_delta,
                    }
                )
    out = pd.DataFrame(records)
    ranked = []
    for (metric, side), group in out.groupby(["metric", "side"], as_index=False):
        group = group.copy()
        group["rank_most_negative"] = group["treated_minus_control_delta"].rank(method="min", ascending=True).astype(int)
        group["airport_count"] = len(group)
        ranked.append(group)
    return pd.concat(ranked, ignore_index=True)


def fmt_num(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return ""
    return f"{value:.{digits}f}"


def fmt_pct(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return ""
    return f"{100 * value:.{digits}f}\\%"


def bold_if(text: str, condition: bool) -> str:
    return f"\\textbf{{{text}}}" if condition else text


def latex_table_ewr_period(period: pd.DataFrame) -> str:
    ewr = period[(period["airport"] == "EWR") & (period["side"] == "arr")].copy()
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{EWR arrival reliability across policy periods}",
        "\\label{tab:ewr-arrival-periods}",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "Period & Ops/day & Cancel. rate & Delay-15+ rate & NAS min/op \\\\",
        "\\midrule",
    ]
    for _, row in ewr.iterrows():
        period_name = PERIOD_LABELS[str(row["period"])]
        is_interim = str(row["period"]) == "interim_20250520_0615"
        cells = [
            period_name,
            bold_if(fmt_num(row["ops_per_day"], 1), is_interim),
            bold_if(fmt_pct(row["cancel_rate"], 1), is_interim),
            bold_if(fmt_pct(row["delay15_rate"], 1), is_interim),
            bold_if(fmt_num(row["nas_delay_per_scheduled_op"], 1), is_interim),
        ]
        lines.append(" & ".join(cells) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: Lower cancellation rates, delay-15-plus rates, and NAS minutes per scheduled operation indicate better service reliability. Bold values mark the strongest immediate interim-order reliability recovery period.}",
            "\\end{table}",
        ]
    )
    return "\n".join(lines)


def latex_table_recovery(contrasts: pd.DataFrame) -> str:
    rows = contrasts[
        (contrasts["base_period"] == "stress_20250415_0519")
        & (contrasts["compare_period"] == "interim_20250520_0615")
        & (contrasts["metric"].isin(["ops_per_day", "cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]))
    ].copy()
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{Stress-to-interim recovery relative to control airports}",
        "\\label{tab:stress-interim-recovery}",
        "\\begin{tabular}{@{}llrrr@{}}",
        "\\toprule",
        "Outcome & Side & EWR change & Control change & EWR-control \\\\",
        "\\midrule",
    ]
    for _, row in rows.iterrows():
        metric = row["metric"]
        if metric in ["cancel_rate", "delay15_rate"]:
            ewr = fmt_pct(row["ewr_delta"], 1)
            control = fmt_pct(row["control_mean_delta"], 1)
            contrast = fmt_pct(row["ewr_minus_control_delta"], 1)
        else:
            ewr = fmt_num(row["ewr_delta"], 1)
            control = fmt_num(row["control_mean_delta"], 1)
            contrast = fmt_num(row["ewr_minus_control_delta"], 1)
        good = row["ewr_minus_control_delta"] < 0
        cells = [row["metric_label"], row["side"].upper(), ewr, control, bold_if(contrast, good)]
        lines.append(" & ".join(cells) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: The base period is 2025-04-15 to 2025-05-19, and the comparison period is 2025-05-20 to 2025-06-15. Negative EWR-minus-control values indicate stronger reliability recovery at EWR than at the control airports; these values are bolded.}",
            "\\end{table}",
        ]
    )
    return "\n".join(lines)


def latex_table_united(carrier_period: pd.DataFrame) -> str:
    ua = carrier_period[carrier_period["IATA_CODE_Reporting_Airline"] == "UA"].copy()
    ua = ua[ua["side"].isin(["arr", "dep"])]
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{United Airlines exposure at EWR}",
        "\\label{tab:united-ewr}",
        "\\begin{tabular}{@{}llrrr@{}}",
        "\\toprule",
        "Period & Side & Ops/day & Cancel. rate & Delay-15+ rate \\\\",
        "\\midrule",
    ]
    for _, row in ua.iterrows():
        is_interim = str(row["period"]) == "interim_20250520_0615"
        cells = [
            PERIOD_LABELS[str(row["period"])],
            row["side"].upper(),
            bold_if(fmt_num(row["ops_per_day"], 1), is_interim),
            bold_if(fmt_pct(row["cancel_rate"], 1), is_interim),
            bold_if(fmt_pct(row["delay15_rate"], 1), is_interim),
        ]
        lines.append(" & ".join(cells) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: Lower cancellation and delay-15-plus rates indicate better service reliability. Bold values mark the immediate interim-order period.}",
            "\\end{table}",
        ]
    )
    return "\n".join(lines)


def write_markdown_summary(period: pd.DataFrame, contrasts: pd.DataFrame, carrier_period: pd.DataFrame, out_dir: Path) -> None:
    ewr = period[period["airport"] == "EWR"].copy()
    recovery = contrasts[
        (contrasts["base_period"] == "stress_20250415_0519")
        & (contrasts["compare_period"] == "interim_20250520_0615")
    ].copy()
    ua = carrier_period[carrier_period["IATA_CODE_Reporting_Airline"] == "UA"].copy()
    lines = [
        "# EWR 2025 full-year BTS analysis",
        "",
        "Data: BTS On-Time Performance, January-December 2025.",
        "",
        "## EWR period summary",
        ewr[
            [
                "side",
                "period",
                "days",
                "ops_per_day",
                "cancel_rate",
                "delay15_rate",
                "nas_delay_per_scheduled_op",
                "weather_delay_per_scheduled_op",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Stress-to-interim recovery contrasts",
        recovery[
            [
                "metric",
                "side",
                "ewr_delta",
                "control_mean_delta",
                "ewr_minus_control_delta",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
        "## United Airlines at EWR",
        ua[
            [
                "side",
                "period",
                "days",
                "ops_per_day",
                "cancel_rate",
                "delay15_rate",
                "nas_delay_per_scheduled_op",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def build_outputs(months: list[int], out_dir: Path, table_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)

    side_parts = []
    for month in months:
        df = read_month(month)
        side_parts.append(airport_side_records(df))
    side = pd.concat(side_parts, ignore_index=True)

    daily = summarize_daily(side)
    carrier_daily = summarize_carrier_daily(side)
    period = aggregate_periods(daily)
    carrier_period = carrier_periods(carrier_daily)
    contrasts = all_contrasts(period)
    loo = leave_one_control(period)
    placebo = placebo_rank(period)

    daily.to_csv(out_dir / "airport_side_daily.csv", index=False)
    period.to_csv(out_dir / "airport_side_period_summary.csv", index=False)
    carrier_daily.to_csv(out_dir / "ewr_carrier_side_daily.csv", index=False)
    carrier_period.to_csv(out_dir / "ewr_carrier_period_summary.csv", index=False)
    contrasts.to_csv(out_dir / "ewr_vs_controls_period_contrasts.csv", index=False)
    loo.to_csv(out_dir / "leave_one_control_recovery.csv", index=False)
    placebo.to_csv(out_dir / "placebo_recovery_ranks.csv", index=False)

    (table_dir / "tab_ewr_arrival_periods.tex").write_text(latex_table_ewr_period(period), encoding="utf-8")
    (table_dir / "tab_stress_interim_recovery.tex").write_text(latex_table_recovery(contrasts), encoding="utf-8")
    (table_dir / "tab_united_ewr.tex").write_text(latex_table_united(carrier_period), encoding="utf-8")
    write_markdown_summary(period, contrasts, carrier_period, out_dir)

    quality = {
        "months": months,
        "airport_count": len(AIRPORTS),
        "control_airports": CONTROL_AIRPORTS,
        "periods": PERIOD_LABELS,
        "rows": {
            "airport_side_daily": int(len(daily)),
            "airport_side_period_summary": int(len(period)),
            "ewr_carrier_period_summary": int(len(carrier_period)),
        },
        "stress_to_interim_core_result": contrasts[
            (contrasts["base_period"] == "stress_20250415_0519")
            & (contrasts["compare_period"] == "interim_20250520_0615")
            & (contrasts["metric"].isin(["ops_per_day", "cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]))
        ].to_dict(orient="records"),
        "placebo_rank_for_ewr": placebo[placebo["pseudo_treated_airport"] == "EWR"].to_dict(orient="records"),
    }
    (out_dir / "summary.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", nargs="+", type=int, default=list(range(1, 13)))
    parser.add_argument("--out", type=Path, default=RESULTS)
    parser.add_argument("--tables", type=Path, default=TABLES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    months = sorted(set(args.months))
    invalid = [month for month in months if month < 1 or month > 12]
    if invalid:
        raise ValueError(f"Invalid months: {invalid}")
    build_outputs(months, args.out, args.tables)


if __name__ == "__main__":
    main()

