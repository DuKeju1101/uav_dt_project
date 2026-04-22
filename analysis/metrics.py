from __future__ import annotations

from typing import Dict
import numpy as np
import pandas as pd


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
    cert_cover_rate = float(df["cert_cover"].mean()) if "cert_cover" in df.columns else 0.0
    realized_loss_mean = float(df["realized_loss"].mean()) if "realized_loss" in df.columns else 0.0
    return {
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
        "prediction_violation_prob": violation_slots,
        "outage_prob": outage,
        "success_prob": success,
    }


def aggregate_runs(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    metrics = [
        "avg_sync_cost",
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
            ci95 = 1.96 * stderr
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95"] = ci95
        row["num_runs"] = int(len(group))
        frames.append(row)
    return pd.DataFrame(frames)


def compute_tfscc(df: pd.DataFrame, x_col: str = "avg_twin_badness", y_col: str = "avg_secrecy_rate") -> pd.DataFrame:
    df = df.sort_values(x_col).copy()
    dx = df[x_col].diff()
    dy = df[y_col].diff()
    df["tfscc"] = -dy / dx.replace(0, np.nan)
    return df
