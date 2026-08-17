from __future__ import annotations

import argparse
import io
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


BASE = Path(__file__).resolve().parents[1]
TOP50_DAILY = BASE / "results" / "tra_policy_experiments" / "airport_side_daily_top_airports.csv"
RAW_WEATHER = BASE / "data" / "weather_asos"
OUT = BASE / "results" / "tra_weather_controls"
OUT_SMOKE = BASE / "results" / "tra_weather_controls_smoke"
TABLES = BASE / "article" / "elsarticle" / "tables"

SMOKE_AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL"]
DID_AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL", "IAD", "DCA", "BWI", "ATL", "ORD"]
REFERENCE = ("2025-03-18", "2025-04-14")
PHASES = {
    "stress": ("2025-04-15", "2025-05-19", "Stress"),
    "early_interim": ("2025-05-20", "2025-06-02", "May 20--Jun 2"),
    "late_interim": ("2025-06-03", "2025-06-15", "Jun 3--Jun 15"),
}
METRICS = {
    "cancel_rate": ("Cancellation rate", "pp"),
    "delay15_rate": ("Delay-15-plus rate", "pp"),
    "nas_delay_per_scheduled_op": ("NAS delay", "min/op"),
}
WEATHER_CONTROLS = [
    "avg_wind_kt",
    "max_gust_kt",
    "min_visibility_mi",
    "precip_report_share",
    "thunderstorm_report_share",
    "low_ceiling_report_share",
]


def format_value(value: float, unit: str) -> str:
    if pd.isna(value):
        return "--"
    if unit == "pp":
        return f"{100 * value:.1f} pp"
    return f"{value:.1f}"


def load_airports(smoke: bool, airport_set: str) -> list[str]:
    if smoke:
        return SMOKE_AIRPORTS
    if airport_set == "did10":
        return DID_AIRPORTS
    daily = pd.read_csv(TOP50_DAILY, usecols=["airport"])
    return sorted(daily["airport"].dropna().unique().tolist())


def build_url(station: str) -> str:
    params: list[tuple[str, str | int]] = [
        ("station", station),
        ("data", "sknt"),
        ("data", "gust"),
        ("data", "p01i"),
        ("data", "vsby"),
        ("data", "skyc1"),
        ("data", "skyl1"),
        ("data", "wxcodes"),
        ("year1", 2025),
        ("month1", 3),
        ("day1", 18),
        ("year2", 2025),
        ("month2", 6),
        ("day2", 15),
        ("tz", "Etc/UTC"),
        ("format", "onlycomma"),
        ("latlon", "no"),
        ("elev", "no"),
        ("missing", "M"),
        ("trace", "T"),
        ("direct", "no"),
        ("report_type", 1),
        ("report_type", 2),
    ]
    return "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?" + urlencode(params)


def fetch_station(station: str, force: bool = False) -> Path | None:
    RAW_WEATHER.mkdir(parents=True, exist_ok=True)
    path = RAW_WEATHER / f"{station}_asos_20250318_20250615.csv"
    if path.exists() and not force:
        return path
    url = build_url(station)
    try:
        with urlopen(url, timeout=60) as response:
            content = response.read()
    except Exception as exc:
        print(f"Weather download failed for {station}: {exc}")
        return None
    text = content.decode("utf-8", errors="replace")
    if not text.startswith("station,valid"):
        print(f"Weather download returned unexpected content for {station}")
        return None
    path.write_text(text, encoding="utf-8")
    time.sleep(0.25)
    return path


