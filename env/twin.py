from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np

from .entities import TwinState, Eve
from .mobility import clip_area


@dataclass
class TwinConfig:
    sigma0: float
    velocity_sigma0: float
    area: Tuple[float, float]
    delta_t: float
    process_accel_std: float
    measurement_std_at_max_bw: float
    bandwidth_max: float
    bandwidth_min: float


class TwinTracker:
    def __init__(self, config: TwinConfig):
        self.config = config
        self._H = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float)

    def _transition(self) -> np.ndarray:
        dt = self.config.delta_t
        return np.array(
            [
                [1.0, 0.0, dt, 0.0],
                [0.0, 1.0, 0.0, dt],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )

    def _process_covariance(self) -> np.ndarray:
        dt = self.config.delta_t
        q = float(self.config.process_accel_std) ** 2
        return q * np.array(
            [
                [0.25 * dt**4, 0.0, 0.5 * dt**3, 0.0],
                [0.0, 0.25 * dt**4, 0.0, 0.5 * dt**3],
                [0.5 * dt**3, 0.0, dt**2, 0.0],
                [0.0, 0.5 * dt**3, 0.0, dt**2],
            ],
            dtype=float,
        )

    def _measurement_covariance(self, bandwidth: float) -> np.ndarray:
        bw_max = max(float(self.config.bandwidth_max), 1e-12)
        bw_min = max(float(self.config.bandwidth_min), 1e-12)
        eff_bw = float(np.clip(bandwidth, bw_min, bw_max))
        norm_bw = eff_bw / bw_max
        meas_std = float(self.config.measurement_std_at_max_bw) / np.sqrt(max(norm_bw, 1e-12))
        return np.eye(2, dtype=float) * (meas_std**2)

    def _kalman_update(
        self,
        twin: TwinState,
        measurement: np.ndarray,
        bandwidth: float,
    ) -> TwinState:
        R = self._measurement_covariance(bandwidth)
        innovation = measurement - self._H @ twin.state
        innovation_cov = self._H @ twin.covariance @ self._H.T + R
        kalman_gain = twin.covariance @ self._H.T @ np.linalg.inv(innovation_cov)
        twin.state = twin.state + kalman_gain @ innovation
        eye = np.eye(twin.covariance.shape[0], dtype=float)
        twin.covariance = (eye - kalman_gain @ self._H) @ twin.covariance
        twin.eve_est = clip_area(twin.eve_est, self.config.area)
        twin.aoi = 0
        twin.last_sync_bandwidth = float(bandwidth)
        return twin

    def initialize(self, eve: Eve) -> TwinState:
        covariance = np.diag(
            [
                float(self.config.sigma0) ** 2,
                float(self.config.sigma0) ** 2,
                float(self.config.velocity_sigma0) ** 2,
                float(self.config.velocity_sigma0) ** 2,
            ]
        )
        return TwinState(
            state=np.array([eve.position[0], eve.position[1], eve.velocity[0], eve.velocity[1]], dtype=float),
            covariance=covariance,
            aoi=0,
            last_sync_bandwidth=float(self.config.bandwidth_max),
        )

    def sync(
        self,
        twin: TwinState,
        eve: Eve,
        bandwidth: float,
        rng: np.random.Generator | None = None,
        noisy: bool = True,
    ) -> TwinState:
        measurement = eve.position.copy()
        if noisy and rng is not None:
            measurement_noise = rng.multivariate_normal(
                mean=np.zeros(2, dtype=float),
                cov=self._measurement_covariance(bandwidth),
            )
            measurement = measurement + measurement_noise
        return self._kalman_update(twin, clip_area(measurement, self.config.area), bandwidth)

    def expected_sync(self, twin: TwinState, true_position: np.ndarray, bandwidth: float) -> TwinState:
        return self._kalman_update(twin, clip_area(np.asarray(true_position, dtype=float), self.config.area), bandwidth)

    def predict(self, twin: TwinState) -> TwinState:
        F = self._transition()
        Q = self._process_covariance()
        twin.state = F @ twin.state
        twin.covariance = F @ twin.covariance @ F.T + Q
        twin.eve_est = clip_area(twin.eve_est, self.config.area)
        twin.aoi += 1
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
