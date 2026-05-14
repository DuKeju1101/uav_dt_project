from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd

from analysis.metrics import aggregate_runs_with_ci, paired_comparisons
from experiments.common import ROOT, load_config, run_single_episode


DEFAULT_CONFIGS = [
    str(ROOT / "configs" / "paper_base.yaml"),
    str(ROOT / "configs" / "paper_hard.yaml"),
    str(ROOT / "configs" / "scenario_stress.yaml"),
]

DEFAULT_METHODS = [
    "full",
    "periodic",
    "aoi_only",
    "security_risk",
    "security_margin",
    "decoupled",
    "random_budgeted",
    "myopic_greedy_no_sync",
    "no_twin",
    "sca_twin",
    "sca_oracle",
    "rollout_fixed_periodic",
    "rollout_no_sync",
    "rollout_joint",
    "oracle_sync",
]

METHOD_NOTES = {
    "full": "Synchronize whenever budget is available, with greedy joint motion/power control.",
    "periodic": "Fixed-period synchronization with greedy joint motion/power control.",
    "aoi_only": "Age-of-information threshold synchronization baseline.",
    "security_risk": "Risk-triggered synchronization baseline.",
    "security_margin": "Certificate-triggered synchronization baseline.",
    "decoupled": "Decoupled periodic synchronization followed by greedy motion/power control.",
    "random_budgeted": "Stochastic budget-aware synchronization baseline.",
    "myopic_greedy_no_sync": "Myopic greedy motion/power controller with synchronization disabled.",
    "no_twin": "Rollout controller with digital-twin prediction disabled; it acts on the last synced Eve estimate.",
    "sca_twin": "Successive-approximation optimizer that scores candidates with the deployable twin estimate.",
    "sca_oracle": "Oracle successive-approximation upper reference that scores candidates with true Eve state.",
    "rollout_fixed_periodic": "Same rollout motion/power search as rollout_joint, but synchronization is fixed periodic.",
    "rollout_no_sync": "Same rollout motion/power search as rollout_joint, but synchronization is disabled.",
    "rollout_joint": "Proposed adaptive synchronization, motion, and power rollout controller.",
    "oracle_sync": "Upper-reference rollout that evaluates candidates with true Eve state.",
}


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
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "strengthening_suite"))
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
                print(f"[done] scenario={scenario} method={method} seed={seed}", flush=True)

    all_runs = pd.DataFrame(rows)
    all_runs.to_csv(outdir / "all_runs.csv", index=False)

    summary = aggregate_runs_with_ci(all_runs, ["scenario", "method"])
    summary.to_csv(outdir / "summary.csv", index=False)

    base_periodic = summary[summary["method"] == "periodic"][
        ["scenario", "avg_secrecy_rate_mean", "outage_prob_mean"]
    ].rename(
        columns={
            "avg_secrecy_rate_mean": "periodic_avg_secrecy_rate_mean",
            "outage_prob_mean": "periodic_outage_prob_mean",
        }
    )
    base_fixed = summary[summary["method"] == "rollout_fixed_periodic"][
        ["scenario", "avg_secrecy_rate_mean", "outage_prob_mean"]
    ].rename(
        columns={
            "avg_secrecy_rate_mean": "fixed_rollout_avg_secrecy_rate_mean",
            "outage_prob_mean": "fixed_rollout_outage_prob_mean",
        }
    )
    oracle = summary[summary["method"] == "oracle_sync"][["scenario", "avg_secrecy_rate_mean"]].rename(
        columns={"avg_secrecy_rate_mean": "oracle_avg_secrecy_rate_mean"}
    )

    gains = summary.merge(base_periodic, on="scenario", how="left")
    gains = gains.merge(base_fixed, on="scenario", how="left")
    gains = gains.merge(oracle, on="scenario", how="left")
    gains["secrecy_gain_vs_periodic"] = gains["avg_secrecy_rate_mean"] - gains["periodic_avg_secrecy_rate_mean"]
    gains["outage_gain_vs_periodic"] = gains["periodic_outage_prob_mean"] - gains["outage_prob_mean"]
    gains["secrecy_gain_vs_fixed_rollout"] = (
        gains["avg_secrecy_rate_mean"] - gains["fixed_rollout_avg_secrecy_rate_mean"]
    )
    gains["outage_gain_vs_fixed_rollout"] = gains["fixed_rollout_outage_prob_mean"] - gains["outage_prob_mean"]
    gains["oracle_secrecy_gap"] = gains["oracle_avg_secrecy_rate_mean"] - gains["avg_secrecy_rate_mean"]
    gains.to_csv(outdir / "summary_with_gains.csv", index=False)

    main_cols = [
        "scenario",
        "method",
        "num_runs",
        "episode_length_mean",
        "avg_secrecy_rate_mean",
        "avg_secrecy_rate_ci95",
        "avg_secrecy_rate_ci95_low",
        "avg_secrecy_rate_ci95_high",
        "outage_prob_mean",
        "outage_prob_ci95",
        "avg_sync_cost_mean",
        "certificate_in_policy_cover_rate_mean",
        "certificate_empirical_cover_rate_mean",
        "certificate_margin_cover_rate_mean",
        "runtime_per_slot_ms_mean",
        "secrecy_gain_vs_periodic",
        "secrecy_gain_vs_fixed_rollout",
        "oracle_secrecy_gap",
    ]
    main_table = gains[main_cols].sort_values(["scenario", "avg_secrecy_rate_mean"], ascending=[True, False])
    main_table.to_csv(outdir / "main_table.csv", index=False)
    _save_markdown(main_table, outdir / "main_table.md")

    paired_baselines = [method for method in args.methods if method != "rollout_joint"]
    paired = paired_comparisons(all_runs, target="rollout_joint", baselines=paired_baselines)
    paired.to_csv(outdir / "paired_rollout_joint_gains.csv", index=False)
    paired.to_csv(outdir / "paired_comparisons_rollout_joint.csv", index=False)
    if not paired.empty:
        _save_markdown(paired, outdir / "paired_rollout_joint_gains.md")
        _save_markdown(paired, outdir / "paired_comparisons_rollout_joint.md")

    notes = pd.DataFrame(
        [{"method": method, "note": METHOD_NOTES.get(method, "")} for method in args.methods]
    )
    notes.to_csv(outdir / "method_notes.csv", index=False)
    _save_markdown(notes, outdir / "method_notes.md")

    print(f"Saved strengthening suite to: {outdir}")


if __name__ == "__main__":
    main()
