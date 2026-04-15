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
    env = UAVSecurityEnv(cfg)
    obs = env.reset(seed=seed)

    if method == "decoupled":
        controller = DecoupledController(cfg, sync_rule="periodic")
    elif method == "random_budgeted":
        controller = RandomBudgetedController(cfg)
    elif method == "risk_adaptive_hybrid_rollout":
        hybrid_cfg = copy.deepcopy(cfg)
        hybrid_cfg.setdefault("control", {})
        hybrid_cfg["control"]["rollout_hybrid_enable"] = True
        hybrid_cfg["control"]["rollout_force_sync_if_unsafe"] = False
        hybrid_cfg["control"]["rollout_force_sync_badness_threshold"] = None
        hybrid_cfg["control"]["rollout_force_sync_margin_threshold"] = None
        controller = RolloutJointController(hybrid_cfg, use_oracle_state=False)
    elif method == "rollout_joint":
        controller = RolloutJointController(cfg, use_oracle_state=False)
    elif method == "oracle_sync":
        controller = RolloutJointController(cfg, use_oracle_state=True)
    else:
        controller = GreedyJointController(cfg)

    records: List[Dict[str, Any]] = []
    done = False
    t0 = time.perf_counter()
    while not done:
        if method == "decoupled":
            action = controller.act(env, obs)
        elif method in {"random_budgeted", "rollout_joint", "risk_adaptive_hybrid_rollout", "oracle_sync"}:
            action = controller.act(env, obs)
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
