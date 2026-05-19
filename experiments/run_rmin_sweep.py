from __future__ import annotations

import argparse
import copy
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from analysis.metrics import aggregate_runs_with_ci
from experiments.common import ROOT, load_config, run_single_episode


DEFAULT_R_MIN_VALUES = [0.6, 0.9, 1.1, 1.4, 1.7, 2.0, 2.5]
DEFAULT_METHODS = ["periodic", "security_risk", "security_margin", "rollout_joint"]
DEFAULT_CONFIG = ROOT / "results" / "final_2026-05-12" / "scheme_c_holdout" / "configs" / "scenario_stress_holdoutfit.yaml"


def _case_key(row: pd.Series | dict) -> tuple[float, str, int]:
    return (round(float(row["r_min"]), 12), str(row["method"]), int(row["seed"]))


def _run_case(case: tuple[str, float, int, str]) -> dict:
    config_path, r_min, seed, method = case
    local_cfg = load_config(config_path)
    local_cfg = copy.deepcopy(local_cfg)
    local_cfg.setdefault("channel", {})
    local_cfg["channel"]["r_min"] = float(r_min)
    _, summary = run_single_episode(local_cfg, seed=seed, method=method)
    summary["r_min"] = float(r_min)
    summary["config_path"] = str(config_path)
    return summary


def _save_gain_plot(gains: pd.DataFrame, y_col: str, ylabel: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    has_series = False
    for method, group in gains.groupby("method"):
        if method == "periodic":
            continue
        group = group.sort_values("r_min")
        ax.plot(group["r_min"], group[y_col], marker="o", linewidth=1.6, label=str(method))
        has_series = True
    ax.axhline(0.0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel(r"$R_{\min}$")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    if has_series:
        ax.legend(frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def _add_periodic_gains(summary: pd.DataFrame) -> pd.DataFrame:
    periodic = summary[summary["method"] == "periodic"][
        ["r_min", "avg_secrecy_rate_mean", "outage_prob_mean"]
    ].rename(
        columns={
            "avg_secrecy_rate_mean": "periodic_avg_secrecy_rate_mean",
            "outage_prob_mean": "periodic_outage_prob_mean",
        }
    )
    gains = summary.merge(periodic, on="r_min", how="left")
    gains["secrecy_gain_vs_periodic"] = gains["avg_secrecy_rate_mean"] - gains["periodic_avg_secrecy_rate_mean"]
    gains["outage_gain_vs_periodic"] = gains["periodic_outage_prob_mean"] - gains["outage_prob_mean"]
    return gains


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sweep the stress-scenario secrecy outage threshold R_min."
    )
    parser.add_argument("--config", type=str, default=str(DEFAULT_CONFIG))
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(ROOT / "results" / "final_2026-05-12" / "rmin_sweep_stress"),
    )
    parser.add_argument("--r-min-values", nargs="+", type=float, default=DEFAULT_R_MIN_VALUES)
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    parser.add_argument("--num-seeds", type=int, default=5)
    parser.add_argument("--seed-start", type=int, default=62)
    parser.add_argument("--jobs", type=int, default=1, help="Number of worker processes.")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_runs_path = outdir / "all_runs.csv"
    rows: list[dict] = []
    completed: set[tuple[float, str, int]] = set()
    if all_runs_path.exists():
        existing = pd.read_csv(all_runs_path)
        if not existing.empty:
            rows = existing.to_dict("records")
            completed = {_case_key(row) for row in rows}
            print(f"[resume] loaded {len(rows)} completed rows from {all_runs_path}", flush=True)

    cases: list[tuple[str, float, int, str]] = []
    for r_min in args.r_min_values:
        for seed_offset in range(int(args.num_seeds)):
            seed = int(args.seed_start) + seed_offset
            for method in args.methods:
                key = (round(float(r_min), 12), str(method), int(seed))
                if key not in completed:
                    cases.append((str(args.config), float(r_min), int(seed), str(method)))

    print(f"[plan] pending cases: {len(cases)}", flush=True)
    if cases:
        if int(args.jobs) <= 1:
            for case in cases:
                summary = _run_case(case)
                rows.append(summary)
                pd.DataFrame(rows).sort_values(["r_min", "method", "seed"]).to_csv(all_runs_path, index=False)
                print(f"[done] r_min={case[1]} method={case[3]} seed={case[2]}", flush=True)
        else:
            with ProcessPoolExecutor(max_workers=int(args.jobs)) as executor:
                future_to_case = {executor.submit(_run_case, case): case for case in cases}
                for future in as_completed(future_to_case):
                    case = future_to_case[future]
                    summary = future.result()
                    rows.append(summary)
                    pd.DataFrame(rows).sort_values(["r_min", "method", "seed"]).to_csv(all_runs_path, index=False)
                    print(f"[done] r_min={case[1]} method={case[3]} seed={case[2]}", flush=True)

    all_runs = pd.DataFrame(rows).sort_values(["r_min", "method", "seed"])
    all_runs.to_csv(all_runs_path, index=False)

    summary = aggregate_runs_with_ci(all_runs, ["r_min", "method"])
    summary.to_csv(outdir / "summary.csv", index=False)

    gains = _add_periodic_gains(summary)
    gains.to_csv(outdir / "gains_vs_periodic.csv", index=False)

    _save_gain_plot(
        gains,
        y_col="secrecy_gain_vs_periodic",
        ylabel="Secrecy-rate gain vs periodic",
        out_path=outdir / "rmin_sweep_secrecy_gain.pdf",
    )
    _save_gain_plot(
        gains,
        y_col="outage_gain_vs_periodic",
        ylabel="Outage reduction vs periodic",
        out_path=outdir / "rmin_sweep_outage_gain.pdf",
    )

    print(f"Saved R_min sweep results to: {outdir}")


if __name__ == "__main__":
    main()
