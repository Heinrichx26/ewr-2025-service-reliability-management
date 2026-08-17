from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


BASE = Path(__file__).resolve().parents[1]
DAILY = BASE / "results" / "ewr_2025_full" / "airport_side_daily.csv"
OUT = BASE / "results" / "did_robustness"
TABLES = BASE / "results" / "tables"

WINDOWS = {
    "main": ("2025-04-15", "2025-05-19", "2025-05-20", "2025-06-15"),
    "pre_stress_placebo": ("2025-02-12", "2025-03-18", "2025-03-19", "2025-04-14"),
}

METRICS = {
    "scheduled_ops": ("Scheduled ops/day", False, "ops"),
    "cancel_rate": ("Cancellation rate", True, "pp"),
    "delay15_rate": ("Delay-15-plus rate", True, "pp"),
    "nas_delay_per_scheduled_op": ("NAS delay", True, "min"),
}


def format_value(value: float, unit: str) -> str:
    if unit == "pp":
        return f"{100 * value:.1f} pp"
    return f"{value:.1f}"


def fit_did(data: pd.DataFrame, outcome: str, adjust_weather: bool) -> float:
    rhs = "treated_post + post + C(airport) + C(dow)"
    if adjust_weather:
        rhs += " + weather_delay_per_scheduled_op"
    model = smf.ols(f"{outcome} ~ {rhs}", data=data).fit()
    return float(model.params["treated_post"])


def prepare_window(daily: pd.DataFrame, window: tuple[str, str, str, str], side: str) -> pd.DataFrame:
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


