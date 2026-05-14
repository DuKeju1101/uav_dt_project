from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "final_2026-05-12"
FIGURES = ROOT / "paper" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)


plt.rcParams.update(
    {
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


COLORS = {
    "rollout_joint": "#0072B2",
    "periodic": "#D55E00",
    "security_risk": "#009E73",
    "security_margin": "#CC79A7",
    "oracle_sync": "#000000",
    "rollout_fixed_periodic": "#56B4E9",
    "no_twin": "#E69F00",
    "rollout_no_sync": "#F0E442",
    "sca_twin": "#8A8A8A",
    "sca_oracle": "#9467BD",
    "ppo_baseline": "#A65628",
}


def method_label(name: str) -> str:
    return {
        "rollout_joint": "Joint rollout",
        "periodic": "Periodic",
        "security_risk": "Risk rule",
        "security_margin": "Margin rule",
        "oracle_sync": "Oracle rollout",
        "rollout_fixed_periodic": "Fixed-sync rollout",
        "no_twin": "No twin",
        "rollout_no_sync": "No sync rollout",
        "sca_twin": "SCA twin",
        "sca_oracle": "SCA oracle",
        "ppo_baseline": "PPO",
    }.get(name, name.replace("_", " "))


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIGURES / name, bbox_inches="tight")
    plt.close()


def plot_main_results() -> None:
    df = pd.read_csv(RESULTS / "scheme_c_readiness_20seed" / "main_table.csv")
    scenarios = ["paper_base_holdoutfit", "paper_hard_holdoutfit", "scenario_stress_holdoutfit"]
    scenario_labels = ["Base", "Hard", "Stress"]
    methods = ["rollout_joint", "periodic", "security_risk", "security_margin"]
    width = 0.18
    x = np.arange(len(scenarios))

    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8), sharex=True)
    for idx, method in enumerate(methods):
        part = df[df["method"] == method].set_index("scenario").loc[scenarios]
        offset = (idx - 1.5) * width
        axes[0].bar(
            x + offset,
            part["avg_secrecy_rate_mean"],
            width,
            yerr=part["avg_secrecy_rate_ci95"],
            capsize=2,
            label=method_label(method),
            color=COLORS[method],
            edgecolor="black",
            linewidth=0.3,
        )
        axes[1].bar(
            x + offset,
            part["outage_prob_mean"],
            width,
            yerr=part["outage_prob_ci95"],
            capsize=2,
            color=COLORS[method],
            edgecolor="black",
            linewidth=0.3,
        )

    axes[0].set_ylabel("Average secrecy rate")
    axes[1].set_ylabel("Secrecy outage probability")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(scenario_labels)
        ax.grid(axis="y", alpha=0.25)
    axes[0].legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(1.06, 1.25))
    savefig("main_results_secrecy_outage.pdf")


def plot_stress_strengthening() -> None:
    df = pd.read_csv(RESULTS / "strengthening_suite_3seed_stress_holdoutfit" / "main_table.csv")
    methods = [
        "oracle_sync",
        "rollout_joint",
        "rollout_fixed_periodic",
        "periodic",
        "no_twin",
        "rollout_no_sync",
        "sca_twin",
        "random_budgeted",
    ]
    part = df[df["method"].isin(methods)].set_index("method").loc[methods].reset_index()
    labels = [method_label(m) for m in part["method"]]
    y = np.arange(len(part))

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.2), sharey=True)
    metrics = [
        ("avg_secrecy_rate_mean", "Average secrecy rate"),
        ("outage_prob_mean", "Outage probability"),
        ("runtime_per_slot_ms_mean", "Runtime ms/slot"),
    ]
    for ax, (col, title) in zip(axes, metrics):
        vals = part[col]
        colors = [COLORS.get(m, "#BBBBBB") for m in part["method"]]
        ax.barh(y, vals, color=colors, edgecolor="black", linewidth=0.3)
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.25)
        ax.invert_yaxis()
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(labels)
    axes[1].tick_params(axis="y", labelleft=False)
    axes[2].tick_params(axis="y", labelleft=False)
    savefig("stress_strengthening_suite.pdf")


