from __future__ import annotations

import numpy as np
import pandas as pd

from .common import MethodMetadata, minmax


METADATA = MethodMetadata(
    method_id="equity_efficiency_frontier",
    family="Equity-efficiency allocation",
    source="Eisenhandler, Meyer, and Tzur",
    venue="Socio-Economic Planning Sciences",
    year=2026,
    doi="10.1016/j.seps.2026.102483",
    reproduced_components="explicit effectiveness-equity trade-off and preference-weight sweep",
    airport_adaptation="effectiveness combines retained service and reliability; equity is the minimum standardized access and burden outcome",
    output_type="preference-dependent frontier",
    decision_limit="normalization can label uniformly poor service as equitable and the preference weight determines whether safety is protected",
)


def run(frame: pd.DataFrame, grid_points: int = 101) -> pd.DataFrame:
    service = minmax(frame["service"], True)
    reliability = minmax(frame["risk_high"], False)
    effectiveness = 0.5 * service + 0.5 * reliability
    domestic = minmax(frame["domestic_retention"], True)
    international = minmax(frame["international_retention"], True)
    burden = minmax(frame["combined_burden_index"], False)
    equity = np.minimum.reduce([domestic, international, burden])
    weights = np.linspace(0.0, 1.0, grid_points)
    winner_count = np.zeros(len(frame), dtype=int)
    balanced_score = None
    for weight in weights:
        score = weight * effectiveness + (1.0 - weight) * equity
        winner_count[int(np.argmax(score))] += 1
        if np.isclose(weight, 0.5):
            balanced_score = score.copy()
    if balanced_score is None:
        balanced_score = 0.5 * effectiveness + 0.5 * equity
    result = pd.DataFrame(
        {
            "phase": frame["phase"],
            "score": balanced_score,
            "effectiveness": effectiveness,
            "equity": equity,
            "winner_probability": winner_count / grid_points,
        }
    )
    result["rank"] = result["score"].rank(ascending=False, method="min").astype(int)
    return result.sort_values(["rank", "phase"]).reset_index(drop=True)
