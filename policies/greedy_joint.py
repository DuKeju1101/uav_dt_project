from __future__ import annotations

from typing import Any, Dict, Tuple
import copy
import itertools

from env.mobility import ALL_MOVES
from env.sync import SyncPolicies, robust_secrecy_certificate


class GreedyJointController:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = copy.deepcopy(cfg)
        self.step_moves = list(self.cfg["control"].get("allowed_moves", ALL_MOVES))
        self.p_s_levels = [float(x) for x in self.cfg["control"]["p_s_levels"]]
        self.p_j_levels = [float(x) for x in self.cfg["control"]["p_j_levels"]]
        self.lambda_move = float(self.cfg["control"]["lambda_move"])
        self.lambda_power = float(self.cfg["control"]["lambda_power"])
        self.lambda_sync = float(self.cfg["control"]["lambda_sync"])
        self.r_min = float(self.cfg["channel"]["r_min"])
        self.bandwidth_min = float(self.cfg["sync"].get("bandwidth_min", 0.25))
        self.bandwidth_max = float(self.cfg["sync"].get("bandwidth_max", 1.0))
        self.move_candidate_limit = int(self.cfg["control"].get("greedy_move_candidates", 5))
        self.power_candidate_limit = int(self.cfg["control"].get("greedy_power_candidates", 3))

    def choose_sync(self, method: str, obs: Dict[str, Any], slot: int, remaining_budget: float) -> Tuple[bool, float, str, Dict[str, float]]:
        sync_cfg = self.cfg["sync"]
        if method == "full":
            dec = SyncPolicies.full(
                slot=slot,
                remaining_budget=remaining_budget,
                bandwidth_max=self.bandwidth_max,
                bandwidth_min=self.bandwidth_min,
            )
        elif method == "periodic":
            dec = SyncPolicies.periodic(
                slot=slot,
                remaining_budget=remaining_budget,
                k=int(sync_cfg["periodic_k"]),
                bandwidth_max=self.bandwidth_max,
                bandwidth_min=self.bandwidth_min,
            )
        elif method == "aoi_only":
            dec = SyncPolicies.aoi_only(
                aoi=int(obs["aoi"]),
                remaining_budget=remaining_budget,
                aoi_threshold=int(sync_cfg["aoi_threshold"]),
                bandwidth_min=self.bandwidth_min,
                bandwidth_max=self.bandwidth_max,
            )
        elif method == "security_risk":
            dec = SyncPolicies.security_risk(
                aoi=int(obs["aoi"]),
                pred_error_radius=float(obs["pred_error_radius"]),
                sigma=float(obs["twin_sigma"]),
                predicted_secrecy_rate=float(obs["pred_margin"] + self.r_min),
                r_safe=self.r_min,
                remaining_budget=remaining_budget,
                total_budget=float(sync_cfg["budget"]),
                w_risk=tuple(self.cfg["threshold"]["w_risk"]),
                tau0=float(sync_cfg["tau0"]),
                tau_budget_eta=float(sync_cfg["tau_budget_eta"]),
                a_max=float(self.cfg["metrics"]["a_max"]),
                d_max=float(self.cfg["metrics"]["d_max"]),
                sigma_max=float(self.cfg["metrics"]["sigma_max"]),
                bandwidth_min=self.bandwidth_min,
                bandwidth_max=self.bandwidth_max,
            )
        elif method == "security_margin":
            certificate = robust_secrecy_certificate(
                aoi=int(obs["aoi"]),
                pred_error_radius=float(obs["pred_error_radius"]),
                sigma=float(obs["twin_sigma"]),
                predicted_margin=float(obs["pred_margin"]),
                rho=float(sync_cfg["rho"]),
                sync_delay=int(sync_cfg.get("delay_slots", 0)),
                failure_prob=float(sync_cfg.get("failure_prob", 0.0)),
                kappa=tuple(self.cfg["threshold"]["kappa"]),
                theory=self.cfg["theory"].get("loss_model") and self.cfg["theory"] or tuple(self.cfg["theory"]["margin_coeffs"]),
                feature_scales={
                    "aoi": float(self.cfg["metrics"]["a_max"]),
                    "pred_error_radius": float(self.cfg["metrics"]["d_max"]),
                    "sigma": float(self.cfg["metrics"]["sigma_max"]),
                },
            )
            dec = SyncPolicies.security_margin(
                aoi=int(obs["aoi"]),
                pred_error_radius=float(obs["pred_error_radius"]),
                sigma=float(obs["twin_sigma"]),
                predicted_margin=float(obs["pred_margin"]),
                rho=float(sync_cfg["rho"]),
                remaining_budget=remaining_budget,
                sync_delay=int(sync_cfg.get("delay_slots", 0)),
                failure_prob=float(sync_cfg.get("failure_prob", 0.0)),
                kappa=tuple(self.cfg["threshold"]["kappa"]),
                theory=self.cfg["theory"].get("loss_model") and self.cfg["theory"] or tuple(self.cfg["theory"]["margin_coeffs"]),
                feature_scales={
                    "aoi": float(self.cfg["metrics"]["a_max"]),
                    "pred_error_radius": float(self.cfg["metrics"]["d_max"]),
                    "sigma": float(self.cfg["metrics"]["sigma_max"]),
                },
                bandwidth_min=self.bandwidth_min,
                bandwidth_max=self.bandwidth_max,
            )
            extras = {
                "threshold_value": float(certificate["required_margin"]),
                "risk_value": float(certificate["certificate_slack"]),
            }
            return dec.should_sync, float(dec.bandwidth), dec.reason, extras
        else:
            raise ValueError(f"Unknown sync method: {method}")
        extras = {
            "threshold_value": dec.threshold_value if dec.threshold_value is not None else -1.0,
            "risk_value": dec.risk_value if dec.risk_value is not None else -1.0,
        }
        return dec.should_sync, float(dec.bandwidth), dec.reason, extras

    def score_action(self, env, action: Dict[str, Any]) -> float:
        return float(env.evaluate_candidate(action, include_sync_penalty=True))

    def _top_move_pairs(self, env, sync_bandwidth: float) -> list[tuple[str, str]]:
        proxy_p_s = max(self.p_s_levels)
        proxy_p_j = self.p_j_levels[min(len(self.p_j_levels) - 1, max(0, len(self.p_j_levels) // 2))]
        scored = []
        for move1, move2 in itertools.product(self.step_moves, self.step_moves):
            action = {
                "move_uav1": move1,
                "move_uav2": move2,
                "p_s": proxy_p_s,
                "p_j": proxy_p_j,
                "sync": sync_bandwidth > 0.0,
                "sync_bandwidth": float(sync_bandwidth),
            }
            scored.append((self.score_action(env, action), (move1, move2)))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [pair for _, pair in scored[: self.move_candidate_limit]]

    def _top_power_pairs(self, env, sync_bandwidth: float) -> list[tuple[float, float]]:
        scored = []
        for p_s, p_j in itertools.product(self.p_s_levels, self.p_j_levels):
            action = {
                "move_uav1": "stay",
                "move_uav2": "stay",
                "p_s": p_s,
                "p_j": p_j,
                "sync": sync_bandwidth > 0.0,
                "sync_bandwidth": float(sync_bandwidth),
            }
            scored.append((self.score_action(env, action), (p_s, p_j)))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [pair for _, pair in scored[: self.power_candidate_limit]]

    def act(self, env, obs: Dict[str, Any], sync_method: str) -> Dict[str, Any]:
        do_sync, sync_bandwidth, reason, extras = self.choose_sync(
            method=sync_method,
            obs=obs,
            slot=int(obs["slot"]),
            remaining_budget=float(obs["remaining_budget"]),
        )

        best_score = None
        best_action = None
        move_pairs = self._top_move_pairs(env, sync_bandwidth)
        power_pairs = self._top_power_pairs(env, sync_bandwidth)
        for move1, move2 in move_pairs:
            for p_s, p_j in power_pairs:
                action = {
                    "move_uav1": move1,
                    "move_uav2": move2,
                    "p_s": p_s,
                    "p_j": p_j,
                    "sync": do_sync,
                    "sync_bandwidth": float(sync_bandwidth),
                    "sync_reason": reason,
                    "sync_threshold": extras["threshold_value"],
                    "sync_risk": extras["risk_value"],
                }
                score = self.score_action(env, action)
                if best_score is None or score > best_score:
                    best_score = score
                    best_action = action
        assert best_action is not None
        best_action["controller_score"] = float(best_score)
        return best_action
