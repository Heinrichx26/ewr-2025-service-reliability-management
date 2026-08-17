from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from .common import MethodMetadata


METADATA = MethodMetadata(
    method_id="znumber_network_dea",
    family="Efficiency with undesirable outputs and uncertainty",
    source="Yang, Omrani, and Imanirad",
    venue="Socio-Economic Planning Sciences",
    year=2024,
    doi="10.1016/j.seps.2024.102080",
    reproduced_components="network DEA weighting, shared service output, undesirable outputs, and Z-number reliability weighting",
    airport_adaptation="dated policy regimes are decision-making units and bootstrap width supplies the reliability component of each Z-number",
    output_type="cross-efficiency ranking",
    decision_limit="efficiency can compensate a weak public-service outcome with another output and supplies no threshold guarantee",
)


def _multiplier_weights(inputs: np.ndarray, outputs: np.ndarray, focal: int) -> np.ndarray:
    n_inputs = inputs.shape[1]
    n_outputs = outputs.shape[1]
    objective = np.r_[np.zeros(n_inputs), -outputs[focal]]
    a_ub = np.c_[-inputs, outputs]
    b_ub = np.zeros(inputs.shape[0])
    a_eq = np.r_[inputs[focal], np.zeros(n_outputs)][None, :]
    result = linprog(
        objective,
        A_ub=a_ub,
        b_ub=b_ub,
        A_eq=a_eq,
        b_eq=np.array([1.0]),
        bounds=[(1e-5, None)] * (n_inputs + n_outputs),
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"DEA multiplier problem failed for unit {focal}: {result.message}")
    return result.x


def _cross_efficiency(inputs: np.ndarray, outputs: np.ndarray) -> np.ndarray:
    evaluations = []
    for focal in range(inputs.shape[0]):
        weights = _multiplier_weights(inputs, outputs, focal)
        v = weights[: inputs.shape[1]]
        u = weights[inputs.shape[1] :]
        denominator = np.maximum(inputs @ v, 1e-12)
        evaluations.append((outputs @ u) / denominator)
    return np.mean(np.vstack(evaluations), axis=0)


def run(frame: pd.DataFrame) -> pd.DataFrame:
    eps = 1e-3
    service = (frame["service"] / frame["service"].max()).to_numpy()[:, None]
    access = frame[["domestic_retention", "international_retention"]].to_numpy()
    stage1_central = _cross_efficiency(
        (frame["risk_index"] + eps).to_numpy()[:, None], service
    )
    stage1_adverse = _cross_efficiency(
        (frame["risk_high"] + eps).to_numpy()[:, None], service
    )
    stage2_inputs = np.c_[service[:, 0], frame["combined_burden_index"] + eps]
    stage2 = _cross_efficiency(stage2_inputs, access)
    central = np.sqrt(stage1_central * stage2)
    adverse = np.sqrt(stage1_adverse * stage2)
    relative_width = frame["uncertainty_width"] / np.maximum(frame["risk_index"], eps)
    reliability = 1.0 / (1.0 + relative_width)
    score = reliability * np.sqrt(np.maximum(central * adverse, 0.0)) + (
        1.0 - reliability
    ) * np.minimum(central, adverse)
    result = pd.DataFrame(
        {
            "phase": frame["phase"],
            "score": score,
            "central_cross_efficiency": central,
            "adverse_cross_efficiency": adverse,
            "z_reliability": reliability,
        }
    )
    result["rank"] = result["score"].rank(ascending=False, method="min").astype(int)
    return result.sort_values(["rank", "phase"]).reset_index(drop=True)
