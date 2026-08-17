from __future__ import annotations

import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / "results" / "ewr_2025_full"
HOURLY_DIR = PROJECT_ROOT / "results" / "hourly_schedule_pressure"
DID_DIR = PROJECT_ROOT / "results" / "did_robustness"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures"
PREVIEW_DIR = PROJECT_ROOT / "results" / "figure_previews"


PERIODS = [
    {
        "key": "pre_20250101_0414",
        "label": "Baseline",
        "short": "Baseline",
        "start": "2025-01-01",
        "end": "2025-04-14",
        "color": "#6B7280",
    },
    {
        "key": "stress_20250415_0519",
        "label": "Construction and pre-order stress",
        "short": "Stress",
        "start": "2025-04-15",
        "end": "2025-05-19",
        "color": "#B91C1C",
    },
    {
        "key": "interim_20250520_0615",
        "label": "Interim order",
        "short": "Interim",
        "start": "2025-05-20",
        "end": "2025-06-15",
        "color": "#047857",
    },
    {
        "key": "cap_20250616_1025",
        "label": "Operating limit",
        "short": "Limit",
        "start": "2025-06-16",
        "end": "2025-10-25",
        "color": "#2563EB",
    },
    {
        "key": "extension_20251026_1231",
        "label": "Extension",
        "short": "Extension",
        "start": "2025-10-26",
        "end": "2025-12-31",
        "color": "#7C3AED",
    },
]

PERIOD_BY_KEY = {item["key"]: item for item in PERIODS}
CORE_PERIODS = [item["key"] for item in PERIODS]
PRESSURE_PERIODS = ["stress_20250415_0519", "interim_20250520_0615", "cap_20250616_1025"]


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
            "figure.titlesize": 11,
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


def add_event_context(ax: plt.Axes, show_spans: bool = True) -> None:
    if show_spans:
        for period in PERIODS:
            if period["key"] in {"stress_20250415_0519", "interim_20250520_0615"}:
                ax.axvspan(
                    pd.Timestamp(period["start"]),
                    pd.Timestamp(period["end"]),
                    color=period["color"],
                    alpha=0.07,
                    linewidth=0,
                    zorder=0,
                )
    for period in PERIODS[1:]:
        ax.axvline(
            pd.Timestamp(period["start"]),
            color="#374151",
            linewidth=0.8,
            linestyle="--",
            alpha=0.55,
            zorder=1,
        )


def make_daily_event_figure(daily: pd.DataFrame) -> None:
    ewr_arr = daily[(daily["airport"] == "EWR") & (daily["side"] == "arr")].copy()
    ewr_arr = ewr_arr.sort_values("FlightDate")
    metrics = [
        ("scheduled_ops", "(a)Scheduled arrivals", "flights/day", 1.0),
        ("cancel_rate", "(b)Cancellation rate", "%", 100.0),
        ("delay15_rate", "(c)Delay-15-plus rate", "%", 100.0),
        ("nas_delay_per_scheduled_op", "(d)NAS delay", "min/scheduled arrival", 1.0),
    ]

    fig, axes = plt.subplots(4, 1, figsize=(7.2, 8.4), sharex=True)
    line_color = "#111827"
    smooth_color = "#D97706"

    for ax, (metric, title, unit, scale) in zip(axes, metrics):
        values = ewr_arr[metric] * scale
        smooth = values.rolling(window=7, center=True, min_periods=1).mean()
        ax.plot(ewr_arr["FlightDate"], values, color=line_color, linewidth=0.7, alpha=0.35)
        ax.plot(ewr_arr["FlightDate"], smooth, color=smooth_color, linewidth=1.5)
        add_event_context(ax)
        ax.set_ylabel(unit)
        ax.set_title(title, loc="center", pad=4)

    fig.legend(
        handles=[
            Line2D([0], [0], color=line_color, lw=0.9, alpha=0.45, label="Daily"),
            Line2D([0], [0], color=smooth_color, lw=1.7, label="7-day mean"),
            Patch(facecolor="#B91C1C", alpha=0.10, label="Stress window"),
            Patch(facecolor="#047857", alpha=0.10, label="Interim order"),
        ],
        ncol=4,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
    )
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axes[-1].set_xlabel("2025")
    fig.tight_layout(rect=[0, 0.11, 1, 1])
    save_figure(fig, "fig_ewr_daily_event")


def make_hourly_pressure_figure(by_hour: pd.DataFrame) -> None:
    colors = {
        "stress_20250415_0519": "#B91C1C",
        "interim_20250520_0615": "#047857",
        "cap_20250616_1025": "#2563EB",
    }
    labels = {
        "stress_20250415_0519": "Stress",
        "interim_20250520_0615": "Interim order",
        "cap_20250616_1025": "Operating limit",
    }

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.8), sharey=True)
    for ax, side, panel_title in zip(axes, ["arr", "dep"], ["(a)Arrivals", "(b)Departures"]):
        for period in PRESSURE_PERIODS:
            data = by_hour[(by_hour["side"] == side) & (by_hour["period"] == period)].sort_values("hour")
            ax.plot(
                data["hour"],
                data["avg_ops"],
                color=colors[period],
                linewidth=1.8,
                marker="o",
                markersize=3.5,
                label=labels[period],
            )
        ax.axhline(28, color="#111827", linewidth=0.8, linestyle="--", alpha=0.75)
        ax.axhline(34, color="#6B7280", linewidth=0.8, linestyle=":", alpha=0.9)
        ax.set_title(panel_title, loc="center")
        ax.set_xlabel("Scheduled local hour")
        ax.set_xticks([6, 9, 12, 15, 18, 21])
    axes[0].set_ylabel("Mean scheduled operations/hour")
    handles, labels_out = axes[0].get_legend_handles_labels()
    handles.extend(
        [
            Line2D([0], [0], color="#111827", lw=0.8, linestyle="--", label="28 target"),
            Line2D([0], [0], color="#6B7280", lw=0.8, linestyle=":", label="34 target"),
        ]
    )
    fig.legend(handles=handles, ncol=5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 0.03))
    fig.tight_layout(rect=[0, 0.22, 1, 1])
    save_figure(fig, "fig_hourly_schedule_pressure")


