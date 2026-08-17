from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw_bts_2024"
OUT = BASE / "results" / "calendar_placebo_2024"
TABLES = BASE / "results" / "tables"
DID_2025 = BASE / "results" / "did_robustness" / "did_robustness.csv"

AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL", "IAD", "DCA", "BWI", "ATL", "ORD"]
WINDOW_2024 = ("2024-04-15", "2024-05-19", "2024-05-20", "2024-06-15")
SMOKE_WINDOW = ("2024-04-15", "2024-04-20", "2024-05-20", "2024-05-25")

USECOLS = [
    "FlightDate",
    "Origin",
    "Dest",
    "DepDel15",
    "ArrDel15",
    "Cancelled",
    "Diverted",
    "WeatherDelay",
    "NASDelay",
]

METRICS = {
    "scheduled_ops": ("Scheduled ops/day", False, "ops"),
    "cancel_rate": ("Cancellation rate", True, "pp"),
    "delay15_rate": ("Delay-15-plus rate", True, "pp"),
    "nas_delay_per_scheduled_op": ("NAS delay", True, "min"),
}


def read_month(month: int) -> pd.DataFrame:
    zip_path = RAW / f"bts_on_time_2024_{month:02d}.zip"
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

    arr = df[df["Dest"].isin(AIRPORTS)].copy()
    arr["airport"] = arr["Dest"]
    arr["side"] = "arr"
    arr["delay15"] = arr["ArrDel15"]

    cols = [
        "FlightDate",
        "airport",
        "side",
        "delay15",
        "Cancelled",
        "Diverted",
        "WeatherDelay",
        "NASDelay",
    ]
    return pd.concat([dep[cols], arr[cols]], ignore_index=True)


def safe_rate(num: pd.Series, den: pd.Series) -> pd.Series:
    return num / den.replace(0, np.nan)


