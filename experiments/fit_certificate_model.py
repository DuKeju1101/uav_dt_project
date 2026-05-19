from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from experiments.common import ROOT, load_config, run_single_episode


FEATURE_NAMES = [
    "bias",
    "aoi_norm",
    "pred_error_radius_norm",
    "sigma_norm",
    "sync_delay",
    "failure_prob",
    "aoi_x_radius",
    "radius_x_sigma",
    "aoi_x_sigma",
    "delay_x_radius",
    "delay_x_sigma",
]


def build_feature_frame(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    a_scale = max(float(cfg["metrics"]["a_max"]), 1e-12)
    d_scale = max(float(cfg["metrics"]["d_max"]), 1e-12)
    s_scale = max(float(cfg["metrics"]["sigma_max"]), 1e-12)
    out = pd.DataFrame()
    out["bias"] = 1.0
    out["aoi_norm"] = df["aoi"] / a_scale
    out["pred_error_radius_norm"] = df["pred_error_radius"] / d_scale
    out["sigma_norm"] = df["sigma"] / s_scale
    out["sync_delay"] = float(cfg["sync"].get("delay_slots", 0))
    out["failure_prob"] = float(cfg["sync"].get("failure_prob", 0.0))
    out["aoi_x_radius"] = out["aoi_norm"] * out["pred_error_radius_norm"]
    out["radius_x_sigma"] = out["pred_error_radius_norm"] * out["sigma_norm"]
    out["aoi_x_sigma"] = out["aoi_norm"] * out["sigma_norm"]
    out["delay_x_radius"] = out["sync_delay"] * out["pred_error_radius_norm"]
    out["delay_x_sigma"] = out["sync_delay"] * out["sigma_norm"]
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def fit_holdout_empirical_upper(
    df: pd.DataFrame,
    ridge: float,
    alpha: float,
    calibration_ratio: float,
) -> tuple[dict, pd.DataFrame]:
    shuffled = df.sample(frac=1.0, random_state=0).reset_index(drop=True)
    calib_size = max(1, int(len(shuffled) * calibration_ratio))
    if calib_size >= len(shuffled):
        calib_size = max(1, len(shuffled) // 5)
    train_core = shuffled.iloc[:-calib_size].copy() if len(shuffled) > calib_size else shuffled.copy()
    calib = shuffled.iloc[-calib_size:].copy()

    x_train = np.nan_to_num(train_core[FEATURE_NAMES].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    y_train = np.nan_to_num(train_core["realized_loss"].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    xtx = x_train.T @ x_train + ridge * np.eye(x_train.shape[1])
    xty = x_train.T @ y_train
    beta = np.linalg.solve(xtx, xty)
    beta = np.maximum(beta, 0.0)

    x_calib = np.nan_to_num(calib[FEATURE_NAMES].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    y_calib = np.nan_to_num(calib["realized_loss"].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    calib_pred = np.maximum(x_calib @ beta, 0.0)
    calibration_residuals = np.maximum(y_calib - calib_pred, 0.0)
    q_level = min(1.0, np.ceil((len(calibration_residuals) + 1) * (1.0 - alpha)) / max(len(calibration_residuals), 1))
    qhat = float(np.quantile(calibration_residuals, q_level, method="higher"))

    model_dict = {
        "model_type": "holdout_empirical_upper",
        "feature_names": FEATURE_NAMES,
        "coefficients": {name: float(val) for name, val in zip(FEATURE_NAMES, beta)},
        "intercept": 0.0,
        "alpha": float(alpha),
        "calibration_ratio": float(calibration_ratio),
        "calibration_residual_quantile": qhat,
        "nonconformity_quantile": qhat,
        "safety_scale": 1.0,
    }

    split_df = pd.DataFrame(
        {
            "split": ["train"] * len(train_core) + ["calibration"] * len(calib),
            "scenario": list(train_core["scenario"]) + list(calib["scenario"]),
            "method": list(train_core["method"]) + list(calib["method"]),
            "seed": list(train_core["seed"]) + list(calib["seed"]),
        }
    )
    return model_dict, split_df


# Backward-compatible alias for older experiment commands.
fit_split_conformal_upper = fit_holdout_empirical_upper


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--configs",
        nargs="+",
        default=[
            str(ROOT / "configs" / "base.yaml"),
            str(ROOT / "configs" / "scenario_hard.yaml"),
            str(ROOT / "configs" / "scenario_stress.yaml"),
        ],
    )
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "certificate_fit"))
    parser.add_argument("--out-configs-dir", type=str, default=str(ROOT / "configs"))
    parser.add_argument("--num-seeds", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--calibration-ratio", type=float, default=0.2)
    parser.add_argument("--ridge", type=float, default=1e-6)
    parser.add_argument("--methods", nargs="+", default=["periodic", "security_risk", "aoi_only", "rollout_joint"])
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_configs_dir = Path(args.out_configs_dir)
    out_configs_dir.mkdir(parents=True, exist_ok=True)

    trace_frames = []
    methods = list(args.methods)
    base_feature_scales = None
    for config_path in args.configs:
        cfg = load_config(config_path)
        base_feature_scales = {
            "aoi": float(cfg["metrics"]["a_max"]),
            "pred_error_radius": float(cfg["metrics"]["d_max"]),
            "sigma": float(cfg["metrics"]["sigma_max"]),
        }
        scenario = Path(config_path).stem
        for seed_offset in range(args.num_seeds):
            seed = int(cfg["seed"]) + seed_offset
            for method in methods:
                df, _ = run_single_episode(copy.deepcopy(cfg), seed=seed, method=method)
                feats = build_feature_frame(df, cfg)
                feats["realized_loss"] = (df["pred_r_sec"] - df["true_r_sec"]).clip(lower=0.0)
                feats["scenario"] = scenario
                feats["method"] = method
                feats["seed"] = seed
                trace_frames.append(feats)
                print(f"[done] fit-data scenario={scenario} method={method} seed={seed}")

    train_df = pd.concat(trace_frames, ignore_index=True)
    train_df.to_csv(outdir / "certificate_fit_traces.csv", index=False)
    model_dict, split_df = fit_holdout_empirical_upper(
        train_df,
        ridge=float(args.ridge),
        alpha=float(args.alpha),
        calibration_ratio=float(args.calibration_ratio),
    )
    split_df.to_csv(outdir / "certificate_fit_splits.csv", index=False)

    summary = pd.DataFrame(
        {
            "feature": FEATURE_NAMES,
            "coefficient": [float(model_dict["coefficients"][name]) for name in FEATURE_NAMES],
        }
    )
    summary.to_csv(outdir / "certificate_fit_coefficients.csv", index=False)

    metrics_rows = []
    x = np.nan_to_num(train_df[FEATURE_NAMES].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    pred = np.maximum(x @ np.array([float(model_dict["coefficients"][name]) for name in FEATURE_NAMES], dtype=float), 0.0)
    y = np.nan_to_num(train_df["realized_loss"].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    pred_upper = pred + float(model_dict["nonconformity_quantile"])
    cover_rate = float(np.mean(pred_upper >= y))
    mean_gap = float(np.mean(pred_upper - y))
    metrics_rows.append(
        {
            "cover_rate": cover_rate,
            "mean_upper_minus_loss": mean_gap,
            "alpha": float(model_dict["alpha"]),
            "nonconformity_quantile": float(model_dict["nonconformity_quantile"]),
        }
    )
    pd.DataFrame(metrics_rows).to_csv(outdir / "certificate_fit_metrics.csv", index=False)

    for config_path in args.configs:
        cfg = load_config(config_path)
        cfg["theory"] = {
            "loss_model": model_dict,
            "feature_scales": {
                "aoi": float(cfg["metrics"]["a_max"]),
                "pred_error_radius": float(cfg["metrics"]["d_max"]),
                "sigma": float(cfg["metrics"]["sigma_max"]),
            },
        }
        out_path = out_configs_dir / f"{Path(config_path).stem}_fitted.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
        print(f"Saved fitted config: {out_path}")

    print(f"Saved fit artifacts to: {outdir}")


if __name__ == "__main__":
    main()
