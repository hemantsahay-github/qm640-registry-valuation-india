"""
plotstyle.py — One consistent, colour-blind-checked style for every figure.

Categorical order is fixed (never cycled): Pune = slot 1 (blue), Thane = slot 2
(orange). Correlations use a diverging blue / grey / red map with a neutral
midpoint. Figures carry a footer label stating the data source so a synthetic
validation figure can never be mistaken for a study finding.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]           # fixed categorical order
DISTRICT_COLOR = {"Pune": SERIES[0], "Thane": SERIES[1]}
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
DIVERGING = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#2a78d6"])
SEQUENTIAL = LinearSegmentedColormap.from_list("seq", ["#eaf2fc", "#2a78d6", "#0d3b73"])

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": INK_2, "axes.labelcolor": INK, "axes.titleweight": "bold",
    "axes.titlesize": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "xtick.color": INK_2, "ytick.color": INK_2, "legend.frameon": False,
    "lines.linewidth": 2,
})


def footer(fig, label: str) -> None:
    fig.text(0.01, -0.02, label, fontsize=7.5, color=INK_2, ha="left", va="top", style="italic")
