from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from policy_method_benchmarks import (
    cocofiso,
    equity_efficiency_frontier,
    feasibility_sequence,
    risk_averse_fair,
    series_sbm_dea,
    znumber_network_dea,
)
from policy_method_benchmarks.common import ROOT, load_regimes


METHODS = [
    risk_averse_fair,
    znumber_network_dea,
    series_sbm_dea,
    cocofiso,
    equity_efficiency_frontier,
    feasibility_sequence,
]


def run(smoke: bool, seed: int) -> Path:
    frame = load_regimes()
    out_dir = ROOT / "results" / ("policy_method_benchmarks_smoke" if smoke else "policy_method_benchmarks")
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    fidelity_rows = []
    audit_rows = []
    for module in METHODS:
        kwargs = {}
        if module is risk_averse_fair:
            kwargs = {"draws": 500 if smoke else 20_000, "seed": seed}
        elif module in {cocofiso, feasibility_sequence}:
            kwargs = {"sensitivity_draws": 200 if smoke else 5_000, "seed": seed}
        result = module.run(frame.copy(), **kwargs)
        result.to_csv(out_dir / f"{module.METADATA.method_id}.csv", index=False)
        top_rank = result["rank"].min()
        top = result.loc[result["rank"].eq(top_rank)].sort_values("phase")
        winner = top.iloc[0]
        unique = len(top) == 1
        selected_phase = winner["phase"] if unique else "non_unique"
        summary_rows.append(
            {
                "method_id": module.METADATA.method_id,
                "family": module.METADATA.family,
                "venue": module.METADATA.venue,
                "year": module.METADATA.year,
                "doi": module.METADATA.doi,
                "selected_phase": selected_phase,
                "top_rank_set": ";".join(top["phase"]),
                "unique_selection": unique,
                "selected_score": winner["score"],
            }
        )
        top_metrics = frame.loc[frame["phase"].isin(top["phase"])].copy()
        top_metrics["passes"] = (
            (top_metrics["risk_high"] <= 0.75)
            & (top_metrics["domestic_retention"] >= 0.997)
            & (top_metrics["international_retention"] >= 0.983)
            & (top_metrics["combined_burden_index"] <= 0.05)
        )
        unsafe_probability = None
        if "winner_probability" in result.columns:
            safe_lookup = frame.set_index("phase").assign(
                passes=lambda x: (
                    (x["risk_high"] <= 0.75)
                    & (x["domestic_retention"] >= 0.997)
                    & (x["international_retention"] >= 0.983)
                    & (x["combined_burden_index"] <= 0.05)
                )
            )["passes"]
            unsafe_probability = float(
                result.loc[
                    ~result["phase"].map(safe_lookup).astype(bool), "winner_probability"
                ].sum()
            )
        audit_rows.append(
            {
                "method_id": module.METADATA.method_id,
                "selected_phase": selected_phase,
                "top_rank_set": ";".join(top["phase"]),
                "top_set_size": len(top),
                "safe_share_in_top_set": float(top_metrics["passes"].mean()),
                "unsafe_winner_probability": unsafe_probability,
                "all_top_regimes_pass_balanced_bounds": bool(top_metrics["passes"].all()),
            }
        )
        fidelity_rows.append(module.METADATA.__dict__)
    proposed = frame.loc[
        (frame["risk_high"] <= 0.75)
        & (frame["domestic_retention"] >= 0.997)
        & (frame["international_retention"] >= 0.983)
        & (frame["combined_burden_index"] <= 0.05)
    ].sort_values(["service", "risk_index"], ascending=[False, True])
    if proposed.empty:
        raise RuntimeError("The balanced governance scenario has no eligible regime")
    selected = proposed.iloc[0]
    audit_rows.append(
        {
            "method_id": "observed_regime_governance_rule",
            "selected_phase": selected["phase"],
            "top_rank_set": selected["phase"],
            "top_set_size": 1,
            "safe_share_in_top_set": 1.0,
            "unsafe_winner_probability": 0.0,
            "all_top_regimes_pass_balanced_bounds": True,
        }
    )
    pd.DataFrame(summary_rows).to_csv(out_dir / "benchmark_summary.csv", index=False)
    pd.DataFrame(fidelity_rows).to_csv(out_dir / "implementation_fidelity.csv", index=False)
    pd.DataFrame(audit_rows).to_csv(out_dir / "selected_policy_audit.csv", index=False)
    manifest = {
        "smoke": smoke,
        "seed": seed,
        "methods": len(METHODS),
        "input_rows": len(frame),
        "outputs": [module.METADATA.method_id for module in METHODS],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--seed", type=int, default=20260817)
    args = parser.parse_args()
    out_dir = run(args.smoke, args.seed)
    print(out_dir)


if __name__ == "__main__":
    main()
