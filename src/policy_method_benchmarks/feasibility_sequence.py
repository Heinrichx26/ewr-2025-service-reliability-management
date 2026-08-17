from __future__ import annotations

import numpy as np
import pandas as pd

from .common import MethodMetadata, normalized_decision_matrix, weight_draws


METADATA = MethodMetadata(
    method_id="feasibility_sequence",
    family="Feasibility-constrained public decision support",
    source="Do, Xia, and Pham",
    venue="Socio-Economic Planning Sciences",
    year=2026,
    doi="10.1016/j.seps.2026.102568",
    reproduced_components="multi-criteria priority score, hard feasibility screening, sequencing, and robustness to preference weights",
    airport_adaptation="dated capacity regimes form a monotone recovery sequence and governance bounds define feasibility",
    output_type="feasible recovery sequence",
    decision_limit="a composite priority score still determines the order inside the feasible set and can obscure which bound is binding",
)


def _feasible(frame: pd.DataFrame) -> np.ndarray:
    return (
        (frame["risk_high"].to_numpy() <= 0.75)
        & (frame["domestic_retention"].to_numpy() >= 0.997)
        & (frame["international_retention"].to_numpy() >= 0.983)
        & (frame["combined_burden_index"].to_numpy() <= 0.05)
    )


def run(
    frame: pd.DataFrame,
    sensitivity_draws: int = 5_000,
    seed: int = 20260817,
) -> pd.DataFrame:
    matrix = normalized_decision_matrix(frame)
    feasible = _feasible(frame)
    weights = np.full(matrix.shape[1], 1.0 / matrix.shape[1])
    point_score = matrix.to_numpy() @ weights
    point_score = np.where(feasible, point_score, -np.inf)
    draws = weight_draws(list(matrix.columns), sensitivity_draws, seed)
    winner_count = np.zeros(len(frame), dtype=int)
    for weight in draws.to_numpy():
        score = matrix.to_numpy() @ weight
        score = np.where(feasible, score, -np.inf)
        if np.isfinite(score).any():
            winner_count[int(np.argmax(score))] += 1
    finite_score = np.where(np.isfinite(point_score), point_score, np.nan)
    result = pd.DataFrame(
        {
            "phase": frame["phase"],
            "score": finite_score,
            "feasible": feasible,
            "winner_probability": winner_count / sensitivity_draws,
        }
    )
    result["rank"] = result["score"].rank(ascending=False, method="min", na_option="bottom").astype(int)
    return result.sort_values(["rank", "phase"]).reset_index(drop=True)
