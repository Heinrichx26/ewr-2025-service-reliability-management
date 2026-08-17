from __future__ import annotations

import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / "results" / "ewr_2025_full"
DID_DIR = PROJECT_ROOT / "results" / "did_robustness"
CAL_PLACEBO_DIR = PROJECT_ROOT / "results" / "calendar_placebo_2024"
TRA_DIR = PROJECT_ROOT / "results" / "tra_policy_experiments"
DEEP_DIR = PROJECT_ROOT / "results" / "tra_deep_policy_checks"
INTL_DIR = PROJECT_ROOT / "results" / "tra_t100_international_exposure"
ARTICLE_FIGURE_DIR = PROJECT_ROOT / "article" / "elsarticle" / "figures"
PREVIEW_DIR = PROJECT_ROOT / "results" / "figure_previews"
FIGURE_DIR = ARTICLE_FIGURE_DIR if ARTICLE_FIGURE_DIR.exists() else PREVIEW_DIR


PERIODS = [
    ("Stress", "2025-04-15", "2025-05-19", "#B91C1C"),
    ("Interim order", "2025-05-20", "2025-06-15", "#047857"),
]


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#E5E7EB",
            "grid.linewidth": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def ensure_dirs() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


def save_figure(fig: plt.Figure, stem: str) -> None:
    pdf_path = FIGURE_DIR / f"{stem}.pdf"
    png_path = PREVIEW_DIR / f"{stem}.png"
    fig.savefig(pdf_path, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(png_path, dpi=180, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def add_policy_windows(ax: plt.Axes) -> None:
    for label, start, end, color in PERIODS:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=color, alpha=0.07, linewidth=0)
        ax.axvline(pd.Timestamp(start), color="#374151", linewidth=0.8, linestyle="--", alpha=0.55)
    ax.axvline(pd.Timestamp("2025-06-16"), color="#374151", linewidth=0.8, linestyle="--", alpha=0.55)


def make_daily_event_figure(daily: pd.DataFrame) -> None:
    ewr_arr = daily[(daily["airport"] == "EWR") & (daily["side"] == "arr")].sort_values("FlightDate")
    metrics = [
        ("scheduled_ops", "(a)Scheduled arrivals", "flights/day", 1.0),
        ("cancel_rate", "(b)Cancellation rate", "%", 100.0),
        ("delay15_rate", "(c)Delay-15-plus rate", "%", 100.0),
        ("nas_delay_per_scheduled_op", "(d)NAS delay", "min/scheduled arrival", 1.0),
    ]
    fig, axes = plt.subplots(4, 1, figsize=(7.2, 8.2), sharex=True)
    daily_color = "#111827"
    mean_color = "#D97706"
    for ax, (metric, title, ylabel, scale) in zip(axes, metrics):
        series = ewr_arr[metric] * scale
        ax.plot(ewr_arr["FlightDate"], series, color=daily_color, linewidth=0.7, alpha=0.32)
        ax.plot(
            ewr_arr["FlightDate"],
            series.rolling(7, center=True, min_periods=1).mean(),
            color=mean_color,
            linewidth=1.5,
        )
        add_policy_windows(ax)
        ax.set_title(title, loc="center", pad=4)
        ax.set_ylabel(ylabel)
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[-1].set_xlabel("2025")
    fig.legend(
        handles=[
            Line2D([0], [0], color=daily_color, lw=0.9, alpha=0.45, label="Daily"),
            Line2D([0], [0], color=mean_color, lw=1.7, label="7-day mean"),
            Patch(facecolor="#B91C1C", alpha=0.10, label="Stress window"),
            Patch(facecolor="#047857", alpha=0.10, label="Interim order"),
        ],
        ncol=4,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
    )
    fig.tight_layout(rect=[0, 0.11, 1, 1])
    save_figure(fig, "fig_ewr_daily_event")


def make_dynamic_event_study_figure(dynamic: pd.DataFrame) -> None:
    specs = [
        ("scheduled_ops", "(a)Scheduled operations", "flights/day"),
        ("cancel_rate", "(b)Cancellation rate", "percentage points"),
        ("delay15_rate", "(c)Delay-15-plus rate", "percentage points"),
        ("nas_delay_per_scheduled_op", "(d)NAS delay", "min/scheduled op"),
    ]
    side_style = {
        "arr": ("Arrivals", "#2563EB", "-"),
        "dep": ("Departures", "#047857", "--"),
    }
    fig, axes = plt.subplots(4, 1, figsize=(7.2, 7.6), sharex=True)
    for ax, (metric, title, ylabel) in zip(axes, specs):
        data = dynamic[dynamic["metric"] == metric].copy()
        for side, (label, color, linestyle) in side_style.items():
            side_data = data[data["side"] == side].sort_values("FlightDate")
            ax.plot(
                side_data["FlightDate"],
                side_data["dynamic_contrast_scaled"],
                color=color,
                linewidth=0.8,
                alpha=0.22,
            )
            ax.plot(
                side_data["FlightDate"],
                side_data["dynamic_contrast_scaled"].rolling(5, center=True, min_periods=1).mean(),
                color=color,
                linewidth=1.35,
                linestyle=linestyle,
                label=label,
            )
        ax.axhline(0, color="#111827", linewidth=0.75)
        ax.axvline(pd.Timestamp("2025-04-15"), color="#B91C1C", linewidth=0.95, linestyle="--")
        ax.axvline(pd.Timestamp("2025-05-20"), color="#047857", linewidth=0.95, linestyle="--")
        ax.axvspan(pd.Timestamp("2025-04-15"), pd.Timestamp("2025-05-19"), color="#B91C1C", alpha=0.06, linewidth=0)
        ax.axvspan(pd.Timestamp("2025-05-20"), pd.Timestamp("2025-06-15"), color="#047857", alpha=0.06, linewidth=0)
        ax.set_title(title, loc="center", pad=4)
        ax.set_ylabel(ylabel)
    axes[-1].xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    axes[-1].set_xlabel("2025")
    fig.legend(
        handles=[
            Line2D([0], [0], color="#2563EB", lw=1.35, label="Arrivals"),
            Line2D([0], [0], color="#047857", lw=1.35, linestyle="--", label="Departures"),
            Line2D([0], [0], color="#B91C1C", lw=0.95, linestyle="--", label="Apr 15"),
            Line2D([0], [0], color="#047857", lw=0.95, linestyle="--", label="May 20"),
        ],
        ncol=4,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
    )
    fig.tight_layout(rect=[0, 0.10, 1, 1])
    save_figure(fig, "fig_dynamic_event_study")


def make_synthetic_figure(paths: pd.DataFrame, summary: pd.DataFrame) -> None:
    specs = [
        ("arr", "delay15_rate", "(a)Arrival delay-15-plus rate", "%", 100.0),
        ("arr", "nas_delay_per_scheduled_op", "(b)Arrival NAS delay", "min/scheduled arrival", 1.0),
        ("dep", "delay15_rate", "(c)Departure delay-15-plus rate", "%", 100.0),
        ("dep", "nas_delay_per_scheduled_op", "(d)Departure NAS delay", "min/scheduled departure", 1.0),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.6), sharex=True)
    for ax, (side, metric, title, ylabel, scale) in zip(axes.ravel(), specs):
        data = paths[(paths["side"] == side) & (paths["metric"] == metric)].sort_values("FlightDate")
        ax.plot(data["FlightDate"], data["observed"] * scale, color="#111827", linewidth=1.2, label="EWR")
        ax.plot(data["FlightDate"], data["synthetic"] * scale, color="#2563EB", linewidth=1.2, linestyle="--", label="Synthetic EWR")
        add_policy_windows(ax)
        row = summary[(summary["side"] == side) & (summary["metric"] == metric)].iloc[0]
        gap = row["recovery_gap"] * scale
        unit = "pp" if scale == 100.0 else "min/op"
        ax.text(
            0.02,
            0.92,
            f"Recovery gap: {gap:.1f} {unit}",
            transform=ax.transAxes,
            fontsize=8,
            color="#111827",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.5},
        )
        ax.set_title(title, loc="center")
        ax.set_ylabel(ylabel)
    axes[-1, 0].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[-1, 0].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[-1, 1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[-1, 1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.legend(
        handles=[
            Line2D([0], [0], color="#111827", lw=1.2, label="EWR"),
            Line2D([0], [0], color="#2563EB", lw=1.2, linestyle="--", label="Synthetic EWR"),
            Patch(facecolor="#B91C1C", alpha=0.10, label="Stress window"),
            Patch(facecolor="#047857", alpha=0.10, label="Interim order"),
        ],
        ncol=4,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.03),
    )
    fig.tight_layout(rect=[0, 0.12, 1, 1])
    save_figure(fig, "fig_synthetic_reliability")


def make_access_exposure_figure(
    t100_summary: pd.DataFrame,
    carrier_summary: pd.DataFrame,
    international_summary: pd.DataFrame,
    international_carrier: pd.DataFrame,
    externality: pd.DataFrame,
) -> None:
    side_labels = {"arr": "Arrivals", "dep": "Departures"}
    colors = {"arr": "#2563EB", "dep": "#047857", "United": "#7C3AED", "Other carriers": "#6B7280"}

    def exposure_panel(ax: plt.Axes, summary: pd.DataFrame, title: str, upper: float | None = None) -> None:
        width = 0.32
        x = np.arange(2)
        max_val = 0.0
        for i, side in enumerate(["arr", "dep"]):
            row = summary[summary["side"] == side].iloc[0]
            vals = [row["seat_retention_apr_to_jun"] * 100, row["passenger_retention_apr_to_jun"] * 100]
            max_val = max(max_val, max(vals))
            pos = x + (i - 0.5) * width
            ax.bar(pos, vals, width=width, color=colors[side], label=side_labels[side])
            for p, v in zip(pos, vals):
                ax.text(p, v + 1.0, f"{v:.1f}", ha="center", va="bottom", fontsize=7.2)
        ax.set_xticks(x)
        ax.set_xticklabels(["Seats", "Passengers"])
        ax.set_ylim(0, upper if upper else max_val + 13)
        ax.set_ylabel("April-to-June retention (%)")
        ax.set_title(title, loc="center", pad=4)

    def route_panel(ax: plt.Axes, summary: pd.DataFrame, title: str) -> None:
        vals = []
        for side in ["arr", "dep"]:
            row = summary[summary["side"] == side].iloc[0]
            vals.append(row["route_retention_apr_to_jun"] * 100)
        ax.bar([0, 1], vals, color=[colors["arr"], colors["dep"]], width=0.55)
        for p, v in zip([0, 1], vals):
            ax.text(p, v + 1.0, f"{v:.1f}", ha="center", va="bottom", fontsize=7.2)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Arrivals", "Departures"])
        ax.set_ylim(0, max(vals) + 14)
        ax.set_ylabel("Route ratio (%)")
        ax.set_title(title, loc="center", pad=4)

    def carrier_panel(ax: plt.Axes, carrier: pd.DataFrame, title: str) -> None:
        width = 0.32
        pivot = carrier.pivot_table(
            index="carrier_group",
            columns="side",
            values="seat_change_apr_to_jun",
            aggfunc="first",
        ).reindex(["United", "Other carriers"])
        x = np.arange(len(pivot.index))
        vals_all = []
        for i, side in enumerate(["arr", "dep"]):
            vals = pivot[side].to_numpy(dtype=float) / 1000
            vals_all.extend(vals.tolist())
            pos = x + (i - 0.5) * width
            ax.bar(pos, vals, width=width, color=colors[side], label=side_labels[side])
            for p, v in zip(pos, vals):
                if v < 0:
                    ax.text(p, v * 0.50, f"{v:.1f}", ha="center", va="center", fontsize=7.2, rotation=90, color="white")
                else:
                    ax.text(p, v + 0.06 * max(1.0, max(vals_all)), f"{v:.1f}", ha="center", va="bottom", fontsize=7.2)
        low = min(vals_all + [0])
        high = max(vals_all + [0])
        span = max(high - low, 10.0)
        ax.axhline(0, color="#111827", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(["United", "Other"])
        ax.set_ylim(low - 0.16 * span, high + 0.22 * span)
        ax.set_ylabel("Seat change (thousand)")
        ax.set_title(title, loc="center", pad=4)

    fig_domestic, axes_domestic = plt.subplots(1, 3, figsize=(7.3, 2.85))
    exposure_panel(axes_domestic[0], t100_summary, "(a)Domestic exposure", upper=112)
    route_panel(axes_domestic[1], t100_summary, "(b)Domestic route access")
    carrier_panel(axes_domestic[2], carrier_summary, "(c)Domestic carrier burden")
    handles, labels = axes_domestic[0].get_legend_handles_labels()
    fig_domestic.legend(handles, labels, ncol=2, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 0.00))
    fig_domestic.tight_layout(rect=[0, 0.12, 1, 1], w_pad=1.0)
    save_figure(fig_domestic, "fig_domestic_access_exposure")

    fig_international, axes_international = plt.subplots(1, 3, figsize=(7.3, 2.85))
    exposure_panel(axes_international[0], international_summary, "(a)International exposure", upper=122)
    route_panel(axes_international[1], international_summary, "(b)International route access")
    carrier_panel(axes_international[2], international_carrier, "(c)International carrier exposure")
    handles, labels = axes_international[0].get_legend_handles_labels()
    fig_international.legend(handles, labels, ncol=2, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 0.00))
    fig_international.tight_layout(rect=[0, 0.12, 1, 1], w_pad=1.0)
    save_figure(fig_international, "fig_international_access_exposure")