def block_bootstrap_ci(
    data: pd.DataFrame,
    outcome: str,
    adjust_weather: bool,
    boot: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    blocks = np.array(sorted(data["week_block"].unique()))
    coefs = []
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


def run_models(daily: pd.DataFrame, boot: int, seed: int) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(seed)
    for window_name, window in WINDOWS.items():
        for side in ["arr", "dep"]:
            data = prepare_window(daily, window, side)
            for metric, (label, adjust_weather, unit) in METRICS.items():
                coef = fit_did(data, metric, adjust_weather)
                lo, hi = block_bootstrap_ci(data, metric, adjust_weather, boot, rng)
                rows.append(
                    {
                        "window": window_name,
                        "side": side,
                        "metric": metric,
                        "metric_label": label,
                        "unit": unit,
                        "weather_adjusted": adjust_weather,
                        "coef": coef,
                        "ci_low": lo,
                        "ci_high": hi,
                    }
                )
    return pd.DataFrame(rows)


def run_no_weather_models(daily: pd.DataFrame, boot: int, seed: int) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(seed)
    for side in ["arr", "dep"]:
        data = prepare_window(daily, WINDOWS["main"], side)
        for metric, (label, _adjust_weather, unit) in METRICS.items():
            if metric == "scheduled_ops":
                continue
            coef = fit_did(data, metric, adjust_weather=False)
            lo, hi = block_bootstrap_ci(data, metric, adjust_weather=False, boot=boot, rng=rng)
            rows.append(
                {
                    "window": "main",
                    "side": side,
                    "metric": metric,
                    "metric_label": label,
                    "unit": unit,
                    "weather_adjusted": False,
                    "coef": coef,
                    "ci_low": lo,
                    "ci_high": hi,
                }
            )
    return pd.DataFrame(rows)


def write_latex_table(results: pd.DataFrame, table_path: Path) -> None:
    main = results[results["window"] == "main"].copy()
    placebo = results[results["window"] == "pre_stress_placebo"][
        ["side", "metric", "coef"]
    ].rename(columns={"coef": "placebo_coef"})
    merged = main.merge(placebo, on=["side", "metric"], how="left")
    order = ["scheduled_ops", "cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{Daily DID robustness and pre-stress placebo checks}",
        "\\label{tab:did-robustness}",
        "\\begin{tabular}{@{}llrrr@{}}",
        "\\toprule",
        "Outcome & Side & Main DID & 95\\% block CI & Pre-stress placebo \\\\",
        "\\midrule",
    ]
    for metric in order:
        for side in ["arr", "dep"]:
            row = merged[(merged["metric"] == metric) & (merged["side"] == side)].iloc[0]
            unit = row["unit"]
            coef = format_value(row["coef"], unit)
            lo = format_value(row["ci_low"], unit)
            hi = format_value(row["ci_high"], unit)
            placebo = format_value(row["placebo_coef"], unit)
            good = row["coef"] < 0
            coef_cell = f"\\textbf{{{coef}}}" if good else coef
            lines.append(
                f"{row['metric_label']} & {side.upper()} & {coef_cell} & [{lo}, {hi}] & {placebo} \\\\"
            )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: DID means difference-in-differences, ARR means arrivals, DEP means departures, NAS means National Airspace System, and pp means percentage points. Models use airport and day-of-week fixed effects; reliability models also include weather-delay minutes per scheduled operation. The main window compares April 15--May 19 with May 20--June 15, 2025. The placebo compares February 12--March 18 with March 19--April 14, 2025. Confidence intervals use calendar-week block bootstrap. Lower values indicate stronger recovery at EWR and are bolded.}",
            "\\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_no_weather_latex_table(
    weather_results: pd.DataFrame,
    no_weather: pd.DataFrame,
    table_path: Path,
) -> None:
    weather_main = weather_results[
        (weather_results["window"] == "main")
        & (weather_results["metric"].isin(no_weather["metric"].unique()))
    ][["side", "metric", "coef"]].rename(columns={"coef": "weather_adjusted_coef"})
    merged = no_weather.merge(weather_main, on=["side", "metric"], how="left")
    order = ["cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{Daily reliability DID estimates without weather-delay control}",
        "\\label{tab:did-no-weather}",
        "\\begin{tabular}{@{}llrrr@{}}",
        "\\toprule",
        "Outcome & Side & No-weather DID & 95\\% block CI & Table 5 DID \\\\",
        "\\midrule",
    ]
    for metric in order:
        for side in ["arr", "dep"]:
            row = merged[(merged["metric"] == metric) & (merged["side"] == side)].iloc[0]
            unit = row["unit"]
            coef = format_value(row["coef"], unit)
            lo = format_value(row["ci_low"], unit)
            hi = format_value(row["ci_high"], unit)
            weather_coef = format_value(row["weather_adjusted_coef"], unit)
            coef_cell = f"\\textbf{{{coef}}}" if row["coef"] < 0 else coef
            lines.append(
                f"{row['metric_label']} & {side.upper()} & {coef_cell} & [{lo}, {hi}] & {weather_coef} \\\\"
            )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: DID means difference-in-differences, ARR means arrivals, DEP means departures, NAS means National Airspace System, and pp means percentage points. No-weather models use airport and day-of-week fixed effects. Table 5 DID reports the corresponding main-manuscript estimates with weather-delay minutes per scheduled operation included. Lower values indicate stronger recovery at EWR and are bolded.}",
            "\\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(results: pd.DataFrame, no_weather: pd.DataFrame, out_dir: Path) -> None:
    lines = [
        "# Daily DID robustness",
        "",
        "Models use airport and day-of-week fixed effects. Reliability outcomes include weather-delay minutes per scheduled operation as a covariate.",
        "",
        results.to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Reliability DID without weather-delay control",
        "",
        "These models use airport and day-of-week fixed effects only.",
        "",
        no_weather.to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boot", type=int, default=499)
    parser.add_argument("--seed", type=int, default=20260510)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    daily = pd.read_csv(DAILY, parse_dates=["FlightDate"])
    boot = 49 if args.smoke else args.boot
    results = run_models(daily, boot=boot, seed=args.seed)
    no_weather = run_no_weather_models(daily, boot=boot, seed=args.seed + 17)
    if args.smoke:
        print(results.to_string(index=False))
        print("\nNo-weather reliability DID:")
        print(no_weather.to_string(index=False))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT / "did_robustness.csv", index=False)
    no_weather.to_csv(OUT / "did_no_weather_reliability.csv", index=False)
    write_summary(results, no_weather, OUT)
    if TABLES.exists():
        write_latex_table(results, TABLES / "tab_did_robustness.tex")
        write_no_weather_latex_table(results, no_weather, TABLES / "tab_did_no_weather.tex")
    print(results.to_string(index=False))
    print("\nNo-weather reliability DID:")
    print(no_weather.to_string(index=False))


if __name__ == "__main__":
    main()
