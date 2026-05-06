from __future__ import annotations

from typing import Any, Dict
import copy
import itertools

from env.mobility import ALL_MOVES


class RolloutJointController:
    """
    A lightweight receding-horizon controller that jointly evaluates
    sync / motion / power decisions over a short rollout horizon.
    """

    def __init__(self, cfg: Dict[str, Any], use_oracle_state: bool = False):
        self.cfg = copy.deepcopy(cfg)
        self.step_moves = list(self.cfg["control"].get("allowed_moves", ALL_MOVES))
        self.p_s_levels = [float(x) for x in self.cfg["control"]["p_s_levels"]]
        self.p_j_levels = [float(x) for x in self.cfg["control"]["p_j_levels"]]
        self.sync_bandwidth_levels = [
            float(x)
            for x in self.cfg["sync"].get(
                "bandwidth_levels",
                [self.cfg["sync"].get("bandwidth_max", 1.0)],
            )
            if float(x) > 0.0
        ]
        self.bandwidth_min = float(self.cfg["sync"].get("bandwidth_min", 0.25))
        self.move_candidate_limit = int(self.cfg["control"].get("rollout_move_candidates", 5))
        self.power_candidate_limit = int(self.cfg["control"].get("rollout_power_candidates", 3))
        self.single_move_prefilter = int(
            self.cfg["control"].get(
                "rollout_single_move_prefilter",
                max(self.move_candidate_limit, min(len(self.step_moves), 5)),
            )
        )
        self.rollout_horizon = int(self.cfg["control"].get("rollout_horizon", 3))
        self.gamma = float(self.cfg["control"].get("rollout_gamma", 0.92))
        self.branching_limit = int(self.cfg["control"].get("rollout_branching", 16))
        self.deep_branching_limit = int(
            self.cfg["control"].get(
                "rollout_deep_branching",
                max(4, min(self.branching_limit, self.branching_limit // 3)),
            )
        )
        self.tail_branching_limit = int(
            self.cfg["control"].get(
                "rollout_tail_branching",
                max(2, min(self.deep_branching_limit, 3)),
            )
        )
        self.min_sync_branching = int(
            self.cfg["control"].get(
                "rollout_min_sync_branching",
                max(2, min(4, self.branching_limit // 3)),
            )
        )
        self.min_tail_sync_branching = int(
            self.cfg["control"].get(
                "rollout_min_tail_sync_branching",
                max(1, min(2, self.tail_branching_limit // 2 if self.tail_branching_limit > 1 else 1)),
            )
        )
        self.use_oracle_state = bool(use_oracle_state)
        self.force_sync_badness_threshold = self.cfg["control"].get("rollout_force_sync_badness_threshold")
        self.force_sync_margin_threshold = self.cfg["control"].get("rollout_force_sync_margin_threshold")
        self.force_sync_if_unsafe = bool(self.cfg["control"].get("rollout_force_sync_if_unsafe", False))
        self.force_sync_aoi_threshold = int(
            self.cfg["control"].get(
                "rollout_force_sync_aoi_threshold",
                max(2, int(self.cfg["sync"].get("aoi_threshold", 5)) - 1),
            )
        )
        self.force_hold_when_safe = bool(self.cfg["control"].get("rollout_force_hold_when_safe", True))
        self.safe_badness_threshold = float(
            self.cfg["control"].get("rollout_safe_badness_threshold", 0.16)
        )
        self.safe_margin_threshold = float(
            self.cfg["control"].get("rollout_safe_margin_threshold", 0.06)
        )
        self.safe_cert_slack_threshold = float(
            self.cfg["control"].get("rollout_safe_cert_slack_threshold", 0.08)
        )
        self.safe_aoi_threshold = int(self.cfg["control"].get("rollout_safe_aoi_threshold", 1))
        self.rollout_budget_guard_ratio = float(self.cfg["control"].get("rollout_budget_guard_ratio", 0.35))
        self.resync_cooldown_aoi = int(self.cfg["control"].get("rollout_resync_cooldown_aoi", 0))
        self.fixed_sync_rule = str(self.cfg["control"].get("rollout_fixed_sync_rule", "free"))
        self.fixed_sync_periodic_k = int(
            self.cfg["control"].get("rollout_fixed_sync_periodic_k", self.cfg["sync"].get("periodic_k", 1))
        )
        self._eval_cache: dict[tuple[Any, ...], float] = {}

    def _state_cache_key(self, env) -> tuple[Any, ...]:
        pending = tuple(
            (round(float(item["steps_left"]), 4), round(float(item["bandwidth"]), 4))
            for item in env.pending_syncs
        )
        return (
            int(env.slot),
            round(float(env.remaining_budget), 4),
            round(float(env.total_sync_cost), 4),
            int(env.sync_count),
            tuple(round(float(x), 3) for x in env.uav1.position),
            tuple(round(float(x), 3) for x in env.uav2.position),
            tuple(round(float(x), 3) for x in env.eve.position),
            tuple(round(float(x), 3) for x in env.eve.velocity),
            tuple(round(float(x), 3) for x in env.twin.state),
            int(env.twin.aoi),
            round(float(env.twin.sigma), 3),
            round(float(env.twin.last_sync_bandwidth), 3),
            pending,
        )

    def _action_cache_key(
        self,
        env,
        action: Dict[str, Any],
        include_sync_penalty: bool,
    ) -> tuple[Any, ...]:
        return (
            self._state_cache_key(env),
            bool(include_sync_penalty),
            bool(self.use_oracle_state),
            str(action.get("move_uav1", "stay")),
            str(action.get("move_uav2", "stay")),
            round(float(action.get("p_s", 0.0)), 4),
            round(float(action.get("p_j", 0.0)), 4),
            bool(action.get("sync", False)),
            round(float(action.get("sync_bandwidth", 0.0)), 4),
        )

    def _score_action_cached(
        self,
        env,
        action: Dict[str, Any],
        include_sync_penalty: bool,
    ) -> float:
        key = self._action_cache_key(env, action, include_sync_penalty)
        cached = self._eval_cache.get(key)
        if cached is not None:
            return cached
        score = float(
            env.evaluate_candidate(
                action,
                include_sync_penalty=include_sync_penalty,
                use_true_eve=self.use_oracle_state,
            )
        )
        self._eval_cache[key] = score
        return score

    def _merge_ranked_pairs(
        self,
        primary: list[tuple[float, tuple]],
        secondary: list[tuple[float, tuple]],
        limit: int,
    ) -> list[tuple]:
        merged: list[tuple] = []
        seen: set[tuple] = set()
        for bucket in (primary, secondary):
            for _, pair in bucket:
                if pair in seen:
                    continue
                merged.append(pair)
                seen.add(pair)
                if len(merged) >= limit:
                    return merged
        return merged

    def _top_move_pairs(self, env, representative_sync_bw: float = 0.0) -> list[tuple[str, str]]:
        proxy_p_s = max(self.p_s_levels)
        proxy_p_j = self.p_j_levels[min(len(self.p_j_levels) - 1, max(0, len(self.p_j_levels) // 2))]
        candidate_moves = self.step_moves
        if 0 < self.single_move_prefilter < len(self.step_moves):
            scored_uav1: list[tuple[float, str]] = []
            scored_uav2: list[tuple[float, str]] = []
            for move in self.step_moves:
                action_uav1 = {
                    "move_uav1": move,
                    "move_uav2": "stay",
                    "p_s": proxy_p_s,
                    "p_j": proxy_p_j,
                    "sync": False,
                    "sync_bandwidth": 0.0,
                }
                action_uav2 = {
                    "move_uav1": "stay",
                    "move_uav2": move,
                    "p_s": proxy_p_s,
                    "p_j": proxy_p_j,
                    "sync": False,
                    "sync_bandwidth": 0.0,
                }
                scored_uav1.append((self._score_action_cached(env, action_uav1, include_sync_penalty=False), move))
                scored_uav2.append((self._score_action_cached(env, action_uav2, include_sync_penalty=False), move))
            scored_uav1.sort(key=lambda item: item[0], reverse=True)
            scored_uav2.sort(key=lambda item: item[0], reverse=True)
            selected = {"stay"}
            selected.update(move for _, move in scored_uav1[: self.single_move_prefilter])
            selected.update(move for _, move in scored_uav2[: self.single_move_prefilter])
            candidate_moves = [move for move in self.step_moves if move in selected]

        scored_nosync: list[tuple[float, tuple[str, str]]] = []
        scored_sync: list[tuple[float, tuple[str, str]]] = []
        for move1, move2 in itertools.product(candidate_moves, candidate_moves):
            action_nosync = {
                "move_uav1": move1,
                "move_uav2": move2,
                "p_s": proxy_p_s,
                "p_j": proxy_p_j,
                "sync": False,
                "sync_bandwidth": 0.0,
            }
            score_nosync = self._score_action_cached(env, action_nosync, include_sync_penalty=False)
            scored_nosync.append((score_nosync, (move1, move2)))
            if representative_sync_bw > 0.0:
                action_sync = dict(action_nosync)
                action_sync["sync"] = True
                action_sync["sync_bandwidth"] = float(representative_sync_bw)
                score_sync = self._score_action_cached(env, action_sync, include_sync_penalty=False)
                scored_sync.append((score_sync, (move1, move2)))
        scored_nosync.sort(key=lambda item: item[0], reverse=True)
        scored_sync.sort(key=lambda item: item[0], reverse=True)
        return self._merge_ranked_pairs(scored_nosync, scored_sync, self.move_candidate_limit)

    def _top_power_pairs(self, env, representative_sync_bw: float = 0.0) -> list[tuple[float, float]]:
        scored_nosync: list[tuple[float, tuple[float, float]]] = []
        scored_sync: list[tuple[float, tuple[float, float]]] = []
        for p_s, p_j in itertools.product(self.p_s_levels, self.p_j_levels):
            action_nosync = {
                "move_uav1": "stay",
                "move_uav2": "stay",
                "p_s": p_s,
                "p_j": p_j,
                "sync": False,
                "sync_bandwidth": 0.0,
            }
            score_nosync = self._score_action_cached(env, action_nosync, include_sync_penalty=False)
            scored_nosync.append((score_nosync, (p_s, p_j)))
            if representative_sync_bw > 0.0:
                action_sync = dict(action_nosync)
                action_sync["sync"] = True
                action_sync["sync_bandwidth"] = float(representative_sync_bw)
                score_sync = self._score_action_cached(env, action_sync, include_sync_penalty=False)
                scored_sync.append((score_sync, (p_s, p_j)))
        scored_nosync.sort(key=lambda item: item[0], reverse=True)
        scored_sync.sort(key=lambda item: item[0], reverse=True)
        return self._merge_ranked_pairs(scored_nosync, scored_sync, self.power_candidate_limit)

    def _action_space(self, env, remaining_budget: float) -> list[Dict[str, Any]]:
        feasible_sync_bandwidths = tuple(
            bw for bw in self.sync_bandwidth_levels if bw <= float(remaining_budget) + 1e-12 and bw >= self.bandwidth_min
        )
        representative_sync_bw = max(feasible_sync_bandwidths) if feasible_sync_bandwidths else 0.0
        move_pairs = self._top_move_pairs(env, representative_sync_bw=representative_sync_bw)
        power_pairs = self._top_power_pairs(env, representative_sync_bw=representative_sync_bw)
        actions = []
        for move1, move2 in move_pairs:
            for p_s, p_j in power_pairs:
                actions.append(
                    {
                        "move_uav1": move1,
                        "move_uav2": move2,
                        "p_s": p_s,
                        "p_j": p_j,
                        "sync": False,
                        "sync_bandwidth": 0.0,
                        "sync_reason": "rollout_skip",
                    }
                )
                for bandwidth in feasible_sync_bandwidths:
                    actions.append(
                        {
                            "move_uav1": move1,
                            "move_uav2": move2,
                            "p_s": p_s,
                            "p_j": p_j,
                            "sync": True,
                            "sync_bandwidth": float(bandwidth),
                            "sync_reason": "rollout_joint",
                        }
                    )
        return [dict(action) for action in actions]

    def _scored_candidates(self, env, remaining_budget: float, limit: int) -> list[tuple[float, Dict[str, Any]]]:
        actions = self._action_space(env, remaining_budget)
        if len(actions) <= limit:
            return [
                (self._score_action_cached(env, action, include_sync_penalty=True), action)
                for action in actions
            ]

        scored = []
        for action in actions:
            score = self._score_action_cached(env, action, include_sync_penalty=True)
            scored.append((score, action))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:limit]

    def _greedy_tail_value(self, env, depth: int) -> float:
        if depth <= 0:
            return 0.0

        obs = env.get_observation()
        scored = self._scored_candidates(env, float(obs["remaining_budget"]), self.tail_branching_limit * 3)
        scored = self._diversify_candidates(
            scored,
            limit=self.tail_branching_limit,
            min_sync=self.min_tail_sync_branching if float(obs["remaining_budget"]) >= self.bandwidth_min else 0,
        )
        if not scored:
            return 0.0

        best_immediate, best_action = scored[0]
        state = env.clone_state()
        result = env.step(best_action)
        future = 0.0 if result.done else self.gamma * self._greedy_tail_value(env, depth - 1)
        env.restore_state(state)
        return float(best_immediate + future)

    def _root_candidates(
        self,
        env,
        remaining_budget: float,
        force_sync_only: bool = False,
        force_nosync_only: bool = False,
    ) -> list[tuple[float, Dict[str, Any]]]:
        if force_sync_only or force_nosync_only:
            actions = self._action_space(env, remaining_budget)
            if force_sync_only:
                actions = [action for action in actions if float(action.get("sync_bandwidth", 0.0)) > 0.0]
            else:
                actions = [action for action in actions if float(action.get("sync_bandwidth", 0.0)) <= 0.0]
            scored = [
                (self._score_action_cached(env, action, include_sync_penalty=True), action)
                for action in actions
            ]
            scored.sort(key=lambda item: item[0], reverse=True)
            scored = scored[: self.branching_limit * 3]
        else:
            scored = self._scored_candidates(env, remaining_budget, self.branching_limit * 3)
        return self._diversify_candidates(
            scored,
            limit=self.branching_limit,
            min_sync=self.min_sync_branching if (remaining_budget >= self.bandwidth_min and not force_nosync_only) else 0,
        )

    def _rollout_value(self, env, depth: int) -> float:
        return self._greedy_tail_value(env, depth)

    def _fixed_sync_gate(self, obs: Dict[str, Any]) -> tuple[str, str]:
        if self.fixed_sync_rule in {"", "free", "adaptive"}:
            return "free", "rollout_adaptive_sync"
        if float(obs["remaining_budget"]) < self.bandwidth_min:
            return "force_nosync", "fixed_sync_budget_exhausted"
        if self.fixed_sync_rule == "never":
            return "force_nosync", "fixed_sync_never"
        if self.fixed_sync_rule == "periodic":
            slot = int(obs.get("slot", 0))
            if (slot % max(self.fixed_sync_periodic_k, 1)) == 0:
                return "force_sync", f"fixed_periodic_k={self.fixed_sync_periodic_k}"
            return "force_nosync", f"fixed_periodic_skip_k={self.fixed_sync_periodic_k}"
        raise ValueError(f"Unknown rollout_fixed_sync_rule: {self.fixed_sync_rule}")

    def _diversify_candidates(
        self,
        scored: list[tuple[float, Dict[str, Any]]],
        limit: int,
        min_sync: int,
    ) -> list[tuple[float, Dict[str, Any]]]:
        if len(scored) <= limit:
            return scored

        sync_scored = [item for item in scored if float(item[1].get("sync_bandwidth", 0.0)) > 0.0]
        picked: list[tuple[float, Dict[str, Any]]] = []
        used_ids: set[int] = set()

        for bucket, need in ((sync_scored, min_sync),):
            for item in bucket[: max(0, min(need, limit))]:
                picked.append(item)
                used_ids.add(id(item[1]))

        for item in scored:
            if len(picked) >= limit:
                break
            if id(item[1]) in used_ids:
                continue
            picked.append(item)
            used_ids.add(id(item[1]))

        picked.sort(key=lambda item: item[0], reverse=True)
        return picked[:limit]

    def act(self, env, obs: Dict[str, Any]) -> Dict[str, Any]:
        self._eval_cache = {}
        force_sync_only = False
        force_nosync_only = False
        forced_sync_reason = None
        forced_nosync_reason = None

        sync_gate, fixed_sync_reason = self._fixed_sync_gate(obs)
        if sync_gate == "force_sync":
            force_sync_only = True
            forced_sync_reason = fixed_sync_reason
        elif sync_gate == "force_nosync":
            force_nosync_only = True
            forced_nosync_reason = fixed_sync_reason

        if sync_gate == "free" and float(obs["remaining_budget"]) >= self.bandwidth_min:
            aoi = int(obs.get("aoi", 0))
            badness = float(obs.get("decision_twin_badness", obs.get("twin_badness", 0.0)))
            pred_margin = float(obs.get("pred_margin", 0.0))
            cert_slack = float(obs.get("cert_slack", 0.0))
            unsafe = int(obs.get("certified_safe", 1)) == 0
            budget_ratio = float(obs["remaining_budget"]) / max(float(self.cfg["sync"].get("budget", 1.0)), 1e-12)
            high_badness = (
                self.force_sync_badness_threshold is not None
                and badness >= float(self.force_sync_badness_threshold)
            )
            low_margin = (
                self.force_sync_margin_threshold is not None
                and pred_margin <= float(self.force_sync_margin_threshold)
            )
            stale_twin = bool(high_badness or aoi >= self.force_sync_aoi_threshold)
            low_risk_hold = bool(
                self.force_hold_when_safe
                and (not unsafe)
                and badness <= self.safe_badness_threshold
                and pred_margin >= self.safe_margin_threshold
                and cert_slack >= self.safe_cert_slack_threshold
                and aoi <= self.safe_aoi_threshold
            )
            emergency_force_sync = bool(
                ((self.force_sync_if_unsafe and unsafe) or low_margin) and stale_twin
            )
            if emergency_force_sync:
                force_sync_only = True
                forced_sync_reason = "rollout_emergency_force_sync"
            elif (
                self.resync_cooldown_aoi > 0
                and int(obs.get("slot", 0)) > 0
                and aoi < self.resync_cooldown_aoi
            ):
                force_nosync_only = True
                forced_nosync_reason = "rollout_resync_cooldown"
            elif budget_ratio <= self.rollout_budget_guard_ratio:
                force_nosync_only = True
                forced_nosync_reason = "rollout_budget_guard"
            elif low_risk_hold:
                force_nosync_only = True
                forced_nosync_reason = "rollout_secrecy_guard"

        best_action = None
        best_value = None
        root_candidates = self._root_candidates(
            env,
            float(obs["remaining_budget"]),
            force_sync_only=force_sync_only,
            force_nosync_only=force_nosync_only,
        )
        if not root_candidates and force_sync_only:
            root_candidates = self._root_candidates(
                env,
                float(obs["remaining_budget"]),
                force_sync_only=False,
                force_nosync_only=False,
            )
        if not root_candidates and force_nosync_only:
            root_candidates = self._root_candidates(
                env,
                float(obs["remaining_budget"]),
                force_sync_only=False,
                force_nosync_only=False,
            )

        for immediate, action in root_candidates:
            state = env.clone_state()
            result = env.step(action)
            future = 0.0 if result.done else self.gamma * self._rollout_value(env, self.rollout_horizon - 1)
            total = immediate + future
            env.restore_state(state)
            if best_value is None or total > best_value:
                best_value = total
                best_action = dict(action)

        assert best_action is not None
        best_action["controller_score"] = float(best_value)
        if self.use_oracle_state:
            best_action["sync_reason"] = "oracle_rollout_sync" if best_action["sync"] else "oracle_rollout_skip"
        elif best_action["sync"] and forced_sync_reason is not None:
            best_action["sync_reason"] = forced_sync_reason
        elif (not best_action["sync"]) and forced_nosync_reason is not None:
            best_action["sync_reason"] = forced_nosync_reason
        return best_action