def make_did_figure(did: pd.DataFrame) -> None:
    main = did[did["window"] == "main"].copy()
    placebo = did[did["window"] == "pre_stress_placebo"][["side", "metric", "coef"]].rename(
        columns={"coef": "placebo_coef"}
    )
    data = main.merge(placebo, on=["side", "metric"], how="left")
    specs = [
        ("scheduled_ops", "(a)Scheduled operations", "ops/day", 1.0),
        ("cancel_rate", "(b)Cancellation rate", "percentage points", 100.0),
        ("delay15_rate", "(c)Delay-15-plus rate", "percentage points", 100.0),
        ("nas_delay_per_scheduled_op", "(d)NAS delay", "min/scheduled op", 1.0),
    ]
    side_order = ["arr", "dep"]
    side_labels = {"arr": "Arrivals", "dep": "Departures"}
    colors = {"arr": "#2563EB", "dep": "#047857"}
    label_box = {
        "boxstyle": "round,pad=0.12",
        "facecolor": "white",
        "edgecolor": "none",
        "alpha": 0.88,
    }

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))
    for ax, (metric, title, xlabel, scale) in zip(axes.ravel(), specs):
        subset = data[data["metric"] == metric].set_index("side").reindex(side_order)
        y = [1, 0]
        coef = subset["coef"] * scale
        ci_low = subset["ci_low"] * scale
        ci_high = subset["ci_high"] * scale
        placebo_vals = subset["placebo_coef"] * scale
        for idx, side in enumerate(side_order):
            value = coef.loc[side]
            lo = ci_low.loc[side]
            hi = ci_high.loc[side]
            ax.errorbar(
                value,
                y[idx],
                xerr=[[value - lo], [hi - value]],
                fmt="o",
                color=colors[side],
                ecolor=colors[side],
                elinewidth=1.1,
                capsize=3,
                markersize=5,
            )
            ax.scatter(
                placebo_vals.loc[side],
                y[idx] - 0.18,
                marker="x",
                color="#6B7280",
                s=28,
                zorder=4,
            )
            ax.annotate(
                f"{value:.1f}",
                xy=(value, y[idx]),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7.4,
                color=colors[side],
                bbox=label_box,
                clip_on=True,
                zorder=5,
            )
            ax.annotate(
                f"{placebo_vals.loc[side]:.1f}",
                xy=(placebo_vals.loc[side], y[idx] - 0.18),
                xytext=(7, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=7.2,
                color="#4B5563",
                bbox=label_box,
                clip_on=True,
                zorder=5,
            )
        x_values = list(coef) + list(ci_low) + list(ci_high) + list(placebo_vals) + [0]
        x_min = min(x_values)
        x_max = max(x_values)
        x_span = max(x_max - x_min, 1.0)
        ax.set_xlim(x_min - 0.08 * x_span, x_max + 0.18 * x_span)
        ax.set_ylim(-0.42, 1.24)
        ax.axvline(0, color="#111827", linewidth=0.8)
        ax.set_yticks(y)
        ax.set_yticklabels([side_labels[side] for side in side_order])
        ax.set_title(title, loc="center")
        ax.set_xlabel(xlabel)
    fig.legend(
        handles=[
            Line2D([0], [0], marker="o", color="#111827", lw=0, label="Main DID"),
            Line2D([0], [0], marker="x", color="#6B7280", lw=0, label="Pre-stress placebo"),
        ],
        ncol=2,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.025),
    )
    fig.tight_layout(rect=[0, 0.14, 1, 1])
    save_figure(fig, "fig_did_robustness")


def write_manifest() -> None:
    files = [
        "fig_ewr_daily_event.pdf",
        "fig_hourly_schedule_pressure.pdf",
        "fig_did_robustness.pdf",
    ]
    manifest = {
        "source_results": {
            "daily": str(RESULT_DIR.name),
            "hourly": str(HOURLY_DIR.name),
            "did": str(DID_DIR.name),
        },
        "figures": files,
        "previews": [file.replace(".pdf", ".png") for file in files],
        "note": "Data figures are generated from existing result CSVs and do not rerun the full analysis.",
    }
    (PREVIEW_DIR / "figure_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    setup_style()
    ensure_dirs()
    daily = pd.read_csv(RESULT_DIR / "airport_side_daily.csv", parse_dates=["FlightDate"])
    by_hour = pd.read_csv(HOURLY_DIR / "hourly_schedule_pressure_by_hour.csv")
    did = pd.read_csv(DID_DIR / "did_robustness.csv")
    make_daily_event_figure(daily)
    make_hourly_pressure_figure(by_hour)
    make_did_figure(did)
    write_manifest()
    print(f"Wrote manuscript figures to {FIGURE_DIR}")
    print(f"Wrote previews to {PREVIEW_DIR}")


if __name__ == "__main__":
    main()
