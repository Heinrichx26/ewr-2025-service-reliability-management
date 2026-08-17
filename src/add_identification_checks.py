from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


BASE = Path(__file__).resolve().parents[1]
DAILY = BASE / "results" / "ewr_2025_full" / "airport_side_daily.csv"
OUT = BASE / "results" / "identification_checks"
TABLES = BASE / "results" / "tables"

MAIN_WINDOW = ("2025-04-15", "2025-05-19", "2025-05-20", "2025-06-15")
SHORT_WINDOWS = {
    "May 20--Jun 2": ("2025-04-15", "2025-05-19", "2025-05-20", "2025-06-02"),
    "Jun 3--Jun 15": ("2025-04-15", "2025-05-19", "2025-06-03", "2025-06-15"),
}
PLACEBO_WINDOWS = {
    "Jan 15--Feb 10": ("2025-01-15", "2025-02-10", "2025-02-11", "2025-03-09"),
    "Feb 12--Mar 18": ("2025-02-12", "2025-03-18", "2025-03-19", "2025-04-14"),
    "Mar 1--Mar 27": ("2025-03-01", "2025-03-27", "2025-03-28", "2025-04-14"),
}
EVENT_DATES = [
    ("Stress start", "2025-04-15", "2025-04-28"),
    ("Pre-order late", "2025-04-29", "2025-05-19"),
    ("May 20--Jun 2", "2025-05-20", "2025-06-02"),
    ("Jun 3--Jun 15", "2025-06-03", "2025-06-15"),
]

METRICS = {
    "scheduled_ops": ("Scheduled ops/day", False, "ops"),
    "cancel_rate": ("Cancellation rate", True, "pp"),
    "delay15_rate": ("Delay-15-plus rate", True, "pp"),
    "nas_delay_per_scheduled_op": ("NAS delay", True, "min"),
}


def format_value(value: float, unit: str) -> str:
    if pd.isna(value):
        return "--"
    if unit == "pp":
        return f"{100 * value:.1f} pp"
    return f"{value:.1f}"


def prepare_window(
    daily: pd.DataFrame,
    window: tuple[str, str, str, str],
    side: str,
    treated_airport: str = "EWR",
) -> pd.DataFrame:
    base_start, base_end, post_start, post_end = [pd.Timestamp(x) for x in window]
    data = daily[
        (daily["side"] == side)
        & (
            daily["FlightDate"].between(base_start, base_end)
            | daily["FlightDate"].between(post_start, post_end)
        )
    ].copy()
    data["post"] = data["FlightDate"].between(post_start, post_end).astype(int)
    data["treated"] = (data["airport"] == treated_airport).astype(int)
    data["treated_post"] = (data["treated"] & (data["post"] == 1)).astype(int)
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


def run_short_window_did(daily: pd.DataFrame, boot: int, seed: int) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(seed)
    for label, window in SHORT_WINDOWS.items():
        for side in ["arr", "dep"]:
            data = prepare_window(daily, window, side)
            for metric, (metric_label, adjust_weather, unit) in METRICS.items():
                coef = fit_did(data, metric, adjust_weather)
                lo, hi = block_bootstrap_ci(data, metric, adjust_weather, boot, rng)
                rows.append(
                    {
                        "window": label,
                        "side": side,
                        "metric": metric,
                        "metric_label": metric_label,
                        "unit": unit,
                        "coef": coef,
                        "ci_low": lo,
                        "ci_high": hi,
                    }
                )
    return pd.DataFrame(rows)


