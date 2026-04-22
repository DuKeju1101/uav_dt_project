from __future__ import annotations

import argparse
import copy
import itertools
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from experiments.common import ROOT, load_config
from env.simulator import UAVSecurityEnv


def build_action_space(cfg: dict) -> list[dict]:
    moves = list(cfg["control"].get("allowed_moves", ["stay", "up", "down", "left", "right"]))
    p_s_levels = [float(x) for x in cfg["control"]["p_s_levels"]]
    p_j_levels = [float(x) for x in cfg["control"]["p_j_levels"]]
    bandwidth_levels = [0.0] + [float(x) for x in cfg["sync"].get("bandwidth_levels", [cfg["sync"].get("bandwidth_max", 1.0)])]
    actions = []
    for move1, move2, p_s, p_j, bandwidth in itertools.product(moves, moves, p_s_levels, p_j_levels, bandwidth_levels):
        actions.append(
            {
                "move_uav1": move1,
                "move_uav2": move2,
                "p_s": p_s,
                "p_j": p_j,
                "sync": bandwidth > 0.0,
                "sync_bandwidth": float(bandwidth),
                "sync_reason": "mdp_upper_bound" if bandwidth > 0.0 else "mdp_skip",
            }
        )
    return actions


def compact_snapshot(env: UAVSecurityEnv) -> dict:
    return {
        "slot": int(env.slot),
        "remaining_budget": float(env.remaining_budget),
        "total_sync_cost": float(env.total_sync_cost),
        "sync_count": int(env.sync_count),
        "uav1_pos": env.uav1.position.copy(),
        "uav2_pos": env.uav2.position.copy(),
        "eve_pos": env.eve.position.copy(),
        "eve_vel": env.eve.velocity.copy(),
        "twin": env.twin.copy(),
        "pending_syncs": [dict(item) for item in env.pending_syncs],
        "rng_state": copy.deepcopy(env.rng.bit_generator.state),
    }


def restore_compact(env: UAVSecurityEnv, state: dict) -> None:
    env.slot = int(state["slot"])
    env.remaining_budget = float(state["remaining_budget"])
    env.total_sync_cost = float(state["total_sync_cost"])
    env.sync_count = int(state["sync_count"])
    env.uav1.position = state["uav1_pos"].copy()
    env.uav2.position = state["uav2_pos"].copy()
    env.eve.position = state["eve_pos"].copy()
    env.eve.velocity = state["eve_vel"].copy()
    env.twin = state["twin"].copy()
    env.pending_syncs = [dict(item) for item in state["pending_syncs"]]
    env.uav1.history = [env.uav1.position.copy()]
    env.uav2.history = [env.uav2.position.copy()]
    env.true_eve_history = [env.eve.position.copy()]
    env.history = []
    env.rng.bit_generator.state = copy.deepcopy(state["rng_state"])


def serialize_state(env: UAVSecurityEnv) -> str:
    state = compact_snapshot(env)
    payload = {
        "slot": int(state["slot"]),
        "remaining_budget": round(float(state["remaining_budget"]), 2),
        "uav1_pos": [round(float(x), 1) for x in state["uav1_pos"]],
        "uav2_pos": [round(float(x), 1) for x in state["uav2_pos"]],
        "eve_pos": [round(float(x), 1) for x in state["eve_pos"]],
        "eve_vel": [round(float(x), 1) for x in state["eve_vel"]],
        "twin_state": [round(float(x), 2) for x in state["twin"].state],
        "twin_cov": [round(float(x), 2) for x in state["twin"].covariance.flatten()],
        "aoi": int(state["twin"].aoi),
        "pending_syncs": [
            {"steps_left": round(float(item["steps_left"]), 1), "bandwidth": round(float(item["bandwidth"]), 2)}
            for item in state["pending_syncs"]
        ],
    }
    return json.dumps(payload, sort_keys=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=str(ROOT / "configs" / "small_mdp_bound.yaml"))
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "small_mdp_bound"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cfg = load_config(args.config)
    cfg["seed"] = int(args.seed)
    env = UAVSecurityEnv(copy.deepcopy(cfg))
    env.reset(seed=int(args.seed))
    actions = build_action_space(cfg)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    decision_trace: list[dict] = []

    @lru_cache(maxsize=None)
    def solve(state_key: str) -> tuple[float, tuple | None]:
        restore_compact(env, current_states[state_key])
        if env.slot >= env.T:
            return 0.0, None

        best_value = None
        best_action = None
        for action in actions:
            if action["sync"] and action["sync_bandwidth"] > env.remaining_budget + 1e-12:
                continue
            snapshot = compact_snapshot(env)
            result = env.step(action)
            next_key = serialize_state(env)
            if next_key not in current_states:
                current_states[next_key] = compact_snapshot(env)
            future_value, _ = solve(next_key)
            total_value = float(result.info["true_r_sec"]) + future_value
            restore_compact(env, snapshot)
            if best_value is None or total_value > best_value:
                best_value = total_value
                best_action = action
        return float(best_value or 0.0), tuple(best_action.items()) if best_action is not None else None

    current_states = {serialize_state(env): compact_snapshot(env)}
    initial_key = serialize_state(env)
    optimal_cumulative, _ = solve(initial_key)

    restore_compact(env, current_states[initial_key])
    while env.slot < env.T:
        state_key = serialize_state(env)
        _, action_tuple = solve(state_key)
        if action_tuple is None:
            break
        action = dict(action_tuple)
        result = env.step(action)
        decision_trace.append(dict(result.info))

    trace_df = pd.DataFrame(decision_trace)
    trace_df.to_csv(outdir / "optimal_trace.csv", index=False)
    summary = pd.DataFrame(
        [
            {
                "config": str(args.config),
                "seed": int(args.seed),
                "episode_length": int(env.T),
                "optimal_cumulative_secrecy": float(optimal_cumulative),
                "optimal_avg_secrecy": float(optimal_cumulative / max(env.T, 1)),
                "num_states_evaluated": int(solve.cache_info().currsize),
                "num_actions": int(len(actions)),
                "state_abstraction": "rounded_state_dp(pos=0.1,twin=0.01,cov=0.01)",
            }
        ]
    )
    summary.to_csv(outdir / "summary.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
