from __future__ import annotations

import argparse
from pathlib import Path
import copy
import pandas as pd

from analysis.metrics import aggregate_runs_with_ci
from experiments.common import ROOT, load_config, run_single_episode


METHODS = [
    "full",
    "periodic",
    "aoi_only",
    "decoupled",
    "security_margin",
    "security_risk",
    "random_budgeted",
    "rollout_joint",
    "oracle_sync",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=str(ROOT / "configs" / "base.yaml"))
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "baselines"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    summaries = []
    for method in METHODS:
        for seed_offset in range(int(cfg.get("num_seeds", 5))):
            seed = int(cfg["seed"]) + seed_offset
            df_slot, summary = run_single_episode(copy.deepcopy(cfg), seed=seed, method=method)
            df_slot.to_csv(outdir / f"slot_{method}_seed{seed}.csv", index=False)
            summary.update(
                {
                    "budget": int(cfg["sync"]["budget"]),
                    "periodic_k": int(cfg["sync"]["periodic_k"]),
                    "aoi_threshold": int(cfg["sync"]["aoi_threshold"]),
                    "eve_speed": float((cfg["eve"]["velocity"][0] ** 2 + cfg["eve"]["velocity"][1] ** 2) ** 0.5),
                }
            )
            summaries.append(summary)
            print(f"[done] method={method} seed={seed} avg_Rs={summary['avg_secrecy_rate']:.4f}")

    df_summary = pd.DataFrame(summaries)
    df_summary.to_csv(outdir / "summary_all_methods.csv", index=False)
    agg = aggregate_runs_with_ci(df_summary, ["method"])
    agg.to_csv(outdir / "summary_agg_methods.csv", index=False)
    print(f"Saved to: {outdir}")


if __name__ == "__main__":
    main()
