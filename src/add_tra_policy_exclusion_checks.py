from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from add_tra_policy_experiments import run_synthetic_placebos, synthetic_one


BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "results" / "tra_policy_experiments"
TABLES = BASE / "article" / "elsarticle" / "tables"

DAILY_FILE = OUT / "airport_side_daily_top_airports.csv"
AIRPORTS_FILE = OUT / "synthetic_donor_airports.json"
WEIGHTS_FILE = OUT / "synthetic_control_weights.csv"

METRICS = ["delay15_rate", "nas_delay_per_scheduled_op"]
METRIC_LABELS = {
    "delay15_rate": "Delay-15-plus rate",
    "nas_delay_per_scheduled_op": "NAS delay",
}
METRIC_UNITS = {
    "delay15_rate": "pp",
    "nas_delay_per_scheduled_op": "min/op",
}


def fmt(value: float, unit: str) -> str:
    if pd.isna(value):
        return "--"
    if unit == "pp":
        return f"{100 * value:.1f}"
    return f"{value:.1f}"


def bold_if_negative(text: str, value: float) -> str:
    return f"\\textbf{{{text}}}" if value < 0 else text


def load_base_airports() -> list[str]:
    data = json.loads(AIRPORTS_FILE.read_text(encoding="utf-8"))
    airports = data["airports"]
    if "EWR" not in airports:
        airports.append("EWR")
    return airports


