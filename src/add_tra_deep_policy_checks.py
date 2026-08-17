from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


BASE = Path(__file__).resolve().parents[1]
RAW_BTS = BASE / "data" / "raw_bts_2025"
DAILY_TOP50 = BASE / "results" / "tra_policy_experiments" / "airport_side_daily_top_airports.csv"
HOURLY_DAY = BASE / "results" / "tra_peak_hour_mechanism" / "airport_day_hour_group.csv"
HOURLY_DAY_SMOKE = BASE / "results" / "tra_peak_hour_mechanism_smoke" / "airport_day_hour_group.csv"
WEATHER_PANEL = BASE / "results" / "tra_weather_controls" / "airport_day_weather_panel.csv"
T100_DOMESTIC = BASE / "results" / "tra_policy_experiments" / "t100_ewr_route_carrier_month.csv"
T100_DOMESTIC_MONTHLY = BASE / "results" / "tra_policy_experiments" / "t100_ewr_monthly_exposure.csv"
T100_INTL = BASE / "results" / "tra_t100_international_exposure" / "t100_international_ewr_route_carrier_month.csv"
T100_INTL_MONTHLY = BASE / "results" / "tra_t100_international_exposure" / "t100_international_ewr_monthly_exposure.csv"
OUT = BASE / "results" / "tra_deep_policy_checks"
OUT_SMOKE = BASE / "results" / "tra_deep_policy_checks_smoke"
TABLES = BASE / "article" / "elsarticle" / "tables"

SMOKE_AIRPORTS = ["EWR", "JFK", "LGA", "BOS", "PHL"]
CONTROL_AIRPORTS = ["JFK", "LGA", "BOS", "PHL", "IAD", "DCA", "BWI", "ATL", "ORD"]
REFERENCE = ("2025-03-18", "2025-04-14")
STRESS = ("2025-04-15", "2025-05-19")
INTERIM = ("2025-05-20", "2025-06-15")
LATE_INTERIM = ("2025-06-03", "2025-06-15")
USE_MONTHS = [3, 4, 5, 6]

OTP_USECOLS = [
    "FlightDate",
    "Reporting_Airline",
    "Origin",
    "Dest",
    "DepDel15",
    "ArrDel15",
    "DepDelayMinutes",
    "ArrDelayMinutes",
    "Cancelled",
    "NASDelay",
]

MAIN_METRICS = {
    "scheduled_ops": ("Scheduled operations", "ops/day", 1.0),
    "cancel_rate": ("Cancellation rate", "pp", 100.0),
    "delay15_rate": ("Delay-15-plus rate", "pp", 100.0),
    "nas_delay_per_scheduled_op": ("NAS delay", "min/op", 1.0),
}

TAIL_METRICS = {
    "p90_delay_minutes": ("P90 delay", "min", 1.0),
    "p95_delay_minutes": ("P95 delay", "min", 1.0),
    "delay60_rate": ("Delay-60-plus rate", "pp", 100.0),
    "cancel_or_delay60_rate": ("Cancellation-or-60-plus rate", "pp", 100.0),
}


def date_between(s: pd.Series, start: str, end: str) -> pd.Series:
    return s.between(pd.Timestamp(start), pd.Timestamp(end))


