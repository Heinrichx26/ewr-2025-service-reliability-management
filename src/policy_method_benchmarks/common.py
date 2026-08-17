from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "results" / "seps_policy_frontier" / "policy_regime_metrics.csv"

PHASE_ORDER = ["stress", "interim_28", "cap_34", "extension_36"]
DISPLAY = {
    "stress": "Stress",
    "interim_28": "28/28",
    "cap_34": "34/34",
    "extension_36": "36/36",
}

BENEFIT_COLUMNS = [
    "service_score",
    "reliability_score",
    "domestic_retention",
    "international_retention",
    "burden_score",
]


@dataclass(frozen=True)
class MethodMetadata:
    method_id: str
    family: str
    source: str
    venue: str
    year: int
    doi: str
    reproduced_components: str
    airport_adaptation: str
    output_type: str
    decision_limit: str


def minmax(values: Iterable[float], higher_is_better: bool = True) -> np.ndarray:
    x = np.asarray(list(values), dtype=float)
    lo = np.nanmin(x)
    hi = np.nanmax(x)
    if np.isclose(hi, lo):
        out = np.ones_like(x)
    else:
        out = (x - lo) / (hi - lo)
    return out if higher_is_better else 1.0 - out


def load_regimes(path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = set(PHASE_ORDER).difference(frame["phase"])
    if missing:
        raise ValueError(f"Missing policy regimes: {sorted(missing)}")
    frame = frame.set_index("phase").loc[PHASE_ORDER].reset_index()
    frame["display"] = frame["phase"].map(DISPLAY)
    frame["service"] = frame["arr_ops_per_day"] + frame["dep_ops_per_day"]
    frame["domestic_retention"] = 1.0 - frame["domestic_access_loss"]
    frame["international_retention"] = 1.0 - frame["international_access_loss"]
    frame["uncertainty_width"] = frame["risk_high"] - frame["risk_low"]
    frame["service_score"] = minmax(frame["service"], True)
    frame["reliability_score"] = minmax(frame["risk_high"], False)
    frame["burden_score"] = minmax(frame["combined_burden_index"], False)
    frame["domestic_score"] = minmax(frame["domestic_retention"], True)
    frame["international_score"] = minmax(frame["international_retention"], True)
    return frame


def normalized_decision_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    matrix = pd.DataFrame(index=frame["phase"])
    matrix["service"] = minmax(frame["service"], True)
    matrix["reliability"] = minmax(frame["risk_high"], False)
    matrix["domestic_access"] = minmax(frame["domestic_retention"], True)
    matrix["international_access"] = minmax(frame["international_retention"], True)
    matrix["carrier_burden"] = minmax(frame["combined_burden_index"], False)
    return matrix


def risk_scenarios(
    frame: pd.DataFrame,
    draws: int,
    seed: int,
) -> pd.DataFrame:
    """Approximate regime risk distributions from point estimates and 95% bounds."""
    rng = np.random.default_rng(seed)
    samples: dict[str, np.ndarray] = {}
    for row in frame.itertuples(index=False):
        left_sd = max((row.risk_index - row.risk_low) / 1.96, 1e-6)
        right_sd = max((row.risk_high - row.risk_index) / 1.96, 1e-6)
        z = rng.standard_normal(draws)
        sd = np.where(z < 0, left_sd, right_sd)
        samples[row.phase] = np.clip(row.risk_index + z * sd, 0.0, None)
    return pd.DataFrame(samples)


def rank_rows(scores: pd.Series, higher_is_better: bool = True) -> pd.DataFrame:
    result = scores.rename("score").reset_index().rename(columns={"index": "phase"})
    result["rank"] = result["score"].rank(
        ascending=not higher_is_better, method="min"
    ).astype(int)
    return result.sort_values(["rank", "phase"]).reset_index(drop=True)


def weight_draws(columns: list[str], draws: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.dirichlet(np.ones(len(columns)), size=draws), columns=columns)
