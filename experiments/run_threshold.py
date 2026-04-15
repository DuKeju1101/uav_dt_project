from __future__ import annotations

import argparse
from pathlib import Path
import copy
import pandas as pd

from experiments.common import ROOT, load_config, run_single_episode
from analysis.plotter import plot_line, plot_pareto
from analysis.metrics import aggregate_runs_with_ci


A_THR_LIST = [2, 4, 6, 8, 10]
RISK_TAU_LIST = [0.35, 0.45, 0.55, 0.65]
RHO_LIST = [0.02, 0.05, 0.10, 0.20]
METHODS = ["aoi_only", "security_risk", "security_margin"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=str(ROOT / "configs" / "base.yaml"))
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "threshold"))
    args = parser.parse_args()

    cfg = load_config(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows = []
    for method in METHODS:
        scan_values = A_THR_LIST if method == "aoi_only" else (RISK_TAU_LIST if method == "security_risk" else RHO_LIST)
        for val in scan_values:
            local_cfg = copy.deepcopy(cfg)
            if method == "aoi_only":
                local_cfg["sync"]["aoi_threshold"] = int(val)
            elif method == "security_risk":
                local_cfg["sync"]["tau0"] = float(val)
            elif method == "security_margin":
                local_cfg["sync"]["rho"] = float(val)
            for seed_offset in range(int(cfg.get("num_seeds", 5))):
                seed = int(cfg["seed"]) + seed_offset
                _, summary = run_single_episode(local_cfg, seed=seed, method=method)
                summary["scan_value"] = float(val)
                rows.append(summary)
                print(f"[done] method={method} scan={val} seed={seed}")

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "threshold_summary.csv", index=False)
    agg = aggregate_runs_with_ci(df, ["method", "scan_value"])
    agg.to_csv(outdir / "threshold_summary_agg.csv", index=False)

    plot_line(agg, x="scan_value", y="avg_secrecy_rate_mean", hue="method", title="Threshold scan vs avg secrecy rate", out_path=outdir / "threshold_vs_secrecy.png")
    plot_line(agg, x="scan_value", y="outage_prob_mean", hue="method", title="Threshold scan vs outage probability", out_path=outdir / "threshold_vs_outage.png")
    plot_pareto(agg, x="avg_sync_cost_mean", y="avg_secrecy_rate_mean", hue="method", title="Pareto: threshold methods", out_path=outdir / "threshold_pareto.png")
    print(f"Saved to: {outdir}")


if __name__ == "__main__":
    main()
