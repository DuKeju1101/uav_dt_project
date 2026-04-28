from __future__ import annotations

import argparse
import math
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    print(f"[run] {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def _markdown_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(str(row[c]) for c in cols) + " |" for _, row in df.iterrows()]
    return "\n".join([header, sep] + rows)


def _format_main_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["avg_secrecy_rate_mean", "avg_secrecy_rate_ci95", "outage_prob_mean", "outage_prob_ci95", "avg_sync_cost_mean", "certificate_cover_rate_mean", "runtime_per_slot_ms_mean"]:
        if col in out.columns:
            out[col] = out[col].map(lambda x: f"{float(x):.4f}" if col != "runtime_per_slot_ms_mean" else f"{float(x):.2f}")
    keep = [
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
    ]
    return out[keep]


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _paired_stats(all_runs: pd.DataFrame, scenario: str, baseline: str, target: str) -> dict[str, float | int | str]:
    cols = ["seed", "avg_secrecy_rate", "outage_prob", "runtime_per_slot_ms"]
    base = all_runs[(all_runs["scenario"] == scenario) & (all_runs["method"] == baseline)][cols].rename(
        columns={
            "avg_secrecy_rate": "base_secrecy",
            "outage_prob": "base_outage",
            "runtime_per_slot_ms": "base_runtime",
        }
    )
    targ = all_runs[(all_runs["scenario"] == scenario) & (all_runs["method"] == target)][cols].rename(
        columns={
            "avg_secrecy_rate": "target_secrecy",
            "outage_prob": "target_outage",
            "runtime_per_slot_ms": "target_runtime",
        }
    )
    merged = base.merge(targ, on="seed", how="inner").sort_values("seed")
    if merged.empty:
        return {"scenario": scenario, "baseline": baseline, "target": target, "n": 0}

    secrecy_diff = merged["target_secrecy"] - merged["base_secrecy"]
    outage_diff = merged["base_outage"] - merged["target_outage"]
    n = int(len(merged))
    secrecy_mean = float(secrecy_diff.mean())
    secrecy_std = float(secrecy_diff.std(ddof=1)) if n > 1 else 0.0
    secrecy_t = secrecy_mean / max(secrecy_std / math.sqrt(max(n, 1)), 1e-12) if n > 1 else 0.0
    secrecy_p = float(2.0 * (1.0 - _normal_cdf(abs(secrecy_t))))
    wins = int((secrecy_diff > 0).sum())
    return {
        "scenario": scenario,
        "baseline": baseline,
        "target": target,
        "n": n,
        "mean_secrecy_gain": secrecy_mean,
        "mean_outage_gain": float(outage_diff.mean()),
        "mean_runtime_delta_ms": float((merged["target_runtime"] - merged["base_runtime"]).mean()),
        "paired_t_stat": secrecy_t,
        "paired_t_pvalue_approx": secrecy_p,
        "secrecy_win_seeds": wins,
    }


def _generate_doc(
    readiness_outdir: Path,
    holdout_outdir: Path,
    small_mdp_outdir: Path,
    doc_path: Path,
) -> None:
    summary = pd.read_csv(readiness_outdir / "summary.csv")
    main_table = pd.read_csv(readiness_outdir / "main_table.csv")
    all_runs = pd.read_csv(readiness_outdir / "all_runs.csv")
    holdout_summary = pd.read_csv(holdout_outdir / "holdout_summary.csv")
    small_summary = pd.read_csv(small_mdp_outdir / "summary.csv") if (small_mdp_outdir / "summary.csv").exists() else pd.DataFrame()

    paired_rows = []
    for scenario in sorted(all_runs["scenario"].unique()):
        for baseline in ["periodic", "security_risk", "security_margin"]:
            paired_rows.append(_paired_stats(all_runs, scenario, baseline, "rollout_joint"))
    paired_df = pd.DataFrame(paired_rows)
    paired_csv = readiness_outdir / "paired_comparisons_rollout_joint.csv"
    paired_df.to_csv(paired_csv, index=False)

    lines: list[str] = []
    today = date.today().isoformat()
    lines.append(f"# 方案 C 重跑结果（{today}）")
    lines.append("")
    lines.append("## 1. 运行设置")
    lines.append("")
    lines.append("1. 改动口径：全部 P0 + 全部 P1。")
    lines.append("2. 关键机制：Kalman twin、conformal certificate、adaptive Eve、概率 LoS/NLoS 信道、连续带宽同步、扩展动作空间。")
    lines.append("3. 主表场景：`paper_base`、`paper_hard`、`scenario_stress`。")
    lines.append("4. 主表方法：`periodic`、`security_risk`、`security_margin`、`rollout_joint`。")
    lines.append("5. 验证 seed：`62-81`。")
    lines.append("")
    lines.append("结果文件：")
    lines.append(f"1. [summary.csv](../{readiness_outdir.relative_to(ROOT)}/summary.csv)")
    lines.append(f"2. [main_table.csv](../{readiness_outdir.relative_to(ROOT)}/main_table.csv)")
    lines.append(f"3. [all_runs.csv](../{readiness_outdir.relative_to(ROOT)}/all_runs.csv)")
    lines.append(f"4. [paired_comparisons_rollout_joint.csv](../{paired_csv.relative_to(ROOT)})")
    lines.append(f"5. [holdout_summary.csv](../{holdout_outdir.relative_to(ROOT)}/holdout_summary.csv)")
    if not small_summary.empty:
        lines.append(f"6. [small_mdp summary.csv](../{small_mdp_outdir.relative_to(ROOT)}/summary.csv)")
    lines.append("")
    lines.append("## 2. 主表")
    lines.append("")
    lines.append(_markdown_table(_format_main_table(main_table)))
    lines.append("")
    lines.append("## 3. Holdout 证书覆盖")
    lines.append("")
    holdout_display = holdout_summary.copy()
    for col in ["cover_rate", "mean_upper_minus_loss", "p90_upper_minus_loss", "avg_realized_loss"]:
        holdout_display[col] = holdout_display[col].map(lambda x: f"{float(x):.4f}")
    lines.append(_markdown_table(holdout_display))
    lines.append("")
    lines.append("## 4. 配对比较")
    lines.append("")
    paired_display = paired_df.copy()
    for col in ["mean_secrecy_gain", "mean_outage_gain", "mean_runtime_delta_ms", "paired_t_stat", "paired_t_pvalue_approx"]:
        if col in paired_display.columns:
            paired_display[col] = paired_display[col].map(lambda x: f"{float(x):.4f}")
    lines.append(_markdown_table(paired_display))
    lines.append("")
    if not small_summary.empty:
        lines.append("## 5. 小场景理论上界")
        lines.append("")
        small_display = small_summary.copy()
        for col in ["optimal_cumulative_secrecy", "optimal_avg_secrecy"]:
            small_display[col] = small_display[col].map(lambda x: f"{float(x):.4f}")
        lines.append(_markdown_table(small_display))
        lines.append("")

    scenario_rows = []
    for scenario in sorted(summary["scenario"].unique()):
        sub = summary[summary["scenario"] == scenario].copy()
        best_secrecy = sub.sort_values("avg_secrecy_rate_mean", ascending=False).iloc[0]
        best_outage = sub.sort_values("outage_prob_mean", ascending=True).iloc[0]
        fastest = sub.sort_values("runtime_per_slot_ms_mean", ascending=True).iloc[0]
        scenario_rows.append(
            f"1. `{scenario}`: 最高 secrecy 是 `{best_secrecy['method']}` ({best_secrecy['avg_secrecy_rate_mean']:.4f})，最低 outage 是 `{best_outage['method']}` ({best_outage['outage_prob_mean']:.4f})，最快方法是 `{fastest['method']}` ({fastest['runtime_per_slot_ms_mean']:.2f} ms/slot)。"
        )
    lines.append("## 6. 结论摘要")
    lines.append("")
    lines.extend(scenario_rows)
    lines.append("2. 如果 `rollout_joint` 在某些场景 secrecy 最优但 outage 不是最优，这说明方案 C 更适合写成性能-成本-鲁棒性 tradeoff 叙事。")
    lines.append("3. 如果 holdout `cover_rate` 接近设定覆盖率以上，conformal certificate 的统计保证叙事可以保留到论文正文。")
    lines.append("")

    doc_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--holdout-outdir", type=str, default=str(ROOT / "results" / "scheme_c_holdout"))
    parser.add_argument("--readiness-outdir", type=str, default=str(ROOT / "results" / "scheme_c_readiness_20seed"))
    parser.add_argument("--small-mdp-outdir", type=str, default=str(ROOT / "results" / "scheme_c_small_mdp"))
    parser.add_argument("--doc-path", type=str, default=str(ROOT / "docs" / f"scheme_c_results_{date.today().isoformat()}.md"))
    args = parser.parse_args()

    holdout_outdir = Path(args.holdout_outdir)
    readiness_outdir = Path(args.readiness_outdir)
    small_mdp_outdir = Path(args.small_mdp_outdir)
    doc_path = Path(args.doc_path)

    _run(
        [
            sys.executable,
            "-u",
            "-m",
            "experiments.fit_certificate_holdout",
            "--train-configs",
            "configs/base.yaml",
            "configs/scenario_hard.yaml",
            "configs/scenario_stress.yaml",
            "--eval-configs",
            "configs/paper_base.yaml",
            "configs/paper_hard.yaml",
            "configs/scenario_stress.yaml",
            "--train-methods",
            "periodic",
            "security_risk",
            "aoi_only",
            "--eval-methods",
            "periodic",
            "security_risk",
            "security_margin",
            "rollout_joint",
            "--train-seeds",
            "3",
            "--eval-seeds",
            "1",
            "--eval-seed-start",
            "20",
            "--alpha",
            "0.05",
            "--calibration-ratio",
            "0.2",
            "--outdir",
            str(holdout_outdir),
        ]
    )

    _run(
        [
            sys.executable,
            "-u",
            "-m",
            "experiments.run_readiness_multiseed",
            "--configs",
            str(holdout_outdir / "configs" / "paper_base_holdoutfit.yaml"),
            str(holdout_outdir / "configs" / "paper_hard_holdoutfit.yaml"),
            str(holdout_outdir / "configs" / "scenario_stress_holdoutfit.yaml"),
            "--methods",
            "periodic",
            "security_risk",
            "security_margin",
            "rollout_joint",
            "--num-seeds",
            "20",
            "--seed-start",
            "62",
            "--outdir",
            str(readiness_outdir),
        ]
    )

    _run(
        [
            sys.executable,
            "-u",
            "-m",
            "experiments.run_small_mdp_bound",
            "--config",
            "configs/small_mdp_bound.yaml",
            "--outdir",
            str(small_mdp_outdir),
        ]
    )

    _generate_doc(
        readiness_outdir=readiness_outdir,
        holdout_outdir=holdout_outdir,
        small_mdp_outdir=small_mdp_outdir,
        doc_path=doc_path,
    )
    print(f"[done] wrote result doc to {doc_path}")


if __name__ == "__main__":
    main()
