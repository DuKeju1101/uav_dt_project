from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Tuple
import time
import yaml
import pandas as pd

from env.simulator import UAVSecurityEnv
from policies.greedy_joint import GreedyJointController
from policies.decoupled import DecoupledController
from policies.random_budgeted import RandomBudgetedController
from policies.rollout_joint import RolloutJointController
from policies.sca_baseline import SuccessiveApproximationController
from analysis.metrics import summarize_episode


ROOT = Path(__file__).resolve().parents[1]


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = ROOT / "configs" / "base.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg


def run_single_episode(cfg: Dict[str, Any], seed: int, method: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    cfg = copy.deepcopy(cfg)
    cfg["seed"] = seed
    if method == "no_twin":
        cfg.setdefault("twin", {})
        cfg["twin"]["prediction_enabled"] = False
    env = UAVSecurityEnv(cfg)
    obs = env.reset(seed=seed)

    if method == "decoupled":
        controller = DecoupledController(cfg, sync_rule="periodic")
    elif method == "random_budgeted":
        controller = RandomBudgetedController(cfg)
    elif method == "rollout_fixed_periodic":
        fixed_cfg = copy.deepcopy(cfg)
        fixed_cfg.setdefault("control", {})
        fixed_cfg["control"]["rollout_fixed_sync_rule"] = "periodic"
        fixed_cfg["control"]["rollout_fixed_sync_periodic_k"] = int(fixed_cfg["sync"].get("periodic_k", 1))
        controller = RolloutJointController(fixed_cfg, use_oracle_state=False)
    elif method == "rollout_no_sync":
        fixed_cfg = copy.deepcopy(cfg)
        fixed_cfg.setdefault("control", {})
        fixed_cfg["control"]["rollout_fixed_sync_rule"] = "never"
        controller = RolloutJointController(fixed_cfg, use_oracle_state=False)
    elif method == "rollout_joint":
        controller = RolloutJointController(cfg, use_oracle_state=False)
    elif method == "oracle_sync":
        controller = RolloutJointController(cfg, use_oracle_state=True)
    elif method == "no_twin":
        controller = RolloutJointController(cfg, use_oracle_state=False)
    elif method == "myopic_greedy_no_sync":
        controller = GreedyJointController(cfg)
    elif method == "sca_twin":
        controller = SuccessiveApproximationController(cfg, use_oracle_state=False)
    elif method == "sca_oracle":
        controller = SuccessiveApproximationController(cfg, use_oracle_state=True)
    else:
        controller = GreedyJointController(cfg)

    records: List[Dict[str, Any]] = []
    done = False
    t0 = time.perf_counter()
    while not done:
        if method == "decoupled":
            action = controller.act(env, obs)
        elif method in {
            "random_budgeted",
            "rollout_fixed_periodic",
            "rollout_no_sync",
            "rollout_joint",
            "oracle_sync",
            "no_twin",
            "sca_twin",
            "sca_oracle",
        }:
            action = controller.act(env, obs)
        elif method == "myopic_greedy_no_sync":
            action = controller.act(env, obs, sync_method="none")
        else:
            action = controller.act(env, obs, sync_method=method)
        result = env.step(action)
        records.append(result.info)
        obs = result.observation
        done = result.done

    df = pd.DataFrame(records)
    summary = summarize_episode(df)
    runtime_sec = time.perf_counter() - t0
    summary.update(
        {
            "method": method,
            "seed": seed,
            "runtime_sec": float(runtime_sec),
            "runtime_per_slot_ms": float(1000.0 * runtime_sec / max(len(df), 1)),
        }
    )
    return df, summary