def make_policy_robustness_figure(did: pd.DataFrame, calendar_2024: pd.DataFrame, synthetic: pd.DataFrame) -> None:
    metrics = [
        ("delay15_rate", "(a)Delay-15-plus recovery", "percentage points", 100.0),
        ("nas_delay_per_scheduled_op", "(b)NAS-delay recovery", "min/scheduled op", 1.0),
    ]
    labels = ["DID", "Pre-stress placebo", "2024 placebo", "Synthetic recovery"]
    colors = ["#111827", "#6B7280", "#9CA3AF", "#2563EB"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6))
    for ax, (metric, title, xlabel, scale) in zip(axes, metrics):
        rows = []
        for side in ["arr", "dep"]:
            did_main = did[(did["window"] == "main") & (did["side"] == side) & (did["metric"] == metric)]["coef"].iloc[0]
            did_placebo = did[(did["window"] == "pre_stress_placebo") & (did["side"] == side) & (did["metric"] == metric)]["coef"].iloc[0]
            cal = calendar_2024[(calendar_2024["side"] == side) & (calendar_2024["metric"] == metric)]["coef"].iloc[0]
            syn = synthetic[(synthetic["side"] == side) & (synthetic["metric"] == metric)]["recovery_gap"].iloc[0]
            rows.append((side.upper(), [did_main * scale, did_placebo * scale, cal * scale, syn * scale]))
        y_base = np.array([1.1, 0.25])
        for side_i, (side_label, vals) in enumerate(rows):
            for j, val in enumerate(vals):
                y = y_base[side_i] + (j - 1.5) * 0.11
                ax.scatter(val, y, color=colors[j], s=28, zorder=4)
                ax.text(
                    val,
                    y + 0.055,
                    f"{val:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=7.0,
                    color=colors[j],
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 0.8},
                )
        x_values = [v for _, vals in rows for v in vals] + [0]
        span = max(x_values) - min(x_values)
        span = span if span > 1 else 1
        ax.set_xlim(min(x_values) - 0.12 * span, max(x_values) + 0.20 * span)
        ax.axvline(0, color="#111827", linewidth=0.8)
        ax.set_yticks(y_base)
        ax.set_yticklabels(["ARR", "DEP"])
        ax.set_title(title, loc="center")
        ax.set_xlabel(xlabel)
    fig.legend(
        handles=[Line2D([0], [0], marker="o", color=c, lw=0, label=l) for c, l in zip(colors, labels)],
        ncol=4,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.04),
    )
    fig.tight_layout(rect=[0, 0.18, 1, 1])
    save_figure(fig, "fig_policy_robustness")


