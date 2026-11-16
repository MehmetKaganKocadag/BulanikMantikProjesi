"""K1 — Hibrit adaptif MF ve ağ ömrü (CP4 §2).

1. Ayar: ρ ∈ {0.25, 0.5, 0.75} ayrı tohumlarda (100–109) denenir; ana ölçütün (toplam teslim)
   P'ye oranı en yüksek olan ρ seçilir.
2. Test: B1, B2, P, PH (seçilen ρ) — N = 50, E₀ = 0.25 J, son düğüm ölene kadar;
   homojen ve heterojen (±%50) başlangıç enerjisi; 3 veri seti × 30 tohum.

Çıktılar:
    results/tables/k1_tune.csv, k1_raw.csv, k1_summary.csv, k1_tests.csv, k1_alive.csv
    results/figures/k1_lifetime.png, k1_metrics.png
Çalıştırma (repo kökünden):  python experiments/proposed/run_k1.py
Yalnız analiz (koşuları tekrarlamadan):  python experiments/proposed/run_k1.py --analyze
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from afl_wsn.experiment import holm, make_tasks, paired_tests, run_many, summarize  # noqa: E402
from afl_wsn.plotting import DATASET_LABELS, METHOD_COLORS, SURFACE, TEXT_2, apply_style, plt  # noqa: E402

TAB, FIG = ROOT / "results" / "tables", ROOT / "results" / "figures"
DATASETS = ["data1", "data2", "data3"]
TEST_SEEDS = range(30)
TUNE_SEEDS = range(100, 110)
RHOS = [0.25, 0.5, 0.75]
SCENARIOS = {"homojen": 0.0, "heterojen": 0.5}
METHODS = ["PH", "P", "B2", "B1"]
COLORS = {**METHOD_COLORS, "PH": "#6250d6"}  # referans paletin 7. slotu (violet)
LABELS = {"PH": "PH — hibrit MF (önerilen)", "P": "P — adaptif MF (makale)", "B2": "B2 — statik MF",
          "B1": "B1 — LEACH"}
METRICS = ["delivered", "fnd", "hnd", "lnd", "pdr", "ee_bit_per_j", "n_ch_std"]
BASE = {"n_nodes": 50, "e_init": 0.25, "run_until_dead": True, "n_rounds": 5000}


def run(tasks: list[dict]) -> pd.DataFrame:
    rows = run_many(tasks)
    alive = []
    for r in rows:
        pr = r.pop("_per_round")
        r["n_ch_std"] = float(np.std(pr["n_ch"]))
        alive.append((r["method"], r["scenario"], r["dataset"], r["seed"], pr["alive"]))
    df = pd.DataFrame(rows)
    df.attrs["alive"] = alive
    return df


def tasks_for(methods, seeds, rho_by_method: dict) -> list[dict]:
    out = []
    for scen, spread in SCENARIOS.items():
        for m in methods:
            ov = {**BASE, "e_init_spread": spread}
            if m in rho_by_method:
                ov["mf_rho"] = rho_by_method[m]
            out += make_tasks([m], DATASETS, seeds, overrides=ov, tag={"scenario": scen}, keep_rounds=True)
    return out


def tune() -> tuple[float, pd.DataFrame]:
    tasks = []
    for rho in [0.0] + RHOS:
        for t in tasks_for(["P"], TUNE_SEEDS, {"P": rho}):
            t["tag"] = {**t["tag"], "rho": rho}
            tasks.append(t)
    df = run(tasks)
    base = df[df.rho == 0.0].set_index(["scenario", "dataset", "seed"])["delivered"]
    rows = []
    for rho in RHOS:
        d = df[df.rho == rho].set_index(["scenario", "dataset", "seed"])["delivered"]
        ratio = (d / base.loc[d.index]).mean()
        rows.append({"rho": rho, "delivered_ratio_vs_P": ratio,
                     "delivered_mean": d.mean(), "hnd_mean": df[df.rho == rho]["hnd"].mean()})
    tab = pd.DataFrame(rows)
    best = float(tab.loc[tab["delivered_ratio_vs_P"].idxmax(), "rho"])
    return best, tab


def alive_curves(alive) -> pd.DataFrame:
    """Canlı düğüm oranı – tur; ağ öldükten sonraki turlar 0 sayılır, tohumlar üzerinden ortalama."""
    groups: dict = {}
    for m, scen, ds, seed, a in alive:
        groups.setdefault((m, scen, ds), []).append(a / BASE["n_nodes"])
    rows = []
    for (m, scen, ds), arrs in groups.items():
        T = max(len(a) for a in arrs)
        M = np.zeros((len(arrs), T))
        for i, a in enumerate(arrs):
            M[i, : len(a)] = a
        mean = M.mean(axis=0)
        for t in range(0, T, 5):
            rows.append({"method": m, "scenario": scen, "dataset": ds, "round": t + 1, "alive_frac": mean[t]})
    return pd.DataFrame(rows)


def plot_lifetime(curves: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.4), sharex="col", sharey=True)
    for r, scen in enumerate(SCENARIOS):
        for c, ds in enumerate(DATASETS):
            ax = axes[r, c]
            for m in METHODS:
                g = curves[(curves.method == m) & (curves.scenario == scen) & (curves.dataset == ds)]
                ax.plot(g["round"], g["alive_frac"], color=COLORS[m], label=LABELS[m],
                        lw=2.4 if m == "PH" else 1.6)
            ax.set_title(f"{DATASET_LABELS[ds].replace(chr(10), ' — ')} · {scen}", fontsize=9.5)
            ax.grid(True, axis="both")
            if r == 1:
                ax.set_xlabel("Tur")
            if c == 0:
                ax.set_ylabel("Canlı düğüm oranı")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(FIG / "k1_lifetime.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_metrics(summ: pd.DataFrame) -> None:
    show = [("delivered", "Toplam teslim (bin okuma)", 1e-3), ("fnd", "FND (tur)", 1), ("hnd", "HND (tur)", 1)]
    cells = [(s, d) for s in SCENARIOS for d in DATASETS]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9))
    width = 0.8 / len(METHODS)
    x = np.arange(len(cells))
    for ax, (metric, label, scale) in zip(axes, show):
        for j, m in enumerate(METHODS):
            rows = [summ[(summ.scenario == s) & (summ.dataset == d) & (summ.method == m)].iloc[0] for s, d in cells]
            mean = np.array([row[f"{metric}_mean"] for row in rows]) * scale
            ci = np.array([row[f"{metric}_ci95"] for row in rows]) * scale
            xs = x - 0.4 + width * (j + 0.5)
            ax.bar(xs, mean, width, color=COLORS[m], edgecolor=SURFACE, linewidth=1.5, label=LABELS[m], zorder=2)
            ax.errorbar(xs, mean, yerr=ci, fmt="none", ecolor=TEXT_2, elinewidth=0.8, capsize=1.5, zorder=3)
        ax.set_xticks(x, [f"{d}\n{s}" for s, d in cells], fontsize=7.5)
        ax.set_ylabel(label)
        ax.set_axisbelow(True)
        ax.set_ylim(0, None)  # çubuk grafik: eksen sıfırdan başlar
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(FIG / "k1_metrics.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    if "--analyze" in sys.argv:
        tune_tab = pd.read_csv(TAB / "k1_tune.csv")
        rho = float(tune_tab.loc[tune_tab["delivered_ratio_vs_P"].idxmax(), "rho"])
        df = pd.read_csv(TAB / "k1_raw.csv")
        curves = pd.read_csv(TAB / "k1_alive.csv")
    else:
        t0 = time.perf_counter()
        rho, tune_tab = tune()
        tune_tab.to_csv(TAB / "k1_tune.csv", index=False)
        print(f"Ayar ({time.perf_counter() - t0:.0f} s):\n{tune_tab.round(4).to_string(index=False)}\nSeçilen ρ = {rho}")
        t0 = time.perf_counter()
        df = run(tasks_for(METHODS, TEST_SEEDS, {"PH": rho}))
        print(f"Test: {len(df)} koşu, {time.perf_counter() - t0:.0f} s")
        curves = alive_curves(df.attrs["alive"])
        df.to_csv(TAB / "k1_raw.csv", index=False)
        curves.to_csv(TAB / "k1_alive.csv", index=False)

    summ = summarize(df, ["scenario", "dataset", "method"], METRICS)
    summ.to_csv(TAB / "k1_summary.csv", index=False)
    t1 = paired_tests(df, "PH", ["P", "B2", "B1"], ["scenario", "dataset"], METRICS[:-1])
    t2 = paired_tests(df, "P", ["B2"], ["scenario", "dataset"], METRICS[:-1])  # H1a
    tests = pd.concat([t1, t2], ignore_index=True)
    tests["wilcoxon_p_holm"] = holm(tests["wilcoxon_p"].to_numpy())
    tests.to_csv(TAB / "k1_tests.csv", index=False)

    apply_style()
    plot_lifetime(curves)
    plot_metrics(summ)

    pd.set_option("display.width", 220)
    print(f"ρ = {rho}")
    cols = ["scenario", "dataset", "method"] + [f"{m}_mean" for m in METRICS]
    print(summ[cols].round(3).to_string(index=False))
    tt = tests[tests.metric.isin(["delivered", "fnd", "hnd"])]
    print(tt.pivot_table(index=["ref", "vs", "scenario", "dataset"], columns="metric",
                         values=["improvement_pct", "wilcoxon_p_holm"]).round(4).to_string())


if __name__ == "__main__":
    main()
