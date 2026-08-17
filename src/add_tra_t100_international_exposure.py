from __future__ import annotations

import argparse
import zipfile
from calendar import monthrange
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parents[1]
RAW_DIR = BASE / "data" / "t100_international_segment"
EXTRACTED_DIR = RAW_DIR / "extracted"
OUT = BASE / "results" / "tra_t100_international_exposure"
OUT_SMOKE = BASE / "results" / "tra_t100_international_exposure_smoke"
TABLES = BASE / "article" / "elsarticle" / "tables"

COLS = [
    "year",
    "month",
    "origin",
    "origin_airport_id",
    "origin_wac",
    "origin_city_name",
    "dest",
    "dest_airport_id",
    "dest_wac",
    "dest_city_name",
    "carrier",
    "carrier_entity",
    "carrier_group_code",
    "distance",
    "service_class",
    "aircraft_group",
    "aircraft_type",
    "aircraft_config",
    "departures_performed",
    "departures_scheduled",
    "payload",
    "seats",
    "passengers",
    "freight",
    "mail",
    "ramp_to_ramp",
    "air_time",
    "carrier_wac",
]

NUMERIC_COLS = [
    "year",
    "month",
    "origin_airport_id",
    "origin_wac",
    "dest_airport_id",
    "dest_wac",
    "carrier_group_code",
    "distance",
    "aircraft_group",
    "aircraft_type",
    "aircraft_config",
    "departures_performed",
    "departures_scheduled",
    "payload",
    "seats",
    "passengers",
    "freight",
    "mail",
    "ramp_to_ramp",
    "air_time",
    "carrier_wac",
]


def extract_archives() -> list[Path]:
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    for archive in sorted(RAW_DIR.glob("*.zip")):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                target = EXTRACTED_DIR / info.filename
                if not target.exists() or target.stat().st_size != info.file_size:
                    zf.extract(info, EXTRACTED_DIR)
                extracted.append(target)
    if not extracted:
        raise FileNotFoundError(f"No T-100 International Segment zip files were found in {RAW_DIR}.")
    return extracted


def asc_path(year: int) -> Path:
    matches = sorted(EXTRACTED_DIR.glob(f"db28seg.fd.wac.{year}01.{year}12.asc"))
    if not matches:
        raise FileNotFoundError(f"No extracted DB28SEG file was found for {year}.")
    return matches[0]


def read_year(year: int, months: list[int] | None = None) -> pd.DataFrame:
    path = asc_path(year)
    df = pd.read_csv(
        path,
        sep="|",
        names=COLS + ["_trail"],
        usecols=COLS,
        dtype={
            "origin": "string",
            "origin_city_name": "string",
            "dest": "string",
            "dest_city_name": "string",
            "carrier": "string",
            "carrier_entity": "string",
            "service_class": "string",
        },
        low_memory=False,
    )
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if months is not None:
        df = df[df["month"].isin(months)].copy()
    return df


def build_ewr_records(years: list[int], months: list[int] | None, service_classes: tuple[str, ...]) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for year in years:
        df = read_year(year, months=months)
        ewr = df[(df["origin"].eq("EWR") | df["dest"].eq("EWR"))].copy()
        ewr = ewr[ewr["service_class"].isin(service_classes)].copy()
        ewr["side"] = np.where(ewr["origin"].eq("EWR"), "dep", "arr")
        ewr["counterpart"] = np.where(ewr["origin"].eq("EWR"), ewr["dest"], ewr["origin"])
        ewr["counterpart_city"] = np.where(
            ewr["origin"].eq("EWR"),
            ewr["dest_city_name"],
            ewr["origin_city_name"],
        )
        ewr["counterpart_wac"] = np.where(ewr["origin"].eq("EWR"), ewr["dest_wac"], ewr["origin_wac"])
        ewr = ewr[ewr["counterpart_wac"] > 100].copy()
        ewr = ewr[(ewr["departures_performed"] > 0) | (ewr["seats"] > 0) | (ewr["passengers"] > 0)].copy()
        pieces.append(ewr)
    if not pieces:
        return pd.DataFrame()
    records = pd.concat(pieces, ignore_index=True)
    records["carrier_group"] = np.where(records["carrier"].eq("UA"), "United", "Other carriers")
    return records.sort_values(["year", "month", "side", "counterpart", "carrier"]).reset_index(drop=True)


