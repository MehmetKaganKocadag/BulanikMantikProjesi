"""E6 — "5 ve 20 SN" yorumlarının testi (CP1 T8, T20–T24; CP3 §11).

Yorum A (E1 N=20 ve E3 N=5): 5/20 fiziksel sensör sayısıdır. Bu deneyde yeniden koşulmaz.
Yorum B (bu deney): 5/20 küme başı (CH) sayısıdır. 100 sensör, K ∈ {5, 20} sabit CH.
İki yerleşim:
    uniform — 100×100 m'ye düzgün rastgele (Tablo 3)
    data    — her düğüm bir veri kaydıdır; iki sütunu alana ölçeklenip konum olur
              (makale şekillerinin olası üretimi; yaş sütunu olmadığından data1'de
              kalp hızı – sistolik tansiyon, data2'de sıcaklık – ECG, data3'te sıcaklık – nabız)
Yöntemler: P, B2, B1 (LEACH p = K/N), B0, KM (k-means + PSO-GA).

Çıktılar:
    results/tables/e6_raw.csv, e6_summary.csv, e6_summary_pooled.csv, e6_tests.csv
    results/figures/e6_metrics.png, e6_placement_example.png
Çalıştırma (repo kökünden):  python experiments/baseline/run_e6.py
Yalnız analiz (koşuları tekrarlamadan, e6_raw.csv'den):  python experiments/baseline/run_e6.py --analyze
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from afl_wsn.clustering import FuzzyClustering, KMeansClustering, form_clusters  # noqa: E402
from afl_wsn.config import SimConfig  # noqa: E402
from afl_wsn.experiment import METRICS, make_tasks, paired_tests, run_many, summarize  # noqa: E402
from afl_wsn.plotting import (  # noqa: E402
    DATASET_LABELS, GRID, METHOD_COLORS, METRIC_LABELS, METRIC_SCALE, SURFACE, TEXT, TEXT_2, apply_style, plt,
)
from afl_wsn.simulator import data_topology  # noqa: E402
from afl_wsn.traffic import DATASETS as DS_SPEC  # noqa: E402

TAB, FIG = ROOT / "results" / "tables", ROOT / "results" / "figures"
DATASETS = ["data1", "data2", "data3"]
SEEDS = range(30)
N = 100
KS = [5, 20]
PLACEMENTS = ["uniform", "data"]
METHODS = ["P", "B2", "B1", "B0", "KM"]
COLORS = {**METHOD_COLORS, "KM": "#e87ba4"}  # referans paletin 5. slotu
LABELS = {"P": "P (AFL + PSO-GA)", "B2": "B2 (statik bulanık + PSO-GA)", "B1": "B1 (LEACH + PSO-GA)",
          "B0": "B0 (LEACH + doğrudan)", "KM": "KM (k-means + PSO-GA)"}
PLACEMENT_LABELS = {"uniform": "Rastgele yerleşim", "data": "Veriden yerleşim"}
EXTRA = ["energy_j", "n_ch_mean", "route_hops_mean", "disconnected_ch_frac", "member_dist_mean",
         "member_out_of_range_frac"]


def overrides(placement: str, k: int) -> dict:
    return {"n_nodes": N, "n_ch": k, "leach_p": k / N, "placement": placement}


def metrics_figure(summ: pd.DataFrame) -> None:
    """Veri seti başına paneller (data2'de veriden yerleşim ağı tamamen böldüğü için havuzlanmaz).
    Değer etiketleri yerine tam tablolar CP3 §11'de verilir."""
    configs = [(p, k) for p in PLACEMENTS for k in KS]
    fig, axes = plt.subplots(2, len(DATASETS), figsize=(13, 6.6), sharey="row")
    width = 0.8 / len(METHODS)
    x = np.arange(len(configs))
    for r, metric in enumerate(["pdr", "ee_bit_per_j"]):
        scale = METRIC_SCALE.get(metric, 1.0)
        for c, ds in enumerate(DATASETS):
            ax = axes[r, c]
            for j, m in enumerate(METHODS):
                rows = [summ[(summ.placement == p) & (summ.n_ch == k) & (summ.dataset == ds) & (summ.method == m)]
                        .iloc[0] for p, k in configs]
                mean = np.array([row[f"{metric}_mean"] for row in rows]) * scale
                ci = np.nan_to_num(np.array([row[f"{metric}_ci95"] for row in rows]) * scale)
                xs = x - 0.4 + width * (j + 0.5)
                ax.bar(xs, mean, width, color=COLORS[m], edgecolor=SURFACE, linewidth=1.5, label=LABELS[m],
                       zorder=2)
                ax.errorbar(xs, mean, yerr=ci, fmt="none", ecolor=TEXT_2, elinewidth=0.8, capsize=1.5, zorder=3)
            if ds == "data2":
                for xi in x[2:]:
                    ax.text(xi, 0.02 * ax.get_ylim()[1] + 0.02, "ağ\nbağlantısız", ha="center", va="bottom",
                            fontsize=7, color=TEXT_2)
            ax.set_xticks(x, [f"{'Rastgele' if p == 'uniform' else 'Veriden'}\nK = {k}" for p, k in configs])
            ax.set_axisbelow(True)
            if r == 0:
                ax.set_title(DATASET_LABELS[ds].replace("\n", " — "))
            if c == 0:
                ax.set_ylabel(METRIC_LABELS[metric])
    axes[0, 0].set_ylim(0, 1.0)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout()
    fig.savefig(FIG / "e6_metrics.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def placement_figure(seed: int = 0) -> None:
    """Makale Şekil 3–5'in karşılığı: veriden yerleşimde P'nin CH'leri ve k-means merkezleri."""
    fig, axes = plt.subplots(len(KS), len(DATASETS), figsize=(11, 7.2))
    for c, ds in enumerate(DATASETS):
        xcol, ycol = DS_SPEC[ds]["placement"]
        for r, k in enumerate(KS):
            ax = axes[r, c]
            cfg = SimConfig().with_(**overrides("data", k))
            topo, _ = data_topology(cfg, ds, seed)
            alive, energy = np.ones(N, dtype=bool), np.full(N, cfg.e_init)
            ch = FuzzyClustering(cfg).select(energy, np.ones(N), alive, topo, None, 0)
            parent, ch = form_clusters(ch, alive, topo, cfg)
            km = KMeansClustering(cfg)
            km.select(energy, np.ones(N), alive, topo, np.random.default_rng([seed, 2]), 0)
            pos = topo.pos
            for i in np.flatnonzero(~ch):
                ax.plot(*pos[[i, parent[i]]].T, color=GRID, lw=0.8, zorder=1)
            ax.scatter(*pos[~ch].T, s=10, color=TEXT_2, alpha=0.6, lw=0, zorder=2, label="Sensör (veri kaydı)")
            ax.scatter(*pos[ch].T, s=70, color=COLORS["P"], edgecolor=SURFACE, lw=1.5, zorder=4,
                       label="P'nin CH'si (bir düğüm)")
            ax.scatter(*km.centroids.T, s=55, marker="x", color=COLORS["KM"], lw=2, zorder=5,
                       label="k-means merkezi")
            ax.scatter(*cfg.bs, s=60, marker="s", color=TEXT, zorder=6, label="BS")
            uniq = len(np.unique(pos.round(6), axis=0))
            ax.set_title(f"{ds}, K = {k}   ({uniq} farklı konum)", fontsize=9.5)
            ax.set_xlim(-4, 104)
            ax.set_ylim(-4, 104)
            ax.set_aspect("equal")
            ax.grid(False)
            short = lambda s: s.split(" (")[0]  # noqa: E731
            ax.set_xlabel(f"{short(xcol)} → x (m)", fontsize=8)
            ax.set_ylabel(f"{short(ycol)} → y (m)", fontsize=8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.01))
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "e6_placement_example.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    if "--analyze" in sys.argv:
        df = pd.read_csv(TAB / "e6_raw.csv")
    else:
        t0 = time.perf_counter()
        tasks = []
        for p in PLACEMENTS:
            for k in KS:
                tasks += make_tasks(METHODS, DATASETS, SEEDS, overrides=overrides(p, k),
                                    tag={"placement": p, "n_ch": k})
        df = pd.DataFrame(run_many(tasks))
        print(f"{len(df)} koşu, {time.perf_counter() - t0:.1f} s")
        df.to_csv(TAB / "e6_raw.csv", index=False)

    summ = summarize(df, ["placement", "n_ch", "dataset", "method"], METRICS + EXTRA)
    summ.to_csv(TAB / "e6_summary.csv", index=False)
    pooled = summarize(df, ["placement", "n_ch", "method"], METRICS + EXTRA)
    pooled.to_csv(TAB / "e6_summary_pooled.csv", index=False)
    tests = paired_tests(df, "P", ["B2", "B1", "B0", "KM"], ["placement", "n_ch", "dataset"])
    tests.to_csv(TAB / "e6_tests.csv", index=False)

    apply_style()
    metrics_figure(summ)
    placement_figure()

    pd.set_option("display.width", 220)
    cols = ["placement", "n_ch", "method"] + [f"{m}_mean" for m in METRICS + EXTRA[1:]]
    print(pooled[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
