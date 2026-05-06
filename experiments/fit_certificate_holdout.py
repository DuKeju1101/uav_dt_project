from __future__ import annotations

import argparse
import copy
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from experiments.common import ROOT, load_config, run_single_episode
from experiments.fit_certificate_model import FEATURE_NAMES, build_feature_frame, fit_split_conformal_upper


def _scenario_names(config_paths: list[str]) -> set[str]:
    return {Path(config_path).stem for config_path in config_paths}


def _seed_values(config_paths: list[str], seed_start: int, num_seeds: int) -> set[int]:
    seeds: set[int] = set()
    for config_path in config_paths:
        cfg = load_config(config_path)
        base_seed = int(cfg["seed"])
        seeds.update(base_seed + offset for offset in range(seed_start, seed_start + num_seeds))
    return seeds


def _validate_holdout_inputs(
    train_configs: list[str],
    eval_configs: list[str],
    train_seed_start: int,
    train_seeds: int,
    eval_seed_start: int,
    eval_seeds: int,
    allow_overlap: bool,
) -> None:
    if allow_overlap:
        return

    scenario_overlap = _scenario_names(train_configs) & _scenario_names(eval_configs)
    if scenario_overlap:
        overlap = ", ".join(sorted(scenario_overlap))
        raise ValueError(f"Holdout train/eval scenarios overlap: {overlap}")

    train_seed_values = _seed_values(train_configs, train_seed_start, train_seeds)
    eval_seed_values = _seed_values(eval_configs, eval_seed_start, eval_seeds)
    seed_overlap = train_seed_values & eval_seed_values
    if seed_overlap:
        overlap = ", ".join(str(seed) for seed in sorted(seed_overlap))
        raise ValueError(f"Holdout train/eval seeds overlap: {overlap}")


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


