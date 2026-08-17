from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
DAILY = BASE / "results" / "ewr_2025_full" / "airport_side_daily.csv"
HOURLY_SUMMARY = BASE / "results" / "hourly_schedule_pressure" / "hourly_schedule_pressure_summary.csv"
DATA_OUT = BASE / "data" / "opsnet"
OUT = BASE / "results" / "public_data_validation_checks"

OPSN_ADDR = "https://www.aspm.faa.gov/opsnet/sys/opsnet-server-x.asp"

WINDOWS = [
    ("stress", "2025-04-15", "2025-05-19"),
    ("interim_early", "2025-05-20", "2025-06-02"),
    ("interim_late", "2025-06-03", "2025-06-15"),
    ("interim_full", "2025-05-20", "2025-06-15"),
]

PERIOD_LABELS = {
    "stress_20250415_0519": "Stress",
    "interim_20250520_0615": "Interim order",
    "cap_20250616_1025": "Operating limit",
}

SIDE_LABELS = {"arr": "Arrivals", "dep": "Departures"}


def pct(value: float) -> str:
    return f"{value * 100:.1f}\\%"


def pp(value: float) -> str:
    return f"{value * 100:.1f} pp"


def numeric(value: str) -> int:
    return int(value.replace(",", "").strip())


def atads_query(start_yyyymm: int, end_yyyymm: int, locid: str = "EWR") -> str:
    select_fields = (
        "YYYYMM,"
        "SUM(IFR_ITIN_AC) AS IFR_ITIN_AC,"
        "SUM(IFR_ITIN_AT) AS IFR_ITIN_AT,"
        "SUM(IFR_ITIN_GA) AS IFR_ITIN_GA,"
        "SUM(IFR_ITIN_MI) AS IFR_ITIN_MI,"
        "SUM(IFR_ITIN_AC+IFR_ITIN_AT+IFR_ITIN_GA+IFR_ITIN_MI) AS TOT_ITII,"
        "SUM(VFR_ITIN_AC) AS VFR_ITIN_AC,"
        "SUM(VFR_ITIN_AT) AS VFR_ITIN_AT,"
        "SUM(VFR_ITIN_GA) AS VFR_ITIN_GA,"
        "SUM(VFR_ITIN_MI) AS VFR_ITIN_MI,"
        "SUM(VFR_ITIN_AC+VFR_ITIN_AT+VFR_ITIN_GA+VFR_ITIN_MI) AS TOT_ITIV,"
        "SUM(AC) AS AC,"
        "SUM(ATAXI) AS ATAXI,"
        "SUM(IFR_ITIN_GA+VFR_ITIN_GA) AS GA,"
        "SUM(IFR_ITIN_MI+VFR_ITIN_MI) AS MIL,"
        "SUM(AC+ATAXI+IFR_ITIN_GA+VFR_ITIN_GA+IFR_ITIN_MI+VFR_ITIN_MI) AS TOT_ITI,"
        "SUM(LOCAL_GA) AS LOCAL_GA,"
        "SUM(LOCAL_MIL) AS LOCAL_MIL,"
        "SUM(LOCAL_GA+LOCAL_MIL) AS TOT_LOC,"
        "SUM(TOTAL) AS TOTAL"
    )
    return (
        f"SELECT {select_fields} FROM TOWER_DAY "
        f"WHERE YYYYMM>={start_yyyymm} AND YYYYMM<={end_yyyymm} "
        f"AND LOCID IN ('{locid}') GROUP BY YYYYMM ORDER BY YYYYMM"
    )


