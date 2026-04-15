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
        self._action_cache: dict[bool, list[Dict[str, Any]]] = {}
        self.force_sync_badness_threshold = self.cfg["control"].get("rollout_force_sync_badness_threshold")
        self.force_sync_margin_threshold = self.cfg["control"].get("rollout_force_sync_margin_threshold")
        self.force_sync_if_unsafe = bool(self.cfg["control"].get("rollout_force_sync_if_unsafe", False))
        self.hybrid_enable = bool(self.cfg["control"].get("rollout_hybrid_enable", False))
        self.hybrid_periodic_k = int(
            self.cfg["control"].get("rollout_hybrid_periodic_k", self.cfg["sync"].get("periodic_k", 6))
        )
        self.hybrid_badness_low = float(self.cfg["control"].get("rollout_hybrid_badness_low", 0.16))
        self.hybrid_badness_high = float(self.cfg["control"].get("rollout_hybrid_badness_high", 0.25))
        self.hybrid_margin_low = float(self.cfg["control"].get("rollout_hybrid_margin_low", -0.08))
        self.hybrid_margin_high = float(self.cfg["control"].get("rollout_hybrid_margin_high", 0.06))
        self.hybrid_cert_slack_low = float(self.cfg["control"].get("rollout_hybrid_cert_slack_low", 0.08))
        self.hybrid_outage_pressure_threshold = float(
            self.cfg["control"].get("rollout_hybrid_outage_pressure_threshold", 0.015)
        )
        self.hybrid_force_hold_when_safe = bool(
            self.cfg["control"].get("rollout_hybrid_force_hold_when_safe", True)
        )
        self.hybrid_budget_guard_ratio = float(self.cfg["control"].get("rollout_hybrid_budget_guard_ratio", 0.35))

    def _action_space(self, remaining_budget: int) -> list[Dict[str, Any]]:
        has_budget = remaining_budget > 0
        if has_budget in self._action_cache:
            return [dict(action) for action in self._action_cache[has_budget]]

        sync_choices = [False, True] if has_budget else [False]
        actions = []
        for move1, move2, p_s, p_j, sync_flag in itertools.product(
            self.step_moves,
            self.step_moves,
            self.p_s_levels,
            self.p_j_levels,
            sync_choices,
        ):
            actions.append(
                {
                    "move_uav1": move1,
                    "move_uav2": move2,
                    "p_s": p_s,
                    "p_j": p_j,
                    "sync": sync_flag,
                    "sync_reason": "rollout_joint" if sync_flag else "rollout_skip",
                }
            )
        self._action_cache[has_budget] = [dict(action) for action in actions]
        return [dict(action) for action in actions]

    def _scored_candidates(self, env, remaining_budget: int, limit: int) -> list[tuple[float, Dict[str, Any]]]:
        actions = self._action_space(remaining_budget)
        if len(actions) <= limit:
            return [
                (
                    float(
                        env.evaluate_candidate(
                            action,
                            include_sync_penalty=True,
                            use_true_eve=self.use_oracle_state,
                        )
                    ),
                    action,
                )
                for action in actions
            ]

        scored = []
        for action in actions:
            score = float(
                env.evaluate_candidate(
                    action,
                    include_sync_penalty=True,
                    use_true_eve=self.use_oracle_state,
                )
            )
            scored.append((score, action))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:limit]

    def _greedy_tail_value(self, env, depth: int) -> float:
        if depth <= 0:
            return 0.0

        obs = env.get_observation()
        scored = self._scored_candidates(env, int(obs["remaining_budget"]), self.tail_branching_limit * 3)
        scored = self._diversify_candidates(
            scored,
            limit=self.tail_branching_limit,
            min_sync=self.min_tail_sync_branching if int(obs["remaining_budget"]) > 0 else 0,
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
        remaining_budget: int,
        force_sync_only: bool = False,
        force_nosync_only: bool = False,
    ) -> list[tuple[float, Dict[str, Any]]]:
        scored = self._scored_candidates(env, remaining_budget, self.branching_limit * 3)
        if force_sync_only:
            scored = [item for item in scored if bool(item[1].get("sync", False))]
        elif force_nosync_only:
            scored = [item for item in scored if not bool(item[1].get("sync", False))]
        return self._diversify_candidates(
            scored,
            limit=self.branching_limit,
            min_sync=self.min_sync_branching if (remaining_budget > 0 and not force_nosync_only) else 0,
        )

    def _rollout_value(self, env, depth: int) -> float:
        return self._greedy_tail_value(env, depth)

    def _hybrid_sync_gate(self, obs: Dict[str, Any]) -> tuple[str, str]:
        if not self.hybrid_enable or int(obs["remaining_budget"]) <= 0:
            return "free", "rollout_default"

        slot = int(obs.get("slot", 0))
        periodic_hit = (slot % max(self.hybrid_periodic_k, 1)) == 0
        certified_safe = int(obs.get("certified_safe", 1)) == 1
        badness = float(obs.get("twin_badness", 0.0))
        pred_margin = float(obs.get("pred_margin", 0.0))
        cert_slack = float(obs.get("cert_slack", 0.0))
        outage_pressure = max(-pred_margin, 0.0)
        budget_ratio = int(obs["remaining_budget"]) / max(int(self.cfg["sync"].get("budget", 1)), 1)

        high_risk = (
            (not certified_safe)
            or badness >= self.hybrid_badness_high
            or pred_margin <= self.hybrid_margin_low
            or cert_slack <= 0.0
            or outage_pressure >= self.hybrid_outage_pressure_threshold
        )
        low_risk = (
            certified_safe
            and badness <= self.hybrid_badness_low
            and pred_margin >= self.hybrid_margin_high
            and cert_slack >= self.hybrid_cert_slack_low
        )

        if high_risk:
            if budget_ratio <= self.hybrid_budget_guard_ratio and not periodic_hit:
                return "force_nosync", "hybrid_budget_guard"
            return "force_sync", "hybrid_outage_priority"
        if periodic_hit:
            return "force_sync", f"hybrid_periodic_refresh_k={self.hybrid_periodic_k}"
        if low_risk and self.hybrid_force_hold_when_safe:
            return "force_nosync", "hybrid_secrecy_guard"
        return "free", "hybrid_transition"

    def _diversify_candidates(
        self,
        scored: list[tuple[float, Dict[str, Any]]],
        limit: int,
        min_sync: int,
    ) -> list[tuple[float, Dict[str, Any]]]:
        if len(scored) <= limit:
            return scored

        sync_scored = [item for item in scored if bool(item[1].get("sync", False))]
        nonsync_scored = [item for item in scored if not bool(item[1].get("sync", False))]

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
        force_sync_only = False
        force_nosync_only = False
        forced_sync_reason = None
        forced_nosync_reason = None

        sync_gate, hybrid_reason = self._hybrid_sync_gate(obs)
        if int(obs["remaining_budget"]) > 0:
            unsafe = int(obs.get("certified_safe", 1)) == 0
            high_badness = (
                self.force_sync_badness_threshold is not None
                and float(obs.get("twin_badness", 0.0)) >= float(self.force_sync_badness_threshold)
            )
            low_margin = (
                self.force_sync_margin_threshold is not None
                and float(obs.get("pred_margin", 0.0)) <= float(self.force_sync_margin_threshold)
            )
            emergency_force_sync = bool((self.force_sync_if_unsafe and unsafe and high_badness) or low_margin)
            if emergency_force_sync:
                force_sync_only = True
                forced_sync_reason = "rollout_emergency_force_sync"
            elif sync_gate == "force_sync":
                force_sync_only = True
                forced_sync_reason = hybrid_reason
            elif sync_gate == "force_nosync":
                force_nosync_only = True
                forced_nosync_reason = hybrid_reason

        best_action = None
        best_value = None
        root_candidates = self._root_candidates(
            env,
            int(obs["remaining_budget"]),
            force_sync_only=force_sync_only,
            force_nosync_only=force_nosync_only,
        )
        if not root_candidates and force_sync_only:
            root_candidates = self._root_candidates(
                env,
                int(obs["remaining_budget"]),
                force_sync_only=False,
                force_nosync_only=False,
            )
        if not root_candidates and force_nosync_only:
            root_candidates = self._root_candidates(
                env,
                int(obs["remaining_budget"]),
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
