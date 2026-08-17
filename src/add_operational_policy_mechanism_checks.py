from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "results" / "operational_policy_mechanism"
OUT_SMOKE = BASE / "results" / "operational_policy_mechanism_smoke"
TABLES = BASE / "article" / "elsarticle" / "tables"


def result_csv(directories: list[str], filename: str) -> Path:
    for directory in directories:
        candidate = BASE / "results" / directory / filename
        if candidate.exists():
            return candidate
    searched = ", ".join(str(BASE / "results" / directory / filename) for directory in directories)
    raise FileNotFoundError(f"Could not find {filename}. Searched: {searched}")


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}\\%"


def pp_change(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f} pp"


def num(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def bold(text: str) -> str:
    return f"\\textbf{{{text}}}"


def load_inputs() -> dict[str, pd.DataFrame]:
    return {
        "period": pd.read_csv(BASE / "results" / "ewr_2025_full" / "airport_side_period_summary.csv"),
        "did": pd.read_csv(BASE / "results" / "did_robustness" / "did_robustness.csv"),
        "no_weather": pd.read_csv(BASE / "results" / "did_robustness" / "did_no_weather_reliability.csv"),
        "hourly": pd.read_csv(BASE / "results" / "hourly_schedule_pressure" / "hourly_schedule_pressure_summary.csv"),
        "route": pd.read_csv(
            result_csv(["rtbm_business_checks", "access_carrier_checks"], "route_service_retention.csv")
        ),
        "carrier": pd.read_csv(
            result_csv(["rtbm_business_checks", "access_carrier_checks"], "carrier_group_stress_interim_contrast.csv")
        ),
        "t100": pd.read_csv(BASE / "results" / "tra_policy_experiments" / "t100_policy_exposure_summary.csv"),
        "synthetic": pd.read_csv(BASE / "results" / "tra_policy_experiments" / "synthetic_control_summary.csv"),
        "synthetic_placebos": pd.read_csv(
            BASE / "results" / "tra_policy_experiments" / "synthetic_control_placebos.csv"
        ),
        "exclusions": pd.read_csv(
            BASE / "results" / "tra_policy_experiments" / "synthetic_control_exclusion_sensitivity.csv"
        ),
    }


def period_row(period: pd.DataFrame, side: str, period_name: str) -> pd.Series:
    row = period[
        (period["airport"] == "EWR") & (period["side"] == side) & (period["period"] == period_name)
    ]
    if row.empty:
        raise ValueError(f"Missing period row: {side} {period_name}")
    return row.iloc[0]


def did_coef(did: pd.DataFrame, side: str, metric: str) -> float:
    row = did[(did["window"] == "main") & (did["side"] == side) & (did["metric"] == metric)]
    if row.empty:
        raise ValueError(f"Missing DID row: {side} {metric}")
    return float(row.iloc[0]["coef"])


def route_retention(route: pd.DataFrame, side: str, threshold: str) -> float:
    row = route[(route["side"] == side) & (route["threshold"] == threshold)]
    if row.empty:
        raise ValueError(f"Missing route retention row: {side} {threshold}")
    return float(row.iloc[0]["retention_rate"])


def t100_value(t100: pd.DataFrame, side: str, col: str) -> float:
    row = t100[t100["side"] == side]
    if row.empty:
        raise ValueError(f"Missing T-100 row: {side}")
    return float(row.iloc[0][col])


def carrier_delta(carrier: pd.DataFrame, group: str, side: str) -> float:
    row = carrier[(carrier["carrier_group"] == group) & (carrier["side"] == side)]
    if row.empty:
        raise ValueError(f"Missing carrier row: {group} {side}")
    return float(row.iloc[0]["delta_ops_per_day"])


def build_bridge(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    period = data["period"]
    did = data["did"]
    no_weather = data["no_weather"]
    hourly = data["hourly"]
    route = data["route"]
    carrier = data["carrier"]
    t100 = data["t100"]
    synthetic = data["synthetic"]
    synthetic_placebos = data["synthetic_placebos"]
    exclusions = data["exclusions"]

    arr_stress = period_row(period, "arr", "stress_20250415_0519")
    arr_interim = period_row(period, "arr", "interim_20250520_0615")
    dep_stress = period_row(period, "dep", "stress_20250415_0519")
    dep_interim = period_row(period, "dep", "interim_20250520_0615")

    arr_ops_delta = arr_interim["scheduled_ops"] / arr_interim["days"] - arr_stress["scheduled_ops"] / arr_stress["days"]
    dep_ops_delta = dep_interim["scheduled_ops"] / dep_interim["days"] - dep_stress["scheduled_ops"] / dep_stress["days"]

    dep_hour_stress = hourly[(hourly["period"] == "stress_20250415_0519") & (hourly["side"] == "dep")].iloc[0]
    dep_hour_interim = hourly[(hourly["period"] == "interim_20250520_0615") & (hourly["side"] == "dep")].iloc[0]
    arr_hour_stress = hourly[(hourly["period"] == "stress_20250415_0519") & (hourly["side"] == "arr")].iloc[0]
    arr_hour_interim = hourly[(hourly["period"] == "interim_20250520_0615") & (hourly["side"] == "arr")].iloc[0]

    arr_nas_stress = arr_stress["nas_delay_minutes"] / arr_stress["scheduled_ops"]
    arr_nas_interim = arr_interim["nas_delay_minutes"] / arr_interim["scheduled_ops"]
    arr_cancel_stress = arr_stress["cancelled_ops"] / arr_stress["scheduled_ops"]
    arr_cancel_interim = arr_interim["cancelled_ops"] / arr_interim["scheduled_ops"]
    arr_d15_stress = arr_stress["delay15_ops"] / arr_stress["operated_ops"]
    arr_d15_interim = arr_interim["delay15_ops"] / arr_interim["operated_ops"]

    arr_nas_no_weather = did_coef(no_weather, "arr", "nas_delay_per_scheduled_op")
    arr_sc = synthetic[
        (synthetic["treated_airport"] == "EWR")
        & (synthetic["side"] == "arr")
        & (synthetic["metric"] == "nas_delay_per_scheduled_op")
    ].iloc[0]
    arr_sc_placebo = synthetic_placebos[
        (synthetic_placebos["treated_airport"] == "EWR")
        & (synthetic_placebos["side"] == "arr")
        & (synthetic_placebos["metric"] == "nas_delay_per_scheduled_op")
    ].iloc[0]
    arr_excl = exclusions[
        (exclusions["side"] == "arr") & (exclusions["metric"] == "nas_delay_per_scheduled_op")
    ]
    excl_min = arr_excl.loc[arr_excl["scenario"] != "Baseline donor pool", "recovery_gap"].max()
    excl_max = arr_excl.loc[arr_excl["scenario"] != "Baseline donor pool", "recovery_gap"].min()

    rows = [
        {
            "layer": "Capacity governance",
            "operational_complication": "Scheduled access target",
            "evidence_bridge": (
                f"BTS ops/day: ARR {bold(num(arr_ops_delta))}, DEP {bold(num(dep_ops_delta))}."
            ),
        },
        {
            "layer": "Peak-hour pressure",
            "operational_complication": "Bank and peak exposure",
            "evidence_bridge": (
                f"DEP p95 hourly scheduled ops falls {num(dep_hour_stress['p95_ops_per_hour'], 0)} to "
                f"{bold(num(dep_hour_interim['p95_ops_per_hour'], 0))}; "
                f"DEP hours above 28 fall {pct(dep_hour_stress['share_above_28'])} to "
                f"{bold(pct(dep_hour_interim['share_above_28']))}."
            ),
        },
        {
            "layer": "Delivered reliability",
            "operational_complication": "Realized service quality",
            "evidence_bridge": (
                f"ARR NAS min/op falls {num(arr_nas_stress)} to {bold(num(arr_nas_interim))}; "
                f"D15+ falls {pct(arr_d15_stress)} to {bold(pct(arr_d15_interim))}."
            ),
        },
        {
            "layer": "Counterfactual credibility",
            "operational_complication": "Compound recovery setting",
            "evidence_bridge": (
                f"SC ARR NAS gap is {bold(num(arr_sc['recovery_gap']))} with rank "
                f"{bold(str(int(arr_sc_placebo['rank_recovery_most_negative'])) + '/' + str(int(arr_sc_placebo['airports'])))}; "
                f"no-weather ARR NAS DID is {bold(num(arr_nas_no_weather))}."
            ),
        },
        {
            "layer": "Access and burden",
            "operational_complication": "Route access and carrier response",
            "evidence_bridge": (
                f"Weekly market retention: ARR {bold(pct(route_retention(route, 'arr', 'weekly')))}, "
                f"DEP {bold(pct(route_retention(route, 'dep', 'weekly')))}; "
                f"United ops/day: ARR {bold(num(carrier_delta(carrier, 'United', 'arr')))}, "
                f"DEP {bold(num(carrier_delta(carrier, 'United', 'dep')))}."
            ),
        },
    ]
    return pd.DataFrame(rows)


def write_latex(bridge: pd.DataFrame) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\small",
        "\\caption{Operational-policy mechanism and evidence bridge}",
        "\\label{tab:metric-set}",
        "\\begin{tabular}{@{}P{0.18\\linewidth}P{0.25\\linewidth}P{0.48\\linewidth}@{}}",
        "\\toprule",
        "Policy layer & Operational issue & Evidence bridge \\\\",
        "\\midrule",
    ]
    for row in bridge.itertuples(index=False):
        lines.append(f"{row.layer} & {row.operational_complication} & {row.evidence_bridge} \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\small Notes: ARR means arrivals, DEP means departures, BTS means Bureau of Transportation Statistics, FAA means Federal Aviation Administration, DID means difference-in-differences, SC means synthetic control, NAS means National Airspace System, and D15+ means delay-15-plus. Bold values mark the favorable policy-relevant evidence in each layer.}",
            "\\end{table}",
        ]
    )
    (TABLES / "tab_policy_metric_set.tex").write_text("\n".join(lines), encoding="utf-8")


def write_outputs(bridge: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    bridge.to_csv(out_dir / "policy_mechanism_bridge.csv", index=False)
    lines = ["# Operational-policy mechanism bridge", "", bridge.to_markdown(index=False), ""]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bridge = build_bridge(load_inputs())
    out_dir = OUT_SMOKE if args.smoke else OUT
    write_outputs(bridge, out_dir)
    if not args.smoke and TABLES.parent.exists():
        write_latex(bridge)
    print(bridge.to_string(index=False))


if __name__ == "__main__":
    main()
