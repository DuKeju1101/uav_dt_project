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

    def choose_sync(self, method: str, obs: Dict[str, Any], slot: int, remaining_budget: int) -> Tuple[bool, str, Dict[str, float]]:
        sync_cfg = self.cfg["sync"]
        if method == "full":
            dec = SyncPolicies.full(slot=slot, remaining_budget=remaining_budget)
        elif method == "periodic":
            dec = SyncPolicies.periodic(slot=slot, remaining_budget=remaining_budget, k=int(sync_cfg["periodic_k"]))
        elif method == "aoi_only":
            dec = SyncPolicies.aoi_only(aoi=int(obs["aoi"]), remaining_budget=remaining_budget, aoi_threshold=int(sync_cfg["aoi_threshold"]))
        elif method == "security_risk":
            dec = SyncPolicies.security_risk(
                aoi=int(obs["aoi"]),
                pred_error_radius=float(obs["pred_error_radius"]),
                sigma=float(obs["twin_sigma"]),
                predicted_secrecy_rate=float(obs["pred_margin"] + self.r_min),
                r_safe=self.r_min,
                remaining_budget=remaining_budget,
                total_budget=int(sync_cfg["budget"]),
                w_risk=tuple(self.cfg["threshold"]["w_risk"]),
                tau0=float(sync_cfg["tau0"]),
                tau_budget_eta=float(sync_cfg["tau_budget_eta"]),
                a_max=float(self.cfg["metrics"]["a_max"]),
                d_max=float(self.cfg["metrics"]["d_max"]),
                sigma_max=float(self.cfg["metrics"]["sigma_max"]),
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
            )
            extras = {
                "threshold_value": float(certificate["required_margin"]),
                "risk_value": float(certificate["certificate_slack"]),
            }
            return dec.should_sync, dec.reason, extras
        else:
            raise ValueError(f"Unknown sync method: {method}")
        extras = {
            "threshold_value": dec.threshold_value if dec.threshold_value is not None else -1.0,
            "risk_value": dec.risk_value if dec.risk_value is not None else -1.0,
        }
        return dec.should_sync, dec.reason, extras

    def score_action(self, env, action: Dict[str, Any]) -> float:
        return float(env.evaluate_candidate(action, include_sync_penalty=True))

    def act(self, env, obs: Dict[str, Any], sync_method: str) -> Dict[str, Any]:
        do_sync, reason, extras = self.choose_sync(
            method=sync_method,
            obs=obs,
            slot=int(obs["slot"]),
            remaining_budget=int(obs["remaining_budget"]),
        )

        best_score = None
        best_action = None
        for move1, move2, p_s, p_j in itertools.product(self.step_moves, self.step_moves, self.p_s_levels, self.p_j_levels):
            action = {
                "move_uav1": move1,
                "move_uav2": move2,
                "p_s": p_s,
                "p_j": p_j,
                "sync": do_sync,
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