def make_synthetic_diagnostic_figure(paths: pd.DataFrame, placebo: pd.DataFrame, summary: pd.DataFrame) -> None:
    specs = [
        ("arr", "delay15_rate", "(a)ARR delay-15-plus pre-fit", "%", 100.0),
        ("arr", "nas_delay_per_scheduled_op", "(b)ARR NAS pre-fit", "min/op", 1.0),
        ("dep", "delay15_rate", "(c)DEP delay-15-plus placebo", "recovery gap (pp)", 100.0),
        ("dep", "nas_delay_per_scheduled_op", "(d)DEP NAS placebo", "recovery gap (min/op)", 1.0),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))
    pre_end = pd.Timestamp("2025-05-19")
    for ax, (side, metric, title, ylabel, scale) in zip(axes.ravel()[:2], specs[:2]):
        data = paths[(paths["side"] == side) & (paths["metric"] == metric) & (paths["FlightDate"] <= pre_end)].sort_values("FlightDate")
        ax.plot(data["FlightDate"], data["observed"] * scale, color="#111827", linewidth=1.1, label="EWR")
        ax.plot(data["FlightDate"], data["synthetic"] * scale, color="#2563EB", linewidth=1.1, linestyle="--", label="Synthetic EWR")
        ax.axvspan(pd.Timestamp("2025-04-15"), pd.Timestamp("2025-05-19"), color="#B91C1C", alpha=0.07, linewidth=0)
        row = summary[(summary["side"] == side) & (summary["metric"] == metric)].iloc[0]
        rmspe = row["pre_rmse"] * scale
        unit = "pp" if scale == 100.0 else "min/op"
        ax.text(
            0.02,
            0.90,
            f"Pre-RMSPE: {rmspe:.1f} {unit}",
            transform=ax.transAxes,
            fontsize=8,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.5},
        )
        ax.set_title(title, loc="center")
        ax.set_ylabel(ylabel)
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    for ax, (side, metric, title, xlabel, scale) in zip(axes.ravel()[2:], specs[2:]):
        group = placebo[(placebo["side"] == side) & (placebo["metric"] == metric)].copy()
        group["gap_scaled"] = group["recovery_gap"] * scale
        ewr = group[group["treated_airport"] == "EWR"].iloc[0]
        ax.hist(group["gap_scaled"], bins=16, color="#D1D5DB", edgecolor="white")
        ewr_gap = ewr["gap_scaled"]
        ax.axvline(ewr_gap, color="#2563EB", linewidth=1.6)
        ax.text(
            ewr_gap,
            ax.get_ylim()[1] * 0.92,
            f"EWR {ewr_gap:.1f}\nrank {int(ewr['rank_recovery_most_negative'])}/{int(ewr['airports'])}",
            ha="left" if ewr_gap < group["gap_scaled"].median() else "right",
            va="top",
            fontsize=8,
            color="#2563EB",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.5},
        )
        ax.axvline(0, color="#111827", linewidth=0.8)
        ax.set_title(title, loc="center")
        ax.set_xlabel(xlabel)
        ax.set_ylabel("donor airports")
    fig.legend(
        handles=[
            Line2D([0], [0], color="#111827", lw=1.1, label="EWR"),
            Line2D([0], [0], color="#2563EB", lw=1.1, linestyle="--", label="Synthetic EWR"),
            Patch(facecolor="#B91C1C", alpha=0.10, label="Stress window"),
            Line2D([0], [0], color="#2563EB", lw=1.6, label="EWR placebo rank"),
        ],
        ncol=4,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.03),
    )
    fig.tight_layout(rect=[0, 0.13, 1, 1])
    save_figure(fig, "fig_synthetic_diagnostics")