def _evaluate(df: pd.DataFrame, model: dict, split: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    x = np.nan_to_num(df[FEATURE_NAMES].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    beta = np.array([float(model["coefficients"][name]) for name in FEATURE_NAMES], dtype=float)
    pred = np.maximum(x @ beta + float(model.get("intercept", 0.0)), 0.0)
    upper = pred + float(model.get("nonconformity_quantile", model.get("residual_quantile", 0.0)))
    loss = df["realized_loss"].to_numpy(dtype=float)
    eval_df = df[["scenario", "method", "seed", "realized_loss"]].copy()
    eval_df["predicted_loss"] = pred
    eval_df["upper_bound"] = upper
    eval_df["empirical_covered"] = (upper >= loss).astype(int)
    eval_df["covered"] = eval_df["empirical_covered"]
    eval_df["upper_minus_loss"] = upper - loss
    eval_df["split"] = split

    rows = []
    overall = {
        "split": split,
        "scenario": "all",
        "cover_rate": float(eval_df["empirical_covered"].mean()),
        "empirical_cover_rate": float(eval_df["empirical_covered"].mean()),
        "holdout_cover_rate": float(eval_df["empirical_covered"].mean()),
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
                "cover_rate": float(group["empirical_covered"].mean()),
                "empirical_cover_rate": float(group["empirical_covered"].mean()),
                "holdout_cover_rate": float(group["empirical_covered"].mean()),
                "mean_upper_minus_loss": float(group["upper_minus_loss"].mean()),
                "p90_upper_minus_loss": float(group["upper_minus_loss"].quantile(0.9)),
                "avg_realized_loss": float(group["realized_loss"].mean()),
            }
        )
    return eval_df, pd.DataFrame(rows)


def _split_eval_calibration(df: pd.DataFrame, calibration_ratio: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    calibration_ratio = float(calibration_ratio)
    if calibration_ratio <= 0.0:
        return df.iloc[0:0].copy(), df.copy()
    if calibration_ratio >= 1.0:
        raise ValueError("--posthoc-calibration-ratio must be less than 1.0")

    shuffled = df.sample(frac=1.0, random_state=1).reset_index(drop=True)
    calib_size = max(1, int(len(shuffled) * calibration_ratio))
    if calib_size >= len(shuffled):
        calib_size = max(1, len(shuffled) - 1)
    return shuffled.iloc[:calib_size].copy(), shuffled.iloc[calib_size:].copy()


def _conformal_quantile(nonconformity: np.ndarray, alpha: float) -> float:
    q_level = min(
        1.0,
        np.ceil((len(nonconformity) + 1) * (1.0 - float(alpha))) / max(len(nonconformity), 1),
    )
    return float(np.quantile(nonconformity, q_level, method="higher"))


def _calibrate_model_buffer(model: dict, df: pd.DataFrame, alpha: float, by_scenario: bool) -> dict:
    if df.empty:
        return model

    x = np.nan_to_num(df[FEATURE_NAMES].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    beta = np.array([float(model["coefficients"][name]) for name in FEATURE_NAMES], dtype=float)
    pred = np.maximum(x @ beta + float(model.get("intercept", 0.0)), 0.0)
    loss = df["realized_loss"].to_numpy(dtype=float)
    nonconformity = np.maximum(loss - pred, 0.0)

    scenario_qhats: dict[str, float] = {}
    if by_scenario:
        scenario_names = sorted(str(name) for name in df["scenario"].unique())
        scenario_alpha = float(alpha) / max(len(scenario_names), 1)
        for scenario in scenario_names:
            mask = df["scenario"].astype(str).to_numpy() == scenario
            scenario_qhats[scenario] = _conformal_quantile(nonconformity[mask], scenario_alpha)
        extra_qhat = max(scenario_qhats.values()) if scenario_qhats else 0.0
    else:
        extra_qhat = _conformal_quantile(nonconformity, alpha)

    current_qhat = float(model.get("nonconformity_quantile", model.get("residual_quantile", 0.0)))
    model["nonconformity_quantile"] = max(current_qhat, extra_qhat)
    model["posthoc_nonconformity_quantile"] = extra_qhat
    model["posthoc_scenario_nonconformity_quantiles"] = scenario_qhats
    model["posthoc_calibration_size"] = int(len(nonconformity))
    return model


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
    parser.add_argument("--train-seed-start", type=int, default=0)
    parser.add_argument("--eval-seeds", type=int, default=1)
    parser.add_argument("--eval-seed-start", type=int, default=100)
    parser.add_argument("--ridge", type=float, default=1e-6)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--calibration-ratio", type=float, default=0.2)
    parser.add_argument("--posthoc-calibration-ratio", type=float, default=0.0)
    parser.add_argument("--posthoc-calibration-by-scenario", action="store_true")
    parser.add_argument("--coverage-target", type=float, default=None)
    parser.add_argument("--allow-overlap", action="store_true")
    parser.add_argument("--allow-undercoverage", action="store_true")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    _validate_holdout_inputs(
        train_configs=list(args.train_configs),
        eval_configs=list(args.eval_configs),
        train_seed_start=int(args.train_seed_start),
        train_seeds=int(args.train_seeds),
        eval_seed_start=int(args.eval_seed_start),
        eval_seeds=int(args.eval_seeds),
        allow_overlap=bool(args.allow_overlap),
    )

    train_df, _ = _collect_traces(
        args.train_configs,
        list(args.train_methods),
        args.train_seeds,
        seed_start=int(args.train_seed_start),
    )
    eval_df, _ = _collect_traces(args.eval_configs, list(args.eval_methods), args.eval_seeds, seed_start=args.eval_seed_start)
    train_df.to_csv(outdir / "holdout_train_traces.csv", index=False)
    eval_df.to_csv(outdir / "holdout_eval_traces.csv", index=False)

    model, split_df = fit_split_conformal_upper(
        df=train_df,
        ridge=float(args.ridge),
        alpha=float(args.alpha),
        calibration_ratio=float(args.calibration_ratio),
    )
    split_df.to_csv(outdir / "holdout_train_splits.csv", index=False)
    pd.DataFrame(
        {"feature": FEATURE_NAMES, "coefficient": [float(model["coefficients"][name]) for name in FEATURE_NAMES]}
    ).to_csv(outdir / "holdout_model_coefficients.csv", index=False)

    eval_calib_df, eval_valid_df = _split_eval_calibration(eval_df, float(args.posthoc_calibration_ratio))
    if not eval_calib_df.empty:
        model = _calibrate_model_buffer(
            model,
            eval_calib_df,
            alpha=float(args.alpha),
            by_scenario=bool(args.posthoc_calibration_by_scenario),
        )

    train_eval_df, train_summary = _evaluate(train_df, model, split="train")
    valid_eval_df, valid_summary = _evaluate(eval_valid_df, model, split="validation")
    train_eval_df.to_csv(outdir / "holdout_train_predictions.csv", index=False)
    valid_eval_df.to_csv(outdir / "holdout_validation_predictions.csv", index=False)
    summaries = [train_summary, valid_summary]
    if not eval_calib_df.empty:
        calib_eval_df, calib_summary = _evaluate(eval_calib_df, model, split="posthoc_calibration")
        calib_eval_df.to_csv(outdir / "holdout_posthoc_calibration_predictions.csv", index=False)
        summaries.insert(1, calib_summary)
    summary = pd.concat(summaries, ignore_index=True)
    summary.to_csv(outdir / "holdout_summary.csv", index=False)

    coverage_target = float(args.coverage_target) if args.coverage_target is not None else 1.0 - float(args.alpha)
    validation_overall = summary[(summary["split"] == "validation") & (summary["scenario"] == "all")]
    if not validation_overall.empty:
        validation_cover = float(validation_overall.iloc[0]["cover_rate"])
        if validation_cover + 1e-12 < coverage_target and not bool(args.allow_undercoverage):
            raise ValueError(
                "Validation cover_rate below target: "
                f"{validation_cover:.6f} < {coverage_target:.6f}. "
                "Review the holdout split/model or rerun with --allow-undercoverage for diagnostics only."
            )
    validation_scenarios = summary[(summary["split"] == "validation") & (summary["scenario"] != "all")]
    undercovered = validation_scenarios[validation_scenarios["cover_rate"] + 1e-12 < coverage_target]
    if not undercovered.empty and not bool(args.allow_undercoverage):
        details = ", ".join(
            f"{row.scenario}={float(row.cover_rate):.6f}" for row in undercovered.itertuples(index=False)
        )
        raise ValueError(
            "Validation scenario cover_rate below target: "
            f"{details}; target={coverage_target:.6f}. "
            "Use --posthoc-calibration-by-scenario or a more conservative calibration split."
        )

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
