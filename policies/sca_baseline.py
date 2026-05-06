from __future__ import annotations

from typing import Any, Dict
import copy
import itertools

from env.mobility import ALL_MOVES


class SuccessiveApproximationController:
    """
    Lightweight SCA-style baseline.

    It solves the per-slot motion, power, and sync decision by repeatedly
    optimizing a local surrogate action set around the current best action.
    The twin variant scores candidates with the deployable twin estimate,
    while the oracle variant scores candidates with true Eve state.
    """

    def __init__(self, cfg: Dict[str, Any], use_oracle_state: bool = False):
        self.cfg = copy.deepcopy(cfg)
        self.step_moves = list(self.cfg["control"].get("allowed_moves", ALL_MOVES))
        self.p_s_levels = [float(x) for x in self.cfg["control"]["p_s_levels"]]
        self.p_j_levels = [float(x) for x in self.cfg["control"]["p_j_levels"]]
        self.bandwidth_levels = [
            float(x)
            for x in self.cfg["sync"].get(
                "bandwidth_levels",
                [self.cfg["sync"].get("bandwidth_max", 1.0)],
            )
            if float(x) > 0.0
        ]
        self.bandwidth_min = float(self.cfg["sync"].get("bandwidth_min", 0.25))
        self.use_oracle_state = bool(use_oracle_state)
        self.iterations = int(self.cfg["control"].get("sca_iterations", 3))
        self.move_window = int(self.cfg["control"].get("sca_move_window", 5))
        self.power_window = int(self.cfg["control"].get("sca_power_window", 3))
        self.candidate_limit = int(self.cfg["control"].get("sca_candidate_limit", 96))

    def _initial_action(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        p_s = self.p_s_levels[min(len(self.p_s_levels) - 1, max(0, len(self.p_s_levels) // 2 + 1))]
        p_j = self.p_j_levels[min(len(self.p_j_levels) - 1, max(0, len(self.p_j_levels) // 2))]
        return {
            "move_uav1": "stay",
            "move_uav2": "stay",
            "p_s": p_s,
            "p_j": p_j,
            "sync": False,
            "sync_bandwidth": 0.0,
            "sync_reason": "sca_skip",
        }

    def _score(self, env, action: Dict[str, Any]) -> float:
        return float(
            env.evaluate_candidate(
                action,
                include_sync_penalty=True,
                use_true_eve=self.use_oracle_state,
            )
        )

    def _rank_moves(self, env, base_action: Dict[str, Any]) -> list[tuple[str, str]]:
        scored = []
        for move1, move2 in itertools.product(self.step_moves, self.step_moves):
            action = dict(base_action)
            action["move_uav1"] = move1
            action["move_uav2"] = move2
            scored.append((self._score(env, action), (move1, move2)))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [pair for _, pair in scored[: self.move_window]]

    def _rank_powers(self, env, base_action: Dict[str, Any]) -> list[tuple[float, float]]:
        scored = []
        for p_s, p_j in itertools.product(self.p_s_levels, self.p_j_levels):
            action = dict(base_action)
            action["p_s"] = p_s
            action["p_j"] = p_j
            scored.append((self._score(env, action), (p_s, p_j)))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [pair for _, pair in scored[: self.power_window]]

    def _sync_options(self, obs: Dict[str, Any]) -> list[tuple[bool, float, str]]:
        options = [(False, 0.0, "sca_skip")]
        remaining_budget = float(obs["remaining_budget"])
        if remaining_budget + 1e-12 < self.bandwidth_min:
            return options
        feasible = [
            bandwidth
            for bandwidth in self.bandwidth_levels
            if bandwidth <= remaining_budget + 1e-12 and bandwidth >= self.bandwidth_min
        ]
        if not feasible:
            return options
        # Include a conservative low-bandwidth and the highest feasible option.
        selected = sorted({min(feasible), max(feasible)})
        for bandwidth in selected:
            options.append((True, float(bandwidth), "sca_sync"))
        return options

    def _candidate_actions(self, env, obs: Dict[str, Any], base_action: Dict[str, Any]) -> list[Dict[str, Any]]:
        move_pairs = self._rank_moves(env, base_action)
        power_pairs = self._rank_powers(env, base_action)
        actions: list[Dict[str, Any]] = []
        for move1, move2 in move_pairs:
            for p_s, p_j in power_pairs:
                for do_sync, bandwidth, reason in self._sync_options(obs):
                    actions.append(
                        {
                            "move_uav1": move1,
                            "move_uav2": move2,
                            "p_s": p_s,
                            "p_j": p_j,
                            "sync": do_sync,
                            "sync_bandwidth": bandwidth,
                            "sync_reason": reason,
                        }
                    )
        if len(actions) <= self.candidate_limit:
            return actions
        scored = [(self._score(env, action), action) for action in actions]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [action for _, action in scored[: self.candidate_limit]]

    def act(self, env, obs: Dict[str, Any]) -> Dict[str, Any]:
        best_action = self._initial_action(obs)
        best_score = self._score(env, best_action)
        for _ in range(max(1, self.iterations)):
            improved = False
            for action in self._candidate_actions(env, obs, best_action):
                score = self._score(env, action)
                if score > best_score:
                    best_score = score
                    best_action = dict(action)
                    improved = True
            if not improved:
                break
        best_action["controller_score"] = float(best_score)
        if self.use_oracle_state:
            best_action["sync_reason"] = "sca_oracle_sync" if best_action["sync"] else "sca_oracle_skip"
        return best_action