def plot_certificate_validation() -> None:
    df = pd.read_csv(RESULTS / "scheme_c_holdout" / "holdout_summary.csv")
    part = df[df["split"].eq("validation")].copy()
    order = ["paper_base", "paper_hard", "scenario_stress", "all"]
    part = part.set_index("scenario").loc[order].reset_index()
    labels = ["Base", "Hard", "Stress", "All"]
    x = np.arange(len(part))

    fig, ax1 = plt.subplots(figsize=(5.0, 2.8))
    ax1.bar(x - 0.18, part["cover_rate"], 0.36, color="#0072B2", edgecolor="black", linewidth=0.3, label="Cover rate")
    ax1.axhline(0.95, color="#D55E00", linestyle="--", linewidth=1.0, label="Target 0.95")
    ax1.set_ylim(0.90, 1.01)
    ax1.set_ylabel("Certificate cover rate")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.grid(axis="y", alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(x + 0.18, part["avg_realized_loss"], color="#009E73", marker="o", linewidth=1.5, label="Avg. realized loss")
    ax2.set_ylabel("Average realized loss")
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3)
    savefig("certificate_validation.pdf")


def plot_ppo_training() -> None:
    df = pd.read_csv(RESULTS / "drl_ppo_200ep_5seed_stress_holdoutfit" / "training_log.csv")
    df = df.sort_values("train_episode")
    roll = df["avg_secrecy_rate"].rolling(window=10, min_periods=1).mean()

    plt.figure(figsize=(5.2, 2.7))
    plt.plot(df["train_episode"], df["avg_secrecy_rate"], color="#BBBBBB", linewidth=0.8, label="Episode")
    plt.plot(df["train_episode"], roll, color="#0072B2", linewidth=1.8, label="10-episode mean")
    plt.xlabel("Training episode")
    plt.ylabel("Average secrecy rate")
    plt.grid(alpha=0.25)
    plt.legend(frameon=False)
    savefig("ppo_training_curve.pdf")


def plot_small_mdp_trace() -> None:
    df = pd.read_csv(RESULTS / "small_mdp_bound" / "optimal_trace.csv")

    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.8))
    axes[0].plot(df["uav1_x"], df["uav1_y"], marker="o", color="#0072B2", label="UAV 1")
    axes[0].plot(df["uav2_x"], df["uav2_y"], marker="s", color="#D55E00", label="UAV 2")
    axes[0].plot(df["eve_true_x"], df["eve_true_y"], marker="^", color="#000000", label="Eve")
    axes[0].set_xlabel("x position")
    axes[0].set_ylabel("y position")
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False, loc="best")

    axes[1].plot(df["slot"], df["true_r_sec"], marker="o", color="#0072B2", label="True secrecy")
    axes[1].plot(df["slot"], df["pred_r_sec"], marker="s", color="#009E73", label="Predicted secrecy")
    axes[1].set_xlabel("Slot")
    axes[1].set_ylabel("Secrecy rate")
    axes[1].grid(alpha=0.25)
    axes[1].legend(frameon=False, loc="best")
    savefig("small_mdp_trace.pdf")


def plot_framework() -> None:
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    ax.axis("off")

    boxes = {
        "Physical UAV system": (0.04, 0.58, 0.22, 0.22),
        "Digital twin state": (0.39, 0.58, 0.22, 0.22),
        "Certificate risk estimator": (0.39, 0.18, 0.22, 0.22),
        "Joint rollout controller": (0.73, 0.38, 0.23, 0.24),
        "Actions: sync, motion, power, jamming": (0.04, 0.18, 0.25, 0.22),
    }
    for text, (x, y, w, h) in boxes.items():
        ax.add_patch(
            plt.Rectangle((x, y), w, h, facecolor="#F2F2F2", edgecolor="black", linewidth=0.8)
        )
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", wrap=True)

    def arrow(start, end, label=None, dy=0.0):
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", linewidth=1.0))
        if label:
            ax.text((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + dy, label, ha="center", va="center", fontsize=8)

    arrow((0.26, 0.69), (0.39, 0.69), "sensing/sync")
    arrow((0.50, 0.58), (0.50, 0.40), "age, uncertainty", dy=0.02)
    arrow((0.61, 0.69), (0.73, 0.52), "twin features")
    arrow((0.61, 0.29), (0.73, 0.43), "risk slack")
    arrow((0.73, 0.42), (0.29, 0.29), "selected action", dy=-0.03)
    arrow((0.16, 0.40), (0.16, 0.58), "execution")
    arrow((0.29, 0.20), (0.73, 0.38), "candidate set", dy=-0.03)
    ax.text(0.5, 0.93, "Digital-twin-aware secure UAV control loop", ha="center", fontsize=11, fontweight="bold")
    savefig("framework_control_loop.pdf")


if __name__ == "__main__":
    plot_framework()
    plot_main_results()
    plot_certificate_validation()
    plot_stress_strengthening()
    plot_ppo_training()
    plot_small_mdp_trace()
