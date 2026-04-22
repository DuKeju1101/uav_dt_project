from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import numpy as np


@dataclass
class PointEntity:
    name: str
    position: np.ndarray

    def copy(self) -> "PointEntity":
        return PointEntity(name=self.name, position=self.position.copy())


@dataclass
class UAV(PointEntity):
    power: float = 0.0
    history: List[np.ndarray] = field(default_factory=list)

    def record(self) -> None:
        self.history.append(self.position.copy())

    def reset_history(self) -> None:
        self.history = [self.position.copy()]


@dataclass
class User(PointEntity):
    pass


@dataclass
class Eve(PointEntity):
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=float))

    def step(self, delta_t: float, noise_std: float = 0.0, rng: np.random.Generator | None = None) -> None:
        noise = np.zeros(2, dtype=float)
        if rng is not None and noise_std > 0:
            noise = rng.normal(0.0, noise_std, size=2)
        self.position = self.position + (self.velocity + noise) * delta_t


@dataclass
class TwinState:
    state: np.ndarray
    covariance: np.ndarray
    aoi: int
    last_sync_bandwidth: float = 0.0

    @property
    def eve_est(self) -> np.ndarray:
        return self.state[:2]

    @eve_est.setter
    def eve_est(self, value: np.ndarray) -> None:
        self.state[:2] = np.asarray(value, dtype=float)

    @property
    def eve_vel_est(self) -> np.ndarray:
        return self.state[2:]

    @eve_vel_est.setter
    def eve_vel_est(self, value: np.ndarray) -> None:
        self.state[2:] = np.asarray(value, dtype=float)

    @property
    def sigma(self) -> float:
        pos_cov = self.covariance[:2, :2]
        eigvals = np.linalg.eigvalsh(pos_cov)
        return float(np.sqrt(max(float(np.max(eigvals)), 0.0)))

    def copy(self) -> "TwinState":
        return TwinState(
            state=self.state.copy(),
            covariance=self.covariance.copy(),
            aoi=int(self.aoi),
            last_sync_bandwidth=float(self.last_sync_bandwidth),
        )
