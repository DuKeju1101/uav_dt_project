from __future__ import annotations

import argparse
import copy
from pathlib import Path
import time
from typing import Any, Dict

import numpy as np
import pandas as pd

from analysis.metrics import aggregate_runs_with_ci, paired_comparisons, summarize_episode
from env.simulator import UAVSecurityEnv
from experiments.common import ROOT, load_config, run_single_episode
from policies.ppo_baseline import PPOPolicy, discounted_returns, reward_from_info


DEFAULT_CONFIGS = [
    str(ROOT / "configs" / "paper_base.yaml"),
    str(ROOT / "configs" / "paper_hard.yaml"),
    str(ROOT / "configs" / "scenario_stress.yaml"),
]


def _save_markdown(df: pd.DataFrame, path: Path) -> None:
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(str(row[c]) for c in cols) + " |" for _, row in df.iterrows()]
    path.write_text("\n".join([header, sep] + rows) + "\n", encoding="utf-8")


def _collect_episode(
    cfg: Dict[str, Any],
    policy: PPOPolicy,
    seed: int,
    rng: np.random.Generator,
    gamma: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = copy.deepcopy(cfg)
    cfg["seed"] = seed
    env = UAVSecurityEnv(cfg)
    obs = env.reset(seed=seed)
    done = False
    samples: list[dict[str, Any]] = []
    rewards: list[float] = []
    records: list[dict[str, Any]] = []
    while not done:
        action, indices, logprob, value, features = policy.sample(obs, rng)
        result = env.step(action)
        reward = reward_from_info(result.info, cfg)
        samples.append(
            {
                "features": features,
                "indices": indices,
                "logprob": logprob,
                "value": value,
                "reward": reward,
            }
        )
        rewards.append(reward)
        records.append(result.info)
        obs = result.observation
        done = result.done

    returns = discounted_returns(rewards, gamma)
    for sample, ret in zip(samples, returns):
        sample["return"] = float(ret)
        sample["advantage"] = float(ret - sample["value"])

    summary = summarize_episode(pd.DataFrame(records))
    return samples, summary


def _evaluate_policy(cfg: Dict[str, Any], policy: PPOPolicy, seed: int) -> dict[str, Any]:
    cfg = copy.deepcopy(cfg)
    cfg["seed"] = seed
    env = UAVSecurityEnv(cfg)
    obs = env.reset(seed=seed)
    records: list[dict[str, Any]] = []
    done = False
    t0 = time.perf_counter()
    while not done:
        result = env.step(policy.act(obs))
        records.append(result.info)
        obs = result.observation
        done = result.done
    summary = summarize_episode(pd.DataFrame(records))
    runtime_sec = time.perf_counter() - t0
    summary["method"] = "ppo_baseline"
    summary["seed"] = seed
    summary["runtime_sec"] = float(runtime_sec)
    summary["runtime_per_slot_ms"] = float(1000.0 * runtime_sec / max(len(records), 1))
    return summary


def _train_for_config(
    cfg: Dict[str, Any],
    scenario: str,
    args: argparse.Namespace,
    outdir: Path,
) -> tuple[PPOPolicy, pd.DataFrame]:
    rng = np.random.default_rng(int(args.train_seed))
    policy = PPOPolicy.initialize(cfg, rng)
    log_rows: list[dict[str, Any]] = []
    for episode_idx in range(int(args.train_episodes)):
        seed = int(args.train_seed_start) + episode_idx
        samples, summary = _collect_episode(cfg, policy, seed, rng, float(args.gamma))
        policy.update(
            samples,
            learning_rate=float(args.learning_rate),
            value_learning_rate=float(args.value_learning_rate),
            clip_eps=float(args.clip_eps),
            entropy_coef=float(args.entropy_coef),
            epochs=int(args.ppo_epochs),
            rng=rng,
        )
        summary["scenario"] = scenario
        summary["train_episode"] = episode_idx
        summary["seed"] = seed
        log_rows.append(summary)
        print(
            f"[train] scenario={scenario} episode={episode_idx + 1}/{args.train_episodes} "
            f"avg_r_sec={summary['avg_secrecy_rate']:.4f}",
            flush=True,
        )
    policy_path = outdir / f"ppo_policy_{scenario}.npz"
    policy.save(policy_path)
    return policy, pd.DataFrame(log_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+", default=DEFAULT_CONFIGS)
    parser.add_argument("--train-episodes", type=int, default=12)
    parser.add_argument("--eval-seeds", type=int, default=3)
    parser.add_argument("--eval-seed-start", type=int, default=62)
    parser.add_argument("--train-seed-start", type=int, default=200)
    parser.add_argument("--train-seed", type=int, default=7)
    parser.add_argument("--gamma", type=float, default=0.97)
    parser.add_argument("--learning-rate", type=float, default=0.002)
    parser.add_argument("--value-learning-rate", type=float, default=0.01)
    parser.add_argument("--clip-eps", type=float, default=0.2)
    parser.add_argument("--entropy-coef", type=float, default=0.001)
    parser.add_argument("--ppo-epochs", type=int, default=2)
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "drl_ppo_baseline"))
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    training_logs: list[pd.DataFrame] = []
    eval_rows: list[dict[str, Any]] = []
    for config_path in args.configs:
        cfg = load_config(config_path)
        scenario = Path(config_path).stem
        policy, train_log = _train_for_config(cfg, scenario, args, outdir)
        training_logs.append(train_log)

        for seed in range(int(args.eval_seed_start), int(args.eval_seed_start) + int(args.eval_seeds)):
            summary = _evaluate_policy(cfg, policy, seed)
            summary["scenario"] = scenario
            summary["config_path"] = str(config_path)
            eval_rows.append(summary)
            print(f"[eval] scenario={scenario} method=ppo_baseline seed={seed}", flush=True)

        for method in ["periodic", "rollout_joint"]:
            for seed in range(int(args.eval_seed_start), int(args.eval_seed_start) + int(args.eval_seeds)):
                _, summary = run_single_episode(copy.deepcopy(cfg), seed=seed, method=method)
                summary["scenario"] = scenario
                summary["config_path"] = str(config_path)
                eval_rows.append(summary)
                print(f"[eval] scenario={scenario} method={method} seed={seed}", flush=True)

    train_df = pd.concat(training_logs, ignore_index=True) if training_logs else pd.DataFrame()
    train_df.to_csv(outdir / "training_log.csv", index=False)

    all_runs = pd.DataFrame(eval_rows)
    all_runs.to_csv(outdir / "all_runs.csv", index=False)

    summary = aggregate_runs_with_ci(all_runs, ["scenario", "method"])
    summary.to_csv(outdir / "summary.csv", index=False)

    periodic = summary[summary["method"] == "periodic"][["scenario", "avg_secrecy_rate_mean"]].rename(
        columns={"avg_secrecy_rate_mean": "periodic_avg_secrecy_rate_mean"}
    )
    rollout = summary[summary["method"] == "rollout_joint"][["scenario", "avg_secrecy_rate_mean"]].rename(
        columns={"avg_secrecy_rate_mean": "rollout_avg_secrecy_rate_mean"}
    )
    gains = summary.merge(periodic, on="scenario", how="left").merge(rollout, on="scenario", how="left")
    gains["secrecy_gain_vs_periodic"] = gains["avg_secrecy_rate_mean"] - gains["periodic_avg_secrecy_rate_mean"]
    gains["secrecy_gap_vs_rollout"] = gains["rollout_avg_secrecy_rate_mean"] - gains["avg_secrecy_rate_mean"]
    gains.to_csv(outdir / "summary_with_gains.csv", index=False)

    paired = paired_comparisons(
        all_runs,
        target="rollout_joint",
        baselines=[method for method in sorted(all_runs["method"].unique()) if method != "rollout_joint"],
    )
    paired.to_csv(outdir / "paired_comparisons_rollout_joint.csv", index=False)
    if not paired.empty:
        _save_markdown(paired, outdir / "paired_comparisons_rollout_joint.md")

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
        "avg_sync_cost_mean",
        "certificate_in_policy_cover_rate_mean",
        "certificate_empirical_cover_rate_mean",
        "certificate_margin_cover_rate_mean",
        "runtime_per_slot_ms_mean",
        "secrecy_gain_vs_periodic",
        "secrecy_gap_vs_rollout",
    ]
    main_table = gains[main_cols].sort_values(["scenario", "avg_secrecy_rate_mean"], ascending=[True, False])
    main_table.to_csv(outdir / "main_table.csv", index=False)
    _save_markdown(main_table, outdir / "main_table.md")

    print(f"Saved PPO baseline results to: {outdir}")


if __name__ == "__main__":
    main()
