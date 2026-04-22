from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class SyncDecision:
    should_sync: bool
    reason: str
    bandwidth: float = 0.0
    threshold_value: float | None = None
    risk_value: float | None = None


def _clip_bandwidth(remaining_budget: float, bandwidth: float, min_bandwidth: float) -> float:
    if remaining_budget <= 0.0:
        return 0.0
    feasible = min(float(remaining_budget), max(float(bandwidth), 0.0))
    if feasible + 1e-12 < float(min_bandwidth):
        return 0.0
    return feasible


def _bandwidth_from_pressure(
    pressure: float,
    remaining_budget: float,
    bandwidth_min: float,
    bandwidth_max: float,
) -> float:
    pressure = float(np.clip(pressure, 0.0, 1.0))
    bw = float(bandwidth_min) + pressure * max(float(bandwidth_max) - float(bandwidth_min), 0.0)
    return _clip_bandwidth(remaining_budget=remaining_budget, bandwidth=bw, min_bandwidth=bandwidth_min)


class SyncPolicies:
    @staticmethod
    def full(
        slot: int,
        remaining_budget: float,
        bandwidth_max: float,
        bandwidth_min: float,
    ) -> SyncDecision:
        bandwidth = _clip_bandwidth(remaining_budget, bandwidth_max, bandwidth_min)
        return SyncDecision(should_sync=bandwidth > 0.0, reason="full_sync", bandwidth=bandwidth)

    @staticmethod
    def periodic(
        slot: int,
        remaining_budget: float,
        k: int,
        bandwidth_max: float,
        bandwidth_min: float,
    ) -> SyncDecision:
        should = remaining_budget > 0.0 and (slot % max(k, 1) == 0)
        bandwidth = _clip_bandwidth(remaining_budget, bandwidth_max, bandwidth_min) if should else 0.0
        return SyncDecision(should_sync=bandwidth > 0.0, reason=f"periodic_k={k}", bandwidth=bandwidth)

    @staticmethod
    def aoi_only(
        aoi: int,
        remaining_budget: float,
        aoi_threshold: int,
        bandwidth_min: float,
        bandwidth_max: float,
    ) -> SyncDecision:
        should = remaining_budget > 0.0 and aoi >= aoi_threshold
        pressure = float(aoi) / max(float(aoi_threshold), 1.0)
        bandwidth = _bandwidth_from_pressure(pressure, remaining_budget, bandwidth_min, bandwidth_max) if should else 0.0
        return SyncDecision(should_sync=bandwidth > 0.0, reason=f"aoi_thr={aoi_threshold}", bandwidth=bandwidth)

    @staticmethod
    def security_risk(
        aoi: int,
        pred_error_radius: float,
        sigma: float,
        predicted_secrecy_rate: float,
        r_safe: float,
        remaining_budget: float,
        total_budget: float,
        w_risk: tuple[float, float, float, float],
        tau0: float,
        tau_budget_eta: float,
        a_max: float,
        d_max: float,
        sigma_max: float,
        bandwidth_min: float,
        bandwidth_max: float,
    ) -> SyncDecision:
        if remaining_budget <= 0:
            return SyncDecision(should_sync=False, reason="budget_exhausted", threshold_value=1.0, risk_value=0.0)

        w1, w2, w3, w4 = w_risk
        risk = (
            w1 * min(aoi / max(a_max, 1e-12), 1.0)
            + w2 * min(pred_error_radius / max(d_max, 1e-12), 1.0)
            + w3 * min(sigma / max(sigma_max, 1e-12), 1.0)
            + w4 * min(max(r_safe - predicted_secrecy_rate, 0.0) / max(r_safe, 1e-12), 1.0)
        )
        budget_ratio_used = 1.0 - (remaining_budget / max(total_budget, 1e-12))
        threshold = tau0 + tau_budget_eta * budget_ratio_used
        pressure = max(risk - threshold, 0.0) / max(1.0 - threshold, 1e-12)
        bandwidth = _bandwidth_from_pressure(pressure, remaining_budget, bandwidth_min, bandwidth_max) if risk > threshold else 0.0
        return SyncDecision(
            should_sync=bandwidth > 0.0,
            reason="security_risk",
            bandwidth=bandwidth,
            threshold_value=float(threshold),
            risk_value=float(risk),
        )

    @staticmethod
    def security_margin(
        aoi: int,
        pred_error_radius: float,
        sigma: float,
        predicted_margin: float,
        rho: float,
        remaining_budget: float,
        sync_delay: int,
        failure_prob: float,
        kappa: tuple[float, float, float],
        theory: Any,
        feature_scales: dict[str, float] | None = None,
        bandwidth_min: float = 0.0,
        bandwidth_max: float = 1.0,
    ) -> SyncDecision:
        if remaining_budget <= 0:
            return SyncDecision(should_sync=False, reason="budget_exhausted")
        certificate = robust_secrecy_certificate(
            aoi=aoi,
            pred_error_radius=pred_error_radius,
            sigma=sigma,
            predicted_margin=predicted_margin,
            rho=rho,
            sync_delay=sync_delay,
            failure_prob=failure_prob,
            kappa=kappa,
            theory=theory,
            feature_scales=feature_scales,
        )
        slack = float(certificate["certificate_slack"])
        pressure = max(-slack, 0.0) / max(float(certificate["required_margin"]), 1e-12)
        bandwidth = _bandwidth_from_pressure(pressure, remaining_budget, bandwidth_min, bandwidth_max) if slack < 0.0 else 0.0
        should = bandwidth > 0.0
        return SyncDecision(
            should_sync=should,
            reason="security_margin_certificate",
            bandwidth=bandwidth,
            threshold_value=float(certificate["required_margin"]),
            risk_value=slack,
        )


