from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _save_markdown(df: pd.DataFrame, path: Path) -> None:
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(str(row[c]) for c in cols) + " |" for _, row in df.iterrows()]
    path.write_text("\n".join([header, sep] + rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=str, required=True)
    parser.add_argument("--outdir", type=str, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.summary)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    main = df[
        [
            "scenario",
            "method",
            "avg_secrecy_rate_mean",
            "outage_prob_mean",
            "avg_sync_cost_mean",
            "certificate_cover_rate_mean",
            "certified_safe_rate_mean",
            "avg_cert_slack_mean",
            "runtime_sec_mean",
            "runtime_per_slot_ms_mean",
        ]
    ].sort_values(["scenario", "avg_secrecy_rate_mean"], ascending=[True, False])
    main.to_csv(outdir / "publication_main_table.csv", index=False)
    _save_markdown(main, outdir / "publication_main_table.md")

    pivot = df.pivot(index="method", columns="scenario", values="avg_secrecy_rate_mean").reset_index()
    pivot.to_csv(outdir / "publication_secrecy_pivot.csv", index=False)
    _save_markdown(pivot, outdir / "publication_secrecy_pivot.md")

    runtime = df[
        [
            "scenario",
            "method",
            "runtime_sec_mean",
            "runtime_per_slot_ms_mean",
        ]
    ].sort_values(["scenario", "runtime_sec_mean"], ascending=[True, True])
    runtime.to_csv(outdir / "publication_runtime_table.csv", index=False)
    _save_markdown(runtime, outdir / "publication_runtime_table.md")

    print(f"Saved publication tables to: {outdir}")


if __name__ == "__main__":
    main()
