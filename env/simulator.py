from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import copy
import numpy as np

from .entities import Eve, PointEntity, UAV, User, TwinState
from .mobility import apply_move, clip_area
from .channel import best_eve_interception_rate, best_user_metrics
from .twin import TwinConfig, TwinTracker, predicted_error_radius, twin_quality
from .sync import robust_secrecy_certificate, secrecy_loss_upper_bound


@dataclass
class StepResult:
    observation: Dict[str, Any]
    info: Dict[str, Any]
    done: bool


class UAVSecurityEnv:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = copy.deepcopy(config)
        self.delta_t = float(self.cfg["delta_t"])
        self.T = int(self.cfg["episode_length"])
        self.area = (float(self.cfg["area"]["width"]), float(self.cfg["area"]["height"]))
        self.height = float(self.cfg["height_uav"])
        self.bs = PointEntity("bs", np.array([self.cfg["bs"]["x"], self.cfg["bs"]["y"]], dtype=float))
        self.user_positions = [np.array(p, dtype=float) for p in self.cfg["users"]["positions"]]
        self.users = [User(name=f"user_{i}", position=p.copy()) for i, p in enumerate(self.user_positions)]
        self.twin_tracker = TwinTracker(
            TwinConfig(
                sigma0=float(self.cfg["sync"]["sigma0"]),
                velocity_sigma0=float(
                    self.cfg["sync"].get("kalman_velocity_sigma0", self.cfg["sync"].get("sigma_growth", 1.0))
                ),
                area=self.area,
                delta_t=self.delta_t,
                process_accel_std=float(self.cfg["sync"].get("kalman_process_accel_std", 1.0)),
                measurement_std_at_max_bw=float(self.cfg["sync"].get("measurement_std_at_max_bw", 1.0)),
                bandwidth_max=float(self.cfg["sync"].get("bandwidth_max", 1.0)),
                bandwidth_min=float(self.cfg["sync"].get("bandwidth_min", 0.25)),
            )
        )
        self.bandwidth_max = float(self.cfg["sync"].get("bandwidth_max", 1.0))
        self.bandwidth_min = float(self.cfg["sync"].get("bandwidth_min", 0.25))
        self.default_bandwidth = float(self.cfg["sync"].get("default_bandwidth", self.bandwidth_max))
        self.total_sync_budget = float(self.cfg["sync"]["budget"])
        self.rng = np.random.default_rng(int(self.cfg.get("seed", 42)))
        self.reset(seed=int(self.cfg.get("seed", 42)))

    def reset(self, seed: int | None = None) -> Dict[str, Any]:
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.slot = 0
        self.remaining_budget = float(self.total_sync_budget)
        self.total_sync_cost = 0.0
        self.sync_count = 0
        self.uav1 = UAV("uav1", np.array(self.cfg["uav1"]["start"], dtype=float))
        self.uav2 = UAV("uav2", np.array(self.cfg["uav2"]["start"], dtype=float))
        self.uav1.reset_history()
        self.uav2.reset_history()
        self.eve = Eve(
            "eve",
            np.array(self.cfg["eve"]["start"], dtype=float),
            velocity=np.array(self.cfg["eve"]["velocity"], dtype=float),
        )
        self.true_eve_history = [self.eve.position.copy()]
        self.twin = self.twin_tracker.initialize(self.eve)
        self.history: List[Dict[str, Any]] = []
        self.pending_syncs: List[Dict[str, float]] = []
        return self.get_observation()

    def clone_state(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "remaining_budget": self.remaining_budget,
            "total_sync_cost": self.total_sync_cost,
            "sync_count": self.sync_count,
            "uav1_pos": self.uav1.position.copy(),
            "uav2_pos": self.uav2.position.copy(),
            "eve_pos": self.eve.position.copy(),
            "eve_vel": self.eve.velocity.copy(),
            "twin": self.twin.copy(),
            "uav1_history": [p.copy() for p in self.uav1.history],
            "uav2_history": [p.copy() for p in self.uav2.history],
            "true_eve_history": [p.copy() for p in self.true_eve_history],
            "history": [dict(row) for row in self.history],
            "pending_syncs": [dict(item) for item in self.pending_syncs],
            "rng_state": copy.deepcopy(self.rng.bit_generator.state),
        }

    def restore_state(self, state: Dict[str, Any]) -> None:
        self.slot = state["slot"]
        self.remaining_budget = state["remaining_budget"]
        self.total_sync_cost = state["total_sync_cost"]
        self.sync_count = state["sync_count"]
        self.uav1.position = state["uav1_pos"].copy()
        self.uav2.position = state["uav2_pos"].copy()
        self.eve.position = state["eve_pos"].copy()
        self.eve.velocity = state["eve_vel"].copy()
        self.twin = state["twin"].copy()
        self.uav1.history = [p.copy() for p in state["uav1_history"]]
        self.uav2.history = [p.copy() for p in state["uav2_history"]]
        self.true_eve_history = [p.copy() for p in state["true_eve_history"]]
        self.history = [dict(row) for row in state["history"]]
        self.pending_syncs = [dict(item) for item in state["pending_syncs"]]
        self.rng.bit_generator.state = copy.deepcopy(state["rng_state"])

    def get_observation(self) -> Dict[str, Any]:
        eve_error = float(np.linalg.norm(self.eve.position - self.twin.eve_est))
        q = twin_quality(
            aoi=self.twin.aoi,
            eve_error=eve_error,
            sigma=self.twin.sigma,
            a_max=float(self.cfg["metrics"]["a_max"]),
            d_max=float(self.cfg["metrics"]["d_max"]),
            sigma_max=float(self.cfg["metrics"]["sigma_max"]),
            weights=tuple(self.cfg["metrics"]["q_weights"]),
        )
        pred_radius = predicted_error_radius(
            aoi=self.twin.aoi,
            v_max=float(np.linalg.norm(self.eve.velocity) + 3 * self.cfg["eve"].get("speed_noise_std", 0.0)),
            delta_t=self.delta_t,
        )
        pred_metrics = self.compute_best_metrics(use_twin=True, p_s=1.0, p_j=0.8)
        margin = pred_metrics["r_sec"] - float(self.cfg["channel"]["r_min"])
        loss_ub = secrecy_loss_upper_bound(
            aoi=self.twin.aoi,
            pred_error_radius=pred_radius,
            sigma=self.twin.sigma,
            kappa=tuple(self.cfg["threshold"]["kappa"]),
        )
        certificate = robust_secrecy_certificate(
            aoi=self.twin.aoi,
            pred_error_radius=pred_radius,
            sigma=self.twin.sigma,
            predicted_margin=margin,
            rho=float(self.cfg["sync"]["rho"]),
            sync_delay=int(self.cfg["sync"].get("delay_slots", 0)),
            failure_prob=float(self.cfg["sync"].get("failure_prob", 0.0)),
            kappa=tuple(self.cfg["threshold"]["kappa"]),
            theory=self.cfg["theory"].get("loss_model") and self.cfg["theory"] or tuple(self.cfg["theory"]["margin_coeffs"]),
            feature_scales={
                "aoi": float(self.cfg["metrics"]["a_max"]),
                "pred_error_radius": float(self.cfg["metrics"]["d_max"]),
                "sigma": float(self.cfg["metrics"]["sigma_max"]),
            },
        )
        obs = {
            "slot": self.slot,
            "uav1_pos": self.uav1.position.copy(),
            "uav2_pos": self.uav2.position.copy(),
            "bs_pos": self.bs.position.copy(),
            "users": [u.position.copy() for u in self.users],
            "true_eve_pos": self.eve.position.copy(),
            "twin_eve_pos": self.twin.eve_est.copy(),
            "twin_sigma": float(self.twin.sigma),
            "aoi": int(self.twin.aoi),
            "remaining_budget": float(self.remaining_budget),
            "remaining_budget_ratio": float(self.remaining_budget / max(self.total_sync_budget, 1e-12)),
            "twin_quality": q["quality"],
            "twin_badness": q["badness"],
            "pred_error_radius": pred_radius,
            "pred_margin": margin,
            "pred_loss_ub": loss_ub,
            "cert_base_bound": float(certificate["base_bound"]),
            "cert_empirical_upper_bound": float(certificate["empirical_upper_bound"]),
            "cert_required_margin": float(certificate["required_margin"]),
            "cert_slack": float(certificate["certificate_slack"]),
            "certified_safe": int(certificate["certified"]),
            "pending_syncs": int(len(self.pending_syncs)),
            "last_sync_bandwidth": float(self.twin.last_sync_bandwidth),
            "bandwidth_max": float(self.bandwidth_max),
        }
        return obs

    def compute_best_metrics(self, use_twin: bool, p_s: float, p_j: float) -> Dict[str, float]:
        eve_pos = self.twin.eve_est if use_twin else self.eve.position
        return best_user_metrics(
            uav1_pos=self.uav1.position,
            uav2_pos=self.uav2.position,
            eve_pos=eve_pos,
            user_positions=self.user_positions,
            p_s=p_s,
            p_j=p_j,
            height=self.height,
            beta0=float(self.cfg["channel"]["beta0"]),
            alpha=float(self.cfg["channel"]["path_loss_exp"]),
            noise_power=float(self.cfg["channel"]["noise_power"]),
            xi_legit_interference=float(self.cfg["channel"]["xi_legit_interference"]),
            channel_cfg=self.cfg["channel"],
        )

    def _resolve_sync_bandwidth(self, action: Dict[str, Any]) -> float:
        if not bool(action.get("sync", False)):
            return 0.0
        requested = float(action.get("sync_bandwidth", self.default_bandwidth))
        if requested <= 0.0:
            return 0.0
        if self.remaining_budget + 1e-12 < self.bandwidth_min:
            return 0.0
        return float(np.clip(requested, self.bandwidth_min, min(self.bandwidth_max, self.remaining_budget)))

    def _predict_next_eve_position(
        self,
        uav1_pos: np.ndarray,
        uav2_pos: np.ndarray,
        p_s: float,
        p_j: float,
    ) -> np.ndarray:
        eve_mode = str(self.cfg["eve"].get("mode", "mobile"))
        if eve_mode not in {"adaptive", "adaptive_mobile"}:
            return clip_area(self.eve.position + self.eve.velocity * self.delta_t, self.area)

        move_names = list(
            self.cfg["eve"].get(
                "adaptive_moves",
                ["stay", "up", "down", "left", "right", "up_left", "up_right", "down_left", "down_right"],
            )
        )
        max_speed = float(
            self.cfg["eve"].get(
                "max_speed",
                max(np.linalg.norm(self.eve.velocity), 1.0),
            )
        )
        step_size = max_speed * self.delta_t
        best_pos = self.eve.position.copy()
        best_score = None
        for move_name in move_names:
            candidate_pos = apply_move(self.eve.position.copy(), move_name, step_size, self.area)
            score = best_eve_interception_rate(
                uav1_pos=uav1_pos,
                uav2_pos=uav2_pos,
                eve_pos=candidate_pos,
                user_positions=self.user_positions,
                p_s=p_s,
                p_j=p_j,
                height=self.height,
                beta0=float(self.cfg["channel"]["beta0"]),
                alpha=float(self.cfg["channel"]["path_loss_exp"]),
                noise_power=float(self.cfg["channel"]["noise_power"]),
                channel_cfg=self.cfg["channel"],
            )
            if best_score is None or score > best_score:
                best_score = score
                best_pos = candidate_pos
        return clip_area(best_pos, self.area)

    def _project_pending_queue(
        self,
        queue: List[Dict[str, float]],
    ) -> tuple[list[float], list[Dict[str, float]]]:
        matured_bandwidths: list[float] = []
        updated_queue: list[Dict[str, float]] = []
        for item in queue:
            new_steps_left = float(item["steps_left"]) - 1.0
            if new_steps_left <= 0.0:
                matured_bandwidths.append(float(item["bandwidth"]))
            else:
                updated_queue.append({"steps_left": new_steps_left, "bandwidth": float(item["bandwidth"])})
        return matured_bandwidths, updated_queue

    def _project_next_twin(
        self,
        next_true_eve: np.ndarray,
        do_sync: bool,
        sync_bandwidth: float,
        use_true_eve: bool = False,
    ) -> tuple[TwinState, list[Dict[str, float]], bool]:
        projected_twin = self.twin.copy()
        matured_bandwidths, next_pending_queue = self._project_pending_queue(self.pending_syncs)
        sync_applied = False

        if matured_bandwidths:
            applied_bw = max(matured_bandwidths)
            projected_twin = self.twin_tracker.expected_sync(projected_twin, next_true_eve, applied_bw)
            sync_applied = True

        sync_delay = int(self.cfg["sync"].get("delay_slots", 0))
        if do_sync and sync_bandwidth > 0.0:
            if sync_delay <= 0:
                projected_twin = self.twin_tracker.expected_sync(projected_twin, next_true_eve, sync_bandwidth)
                sync_applied = True
            else:
                next_pending_queue.append({"steps_left": float(sync_delay), "bandwidth": float(sync_bandwidth)})

        if not sync_applied:
            projected_twin = self.twin_tracker.predict(projected_twin)

        if use_true_eve:
            projected_twin.eve_est = next_true_eve.copy()
        return projected_twin, next_pending_queue, sync_applied

    def evaluate_candidate(
        self,
        action: Dict[str, Any],
        include_sync_penalty: bool = True,
        use_true_eve: bool = False,
    ) -> float:
        move1 = action.get("move_uav1", "stay")
        move2 = action.get("move_uav2", "stay")
        p_s = float(action.get("p_s", 1.0))
        p_j = float(action.get("p_j", 0.8))
        sync_bandwidth = self._resolve_sync_bandwidth(action)
        do_sync = sync_bandwidth > 0.0

        next_uav1 = apply_move(self.uav1.position.copy(), move1, float(self.cfg["control"]["step_size"]), self.area)
        next_uav2 = apply_move(self.uav2.position.copy(), move2, float(self.cfg["control"]["step_size"]), self.area)
        next_true_eve = self._predict_next_eve_position(next_uav1, next_uav2, p_s, p_j)
        projected_twin, next_pending_queue, _ = self._project_next_twin(
            next_true_eve=next_true_eve,
            do_sync=do_sync,
            sync_bandwidth=sync_bandwidth,
            use_true_eve=use_true_eve,
        )
        est_eve = projected_twin.eve_est.copy()

        pred_metrics = best_user_metrics(
            uav1_pos=next_uav1,
            uav2_pos=next_uav2,
            eve_pos=est_eve,
            user_positions=self.user_positions,
            p_s=p_s,
            p_j=p_j,
            height=self.height,
            beta0=float(self.cfg["channel"]["beta0"]),
            alpha=float(self.cfg["channel"]["path_loss_exp"]),
            noise_power=float(self.cfg["channel"]["noise_power"]),
            xi_legit_interference=float(self.cfg["channel"]["xi_legit_interference"]),
            channel_cfg=self.cfg["channel"],
        )
        movement_cost = float(np.linalg.norm(next_uav1 - self.uav1.position) + np.linalg.norm(next_uav2 - self.uav2.position))
        power_cost = p_s + p_j
        sync_cost = float(sync_bandwidth) if do_sync and include_sync_penalty else 0.0
        r_min = float(self.cfg["channel"]["r_min"])
        pred_margin = pred_metrics["r_sec"] - r_min
        pred_radius = predicted_error_radius(
            aoi=projected_twin.aoi,
            v_max=float(np.linalg.norm(self.eve.velocity) + 3 * self.cfg["eve"].get("speed_noise_std", 0.0)),
            delta_t=self.delta_t,
        )
        cert = robust_secrecy_certificate(
            aoi=projected_twin.aoi,
            pred_error_radius=pred_radius,
            sigma=projected_twin.sigma,
            predicted_margin=pred_margin,
            rho=float(self.cfg["sync"]["rho"]),
            sync_delay=int(self.cfg["sync"].get("delay_slots", 0)),
            failure_prob=float(self.cfg["sync"].get("failure_prob", 0.0)),
            kappa=tuple(self.cfg["threshold"]["kappa"]),
            theory=self.cfg["theory"].get("loss_model") and self.cfg["theory"] or tuple(self.cfg["theory"]["margin_coeffs"]),
            feature_scales={
                "aoi": float(self.cfg["metrics"]["a_max"]),
                "pred_error_radius": float(self.cfg["metrics"]["d_max"]),
                "sigma": float(self.cfg["metrics"]["sigma_max"]),
            },
        )
        projected_badness = twin_quality(
            aoi=projected_twin.aoi,
            eve_error=float(np.linalg.norm(next_true_eve - est_eve)),
            sigma=projected_twin.sigma,
            a_max=float(self.cfg["metrics"]["a_max"]),
            d_max=float(self.cfg["metrics"]["d_max"]),
            sigma_max=float(self.cfg["metrics"]["sigma_max"]),
            weights=tuple(self.cfg["metrics"]["q_weights"]),
        )["badness"]
        lambda_outage = float(self.cfg["control"].get("lambda_outage", 0.0))
        lambda_certificate = float(self.cfg["control"].get("lambda_certificate", 0.0))
        lambda_certificate_relief = float(self.cfg["control"].get("lambda_certificate_relief", 0.0))
        lambda_sync_emergency_bonus = float(self.cfg["control"].get("lambda_sync_emergency_bonus", 0.0))
        lambda_backlog = float(self.cfg["control"].get("lambda_pending_sync", 0.0))
        lambda_badness = float(self.cfg["control"].get("lambda_badness", 0.0))
        lambda_margin = float(self.cfg["control"].get("lambda_margin", 0.0))
        outage_penalty = max(r_min - pred_metrics["r_sec"], 0.0)
        certificate_penalty = max(-float(cert["certificate_slack"]), 0.0)
        stress_relief = min(
            0.9,
            lambda_certificate_relief
            * (
                projected_badness
                + max(outage_penalty, 0.0) / max(r_min, 1e-12)
            ),
        )
        effective_certificate_penalty = certificate_penalty * max(0.1, 1.0 - stress_relief)
        margin_bonus = max(pred_margin, 0.0)
        emergency_sync_bonus = 0.0
        if do_sync and lambda_sync_emergency_bonus > 0.0:
            emergency_sync_bonus = lambda_sync_emergency_bonus * (
                projected_badness + max(outage_penalty, 0.0) / max(r_min, 1e-12)
            )
        score = (
            pred_metrics["r_sec"]
            - float(self.cfg["control"]["lambda_move"]) * movement_cost
            - float(self.cfg["control"]["lambda_power"]) * power_cost
            - float(self.cfg["control"]["lambda_sync"]) * sync_cost
            - lambda_outage * outage_penalty
            - lambda_certificate * effective_certificate_penalty
            - lambda_backlog * len(next_pending_queue)
            - lambda_badness * projected_badness
            + lambda_margin * margin_bonus
            + emergency_sync_bonus
        )
        # tiny regularization to discourage unnecessary staleness in tie cases
        score -= 0.001 * projected_twin.aoi
        return float(score)

    def _move_eve(self) -> None:
        noise_std = float(self.cfg["eve"].get("speed_noise_std", 0.0))
        eve_mode = str(self.cfg["eve"].get("mode", "mobile"))
        if eve_mode in {"adaptive", "adaptive_mobile"}:
            next_pos = self._predict_next_eve_position(self.uav1.position, self.uav2.position, self.uav1.power, self.uav2.power)
            if noise_std > 0.0:
                next_pos = next_pos + self.rng.normal(0.0, noise_std, size=2) * self.delta_t
            next_pos = clip_area(next_pos, self.area)
            self.eve.velocity = (next_pos - self.eve.position) / max(self.delta_t, 1e-12)
            self.eve.position = next_pos
        else:
            self.eve.step(delta_t=self.delta_t, noise_std=noise_std, rng=self.rng)
            self.eve.position = clip_area(self.eve.position, self.area)

    def _advance_pending_syncs(self) -> tuple[bool, float]:
        if not self.pending_syncs:
            return False, 0.0

        matured_bandwidths, updated_queue = self._project_pending_queue(self.pending_syncs)
        self.pending_syncs = updated_queue
        if not matured_bandwidths:
            return False, 0.0

        failure_prob = float(self.cfg["sync"].get("failure_prob", 0.0))
        if self.rng.random() < failure_prob:
            return False, 0.0

        applied_bw = max(matured_bandwidths)
        self.twin = self.twin_tracker.sync(self.twin, self.eve, applied_bw, rng=self.rng, noisy=True)
        return True, float(applied_bw)

    def step(self, action: Dict[str, Any]) -> StepResult:
        move1 = action.get("move_uav1", "stay")
        move2 = action.get("move_uav2", "stay")
        p_s = float(action.get("p_s", 1.0))
        p_j = float(action.get("p_j", 0.8))
        sync_bandwidth = self._resolve_sync_bandwidth(action)
        do_sync = sync_bandwidth > 0.0
        sync_cost = float(sync_bandwidth) if do_sync else 0.0
        sync_delay = int(self.cfg["sync"].get("delay_slots", 0))

        self.uav1.position = apply_move(self.uav1.position, move1, float(self.cfg["control"]["step_size"]), self.area)
        self.uav2.position = apply_move(self.uav2.position, move2, float(self.cfg["control"]["step_size"]), self.area)
        self.uav1.power = p_s
        self.uav2.power = p_j
        self.uav1.record()
        self.uav2.record()

        self._move_eve()
        self.true_eve_history.append(self.eve.position.copy())

        sync_applied, matured_bandwidth = self._advance_pending_syncs()
        if do_sync:
            self.remaining_budget -= sync_bandwidth
            self.total_sync_cost += sync_cost
            self.sync_count += 1
            if sync_delay <= 0:
                self.twin = self.twin_tracker.sync(self.twin, self.eve, sync_bandwidth, rng=self.rng, noisy=True)
                sync_applied = True
            else:
                self.pending_syncs.append({"steps_left": float(sync_delay), "bandwidth": float(sync_bandwidth)})
            sync_reason = action.get("sync_reason", "sync")
        else:
            sync_reason = action.get("sync_reason", "no_sync")

        if not sync_applied:
            self.twin = self.twin_tracker.predict(self.twin)

        true_metrics = self.compute_best_metrics(use_twin=False, p_s=p_s, p_j=p_j)
        pred_metrics = self.compute_best_metrics(use_twin=True, p_s=p_s, p_j=p_j)
        post_obs = self.get_observation()
        realized_loss = max(float(pred_metrics["r_sec"] - true_metrics["r_sec"]), 0.0)
        cert_cover = int(realized_loss <= float(post_obs["cert_required_margin"] - float(self.cfg["sync"]["rho"])))

        eve_error = float(np.linalg.norm(self.eve.position - self.twin.eve_est))
        twin_scores = twin_quality(
            aoi=self.twin.aoi,
            eve_error=eve_error,
            sigma=self.twin.sigma,
            a_max=float(self.cfg["metrics"]["a_max"]),
            d_max=float(self.cfg["metrics"]["d_max"]),
            sigma_max=float(self.cfg["metrics"]["sigma_max"]),
            weights=tuple(self.cfg["metrics"]["q_weights"]),
        )

        outage = 1 if true_metrics["r_sec"] < float(self.cfg["channel"]["r_min"]) else 0
        success = 1 - outage
        movement_cost = float(np.linalg.norm(self.uav1.history[-1] - self.uav1.history[-2]) + np.linalg.norm(self.uav2.history[-1] - self.uav2.history[-2]))
        power_cost = p_s + p_j

        info = {
            "slot": self.slot,
            "sync": int(do_sync),
            "sync_applied": int(sync_applied),
            "sync_reason": sync_reason,
            "sync_cost": sync_cost,
            "sync_bandwidth": float(sync_bandwidth),
            "matured_sync_bandwidth": float(matured_bandwidth),
            "total_sync_cost": self.total_sync_cost,
            "remaining_budget": self.remaining_budget,
            "pending_syncs": int(len(self.pending_syncs)),
            "move_uav1": move1,
            "move_uav2": move2,
            "p_s": p_s,
            "p_j": p_j,
            "uav1_x": float(self.uav1.position[0]),
            "uav1_y": float(self.uav1.position[1]),
            "uav2_x": float(self.uav2.position[0]),
            "uav2_y": float(self.uav2.position[1]),
            "eve_true_x": float(self.eve.position[0]),
            "eve_true_y": float(self.eve.position[1]),
            "eve_est_x": float(self.twin.eve_est[0]),
            "eve_est_y": float(self.twin.eve_est[1]),
            "eve_error": eve_error,
            "aoi": int(self.twin.aoi),
            "sigma": float(self.twin.sigma),
            "twin_quality": twin_scores["quality"],
            "twin_badness": twin_scores["badness"],
            "pred_r_sec": pred_metrics["r_sec"],
            "true_r_sec": true_metrics["r_sec"],
            "pred_margin": float(post_obs["pred_margin"]),
            "pred_error_radius": float(post_obs["pred_error_radius"]),
            "pred_loss_ub": float(post_obs["pred_loss_ub"]),
            "cert_base_bound": float(post_obs["cert_base_bound"]),
            "cert_empirical_upper_bound": float(post_obs["cert_empirical_upper_bound"]),
            "cert_required_margin": float(post_obs["cert_required_margin"]),
            "cert_slack": float(post_obs["cert_slack"]),
            "certified_safe": int(post_obs["certified_safe"]),
            "realized_loss": float(realized_loss),
            "cert_cover": int(cert_cover),
            "r_b": true_metrics["r_b"],
            "r_e": true_metrics["r_e"],
            "outage": outage,
            "success": success,
            "served_user_idx": int(true_metrics["user_idx"]),
            "movement_cost": movement_cost,
            "power_cost": power_cost,
        }
        self.history.append(info)
        self.slot += 1
        done = self.slot >= self.T
        return StepResult(observation=self.get_observation(), info=info, done=done)