def fmt(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "--"
    return f"{value:.{digits}f}"


def fmt_scaled(value: float, scale: float, digits: int = 1) -> str:
    return fmt(value * scale, digits)


def period_from_date(date: pd.Timestamp) -> str:
    if pd.Timestamp(REFERENCE[0]) <= date <= pd.Timestamp(REFERENCE[1]):
        return "reference"
    if pd.Timestamp(STRESS[0]) <= date <= pd.Timestamp(STRESS[1]):
        return "stress"
    if pd.Timestamp(INTERIM[0]) <= date <= pd.Timestamp(INTERIM[1]):
        return "interim"
    return "other"


def load_daily(smoke: bool) -> pd.DataFrame:
    daily = pd.read_csv(DAILY_TOP50, parse_dates=["FlightDate"])
    daily["date_id"] = daily["FlightDate"].dt.strftime("%Y-%m-%d")
    daily = daily[date_between(daily["FlightDate"], REFERENCE[0], INTERIM[1])].copy()
    if smoke:
        daily = daily[daily["airport"].isin(SMOKE_AIRPORTS)].copy()
    return daily


def top_airports_from_daily(daily: pd.DataFrame, smoke: bool) -> list[str]:
    airports = sorted(daily["airport"].dropna().unique().tolist())
    if smoke:
        return [a for a in SMOKE_AIRPORTS if a in airports]
    return airports


def dynamic_event_study(daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    controls = [a for a in daily["airport"].unique() if a != "EWR"]
    ref_start, ref_end = REFERENCE
    for side in ["arr", "dep"]:
        side_data = daily[daily["side"] == side].copy()
        for metric, (label, unit, scale) in MAIN_METRICS.items():
            pivot = side_data.pivot_table(index="FlightDate", columns="airport", values=metric, aggfunc="first")
            usable_controls = [c for c in controls if c in pivot.columns]
            pivot = pivot.dropna(subset=["EWR"])
            control_mean = pivot[usable_controls].mean(axis=1)
            gap = pivot["EWR"] - control_mean
            ref_gap = gap[date_between(gap.index.to_series(), ref_start, ref_end)].mean()
            coef = gap - ref_gap
            for date, value in coef.items():
                rows.append(
                    {
                        "FlightDate": date,
                        "date_id": pd.Timestamp(date).strftime("%Y-%m-%d"),
                        "period": period_from_date(pd.Timestamp(date)),
                        "side": side,
                        "metric": metric,
                        "metric_label": label,
                        "unit": unit,
                        "scale": scale,
                        "ewr_minus_control_gap": gap.loc[date],
                        "reference_gap": ref_gap,
                        "dynamic_contrast": value,
                        "dynamic_contrast_scaled": value * scale,
                    }
                )
    return pd.DataFrame(rows)


def load_hourly(smoke: bool) -> pd.DataFrame:
    path = HOURLY_DAY_SMOKE if smoke and HOURLY_DAY_SMOKE.exists() else HOURLY_DAY
    hourly = pd.read_csv(path, parse_dates=["FlightDate"])
    hourly = hourly[hourly["hour_group"] == "Facilitated hours"].copy()
    hourly = hourly[date_between(hourly["FlightDate"], REFERENCE[0], INTERIM[1])].copy()
    hourly["date_id"] = hourly["FlightDate"].dt.strftime("%Y-%m-%d")
    if smoke:
        hourly = hourly[hourly["airport"].isin(SMOKE_AIRPORTS)].copy()
    return hourly


def fit_pressure_model(data: pd.DataFrame, outcome: str, pressure: str, weather: bool = False):
    frame = data.dropna(subset=[outcome, pressure]).copy()
    rhs = f"{pressure} + C(airport) + C(date_id) + C(side)"
    if weather:
        weather_cols = [
            "avg_wind_kt",
            "max_gust_kt",
            "min_visibility_mi",
            "precip_report_share",
            "thunderstorm_report_share",
            "low_ceiling_report_share",
        ]
        present = [col for col in weather_cols if col in frame.columns]
        rhs += "".join([f" + {col}" for col in present])
    model = smf.ols(f"{outcome} ~ {rhs}", data=frame).fit(
        cov_type="cluster", cov_kwds={"groups": frame["date_id"]}
    )
    coef = float(model.params.get(pressure, np.nan))
    se = float(model.bse.get(pressure, np.nan))
    return coef, se, coef - 1.96 * se, coef + 1.96 * se, int(model.nobs)


def dose_response_models(hourly: pd.DataFrame, smoke: bool) -> pd.DataFrame:
    rows = []
    pressure_specs = {
        "avg_ops_per_hour": ("Mean scheduled operations/hour", 5.0),
        "p95_ops_per_hour": ("P95 scheduled operations/hour", 5.0),
        "share_above_28": ("Share of hours above 28", 0.10),
        "share_above_34": ("Share of hours above 34", 0.10),
    }
    outcomes = {
        "delay15_rate": ("Delay-15-plus rate", "pp", 100.0),
        "nas_delay_per_scheduled_op": ("NAS delay", "min/op", 1.0),
    }
    for pressure, (pressure_label, increment) in pressure_specs.items():
        for outcome, (outcome_label, unit, scale) in outcomes.items():
            coef, se, low, high, nobs = fit_pressure_model(hourly, outcome, pressure)
            rows.append(
                {
                    "model": "airport_date_side_fe",
                    "outcome": outcome,
                    "outcome_label": outcome_label,
                    "unit": unit,
                    "pressure": pressure,
                    "pressure_label": pressure_label,
                    "increment": increment,
                    "coef": coef,
                    "se": se,
                    "ci_low": low,
                    "ci_high": high,
                    "scaled_coef": coef * increment * scale,
                    "scaled_ci_low": low * increment * scale,
                    "scaled_ci_high": high * increment * scale,
                    "nobs": nobs,
                }
            )
    weather_rows = []
    if WEATHER_PANEL.exists():
        weather = pd.read_csv(WEATHER_PANEL, parse_dates=["FlightDate"])
        weather = weather[
            [
                "FlightDate",
                "date_id",
                "airport",
                "side",
                "avg_wind_kt",
                "max_gust_kt",
                "min_visibility_mi",
                "precip_report_share",
                "thunderstorm_report_share",
                "low_ceiling_report_share",
            ]
        ].drop_duplicates()
        ten = hourly.merge(weather, on=["FlightDate", "date_id", "airport", "side"], how="inner")
        if smoke:
            ten = ten[ten["airport"].isin(SMOKE_AIRPORTS)].copy()
        for pressure, (pressure_label, increment) in pressure_specs.items():
            for outcome, (outcome_label, unit, scale) in outcomes.items():
                coef, se, low, high, nobs = fit_pressure_model(ten, outcome, pressure, weather=True)
                weather_rows.append(
                    {
                        "model": "airport_date_side_fe_station_weather",
                        "outcome": outcome,
                        "outcome_label": outcome_label,
                        "unit": unit,
                        "pressure": pressure,
                        "pressure_label": pressure_label,
                        "increment": increment,
                        "coef": coef,
                        "se": se,
                        "ci_low": low,
                        "ci_high": high,
                        "scaled_coef": coef * increment * scale,
                        "scaled_ci_low": low * increment * scale,
                        "scaled_ci_high": high * increment * scale,
                        "nobs": nobs,
                    }
                )
    return pd.concat([pd.DataFrame(rows), pd.DataFrame(weather_rows)], ignore_index=True)


def read_otp_month(month: int) -> pd.DataFrame:
    zip_path = RAW_BTS / f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_{month}.zip"
    with zipfile.ZipFile(zip_path) as zf:
        name = [name for name in zf.namelist() if name.lower().endswith(".csv")][0]
        with zf.open(name) as fh:
            df = pd.read_csv(fh, usecols=OTP_USECOLS, low_memory=False)
    df["FlightDate"] = pd.to_datetime(df["FlightDate"])
    return df


def build_flight_panels(airports: list[str], smoke: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    months = [4, 5, 6] if smoke else USE_MONTHS
    tail_parts = []
    carrier_parts = []
    for month in months:
        df = read_otp_month(month)
        df["Cancelled"] = df["Cancelled"].fillna(0).astype(float)
        df["NASDelay"] = df["NASDelay"].fillna(0).astype(float)
        df["DepDel15"] = df["DepDel15"].fillna(0).astype(float)
        df["ArrDel15"] = df["ArrDel15"].fillna(0).astype(float)
        df["DepDelayMinutes"] = df["DepDelayMinutes"].fillna(0).astype(float)
        df["ArrDelayMinutes"] = df["ArrDelayMinutes"].fillna(0).astype(float)
        df["carrier_group"] = np.where(df["Reporting_Airline"] == "UA", "United", "Other carriers")

        dep = df[df["Origin"].isin(airports)].copy()
        dep = dep.assign(
            airport=dep["Origin"],
            side="dep",
            delay15_flag=dep["DepDel15"],
            delay_minutes=dep["DepDelayMinutes"],
            cancelled_flag=dep["Cancelled"],
        )
        arr = df[df["Dest"].isin(airports)].copy()
        arr = arr.assign(
            airport=arr["Dest"],
            side="arr",
            delay15_flag=arr["ArrDel15"],
            delay_minutes=arr["ArrDelayMinutes"],
            cancelled_flag=arr["Cancelled"],
        )
        records = pd.concat([arr, dep], ignore_index=True)
        records["operated_flag"] = (records["cancelled_flag"] == 0).astype(float)
        records["delay60_flag"] = ((records["operated_flag"] == 1) & (records["delay_minutes"] >= 60)).astype(float)
        records["cancel_or_delay60_flag"] = ((records["cancelled_flag"] == 1) | (records["delay60_flag"] == 1)).astype(float)
        records["operated_delay_minutes"] = records["delay_minutes"].where(records["operated_flag"] == 1)

        tail = (
            records.groupby(["FlightDate", "airport", "side"], as_index=False)
            .agg(
                scheduled_ops=("airport", "size"),
                operated_ops=("operated_flag", "sum"),
                p90_delay_minutes=("operated_delay_minutes", lambda x: x.dropna().quantile(0.90)),
                p95_delay_minutes=("operated_delay_minutes", lambda x: x.dropna().quantile(0.95)),
                delay60_ops=("delay60_flag", "sum"),
                cancel_or_delay60_ops=("cancel_or_delay60_flag", "sum"),
            )
        )
        tail["delay60_rate"] = tail["delay60_ops"] / tail["operated_ops"].replace(0, np.nan)
        tail["cancel_or_delay60_rate"] = tail["cancel_or_delay60_ops"] / tail["scheduled_ops"].replace(0, np.nan)
        tail_parts.append(tail)

        carrier = (
            records.groupby(["FlightDate", "airport", "side", "carrier_group"], as_index=False)
            .agg(
                scheduled_ops=("airport", "size"),
                operated_ops=("operated_flag", "sum"),
                cancelled_ops=("cancelled_flag", "sum"),
                delay15_ops=("delay15_flag", "sum"),
                nas_delay_minutes=("NASDelay", "sum"),
            )
        )
        carrier["cancel_rate"] = carrier["cancelled_ops"] / carrier["scheduled_ops"].replace(0, np.nan)
        carrier["delay15_rate"] = carrier["delay15_ops"] / carrier["operated_ops"].replace(0, np.nan)
        carrier["nas_delay_per_scheduled_op"] = carrier["nas_delay_minutes"] / carrier["scheduled_ops"].replace(0, np.nan)
        carrier_parts.append(carrier)

    tail_daily = pd.concat(tail_parts, ignore_index=True)
    carrier_daily = pd.concat(carrier_parts, ignore_index=True)
    for frame in [tail_daily, carrier_daily]:
        frame["date_id"] = frame["FlightDate"].dt.strftime("%Y-%m-%d")
        frame["period"] = frame["FlightDate"].map(period_from_date)
        frame.drop(frame[frame["period"] == "other"].index, inplace=True)
    return tail_daily, carrier_daily


def phase_model(data: pd.DataFrame, outcome: str) -> tuple[float, float, float, int]:
    frame = data[date_between(data["FlightDate"], REFERENCE[0], LATE_INTERIM[1])].dropna(subset=[outcome]).copy()
    frame["ewr_stress"] = ((frame["airport"] == "EWR") & date_between(frame["FlightDate"], STRESS[0], STRESS[1])).astype(int)
    frame["ewr_late_interim"] = (
        (frame["airport"] == "EWR") & date_between(frame["FlightDate"], LATE_INTERIM[0], LATE_INTERIM[1])
    ).astype(int)
    model = smf.ols(f"{outcome} ~ ewr_stress + ewr_late_interim + C(airport) + C(date_id)", data=frame).fit(
        cov_type="cluster", cov_kwds={"groups": frame["date_id"]}
    )
    cov = model.cov_params()
    late = float(model.params.get("ewr_late_interim", np.nan))
    stress = float(model.params.get("ewr_stress", np.nan))
    recovery = late - stress
    if {"ewr_late_interim", "ewr_stress"}.issubset(cov.index):
        se = float(
            np.sqrt(
                cov.loc["ewr_late_interim", "ewr_late_interim"]
                + cov.loc["ewr_stress", "ewr_stress"]
                - 2 * cov.loc["ewr_late_interim", "ewr_stress"]
            )
        )
    else:
        se = np.nan
    return recovery, recovery - 1.96 * se, recovery + 1.96 * se, int(model.nobs)


def tail_phase_checks(tail_daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for side in ["arr", "dep"]:
        side_data = tail_daily[tail_daily["side"] == side].copy()
        for metric, (label, unit, scale) in TAIL_METRICS.items():
            coef, low, high, nobs = phase_model(side_data, metric)
            rows.append(
                {
                    "side": side,
                    "metric": metric,
                    "metric_label": label,
                    "unit": unit,
                    "scale": scale,
                    "late_minus_stress": coef,
                    "ci_low": low,
                    "ci_high": high,
                    "scaled_late_minus_stress": coef * scale,
                    "scaled_ci_low": low * scale,
                    "scaled_ci_high": high * scale,
                    "nobs": nobs,
                }
            )
    return pd.DataFrame(rows)


def carrier_heterogeneity(carrier_daily: pd.DataFrame) -> pd.DataFrame:
    rows = []
    controls = [a for a in CONTROL_AIRPORTS if a in carrier_daily["airport"].unique()]
    for side in ["arr", "dep"]:
        for group in ["United", "Other carriers"]:
            subset = carrier_daily[(carrier_daily["side"] == side) & (carrier_daily["carrier_group"] == group)].copy()
            for metric, (label, unit, scale) in MAIN_METRICS.items():
                ewr_stress = subset[(subset["airport"] == "EWR") & (subset["period"] == "stress")][metric].mean()
                ewr_interim = subset[(subset["airport"] == "EWR") & (subset["period"] == "interim")][metric].mean()
                control_stress = subset[(subset["airport"].isin(controls)) & (subset["period"] == "stress")].groupby("FlightDate")[metric].mean().mean()
                control_interim = subset[(subset["airport"].isin(controls)) & (subset["period"] == "interim")].groupby("FlightDate")[metric].mean().mean()
                ewr_change = ewr_interim - ewr_stress
                control_change = control_interim - control_stress
                rows.append(
                    {
                        "side": side,
                        "carrier_group": group,
                        "metric": metric,
                        "metric_label": label,
                        "unit": unit,
                        "scale": scale,
                        "ewr_change": ewr_change,
                        "control_change": control_change,
                        "did": ewr_change - control_change,
                        "scaled_ewr_change": ewr_change * scale,
                        "scaled_control_change": control_change * scale,
                        "scaled_did": (ewr_change - control_change) * scale,
                    }
                )
    return pd.DataFrame(rows)


def market_access_weighted() -> pd.DataFrame:
    rows = []
    sources = [
        ("Domestic", pd.read_csv(T100_DOMESTIC), pd.read_csv(T100_DOMESTIC_MONTHLY)),
        ("International", pd.read_csv(T100_INTL).query("year == 2025").copy(), pd.read_csv(T100_INTL_MONTHLY).query("year == 2025").copy()),
    ]
    for layer, routes, monthly in sources:
        for side in ["arr", "dep"]:
            april = routes[(routes["month"] == 4) & (routes["side"] == side)].copy()
            june = routes[(routes["month"] == 6) & (routes["side"] == side)].copy()
            april_route = april.groupby("counterpart", as_index=False).agg(
                apr_passengers=("passengers", "sum"),
                apr_seats=("seats", "sum"),
            )
            june_route = june.groupby("counterpart", as_index=False).agg(
                jun_passengers=("passengers", "sum"),
                jun_seats=("seats", "sum"),
            )
            merged = april_route.merge(june_route, on="counterpart", how="left").fillna(0)
            total_apr_passengers = merged["apr_passengers"].sum()
            total_apr_seats = merged["apr_seats"].sum()
            retained = merged["jun_seats"] > 0
            passenger_weighted_market_retention = (
                merged.loc[retained, "apr_passengers"].sum() / total_apr_passengers if total_apr_passengers else np.nan
            )
            seat_retention_existing_april_markets = (
                merged["jun_seats"].sum() / total_apr_seats if total_apr_seats else np.nan
            )
            passenger_retention_existing_april_markets = (
                merged["jun_passengers"].sum() / total_apr_passengers if total_apr_passengers else np.nan
            )
            rows.append(
                {
                    "layer": layer,
                    "side": side,
                    "april_markets": int(len(april_route)),
                    "june_markets": int(june_route["counterpart"].nunique()),
                    "passenger_weighted_market_retention": passenger_weighted_market_retention,
                    "seat_retention_existing_april_markets": seat_retention_existing_april_markets,
                    "passenger_retention_existing_april_markets": passenger_retention_existing_april_markets,
                }
            )
    return pd.DataFrame(rows)


def passenger_time_bootstrap(daily: pd.DataFrame, reps: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t100 = pd.read_csv(T100_DOMESTIC_MONTHLY)
    rows = []
    ewr = daily[daily["airport"] == "EWR"].copy()
    for side in ["arr", "dep"]:
        stress = ewr[(ewr["side"] == side) & (ewr["period"] == "stress")]["nas_delay_minutes"].dropna().to_numpy()
        interim = ewr[(ewr["side"] == side) & (ewr["period"] == "interim")]["nas_delay_minutes"].dropna().to_numpy()
        t100_side = t100[(t100["side"] == side) & (t100["month"].isin([4, 5, 6]))]
        pax_per_flight = t100_side["passengers"].sum() / t100_side["departures_performed"].sum()
        point = (stress.mean() - interim.mean()) * pax_per_flight
        boot = []
        for _ in range(reps):
            s = rng.choice(stress, size=len(stress), replace=True)
            i = rng.choice(interim, size=len(interim), replace=True)
            boot.append((s.mean() - i.mean()) * pax_per_flight)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        rows.append(
            {
                "side": side,
                "nas_min_day_reduction": stress.mean() - interim.mean(),
                "passengers_per_flight": pax_per_flight,
                "passenger_min_day_reduction": point,
                "ci_low": lo,
                "ci_high": hi,
                "bootstrap_reps": reps,
            }
        )
    return pd.DataFrame(rows)


def ridge_counterfactual(daily: pd.DataFrame, alpha: float = 10.0) -> pd.DataFrame:
    rows = []
    airports = sorted([a for a in daily["airport"].unique() if a != "EWR"])
    for side in ["arr", "dep"]:
        side_data = daily[daily["side"] == side].copy()
        for metric, (label, unit, scale) in MAIN_METRICS.items():
            pivot = side_data.pivot_table(index="FlightDate", columns="airport", values=metric, aggfunc="first")
            pivot = pivot.dropna(subset=["EWR"])
            donors = [a for a in airports if a in pivot.columns]
            pivot = pivot.dropna(subset=donors)
            pre = pivot.index < pd.Timestamp(INTERIM[0])
            x_pre = pivot.loc[pre, donors].to_numpy(float)
            y_pre = pivot.loc[pre, "EWR"].to_numpy(float)
            x_mean = x_pre.mean(axis=0)
            x_std = x_pre.std(axis=0)
            x_std[x_std < 1e-9] = 1.0
            y_mean = y_pre.mean()
            y_std = y_pre.std() if y_pre.std() > 1e-9 else 1.0
            xs = (x_pre - x_mean) / x_std
            ys = (y_pre - y_mean) / y_std
            beta = np.linalg.solve(xs.T @ xs + alpha * np.eye(xs.shape[1]), xs.T @ ys)
            x_all = (pivot[donors].to_numpy(float) - x_mean) / x_std
            pred = (x_all @ beta) * y_std + y_mean
            path = pd.DataFrame({"FlightDate": pivot.index, "observed": pivot["EWR"].to_numpy(float), "ridge": pred})
            stress = date_between(path["FlightDate"], STRESS[0], STRESS[1])
            interim = date_between(path["FlightDate"], INTERIM[0], INTERIM[1])
            obs_change = path.loc[interim, "observed"].mean() - path.loc[stress, "observed"].mean()
            ridge_change = path.loc[interim, "ridge"].mean() - path.loc[stress, "ridge"].mean()
            rows.append(
                {
                    "side": side,
                    "metric": metric,
                    "metric_label": label,
                    "unit": unit,
                    "scale": scale,
                    "observed_change": obs_change,
                    "ridge_change": ridge_change,
                    "recovery_gap": obs_change - ridge_change,
                    "scaled_recovery_gap": (obs_change - ridge_change) * scale,
                    "alpha": alpha,
                    "donor_count": len(donors),
                }
            )
    return pd.DataFrame(rows)


def write_tables(
    dose: pd.DataFrame,
    tail: pd.DataFrame,
    access: pd.DataFrame,
    exposure_ci: pd.DataFrame,
    carrier: pd.DataFrame,
    ridge: pd.DataFrame,
) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)

    main_dose = dose[
        (dose["model"] == "airport_date_side_fe")
        & (dose["pressure"].isin(["avg_ops_per_hour", "share_above_28"]))
    ].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\small",
        r"\caption{Dose-response link between schedule pressure and reliability}",
        r"\label{tab:dose-response}",
        r"\begin{tabular}{@{}llrr@{}}",
        r"\toprule",
        r"Outcome & Pressure measure & Estimate & 95\% CI \\",
        r"\midrule",
    ]
    for _, row in main_dose.iterrows():
        unit = "pp" if row["unit"] == "pp" else "min/op"
        inc = "5 ops" if row["pressure"] == "avg_ops_per_hour" else "10 pp"
        estimate = f"{fmt(row['scaled_coef'])} {unit}"
        if row["scaled_coef"] > 0 and row["scaled_ci_low"] > 0:
            estimate = rf"\textbf{{{estimate}}}"
        lines.append(
            f"{row['outcome_label']} & {row['pressure_label']} ({inc}) & "
            f"{estimate} & "
            f"[{fmt(row['scaled_ci_low'])}, {fmt(row['scaled_ci_high'])}] \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\small Notes: Estimates come from airport-day-side models for facilitated hours with airport, calendar-date, and operation-side fixed effects. Pressure increments are five scheduled operations for P95 hourly pressure and ten percentage points for the share of hours above 28 scheduled operations. Positive estimates indicate higher reliability failures at higher schedule pressure.}",
            r"\end{table}",
        ]
    )
    (TABLES / "tab_dose_response.tex").write_text("\n".join(lines), encoding="utf-8")

    selected_tail = tail[tail["metric"].isin(["p95_delay_minutes", "delay60_rate", "cancel_or_delay60_rate"])].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\small",
        r"\caption{Tail reliability recovery from stress to late interim}",
        r"\label{tab:tail-reliability}",
        r"\begin{tabular}{@{}llrr@{}}",
        r"\toprule",
        r"Outcome & Side & Late-interim minus stress & 95\% CI \\",
        r"\midrule",
    ]
    for _, row in selected_tail.iterrows():
        unit = "pp" if row["unit"] == "pp" else "min"
        value = f"{fmt(row['scaled_late_minus_stress'])} {unit}"
        if row["scaled_late_minus_stress"] < 0:
            value = rf"\textbf{{{value}}}"
        lines.append(
            f"{row['metric_label']} & {row['side'].upper()} & {value} & "
            f"[{fmt(row['scaled_ci_low'])}, {fmt(row['scaled_ci_high'])}] \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\small Notes: Values are late-interim minus stress recovery contrasts from calendar-date fixed-effect phase models. Delay-60-plus and cancellation-or-60-plus values are percentage points. Lower values indicate fewer severe reliability failures.}",
            r"\end{table}",
        ]
    )
    (TABLES / "tab_tail_reliability.tex").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\small",
        r"\caption{Passenger-weighted market-access retention}",
        r"\label{tab:weighted-access}",
        r"\begin{tabular}{@{}llrrr@{}}",
        r"\toprule",
        r"Layer & Side & April markets & Passenger-weighted retention & Seat retention \\",
        r"\midrule",
    ]
    for _, row in access.iterrows():
        lines.append(
            f"{row['layer']} & {row['side'].upper()} & {int(row['april_markets'])} & "
            f"\\textbf{{{fmt(100 * row['passenger_weighted_market_retention'])}\\%}} & "
            f"\\textbf{{{fmt(100 * row['seat_retention_existing_april_markets'])}\\%}} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\small Notes: Passenger-weighted retention is the April passenger share in markets that remain active in June. Seat retention compares June seats with April seats within April markets. T-100 data are monthly access-context measures around the daily reliability window.}",
            r"\end{table}",
        ]
    )
    (TABLES / "tab_weighted_access.tex").write_text("\n".join(lines), encoding="utf-8")

    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\small",
        r"\caption{Passenger-time exposure accounting with bootstrap intervals}",
        r"\label{tab:passenger-time-bootstrap}",
        r"\begin{tabular}{@{}lrrr@{}}",
        r"\toprule",
        r"Side & Passenger-min/day reduction & 95\% interval & Passengers/flight \\",
        r"\midrule",
    ]
    for _, row in exposure_ci.iterrows():
        lines.append(
            f"{row['side'].upper()} & \\textbf{{{fmt(row['passenger_min_day_reduction'], 0)}}} & "
            f"[{fmt(row['ci_low'], 0)}, {fmt(row['ci_high'], 0)}] & {fmt(row['passengers_per_flight'])} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\small Notes: The interval resamples EWR stress and interim days with replacement and multiplies daily NAS-delay-minute reductions by April--June T-100 domestic passengers per performed segment. NAS means National Airspace System.}",
            r"\end{table}",
        ]
    )
    (TABLES / "tab_passenger_time_bootstrap.tex").write_text("\n".join(lines), encoding="utf-8")

    selected_carrier = carrier[
        (carrier["metric"].isin(["scheduled_ops", "delay15_rate", "nas_delay_per_scheduled_op"]))
        & (carrier["carrier_group"].isin(["United", "Other carriers"]))
    ].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\small",
        r"\caption{Carrier-group heterogeneity in schedule and reliability adjustment}",
        r"\label{tab:carrier-heterogeneity}",
        r"\begin{tabular}{@{}lllrrr@{}}",
        r"\toprule",
        r"Carrier group & Outcome & Side & EWR change & Control change & DID \\",
        r"\midrule",
    ]
    for _, row in selected_carrier.iterrows():
        value = fmt(row["scaled_did"])
        if row["carrier_group"] == "United" and row["metric"] == "scheduled_ops" and row["scaled_did"] < 0:
            value = rf"\textbf{{{value}}}"
        lines.append(
            f"{row['carrier_group']} & {row['metric_label']} & {row['side'].upper()} & "
            f"{fmt(row['scaled_ewr_change'])} & {fmt(row['scaled_control_change'])} & {value} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\small Notes: Changes compare stress with the interim period. DID is the EWR change minus the mean same-group change at the control airports. Cancellation and delay-15-plus values are percentage points. Bold values mark the largest schedule-burden evidence.}",
            r"\end{table}",
        ]
    )
    (TABLES / "tab_carrier_heterogeneity.tex").write_text("\n".join(lines), encoding="utf-8")

    selected_ridge = ridge[ridge["metric"].isin(["delay15_rate", "nas_delay_per_scheduled_op"])].copy()
    lines = [
        r"\begin{table}[!htbp]",
        r"\centering",
        r"\small",
        r"\caption{Ridge counterfactual recovery check}",
        r"\label{tab:ridge-counterfactual}",
        r"\begin{tabular}{@{}llrrr@{}}",
        r"\toprule",
        r"Outcome & Side & EWR change & Ridge change & Recovery gap \\",
        r"\midrule",
    ]
    for _, row in selected_ridge.iterrows():
        gap = fmt(row["scaled_recovery_gap"])
        if row["scaled_recovery_gap"] < 0:
            gap = rf"\textbf{{{gap}}}"
        lines.append(
            f"{row['metric_label']} & {row['side'].upper()} & "
            f"{fmt(row['observed_change'] * row['scale'])} & {fmt(row['ridge_change'] * row['scale'])} & {gap} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{2mm}",
            r"\parbox{0.94\linewidth}{\small Notes: The ridge counterfactual predicts EWR from donor-airport paths before May 20 and compares stress-to-interim changes. Lower values indicate stronger EWR recovery for delay outcomes.}",
            r"\end{table}",
        ]
    )
    (TABLES / "tab_ridge_counterfactual.tex").write_text("\n".join(lines), encoding="utf-8")