def fetch_atads_monthly(start_yyyymm: int, end_yyyymm: int, locid: str = "EWR") -> str:
    line = atads_query(start_yyyymm, end_yyyymm, locid)
    body = {
        "dstyle": "m",
        "dfld": "yyyymm",
        "dlist": "",
        "fromdate": str(start_yyyymm),
        "todate": str(end_yyyymm),
        "llist": f"'{locid}'",
        "keylist": "YYYYMM",
        "compdstyle": "",
        "compdfld": "",
        "compdlist": "",
        "compfromdate": "",
        "comptodate": "",
        "line": line,
        "cmd": "air_bas",
        "nopage": "y",
        "nost": "y",
        "defs": "",
        "avgdays": "1",
        "addifr": "",
        "addvfr": "",
        "additi": "y",
        "addloc": "y",
        "oktosave": "y",
        "reportformat": "asp",
    }
    encoded = urlencode(body).encode("utf-8")
    req = Request(
        OPSN_ADDR,
        data=encoded,
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(req, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_atads_monthly(html: str) -> pd.DataFrame:
    pattern = re.compile(
        r"<td[^>]*>(\d{2})/2025</td>\s*"
        r"<td[^>]*>([\d,]+)</td>\s*"
        r"<td[^>]*>([\d,]+)</td>\s*"
        r"<td[^>]*>([\d,]+)</td>\s*"
        r"<td[^>]*>([\d,]+)</td>\s*"
        r"<td[^>]*>([\d,]+)</td>\s*"
        r"<td[^>]*>([\d,]+)</td>\s*"
        r"<td[^>]*>([\d,]+)</td>\s*"
        r"<td[^>]*>([\d,]+)</td>\s*"
        r"<td[^>]*>([\d,]+)</td>",
        flags=re.IGNORECASE,
    )
    rows = []
    for match in pattern.finditer(html):
        month = int(match.group(1))
        rows.append(
            {
                "month": month,
                "year_month": f"2025-{month:02d}",
                "opsnet_air_carrier": numeric(match.group(2)),
                "opsnet_air_taxi": numeric(match.group(3)),
                "opsnet_ga": numeric(match.group(4)),
                "opsnet_military": numeric(match.group(5)),
                "opsnet_itinerant_total": numeric(match.group(6)),
                "opsnet_local_civil": numeric(match.group(7)),
                "opsnet_local_military": numeric(match.group(8)),
                "opsnet_local_total": numeric(match.group(9)),
                "opsnet_total_operations": numeric(match.group(10)),
            }
        )
    if not rows:
        raise RuntimeError("No ATADS rows parsed from the OPSNET HTML response.")
    return pd.DataFrame(rows)


def bts_monthly_totals(daily: pd.DataFrame, months: list[int]) -> pd.DataFrame:
    ewr = daily[daily["airport"] == "EWR"].copy()
    ewr["FlightDate"] = pd.to_datetime(ewr["FlightDate"])
    ewr["month"] = ewr["FlightDate"].dt.month
    ewr = ewr[ewr["month"].isin(months)]
    out = (
        ewr.groupby("month", as_index=False)
        .agg(
            bts_domestic_scheduled_ops=("scheduled_ops", "sum"),
            bts_domestic_operated_ops=("operated_ops", "sum"),
            bts_cancelled_ops=("cancelled_ops", "sum"),
        )
        .sort_values("month")
    )
    out["year_month"] = out["month"].map(lambda month: f"2025-{month:02d}")
    return out


def build_short_window_summary(daily: pd.DataFrame) -> pd.DataFrame:
    ewr = daily[daily["airport"] == "EWR"].copy()
    ewr["FlightDate"] = pd.to_datetime(ewr["FlightDate"])
    rows = []
    for label, start, end in WINDOWS:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        window = ewr[(ewr["FlightDate"] >= start_ts) & (ewr["FlightDate"] <= end_ts)]
        for side in ["arr", "dep"]:
            sub = window[window["side"] == side]
            rows.append(
                {
                    "window": label,
                    "start": start,
                    "end": end,
                    "days": int(sub["FlightDate"].nunique()),
                    "side": side,
                    "ops_per_day": sub["scheduled_ops"].mean(),
                    "cancel_rate": sub["cancel_rate"].mean(),
                    "delay15_rate": sub["delay15_rate"].mean(),
                    "nas_delay_per_scheduled_op": sub["nas_delay_per_scheduled_op"].mean(),
                    "weather_delay_per_scheduled_op": sub["weather_delay_per_scheduled_op"].mean(),
                }
            )
    return pd.DataFrame(rows)


def build_short_window_contrast(summary: pd.DataFrame) -> pd.DataFrame:
    stress = summary[summary["window"] == "stress"].set_index("side")
    rows = []
    for window in ["interim_early", "interim_late", "interim_full"]:
        current = summary[summary["window"] == window].set_index("side")
        for side in ["arr", "dep"]:
            row = {"window": window, "side": side}
            for metric in ["ops_per_day", "cancel_rate", "delay15_rate", "nas_delay_per_scheduled_op"]:
                row[f"{metric}_change_vs_stress"] = current.loc[side, metric] - stress.loc[side, metric]
            rows.append(row)
    return pd.DataFrame(rows)


def build_hourly_tail_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "period": PERIOD_LABELS[row["period"]],
                "side": SIDE_LABELS[row["side"]],
                "hours": int(row["hours"]),
                "mean": row["avg_ops_per_hour"],
                "p90": row["p90_ops_per_hour"],
                "p95": row["p95_ops_per_hour"],
                "max": int(row["max_ops_per_hour"]),
                "above_28": row["share_above_28"],
                "above_34": row["share_above_34"],
            }
        )
    return pd.DataFrame(rows)