def high_weight_donors() -> list[str]:
    weights = pd.read_csv(WEIGHTS_FILE)
    donors = (
        weights.loc[weights["weight"] > 0.01, "donor_airport"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    return sorted(set(donors))


def scenario_definitions() -> list[tuple[str, list[str]]]:
    return [
        ("Baseline donor pool", []),
        ("Exclude NYC airports (JFK, LGA)", ["JFK", "LGA"]),
        ("Exclude nearby Northeast airports", ["JFK", "LGA", "BOS", "PHL", "BWI", "DCA", "IAD"]),
        ("Exclude high-weight donor airports", high_weight_donors()),
    ]


def donor_airports(base_airports: list[str], exclude: list[str]) -> list[str]:
    exclude_set = set(exclude)
    return [airport for airport in base_airports if airport not in exclude_set]


def evaluate_scenario(
    daily: pd.DataFrame,
    base_airports: list[str],
    scenario_name: str,
    exclude: list[str],
    intervention_date: str,
    metrics: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    airports = donor_airports(base_airports, exclude)
    if "EWR" not in airports:
        airports.append("EWR")

    paths = []
    weights = []
    summary_rows = []
    for side in ["arr", "dep"]:
        for metric in metrics:
            path, weight, stats = synthetic_one(
                daily,
                "EWR",
                side,
                metric,
                airports,
                intervention_date,
                "2025-06-15",
            )
            paths.append(path)
            weights.append(weight)
            summary_rows.append(
                {
                    "scenario": scenario_name,
                    "side": side,
                    "metric": metric,
                    "metric_label": METRIC_LABELS[metric],
                    "unit": METRIC_UNITS[metric],
                    "excluded_airports": ", ".join(exclude) if exclude else "--",
                    **stats,
                }
            )

    placebo = run_synthetic_placebos(daily, airports, intervention_date, metrics)
    summary = pd.DataFrame(summary_rows)
    ewr_placebo = placebo[placebo["treated_airport"] == "EWR"].copy()
    summary = summary.merge(
        ewr_placebo[
            [
                "treated_airport",
                "side",
                "metric",
                "rank_recovery_most_negative",
                "airports",
                "permutation_p_recovery_lower_or_equal",
            ]
        ].rename(
            columns={
                "treated_airport": "airport",
                "rank_recovery_most_negative": "rank",
                "permutation_p_recovery_lower_or_equal": "p_value",
                "airports": "donor_count",
            }
        ),
        left_on=["side", "metric"],
        right_on=["side", "metric"],
        how="left",
    )
    summary["scenario_airports"] = len(airports) - 1
    summary["donor_count"] = summary["scenario_airports"]
    summary["rank"] = summary["rank"].fillna(np.nan)
    summary["p_value"] = summary["p_value"].fillna(np.nan)
    return summary, pd.concat(weights, ignore_index=True)


def write_markdown(summary: pd.DataFrame, out_dir: Path) -> None:
    lines = [
        "# Synthetic-control exclusion sensitivity",
        "",
        "The table reports EWR recovery gaps after excluding selected donor airports from the synthetic-control donor pool.",
        "",
        summary[
            [
                "scenario",
                "side",
                "metric",
                "excluded_airports",
                "recovery_gap",
                "pre_rmse",
                "rank",
                "p_value",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    (out_dir / "synthetic_control_exclusion_sensitivity.md").write_text("\n".join(lines), encoding="utf-8")


def write_latex(summary: pd.DataFrame) -> None:
    pivot = summary.pivot_table(
        index="scenario",
        columns=["side", "metric"],
        values="recovery_gap",
        aggfunc="first",
        observed=False,
    )
    order = [
        "Baseline donor pool",
        "Exclude NYC airports (JFK, LGA)",
        "Exclude nearby Northeast airports",
        "Exclude high-weight donor airports",
    ]
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\small",
        "\\caption{Synthetic-control exclusion sensitivity}",
        "\\label{tab:synthetic-exclusion-sensitivity}",
        "\\begin{tabular}{@{}P{0.34\\linewidth}rrrr@{}}",
        "\\toprule",
        "Scenario & ARR delay-15+ & ARR NAS & DEP delay-15+ & DEP NAS \\\\",
        "\\midrule",
    ]
    for scenario in order:
        arr_delay = float(pivot.loc[scenario, ("arr", "delay15_rate")])
        arr_nas = float(pivot.loc[scenario, ("arr", "nas_delay_per_scheduled_op")])
        dep_delay = float(pivot.loc[scenario, ("dep", "delay15_rate")])
        dep_nas = float(pivot.loc[scenario, ("dep", "nas_delay_per_scheduled_op")])
        cells = [
            scenario,
            bold_if_negative(fmt(arr_delay, "pp"), arr_delay),
            bold_if_negative(fmt(arr_nas, "min/op"), arr_nas),
            bold_if_negative(fmt(dep_delay, "pp"), dep_delay),
            bold_if_negative(fmt(dep_nas, "min/op"), dep_nas),
        ]
        lines.append(" & ".join(cells) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.95\\linewidth}{\\small Notes: Values are EWR minus synthetic stress-to-interim recovery gaps. Lower values indicate stronger EWR recovery. NYC airports are JFK and LGA. High-weight donors have weight above 1\\% in at least one baseline reliability synthetic control.}",
            "\\end{table}",
        ]
    )
    (TABLES / "tab_synthetic_exclusion_sensitivity.tex").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--intervention-date", default="2025-05-20")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not DAILY_FILE.exists():
        raise FileNotFoundError(DAILY_FILE)
    daily = pd.read_csv(DAILY_FILE, parse_dates=["FlightDate"])
    base_airports = load_base_airports()
    scenarios = scenario_definitions()
    if args.smoke:
        scenarios = scenarios[:2]
        metrics_to_run = ["nas_delay_per_scheduled_op"]
    else:
        metrics_to_run = METRICS

    all_summary = []
    all_weights = []
    for scenario_name, exclude in scenarios:
        scenario_summary, scenario_weights = evaluate_scenario(
            daily,
            base_airports,
            scenario_name,
            exclude,
            args.intervention_date,
            metrics_to_run,
        )
        all_summary.append(scenario_summary)
        all_weights.append(scenario_weights.assign(scenario=scenario_name))

    summary = pd.concat(all_summary, ignore_index=True)
    weights = pd.concat(all_weights, ignore_index=True)

    if args.smoke:
        print(summary.to_string(index=False))
        return

    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "synthetic_control_exclusion_sensitivity.csv", index=False)
    weights.to_csv(OUT / "synthetic_control_exclusion_weights.csv", index=False)
    write_markdown(summary, OUT)
    if TABLES.exists():
        write_latex(summary)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
