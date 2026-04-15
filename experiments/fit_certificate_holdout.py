from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from experiments.common import ROOT, load_config, run_single_episode
from experiments.fit_certificate_model import FEATURE_NAMES, build_feature_frame


def _collect_traces(config_paths: list[str], methods: list[str], num_seeds: int, seed_start: int = 0) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    frames = []
    feature_scales: dict[str, dict[str, float]] = {}
    for config_path in config_paths:
        cfg = load_config(config_path)
        scenario = Path(config_path).stem
        feature_scales[scenario] = {
            "aoi": float(cfg["metrics"]["a_max"]),
            "pred_error_radius": float(cfg["metrics"]["d_max"]),
            "sigma": float(cfg["metrics"]["sigma_max"]),
        }
        for seed_offset in range(seed_start, seed_start + num_seeds):
            seed = int(cfg["seed"]) + seed_offset
            for method in methods:
                df, _ = run_single_episode(copy.deepcopy(cfg), seed=seed, method=method)
                feats = build_feature_frame(df, cfg)
                feats["realized_loss"] = (df["pred_r_sec"] - df["true_r_sec"]).clip(lower=0.0)
                feats["scenario"] = scenario
                feats["method"] = method
                feats["seed"] = seed
                frames.append(feats)
                print(f"[done] split-data scenario={scenario} method={method} seed={seed}")
    return pd.concat(frames, ignore_index=True), feature_scales


def _fit_nonnegative_ridge(train_df: pd.DataFrame, ridge: float, residual_quantile: float, safety_scale: float) -> dict:
    x = np.nan_to_num(train_df[FEATURE_NAMES].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(train_df["realized_loss"].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    xtx = x.T @ x + ridge * np.eye(x.shape[1])
    xty = x.T @ y
    beta = np.linalg.solve(xtx, xty)
    beta = np.maximum(beta, 0.0)
    pred = x @ beta
    positive_residual = np.maximum(y - pred, 0.0)
    q = float(np.quantile(positive_residual, residual_quantile))
    return {
        "feature_names": FEATURE_NAMES,
        "coefficients": {name: float(val) for name, val in zip(FEATURE_NAMES, beta)},
        "intercept": 0.0,
        "residual_quantile": q,
        "safety_scale": float(safety_scale),
    }


def _evaluate(df: pd.DataFrame, model: dict, split: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = np.nan_to_num(df[FEATURE_NAMES].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    beta = np.array([float(model["coefficients"][name]) for name in FEATURE_NAMES], dtype=float)
    pred = np.maximum(x @ beta + float(model.get("intercept", 0.0)), 0.0)
    upper = pred + float(model.get("safety_scale", 1.0)) * float(model.get("residual_quantile", 0.0))
    loss = df["realized_loss"].to_numpy(dtype=float)
    eval_df = df[["scenario", "method", "seed", "realized_loss"]].copy()
    eval_df["predicted_loss"] = pred
    eval_df["upper_bound"] = upper
    eval_df["covered"] = (upper >= loss).astype(int)
    eval_df["upper_minus_loss"] = upper - loss
    eval_df["split"] = split

    rows = []
    overall = {
        "split": split,
        "scenario": "all",
        "cover_rate": float(eval_df["covered"].mean()),
        "mean_upper_minus_loss": float(eval_df["upper_minus_loss"].mean()),
        "p90_upper_minus_loss": float(eval_df["upper_minus_loss"].quantile(0.9)),
        "avg_realized_loss": float(eval_df["realized_loss"].mean()),
    }
    rows.append(overall)
    for scenario, group in eval_df.groupby("scenario"):
        rows.append(
            {
                "split": split,
                "scenario": scenario,
                "cover_rate": float(group["covered"].mean()),
                "mean_upper_minus_loss": float(group["upper_minus_loss"].mean()),
                "p90_upper_minus_loss": float(group["upper_minus_loss"].quantile(0.9)),
                "avg_realized_loss": float(group["realized_loss"].mean()),
            }
        )
    return eval_df, pd.DataFrame(rows)


def _write_config_with_model(config_path: str, outdir: Path, model: dict) -> Path:
    cfg = load_config(config_path)
    cfg["theory"] = {
        "loss_model": model,
        "feature_scales": {
            "aoi": float(cfg["metrics"]["a_max"]),
            "pred_error_radius": float(cfg["metrics"]["d_max"]),
            "sigma": float(cfg["metrics"]["sigma_max"]),
        },
    }
    outpath = outdir / f"{Path(config_path).stem}_holdoutfit.yaml"
    with open(outpath, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)
    return outpath


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-configs", nargs="+", required=True)
    parser.add_argument("--eval-configs", nargs="+", required=True)
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "certificate_holdout"))
    parser.add_argument("--train-methods", nargs="+", default=["periodic", "security_risk", "aoi_only"])
    parser.add_argument("--eval-methods", nargs="+", default=["periodic", "security_risk", "security_margin", "rollout_joint"])
    parser.add_argument("--train-seeds", type=int, default=2)
    parser.add_argument("--eval-seeds", type=int, default=1)
    parser.add_argument("--eval-seed-start", type=int, default=20)
    parser.add_argument("--ridge", type=float, default=1e-6)
    parser.add_argument("--residual-quantile", type=float, default=0.95)
    parser.add_argument("--safety-scale", type=float, default=1.1)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    train_df, _ = _collect_traces(args.train_configs, list(args.train_methods), args.train_seeds, seed_start=0)
    eval_df, _ = _collect_traces(args.eval_configs, list(args.eval_methods), args.eval_seeds, seed_start=args.eval_seed_start)
    train_df.to_csv(outdir / "holdout_train_traces.csv", index=False)
    eval_df.to_csv(outdir / "holdout_eval_traces.csv", index=False)

    model = _fit_nonnegative_ridge(
        train_df=train_df,
        ridge=float(args.ridge),
        residual_quantile=float(args.residual_quantile),
        safety_scale=float(args.safety_scale),
    )
    pd.DataFrame(
        {"feature": FEATURE_NAMES, "coefficient": [float(model["coefficients"][name]) for name in FEATURE_NAMES]}
    ).to_csv(outdir / "holdout_model_coefficients.csv", index=False)

    train_eval_df, train_summary = _evaluate(train_df, model, split="train")
    valid_eval_df, valid_summary = _evaluate(eval_df, model, split="validation")
    train_eval_df.to_csv(outdir / "holdout_train_predictions.csv", index=False)
    valid_eval_df.to_csv(outdir / "holdout_validation_predictions.csv", index=False)
    summary = pd.concat([train_summary, valid_summary], ignore_index=True)
    summary.to_csv(outdir / "holdout_summary.csv", index=False)

    config_paths = sorted(set(list(args.train_configs) + list(args.eval_configs)))
    config_outdir = outdir / "configs"
    config_outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for config_path in config_paths:
        written.append(str(_write_config_with_model(config_path, config_outdir, model)))
    (outdir / "written_configs.txt").write_text("\n".join(written) + "\n", encoding="utf-8")
    print(f"Saved holdout artifacts to: {outdir}")


if __name__ == "__main__":
    main()