def numeric(series: pd.Series) -> pd.Series:
    cleaned = series.replace({"M": np.nan, "T": 0.0, "": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


def aggregate_station(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    if df.empty:
        return pd.DataFrame()
    station = str(df["station"].iloc[0])
    df["valid"] = pd.to_datetime(df["valid"], errors="coerce")
    df = df.dropna(subset=["valid"]).copy()
    df["FlightDate"] = df["valid"].dt.floor("D")
    for col in ["sknt", "gust", "p01i", "vsby", "skyl1"]:
        df[col] = numeric(df[col])
    codes = df["wxcodes"].fillna("").replace("M", "")
    df["precip_report"] = ((df["p01i"].fillna(0) > 0) | codes.str.contains("RA|SN|TS", regex=True)).astype(float)
    df["thunderstorm_report"] = codes.str.contains("TS", regex=True).astype(float)
    sky_cover = df["skyc1"].fillna("").replace("M", "")
    df["low_ceiling_report"] = ((df["skyl1"] <= 1000) & sky_cover.isin(["BKN", "OVC", "VV"])).astype(float)
    out = (
        df.groupby("FlightDate", as_index=False)
        .agg(
            obs_count=("station", "size"),
            avg_wind_kt=("sknt", "mean"),
            max_wind_kt=("sknt", "max"),
            max_gust_kt=("gust", "max"),
            min_visibility_mi=("vsby", "min"),
            precip_report_share=("precip_report", "mean"),
            thunderstorm_report_share=("thunderstorm_report", "mean"),
            low_ceiling_report_share=("low_ceiling_report", "mean"),
        )
    )
    out["airport"] = station
    out["max_gust_kt"] = out["max_gust_kt"].fillna(out["max_wind_kt"])
    return out


def build_weather(airports: list[str], force: bool) -> pd.DataFrame:
    frames = []
    for airport in airports:
        path = fetch_station(airport, force=force)
        if path is None:
            continue
        station_weather = aggregate_station(path)
        if not station_weather.empty:
            frames.append(station_weather)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def restrict_policy_window(daily: pd.DataFrame) -> pd.DataFrame:
    ref_start, ref_end = [pd.Timestamp(x) for x in REFERENCE]
    mask = daily["FlightDate"].between(ref_start, ref_end)
    for start, end, _label in PHASES.values():
        mask = mask | daily["FlightDate"].between(pd.Timestamp(start), pd.Timestamp(end))
    data = daily.loc[mask].copy()
    data["date_id"] = data["FlightDate"].dt.strftime("%Y-%m-%d")
    data["ewr_stress"] = (
        (data["airport"] == "EWR")
        & data["FlightDate"].between(pd.Timestamp(PHASES["stress"][0]), pd.Timestamp(PHASES["stress"][1]))
    ).astype(int)
    data["ewr_early_interim"] = (
        (data["airport"] == "EWR")
        & data["FlightDate"].between(pd.Timestamp(PHASES["early_interim"][0]), pd.Timestamp(PHASES["early_interim"][1]))
    ).astype(int)
    data["ewr_late_interim"] = (
        (data["airport"] == "EWR")
        & data["FlightDate"].between(pd.Timestamp(PHASES["late_interim"][0]), pd.Timestamp(PHASES["late_interim"][1]))
    ).astype(int)
    return data


def fit_phase_model(data: pd.DataFrame, outcome: str, weather_controls: bool) -> dict[str, tuple[float, float, float]]:
    rhs = "ewr_stress + ewr_early_interim + ewr_late_interim + C(airport) + C(date_id)"
    if weather_controls:
        rhs += " + " + " + ".join(WEATHER_CONTROLS)
    model_data = data.dropna(subset=[outcome] + (WEATHER_CONTROLS if weather_controls else [])).copy()
    model = smf.ols(f"{outcome} ~ {rhs}", data=model_data).fit(
        cov_type="cluster",
        cov_kwds={"groups": model_data["date_id"]},
    )
    out = {}
    for term in ["ewr_stress", "ewr_early_interim", "ewr_late_interim"]:
        coef = float(model.params.get(term, np.nan))
        se = float(model.bse.get(term, np.nan))
        out[term] = (coef, coef - 1.96 * se, coef + 1.96 * se)
    return out


def run_models(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    phase_terms = [
        ("ewr_stress", "Stress"),
        ("ewr_early_interim", "May 20--Jun 2"),
        ("ewr_late_interim", "Jun 3--Jun 15"),
    ]
    for side in ["arr", "dep"]:
        side_data = panel[panel["side"] == side].copy()
        for metric, (label, unit) in METRICS.items():
            for weather_controls in [False, True]:
                estimates = fit_phase_model(side_data, metric, weather_controls=weather_controls)
                for term, phase in phase_terms:
                    coef, low, high = estimates[term]
                    rows.append(
                        {
                            "side": side,
                            "metric": metric,
                            "metric_label": label,
                            "unit": unit,
                            "phase": phase,
                            "weather_controls": weather_controls,
                            "coef": coef,
                            "ci_low": low,
                            "ci_high": high,
                        }
                    )
    return pd.DataFrame(rows)


def write_latex_table(results: pd.DataFrame, table_path: Path) -> None:
    focus = results[
        (results["phase"] == "Jun 3--Jun 15")
        & (results["metric"].isin(["delay15_rate", "nas_delay_per_scheduled_op"]))
    ].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\footnotesize",
        r"\caption{External station-weather control sensitivity}",
        r"\label{tab:station-weather-sensitivity}",
        r"\begin{tabular}{@{}llrr@{}}",
        r"\toprule",
        r"Outcome & Side & Date FE & Date FE + weather \\",
        r"\midrule",
    ]
    for metric in ["delay15_rate", "nas_delay_per_scheduled_op"]:
        for side in ["arr", "dep"]:
            base = focus[
                (focus["metric"] == metric) & (focus["side"] == side) & (focus["weather_controls"] == False)
            ].iloc[0]
            weather = focus[
                (focus["metric"] == metric) & (focus["side"] == side) & (focus["weather_controls"] == True)
            ].iloc[0]
            base_val = format_value(base["coef"], base["unit"])
            weather_val = format_value(weather["coef"], weather["unit"])
            if base["coef"] < 0:
                base_val = rf"\textbf{{{base_val}}}"
            if weather["coef"] < 0:
                weather_val = rf"\textbf{{{weather_val}}}"
            lines.append(f"{base['metric_label']} & {side.upper()} & {base_val} & {weather_val} \\\\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\footnotesize Notes: Estimates are the Jun 3--Jun 15 EWR-by-phase coefficients from airport-day panels with airport and calendar-date fixed effects. Weather controls are station-day wind, gust, visibility, precipitation-report share, thunderstorm-report share, and low-ceiling-report share. Bold values mark lower reliability failures.}",
            r"\end{table}",
        ]
    )
    table_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(weather: pd.DataFrame, panel: pd.DataFrame, results: pd.DataFrame, out_dir: Path) -> None:
    coverage = (
        weather.groupby("airport", as_index=False)
        .agg(days=("FlightDate", "nunique"), obs=("obs_count", "sum"))
        .sort_values("airport")
    )
    lines = [
        "# TRA external station-weather control check",
        "",
        "## Weather coverage",
        "",
        coverage.to_markdown(index=False),
        "",
        f"Merged airport-day-side rows: {len(panel)}.",
        "",
        "## Phase estimates",
        "",
        results.to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--airport-set", choices=["did10", "top50"], default="did10")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = OUT_SMOKE if args.smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    airports = load_airports(args.smoke, args.airport_set)
    weather = build_weather(airports, force=args.force)
    if weather.empty:
        raise RuntimeError("No station weather data were downloaded or parsed.")
    daily = pd.read_csv(TOP50_DAILY, parse_dates=["FlightDate"])
    if args.smoke:
        daily = daily[daily["airport"].isin(SMOKE_AIRPORTS)].copy()
    elif args.airport_set == "did10":
        daily = daily[daily["airport"].isin(DID_AIRPORTS)].copy()
    panel = restrict_policy_window(daily).merge(weather, on=["airport", "FlightDate"], how="inner")
    results = run_models(panel)
    weather.to_csv(out_dir / "asos_station_weather_daily.csv", index=False)
    panel.to_csv(out_dir / "airport_day_weather_panel.csv", index=False)
    results.to_csv(out_dir / "weather_control_phase_estimates.csv", index=False)
    write_summary(weather, panel, results, out_dir)
    if not args.smoke and TABLES.exists():
        write_latex_table(results, TABLES / "tab_station_weather_sensitivity.tex")
    print("Weather coverage")
    print(weather.groupby("airport")["FlightDate"].nunique().to_string())
    print("\nPhase estimates")
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
