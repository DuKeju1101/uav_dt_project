from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from experiments.common import ROOT


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required result file: {path}")
    return pd.read_csv(path)


def _fmt(mean: float, ci: float, digits: int = 3) -> str:
    return f"{mean:.{digits}f} +/- {ci:.{digits}f}"


def _markdown_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join([header, sep] + rows) + "\n"


def _save_table(df: pd.DataFrame, out_csv: Path, out_md: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    out_md.write_text(_markdown_table(df), encoding="utf-8")


def export_baseline_tables(baseline_dir: Path, outdir: Path) -> None:
    df = _load_csv(baseline_dir / "summary_agg_methods.csv")
    ref_row = df[df["method"] == "periodic"]
    periodic_rs = float(ref_row["avg_secrecy_rate_mean"].iloc[0]) if not ref_row.empty else 0.0

    main = df.copy()
    main["secrecy_rate"] = main.apply(lambda r: _fmt(r["avg_secrecy_rate_mean"], r["avg_secrecy_rate_ci95"]), axis=1)
    main["outage_prob"] = main.apply(lambda r: _fmt(r["outage_prob_mean"], r["outage_prob_ci95"]), axis=1)
    main["sync_cost"] = main.apply(lambda r: _fmt(r["avg_sync_cost_mean"], r["avg_sync_cost_ci95"]), axis=1)
    main["cert_safe_rate"] = main.apply(lambda r: _fmt(r["certified_safe_rate_mean"], r["certified_safe_rate_ci95"]), axis=1)
    main["pred_violation"] = main.apply(lambda r: _fmt(r["prediction_violation_prob_mean"], r["prediction_violation_prob_ci95"]), axis=1)
    main["certificate_gap"] = main.apply(lambda r: _fmt(r["avg_cert_slack_mean"], r["avg_cert_slack_ci95"]), axis=1)
    main["delta_vs_periodic"] = main["avg_secrecy_rate_mean"] - periodic_rs
    main = main[
        [
            "method",
            "secrecy_rate",
            "delta_vs_periodic",
            "outage_prob",
            "sync_cost",
            "cert_safe_rate",
            "pred_violation",
            "certificate_gap",
        ]
    ].sort_values("delta_vs_periodic", ascending=False)
    _save_table(main, outdir / "baseline_main_table.csv", outdir / "baseline_main_table.md")

    ranking = df[
        [
            "method",
            "avg_secrecy_rate_mean",
            "outage_prob_mean",
            "avg_sync_cost_mean",
            "prediction_violation_prob_mean",
            "certified_safe_rate_mean",
        ]
    ].copy()
    ranking["rank_score"] = (
        ranking["avg_secrecy_rate_mean"]
        - 0.5 * ranking["outage_prob_mean"]
        - 0.2 * ranking["avg_sync_cost_mean"]
        - 0.2 * ranking["prediction_violation_prob_mean"]
        + 0.1 * ranking["certified_safe_rate_mean"]
    )
    ranking = ranking.sort_values("rank_score", ascending=False)
    _save_table(ranking, outdir / "baseline_ranking_table.csv", outdir / "baseline_ranking_table.md")


def export_threshold_tables(threshold_dir: Path, outdir: Path) -> None:
    df = _load_csv(threshold_dir / "threshold_summary_agg.csv")
    best_rows = []
    for method, group in df.groupby("method"):
        best = group.sort_values(
            ["avg_secrecy_rate_mean", "certified_safe_rate_mean", "outage_prob_mean", "avg_sync_cost_mean"],
            ascending=[False, False, True, True],
        ).iloc[0]
        best_rows.append(
            {
                "method": method,
                "best_scan_value": best["scan_value"],
                "secrecy_rate": _fmt(best["avg_secrecy_rate_mean"], best["avg_secrecy_rate_ci95"]),
                "outage_prob": _fmt(best["outage_prob_mean"], best["outage_prob_ci95"]),
                "sync_cost": _fmt(best["avg_sync_cost_mean"], best["avg_sync_cost_ci95"]),
                "cert_safe_rate": _fmt(best["certified_safe_rate_mean"], best["certified_safe_rate_ci95"]),
                "certificate_gap": _fmt(best["avg_cert_slack_mean"], best["avg_cert_slack_ci95"]),
            }
        )
    best_df = pd.DataFrame(best_rows).sort_values("method")
    _save_table(best_df, outdir / "threshold_best_table.csv", outdir / "threshold_best_table.md")


def export_coupling_tables(coupling_dir: Path, outdir: Path, focus_budget: int, focus_eve_speed: float) -> None:
    df = _load_csv(coupling_dir / "coupling_summary_agg.csv")

    delay_summary = (
        df.groupby("sync_delay")[
            [
                "avg_secrecy_rate_mean",
                "avg_sync_cost_mean",
                "outage_prob_mean",
                "certified_safe_rate_mean",
                "prediction_violation_prob_mean",
            ]
        ]
        .mean()
        .reset_index()
        .sort_values("sync_delay")
    )
    _save_table(delay_summary, outdir / "coupling_delay_summary.csv", outdir / "coupling_delay_summary.md")

    focus = df[(df["budget"] == focus_budget) & (df["eve_speed"] == focus_eve_speed)].copy()
    if not focus.empty:
        focus = focus.sort_values(["sync_delay", "periodic_k"])
        focus["secrecy_rate"] = focus.apply(lambda r: _fmt(r["avg_secrecy_rate_mean"], r["avg_secrecy_rate_ci95"]), axis=1)
        focus["outage_prob"] = focus.apply(lambda r: _fmt(r["outage_prob_mean"], r["outage_prob_ci95"]), axis=1)
        focus["sync_cost"] = focus.apply(lambda r: _fmt(r["avg_sync_cost_mean"], r["avg_sync_cost_ci95"]), axis=1)
        focus["cert_safe_rate"] = focus.apply(lambda r: _fmt(r["certified_safe_rate_mean"], r["certified_safe_rate_ci95"]), axis=1)
        focus = focus[
            [
                "periodic_k",
                "sync_delay",
                "secrecy_rate",
                "outage_prob",
                "sync_cost",
                "cert_safe_rate",
                "prediction_violation_prob_mean",
            ]
        ]
        _save_table(focus, outdir / "coupling_focus_table.csv", outdir / "coupling_focus_table.md")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=str, default=str(ROOT / "results" / "baselines"))
    parser.add_argument("--threshold-dir", type=str, default=str(ROOT / "results" / "threshold"))
    parser.add_argument("--coupling-dir", type=str, default=str(ROOT / "results" / "coupling"))
    parser.add_argument("--outdir", type=str, default=str(ROOT / "results" / "paper_tables"))
    parser.add_argument("--focus-budget", type=int, default=20)
    parser.add_argument("--focus-eve-speed", type=float, default=4.0)
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    export_baseline_tables(Path(args.baseline_dir), outdir)
    export_threshold_tables(Path(args.threshold_dir), outdir)
    export_coupling_tables(Path(args.coupling_dir), outdir, args.focus_budget, args.focus_eve_speed)
    print(f"Saved paper tables to: {outdir}")


if __name__ == "__main__":
    main()
