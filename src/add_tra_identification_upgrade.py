from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


BASE = Path(__file__).resolve().parents[1]
TOP50_DAILY = BASE / "results" / "tra_policy_experiments" / "airport_side_daily_top_airports.csv"
TEN_AIRPORT_DAILY = BASE / "results" / "ewr_2025_full" / "airport_side_daily.csv"
OUT = BASE / "results" / "tra_identification_upgrade"
OUT_SMOKE = BASE / "results" / "tra_identification_upgrade_smoke"
TABLES = BASE / "article" / "elsarticle" / "tables"

SMOKE_AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL"]
PHASES = {
    "stress": ("2025-04-15", "2025-05-19", "Stress"),
    "early_interim": ("2025-05-20", "2025-06-02", "May 20--Jun 2"),
    "late_interim": ("2025-06-03", "2025-06-15", "Jun 3--Jun 15"),
}
REFERENCE = ("2025-03-18", "2025-04-14")
STRESS_STARTS = ["2025-04-15", "2025-04-22", "2025-05-01", "2025-05-07", "2025-05-14"]

METRICS = {
    "scheduled_ops": ("Scheduled ops/day", "ops"),
    "cancel_rate": ("Cancellation rate", "pp"),
    "delay15_rate": ("Delay-15-plus rate", "pp"),
    "nas_delay_per_scheduled_op": ("NAS delay", "min/op"),
}


def format_value(value: float, unit: str) -> str:
    if pd.isna(value):
        return "--"
    if unit == "pp":
        return f"{100 * value:.1f} pp"
    return f"{value:.1f}"


def format_month_day(value: str) -> str:
    ts = pd.Timestamp(value)
    return f"{ts:%b} {ts.day}"


def format_ci(coef: float, low: float, high: float, unit: str) -> str:
    if pd.isna(coef) or pd.isna(low) or pd.isna(high):
        return "--"
    if unit == "pp":
        return f"{100 * coef:.1f} [{100 * low:.1f}, {100 * high:.1f}]"
    return f"{coef:.1f} [{low:.1f}, {high:.1f}]"


def load_daily(path: Path, smoke: bool, months: list[int] | None = None) -> pd.DataFrame:
    daily = pd.read_csv(path, parse_dates=["FlightDate"])
    daily["date_id"] = daily["FlightDate"].dt.strftime("%Y-%m-%d")
    if months:
        daily = daily[daily["FlightDate"].dt.month.isin(months)].copy()
    if smoke:
        daily = daily[daily["airport"].isin(SMOKE_AIRPORTS)].copy()
    return daily


def restrict_policy_window(daily: pd.DataFrame, stress_start: str = "2025-04-15") -> pd.DataFrame:
    ref_start, ref_end = [pd.Timestamp(x) for x in REFERENCE]
    stress_start_ts = pd.Timestamp(stress_start)
    stress_end = pd.Timestamp("2025-05-19")
    early_start, early_end = [pd.Timestamp(x) for x in PHASES["early_interim"][:2]]
    late_start, late_end = [pd.Timestamp(x) for x in PHASES["late_interim"][:2]]
    mask = (
        daily["FlightDate"].between(ref_start, ref_end)
        | daily["FlightDate"].between(stress_start_ts, stress_end)
        | daily["FlightDate"].between(early_start, early_end)
        | daily["FlightDate"].between(late_start, late_end)
    )
    data = daily.loc[mask].copy()
    data["ewr_stress"] = ((data["airport"] == "EWR") & data["FlightDate"].between(stress_start_ts, stress_end)).astype(int)
    data["ewr_early_interim"] = (
        (data["airport"] == "EWR") & data["FlightDate"].between(early_start, early_end)
    ).astype(int)
    data["ewr_late_interim"] = (
        (data["airport"] == "EWR") & data["FlightDate"].between(late_start, late_end)
    ).astype(int)
    return data


def fit_phase_model_result(data: pd.DataFrame, outcome: str, include_weather: bool = False):
    rhs = "ewr_stress + ewr_early_interim + ewr_late_interim + C(airport) + C(date_id)"
    if include_weather and "weather_delay_per_scheduled_op" in data.columns and outcome != "scheduled_ops":
        rhs += " + weather_delay_per_scheduled_op"
    return smf.ols(f"{outcome} ~ {rhs}", data=data).fit(
        cov_type="cluster",
        cov_kwds={"groups": data["date_id"]},
    )


