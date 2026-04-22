from __future__ import annotations

import math
from typing import Dict, List
import numpy as np


def distance_3d(p1: np.ndarray, p2: np.ndarray, height: float) -> float:
    diff = p1 - p2
    return float(np.sqrt(np.sum(diff ** 2) + height ** 2))


def horizontal_distance(p1: np.ndarray, p2: np.ndarray) -> float:
    diff = p1 - p2
    return float(np.sqrt(np.sum(diff ** 2)))


def elevation_angle_deg(p1: np.ndarray, p2: np.ndarray, height: float) -> float:
    horiz = max(horizontal_distance(p1, p2), 1e-12)
    return float(np.degrees(np.arctan2(height, horiz)))


def los_probability(
    p1: np.ndarray,
    p2: np.ndarray,
    height: float,
    los_a: float,
    los_b: float,
) -> float:
    theta = elevation_angle_deg(p1, p2, height)
    prob = 1.0 / (1.0 + los_a * np.exp(-los_b * (theta - los_a)))
    return float(np.clip(prob, 0.0, 1.0))


def gain(
    p1: np.ndarray,
    p2: np.ndarray,
    height: float,
    beta0: float,
    alpha: float,
    channel_cfg: Dict[str, float] | None = None,
) -> float:
    d = distance_3d(p1, p2, height)
    base_gain = float(beta0 / (d ** alpha))
    if not channel_cfg or not bool(channel_cfg.get("use_probabilistic_los", False)):
        return base_gain

    p_los = los_probability(
        p1=p1,
        p2=p2,
        height=height,
        los_a=float(channel_cfg.get("los_a", 9.61)),
        los_b=float(channel_cfg.get("los_b", 0.16)),
    )
    los_factor = 10.0 ** (-float(channel_cfg.get("eta_los_db", 0.0)) / 10.0)
    nlos_factor = 10.0 ** (-float(channel_cfg.get("eta_nlos_db", 20.0)) / 10.0)
    fading_los_mean = float(channel_cfg.get("fading_los_mean", 1.0))
    fading_nlos_mean = float(channel_cfg.get("fading_nlos_mean", 1.0))
    effective_factor = p_los * los_factor * fading_los_mean + (1.0 - p_los) * nlos_factor * fading_nlos_mean
    return float(base_gain * effective_factor)


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
    channel_cfg: Dict[str, float] | None = None,
) -> Dict[str, float]:
    g_su = gain(uav1_pos, user_pos, height, beta0, alpha, channel_cfg=channel_cfg)
    g_ju = gain(uav2_pos, user_pos, height, beta0, alpha, channel_cfg=channel_cfg)
    g_se = gain(uav1_pos, eve_pos, height, beta0, alpha, channel_cfg=channel_cfg)
    g_je = gain(uav2_pos, eve_pos, height, beta0, alpha, channel_cfg=channel_cfg)

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
    channel_cfg: Dict[str, float] | None = None,
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
            channel_cfg=channel_cfg,
        )
        if best is None or metrics["r_sec"] > best["r_sec"]:
            best = metrics
            best_idx = idx
    assert best is not None
    best["user_idx"] = best_idx
    return best


def best_eve_interception_rate(
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
    channel_cfg: Dict[str, float] | None = None,
) -> float:
    best_rate = 0.0
    for user_pos in user_positions:
        g_se = gain(uav1_pos, eve_pos, height, beta0, alpha, channel_cfg=channel_cfg)
        g_je = gain(uav2_pos, eve_pos, height, beta0, alpha, channel_cfg=channel_cfg)
        r_e = rate(signal=p_s * g_se, interference=p_j * g_je, noise=noise_power)
        best_rate = max(best_rate, r_e)
    return float(best_rate)
