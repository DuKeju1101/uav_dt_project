from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_line(df: pd.DataFrame, x: str, y: str, hue: str, title: str, out_path: Path) -> None:
    fig = plt.figure(figsize=(7, 4.5))
    ax = fig.add_subplot(111)
    for key, g in df.groupby(hue):
        g = g.sort_values(x)
        ax.plot(g[x], g[y], marker="o", label=str(key))
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.grid(True, alpha=0.3)
    ax.legend()
    _save(fig, out_path)


def plot_scatter(df: pd.DataFrame, x: str, y: str, hue: str, title: str, out_path: Path) -> None:
    fig = plt.figure(figsize=(7, 4.5))
    ax = fig.add_subplot(111)
    for key, g in df.groupby(hue):
        ax.scatter(g[x], g[y], label=str(key), alpha=0.75)
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.grid(True, alpha=0.3)
    ax.legend()
    _save(fig, out_path)


def plot_pareto(df: pd.DataFrame, x: str, y: str, hue: str, title: str, out_path: Path) -> None:
    fig = plt.figure(figsize=(7, 4.5))
    ax = fig.add_subplot(111)
    for key, g in df.groupby(hue):
        ax.scatter(g[x], g[y], label=str(key), alpha=0.75)
    pareto_df = df.sort_values(x)
    best_y = -1e18
    px, py = [], []
    for _, row in pareto_df.iterrows():
        if row[y] > best_y:
            best_y = row[y]
            px.append(row[x])
            py.append(row[y])
    if px:
        ax.plot(px, py, marker="o")
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.grid(True, alpha=0.3)
    ax.legend()
    _save(fig, out_path)
