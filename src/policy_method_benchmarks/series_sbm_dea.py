from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from .common import MethodMetadata


METADATA = MethodMetadata(
    method_id="series_sbm_dea",
    family="Efficiency with undesirable outputs",
    source="Taleb",
    venue="Socio-Economic Planning Sciences",
    year=2025,
    doi="10.1016/j.seps.2025.102211",
    reproduced_components="series-network decomposition, non-radial slacks, non-controllable exposure, and undesirable outputs",
    airport_adaptation="reliability production and service preservation form two linked stages; uncertainty width is held as a non-controllable exposure",
    output_type="network slack-efficiency ranking",
    decision_limit="several regimes can share the efficient frontier and the efficiency score does not impose policy acceptability bounds",
)


def _additive_slack_efficiency(
    inputs: np.ndarray,
    outputs: np.ndarray,
    undesirable: np.ndarray,
    focal: int,
    non_controllable: np.ndarray | None = None,
) -> float:
    n = inputs.shape[0]
    m = inputs.shape[1]
    s = outputs.shape[1]
    q = undesirable.shape[1]
    x0 = np.maximum(inputs[focal], 1e-6)
    y0 = np.maximum(outputs[focal], 1e-6)
    b0 = np.maximum(undesirable[focal], 1e-6)
    objective = np.r_[
        np.zeros(n),
        -1.0 / (m * x0),
        -1.0 / (s * y0),
        -1.0 / (q * b0),
    ]
    rows = []
    rhs = []
    for k in range(m):
        row = np.zeros(n + m + s + q)
        row[:n] = inputs[:, k]
        row[n + k] = 1.0
        rows.append(row)
        rhs.append(inputs[focal, k])
    for k in range(s):
        row = np.zeros(n + m + s + q)
        row[:n] = outputs[:, k]
        row[n + m + k] = -1.0
        rows.append(row)
        rhs.append(outputs[focal, k])
    for k in range(q):
        row = np.zeros(n + m + s + q)
        row[:n] = undesirable[:, k]
        row[n + m + s + k] = 1.0
        rows.append(row)
        rhs.append(undesirable[focal, k])
    convexity = np.zeros(n + m + s + q)
    convexity[:n] = 1.0
    equality_rows = [*rows, convexity]
    equality_rhs = [*rhs, 1.0]
    if non_controllable is not None:
        for k in range(non_controllable.shape[1]):
            row = np.zeros(n + m + s + q)
            row[:n] = non_controllable[:, k]
            equality_rows.append(row)
            equality_rhs.append(non_controllable[focal, k])
    result = linprog(
        objective,
        A_eq=np.vstack(equality_rows),
        b_eq=np.asarray(equality_rhs),
        bounds=[(0.0, None)] * (n + m + s + q),
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"SBM slack problem failed for unit {focal}: {result.message}")
    normalized_slack = max(-result.fun, 0.0)
    return 1.0 / (1.0 + normalized_slack)


def run(frame: pd.DataFrame) -> pd.DataFrame:
    eps = 1e-3
    service = (frame["service"] / frame["service"].max()).to_numpy()[:, None]
    uncertainty = (frame["uncertainty_width"] + eps).to_numpy()[:, None]
    reliability_bad = (frame["risk_high"] + eps).to_numpy()[:, None]
    constant_resource = np.ones((len(frame), 1))
    stage1 = np.array(
        [
            _additive_slack_efficiency(
                constant_resource,
                service,
                reliability_bad,
                i,
                non_controllable=uncertainty,
            )
            for i in range(len(frame))
        ]
    )
    access = frame[["domestic_retention", "international_retention"]].to_numpy()
    intermediate = np.c_[service[:, 0], uncertainty[:, 0]]
    burden_bad = (frame["combined_burden_index"] + eps).to_numpy()[:, None]
    stage2 = np.array(
        [
            _additive_slack_efficiency(
                intermediate,
                access,
                burden_bad,
                i,
                non_controllable=uncertainty,
            )
            for i in range(len(frame))
        ]
    )
    network = np.sqrt(stage1 * stage2)
    result = pd.DataFrame(
        {
            "phase": frame["phase"],
            "score": network,
            "reliability_stage_efficiency": stage1,
            "service_stage_efficiency": stage2,
        }
    )
    result["rank"] = result["score"].rank(ascending=False, method="min").astype(int)
    return result.sort_values(["rank", "phase"]).reset_index(drop=True)
