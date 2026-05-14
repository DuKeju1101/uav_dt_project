from __future__ import annotations

from typing import Dict, Iterable
import hashlib
import math
import numpy as np
import pandas as pd


DEFAULT_BOOTSTRAP_SAMPLES = 2000


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bootstrap_mean_ci(
    values: Iterable[float],
    *,
    n_boot: int = DEFAULT_BOOTSTRAP_SAMPLES,
    alpha: float = 0.05,
    seed: int = 12345,
) -> tuple[float, float]:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return 0.0, 0.0
    if len(arr) == 1:
        val = float(arr[0])
        return val, val
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(arr), size=(int(n_boot), len(arr)))
    means = arr[indices].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2.0, 1.0 - alpha / 2.0])
    return float(lo), float(hi)


def _holm_adjust(p_values: list[float]) -> list[float]:
    m = len(p_values)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda idx: p_values[idx])
    adjusted = [1.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        raw = min(1.0, (m - rank) * float(p_values[idx]))
        running = max(running, raw)
        adjusted[idx] = min(1.0, running)
    return adjusted


def _bonferroni_adjust(p_values: list[float]) -> list[float]:
    m = max(len(p_values), 1)
    return [min(1.0, float(p) * m) for p in p_values]


def _stable_seed(parts: Iterable[object]) -> int:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values)
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and values[order[j]] == values[order[i]]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        ranks[order[i:j]] = avg_rank
        i = j
    return ranks


def wilcoxon_signed_rank(diff: Iterable[float]) -> dict[str, float]:
    arr = np.asarray(list(diff), dtype=float)
    arr = arr[np.isfinite(arr)]
    arr = arr[np.abs(arr) > 1e-12]
    n = int(len(arr))
    if n == 0:
        return {
            "wilcoxon_n": 0,
            "wilcoxon_w_plus": 0.0,
            "wilcoxon_w_minus": 0.0,
            "wilcoxon_stat": 0.0,
            "wilcoxon_pvalue": 1.0,
            "rank_biserial": 0.0,
        }
    ranks = _average_ranks(np.abs(arr))
    w_plus = float(ranks[arr > 0].sum())
    w_minus = float(ranks[arr < 0].sum())
    stat = min(w_plus, w_minus)
    rank_sum = float(ranks.sum())
    rank_biserial = (w_plus - w_minus) / max(rank_sum, 1e-12)

    if n <= 20:
        possible = np.array([0.0])
        for rank in ranks:
            possible = np.concatenate([possible, possible + rank])
        observed = min(w_plus, rank_sum - w_plus)
        pvalue = min(1.0, 2.0 * float(np.mean(possible <= observed + 1e-12)))
    else:
        mean = n * (n + 1.0) / 4.0
        var = n * (n + 1.0) * (2.0 * n + 1.0) / 24.0
        z = (abs(w_plus - mean) - 0.5) / max(math.sqrt(var), 1e-12)
        pvalue = float(2.0 * (1.0 - _normal_cdf(abs(z))))

    return {
        "wilcoxon_n": n,
        "wilcoxon_w_plus": w_plus,
        "wilcoxon_w_minus": w_minus,
        "wilcoxon_stat": stat,
        "wilcoxon_pvalue": pvalue,
        "rank_biserial": float(rank_biserial),
    }


def _paired_cliffs_delta(target: np.ndarray, baseline: np.ndarray) -> float:
    comparisons = target[:, None] - baseline[None, :]
    greater = float((comparisons > 0.0).sum())
    less = float((comparisons < 0.0).sum())
    denom = max(float(comparisons.size), 1.0)
    return float((greater - less) / denom)


