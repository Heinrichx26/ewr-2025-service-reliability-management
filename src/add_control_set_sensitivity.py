from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = BASE / "results" / "ewr_2025_full" / "airport_side_period_summary.csv"
DEFAULT_OUT = BASE / "results" / "control_set_sensitivity"
DEFAULT_TABLES = BASE / "results" / "tables"

BASE_PERIOD = "stress_20250415_0519"
COMPARE_PERIOD = "interim_20250520_0615"

CONTROL_SETS = {
    "All controls": ["JFK", "LGA", "BOS", "PHL", "IAD", "DCA", "BWI", "ATL", "ORD"],
    "Exclude New York City airports": ["BOS", "PHL", "IAD", "DCA", "BWI", "ATL", "ORD"],
    "Regional controls outside New York City": ["BOS", "PHL", "IAD", "DCA", "BWI"],
    "Large hubs only": ["ATL", "ORD"],
    "Exclude large hubs": ["JFK", "LGA", "BOS", "PHL", "IAD", "DCA", "BWI"],
}

METRICS = {
    "cancel_rate": "Cancellation rate",
    "delay15_rate": "Delay-15-plus rate",
    "nas_delay_per_scheduled_op": "NAS delay",
}


def compute_sensitivity(period: pd.DataFrame) -> pd.DataFrame:
    records = []
    for metric, metric_label in METRICS.items():
        wide = (
            period.pivot_table(
                index=["airport", "side"],
                columns="period",
                values=metric,
                aggfunc="first",
                observed=False,
            )
            .reset_index()
            .copy()
        )
        wide["delta"] = wide[COMPARE_PERIOD] - wide[BASE_PERIOD]
        for set_label, airports in CONTROL_SETS.items():
            for side in ["arr", "dep"]:
                ewr_delta = float(wide[(wide["airport"] == "EWR") & (wide["side"] == side)]["delta"].iloc[0])
                control_delta = float(wide[(wide["airport"].isin(airports)) & (wide["side"] == side)]["delta"].mean())
                records.append(
                    {
                        "control_set": set_label,
                        "metric": metric,
                        "metric_label": metric_label,
                        "side": side,
                        "airport_count": len(airports),
                        "ewr_delta": ewr_delta,
                        "control_mean_delta": control_delta,
                        "ewr_minus_control_delta": ewr_delta - control_delta,
                    }
                )
    return pd.DataFrame(records)


def fmt_pp(value: float) -> str:
    return f"{100 * value:.1f} pp"


def fmt_num(value: float) -> str:
    return f"{value:.1f}"


def bold_negative(text: str, value: float) -> str:
    return f"\\textbf{{{text}}}" if value < 0 else text


def write_latex_table(sensitivity: pd.DataFrame, table_path: Path) -> None:
    order = [
        "All controls",
        "Exclude New York City airports",
        "Regional controls outside New York City",
        "Large hubs only",
        "Exclude large hubs",
    ]
    pivot = sensitivity.pivot_table(
        index="control_set",
        columns=["metric", "side"],
        values="ewr_minus_control_delta",
        aggfunc="first",
        observed=False,
    )
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\footnotesize",
        "\\caption{Control-set sensitivity for the stress-to-interim recovery}",
        "\\label{tab:control-set-sensitivity}",
        "\\begin{tabular}{@{}P{0.29\\linewidth}rrrr@{}}",
        "\\toprule",
        "Control set & ARR delay-15+ & ARR NAS & DEP delay-15+ & DEP NAS \\\\",
        "\\midrule",
    ]
    for label in order:
        arr_delay = float(pivot.loc[label, ("delay15_rate", "arr")])
        arr_nas = float(pivot.loc[label, ("nas_delay_per_scheduled_op", "arr")])
        dep_delay = float(pivot.loc[label, ("delay15_rate", "dep")])
        dep_nas = float(pivot.loc[label, ("nas_delay_per_scheduled_op", "dep")])
        cells = [
            label,
            bold_negative(fmt_pp(arr_delay), arr_delay),
            bold_negative(fmt_num(arr_nas), arr_nas),
            bold_negative(fmt_pp(dep_delay), dep_delay),
            bold_negative(fmt_num(dep_nas), dep_nas),
        ]
        lines.append(" & ".join(cells) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\footnotesize Notes: ARR means arrivals, DEP means departures, and NAS means National Airspace System. Values are EWR changes minus control-airport mean changes from the stress period to the interim-order period. Lower values indicate stronger recovery at EWR and are bolded.}",
            "\\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_markdown_summary(sensitivity: pd.DataFrame, out_dir: Path) -> None:
    rows = sensitivity[
        sensitivity["metric"].isin(["delay15_rate", "nas_delay_per_scheduled_op"])
    ].copy()
    lines = [
        "# Control-set sensitivity",
        "",
        "Comparison: stress period to interim-order period.",
        "",
        rows[
            [
                "control_set",
                "metric",
                "side",
                "airport_count",
                "ewr_delta",
                "control_mean_delta",
                "ewr_minus_control_delta",
            ]
        ].to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    period = pd.read_csv(args.input)
    sensitivity = compute_sensitivity(period)
    if args.smoke:
        smoke = sensitivity[
            (sensitivity["control_set"].isin(["All controls", "Exclude New York City airports"]))
            & (sensitivity["metric"].isin(["delay15_rate", "nas_delay_per_scheduled_op"]))
        ].copy()
        print(smoke.to_string(index=False))
        return

    args.out.mkdir(parents=True, exist_ok=True)
    args.tables.mkdir(parents=True, exist_ok=True)
    sensitivity.to_csv(args.out / "control_set_sensitivity.csv", index=False)
    write_markdown_summary(sensitivity, args.out)
    write_latex_table(sensitivity, args.tables / "tab_control_set_sensitivity.tex")
    print(sensitivity.to_string(index=False))


if __name__ == "__main__":
    main()
