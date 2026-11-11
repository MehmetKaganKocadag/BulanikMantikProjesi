"""Grafik stili ve ortak çizim yardımcıları.

Renkler: dataviz referans paletinin ilk dört kategorik slotu (açık tema), sabit
sırayla ve her zaman aynı yönteme atanır (renk sırayı değil, yöntemi izler).
Açık zeminde 3:1 kontrastın altında kalan slotlar (aqua, sarı) için çubuk
üstü değer etiketleri gösterilir.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

METHOD_ORDER = ["P", "B2", "B1", "B0"]
METHOD_COLORS = {"P": "#2a78d6", "B2": "#eb6834", "B1": "#1baf7a", "B0": "#eda100"}
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3de"

METRIC_LABELS = {
    "pdr": "PDR",
    "delay_ms": "Ortalama gecikme (ms)",
    "throughput_bps": "Throughput (kbps)",
    "ee_bit_per_j": "Enerji verimliliği (Mbit/J)",
    "route_fitness_mean": "Rota uygunluğu f (düşük iyi)",
}
METRIC_SCALE = {"throughput_bps": 1e-3, "ee_bit_per_j": 1e-6}
DATASET_LABELS = {"data1": "data1\nHealthcare IoT", "data2": "data2\nHealth Monitoring",
                  "data3": "data3\nTemp & Pulse"}


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT_2,
        "axes.titlecolor": TEXT,
        "axes.titlesize": 11,
        "axes.labelsize": 9.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "font.size": 9.5,
        "lines.linewidth": 2.0,
    })


def grouped_bars(ax, summary, metric, groups, group_col, methods, labels=None, fmt="{:.2f}"):
    """summary: run_many → summarize çıktısı. Hata çubukları %95 GA."""
    scale = METRIC_SCALE.get(metric, 1.0)
    width = 0.8 / len(methods)
    x = np.arange(len(groups))
    for j, m in enumerate(methods):
        rows = [summary[(summary[group_col] == gv) & (summary["method"] == m)].iloc[0] for gv in groups]
        mean = np.array([r[f"{metric}_mean"] for r in rows]) * scale
        ci = np.array([r[f"{metric}_ci95"] for r in rows]) * scale
        xs = x - 0.4 + width * (j + 0.5)
        ax.bar(xs, mean, width, color=METHOD_COLORS[m], edgecolor=SURFACE, linewidth=2,
               label=(labels or {}).get(m, m), zorder=2)
        ax.errorbar(xs, mean, yerr=ci, fmt="none", ecolor=TEXT_2, elinewidth=1, capsize=2, zorder=3)
        for xi, mi, ci_i in zip(xs, mean, ci):
            ax.text(xi, mi + ci_i, fmt.format(mi), ha="center", va="bottom", fontsize=6.5, color=TEXT_2)
    ax.set_xticks(x, [DATASET_LABELS.get(g, str(g)) for g in groups])
    ax.set_ylabel(METRIC_LABELS.get(metric, metric))
    ax.set_axisbelow(True)
