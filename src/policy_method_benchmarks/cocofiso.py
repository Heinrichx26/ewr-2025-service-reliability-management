from __future__ import annotations

import numpy as np
import pandas as pd

from .common import MethodMetadata, weight_draws


METADATA = MethodMetadata(
    method_id="cocofiso",
    family="Multi-criteria compromise decision support",
    source="Rasoanaivo et al.",
    venue="Expert Systems with Applications",
    year=2024,
    doi="10.1016/j.eswa.2024.124079",
    reproduced_components="TOPSIS vector normalization, additive and multiplicative comparability sequences, and three compromise aggregations",
    airport_adaptation="capacity regimes are alternatives and the five governance outcomes are criteria",
    output_type="compromise ranking",
    decision_limit="criterion compensation can rank a regime first even when one governance bound is violated",
)


def _score(matrix: np.ndarray, weights: np.ndarray, compromise: float = 0.5) -> np.ndarray:
    # CoCoFISo replaces CoCoSo min--max normalization with TOPSIS vector normalization.
    normalized = matrix / np.sqrt(np.sum(np.square(matrix), axis=0, keepdims=True))
    weighted_sum = normalized @ weights
    power_sum = np.sum(np.power(np.clip(normalized, 1e-12, None), weights), axis=1)
    ka = (weighted_sum + power_sum) / np.sum(weighted_sum + power_sum)
    # Corrected K_ib from CoCoFISo, which remains defined when S_i or P_i is zero.
    kb = (weighted_sum + power_sum) / (
        1.0
        + weighted_sum / (1.0 + weighted_sum)
        + power_sum / (1.0 + power_sum)
    )
    kc = (compromise * weighted_sum + (1.0 - compromise) * power_sum) / max(
        compromise * np.max(weighted_sum) + (1.0 - compromise) * np.max(power_sum),
        1e-9,
    )
    return np.cbrt(np.maximum(ka * kb * kc, 0.0)) + (ka + kb + kc) / 3.0


def run(
    frame: pd.DataFrame,
    sensitivity_draws: int = 5_000,
    seed: int = 20260817,
) -> pd.DataFrame:
    matrix = pd.DataFrame(
        {
            "service": frame["service"].to_numpy(),
            "reliability": 1.0 / np.maximum(frame["risk_high"].to_numpy(), 1e-6),
            "domestic_access": frame["domestic_retention"].to_numpy(),
            "international_access": frame["international_retention"].to_numpy(),
            "carrier_burden": 1.0
            / np.maximum(frame["combined_burden_index"].to_numpy(), 1e-6),
        },
        index=frame["phase"].to_numpy(),
    )
    equal_weights = np.full(matrix.shape[1], 1.0 / matrix.shape[1])
    point_score = _score(matrix.to_numpy(), equal_weights)
    draws = weight_draws(list(matrix.columns), sensitivity_draws, seed)
    winner_counts = np.zeros(len(frame), dtype=int)
    ranks = np.zeros((sensitivity_draws, len(frame)), dtype=int)
    for k, weights in enumerate(draws.to_numpy()):
        score = _score(matrix.to_numpy(), weights)
        order = np.argsort(-score, kind="stable")
        winner_counts[order[0]] += 1
        ranks[k, order] = np.arange(1, len(frame) + 1)
    result = pd.DataFrame(
        {
            "phase": frame["phase"],
            "score": point_score,
            "winner_probability": winner_counts / sensitivity_draws,
            "mean_rank_under_weight_uncertainty": ranks.mean(axis=0),
        }
    )
    result["rank"] = result["score"].rank(ascending=False, method="min").astype(int)
    return result.sort_values(["rank", "phase"]).reset_index(drop=True)
