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
        self.p_s_levels = [float(x) for x in self.cfg["control"]["p_s_levels"]]
        self.p_j_levels = [float(x) for x in self.cfg["control"]["p_j_levels"]]
        self.lambda_move = float(self.cfg["control"]["lambda_move"])
        self.lambda_power = float(self.cfg["control"]["lambda_power"])

    def choose_sync(self, obs: Dict[str, Any]) -> tuple[bool, str]:
        rem = int(obs["remaining_budget"])
        if self.sync_rule == "periodic":
            dec = SyncPolicies.periodic(
                slot=int(obs["slot"]),
                remaining_budget=rem,
                k=int(self.cfg["sync"]["periodic_k"]),
            )
        elif self.sync_rule == "aoi_only":
            dec = SyncPolicies.aoi_only(
                aoi=int(obs["aoi"]),
                remaining_budget=rem,
                aoi_threshold=int(self.cfg["sync"]["aoi_threshold"]),
            )
        else:
            raise ValueError(f"Unknown decoupled sync rule: {self.sync_rule}")
        return dec.should_sync, dec.reason

    def score_action(self, env, action: Dict[str, Any]) -> float:
        return float(env.evaluate_candidate(action, include_sync_penalty=False))

    def act(self, env, obs: Dict[str, Any]) -> Dict[str, Any]:
        do_sync, reason = self.choose_sync(obs)
        best_score = None
        best_action = None
        for move1, move2, p_s, p_j in itertools.product(self.cfg["control"].get("allowed_moves", ALL_MOVES), self.cfg["control"].get("allowed_moves", ALL_MOVES), self.p_s_levels, self.p_j_levels):
            action = {
                "move_uav1": move1,
                "move_uav2": move2,
                "p_s": p_s,
                "p_j": p_j,
                "sync": do_sync,
                "sync_reason": f"decoupled_{reason}",
            }
            score = self.score_action(env, action)
            if best_score is None or score > best_score:
                best_score = score
                best_action = action
        assert best_action is not None
        best_action["controller_score"] = float(best_score)
        return best_action
