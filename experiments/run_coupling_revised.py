from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import yaml

from analysis.metrics import aggregate_runs_with_ci, compute_tfscc
from analysis.plotter import plot_line, plot_pareto, plot_scatter
from experiments.common import ROOT, load_config, run_single_episode


PERIODIC_LIST = [1, 2, 4, 8, 12, 16, 20]
BUDGET_LIST = [20, 40, 60, 80]
EVE_SPEED_LIST = [0.0, 2.0, 4.0, 6.0, 8.0]
SYNC_DELAY_LIST = [0, 1, 2]

DEBUG_BUDGET = 20
DEBUG_EVE_SPEED = 4.0
DEBUG_PERIODIC_LIST = [1, 8, 20]


def set_eve_speed(cfg: dict, speed: float) -> None:
    if speed == 0:
        cfg["eve"]["velocity"] = [0.0, 0.0]
    else:
        # Keep a simple deterministic direction for repeatability.
        cfg["eve"]["velocity"] = [float(-speed), 0.0]


def save_config_signature(cfg: dict, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "config_used.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def lineplot_from_grouped(
    df: pd.DataFrame,
    x: str,
    y: str,
    hue: str,
    title: str,
    out_path: Path,
) -> None:
    if df.empty:
        return
    plot_line(df.copy(), x=x, y=y, hue=hue, title=title, out_path=out_path)


def _to_label_pair(budget: int, eve_speed: float) -> str:
    return f"budget={budget}, eve_speed={eve_speed}"