def summarize(records: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    route_carrier = (
        records.groupby(
            [
                "year",
                "month",
                "side",
                "counterpart",
                "counterpart_city",
                "counterpart_wac",
                "carrier",
                "carrier_group",
            ],
            as_index=False,
        )
        .agg(
            departures_performed=("departures_performed", "sum"),
            departures_scheduled=("departures_scheduled", "sum"),
            seats=("seats", "sum"),
            passengers=("passengers", "sum"),
            distance=("distance", "mean"),
        )
        .query("departures_performed > 0 or seats > 0 or passengers > 0")
    )
    monthly = (
        route_carrier.groupby(["year", "month", "side"], as_index=False)
        .agg(
            departures_performed=("departures_performed", "sum"),
            departures_scheduled=("departures_scheduled", "sum"),
            seats=("seats", "sum"),
            passengers=("passengers", "sum"),
            active_routes=("counterpart", "nunique"),
            active_carriers=("carrier", "nunique"),
        )
        .assign(
            days=lambda x: x.apply(lambda r: monthrange(int(r["year"]), int(r["month"]))[1], axis=1),
            departures_per_day=lambda x: x["departures_performed"] / x["days"],
            seats_per_day=lambda x: x["seats"] / x["days"],
            passengers_per_day=lambda x: x["passengers"] / x["days"],
            passengers_per_departure=lambda x: x["passengers"] / x["departures_performed"].replace(0, np.nan),
            load_factor=lambda x: x["passengers"] / x["seats"].replace(0, np.nan),
        )
    )
    carrier = (
        route_carrier.groupby(["year", "month", "side", "carrier_group"], as_index=False)
        .agg(
            departures_performed=("departures_performed", "sum"),
            seats=("seats", "sum"),
            passengers=("passengers", "sum"),
            active_routes=("counterpart", "nunique"),
        )
    )
    return route_carrier, monthly, carrier


def retention_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for (year, side), group in monthly.groupby(["year", "side"]):
        wide = group.set_index("month")
        if not {4, 6}.issubset(wide.index):
            continue
        apr = wide.loc[4]
        jun = wide.loc[6]
        rows.append(
            {
                "year": int(year),
                "side": side,
                "apr_departures_per_day": apr["departures_per_day"],
                "jun_departures_per_day": jun["departures_per_day"],
                "apr_seats_per_day": apr["seats_per_day"],
                "jun_seats_per_day": jun["seats_per_day"],
                "apr_passengers_per_day": apr["passengers_per_day"],
                "jun_passengers_per_day": jun["passengers_per_day"],
                "apr_routes": int(apr["active_routes"]),
                "jun_routes": int(jun["active_routes"]),
                "departure_retention_apr_to_jun": jun["departures_per_day"] / apr["departures_per_day"],
                "seat_retention_apr_to_jun": jun["seats_per_day"] / apr["seats_per_day"],
                "passenger_retention_apr_to_jun": jun["passengers_per_day"] / apr["passengers_per_day"],
                "route_retention_apr_to_jun": jun["active_routes"] / apr["active_routes"],
                "jun_passengers_per_departure": jun["passengers_per_departure"],
                "jun_load_factor": jun["load_factor"],
            }
        )
    summary = pd.DataFrame(rows)
    if summary.empty:
        return summary
    bench = summary[summary["year"].eq(2024)][
        ["side", "seat_retention_apr_to_jun", "passenger_retention_apr_to_jun", "route_retention_apr_to_jun"]
    ].rename(
        columns={
            "seat_retention_apr_to_jun": "same_month_2024_seat_retention",
            "passenger_retention_apr_to_jun": "same_month_2024_passenger_retention",
            "route_retention_apr_to_jun": "same_month_2024_route_retention",
        }
    )
    return summary.merge(bench, on="side", how="left")


def carrier_summary(carrier: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for (year, side, carrier_group), group in carrier.groupby(["year", "side", "carrier_group"]):
        wide = group.set_index("month")
        if not {4, 6}.issubset(wide.index):
            continue
        rows.append(
            {
                "year": int(year),
                "side": side,
                "carrier_group": carrier_group,
                "apr_departures": wide.loc[4, "departures_performed"],
                "jun_departures": wide.loc[6, "departures_performed"],
                "apr_seats": wide.loc[4, "seats"],
                "jun_seats": wide.loc[6, "seats"],
                "apr_passengers": wide.loc[4, "passengers"],
                "jun_passengers": wide.loc[6, "passengers"],
                "departure_change_apr_to_jun": wide.loc[6, "departures_performed"]
                - wide.loc[4, "departures_performed"],
                "seat_change_apr_to_jun": wide.loc[6, "seats"] - wide.loc[4, "seats"],
                "passenger_change_apr_to_jun": wide.loc[6, "passengers"] - wide.loc[4, "passengers"],
            }
        )
    return pd.DataFrame(rows)


def top_route_changes(route_carrier: pd.DataFrame) -> pd.DataFrame:
    route_month = (
        route_carrier[route_carrier["year"].eq(2025)]
        .groupby(["side", "counterpart", "counterpart_city", "month"], as_index=False)
        .agg(
            departures_performed=("departures_performed", "sum"),
            seats=("seats", "sum"),
            passengers=("passengers", "sum"),
        )
    )
    rows: list[dict[str, float | str]] = []
    for (side, counterpart), group in route_month.groupby(["side", "counterpart"]):
        wide = group.set_index("month")
        if not {4, 6}.issubset(wide.index):
            continue
        rows.append(
            {
                "side": side,
                "counterpart": counterpart,
                "counterpart_city": group["counterpart_city"].iloc[0],
                "apr_seats": wide.loc[4, "seats"],
                "jun_seats": wide.loc[6, "seats"],
                "seat_change_apr_to_jun": wide.loc[6, "seats"] - wide.loc[4, "seats"],
                "apr_passengers": wide.loc[4, "passengers"],
                "jun_passengers": wide.loc[6, "passengers"],
                "passenger_change_apr_to_jun": wide.loc[6, "passengers"] - wide.loc[4, "passengers"],
            }
        )
    changes = pd.DataFrame(rows)
    if changes.empty:
        return changes
    return changes.sort_values(["side", "passenger_change_apr_to_jun"], ascending=[True, True]).reset_index(drop=True)


def fmt_pct(value: float) -> str:
    if pd.isna(value):
        return "--"
    return f"{100 * value:.1f}\\%"


def fmt_num(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "--"
    return f"{value:.{digits}f}"


def write_table(summary: pd.DataFrame) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    current = summary[summary["year"].eq(2025)].copy()
    lines = [
        "\\begin{table}[!htbp]",
        "\\centering",
        "\\small",
        "\\caption{Monthly international passenger and seat exposure}",
        "\\label{tab:t100-international-exposure}",
        "\\begin{tabular}{@{}lrrrr@{}}",
        "\\toprule",
        "Side & Seat retention & Passenger retention & Route retention & 2024 seat retention \\\\",
        "\\midrule",
    ]
    for side in ["arr", "dep"]:
        row = current[current["side"].eq(side)]
        if row.empty:
            continue
        r = row.iloc[0]
        lines.append(
            f"{side.upper()} & "
            f"\\textbf{{{fmt_pct(r['seat_retention_apr_to_jun'])}}} & "
            f"\\textbf{{{fmt_pct(r['passenger_retention_apr_to_jun'])}}} & "
            f"\\textbf{{{fmt_pct(r['route_retention_apr_to_jun'])}}} & "
            f"{fmt_pct(r['same_month_2024_seat_retention'])} \\\\"
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{2mm}",
            "\\parbox{0.94\\linewidth}{\\small Notes: T-100 International Segment data are monthly. Retention compares April with June for EWR scheduled international passenger/cargo service. Bold values mark the international access indicators used in the policy interpretation.}",
            "\\end{table}",
        ]
    )
    (TABLES / "tab_t100_international_exposure.tex").write_text("\n".join(lines), encoding="utf-8")


def write_summary(out_dir: Path, summary: pd.DataFrame, carrier: pd.DataFrame, changes: pd.DataFrame) -> None:
    lines = [
        "# T-100 International Segment exposure experiment",
        "",
        "Scope: EWR records in BTS DB28SEG T-100 International Segment. Main sample keeps service class F and non-U.S. counterpart WAC codes.",
        "",
        "## April-to-June retention",
        "",
        summary.to_markdown(index=False),
        "",
        "## Carrier-group changes",
        "",
        carrier.to_markdown(index=False),
        "",
        "## Largest 2025 route passenger changes",
        "",
        changes.groupby("side").head(10).to_markdown(index=False) if not changes.empty else "No route-change rows.",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def run(smoke: bool) -> None:
    extract_archives()
    out_dir = OUT_SMOKE if smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    years = [2025] if smoke else [2024, 2025]
    months = [4, 5, 6] if smoke else list(range(1, 13))
    records = build_ewr_records(years=years, months=months, service_classes=("F",))
    if records.empty:
        raise RuntimeError("No EWR international scheduled passenger/cargo records were found.")
    route_carrier, monthly, carrier = summarize(records)
    summary = retention_summary(monthly)
    carrier_policy = carrier_summary(carrier)
    changes = top_route_changes(route_carrier)

    records.to_csv(out_dir / "t100_international_ewr_records.csv", index=False)
    route_carrier.to_csv(out_dir / "t100_international_ewr_route_carrier_month.csv", index=False)
    monthly.to_csv(out_dir / "t100_international_ewr_monthly_exposure.csv", index=False)
    carrier.to_csv(out_dir / "t100_international_ewr_carrier_monthly.csv", index=False)
    summary.to_csv(out_dir / "t100_international_policy_summary.csv", index=False)
    carrier_policy.to_csv(out_dir / "t100_international_carrier_policy_summary.csv", index=False)
    changes.to_csv(out_dir / "t100_international_route_changes_2025.csv", index=False)
    write_summary(out_dir, summary, carrier_policy, changes)
    if not smoke:
        write_table(summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Run only the 2025 April-June EWR check.")
    args = parser.parse_args()
    run(smoke=args.smoke)


if __name__ == "__main__":
    main()