def paired_comparisons(
    all_runs: pd.DataFrame,
    *,
    target: str,
    baselines: list[str],
    metric: str = "avg_secrecy_rate",
    group_col: str = "scenario",
    seed_col: str = "seed",
    n_boot: int = DEFAULT_BOOTSTRAP_SAMPLES,
    alpha: float = 0.05,
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    required = {group_col, seed_col, "method", metric}
    missing = required - set(all_runs.columns)
    if missing:
        raise ValueError(f"Missing columns for paired comparisons: {sorted(missing)}")

    for group_value, group in all_runs.groupby(group_col):
        target_df = group[group["method"] == target][[seed_col, metric]].rename(columns={metric: "target_metric"})
        for baseline in baselines:
            base_df = group[group["method"] == baseline][[seed_col, metric]].rename(columns={metric: "baseline_metric"})
            merged = base_df.merge(target_df, on=seed_col, how="inner").sort_values(seed_col)
            if merged.empty:
                continue
            base = merged["baseline_metric"].to_numpy(dtype=float)
            targ = merged["target_metric"].to_numpy(dtype=float)
            diff = targ - base
            n = int(len(diff))
            mean_diff = float(np.mean(diff))
            std_diff = float(np.std(diff, ddof=1)) if n > 1 else 0.0
            stderr = std_diff / math.sqrt(n) if n > 1 else 0.0
            t_stat = mean_diff / max(stderr, 1e-12) if n > 1 else 0.0
            # Normal-tail approximation for the t statistic; Wilcoxon is reported alongside it.
            pvalue = float(2.0 * (1.0 - _normal_cdf(abs(t_stat)))) if n > 1 else 1.0
            ci_low, ci_high = bootstrap_mean_ci(
                diff,
                n_boot=n_boot,
                alpha=alpha,
                seed=_stable_seed((group_value, target, baseline, metric)),
            )
            wilcoxon = wilcoxon_signed_rank(diff)
            rows.append(
                {
                    group_col: group_value,
                    "target": target,
                    "baseline": baseline,
                    "metric": metric,
                    "num_pairs": n,
                    "mean_diff": mean_diff,
                    "bootstrap_ci95_low": ci_low,
                    "bootstrap_ci95_high": ci_high,
                    "paired_t_stat": float(t_stat),
                    "paired_t_pvalue_approx": pvalue,
                    "wilcoxon_pvalue": float(wilcoxon["wilcoxon_pvalue"]),
                    "wilcoxon_stat": float(wilcoxon["wilcoxon_stat"]),
                    "cohen_dz": float(mean_diff / max(std_diff, 1e-12)) if n > 1 else 0.0,
                    "rank_biserial": float(wilcoxon["rank_biserial"]),
                    "cliffs_delta": _paired_cliffs_delta(targ, base),
                    "win_pairs": int((diff > 0.0).sum()),
                    "loss_pairs": int((diff < 0.0).sum()),
                    "tie_pairs": int((np.abs(diff) <= 1e-12).sum()),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["paired_t_pvalue_holm"] = _holm_adjust(result["paired_t_pvalue_approx"].tolist())
    result["paired_t_pvalue_bonferroni"] = _bonferroni_adjust(result["paired_t_pvalue_approx"].tolist())
    result["wilcoxon_pvalue_holm"] = _holm_adjust(result["wilcoxon_pvalue"].tolist())
    result["wilcoxon_pvalue_bonferroni"] = _bonferroni_adjust(result["wilcoxon_pvalue"].tolist())
    return result


def summarize_episode(df: pd.DataFrame) -> Dict[str, float]:
    mean_sync = float(df["sync"].mean())
    mean_sync_cost = float(df["sync_cost"].mean()) if "sync_cost" in df.columns else mean_sync
    mean_sync_bandwidth = float(df["sync_bandwidth"].mean()) if "sync_bandwidth" in df.columns else mean_sync_cost
    mean_q = float(df["twin_quality"].mean())
    mean_badness = float(df["twin_badness"].mean())
    mean_r_sec = float(df["true_r_sec"].mean())
    outage = float(df["outage"].mean())
    success = float(df["success"].mean())
    mean_sync_applied = float(df["sync_applied"].mean()) if "sync_applied" in df.columns else mean_sync
    pending_mean = float(df["pending_syncs"].mean()) if "pending_syncs" in df.columns else 0.0
    violation_slots = float((df["true_r_sec"] < df["pred_r_sec"]).mean()) if "pred_r_sec" in df.columns else 0.0
    avg_margin_gap = float((df["pred_r_sec"] - df["true_r_sec"]).mean()) if "pred_r_sec" in df.columns else 0.0
    cert_safe_rate = float(df["certified_safe"].mean()) if "certified_safe" in df.columns else 0.0
    cert_slack_mean = float(df["cert_slack"].mean()) if "cert_slack" in df.columns else 0.0
    cert_violation_rate = float((df["cert_slack"] < 0.0).mean()) if "cert_slack" in df.columns else 0.0
    cert_margin_cover_rate = float(
        df["cert_margin_cover"].mean()
        if "cert_margin_cover" in df.columns
        else df["cert_cover"].mean()
    ) if ("cert_margin_cover" in df.columns or "cert_cover" in df.columns) else 0.0
    cert_empirical_cover_rate = float(
        df["cert_empirical_cover"].mean()
        if "cert_empirical_cover" in df.columns
        else df["cert_cover"].mean()
    ) if ("cert_empirical_cover" in df.columns or "cert_cover" in df.columns) else 0.0
    cert_cover_rate = cert_empirical_cover_rate
    realized_loss_mean = float(df["realized_loss"].mean()) if "realized_loss" in df.columns else 0.0
    episode_length = float(len(df))
    total_r_sec = float(df["true_r_sec"].sum())
    return {
        "episode_length": episode_length,
        "total_secrecy_rate": total_r_sec,
        "avg_sync_cost": mean_sync_cost,
        "avg_sync_bandwidth": mean_sync_bandwidth,
        "sync_request_rate": mean_sync,
        "avg_sync_applied": mean_sync_applied,
        "avg_pending_syncs": pending_mean,
        "avg_twin_quality": mean_q,
        "avg_twin_badness": mean_badness,
        "avg_secrecy_rate": mean_r_sec,
        "avg_realized_loss": realized_loss_mean,
        "avg_margin_gap": avg_margin_gap,
        "avg_cert_slack": cert_slack_mean,
        "certified_safe_rate": cert_safe_rate,
        "certificate_violation_prob": cert_violation_rate,
        "certificate_cover_rate": cert_cover_rate,
        "certificate_in_policy_cover_rate": cert_cover_rate,
        "certificate_empirical_cover_rate": cert_empirical_cover_rate,
        "certificate_margin_cover_rate": cert_margin_cover_rate,
        "prediction_violation_prob": violation_slots,
        "outage_prob": outage,
        "success_prob": success,
    }


def aggregate_runs(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    metrics = [
        "avg_sync_cost",
        "episode_length",
        "total_secrecy_rate",
        "avg_sync_bandwidth",
        "sync_request_rate",
        "avg_sync_applied",
        "avg_pending_syncs",
        "avg_twin_quality",
        "avg_twin_badness",
        "avg_secrecy_rate",
        "avg_realized_loss",
        "avg_margin_gap",
        "avg_cert_slack",
        "certified_safe_rate",
        "certificate_violation_prob",
        "certificate_cover_rate",
        "certificate_in_policy_cover_rate",
        "certificate_empirical_cover_rate",
        "certificate_margin_cover_rate",
        "prediction_violation_prob",
        "outage_prob",
        "success_prob",
        "runtime_sec",
        "runtime_per_slot_ms",
    ]
    grouped = df.groupby(group_cols)[metrics].agg(["mean", "std"]).reset_index()
    grouped.columns = ["_".join(col).strip("_") for col in grouped.columns.values]
    return grouped


def aggregate_runs_with_ci(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    metrics = [
        "avg_sync_cost",
        "episode_length",
        "total_secrecy_rate",
        "avg_sync_bandwidth",
        "sync_request_rate",
        "avg_sync_applied",
        "avg_pending_syncs",
        "avg_twin_quality",
        "avg_twin_badness",
        "avg_secrecy_rate",
        "avg_realized_loss",
        "avg_margin_gap",
        "avg_cert_slack",
        "certified_safe_rate",
        "certificate_violation_prob",
        "certificate_cover_rate",
        "certificate_in_policy_cover_rate",
        "certificate_empirical_cover_rate",
        "certificate_margin_cover_rate",
        "prediction_violation_prob",
        "outage_prob",
        "success_prob",
        "runtime_sec",
        "runtime_per_slot_ms",
    ]
    grouped = df.groupby(group_cols)
    frames = []
    for keys, group in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: key for col, key in zip(group_cols, keys)}
        n = max(len(group), 1)
        for metric in metrics:
            mean = float(group[metric].mean())
            std = float(group[metric].std(ddof=1)) if len(group) > 1 else 0.0
            stderr = std / np.sqrt(n) if n > 0 else 0.0
            ci_low, ci_high = bootstrap_mean_ci(
                group[metric].to_numpy(dtype=float),
                n_boot=DEFAULT_BOOTSTRAP_SAMPLES,
                seed=_stable_seed((*keys, metric)),
            )
            ci95 = max(mean - ci_low, ci_high - mean)
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95"] = ci95
            row[f"{metric}_ci95_low"] = ci_low
            row[f"{metric}_ci95_high"] = ci_high
        row["num_runs"] = int(len(group))
        frames.append(row)
    return pd.DataFrame(frames)


def compute_tfscc(df: pd.DataFrame, x_col: str = "avg_twin_badness", y_col: str = "avg_secrecy_rate") -> pd.DataFrame:
    df = df.sort_values(x_col).copy()
    dx = df[x_col].diff()
    dy = df[y_col].diff()
    df["tfscc"] = -dy / dx.replace(0, np.nan)
    return df
