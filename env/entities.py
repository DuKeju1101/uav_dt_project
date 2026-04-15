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
    eve_est: np.ndarray
    eve_vel_est: np.ndarray
    sigma: float
    aoi: int

    def copy(self) -> "TwinState":
        return TwinState(
            eve_est=self.eve_est.copy(),
            eve_vel_est=self.eve_vel_est.copy(),
            sigma=float(self.sigma),
            aoi=int(self.aoi),
        )
