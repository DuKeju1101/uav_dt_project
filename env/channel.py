from __future__ import annotations

import math
from typing import Dict, List
import numpy as np


def distance_3d(p1: np.ndarray, p2: np.ndarray, height: float) -> float:
    diff = p1 - p2
    return float(np.sqrt(np.sum(diff ** 2) + height ** 2))


def gain(p1: np.ndarray, p2: np.ndarray, height: float, beta0: float, alpha: float) -> float:
    d = distance_3d(p1, p2, height)
    return float(beta0 / (d ** alpha))


def rate(signal: float, interference: float, noise: float) -> float:
    sinr = signal / max(noise + interference, 1e-12)
    return float(math.log2(1.0 + max(sinr, 0.0)))


def secrecy_rate(
    uav1_pos: np.ndarray,
    uav2_pos: np.ndarray,
    eve_pos: np.ndarray,
    user_pos: np.ndarray,
    p_s: float,
    p_j: float,
    height: float,
    beta0: float,
    alpha: float,
    noise_power: float,
    xi_legit_interference: float,
) -> Dict[str, float]:
    g_su = gain(uav1_pos, user_pos, height, beta0, alpha)
    g_ju = gain(uav2_pos, user_pos, height, beta0, alpha)
    g_se = gain(uav1_pos, eve_pos, height, beta0, alpha)
    g_je = gain(uav2_pos, eve_pos, height, beta0, alpha)

    r_b = rate(signal=p_s * g_su, interference=xi_legit_interference * p_j * g_ju, noise=noise_power)
    r_e = rate(signal=p_s * g_se, interference=p_j * g_je, noise=noise_power)
    r_sec = max(r_b - r_e, 0.0)

    return {
        "g_su": g_su,
        "g_ju": g_ju,
        "g_se": g_se,
        "g_je": g_je,
        "r_b": r_b,
        "r_e": r_e,
        "r_sec": r_sec,
    }


def best_user_metrics(
    uav1_pos: np.ndarray,
    uav2_pos: np.ndarray,
    eve_pos: np.ndarray,
    user_positions: List[np.ndarray],
    p_s: float,
    p_j: float,
    height: float,
    beta0: float,
    alpha: float,
    noise_power: float,
    xi_legit_interference: float,
) -> Dict[str, float]:
    best = None
    best_idx = -1
    for idx, user_pos in enumerate(user_positions):
        metrics = secrecy_rate(
            uav1_pos=uav1_pos,
            uav2_pos=uav2_pos,
            eve_pos=eve_pos,
            user_pos=user_pos,
            p_s=p_s,
            p_j=p_j,
            height=height,
            beta0=beta0,
            alpha=alpha,
            noise_power=noise_power,
            xi_legit_interference=xi_legit_interference,
        )
        if best is None or metrics["r_sec"] > best["r_sec"]:
            best = metrics
            best_idx = idx
    assert best is not None
    best["user_idx"] = best_idx
    return best