def secrecy_loss_upper_bound(aoi: int, pred_error_radius: float, sigma: float, kappa: tuple[float, float, float]) -> float:
    k1, k2, k3 = kappa
    return float(k1 * pred_error_radius + k2 * sigma + k3 * aoi)


def build_conformal_features(
    aoi: int,
    pred_error_radius: float,
    sigma: float,
    sync_delay: int,
    failure_prob: float,
    feature_scales: dict[str, float],
) -> dict[str, float]:
    a_scale = max(float(feature_scales.get("aoi", 1.0)), 1e-12)
    d_scale = max(float(feature_scales.get("pred_error_radius", 1.0)), 1e-12)
    s_scale = max(float(feature_scales.get("sigma", 1.0)), 1e-12)
    feats = {
        "bias": 1.0,
        "aoi_norm": float(aoi) / a_scale,
        "pred_error_radius_norm": float(pred_error_radius) / d_scale,
        "sigma_norm": float(sigma) / s_scale,
        "sync_delay": float(sync_delay),
        "failure_prob": float(failure_prob),
    }
    feats["aoi_x_radius"] = feats["aoi_norm"] * feats["pred_error_radius_norm"]
    feats["radius_x_sigma"] = feats["pred_error_radius_norm"] * feats["sigma_norm"]
    feats["aoi_x_sigma"] = feats["aoi_norm"] * feats["sigma_norm"]
    feats["delay_x_radius"] = feats["sync_delay"] * feats["pred_error_radius_norm"]
    feats["delay_x_sigma"] = feats["sync_delay"] * feats["sigma_norm"]
    return feats


def conformal_secrecy_loss_upper_bound(
    aoi: int,
    pred_error_radius: float,
    sigma: float,
    sync_delay: int,
    failure_prob: float,
    model: dict[str, Any],
    feature_scales: dict[str, float],
) -> dict[str, float]:
    feats = build_conformal_features(
        aoi=aoi,
        pred_error_radius=pred_error_radius,
        sigma=sigma,
        sync_delay=sync_delay,
        failure_prob=failure_prob,
        feature_scales=feature_scales,
    )
    feature_names = [str(name) for name in model.get("feature_names", list(feats.keys()))]
    coefficients = {str(k): float(v) for k, v in model.get("coefficients", {}).items()}
    pred = float(model.get("intercept", 0.0))
    for name in feature_names:
        pred += coefficients.get(name, 0.0) * feats.get(name, 0.0)

    predicted_loss = max(pred, 0.0)
    conformal_buffer = float(model.get("nonconformity_quantile", model.get("residual_quantile", 0.0)))
    safety_scale = float(model.get("safety_scale", 1.0))
    upper_bound = predicted_loss + safety_scale * conformal_buffer
    return {
        "predicted_loss": float(predicted_loss),
        "conformal_buffer": float(safety_scale * conformal_buffer),
        "upper_bound": float(upper_bound),
    }


def robust_secrecy_certificate(
    aoi: int,
    pred_error_radius: float,
    sigma: float,
    predicted_margin: float,
    rho: float,
    sync_delay: int,
    failure_prob: float,
    kappa: tuple[float, float, float],
    theory: Any,
    feature_scales: dict[str, float] | None = None,
) -> dict[str, float | bool]:
    delay_penalty = 0.0
    failure_penalty = 0.0
    residual_penalty = 0.0
    empirical_bound = 0.0
    empirical_buffer = 0.0
    if isinstance(theory, dict) and "loss_model" in theory:
        loss_model = conformal_secrecy_loss_upper_bound(
            aoi=aoi,
            pred_error_radius=pred_error_radius,
            sigma=sigma,
            sync_delay=sync_delay,
            failure_prob=failure_prob,
            model=theory["loss_model"],
            feature_scales=feature_scales or theory.get("feature_scales", {}) or {},
        )
        base_bound = float(loss_model["predicted_loss"])
        empirical_bound = float(loss_model["upper_bound"])
        empirical_buffer = float(loss_model["conformal_buffer"])
        required_margin = rho + empirical_bound
    else:
        base_bound = secrecy_loss_upper_bound(
            aoi=aoi,
            pred_error_radius=pred_error_radius,
            sigma=sigma,
            kappa=kappa,
        )
        c_delay, c_failure, c_residual = theory
        delay_penalty = c_delay * max(sync_delay, 0)
        failure_penalty = c_failure * max(failure_prob, 0.0) * (1.0 + pred_error_radius + sigma)
        residual_penalty = c_residual
        required_margin = rho + base_bound + delay_penalty + failure_penalty + residual_penalty

    certificate_slack = predicted_margin - required_margin
    return {
        "base_bound": float(base_bound),
        "delay_penalty": float(delay_penalty),
        "failure_penalty": float(failure_penalty),
        "residual_penalty": float(residual_penalty),
        "empirical_upper_bound": float(empirical_bound),
        "empirical_buffer": float(empirical_buffer),
        "required_margin": float(required_margin),
        "certificate_slack": float(certificate_slack),
        "certified": bool(certificate_slack >= 0.0),
    }
