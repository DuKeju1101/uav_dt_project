from __future__ import annotations

from typing import Any, Dict
import copy

from env.mobility import ALL_MOVES


class RandomBudgetedController:
    """
    A simple stochastic baseline that still respects sync budget.
    """

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = copy.deepcopy(cfg)
        self.step_moves = list(self.cfg["control"].get("allowed_moves", ALL_MOVES))
        self.p_s_levels = [float(x) for x in self.cfg["control"]["p_s_levels"]]
        self.p_j_levels = [float(x) for x in self.cfg["control"]["p_j_levels"]]

    def act(self, env, obs: Dict[str, Any]) -> Dict[str, Any]:
        rng = env.rng
        sync_prob = float(self.cfg["sync"].get("random_sync_prob", 0.35))
        do_sync = int(obs["remaining_budget"]) > 0 and bool(rng.random() < sync_prob)
        return {
            "move_uav1": self.step_moves[int(rng.integers(0, len(self.step_moves)))],
            "move_uav2": self.step_moves[int(rng.integers(0, len(self.step_moves)))],
            "p_s": self.p_s_levels[int(rng.integers(0, len(self.p_s_levels)))],
            "p_j": self.p_j_levels[int(rng.integers(0, len(self.p_j_levels)))],
            "sync": do_sync,
            "sync_reason": "random_budgeted_sync" if do_sync else "random_budgeted_skip",
            "controller_score": 0.0,
        }
