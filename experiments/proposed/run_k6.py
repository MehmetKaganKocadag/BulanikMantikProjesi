"""K6 — Yönlendirme ablasyonu ve Dijkstra başlatmalı PSO-GA (CP4 §3).

A — Algoritma düzeyi: N ∈ {20, 50, 100}, 30 topoloji, iki bağlantı durumu (L_s = 1: yeni ağ;
    L_s ~ U(0.7, 1): yıpranmış ağ); AFL'nin ilk turda seçtiği her CH için
    R1 (Dijkstra), R2 (PSO), R3 (GA), P (PSO-GA), PD (Dijkstra başlatmalı PSO-GA).
    En iyi bilinen çözüm: N = 20'de kaba kuvvet (kesin optimum); N = 50, 100'de bütün yöntemler +
    uzun PD koşusu (100 parçacık, 300 iterasyon).
B — Ağ düzeyi: E1 düzeni (N ∈ {20, 50}, 100 tur, 3 veri seti × 30 tohum); R0, R1, R2, R3, P, PD.

Çıktılar:
    results/tables/k6_algo_raw.csv, k6_algo_summary.csv, k6_convergence.csv,
                   k6_net_raw.csv, k6_net_summary.csv, k6_net_tests.csv
    results/figures/k6_convergence.png, k6_algorithm.png, k6_network.png
Çalıştırma (repo kökünden):  python experiments/proposed/run_k6.py
Yalnız analiz:  python experiments/proposed/run_k6.py --analyze
Yalnız A bölümünü yeniden koş (B'yi CSV'den oku):  python experiments/proposed/run_k6.py --algo-only
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from afl_wsn.clustering import FuzzyClustering, form_clusters  # noqa: E402
from afl_wsn.config import SimConfig  # noqa: E402
from afl_wsn.experiment import METRICS, holm, make_tasks, paired_tests, progress, run_many, summarize  # noqa: E402
from afl_wsn.network import deploy  # noqa: E402
from afl_wsn.plotting import SURFACE, TEXT_2, apply_style, plt  # noqa: E402
from afl_wsn.routing import (  # noqa: E402
    build_graph,
    reachable,
    route_dijkstra,
    route_pso_ga,
    route_pso_ga_ds,
    single_path_fitness,
)

TAB, FIG = ROOT / "results" / "tables", ROOT / "results" / "figures"
DATASETS = ["data1", "data2", "data3"]
SEEDS = range(30)
ALGO_N = [20, 50, 100]
NET_N = [20, 50]
ALGOS = ["R1", "R2", "R3", "P", "PD"]
NET_METHODS = ["PD", "P", "R1", "R2", "R3", "R0"]
COLORS = {"P": "#2a78d6", "PD": "#6250d6", "R1": "#008300", "R2": "#e34948", "R3": "#e87ba4", "R0": "#eda100"}
LABELS = {"PD": "PD — Dijkstra başlatmalı PSO-GA (önerilen)", "P": "P — PSO-GA (makale)", "R1": "R1 — Dijkstra",
          "R2": "R2 — yalnız PSO", "R3": "R3 — yalnız GA", "R0": "R0 — doğrudan"}
EVAL_GRID = np.arange(0, 3601, 30)
LS_MODES = {"yeni": None, "yipranmis": (0.7, 1.0)}
LS_LABELS = {"yeni": "yeni ağ (L_s = 1)", "yipranmis": "yıpranmış ağ (L_s ~ U(0.7, 1))"}
NET_EXTRA = ["route_fitness_mean", "route_ms_per_epoch", "fitness_evals_per_epoch", "disconnected_ch_frac",
             "route_hops_mean"]


# --------------------------------------------------------------------------- A: algoritma düzeyi
def brute_force_best(src, g, cfg) -> float:
    best, stack = np.inf, [(src, [src])]
    while stack:
        u, path = stack.pop()
        if u == g.bs:
            best = min(best, single_path_fitness(path, g, cfg))
            continue
        for v in np.flatnonzero(g.adj[u]):
            if v not in path:
                stack.append((int(v), path + [int(v)]))
    return best


def evals_per_iter(cfg, mode: str, n_iters: int) -> np.ndarray:
    """record=True geçmişinin her elemanına karşılık gelen kümülatif değerlendirme sayısı."""
    pc = cfg.pso
    ev = [pc.n_particles]
    for it in range(1, n_iters + 1):
        e = 0
        if mode in ("pso_ga", "pso"):
            e += pc.n_particles
        if mode == "ga" or (mode == "pso_ga" and it % pc.ga_interval == 0):
            e += pc.n_offspring
        ev.append(ev[-1] + e)
    return np.array(ev)


def on_grid(history, evals) -> np.ndarray:
    """Adım fonksiyonu: her ızgara noktasında o ana kadarki en iyi uygunluk (erken durunca sabit)."""
    idx = np.searchsorted(evals, EVAL_GRID, side="right") - 1
    h = np.asarray(history)
    out = h[np.clip(idx, 0, len(h) - 1)]
    out[idx < 0] = np.nan
    return out


def algo_topology(args) -> tuple[list[dict], list[dict]]:
    n, seed, ls_mode = args
    cfg = SimConfig().with_(n_nodes=n)
    topo = deploy(cfg, np.random.default_rng([1000 + seed, n]))
    alive = np.ones(n, dtype=bool)
    rng_ls = LS_MODES[ls_mode]
    ls = np.ones(n) if rng_ls is None else np.random.default_rng([2000 + seed, n]).uniform(*rng_ls, n)
    ch = FuzzyClustering(cfg).select(np.full(n, cfg.e_init), ls, alive, topo, None, 0)
    _, ch = form_clusters(ch, alive, topo, cfg)
    g = build_graph(topo, alive, ls, cfg)
    rows, curves = [], []
    for h in map(int, np.flatnonzero(ch)):
        if not reachable(h, g):
            continue
        res = {}
        for k, algo in enumerate(ALGOS):
            rng = np.random.default_rng([seed, h, k, n])
            if algo == "R1":
                res[algo] = (route_dijkstra(h, g, cfg), None)
            elif algo == "PD":
                res[algo] = (route_pso_ga_ds(h, g, cfg, rng, record=True), "pso_ga")
            else:
                mode = {"R2": "pso", "R3": "ga", "P": "pso_ga"}[algo]
                res[algo] = (route_pso_ga(h, g, cfg.with_(pso__mode=mode), rng, record=True), mode)
        if n <= 20:
            best = brute_force_best(h, g, cfg)
        else:
            long_cfg = cfg.with_(pso__n_particles=100, pso__max_iter=300, pso__patience=300, pso__n_offspring=100)
            ref = route_pso_ga_ds(h, g, long_cfg, np.random.default_rng([seed, h, 99, n]))
            best = min([ref.fitness] + [r.fitness for r, _ in res.values()])
        for algo, (r, mode) in res.items():
            rows.append({"ls": ls_mode, "n_nodes": n, "topo": seed, "ch": h, "algo": algo, "fitness": r.fitness, "best": best,
                         "rel_gap": (r.fitness - best) / best, "hit": r.fitness <= best + 1e-9,
                         "evals": r.evals, "iters": r.iters, "ms": 1e3 * r.seconds, "hops": len(r.path) - 1})
            if mode is not None:
                gap = (on_grid(r.history, evals_per_iter(cfg, mode, len(r.history) - 1)) - best) / best
                curves.append({"ls": ls_mode, "n_nodes": n, "algo": algo, "gap": gap})
            else:
                curves.append({"ls": ls_mode, "n_nodes": n, "algo": algo,
                               "gap": np.full(EVAL_GRID.size, (r.fitness - best) / best)})
    return rows, curves


def run_algo() -> tuple[pd.DataFrame, pd.DataFrame]:
    jobs = [(n, s, ls) for ls in LS_MODES for n in ALGO_N for s in SEEDS]
    workers = max(1, (os.cpu_count() or 2) - 1)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(progress(ex.map(algo_topology, jobs, chunksize=1), len(jobs), "topoloji"))
    rows = [r for rs, _ in out for r in rs]
    conv = {}
    for _, cs in out:
        for c in cs:
            conv.setdefault((c["ls"], c["n_nodes"], c["algo"]), []).append(c["gap"])
    crow = []
    for (ls, n, algo), gaps in conv.items():
        G = np.vstack(gaps)
        for e, mean in zip(EVAL_GRID, np.nanmean(G, axis=0)):
            crow.append({"ls": ls, "n_nodes": n, "algo": algo, "evals": int(e), "mean_rel_gap": mean})
    return pd.DataFrame(rows), pd.DataFrame(crow)


def summarize_algo(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["ls", "n_nodes", "algo"])
    out = g.agg(n_routes=("hit", "size"), hit_rate=("hit", "mean"), rel_gap_mean=("rel_gap", "mean"),
                rel_gap_max=("rel_gap", "max"), evals_mean=("evals", "mean"), iters_mean=("iters", "mean"),
                ms_mean=("ms", "mean"), ms_median=("ms", "median"), hops_mean=("hops", "mean")).reset_index()
    # PD ≤ R1 garantisi: ihlal sayısı
    piv = df.pivot_table(index=["ls", "n_nodes", "topo", "ch"], columns="algo", values="fitness")
    viol = (piv["PD"] > piv["R1"] + 1e-12).groupby(level=[0, 1]).sum()
    key = list(zip(out["ls"], out["n_nodes"]))
    out["pd_worse_than_r1"] = pd.Series([viol.get(k, np.nan) for k in key]).where(out["algo"] == "PD")
    return out


# --------------------------------------------------------------------------- B: ağ düzeyi
def run_net() -> pd.DataFrame:
    tasks = []
    for n in NET_N:
        tasks += make_tasks(NET_METHODS, DATASETS, SEEDS, overrides={"n_nodes": n}, tag={"n_nodes": n})
    return pd.DataFrame(run_many(tasks))


# --------------------------------------------------------------------------- grafikler
def plot_convergence(conv: pd.DataFrame) -> None:
    fig, axes = plt.subplots(len(LS_MODES), len(ALGO_N), figsize=(13, 6.8), sharey="row", sharex=True)
    for r, lsm in enumerate(LS_MODES):
        for ax, n in zip(axes[r], ALGO_N):
            c = conv[(conv.ls == lsm) & (conv.n_nodes == n)]
            for algo in ["R2", "R3", "P", "PD"]:
                g = c[c.algo == algo]
                ax.plot(g["evals"], 100 * g["mean_rel_gap"], color=COLORS[algo], label=LABELS[algo],
                        lw=2.4 if algo == "PD" else 1.8)
            r1 = c[c.algo == "R1"]["mean_rel_gap"].iloc[0]
            ax.axhline(100 * r1, color=COLORS["R1"], lw=1.6, ls="--", label=LABELS["R1"])
            ax.set_title(f"N = {n} · {LS_LABELS[lsm]}", fontsize=9.5)
            if r == len(LS_MODES) - 1:
                ax.set_xlabel("Uygunluk değerlendirme sayısı")
            final = c[c.evals == c.evals.max()]["mean_rel_gap"].max()  # son düzeyler görünsün, ilk sıçramalar kırpılır
            ax.set_ylim(0, max(0.5, 120 * final))
            ax.grid(True, axis="both")
        axes[r, 0].set_ylabel("En iyi bilinene göre ort. fark (%)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.04), fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(FIG / "k6_convergence.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def bars(ax, table, xcol, xs_vals, ycol, methods, scale=1.0, err=None, fmt=None):
    width = 0.8 / len(methods)
    x = np.arange(len(xs_vals))
    for j, m in enumerate(methods):
        rows = [table[(table[xcol] == v) & (table["method"] == m)].iloc[0] for v in xs_vals]
        y = np.array([r[ycol] for r in rows]) * scale
        xs = x - 0.4 + width * (j + 0.5)
        ax.bar(xs, y, width, color=COLORS[m], edgecolor=SURFACE, linewidth=1.5, label=LABELS[m], zorder=2)
        if err:
            e = np.array([r[err] for r in rows]) * scale
            ax.errorbar(xs, y, yerr=e, fmt="none", ecolor=TEXT_2, elinewidth=0.8, capsize=1.5, zorder=3)
        if fmt:
            for xi, yi in zip(xs, y):
                ax.text(xi, yi, fmt.format(yi), ha="center", va="bottom", fontsize=6, color=TEXT_2)
    ax.set_xticks(x, [f"N = {v}" for v in xs_vals])
    ax.set_axisbelow(True)


def plot_algorithm(summ: pd.DataFrame) -> None:
    fig, axes = plt.subplots(len(LS_MODES), 3, figsize=(13, 7.2))
    for r, lsm in enumerate(LS_MODES):
        t = summ[summ.ls == lsm].rename(columns={"algo": "method"})
        bars(axes[r, 0], t, "n_nodes", ALGO_N, "hit_rate", ALGOS, 100, fmt="{:.0f}")
        axes[r, 0].set_ylabel(f"En iyiye ulaşma (%)\n{LS_LABELS[lsm]}")
        axes[r, 0].set_ylim(0, 110)
        bars(axes[r, 1], t, "n_nodes", ALGO_N, "rel_gap_mean", ALGOS, 100, fmt="{:.2f}")
        axes[r, 1].set_ylabel("Ortalama göreli fark (%)")
        bars(axes[r, 2], t, "n_nodes", ALGO_N, "ms_mean", ALGOS, fmt="{:.1f}")
        axes[r, 2].set_yscale("log")
        axes[r, 2].set_ylabel("Rota başına CPU süresi (ms, log)")
        axes[r, 2].grid(True, axis="y", which="both")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.04), fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(FIG / "k6_algorithm.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_network(summ: pd.DataFrame) -> None:
    pooled = summ.copy()
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, (metric, label, scale, fmt) in zip(axes, [("pdr", "PDR", 1, None),
                                                      ("ee_bit_per_j", "Enerji verimliliği (Mbit/J)", 1e-6, None),
                                                      ("route_ms_per_epoch", "Epoch başına yönlendirme süresi (ms, log)",
                                                       1, "{:.1f}")]):
        bars(ax, pooled, "n_nodes", NET_N, f"{metric}_mean", NET_METHODS, scale, err=f"{metric}_ci95", fmt=fmt)
        ax.set_ylabel(label)
    axes[2].set_yscale("log")
    axes[2].grid(True, axis="y", which="both")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.1), fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(FIG / "k6_network.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    if "--analyze" in sys.argv:
        algo = pd.read_csv(TAB / "k6_algo_raw.csv")
        conv = pd.read_csv(TAB / "k6_convergence.csv")
        net = pd.read_csv(TAB / "k6_net_raw.csv")
    elif "--algo-only" in sys.argv:
        t0 = time.perf_counter()
        algo, conv = run_algo()
        print(f"A: {len(algo)} rota, {time.perf_counter() - t0:.0f} s")
        algo.to_csv(TAB / "k6_algo_raw.csv", index=False)
        conv.to_csv(TAB / "k6_convergence.csv", index=False)
        net = pd.read_csv(TAB / "k6_net_raw.csv")
    else:
        t0 = time.perf_counter()
        algo, conv = run_algo()
        print(f"A: {len(algo)} rota, {time.perf_counter() - t0:.0f} s")
        algo.to_csv(TAB / "k6_algo_raw.csv", index=False)
        conv.to_csv(TAB / "k6_convergence.csv", index=False)
        t0 = time.perf_counter()
        net = run_net()
        print(f"B: {len(net)} koşu, {time.perf_counter() - t0:.0f} s")
        net.to_csv(TAB / "k6_net_raw.csv", index=False)

    asum = summarize_algo(algo)
    asum.to_csv(TAB / "k6_algo_summary.csv", index=False)
    nsum_ds = summarize(net, ["n_nodes", "dataset", "method"], METRICS + NET_EXTRA)
    nsum_ds.to_csv(TAB / "k6_net_summary.csv", index=False)
    nsum = summarize(net, ["n_nodes", "method"], METRICS + NET_EXTRA)
    nsum.to_csv(TAB / "k6_net_summary_pooled.csv", index=False)
    mets = METRICS + ["route_ms_per_epoch"]
    t1 = paired_tests(net, "PD", ["P", "R1"], ["n_nodes", "dataset"], mets)
    t2 = paired_tests(net, "P", ["R0", "R1", "R2", "R3"], ["n_nodes", "dataset"], mets)
    tests = pd.concat([t1, t2], ignore_index=True)
    tests["wilcoxon_p_holm"] = holm(tests["wilcoxon_p"].to_numpy())
    tests.to_csv(TAB / "k6_net_tests.csv", index=False)

    apply_style()
    plot_convergence(conv)
    plot_algorithm(asum)
    plot_network(nsum)

    pd.set_option("display.width", 220)
    print(asum.round(4).to_string(index=False))
    cols = ["n_nodes", "method"] + [f"{m}_mean" for m in METRICS + NET_EXTRA]
    print(nsum[cols].round(4).to_string(index=False))
    tt = tests[tests.metric.isin(["pdr", "ee_bit_per_j", "route_ms_per_epoch"])]
    print(tt.pivot_table(index=["ref", "vs", "n_nodes", "dataset"], columns="metric",
                         values=["improvement_pct", "wilcoxon_p_holm"]).round(4).to_string())


if __name__ == "__main__":
    main()
