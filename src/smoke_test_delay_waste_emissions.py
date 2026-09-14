"""Smoke-test delay-waste fuel and CO2 for EWR 28/28 vs 34/34 vs 36/36.

Boundary: extra engine-on time from NAS-attributed delay and extra taxi, not
full-flight LCA. Public idle/taxi fuel flow from ICAO Doc 9889 / EEDB and
CO2 factor 3.16 kg/kg. Keep results only if regime contrasts are usable.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw_bts_2025"
DAILY = BASE / "results" / "ewr_2025_full" / "airport_side_daily.csv"
OUT = BASE / "results" / "delay_waste_emissions_smoke"
OUT.mkdir(parents=True, exist_ok=True)

AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL", "IAD", "DCA", "BWI", "ATL", "ORD"]
CONTROL = [a for a in AIRPORTS if a != "EWR"]

# ICAO Doc 9889 / EEDB idle (7% thrust), two-engine fleet mix at a U.S. hub.
# CFM56-7B26 ~0.118 kg/s/engine * 2 = 14.16 kg/min; CF34-8E ~12.5 kg/min.
# Primary 12.5 kg/min is a mixed RJ/NB idle flow. Bounds cover SET and WB.
FUEL_KG_PER_MIN = {"low": 8.0, "primary": 12.5, "high": 16.0}
CO2_KG_PER_KG_FUEL = 3.16  # ICAO / IPCC jet-A

PERIOD_ORDER = [
    "stress_20250415_0519",
    "interim_20250520_0615",
    "cap_20250616_1025",
    "extension_20251026_1231",
]
PERIOD_LABEL = {
    "stress_20250415_0519": "stress (no formal target)",
    "interim_20250520_0615": "28/28 construction",
    "cap_20250616_1025": "34/34 operating",
    "extension_20251026_1231": "36/36 extension",
}
REGIME_KEY = {
    "stress_20250415_0519": "stress",
    "interim_20250520_0615": "28/28",
    "cap_20250616_1025": "34/34",
    "extension_20251026_1231": "36/36",
}

USECOLS = [
    "FlightDate",
    "Origin",
    "Dest",
    "Cancelled",
    "TaxiOut",
    "TaxiIn",
    "NASDelay",
    "ArrDelayMinutes",
    "DepDelayMinutes",
    "ArrDel15",
    "DepDel15",
]


def period_label(date: pd.Timestamp) -> str:
    if date <= pd.Timestamp("2025-04-14"):
        return "pre_20250101_0414"
    if date <= pd.Timestamp("2025-05-19"):
        return "stress_20250415_0519"
    if date <= pd.Timestamp("2025-06-15"):
        return "interim_20250520_0615"
    if date <= pd.Timestamp("2025-10-25"):
        return "cap_20250616_1025"
    return "extension_20251026_1231"


def fuel_co2(minutes: float, factor: str = "primary") -> tuple[float, float]:
    fuel = float(minutes) * FUEL_KG_PER_MIN[factor]
    return fuel, fuel * CO2_KG_PER_KG_FUEL


def summarize_nas_from_daily() -> pd.DataFrame:
    daily = pd.read_csv(DAILY, parse_dates=["FlightDate"])
    daily = daily[daily["airport"].isin(AIRPORTS)].copy()
    daily["period"] = daily["FlightDate"].map(period_label)
    g = (
        daily.groupby(["airport", "side", "period"], as_index=False)
        .agg(
            days=("FlightDate", "nunique"),
            scheduled_ops=("scheduled_ops", "sum"),
            nas_delay_minutes=("nas_delay_minutes", "sum"),
        )
    )
    g["ops_per_day"] = g["scheduled_ops"] / g["days"]
    g["nas_min_per_day"] = g["nas_delay_minutes"] / g["days"]
    g["nas_min_per_op"] = g["nas_delay_minutes"] / g["scheduled_ops"]
    return g


def did_nas(nas: pd.DataFrame, pre: str, post: str) -> dict:
    rows = []
    for side in ["arr", "dep"]:
        ewr_pre = nas[(nas.airport == "EWR") & (nas.side == side) & (nas.period == pre)]
        ewr_post = nas[(nas.airport == "EWR") & (nas.side == side) & (nas.period == post)]
        ctrl_pre = nas[(nas.airport.isin(CONTROL)) & (nas.side == side) & (nas.period == pre)]
        ctrl_post = nas[(nas.airport.isin(CONTROL)) & (nas.side == side) & (nas.period == post)]
        ewr_delta_minop = float(ewr_post["nas_min_per_op"].iloc[0] - ewr_pre["nas_min_per_op"].iloc[0])
        ctrl_delta_minop = float(ctrl_post["nas_min_per_op"].mean() - ctrl_pre["nas_min_per_op"].mean())
        did_minop = ewr_delta_minop - ctrl_delta_minop
        ewr_ops_pre = float(ewr_pre["ops_per_day"].iloc[0])
        ewr_delta_minday = float(ewr_post["nas_min_per_day"].iloc[0] - ewr_pre["nas_min_per_day"].iloc[0])
        ctrl_delta_minday = float(ctrl_post["nas_min_per_day"].mean() - ctrl_pre["nas_min_per_day"].mean())
        did_minday_ops = did_minop * ewr_ops_pre
        rows.append(
            {
                "side": side,
                "ewr_delta_min_per_op": ewr_delta_minop,
                "control_delta_min_per_op": ctrl_delta_minop,
                "did_min_per_op": did_minop,
                "ewr_delta_min_per_day": ewr_delta_minday,
                "control_delta_min_per_day": ctrl_delta_minday,
                "did_min_per_day_using_stress_ops": did_minday_ops,
            }
        )
    return rows


def read_month(month: int) -> pd.DataFrame:
    zip_path = RAW / f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_{month}.zip"
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        with zf.open(csv_names[0]) as fh:
            df = pd.read_csv(fh, usecols=USECOLS, low_memory=False)
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    return df


def airport_side_taxi(df: pd.DataFrame) -> pd.DataFrame:
    dep = df[df["Origin"].isin(AIRPORTS)].copy()
    dep["airport"] = dep["Origin"]
    dep["side"] = "dep"
    dep["taxi_min"] = pd.to_numeric(dep["TaxiOut"], errors="coerce")
    dep["delay15"] = pd.to_numeric(dep["DepDel15"], errors="coerce")
    arr = df[df["Dest"].isin(AIRPORTS)].copy()
    arr["airport"] = arr["Dest"]
    arr["side"] = "arr"
    arr["taxi_min"] = pd.to_numeric(arr["TaxiIn"], errors="coerce")
    arr["delay15"] = pd.to_numeric(arr["ArrDel15"], errors="coerce")
    cols = ["FlightDate", "airport", "side", "Cancelled", "taxi_min", "NASDelay", "delay15"]
    out = pd.concat([dep[cols], arr[cols]], ignore_index=True)
    out["Cancelled"] = pd.to_numeric(out["Cancelled"], errors="coerce").fillna(0)
    out["NASDelay"] = pd.to_numeric(out["NASDelay"], errors="coerce").fillna(0)
    return out


def unimpeded_taxi(panel: pd.DataFrame) -> pd.DataFrame:
    """Airport-side unimpeded taxi: 10th percentile among operated on-time flights."""
    ok = panel[(panel["Cancelled"] == 0) & (panel["delay15"].fillna(0) == 0) & panel["taxi_min"].notna()]
    u = ok.groupby(["airport", "side"])["taxi_min"].quantile(0.10).rename("unimpeded_taxi")
    return u.reset_index()


def summarize_taxi(panel: pd.DataFrame, unimp: pd.DataFrame) -> pd.DataFrame:
    panel = panel.merge(unimp, on=["airport", "side"], how="left")
    op = panel[panel["Cancelled"] == 0].copy()
    op["extra_taxi"] = (op["taxi_min"] - op["unimpeded_taxi"]).clip(lower=0)
    op["period"] = op["FlightDate"].map(period_label)
    g = (
        op.groupby(["airport", "side", "period"], as_index=False)
        .agg(
            days=("FlightDate", "nunique"),
            operated_ops=("taxi_min", "size"),
            taxi_min_sum=("taxi_min", "sum"),
            extra_taxi_sum=("extra_taxi", "sum"),
            nas_delay_minutes=("NASDelay", "sum"),
        )
    )
    g["taxi_min_per_day"] = g["taxi_min_sum"] / g["days"]
    g["extra_taxi_per_day"] = g["extra_taxi_sum"] / g["days"]
    g["taxi_min_per_op"] = g["taxi_min_sum"] / g["operated_ops"]
    g["extra_taxi_per_op"] = g["extra_taxi_sum"] / g["operated_ops"]
    return g


def regime_table(nas: pd.DataFrame, taxi: pd.DataFrame | None) -> pd.DataFrame:
    ewr_nas = nas[(nas.airport == "EWR") & (nas.period.isin(PERIOD_ORDER))].copy()
    nas_day = (
        ewr_nas.groupby("period", as_index=False)
        .agg(
            days=("days", "max"),
            ops_per_day=("ops_per_day", "sum"),
            nas_min_per_day=("nas_min_per_day", "sum"),
        )
    )
    if taxi is not None:
        ewr_taxi = taxi[(taxi.airport == "EWR") & (taxi.period.isin(PERIOD_ORDER))]
        taxi_day = (
            ewr_taxi.groupby("period", as_index=False)
            .agg(
                extra_taxi_per_day=("extra_taxi_per_day", "sum"),
                taxi_min_per_day=("taxi_min_per_day", "sum"),
            )
        )
        nas_day = nas_day.merge(taxi_day, on="period", how="left")
    else:
        nas_day["extra_taxi_per_day"] = np.nan
        nas_day["taxi_min_per_day"] = np.nan

    rows = []
    for _, r in nas_day.iterrows():
        period = r["period"]
        nas_min = float(r["nas_min_per_day"])
        extra_taxi = float(r["extra_taxi_per_day"]) if pd.notna(r["extra_taxi_per_day"]) else np.nan
        fuel_nas, co2_nas = fuel_co2(nas_min)
        fuel_nas_lo, co2_nas_lo = fuel_co2(nas_min, "low")
        fuel_nas_hi, co2_nas_hi = fuel_co2(nas_min, "high")
        if pd.notna(extra_taxi):
            fuel_tx, co2_tx = fuel_co2(extra_taxi)
        else:
            fuel_tx = co2_tx = np.nan
        rows.append(
            {
                "period": period,
                "regime": REGIME_KEY[period],
                "label": PERIOD_LABEL[period],
                "ops_per_day": float(r["ops_per_day"]),
                "nas_min_per_day": nas_min,
                "extra_taxi_min_per_day": extra_taxi,
                "nas_fuel_t_per_day": fuel_nas / 1000,
                "nas_co2_t_per_day": co2_nas / 1000,
                "nas_fuel_t_low": fuel_nas_lo / 1000,
                "nas_fuel_t_high": fuel_nas_hi / 1000,
                "nas_co2_t_low": co2_nas_lo / 1000,
                "nas_co2_t_high": co2_nas_hi / 1000,
                "extra_taxi_fuel_t_per_day": fuel_tx / 1000 if pd.notna(fuel_tx) else np.nan,
                "extra_taxi_co2_t_per_day": co2_tx / 1000 if pd.notna(co2_tx) else np.nan,
                "nas_fuel_kg_per_op": fuel_nas / float(r["ops_per_day"]),
                "nas_co2_kg_per_op": co2_nas / float(r["ops_per_day"]),
            }
        )
    out = pd.DataFrame(rows)
    out["period"] = pd.Categorical(out["period"], PERIOD_ORDER, ordered=True)
    return out.sort_values("period").reset_index(drop=True)


def usable_judgment(reg: pd.DataFrame, did_rows: list[dict]) -> dict:
    by = reg.set_index("regime")
    stress_co2 = float(by.loc["stress", "nas_co2_t_per_day"])
    r28_co2 = float(by.loc["28/28", "nas_co2_t_per_day"])
    r34_co2 = float(by.loc["34/34", "nas_co2_t_per_day"])
    r36_co2 = float(by.loc["36/36", "nas_co2_t_per_day"])
    did_arr = next(d for d in did_rows if d["side"] == "arr")
    did_dep = next(d for d in did_rows if d["side"] == "dep")
    did_min = did_arr["did_min_per_day_using_stress_ops"] + did_dep["did_min_per_day_using_stress_ops"]
    did_fuel, did_co2 = fuel_co2(did_min)
    cut_stress_28 = stress_co2 - r28_co2
    # Usable if: (1) stress-to-28/28 CO2 cut is large and same sign as DID;
    # (2) 28/28 has lowest waste among the three targets; (3) 34 vs 36 contrast
    # is reportable even if small.
    usable = (
        cut_stress_28 > 50
        and did_co2 / 1000 < -50
        and r28_co2 < r34_co2
        and r28_co2 < r36_co2
    )
    return {
        "usable": bool(usable),
        "reason": (
            "Stress-to-28/28 delay-waste CO2 cut exceeds 50 t/day, DID-implied "
            "cut exceeds 50 t/day, and 28/28 is the lowest-waste observed target."
            if usable
            else "Contrast too small, wrong-signed, or 28/28 is not the lowest-waste target."
        ),
        "stress_co2_t_day": stress_co2,
        "co2_28": r28_co2,
        "co2_34": r34_co2,
        "co2_36": r36_co2,
        "cut_stress_to_28_t_day": cut_stress_28,
        "lift_28_to_34_t_day": r34_co2 - r28_co2,
        "diff_34_to_36_t_day": r36_co2 - r34_co2,
        "did_min_per_day": did_min,
        "did_fuel_t_day": did_fuel / 1000,
        "did_co2_t_day": did_co2 / 1000,
        "did_arr_min_per_op": did_arr["did_min_per_op"],
        "did_dep_min_per_op": did_dep["did_min_per_op"],
        "fuel_kg_per_min_primary": FUEL_KG_PER_MIN["primary"],
        "co2_kg_per_kg_fuel": CO2_KG_PER_KG_FUEL,
    }


def write_md(reg: pd.DataFrame, judge: dict, taxi_ok: bool) -> str:
    lines = [
        "# Delay-waste fuel and CO2 smoke test",
        "",
        "Accounting boundary: NAS-attributed delay minutes and extra taxi minutes",
        "(operated flights, extra taxi = observed taxi minus airport-side 10th percentile",
        "of on-time taxi). Not a full-flight LCA. Fuel flow 12.5 kg/min (idle/taxi fleet",
        "mix; bounds 8--16 kg/min). CO2 = 3.16 kg/kg fuel (ICAO/IPCC jet A).",
        "",
        f"**Usable for the paper: {judge['usable']}.** {judge['reason']}",
        "",
        "## EWR regime delay-waste (NAS delay, primary factor)",
        "",
        "| Regime | Ops/day | NAS min/day | Fuel t/day | CO2 t/day | CO2 kg/op | Fuel t/day (8--16 kg/min) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in reg.iterrows():
        lines.append(
            f"| {r['label']} | {r['ops_per_day']:.1f} | {r['nas_min_per_day']:.0f} | "
            f"{r['nas_fuel_t_per_day']:.1f} | {r['nas_co2_t_per_day']:.1f} | "
            f"{r['nas_co2_kg_per_op']:.1f} | {r['nas_fuel_t_low']:.1f}--{r['nas_fuel_t_high']:.1f} |"
        )
    lines += [
        "",
        "## Contrasts (primary factor)",
        "",
        f"- Stress to 28/28: {judge['cut_stress_to_28_t_day']:.1f} t CO2/day avoided (observed EWR).",
        f"- DID-implied (EWR minus controls, stress ops): {judge['did_co2_t_day']:.1f} t CO2/day "
        f"({judge['did_fuel_t_day']:.1f} t fuel/day; {judge['did_min_per_day']:.0f} delay-min/day).",
        f"- 28/28 to 34/34: {judge['lift_28_to_34_t_day']:.1f} t CO2/day added as service is restored.",
        f"- 34/34 to 36/36: {judge['diff_34_to_36_t_day']:.1f} t CO2/day.",
        "",
    ]
    if taxi_ok and reg["extra_taxi_co2_t_per_day"].notna().all():
        lines += ["## Extra taxi (engine-on ground waste)", "", "| Regime | Extra taxi min/day | Fuel t/day | CO2 t/day |", "|---|---:|---:|---:|"]
        for _, r in reg.iterrows():
            lines.append(
                f"| {r['label']} | {r['extra_taxi_min_per_day']:.0f} | "
                f"{r['extra_taxi_fuel_t_per_day']:.1f} | {r['extra_taxi_co2_t_per_day']:.1f} |"
            )
        lines.append("")
    lines += [
        "## Judgment notes",
        "",
        "NAS delay includes airborne holding and some assigned ground delay; gate holds",
        "with engines off are not separated. Extra taxi is the more conservative",
        "engine-on ground layer. Headline paper numbers should use DID-implied NAS",
        "waste for the stress-to-interim cut, and observed-regime NAS (and extra taxi",
        "if stable) for 28/28 vs 34/34 vs 36/36.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    nas = summarize_nas_from_daily()
    nas.to_csv(OUT / "nas_period_airport_side.csv", index=False)
    did_rows = did_nas(nas, "stress_20250415_0519", "interim_20250520_0615")
    pd.DataFrame(did_rows).to_csv(OUT / "nas_did_stress_to_interim.csv", index=False)

    taxi_ok = False
    taxi_sum = None
    try:
        parts = []
        for month in range(1, 13):
            zip_path = RAW / f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_{month}.zip"
            if not zip_path.exists():
                continue
            parts.append(airport_side_taxi(read_month(month)))
        if parts:
            panel = pd.concat(parts, ignore_index=True)
            unimp = unimpeded_taxi(panel)
            unimp.to_csv(OUT / "unimpeded_taxi_p10.csv", index=False)
            taxi_sum = summarize_taxi(panel, unimp)
            taxi_sum.to_csv(OUT / "taxi_period_airport_side.csv", index=False)
            taxi_ok = True
    except Exception as exc:
        (OUT / "taxi_error.txt").write_text(str(exc), encoding="utf-8")

    reg = regime_table(nas, taxi_sum)
    reg.to_csv(OUT / "ewr_regime_delay_waste.csv", index=False)
    judge = usable_judgment(reg, did_rows)
    (OUT / "summary.json").write_text(json.dumps(judge, indent=2), encoding="utf-8")
    md = write_md(reg, judge, taxi_ok)
    (OUT / "summary.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