def write_summary(out_dir: Path, outputs: dict[str, pd.DataFrame]) -> None:
    lines = ["# TRA deep policy checks", ""]
    for name, frame in outputs.items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(frame.head(80).to_markdown(index=False, floatfmt=".4f"))
        lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260526)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = OUT_SMOKE if args.smoke else OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    daily = load_daily(args.smoke)
    airports = top_airports_from_daily(daily, args.smoke)
    dynamic = dynamic_event_study(daily)
    hourly = load_hourly(args.smoke)
    dose = dose_response_models(hourly, args.smoke)
    tail_daily, carrier_daily = build_flight_panels(airports, args.smoke)
    tail = tail_phase_checks(tail_daily)
    carrier = carrier_heterogeneity(carrier_daily)
    access = market_access_weighted()
    exposure_ci = passenger_time_bootstrap(daily, args.bootstrap_reps if not args.smoke else min(300, args.bootstrap_reps), args.seed)
    ridge = ridge_counterfactual(daily)

    outputs = {
        "dynamic_event_study": dynamic,
        "dose_response": dose,
        "tail_reliability": tail,
        "carrier_heterogeneity": carrier,
        "weighted_market_access": access,
        "passenger_time_bootstrap": exposure_ci,
        "ridge_counterfactual": ridge,
    }
    for name, frame in outputs.items():
        frame.to_csv(out_dir / f"{name}.csv", index=False)
    tail_daily.to_csv(out_dir / "tail_airport_side_daily.csv", index=False)
    carrier_daily.to_csv(out_dir / "carrier_group_airport_side_daily.csv", index=False)
    write_summary(out_dir, outputs)
    if not args.smoke:
        write_tables(dose, tail, access, exposure_ci, carrier, ridge)
    print(f"Wrote deep policy checks to {out_dir}")
    for name, frame in outputs.items():
        print(f"{name}: {len(frame)} rows")


if __name__ == "__main__":
    main()