def run_multiple_placebos(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, window in PLACEBO_WINDOWS.items():
        for side in ["arr", "dep"]:
            data = prepare_window(daily, window, side)
            for metric, (metric_label, adjust_weather, unit) in METRICS.items():
                coef = fit_did(data, metric, adjust_weather)
                rows.append(
                    {
                        "placebo": label,
                        "side": side,
                        "metric": metric,
                        "metric_label": metric_label,
                        "unit": unit,
                        "coef": coef,
                    }
                )
    return pd.DataFrame(rows)


def run_airport_permutation(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    airports = sorted(daily["airport"].unique())
    for side in ["arr", "dep"]:
        for treated_airport in airports:
            data = prepare_window(daily, MAIN_WINDOW, side, treated_airport)
            for metric, (metric_label, adjust_weather, unit) in METRICS.items():
                coef = fit_did(data, metric, adjust_weather)
                rows.append(
                    {
                        "treated_airport": treated_airport,
                        "side": side,
                        "metric": metric,
                        "metric_label": metric_label,
                        "unit": unit,
                        "coef": coef,
                    }
                )
    out = pd.DataFrame(rows)
    out["rank_lowest"] = out.groupby(["side", "metric"])["coef"].rank(method="min", ascending=True)
    out["airports"] = out.groupby(["side", "metric"])["coef"].transform("count")
    out["permutation_p_lower_or_equal"] = out["rank_lowest"] / out["airports"]
    return out


def run_event_time(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base_start = pd.Timestamp("2025-03-18")
    base_end = pd.Timestamp("2025-04-14")
    for side in ["arr", "dep"]:
        for label, start, end in EVENT_DATES:
            window = (
                base_start.strftime("%Y-%m-%d"),
                base_end.strftime("%Y-%m-%d"),
                start,
                end,
            )
            data = prepare_window(daily, window, side)
            for metric, (metric_label, adjust_weather, unit) in METRICS.items():
                coef = fit_did(data, metric, adjust_weather)
                rows.append(
                    {
                        "event_period": label,
                        "side": side,
                        "metric": metric,
                        "metric_label": metric_label,
                        "unit": unit,
                        "coef": coef,
                    }
                )
    return pd.DataFrame(rows)


def write_short_window_table(short_did: pd.DataFrame, table_path: Path) -> None:
    focus = short_did[short_did["metric"].isin(["scheduled_ops", "nas_delay_per_scheduled_op"])].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Short-window DID estimates around the interim order}",
        r"\label{tab:short-did}",
        r"\begin{tabular}{@{}llrr@{}}",
        r"\toprule",
        r"Window & Side & Scheduled ops/day & NAS min/op \\",
        r"\midrule",
    ]
    for window in ["May 20--Jun 2", "Jun 3--Jun 15"]:
        for side in ["arr", "dep"]:
            sched = focus[
                (focus["window"] == window)
                & (focus["side"] == side)
                & (focus["metric"] == "scheduled_ops")
            ].iloc[0]
            nas = focus[
                (focus["window"] == window)
                & (focus["side"] == side)
                & (focus["metric"] == "nas_delay_per_scheduled_op")
            ].iloc[0]
            sched_value = format_value(sched["coef"], "ops")
            nas_value = format_value(nas["coef"], "min")
            sched_cell = rf"\textbf{{{sched_value}}}" if sched["coef"] < 0 else sched_value
            nas_cell = rf"\textbf{{{nas_value}}}" if nas["coef"] < 0 else nas_value
            lines.append(f"{window} & {side.upper()} & {sched_cell} & {nas_cell} \\\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: DID means difference-in-differences, ARR means arrivals, DEP means departures, and NAS means National Airspace System. Estimates compare each post-May-20 subwindow with April 15--May 19, 2025, using the same controls and fixed effects as the main DID model. Lower values indicate lower schedule exposure or lower NAS delay at EWR relative to controls and are bolded.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_placebo_table(placebos: pd.DataFrame, table_path: Path) -> None:
    focus = placebos[placebos["metric"].isin(["scheduled_ops", "nas_delay_per_scheduled_op"])].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Multiple pre-stress placebo DID estimates}",
        r"\label{tab:multiple-placebos}",
        r"\begin{tabular}{@{}llrr@{}}",
        r"\toprule",
        r"Placebo post window & Side & Scheduled ops/day & NAS min/op \\",
        r"\midrule",
    ]
    for placebo in PLACEBO_WINDOWS:
        for side in ["arr", "dep"]:
            sched = focus[
                (focus["placebo"] == placebo)
                & (focus["side"] == side)
                & (focus["metric"] == "scheduled_ops")
            ].iloc[0]
            nas = focus[
                (focus["placebo"] == placebo)
                & (focus["side"] == side)
                & (focus["metric"] == "nas_delay_per_scheduled_op")
            ].iloc[0]
            lines.append(
                f"{placebo} & {side.upper()} & {format_value(sched['coef'], 'ops')} & {format_value(nas['coef'], 'min')} \\\\"
            )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: DID means difference-in-differences, ARR means arrivals, DEP means departures, and NAS means National Airspace System. Placebo windows end before the April 15 stress-window start. These checks test whether ordinary pre-stress schedule changes were accompanied by the same NAS-delay recovery as the main window.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_permutation_table(permutation: pd.DataFrame, table_path: Path) -> None:
    ewr = permutation[
        (permutation["treated_airport"] == "EWR")
        & (permutation["metric"].isin(["scheduled_ops", "nas_delay_per_scheduled_op"]))
    ].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Airport-label permutation ranks for the main DID window}",
        r"\label{tab:airport-permutation}",
        r"\begin{tabular}{@{}llrr@{}}",
        r"\toprule",
        r"Outcome & Side & EWR DID & Rank among airports \\",
        r"\midrule",
    ]
    for metric in ["scheduled_ops", "nas_delay_per_scheduled_op"]:
        for side in ["arr", "dep"]:
            row = ewr[(ewr["metric"] == metric) & (ewr["side"] == side)].iloc[0]
            value = format_value(row["coef"], row["unit"])
            rank = f"{int(row['rank_lowest'])}/{int(row['airports'])}"
            cell = rf"\textbf{{{value}}}" if row["coef"] < 0 else value
            lines.append(f"{row['metric_label']} & {side.upper()} & {cell} & {rank} \\\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: Each airport is treated in turn as the pseudo-treated airport in the April 15--May 19 versus May 20--June 15 DID window. Rank 1/10 means the most negative estimate among the ten airports. Lower scheduled operations and lower NAS delay are the expected recovery direction and are bolded.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_event_time_table(event_time: pd.DataFrame, table_path: Path) -> None:
    focus = event_time[event_time["metric"] == "nas_delay_per_scheduled_op"].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Event-time DID estimates for NAS delay}",
        r"\label{tab:event-time-nas}",
        r"\begin{tabular}{@{}lrr@{}}",
        r"\toprule",
        r"Event period & ARR NAS min/op & DEP NAS min/op \\",
        r"\midrule",
    ]
    for label, _, _ in EVENT_DATES:
        arr = focus[(focus["event_period"] == label) & (focus["side"] == "arr")].iloc[0]
        dep = focus[(focus["event_period"] == label) & (focus["side"] == "dep")].iloc[0]
        arr_value = format_value(arr["coef"], "min")
        dep_value = format_value(dep["coef"], "min")
        arr_cell = rf"\textbf{{{arr_value}}}" if arr["coef"] < 0 and "Jun" in label else arr_value
        dep_cell = rf"\textbf{{{dep_value}}}" if dep["coef"] < 0 and "Jun" in label else dep_value
        lines.append(f"{label} & {arr_cell} & {dep_cell} \\\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: ARR means arrivals, DEP means departures, DID means difference-in-differences, and NAS means National Airspace System. Each row compares the event period with March 18--April 14, 2025, using airport and day-of-week fixed effects plus weather-delay minutes per scheduled operation. Bold values mark the post-May-20 subwindow with the clearest NAS-delay recovery.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(
    short_did: pd.DataFrame,
    placebos: pd.DataFrame,
    permutation: pd.DataFrame,
    event_time: pd.DataFrame,
    out_dir: Path,
) -> None:
    ewr_perm = permutation[permutation["treated_airport"] == "EWR"].copy()
    lines = [
        "# Identification checks",
        "",
        "## Short-window DID",
        "",
        short_did.to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Multiple pre-stress placebo windows",
        "",
        placebos.to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Airport-label permutation ranks for EWR",
        "",
        ewr_perm.to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Event-time DID",
        "",
        event_time.to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boot", type=int, default=499)
    parser.add_argument("--seed", type=int, default=20260518)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    daily = pd.read_csv(DAILY, parse_dates=["FlightDate"])
    boot = 49 if args.smoke else args.boot
    short_did = run_short_window_did(daily, boot=boot, seed=args.seed)
    placebos = run_multiple_placebos(daily)
    permutation = run_airport_permutation(daily)
    event_time = run_event_time(daily)
    if args.smoke:
        print("Short-window DID")
        print(short_did.to_string(index=False))
        print("\nPlacebos")
        print(placebos.to_string(index=False))
        print("\nPermutation EWR rows")
        print(permutation[permutation["treated_airport"] == "EWR"].to_string(index=False))
        print("\nEvent-time")
        print(event_time.to_string(index=False))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    short_did.to_csv(OUT / "short_window_did.csv", index=False)
    placebos.to_csv(OUT / "multiple_placebo_did.csv", index=False)
    permutation.to_csv(OUT / "airport_label_permutation.csv", index=False)
    event_time.to_csv(OUT / "event_time_did.csv", index=False)
    write_summary(short_did, placebos, permutation, event_time, OUT)
    if TABLES.exists():
        write_short_window_table(short_did, TABLES / "tab_short_did.tex")
        write_placebo_table(placebos, TABLES / "tab_multiple_placebos.tex")
        write_permutation_table(permutation, TABLES / "tab_airport_permutation.tex")
        write_event_time_table(event_time, TABLES / "tab_event_time_nas.tex")
    print("Short-window DID")
    print(short_did.to_string(index=False))
    print("\nPlacebos")
    print(placebos.to_string(index=False))
    print("\nPermutation EWR rows")
    print(permutation[permutation["treated_airport"] == "EWR"].to_string(index=False))
    print("\nEvent-time")
    print(event_time.to_string(index=False))


if __name__ == "__main__":
    main()


