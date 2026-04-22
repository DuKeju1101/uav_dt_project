from __future__ import annotations

from typing import Any, Dict
import copy
import itertools

from env.mobility import ALL_MOVES
from env.sync import SyncPolicies


class DecoupledController:
    """
    First decide sync by a fixed rule, then optimize trajectory/power without charging sync cost
    inside the action score. This is the decoupled baseline.
    """

    def __init__(self, cfg: Dict[str, Any], sync_rule: str = "periodic"):
        self.cfg = copy.deepcopy(cfg)
        self.sync_rule = sync_rule
        self.step_moves = list(self.cfg["control"].get("allowed_moves", ALL_MOVES))
        self.p_s_levels = [float(x) for x in self.cfg["control"]["p_s_levels"]]
        self.p_j_levels = [float(x) for x in self.cfg["control"]["p_j_levels"]]
        self.lambda_move = float(self.cfg["control"]["lambda_move"])
        self.lambda_power = float(self.cfg["control"]["lambda_power"])
        self.bandwidth_min = float(self.cfg["sync"].get("bandwidth_min", 0.25))
        self.bandwidth_max = float(self.cfg["sync"].get("bandwidth_max", 1.0))
        self.move_candidate_limit = int(self.cfg["control"].get("greedy_move_candidates", 5))
        self.power_candidate_limit = int(self.cfg["control"].get("greedy_power_candidates", 3))

    def choose_sync(self, obs: Dict[str, Any]) -> tuple[bool, float, str]:
        rem = float(obs["remaining_budget"])
        if self.sync_rule == "periodic":
            dec = SyncPolicies.periodic(
                slot=int(obs["slot"]),
                remaining_budget=rem,
                k=int(self.cfg["sync"]["periodic_k"]),
                bandwidth_max=self.bandwidth_max,
                bandwidth_min=self.bandwidth_min,
            )
        elif self.sync_rule == "aoi_only":
            dec = SyncPolicies.aoi_only(
                aoi=int(obs["aoi"]),
                remaining_budget=rem,
                aoi_threshold=int(self.cfg["sync"]["aoi_threshold"]),
                bandwidth_min=self.bandwidth_min,
                bandwidth_max=self.bandwidth_max,
            )
        else:
            raise ValueError(f"Unknown decoupled sync rule: {self.sync_rule}")
        return dec.should_sync, float(dec.bandwidth), dec.reason

    def score_action(self, env, action: Dict[str, Any]) -> float:
        return float(env.evaluate_candidate(action, include_sync_penalty=False))

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

    def act(self, env, obs: Dict[str, Any]) -> Dict[str, Any]:
        do_sync, sync_bandwidth, reason = self.choose_sync(obs)
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
                    "sync_reason": f"decoupled_{reason}",
                }
                score = self.score_action(env, action)
                if best_score is None or score > best_score:
                    best_score = score
                    best_action = action
        assert best_action is not None
        best_action["controller_score"] = float(best_score)
        return best_action
