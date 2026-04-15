from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd

from experiments.common import ROOT, load_config, run_single_episode


DEFAULT_CONFIGS = [
    str(ROOT / "configs" / "paper_base.yaml"),
    str(ROOT / "configs" / "paper_hard.yaml"),
]

ROLLOUT_SETTINGS = [
    ("rollout_h1_b4", {"control.rollout_horizon": 1, "control.rollout_branching": 4, "control.rollout_deep_branching": 1, "control.rollout_tail_branching": 1}),
    ("rollout_h1_b8", {"control.rollout_horizon": 1, "control.rollout_branching": 8, "control.rollout_deep_branching": 1, "control.rollout_tail_branching": 1}),
    ("rollout_h2_b8", {"control.rollout_horizon": 2, "control.rollout_branching": 8, "control.rollout_deep_branching": 3, "control.rollout_tail_branching": 2}),
    ("rollout_h2_b12", {"control.rollout_horizon": 2, "control.rollout_branching": 12, "control.rollout_deep_branching": 4, "control.rollout_tail_branching": 2}),
]


def _set_nested(cfg: dict, dotted_key: str, value: float | int) -> None:
    keys = dotted_key.split(".")
    ref = cfg
    for key in keys[:-1]:
        ref = ref[key]
    ref[keys[-1]] = value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+", default=DEFAULT_CONFIGS)
    parser.add_argument("--seed", type=int, default=62)
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "runtime_tradeoff"))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for config_path in args.configs:
        cfg = load_config(config_path)
        scenario = Path(config_path).stem

        for method in ["periodic", "security_margin"]:
            _, summary = run_single_episode(copy.deepcopy(cfg), seed=int(args.seed), method=method)
            summary["scenario"] = scenario
            summary["variant"] = method
            rows.append(summary)
            print(f"[done] scenario={scenario} variant={method} seed={args.seed}")

        for variant, overrides in ROLLOUT_SETTINGS:
            local_cfg = copy.deepcopy(cfg)
            for dotted_key, value in overrides.items():
                _set_nested(local_cfg, dotted_key, value)
            _, summary = run_single_episode(local_cfg, seed=int(args.seed), method="rollout_joint")
            summary["scenario"] = scenario
            summary["variant"] = variant
            rows.append(summary)
            print(f"[done] scenario={scenario} variant={variant} seed={args.seed}")

    pd.DataFrame(rows).to_csv(outdir / "runtime_tradeoff.csv", index=False)
    print(f"Saved runtime tradeoff results to: {outdir}")


if __name__ == "__main__":
    main()
