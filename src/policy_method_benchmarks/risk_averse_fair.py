from __future__ import annotations

import numpy as np
import pandas as pd

from .common import MethodMetadata, minmax, risk_scenarios, weight_draws


METADATA = MethodMetadata(
    method_id="risk_averse_fair",
    family="Risk-averse and fair allocation",
    source="Sun, Deng, Wei, and Xie",
    venue="Naval Research Logistics",
    year=2024,
    doi="10.1002/nav.22217",
    reproduced_components="scenario uncertainty, upper-tail risk, and an explicit fairness term",
    airport_adaptation="observed capacity regimes replace vertiport resource bundles; access and carrier burden define fairness loss",
    output_type="risk-adjusted decision",
    decision_limit="the selected regime depends on risk and fairness penalty weights and does not enforce separate access floors",
)


def run(
    frame: pd.DataFrame,
    draws: int = 20_000,
    seed: int = 20260817,
    alpha: float = 0.95,
    risk_weight: float = 0.45,
    fairness_weight: float = 0.25,
) -> pd.DataFrame:
    scenarios = risk_scenarios(frame, draws=draws, seed=seed)
    tail_start = max(int(np.floor(alpha * draws)), 0)
    cvar = scenarios.apply(lambda x: np.sort(x.to_numpy())[tail_start:].mean())
    service = pd.Series(minmax(frame["service"], True), index=frame["phase"])
    cvar_score = pd.Series(minmax(cvar, False), index=frame["phase"])
    access_loss = frame[["domestic_access_loss", "international_access_loss"]].max(axis=1)
    fairness_loss = access_loss + frame["combined_burden_index"]
    fairness = pd.Series(minmax(fairness_loss, False), index=frame["phase"])
    score = (
        (1.0 - risk_weight - fairness_weight) * service
        + risk_weight * cvar_score
        + fairness_weight * fairness
    )
    components = pd.DataFrame(
        {
            "service": service.to_numpy(),
            "tail_reliability": cvar_score.to_numpy(),
            "fairness": fairness.to_numpy(),
        }
    )
    sensitivity = weight_draws(list(components.columns), min(draws, 5_000), seed + 1)
    winner_count = np.zeros(len(frame), dtype=int)
    for weights in sensitivity.to_numpy():
        candidate_score = components.to_numpy() @ weights
        winner_count[int(np.argmax(candidate_score))] += 1
    result = pd.DataFrame(
        {
            "phase": frame["phase"],
            "score": score.to_numpy(),
            "cvar95": cvar.to_numpy(),
            "fairness_loss": fairness_loss.to_numpy(),
            "winner_probability": winner_count / len(sensitivity),
        }
    )
    result["rank"] = result["score"].rank(ascending=False, method="min").astype(int)
    return result.sort_values(["rank", "phase"]).reset_index(drop=True)