def export_debug_slots(
    cfg: dict,
    outdir: Path,
    periodic_list: Iterable[int],
    budget: int,
    eve_speed: float,
) -> None:
    debug_dir = outdir / "debug_slots"
    debug_dir.mkdir(parents=True, exist_ok=True)

    local_base = copy.deepcopy(cfg)
    local_base["sync"]["budget"] = int(budget)
    set_eve_speed(local_base, eve_speed)

    seed = int(local_base["seed"])
    for k in periodic_list:
        local_cfg = copy.deepcopy(local_base)
        local_cfg["sync"]["periodic_k"] = int(k)
        df, _ = run_single_episode(local_cfg, seed=seed, method="periodic")
        df.to_csv(debug_dir / f"slot_periodic_k{k}_budget{budget}_eve{int(eve_speed)}_seed{seed}.csv", index=False)



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=str(ROOT / "configs" / "base.yaml"))
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "coupling"))
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "debug_slots").mkdir(parents=True, exist_ok=True)
    save_config_signature(cfg, outdir)

    periodic_list = [1, 8, 20] if args.quick else PERIODIC_LIST
    budget_list = [20, 60] if args.quick else BUDGET_LIST
    eve_speed_list = [0.0, 4.0, 8.0] if args.quick else EVE_SPEED_LIST
    sync_delay_list = [0, 1] if args.quick else SYNC_DELAY_LIST

    rows: list[dict] = []
    for k in periodic_list:
        for budget in budget_list:
            for eve_speed in eve_speed_list:
                for sync_delay in sync_delay_list:
                    local_cfg = copy.deepcopy(cfg)
                    local_cfg["sync"]["periodic_k"] = int(k)
                    local_cfg["sync"]["budget"] = int(budget)
                    local_cfg["sync"]["delay_slots"] = int(sync_delay)
                    set_eve_speed(local_cfg, eve_speed)
                    for seed_offset in range(int(cfg.get("num_seeds", 5))):
                        seed = int(cfg["seed"]) + seed_offset
                        slot_df, summary = run_single_episode(local_cfg, seed=seed, method="periodic")
                        summary.update(
                            {
                                "periodic_k": int(k),
                                "budget": int(budget),
                                "eve_speed": float(eve_speed),
                                "sync_delay": int(sync_delay),
                                "seed": int(seed),
                            }
                        )
                        rows.append(summary)
                        if (
                            budget == DEBUG_BUDGET
                            and eve_speed == DEBUG_EVE_SPEED
                            and k in DEBUG_PERIODIC_LIST
                            and sync_delay == 0
                            and seed_offset == 0
                        ):
                            slot_df.to_csv(
                                outdir / "debug_slots" / f"slot_periodic_k{k}_budget{budget}_eve{int(eve_speed)}_seed{seed}.csv",
                                index=False,
                            )
                        print(f"[done] k={k} budget={budget} eve_speed={eve_speed} delay={sync_delay} seed={seed}")

    df = pd.DataFrame(rows)
    df.to_csv(outdir / "coupling_summary.csv", index=False)

    agg = aggregate_runs_with_ci(df, ["periodic_k", "budget", "eve_speed", "sync_delay"])
    agg.to_csv(outdir / "coupling_summary_agg.csv", index=False)

    # 1) Fixed-slice cliff plots: do NOT average away budget/eve_speed.
    # Plot one line per (budget, eve_speed) pair.
    cliff_df = agg[agg["sync_delay"] == 0].copy()
    cliff_df["slice"] = cliff_df.apply(lambda r: _to_label_pair(int(r["budget"]), float(r["eve_speed"])), axis=1)
    lineplot_from_grouped(
        cliff_df,
        x="periodic_k",
        y="avg_secrecy_rate_mean",
        hue="slice",
        title="Cliff effect: periodic_k vs avg secrecy rate (fixed budget/eve speed slices)",
        out_path=outdir / "cliff_effect.png",
    )
    lineplot_from_grouped(
        cliff_df,
        x="periodic_k",
        y="avg_twin_quality_mean",
        hue="slice",
        title="Periodic_k vs twin quality (fixed budget/eve speed slices)",
        out_path=outdir / "periodic_vs_twin_quality.png",
    )
    lineplot_from_grouped(
        cliff_df,
        x="periodic_k",
        y="outage_prob_mean",
        hue="slice",
        title="Periodic_k vs outage probability (fixed budget/eve speed slices)",
        out_path=outdir / "periodic_vs_outage.png",
    )

    # 2) A focused debug slice, easiest to inspect manually.
    focus_budget = DEBUG_BUDGET if DEBUG_BUDGET in budget_list else budget_list[0]
    focus_eve_speed = DEBUG_EVE_SPEED if DEBUG_EVE_SPEED in eve_speed_list else eve_speed_list[min(1, len(eve_speed_list) - 1)]
    focus_df = agg[(agg["budget"] == focus_budget) & (agg["eve_speed"] == focus_eve_speed) & (agg["sync_delay"] == 0)].copy()
    if not focus_df.empty:
        focus_df = focus_df.assign(method=f"budget={focus_budget}, eve_speed={focus_eve_speed}")
        plot_line(
            focus_df,
            x="periodic_k",
            y="avg_secrecy_rate_mean",
            hue="method",
            title=f"Focused cliff slice: budget={focus_budget}, eve_speed={focus_eve_speed}",
            out_path=outdir / "cliff_effect_focus.png",
        )
        plot_line(
            focus_df,
            x="periodic_k",
            y="outage_prob_mean",
            hue="method",
            title=f"Focused outage slice: budget={focus_budget}, eve_speed={focus_eve_speed}",
            out_path=outdir / "periodic_vs_outage_focus.png",
        )

    # 3) Q vs secrecy should keep periodic_k visible instead of averaging it away.
    qmap = agg[agg["sync_delay"] == 0].copy().astype({"periodic_k": str})
    plot_scatter(
        qmap,
        x="avg_twin_quality_mean",
        y="avg_secrecy_rate_mean",
        hue="periodic_k",
        title="Twin quality vs secrecy rate (colored by periodic_k)",
        out_path=outdir / "q_vs_rs.png",
    )

    # 4) Pareto per periodic_k instead of per budget.
    pareto_df = agg[agg["sync_delay"] == 0].copy().astype({"periodic_k": str})
    plot_pareto(
        pareto_df,
        x="avg_sync_cost_mean",
        y="avg_secrecy_rate_mean",
        hue="periodic_k",
        title="Pareto front: sync cost vs secrecy rate (colored by periodic_k)",
        out_path=outdir / "pareto_sync_vs_secrecy.png",
    )

    # 5) TFSCC should be computed within each fixed (budget, eve_speed) slice.
    tfscc_rows: list[pd.DataFrame] = []
    for (budget, eve_speed), g in agg[agg["sync_delay"] == 0].groupby(["budget", "eve_speed"]):
        tmp = compute_tfscc(g[["periodic_k", "avg_twin_badness_mean", "avg_secrecy_rate_mean"]].copy(), x_col="avg_twin_badness_mean", y_col="avg_secrecy_rate_mean")
        tmp["budget"] = int(budget)
        tmp["eve_speed"] = float(eve_speed)
        tfscc_rows.append(tmp)

    if tfscc_rows:
        df_tfscc = pd.concat(tfscc_rows, ignore_index=True)
    else:
        df_tfscc = pd.DataFrame(columns=["periodic_k", "avg_twin_badness_mean", "avg_secrecy_rate_mean", "tfscc", "budget", "eve_speed"])
    df_tfscc.to_csv(outdir / "tfscc.csv", index=False)

    tfscc_plot = (
        df_tfscc.groupby("eve_speed")["tfscc"].mean().reset_index().assign(method="periodic")
        if not df_tfscc.empty
        else pd.DataFrame({"eve_speed": [], "tfscc": [], "method": []})
    )
    if not tfscc_plot.empty:
        plot_line(
            tfscc_plot,
            x="eve_speed",
            y="tfscc",
            hue="method",
            title="TFSCC vs Eve speed",
            out_path=outdir / "tfscc_vs_eve_speed.png",
        )

    # 6) Save a compact focus table for quick reading.
    focus_table = agg[(agg["budget"] == focus_budget) & (agg["eve_speed"] == focus_eve_speed)].copy()
    focus_table.to_csv(outdir / "focus_slice_budget20_eve4.csv", index=False)

    print(f"Saved to: {outdir}")


if __name__ == "__main__":
    main()
