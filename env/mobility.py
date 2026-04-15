from __future__ import annotations

from typing import Dict, Tuple
import numpy as np


DIRECTION_MAP: Dict[str, np.ndarray] = {
    "stay": np.array([0.0, 0.0]),
    "up": np.array([0.0, 1.0]),
    "down": np.array([0.0, -1.0]),
    "left": np.array([-1.0, 0.0]),
    "right": np.array([1.0, 0.0]),
    "up_left": np.array([-1.0, 1.0]),
    "up_right": np.array([1.0, 1.0]),
    "down_left": np.array([-1.0, -1.0]),
    "down_right": np.array([1.0, -1.0]),
}


def normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm <= 1e-12:
        return np.zeros_like(vec)
    return vec / norm


ALL_MOVES = list(DIRECTION_MAP.keys())


def apply_move(position: np.ndarray, move: str, step_size: float, area: Tuple[float, float]) -> np.ndarray:
    delta = normalize(DIRECTION_MAP[move]) * step_size
    new_pos = position + delta
    new_pos[0] = float(np.clip(new_pos[0], 0.0, area[0]))
    new_pos[1] = float(np.clip(new_pos[1], 0.0, area[1]))
    return new_pos


def clip_area(position: np.ndarray, area: Tuple[float, float]) -> np.ndarray:
    out = position.copy()
    out[0] = float(np.clip(out[0], 0.0, area[0]))
    out[1] = float(np.clip(out[1], 0.0, area[1]))
    return out
