from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pandas as pd
import yaml

from experiments.common import ROOT, load_config, run_single_episode


RHO_GRID = [0.02, 0.04, 0.06, 0.08, 0.10]
SCALE_GRID = [0.25, 0.4, 0.55, 0.7, 0.85, 1.0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=str(ROOT / "configs" / "base.yaml"))
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "margin_calibration"))
    parser.add_argument("--out-config", type=str, default="")
    parser.add_argument("--num-seeds", type=int, default=4)
    args = parser.parse_args()

    cfg = load_config(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    base_coeffs = [float(x) for x in cfg["theory"]["margin_coeffs"]]
    rows = []

    for rho in RHO_GRID:
        for scale in SCALE_GRID:
            local_cfg = copy.deepcopy(cfg)
            local_cfg["sync"]["rho"] = float(rho)
            local_cfg["theory"]["margin_coeffs"] = [float(scale * x) for x in base_coeffs]
            for seed_offset in range(args.num_seeds):
                seed = int(cfg["seed"]) + seed_offset
                _, summary = run_single_episode(local_cfg, seed=seed, method="security_margin")
                summary["rho"] = float(rho)
                summary["coeff_scale"] = float(scale)
                rows.append(summary)
                print(f"[done] rho={rho} scale={scale} seed={seed}")

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "margin_calibration_all.csv", index=False)
    agg = (
        df.groupby(["rho", "coeff_scale"])[
            [
                "avg_secrecy_rate",
                "avg_sync_cost",
                "outage_prob",
                "prediction_violation_prob",
                "avg_cert_slack",
                "certified_safe_rate",
                "certificate_violation_prob",
            ]
        ]
        .mean()
        .reset_index()
    )
    agg["objective"] = (
        agg["avg_secrecy_rate"]
        - 0.7 * agg["outage_prob"]
        - 0.25 * agg["avg_sync_cost"]
        - 0.20 * agg["prediction_violation_prob"]
        - 0.20 * agg["certificate_violation_prob"]
        + 0.15 * agg["certified_safe_rate"]
        + 0.05 * agg["avg_cert_slack"]
    )
    agg = agg.sort_values("objective", ascending=False)
    agg.to_csv(outdir / "margin_calibration_summary.csv", index=False)

    best = agg.iloc[0]
    tuned_cfg = copy.deepcopy(cfg)
    tuned_cfg["sync"]["rho"] = float(best["rho"])
    tuned_cfg["theory"]["margin_coeffs"] = [float(best["coeff_scale"] * x) for x in base_coeffs]
    if args.out_config:
        out_config = Path(args.out_config)
    else:
        out_config = outdir / "tuned_config.yaml"
    out_config.parent.mkdir(parents=True, exist_ok=True)
    with open(out_config, "w", encoding="utf-8") as f:
        yaml.safe_dump(tuned_cfg, f, sort_keys=False, allow_unicode=True)

    print("Best calibration:")
    print(best.to_dict())
    print(f"Saved tuned config to: {out_config}")


if __name__ == "__main__":
    main()