def write_latex_tables(short_summary: pd.DataFrame, short_contrast: pd.DataFrame, hourly_tail: pd.DataFrame, validation: pd.DataFrame) -> None:
    table_dir = BASE / "results" / "tables"
    if not table_dir.exists():
        return

    short_lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Short-window EWR reliability around the interim order}",
        r"\label{tab:short-window}",
        r"\begin{tabular}{@{}llrrrr@{}}",
        r"\toprule",
        r"Window & Side & Ops/day & Cancellation & Delay-15+ & NAS min/op \\",
        r"\midrule",
    ]
    labels = {
        "stress": "Stress",
        "interim_early": "May 20--Jun 2",
        "interim_late": "Jun 3--Jun 15",
        "interim_full": "Interim full",
    }
    for _, row in short_summary.iterrows():
        bold = row["window"] in {"interim_early", "interim_late"}
        vals = [
            f"{row['ops_per_day']:.1f}",
            pct(row["cancel_rate"]),
            pct(row["delay15_rate"]),
            f"{row['nas_delay_per_scheduled_op']:.1f}",
        ]
        if bold:
            vals = [rf"\textbf{{{value}}}" for value in vals]
        short_lines.append(
            f"{labels[row['window']]} & {SIDE_LABELS[row['side']]} & "
            + " & ".join(vals)
            + r" \\"
        )
    short_lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\vspace{2mm}",
        r"\parbox{0.94\linewidth}{\footnotesize Notes: NAS means National Airspace System. Lower cancellation, delay-15-plus, and NAS minutes per scheduled operation indicate better reliability. Bold values mark the two post-May-20 subwindows.}",
        r"\end{table}",
        "",
    ]
    (table_dir / "tab_short_window.tex").write_text("\n".join(short_lines), encoding="utf-8")

    tail_lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Hourly schedule-pressure upper-tail summary}",
        r"\label{tab:hourly-tail}",
        r"\begin{tabular}{@{}llrrrrrr@{}}",
        r"\toprule",
        r"Period & Side & Mean & P90 & P95 & Max & $>$28 & $>$34 \\",
        r"\midrule",
    ]
    for _, row in hourly_tail.iterrows():
        emphasis = row["side"] == "Departures" and row["period"] in {"Stress", "Interim order"}
        vals = [
            f"{row['mean']:.1f}",
            f"{row['p90']:.1f}",
            f"{row['p95']:.1f}",
            f"{row['max']:.0f}",
            pct(row["above_28"]),
            pct(row["above_34"]),
        ]
        if emphasis:
            vals = [rf"\textbf{{{value}}}" for value in vals]
        tail_lines.append(f"{row['period']} & {row['side']} & " + " & ".join(vals) + r" \\")
    tail_lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\vspace{2mm}",
        r"\parbox{0.94\linewidth}{\footnotesize Notes: Hourly counts use public BTS scheduled times for EWR domestic reported flights from 06:00 through 22:59. P90 and P95 are hourly upper-tail values. The final two columns report the share of hours above 28 and 34 scheduled operations. Bold values highlight the departure-side reduction after the interim order.}",
        r"\end{table}",
        "",
    ]
    (table_dir / "tab_hourly_tail.tex").write_text("\n".join(tail_lines), encoding="utf-8")

    valid_lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{Monthly total-operation validation against the BTS domestic sample}",
        r"\label{tab:opsnet-validation}",
        r"\begin{tabular}{@{}lrrr@{}}",
        r"\toprule",
        r"Month & FAA total ops & BTS sched. ops & BTS share \\",
        r"\midrule",
    ]
    for _, row in validation.iterrows():
        bold = row["month"] in {4, 5, 6}
        vals = [
            f"{int(row['opsnet_total_operations']):,}",
            f"{int(row['bts_domestic_scheduled_ops']):,}",
            pct(row["bts_to_opsnet_ratio"]),
        ]
        if bold:
            vals = [rf"\textbf{{{value}}}" for value in vals]
        valid_lines.append(f"{row['year_month']} & " + " & ".join(vals) + r" \\")
    valid_lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\vspace{2mm}",
        r"\parbox{0.94\linewidth}{\footnotesize Notes: FAA total operations come from ATADS/OPSNET and include all reported airport operations. BTS scheduled operations are the domestic scheduled arrival and departure records used in the manuscript. The share is a coverage indicator for the public BTS sample. Monthly validation assesses coverage stability, while the main inference uses BTS flight-level reliability outcomes. Bold values mark the main construction and interim-order months.}",
        r"\end{table}",
        "",
    ]
    (table_dir / "tab_opsnet_validation.tex").write_text("\n".join(valid_lines), encoding="utf-8")

    contrast_lines = ["# Short-window changes versus stress", ""]
    contrast_lines.append(short_contrast.to_markdown(index=False, floatfmt=".3f"))
    (OUT / "short_window_contrasts.md").write_text("\n".join(contrast_lines), encoding="utf-8")