def write_manifest() -> None:
    files = [
        "fig_policy_timeline.pdf",
        "fig_dynamic_event_study.pdf",
        "fig_ewr_daily_event.pdf",
        "fig_synthetic_reliability.pdf",
        "fig_synthetic_diagnostics.pdf",
        "fig_domestic_access_exposure.pdf",
        "fig_international_access_exposure.pdf",
        "fig_policy_robustness.pdf",
    ]
    manifest = {
        "source_results": {
            "daily": str(RESULT_DIR.name),
            "did": str(DID_DIR.name),
            "tra_policy": str(TRA_DIR.name),
        },
        "figures": files,
        "previews": [file.replace(".pdf", ".png") for file in files],
        "note": "Data figures are generated from existing result CSVs and do not rerun the full analysis.",
    }
    (PREVIEW_DIR / "tra_figure_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    setup_style()
    ensure_dirs()
    daily = pd.read_csv(RESULT_DIR / "airport_side_daily.csv", parse_dates=["FlightDate"])
    dynamic = pd.read_csv(DEEP_DIR / "dynamic_event_study.csv", parse_dates=["FlightDate"])
    paths = pd.read_csv(TRA_DIR / "synthetic_control_paths.csv", parse_dates=["FlightDate"])
    synthetic = pd.read_csv(TRA_DIR / "synthetic_control_summary.csv")
    placebo = pd.read_csv(TRA_DIR / "synthetic_control_placebos.csv")
    t100_summary = pd.read_csv(TRA_DIR / "t100_policy_exposure_summary.csv")
    carrier_summary = pd.read_csv(TRA_DIR / "t100_carrier_policy_summary.csv")
    international_summary = pd.read_csv(INTL_DIR / "t100_international_policy_summary.csv")
    international_summary = international_summary[international_summary["year"] == 2025].copy()
    international_carrier = pd.read_csv(INTL_DIR / "t100_international_carrier_policy_summary.csv")
    international_carrier = international_carrier[international_carrier["year"] == 2025].copy()
    externality = pd.read_csv(TRA_DIR / "delay_exposure_accounting.csv")
    did = pd.read_csv(DID_DIR / "did_robustness.csv")
    calendar_2024 = pd.read_csv(CAL_PLACEBO_DIR / "calendar_placebo_2024_did.csv")

    make_daily_event_figure(daily)
    make_dynamic_event_study_figure(dynamic)
    make_synthetic_figure(paths, synthetic)
    make_synthetic_diagnostic_figure(paths, placebo, synthetic)
    make_access_exposure_figure(t100_summary, carrier_summary, international_summary, international_carrier, externality)
    make_policy_robustness_figure(did, calendar_2024, synthetic)
    write_manifest()
    print(f"Wrote TRA figures to {FIGURE_DIR}")
    print(f"Wrote previews to {PREVIEW_DIR}")


if __name__ == "__main__":
    main()