def summarize_daily(side: pd.DataFrame) -> pd.DataFrame:
    side = side.copy()
    side["operated"] = (side["Cancelled"].fillna(0) == 0).astype(int)
    side["cancelled_flag"] = side["Cancelled"].fillna(0).astype(float)
    side["delay15_flag"] = side["delay15"].fillna(0).astype(float)
    side["WeatherDelay"] = side["WeatherDelay"].fillna(0).astype(float)
    side["NASDelay"] = side["NASDelay"].fillna(0).astype(float)

    daily = (
        side.groupby(["FlightDate", "airport", "side"], as_index=False)
        .agg(
            scheduled_ops=("operated", "size"),
            operated_ops=("operated", "sum"),
            cancelled_ops=("cancelled_flag", "sum"),
            delay15_ops=("delay15_flag", "sum"),
            weather_delay_minutes=("WeatherDelay", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
        )
    )
    daily["cancel_rate"] = safe_rate(daily["cancelled_ops"], daily["scheduled_ops"])
    daily["delay15_rate"] = safe_rate(daily["delay15_ops"], daily["operated_ops"])
    daily["weather_delay_per_scheduled_op"] = safe_rate(daily["weather_delay_minutes"], daily["scheduled_ops"])
    daily["nas_delay_per_scheduled_op"] = safe_rate(daily["nas_delay_minutes"], daily["scheduled_ops"])
    daily["dow"] = daily["FlightDate"].dt.day_name()
    return daily


def prepare_window(daily: pd.DataFrame, side: str, window: tuple[str, str, str, str]) -> pd.DataFrame:
    base_start, base_end, post_start, post_end = [pd.Timestamp(x) for x in window]
    data = daily[
        (daily["side"] == side)
        & (
            daily["FlightDate"].between(base_start, base_end)
            | daily["FlightDate"].between(post_start, post_end)
        )
    ].copy()
    data["post"] = data["FlightDate"].between(post_start, post_end).astype(int)
    data["treated_post"] = ((data["airport"] == "EWR") & (data["post"] == 1)).astype(int)
    data["week_block"] = data["FlightDate"].dt.to_period("W-SUN").astype(str)
    return data


def fit_did(data: pd.DataFrame, outcome: str, adjust_weather: bool) -> float:
    rhs = "treated_post + post + C(airport) + C(dow)"
    if adjust_weather:
        rhs += " + weather_delay_per_scheduled_op"
    model = smf.ols(f"{outcome} ~ {rhs}", data=data).fit()
    return float(model.params["treated_post"])


def block_bootstrap_ci(
    data: pd.DataFrame,
    outcome: str,
    adjust_weather: bool,
    boot: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    blocks = np.array(sorted(data["week_block"].unique()))
    coefs: list[float] = []
    for _ in range(boot):
        sampled = rng.choice(blocks, size=len(blocks), replace=True)
        pieces = []
        for idx, block in enumerate(sampled):
            piece = data[data["week_block"] == block].copy()
            piece["boot_block"] = idx
            pieces.append(piece)
        boot_data = pd.concat(pieces, ignore_index=True)
        try:
            coefs.append(fit_did(boot_data, outcome, adjust_weather))
        except Exception:
            continue
    if len(coefs) < max(20, boot // 5):
        return float("nan"), float("nan")
    lo, hi = np.percentile(coefs, [2.5, 97.5])
    return float(lo), float(hi)


def run_models(daily: pd.DataFrame, window: tuple[str, str, str, str], boot: int, seed: int) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(seed)
    for side in ["arr", "dep"]:
        data = prepare_window(daily, side, window)
        for metric, (label, adjust_weather, unit) in METRICS.items():
            coef = fit_did(data, metric, adjust_weather)
            lo, hi = block_bootstrap_ci(data, metric, adjust_weather, boot, rng)
            rows.append(
                {
                    "window": "2024_same_calendar",
                    "side": side,
                    "metric": metric,
                    "metric_label": label,
                    "unit": unit,
                    "coef": coef,
                    "ci_low": lo,
                    "ci_high": hi,
                }
            )
    return pd.DataFrame(rows)


def format_value(value: float, unit: str) -> str:
    if pd.isna(value):
        return "--"
    if unit == "pp":
        return f"{100 * value:.1f} pp"
    return f"{value:.1f}"


def write_latex_table(results_2024: pd.DataFrame, table_path: Path) -> None:
    did_2025 = pd.read_csv(DID_2025)
    did_2025 = did_2025[did_2025["window"] == "main"][
        ["side", "metric", "coef"]
    ].rename(columns={"coef": "coef_2025"})
    merged = results_2024.merge(did_2025, on=["side", "metric"], how="left")
    order = ["scheduled_ops", "cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Same-calendar 2024 placebo DID check}",
        r"\label{tab:calendar-placebo-2024}",
        r"\begin{tabular}{@{}llrr@{}}",
        r"\toprule",
        r"Outcome & Side & 2025 main DID & 2024 placebo DID \\",
        r"\midrule",
    ]
    for metric in order:
        for side in ["arr", "dep"]:
            row = merged[(merged["metric"] == metric) & (merged["side"] == side)].iloc[0]
            unit = row["unit"]
            main_2025 = format_value(row["coef_2025"], unit)
            placebo_2024 = format_value(row["coef"], unit)
            main_cell = rf"\textbf{{{main_2025}}}" if row["coef_2025"] < 0 else main_2025
            lines.append(f"{row['metric_label']} & {side.upper()} & {main_cell} & {placebo_2024} \\\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: DID means difference-in-differences, ARR means arrivals, DEP means departures, and NAS means National Airspace System. The 2025 main DID compares April 15--May 19 with May 20--June 15, 2025. The 2024 placebo uses the same calendar days in 2024. Models use airport and day-of-week fixed effects; reliability outcomes include weather-delay minutes per scheduled operation. Bold values mark the 2025 management-signal direction.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(results: pd.DataFrame, out_dir: Path) -> None:
    main = results[results["metric"] == "nas_delay_per_scheduled_op"].copy()
    signal = {
        f"{row.side}_nas_2024_placebo": row.coef for row in main.itertuples(index=False)
    }
    lines = [
        "# Same-calendar 2024 placebo DID check",
        "",
        "The check compares April 15-May 19 with May 20-June 15 in 2024 using the same airport set, fixed effects, and outcome definitions as the main 2025 DID.",
        "",
        results.to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(signal, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boot", type=int, default=499)
    parser.add_argument("--seed", type=int, default=20260520)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    months = [4, 5] if args.smoke else [4, 5, 6]
    boot = 49 if args.smoke else args.boot
    window = SMOKE_WINDOW if args.smoke else WINDOW_2024
    side = pd.concat([airport_side_records(read_month(month)) for month in months], ignore_index=True)
    daily = summarize_daily(side)
    results = run_models(daily, window=window, boot=boot, seed=args.seed)
    if args.smoke:
        print(results.to_string(index=False))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    daily.to_csv(OUT / "airport_side_daily_2024_apr_jun.csv", index=False)
    results.to_csv(OUT / "calendar_placebo_2024_did.csv", index=False)
    write_summary(results, OUT)
    if TABLES.exists():
        write_latex_table(results, TABLES / "tab_calendar_placebo_2024.tex")
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
