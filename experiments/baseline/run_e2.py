"""E2 — PSO inertia weight duyarlılığı (makale Tablo 10'un yeniden gerçekleştirilmesi).

Yöntem P (AFL + PSO-GA); w ∈ {0.3, 0.5, 0.7, 0.9}; 3 veri seti × 30 tohum; N ∈ {20, 50}.
w yalnızca yönlendirmeyi etkilediği için ağ metriklerinin yanında doğrudan optimizasyon
kalitesi de raporlanır: bulunan rotaların ortalama uygunluk değeri (f, düşük iyi).

Çıktılar:
    results/tables/e2_raw.csv, e2_summary.csv, e2_tests.csv
    results/figures/e2_inertia.png

Çalıştırma (repo kökünden):  python experiments/baseline/run_e2.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from afl_wsn.experiment import METRICS, make_tasks, run_many, summarize  # noqa: E402
from afl_wsn.plotting import METRIC_LABELS, METRIC_SCALE, SERIES, TEXT_2, apply_style, plt  # noqa: E402
from scipy import stats  # noqa: E402

TAB, FIG = ROOT / "results" / "tables", ROOT / "results" / "figures"
DATASETS = ["data1", "data2", "data3"]
SEEDS = range(30)
NODES = [20, 50]
W_VALUES = [0.3, 0.5, 0.7, 0.9]
ALL = METRICS + ["route_fitness_mean", "fitness_evals_per_epoch", "route_ms_per_epoch"]


def main() -> None:
    t0 = time.perf_counter()
    tasks = []
    for n in NODES:
        for w in W_VALUES:
            tasks += make_tasks(["P"], DATASETS, SEEDS, overrides={"n_nodes": n, "pso__w": w},
                                tag={"n_nodes": n, "w": w})
    df = pd.DataFrame(run_many(tasks))
    print(f"{len(df)} koşu, {time.perf_counter() - t0:.1f} s")
    df.to_csv(TAB / "e2_raw.csv", index=False)

    # Makale Tablo 10'da veri seti belirtilmediği için üç veri setinin tohum ortalaması alınır.
    summ = summarize(df, ["n_nodes", "w"], ALL)
    summ.to_csv(TAB / "e2_summary.csv", index=False)

    # Friedman testi: w'nin etkisi var mı? (bloklar: veri seti × tohum)
    rows = []
    for n in NODES:
        sub = df[df["n_nodes"] == n]
        for m in METRICS + ["route_fitness_mean"]:
            piv = sub.pivot_table(index=["dataset", "seed"], columns="w", values=m).dropna()
            res = stats.friedmanchisquare(*[piv[w] for w in W_VALUES])
            best = piv.mean().idxmin() if m in ("delay_ms", "route_fitness_mean") else piv.mean().idxmax()
            rows.append({"n_nodes": n, "metric": m, "friedman_chi2": res.statistic, "p": res.pvalue,
                         "best_w": best})
    tests = pd.DataFrame(rows)
    tests.to_csv(TAB / "e2_tests.csv", index=False)

    plot(summ)
    pd.set_option("display.width", 200)
    cols = ["n_nodes", "w"] + [f"{m}_mean" for m in ALL]
    print(summ[cols].round(4).to_string(index=False))
    print(tests.round(4).to_string(index=False))


def plot(summ: pd.DataFrame) -> None:
    apply_style()
    metrics = ["pdr", "delay_ms", "ee_bit_per_j", "route_fitness_mean"]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.4))
    for ax, m in zip(axes, metrics):
        sc = METRIC_SCALE.get(m, 1.0)
        for color, n in zip(SERIES, NODES):
            s = summ[summ["n_nodes"] == n].sort_values("w")
            y, ci = s[f"{m}_mean"] * sc, s[f"{m}_ci95"] * sc
            ax.plot(s["w"], y, "-o", color=color, ms=6, label=f"N = {n}")
            ax.fill_between(s["w"], y - ci, y + ci, color=color, alpha=0.15, linewidth=0)
        ax.set_xticks(W_VALUES)
        ax.set_xlabel("Inertia weight w")
        ax.set_ylabel(METRIC_LABELS[m])
        ax.axvline(0.7, color=TEXT_2, lw=0.8, ls=":")
    axes[0].legend(loc="best")
    fig.suptitle("E2 — PSO inertia weight duyarlılığı (yöntem P; 3 veri seti × 30 tohum; bant: %95 GA; "
                 "noktalı çizgi: makalenin seçtiği w = 0.7)", fontsize=10.5)
    fig.tight_layout()
    fig.savefig(FIG / "e2_inertia.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