def fit_phase_model(data: pd.DataFrame, outcome: str, include_weather: bool = False) -> dict[str, tuple[float, float, float, float]]:
    model = fit_phase_model_result(data, outcome, include_weather)
    out: dict[str, tuple[float, float, float, float]] = {}
    for key in ["ewr_stress", "ewr_early_interim", "ewr_late_interim"]:
        coef = float(model.params.get(key, np.nan))
        se = float(model.bse.get(key, np.nan))
        out[key] = (coef, se, coef - 1.96 * se, coef + 1.96 * se)
    return out


def run_phase_date_fe(daily: pd.DataFrame, include_weather: bool = False) -> pd.DataFrame:
    rows = []
    for side in ["arr", "dep"]:
        side_data = restrict_policy_window(daily[daily["side"] == side].copy())
        for metric, (label, unit) in METRICS.items():
            estimates = fit_phase_model(side_data.dropna(subset=[metric]), metric, include_weather)
            for term, phase_label in [
                ("ewr_stress", "Stress"),
                ("ewr_early_interim", "May 20--Jun 2"),
                ("ewr_late_interim", "Jun 3--Jun 15"),
            ]:
                coef, se, low, high = estimates[term]
                rows.append(
                    {
                        "side": side,
                        "metric": metric,
                        "metric_label": label,
                        "unit": unit,
                        "phase": phase_label,
                        "coef": coef,
                        "se": se,
                        "ci_low": low,
                        "ci_high": high,
                        "weather_control": include_weather,
                    }
                )
    return pd.DataFrame(rows)


