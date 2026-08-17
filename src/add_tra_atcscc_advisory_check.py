from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "atcscc_advisories"
OUT = BASE / "results" / "tra_atcscc_advisories"
OUT_SMOKE = BASE / "results" / "tra_atcscc_advisories_smoke"
TABLES = BASE / "article" / "elsarticle" / "tables"

AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL", "IAD", "DCA", "BWI", "ATL", "ORD"]
PHASES = {
    "reference": ("2025-03-18", "2025-04-14", "Reference"),
    "stress": ("2025-04-15", "2025-05-19", "Stress"),
    "early_interim": ("2025-05-20", "2025-06-02", "May 20--Jun 2"),
    "late_interim": ("2025-06-03", "2025-06-15", "Jun 3--Jun 15"),
}


def date_range(smoke: bool) -> list[pd.Timestamp]:
    if smoke:
        return list(pd.date_range("2025-04-26", "2025-04-28"))
    return list(pd.date_range("2025-03-18", "2025-06-15"))


def advisory_url(date: pd.Timestamp) -> str:
    day = date.strftime("%Y-%m-%d")
    return (
        "https://www.fly.faa.gov/adv/adv_list?"
        "_airflow=on&_ctop=on&_gDelay=on&_gStop=on&_other=on&_route=on"
        f"&advisoryCategory=All&airflow=true&ctop=true&date={day}"
        "&gDelay=true&gStop=true&other=true&route=true&whichAdvisories=ATCSCC"
    )


def fetch_html(date: pd.Timestamp, force: bool) -> Path | None:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / f"atcscc_{date:%Y-%m-%d}.html"
    if path.exists() and not force:
        return path
    try:
        html = pd.read_html(advisory_url(date))
    except Exception as exc:
        print(f"ATCSCC fetch failed for {date:%Y-%m-%d}: {exc}")
        return None
    # Store the parsed advisory table as HTML-compatible CSV cache to avoid repeated page parsing.
    table = select_advisory_table(html)
    if table.empty:
        path.write_text("", encoding="utf-8")
    else:
        table.to_csv(path, index=False)
    time.sleep(0.15)
    return path


def select_advisory_table(tables: list[pd.DataFrame]) -> pd.DataFrame:
    for table in tables:
        flat_columns = [" ".join(str(part) for part in col if str(part) != "nan") if isinstance(col, tuple) else str(col) for col in table.columns]
        lower = [col.lower() for col in flat_columns]
        if any("control element" in col for col in lower) and any("brief title" in col for col in lower):
            out = table.copy()
            out.columns = flat_columns
            out = out.rename(
                columns={
                    next(col for col in out.columns if "CONTROL ELEMENT" in col.upper()): "control_element",
                    next(col for col in out.columns if "BRIEF TITLE" in col.upper()): "brief_title",
                    next(col for col in out.columns if "SEND TIME" in col.upper()): "send_time",
                    next(col for col in out.columns if col.upper().endswith("DATE") or " DATE" in col.upper()): "date",
                    next(col for col in out.columns if "NUMBER" in col.upper()): "number",
                }
            )
            return out[["number", "control_element", "date", "brief_title", "send_time"]].copy()
    return pd.DataFrame(columns=["number", "control_element", "date", "brief_title", "send_time"])


def read_cached(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=["number", "control_element", "date", "brief_title", "send_time"])
    return pd.read_csv(path)


def phase_label(date: pd.Timestamp) -> str | None:
    for key, (start, end, _label) in PHASES.items():
        if pd.Timestamp(start) <= date <= pd.Timestamp(end):
            return key
    return None


