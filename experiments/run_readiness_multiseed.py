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
DEFAULT_METHODS = ["periodic", "security_risk", "security_margin", "rollout_joint", "risk_adaptive_hybrid_rollout"]


def _save_markdown(df: pd.DataFrame, path: Path) -> None:
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(str(row[c]) for c in cols) + " |" for _, row in df.iterrows()]
    path.write_text("\n".join([header, sep] + rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+", default=DEFAULT_CONFIGS)
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    parser.add_argument("--num-seeds", type=int, default=5)
    parser.add_argument("--seed-start", type=int, default=62)
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "readiness_multiseed"))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for config_path in args.configs:
        cfg = load_config(config_path)
        scenario = Path(config_path).stem
        for seed in range(int(args.seed_start), int(args.seed_start) + int(args.num_seeds)):
            for method in args.methods:
                _, summary = run_single_episode(copy.deepcopy(cfg), seed=seed, method=method)
                summary["scenario"] = scenario
                summary["config_path"] = str(config_path)
                rows.append(summary)
                print(f"[done] scenario={scenario} method={method} seed={seed}")

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "all_runs.csv", index=False)

    agg = aggregate_runs_with_ci(df, ["scenario", "method"])
    agg.to_csv(outdir / "summary.csv", index=False)

    base = agg[agg["method"] == "periodic"][["scenario", "avg_secrecy_rate_mean", "outage_prob_mean"]].rename(
        columns={
            "avg_secrecy_rate_mean": "periodic_avg_secrecy_rate_mean",
            "outage_prob_mean": "periodic_outage_prob_mean",
        }
    )
    gains = agg.merge(base, on="scenario", how="left")
    gains["secrecy_gain_vs_periodic"] = gains["avg_secrecy_rate_mean"] - gains["periodic_avg_secrecy_rate_mean"]
    gains["outage_gain_vs_periodic"] = gains["periodic_outage_prob_mean"] - gains["outage_prob_mean"]
    gains.to_csv(outdir / "summary_with_gains.csv", index=False)

    main_table = gains[
        [
            "scenario",
            "method",
            "num_runs",
            "avg_secrecy_rate_mean",
            "avg_secrecy_rate_ci95",
            "outage_prob_mean",
            "outage_prob_ci95",
            "avg_sync_cost_mean",
            "certificate_cover_rate_mean",
            "runtime_per_slot_ms_mean",
            "runtime_per_slot_ms_ci95",
            "secrecy_gain_vs_periodic",
            "outage_gain_vs_periodic",
        ]
    ].sort_values(["scenario", "avg_secrecy_rate_mean"], ascending=[True, False])
    main_table.to_csv(outdir / "main_table.csv", index=False)
    _save_markdown(main_table, outdir / "main_table.md")

    print(f"Saved readiness multiseed results to: {outdir}")


if __name__ == "__main__":
    main()
