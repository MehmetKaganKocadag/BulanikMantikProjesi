"""Deney yardımcıları: yöntem tanımları, tek koşu, paralel koşu, istatistik."""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import product

import numpy as np
import pandas as pd
from scipy import stats

from .config import SimConfig
from .simulator import Simulation, data_topology
from .traffic import get_stream

# CP2 §6 — karşılaştırılan yapılandırmalar
METHODS: dict[str, dict] = {
    "B0": {"clustering": "leach", "routing": "direct", "label": "LEACH + doğrudan"},
    "B1": {"clustering": "leach", "routing": "pso_ga", "label": "LEACH + PSO-GA"},
    "B2": {"clustering": "static_fuzzy", "routing": "pso_ga", "label": "Statik bulanık + PSO-GA"},
    "P": {"clustering": "afl", "routing": "pso_ga", "label": "AFL + PSO-GA (önerilen)"},
    "R1": {"clustering": "afl", "routing": "dijkstra", "label": "AFL + Dijkstra"},
    "R2": {"clustering": "afl", "routing": "pso", "label": "AFL + yalnız PSO"},
    "R3": {"clustering": "afl", "routing": "ga", "label": "AFL + yalnız GA"},
    "KM": {"clustering": "kmeans", "routing": "pso_ga", "label": "k-means + PSO-GA"},  # yalnız sabit K (CP3 §11)
    # Checkpoint 4 önerileri
    "PH": {"clustering": "afl", "routing": "pso_ga", "config": {"mf_rho": 0.5},
           "label": "Hibrit adaptif MF + PSO-GA"},  # ρ, K1 ayar deneyinde seçilir (CP4 §2.3)
    "R0": {"clustering": "afl", "routing": "direct", "label": "AFL + doğrudan"},
    "PD": {"clustering": "afl", "routing": "pso_ga_ds", "label": "AFL + Dijkstra başlatmalı PSO-GA"},
}

METRICS = ["pdr", "delay_ms", "throughput_bps", "ee_bit_per_j"]
LOWER_IS_BETTER = {"delay_ms", "route_fitness_mean", "route_ms_per_epoch", "energy_j", "n_ch_std"}


def run_one(task: dict) -> dict:
    """task: {method, dataset, seed, overrides: dict, tag: dict}"""
    m = METHODS[task["method"]]
    kw = {"clustering": m["clustering"], "routing": m["routing"], **m.get("config", {}), **task.get("overrides", {})}
    cfg = SimConfig().with_(**kw)
    stream = get_stream(task["dataset"], np.random.default_rng([task["seed"], 9]))
    topo = offsets = None
    if cfg.placement == "data":
        topo, offsets = data_topology(cfg, task["dataset"], task["seed"])
    res = Simulation(cfg, stream, task["seed"], topo=topo, offsets=offsets).run()
    row = {"method": task["method"], "dataset": task["dataset"], "seed": task["seed"], **task.get("tag", {})}
    row.update(res.summary)
    if task.get("keep_rounds"):
        row["_per_round"] = res.per_round
    return row


def progress(iterable, total: int, label: str = "koşu"):
    """Tamamlanan iş sayısını yaklaşık %5 aralıklarla stderr'e yazar (tahmini kalan süreyle)."""
    t0, step = time.perf_counter(), max(1, total // 20)
    for i, item in enumerate(iterable, 1):
        if i % step == 0 or i == total:
            el = time.perf_counter() - t0
            print(f"  {i}/{total} {label}, {el / 60:.1f} dk geçti, ~{el / i * (total - i) / 60:.1f} dk kaldı",
                  file=sys.stderr, flush=True)
        yield item


def run_many(tasks: list[dict], workers: int | None = None) -> list[dict]:
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    if workers == 1:
        return list(progress(map(run_one, tasks), len(tasks)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(progress(ex.map(run_one, tasks, chunksize=1), len(tasks)))


def make_tasks(methods, datasets, seeds, overrides=None, tag=None, keep_rounds=False) -> list[dict]:
    return [
        {"method": m, "dataset": d, "seed": int(s), "overrides": overrides or {}, "tag": tag or {},
         "keep_rounds": keep_rounds}
        for m, d, s in product(methods, datasets, seeds)
    ]


def summarize(df: pd.DataFrame, by: list[str], metrics=METRICS) -> pd.DataFrame:
    """Ortalama, std ve %95 güven aralığı (t dağılımı)."""
    rows = []
    for key, g in df.groupby(by, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, key))
        row["n"] = len(g)
        for m in metrics:
            x = g[m].dropna().to_numpy()
            mean, sd = float(np.mean(x)), float(np.std(x, ddof=1)) if x.size > 1 else 0.0
            half = float(stats.t.ppf(0.975, x.size - 1) * sd / np.sqrt(x.size)) if x.size > 1 else np.nan
            row[f"{m}_mean"], row[f"{m}_std"], row[f"{m}_ci95"] = mean, sd, half
        rows.append(row)
    return pd.DataFrame(rows)


def holm(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (p.size - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def paired_tests(df: pd.DataFrame, ref: str, others: list[str], by: list[str], metrics=METRICS) -> pd.DataFrame:
    """ref yöntemi ile diğerleri arasında tohum eşleştirmeli Wilcoxon ve paired t-testi (Holm düzeltmeli)."""
    rows = []
    for key, g in df.groupby(by, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        piv = {m: g.pivot_table(index="seed", columns="method", values=m) for m in metrics}
        for other in others:
            for m in metrics:
                p = piv[m].reindex(columns=[ref, other]).dropna()
                if len(p) < 2:  # ör. hiç paket ulaşmadıysa gecikme tanımsız → test yapılamaz
                    continue
                diff = p[ref] - p[other]
                if (diff == 0).all():
                    w_p, t_stat, t_p = 1.0, 0.0, 1.0
                else:
                    w_p = float(stats.wilcoxon(p[ref], p[other]).pvalue)
                    t_res = stats.ttest_rel(p[ref], p[other])
                    t_stat, t_p = float(t_res.statistic), float(t_res.pvalue)
                base = p[other].mean()
                change = 100 * (p[ref].mean() - base) / base
                if m in LOWER_IS_BETTER:
                    change = -change
                rows.append({**dict(zip(by, key)), "ref": ref, "vs": other, "metric": m, "n": len(p),
                             "ref_mean": p[ref].mean(), "vs_mean": base, "improvement_pct": change,
                             "t": t_stat, "t_p": t_p, "wilcoxon_p": w_p})
    out = pd.DataFrame(rows)
    if not out.empty:
        out["wilcoxon_p_holm"] = holm(out["wilcoxon_p"].to_numpy())
    return out
