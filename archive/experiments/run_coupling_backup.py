from __future__ import annotations

import argparse
from pathlib import Path
import copy
import pandas as pd

from experiments.common import ROOT, load_config, run_single_episode
from analysis.metrics import compute_tfscc
from analysis.plotter import plot_line, plot_scatter, plot_pareto


PERIODIC_LIST = [1, 2, 4, 8, 12, 16, 20]
BUDGET_LIST = [20, 40, 60, 80]
EVE_SPEED_LIST = [0.0, 2.0, 4.0, 6.0, 8.0]


def set_eve_speed(cfg: dict, speed: float) -> None:
    if speed == 0:
        cfg["eve"]["velocity"] = [0.0, 0.0]
    else:
        cfg["eve"]["velocity"] = [float(-speed), float(0.0)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=str(ROOT / "configs" / "base.yaml"))
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "coupling"))
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    periodic_list = [1, 4, 8] if args.quick else PERIODIC_LIST
    budget_list = [20, 60] if args.quick else BUDGET_LIST
    eve_speed_list = [0.0, 4.0, 8.0] if args.quick else EVE_SPEED_LIST

    rows = []
    for k in periodic_list:
        for budget in budget_list:
            for eve_speed in eve_speed_list:
                local_cfg = copy.deepcopy(cfg)
                local_cfg["sync"]["periodic_k"] = int(k)
                local_cfg["sync"]["budget"] = int(budget)
                set_eve_speed(local_cfg, eve_speed)
                for seed_offset in range(int(cfg.get("num_seeds", 5))):
                    seed = int(cfg["seed"]) + seed_offset
                    _, summary = run_single_episode(local_cfg, seed=seed, method="periodic")
                    summary.update({"periodic_k": k, "budget": budget, "eve_speed": eve_speed})
                    rows.append(summary)
                    print(f"[done] k={k} budget={budget} eve_speed={eve_speed} seed={seed}")

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "coupling_summary.csv", index=False)

    agg = df.groupby(["periodic_k", "budget", "eve_speed"])[[
        "avg_sync_cost", "avg_twin_quality", "avg_twin_badness", "avg_secrecy_rate", "outage_prob", "success_prob"
    ]].mean().reset_index()
    agg.to_csv(outdir / "coupling_summary_agg.csv", index=False)

    cliff_df = agg.groupby("periodic_k")[["avg_sync_cost", "avg_twin_quality", "avg_secrecy_rate", "outage_prob"]].mean().reset_index()
    plot_line(cliff_df.assign(method="periodic"), x="periodic_k", y="avg_secrecy_rate", hue="method", title="Cliff effect: periodic_k vs avg secrecy rate", out_path=outdir / "cliff_effect.png")
    plot_line(cliff_df.assign(method="periodic"), x="periodic_k", y="avg_twin_quality", hue="method", title="Periodic_k vs twin quality", out_path=outdir / "periodic_vs_twin_quality.png")
    plot_line(cliff_df.assign(method="periodic"), x="periodic_k", y="outage_prob", hue="method", title="Periodic_k vs outage probability", out_path=outdir / "periodic_vs_outage.png")

    qmap = agg.groupby(["budget", "eve_speed"])[["avg_twin_quality", "avg_secrecy_rate", "avg_sync_cost"]].mean().reset_index()
    plot_scatter(qmap.astype({"budget": str}), x="avg_twin_quality", y="avg_secrecy_rate", hue="budget", title="Twin quality vs secrecy rate", out_path=outdir / "q_vs_rs.png")
    plot_pareto(agg.astype({"budget": str}), x="avg_sync_cost", y="avg_secrecy_rate", hue="budget", title="Pareto front: sync cost vs secrecy rate", out_path=outdir / "pareto_sync_vs_secrecy.png")

    tfscc_rows = []
    for eve_speed, g in agg.groupby("eve_speed"):
        tmp = compute_tfscc(g[["avg_twin_badness", "avg_secrecy_rate"]].copy())
        tmp["eve_speed"] = eve_speed
        tfscc_rows.append(tmp)
    df_tfscc = pd.concat(tfscc_rows, ignore_index=True)
    df_tfscc.to_csv(outdir / "tfscc.csv", index=False)
    tfscc_plot = df_tfscc.groupby("eve_speed")["tfscc"].mean().reset_index().assign(method="periodic")
    plot_line(tfscc_plot, x="eve_speed", y="tfscc", hue="method", title="TFSCC vs Eve speed", out_path=outdir / "tfscc_vs_eve_speed.png")
    print(f"Saved to: {outdir}")


if __name__ == "__main__":
    main()