def parse_daily(date: pd.Timestamp, table: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if table.empty:
        for airport in AIRPORTS:
            rows.append({"FlightDate": date, "airport": airport, "advisory_count": 0})
        return pd.DataFrame(rows)
    table = table.copy()
    table["control_element"] = table["control_element"].fillna("").astype(str).str.upper()
    table["brief_title"] = table["brief_title"].fillna("").astype(str).str.upper()
    for airport in AIRPORTS:
        airport_rows = table[table["control_element"].str.contains(airport, regex=False)].copy()
        title = airport_rows["brief_title"]
        cancel = title.str.contains("CNX|CANCELLATION|CANCEL", regex=True)
        proposed = title.str.contains("PROPOSED", regex=False)
        gdp = title.str.contains("GROUND DELAY PROGRAM", regex=False) & ~cancel & ~proposed
        gs = (title.str.contains("GROUND STOP", regex=False) | title.str.contains("CDM GS", regex=False)) & ~cancel
        rows.append(
            {
                "FlightDate": date,
                "airport": airport,
                "advisory_count": int(len(airport_rows)),
                "gdp_count": int(gdp.sum()),
                "ground_stop_count": int(gs.sum()),
                "arrival_delay_count": int(title.str.contains("ARRIVAL DELAYS", regex=False).sum()),
                "departure_delay_count": int(title.str.contains("DEPARTURE DELAYS", regex=False).sum()),
                "diversion_recovery_count": int(title.str.contains("DIVERSION RECOVERY", regex=False).sum()),
                "has_gdp": int(gdp.any()),
                "has_ground_stop": int(gs.any()),
                "has_arrival_delay": int(title.str.contains("ARRIVAL DELAYS", regex=False).any()),
                "has_departure_delay": int(title.str.contains("DEPARTURE DELAYS", regex=False).any()),
            }
        )
    return pd.DataFrame(rows)


def build_panel(dates: list[pd.Timestamp], force: bool) -> pd.DataFrame:
    frames = []
    for date in dates:
        path = fetch_html(date, force=force)
        table = read_cached(path) if path is not None else pd.DataFrame()
        frames.append(parse_daily(date, table))
    panel = pd.concat(frames, ignore_index=True)
    panel["period"] = panel["FlightDate"].map(phase_label)
    return panel


def summarize(panel: pd.DataFrame) -> pd.DataFrame:
    out = (
        panel.groupby(["airport", "period"], as_index=False)
        .agg(
            days=("FlightDate", "nunique"),
            advisory_days=("advisory_count", lambda x: int((x > 0).sum())),
            gdp_days=("has_gdp", "sum"),
            ground_stop_days=("has_ground_stop", "sum"),
            arrival_delay_days=("has_arrival_delay", "sum"),
            departure_delay_days=("has_departure_delay", "sum"),
            advisories=("advisory_count", "sum"),
            gdp_advisories=("gdp_count", "sum"),
            ground_stop_advisories=("ground_stop_count", "sum"),
        )
    )
    for col in ["advisory_days", "gdp_days", "ground_stop_days", "arrival_delay_days", "departure_delay_days"]:
        out[f"{col}_share"] = out[col] / out["days"]
    return out.sort_values(["airport", "period"]).reset_index(drop=True)


def write_latex_table(summary: pd.DataFrame, table_path: Path) -> None:
    ewr = summary[summary["airport"] == "EWR"].copy()
    phase_labels = {key: label for key, (_start, _end, label) in PHASES.items()}
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{ATCSCC advisory diagnostics for EWR}",
        r"\label{tab:atcscc-advisory-check}",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Phase & Advisory days & GDP days & Ground-stop days & Airport-delay days \\",
        r"\midrule",
    ]
    for phase in ["reference", "stress", "early_interim", "late_interim"]:
        row = ewr[ewr["period"] == phase].iloc[0]
        delay_days = int(max(row["arrival_delay_days"], row["departure_delay_days"]))
        lines.append(
            f"{phase_labels[phase]} & {int(row['advisory_days'])}/{int(row['days'])} & "
            f"{int(row['gdp_days'])} & {int(row['ground_stop_days'])} & {delay_days} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: ATCSCC means Air Traffic Control System Command Center and GDP means Ground Delay Program. Airport-delay days count days with at least one EWR arrival-delay or departure-delay advisory. The table is used as an operational-pressure diagnostic.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(panel: pd.DataFrame, summary: pd.DataFrame, out_dir: Path) -> None:
    ewr = summary[summary["airport"] == "EWR"].copy()
    lines = [
        "# TRA ATCSCC advisory check",
        "",
        "## EWR period summary",
        "",
        ewr.to_markdown(index=False, floatfmt=".3f"),
        "",
        "## Full airport summary",
        "",
        summary.to_markdown(index=False, floatfmt=".3f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = OUT_SMOKE if args.smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    panel = build_panel(date_range(args.smoke), force=args.force)
    summary = summarize(panel)
    panel.to_csv(out_dir / "atcscc_airport_day_advisories.csv", index=False)
    summary.to_csv(out_dir / "atcscc_period_summary.csv", index=False)
    write_summary(panel, summary, out_dir)
    if not args.smoke and TABLES.exists():
        write_latex_table(summary, TABLES / "tab_atcscc_advisory_check.tex")
    print("EWR advisory summary")
    print(summary[summary["airport"] == "EWR"].to_string(index=False))


if __name__ == "__main__":
    main()