def run_stress_start_sensitivity(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for start in STRESS_STARTS:
        for side in ["arr", "dep"]:
            side_data = restrict_policy_window(daily[daily["side"] == side].copy(), stress_start=start)
            for metric in ["delay15_rate", "nas_delay_per_scheduled_op"]:
                label, unit = METRICS[metric]
                model = fit_phase_model_result(side_data.dropna(subset=[metric]), metric)
                cov = model.cov_params()
                stress = float(model.params.get("ewr_stress", np.nan))
                late = float(model.params.get("ewr_late_interim", np.nan))
                stress_se = float(model.bse.get("ewr_stress", np.nan))
                late_se = float(model.bse.get("ewr_late_interim", np.nan))
                if {"ewr_stress", "ewr_late_interim"}.issubset(cov.index):
                    recovery_se = float(
                        np.sqrt(
                            cov.loc["ewr_late_interim", "ewr_late_interim"]
                            + cov.loc["ewr_stress", "ewr_stress"]
                            - 2 * cov.loc["ewr_late_interim", "ewr_stress"]
                        )
                    )
                else:
                    recovery_se = np.nan
                recovery = late - stress
                rows.append(
                    {
                        "stress_start": start,
                        "side": side,
                        "metric": metric,
                        "metric_label": label,
                        "unit": unit,
                        "stress_coef": stress,
                        "stress_se": stress_se,
                        "stress_ci_low": stress - 1.96 * stress_se,
                        "stress_ci_high": stress + 1.96 * stress_se,
                        "late_coef": late,
                        "late_se": late_se,
                        "late_ci_low": late - 1.96 * late_se,
                        "late_ci_high": late + 1.96 * late_se,
                        "late_minus_stress": recovery,
                        "late_minus_stress_se": recovery_se,
                        "late_minus_stress_ci_low": recovery - 1.96 * recovery_se,
                        "late_minus_stress_ci_high": recovery + 1.96 * recovery_se,
                    }
                )
    return pd.DataFrame(rows)


def phase_value(frame: pd.DataFrame, metric: str, side: str, phase: str) -> pd.Series:
    row = frame[(frame["metric"] == metric) & (frame["side"] == side) & (frame["phase"] == phase)]
    if row.empty:
        raise ValueError(f"Missing phase estimate: {metric} {side} {phase}")
    return row.iloc[0]


def write_phase_table(phase: pd.DataFrame, table_path: Path) -> None:
    order = ["scheduled_ops", "cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]
    phase_cols = ["Stress", "May 20--Jun 2", "Jun 3--Jun 15"]
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Calendar-date fixed-effect phase estimates}",
        r"\label{tab:phase-date-fe}",
        r"\begin{tabular}{@{}llccc@{}}",
        r"\toprule",
        r"Outcome & Side & Stress & May 20--Jun 2 & Jun 3--Jun 15 \\",
        r"\midrule",
    ]
    for metric in order:
        for side in ["arr", "dep"]:
            cells = []
            for phase_name in phase_cols:
                row = phase_value(phase, metric, side, phase_name)
                value = format_ci(row["coef"], row["ci_low"], row["ci_high"], row["unit"])
                if row["coef"] < 0 and row["ci_high"] < 0 and phase_name in ["May 20--Jun 2", "Jun 3--Jun 15"]:
                    value = rf"\textbf{{{value}}}"
                cells.append(value)
            label = phase_value(phase, metric, side, "Stress")["metric_label"]
            lines.append(f"{label} & {side.upper()} & {cells[0]} & {cells[1]} & {cells[2]} \\\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: ARR means arrivals, DEP means departures, and NAS means National Airspace System. Cells report coefficient [95\% confidence interval] for the EWR-by-phase interaction from an airport-day panel with airport fixed effects and calendar-date fixed effects. Standard errors are clustered by calendar date. The omitted EWR reference period is March 18--April 14, 2025. Cancellation and delay-15-plus coefficients are percentage-point values. Lower values are favorable for cancellations, delay-15-plus, and NAS delay. Bold post-May-20 values have confidence intervals entirely below zero.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_stress_start_table(sensitivity: pd.DataFrame, table_path: Path) -> None:
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Stress-window start-date sensitivity}",
        r"\label{tab:stress-start-sensitivity}",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Stress start & ARR D15+ & ARR NAS & DEP D15+ & DEP NAS \\",
        r"\midrule",
    ]
    for start in STRESS_STARTS:
        cells = []
        for side, metric in [
            ("arr", "delay15_rate"),
            ("arr", "nas_delay_per_scheduled_op"),
            ("dep", "delay15_rate"),
            ("dep", "nas_delay_per_scheduled_op"),
        ]:
            row = sensitivity[
                (sensitivity["stress_start"] == start) & (sensitivity["side"] == side) & (sensitivity["metric"] == metric)
            ].iloc[0]
            value = format_value(row["late_minus_stress"], row["unit"])
            if row["late_minus_stress"] < 0:
                value = rf"\textbf{{{value}}}"
            cells.append(value)
        lines.append(f"{format_month_day(start)} & {cells[0]} & {cells[1]} & {cells[2]} & {cells[3]} \\\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: D15+ means delay-15-plus, ARR means arrivals, DEP means departures, and NAS means National Airspace System. Values are late-interim minus stress coefficients from the calendar-date fixed-effect phase model after changing the stress-window start date. More negative values indicate stronger recovery from stress to June 3--June 15 at EWR relative to same-date comparison airports.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(phase: pd.DataFrame, weather_phase: pd.DataFrame | None, sensitivity: pd.DataFrame, out_dir: Path) -> None:
    lines = [
        "# TRA identification upgrade",
        "",
        "## Calendar-date fixed-effect phase model",
        "",
        phase.to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    if weather_phase is not None and not weather_phase.empty:
        lines.extend(
            [
                "## Ten-airport phase model with BTS weather-delay control",
                "",
                weather_phase.to_markdown(index=False, floatfmt=".4f"),
                "",
            ]
        )
    lines.extend(
        [
            "## Stress-window start-date sensitivity",
            "",
            sensitivity.to_markdown(index=False, floatfmt=".4f"),
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = OUT_SMOKE if args.smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    top50 = load_daily(TOP50_DAILY, smoke=args.smoke, months=[3, 4, 5, 6])
    phase = run_phase_date_fe(top50, include_weather=False)
    sensitivity = run_stress_start_sensitivity(top50)
    weather_phase = pd.DataFrame()
    if TEN_AIRPORT_DAILY.exists():
        ten = load_daily(TEN_AIRPORT_DAILY, smoke=args.smoke, months=[3, 4, 5, 6])
        weather_phase = run_phase_date_fe(ten, include_weather=True)
    phase.to_csv(out_dir / "phase_date_fe.csv", index=False)
    sensitivity.to_csv(out_dir / "stress_start_sensitivity.csv", index=False)
    if not weather_phase.empty:
        weather_phase.to_csv(out_dir / "phase_date_fe_bts_weather_control.csv", index=False)
    write_summary(phase, weather_phase, sensitivity, out_dir)
    if not args.smoke and TABLES.exists():
        write_phase_table(phase, TABLES / "tab_phase_date_fe.tex")
        write_stress_start_table(sensitivity, TABLES / "tab_stress_start_sensitivity.tex")
    print("Calendar-date FE phase model")
    print(phase.to_string(index=False))
    print("\nStress-start sensitivity")
    print(sensitivity.to_string(index=False))
    if not weather_phase.empty:
        print("\nBTS-weather-control sensitivity")
        print(weather_phase.to_string(index=False))


if __name__ == "__main__":
    main()