def build_outputs(months: list[int], fetch_opsnet: bool) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    daily = pd.read_csv(DAILY, parse_dates=["FlightDate"])
    hourly_summary = pd.read_csv(HOURLY_SUMMARY)

    short_summary = build_short_window_summary(daily)
    short_contrast = build_short_window_contrast(short_summary)
    hourly_tail = build_hourly_tail_table(hourly_summary)

    if fetch_opsnet:
        html = fetch_atads_monthly(202500 + min(months), 202500 + max(months))
        html_path = DATA_OUT / f"atads_opsnet_ewr_2025_{min(months):02d}_{max(months):02d}.html"
        html_path.write_text(html, encoding="utf-8")
    else:
        html_path = DATA_OUT / f"atads_opsnet_ewr_2025_{min(months):02d}_{max(months):02d}.html"
        if not html_path.exists():
            html_path = DATA_OUT / "atads_opsnet_ewr_2025_01_12.html"
        html = html_path.read_text(encoding="utf-8")
    opsnet = parse_atads_monthly(html)
    opsnet = opsnet[opsnet["month"].isin(months)].copy()
    bts = bts_monthly_totals(daily, months)
    validation = opsnet.merge(bts, on=["month", "year_month"], how="left")
    validation["bts_to_opsnet_ratio"] = validation["bts_domestic_scheduled_ops"] / validation["opsnet_total_operations"]

    short_summary.to_csv(OUT / "short_window_summary.csv", index=False)
    short_contrast.to_csv(OUT / "short_window_contrasts.csv", index=False)
    hourly_tail.to_csv(OUT / "hourly_upper_tail_summary.csv", index=False)
    validation.to_csv(OUT / "opsnet_bts_monthly_validation.csv", index=False)
    if min(months) == 1 and max(months) == 12:
        validation.to_csv(DATA_OUT / "atads_opsnet_ewr_2025_monthly_validation.csv", index=False)

    write_latex_tables(short_summary, short_contrast, hourly_tail, validation)

    payload = {
        "months": months,
        "opsnet_source": str(html_path.relative_to(BASE)),
        "outputs": [
            "results/public_data_validation_checks/short_window_summary.csv",
            "results/public_data_validation_checks/hourly_upper_tail_summary.csv",
            "results/public_data_validation_checks/opsnet_bts_monthly_validation.csv",
        ],
        "coverage_ratio_mean": float(validation["bts_to_opsnet_ratio"].mean()),
        "coverage_ratio_min": float(validation["bts_to_opsnet_ratio"].min()),
        "coverage_ratio_max": float(validation["bts_to_opsnet_ratio"].max()),
    }
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", nargs="+", type=int, default=list(range(1, 13)))
    parser.add_argument("--fetch-opsnet", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    months = sorted(set(args.months))
    if any(month < 1 or month > 12 for month in months):
        raise ValueError(f"Invalid months: {months}")
    build_outputs(months, args.fetch_opsnet)


if __name__ == "__main__":
    main()

