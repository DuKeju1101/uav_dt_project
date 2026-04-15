from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.metrics import aggregate_runs_with_ci
from experiments.common import ROOT, load_config, run_single_episode


DEFAULT_CONFIGS = [
    str(ROOT / "configs" / "paper_base.yaml"),
    str(ROOT / "configs" / "paper_hard.yaml"),
    str(ROOT / "configs" / "scenario_stress.yaml"),
]
DEFAULT_METHODS = ["periodic", "security_margin", "rollout_joint"]


def _perturb_config(cfg: dict, rng: np.random.Generator) -> dict:
    local = copy.deepcopy(cfg)
    local["eve"]["velocity"][0] = float(local["eve"]["velocity"][0] * rng.uniform(0.85, 1.15))
    local["eve"]["velocity"][1] = float(local["eve"]["velocity"][1] * rng.uniform(0.85, 1.15))
    local["eve"]["speed_noise_std"] = float(local["eve"]["speed_noise_std"] * rng.uniform(0.8, 1.2))
    local["sync"]["budget"] = int(max(12, round(local["sync"]["budget"] * rng.uniform(0.85, 1.15))))
    local["sync"]["failure_prob"] = float(np.clip(local["sync"]["failure_prob"] * rng.uniform(0.8, 1.25), 0.01, 0.2))
    local["channel"]["r_min"] = float(local["channel"]["r_min"] * rng.uniform(0.97, 1.03))
    jitter_scale = 12.0
    for pos in local["users"]["positions"]:
        pos[0] = float(np.clip(pos[0] + rng.uniform(-jitter_scale, jitter_scale), 0.0, local["area"]["width"]))
        pos[1] = float(np.clip(pos[1] + rng.uniform(-jitter_scale, jitter_scale), 0.0, local["area"]["height"]))
    return local


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+", default=DEFAULT_CONFIGS)
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    parser.add_argument("--num-perturbations", type=int, default=2)
    parser.add_argument("--num-seeds", type=int, default=1)
    parser.add_argument("--seed-start", type=int, default=90)
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "randomized_generalization"))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for config_path in args.configs:
        base_cfg = load_config(config_path)
        scenario = Path(config_path).stem
        for perturb_id in range(int(args.num_perturbations)):
            rng = np.random.default_rng(1000 + perturb_id)
            perturbed_cfg = _perturb_config(base_cfg, rng)
            for seed in range(int(args.seed_start), int(args.seed_start) + int(args.num_seeds)):
                for method in args.methods:
                    _, summary = run_single_episode(copy.deepcopy(perturbed_cfg), seed=seed, method=method)
                    summary["scenario"] = scenario
                    summary["perturb_id"] = perturb_id
                    rows.append(summary)
                    print(f"[done] scenario={scenario} perturb={perturb_id} method={method} seed={seed}")

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "all_runs.csv", index=False)
    agg = aggregate_runs_with_ci(df, ["scenario", "method"])
    agg.to_csv(outdir / "summary.csv", index=False)
    overall = aggregate_runs_with_ci(df, ["method"])
    overall.to_csv(outdir / "overall_summary.csv", index=False)
    print(f"Saved randomized generalization results to: {outdir}")


if __name__ == "__main__":
    main()
