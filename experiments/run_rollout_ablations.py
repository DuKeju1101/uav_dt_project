from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd

from analysis.metrics import aggregate_runs_with_ci
from experiments.common import ROOT, load_config, run_single_episode


DEFAULT_CONFIGS = [
    str(ROOT / "configs" / "paper_base.yaml"),
    str(ROOT / "configs" / "paper_hard.yaml"),
    str(ROOT / "configs" / "scenario_stress.yaml"),
]


ABLATIONS = {
    "rollout_joint": {},
    "rollout_no_certificate": {"control.lambda_certificate": 0.0},
    "rollout_no_outage": {"control.lambda_outage": 0.0},
    "rollout_no_pending_sync": {"control.lambda_pending_sync": 0.0},
    "rollout_one_step": {
        "control.rollout_horizon": 1,
        "control.rollout_tail_branching": 1,
        "control.rollout_deep_branching": 1,
    },
}


def _set_nested(cfg: dict, dotted_key: str, value: float | int) -> None:
    keys = dotted_key.split(".")
    ref = cfg
    for key in keys[:-1]:
        ref = ref[key]
    ref[keys[-1]] = value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+", default=DEFAULT_CONFIGS)
    parser.add_argument("--num-seeds", type=int, default=1)
    parser.add_argument("--seed-start", type=int, default=62)
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "rollout_ablations"))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for config_path in args.configs:
        cfg = load_config(config_path)
        scenario = Path(config_path).stem
        for variant, overrides in ABLATIONS.items():
            for seed in range(int(args.seed_start), int(args.seed_start) + int(args.num_seeds)):
                local_cfg = copy.deepcopy(cfg)
                for dotted_key, value in overrides.items():
                    _set_nested(local_cfg, dotted_key, value)
                _, summary = run_single_episode(local_cfg, seed=seed, method="rollout_joint")
                summary["scenario"] = scenario
                summary["variant"] = variant
                rows.append(summary)
                print(f"[done] scenario={scenario} variant={variant} seed={seed}")

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "all_runs.csv", index=False)
    agg = aggregate_runs_with_ci(df, ["scenario", "variant"])
    agg.to_csv(outdir / "summary.csv", index=False)
    print(f"Saved rollout ablations to: {outdir}")


if __name__ == "__main__":
    main()
