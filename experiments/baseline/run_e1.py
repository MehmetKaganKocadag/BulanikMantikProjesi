"""E1 — Ana karşılaştırma (makale Tablo 4–6'nın yeniden gerçekleştirilmesi).

Yöntemler: P (AFL + PSO-GA), B2 (statik bulanık + PSO-GA), B1 (LEACH + PSO-GA),
B0 (LEACH + doğrudan). 3 veri seti × 30 tohum × N ∈ {20 (makale), 50 (yoğun)}.

Çıktılar:
    results/tables/e1_raw.csv, e1_summary.csv, e1_tests.csv, e1_pdr_per_round.csv
    results/figures/e1_metrics_N20.png, e1_metrics_N50.png, e1_pdr_per_round.png

Çalıştırma (repo kökünden):  python experiments/baseline/run_e1.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from afl_wsn.experiment import METHODS, METRICS, make_tasks, paired_tests, run_many, summarize  # noqa: E402
from afl_wsn.plotting import (  # noqa: E402
    METHOD_COLORS, METHOD_ORDER, SERIES, TEXT_2, apply_style, grouped_bars, plt,
)

TAB, FIG = ROOT / "results" / "tables", ROOT / "results" / "figures"
DATASETS = ["data1", "data2", "data3"]
SEEDS = range(30)
NODES = [20, 50]


def main() -> None:
    t0 = time.perf_counter()
    tasks = []
    for n in NODES:
        tasks += make_tasks(METHOD_ORDER, DATASETS, SEEDS, overrides={"n_nodes": n}, tag={"n_nodes": n},
                            keep_rounds=(n == 20))
    rows = run_many(tasks)
    print(f"{len(rows)} koşu, {time.perf_counter() - t0:.1f} s")

    per_round = [(r["method"], r["dataset"], r.pop("_per_round")) for r in rows if "_per_round" in r]
    df = pd.DataFrame(rows)
    TAB.mkdir(parents=True, exist_ok=True)
    df.to_csv(TAB / "e1_raw.csv", index=False)

    extra = ["energy_j", "n_ch_mean", "route_hops_mean", "disconnected_ch_frac", "route_ms_per_epoch",
             "fitness_evals_per_epoch"]
    summ = summarize(df, ["n_nodes", "dataset", "method"], METRICS + extra)
    summ.to_csv(TAB / "e1_summary.csv", index=False)
    tests = paired_tests(df, "P", ["B2", "B1", "B0"], ["n_nodes", "dataset"])
    tests.to_csv(TAB / "e1_tests.csv", index=False)

    # Tur bazında PDR (makale Şekil 12–14 karşılığı), N=20
    pr_rows = []
    for m, d, pr in per_round:
        with np.errstate(invalid="ignore", divide="ignore"):
            pdr = pr["delivered"] / pr["generated"]
        for t, v in enumerate(pdr):
            pr_rows.append({"method": m, "dataset": d, "round": t + 1, "pdr": v})
    prdf = pd.DataFrame(pr_rows).groupby(["method", "dataset", "round"], as_index=False)["pdr"].mean()
    prdf.to_csv(TAB / "e1_pdr_per_round.csv", index=False)

    plot(summ, prdf)
    print_tables(summ, tests)


def plot(summ: pd.DataFrame, prdf: pd.DataFrame) -> None:
    apply_style()
    FIG.mkdir(parents=True, exist_ok=True)
    labels = {m: f"{m} — {METHODS[m]['label']}" for m in METHOD_ORDER}
    fmts = {"pdr": "{:.2f}", "delay_ms": "{:.0f}", "throughput_bps": "{:.0f}", "ee_bit_per_j": "{:.2f}"}
    for n in NODES:
        s = summ[summ["n_nodes"] == n]
        fig, axes = plt.subplots(2, 2, figsize=(11, 7.2))
        for ax, metric in zip(axes.ravel(), METRICS):
            grouped_bars(ax, s, metric, DATASETS, "dataset", METHOD_ORDER, labels, fmt=fmts[metric])
        handles, lab = axes[0, 0].get_legend_handles_labels()
        fig.legend(handles, lab, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.0))
        fig.suptitle(f"E1 — Yöntem karşılaştırması, N = {n} düğüm (30 tohum, ort. ± %95 GA)",
                     y=0.955, fontsize=11.5)
        fig.tight_layout(rect=(0, 0, 1, 0.92))
        fig.savefig(FIG / f"e1_metrics_N{n}.png", dpi=160)
        plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4), sharey=True)
    for ax, d in zip(axes, DATASETS):
        for m in ["P", "B0"]:
            g = prdf[(prdf["method"] == m) & (prdf["dataset"] == d)]
            ax.plot(g["round"], g["pdr"], color=METHOD_COLORS[m], label=labels[m])
        ax.set_title(d, fontsize=10)
        ax.set_xlabel("Tur")
    axes[0].set_ylabel("PDR (30 tohum ortalaması)")
    axes[0].set_ylim(0, 0.8)
    handles, lab = axes[0].get_legend_handles_labels()
    fig.legend(handles, lab, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 0.93))
    fig.suptitle("E1 — Tur bazında PDR, N = 20 (makale Şekil 12–14 karşılığı)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(FIG / "e1_pdr_per_round.png", dpi=160)
    plt.close(fig)


def print_tables(summ: pd.DataFrame, tests: pd.DataFrame) -> None:
    pd.set_option("display.width", 220)
    for n in NODES:
        print(f"\n=== N = {n} ===")
        for d in DATASETS:
            s = summ[(summ["n_nodes"] == n) & (summ["dataset"] == d)].set_index("method").loc[METHOD_ORDER]
            cols = ["pdr_mean", "delay_ms_mean", "throughput_bps_mean", "ee_bit_per_j_mean", "n_ch_mean_mean",
                    "route_hops_mean_mean", "disconnected_ch_frac_mean", "route_ms_per_epoch_mean"]
            print(f"-- {d}\n{s[cols].round(4).to_string()}")
    t = tests[["n_nodes", "dataset", "vs", "metric", "improvement_pct", "wilcoxon_p_holm"]]
    print("\nP'nin iyileşmesi (%) ve Holm düzeltmeli Wilcoxon p:")
    print(t.pivot_table(index=["n_nodes", "dataset", "vs"], columns="metric",
                        values=["improvement_pct", "wilcoxon_p_holm"]).round(4).to_string())


if __name__ == "__main__":
    main()
