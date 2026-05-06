from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd

from analysis.metrics import aggregate_runs_with_ci, paired_comparisons
from experiments.common import ROOT, load_config, run_single_episode
from experiments.run_readiness_multiseed import DEFAULT_CONFIGS, DEFAULT_METHODS


METHODS = DEFAULT_METHODS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--configs",
        nargs="+",
        default=DEFAULT_CONFIGS,
    )
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "publication_suite"))
    parser.add_argument("--num-seeds", type=int, default=5)
    parser.add_argument("--methods", nargs="+", default=METHODS)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    for config_path in args.configs:
        cfg = load_config(config_path)
        scenario_name = Path(config_path).stem
        for seed_offset in range(args.num_seeds):
            seed = int(cfg["seed"]) + seed_offset
            for method in args.methods:
                _, summary = run_single_episode(copy.deepcopy(cfg), seed=seed, method=method)
                summary["scenario"] = scenario_name
                summary["config_path"] = str(config_path)
                rows.append(summary)
                print(f"[done] scenario={scenario_name} method={method} seed={seed}")

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "publication_suite_all.csv", index=False)
    agg = aggregate_runs_with_ci(df, ["scenario", "method"])
    agg.to_csv(outdir / "publication_suite_summary.csv", index=False)
    paired = paired_comparisons(
        df,
        target="rollout_joint",
        baselines=[method for method in args.methods if method != "rollout_joint"],
    )
    paired.to_csv(outdir / "publication_suite_paired_comparisons.csv", index=False)

    pivot = agg.pivot(index="method", columns="scenario", values="avg_secrecy_rate_mean").reset_index()
    pivot.to_csv(outdir / "publication_suite_secrecy_pivot.csv", index=False)
    print(f"Saved publication suite results to: {outdir}")


if __name__ == "__main__":
    main()
