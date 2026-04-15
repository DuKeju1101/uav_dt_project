from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np

from .entities import TwinState, Eve
from .mobility import clip_area


@dataclass
class TwinConfig:
    sigma0: float
    sigma_growth: float
    area: Tuple[float, float]
    delta_t: float


class TwinTracker:
    def __init__(self, config: TwinConfig):
        self.config = config

    def initialize(self, eve: Eve) -> TwinState:
        return TwinState(
            eve_est=eve.position.copy(),
            eve_vel_est=eve.velocity.copy(),
            sigma=float(self.config.sigma0),
            aoi=0,
        )

    def sync(self, twin: TwinState, eve: Eve) -> TwinState:
        twin.eve_est = eve.position.copy()
        twin.eve_vel_est = eve.velocity.copy()
        twin.sigma = float(self.config.sigma0)
        twin.aoi = 0
        return twin

    def predict(self, twin: TwinState) -> TwinState:
        twin.eve_est = clip_area(
            twin.eve_est + twin.eve_vel_est * self.config.delta_t,
            self.config.area,
        )
        twin.aoi += 1
        twin.sigma += self.config.sigma_growth
        return twin


def predicted_error_radius(aoi: int, v_max: float, delta_t: float) -> float:
    return float(aoi * v_max * delta_t)


def twin_quality(
    aoi: int,
    eve_error: float,
    sigma: float,
    a_max: float,
    d_max: float,
    sigma_max: float,
    weights: Tuple[float, float, float],
) -> Dict[str, float]:
    wa, wd, wu = weights
    badness = (
        wa * min(aoi / max(a_max, 1e-12), 1.0)
        + wd * min(eve_error / max(d_max, 1e-12), 1.0)
        + wu * min(sigma / max(sigma_max, 1e-12), 1.0)
    )
    quality = 1.0 - min(max(badness, 0.0), 1.0)
    return {"badness": float(badness), "quality": float(quality)}
