"""Canlı demo (yönerge md. 14): bulanık sistem, yönlendirme ve küçük bir ağ simülasyonu.

Repo kökünden:
    python experiments/demo.py fis 0.9 0.3 0.4 0.95       # Er, DBS, Nd, Ls için CH skoru ve ateşlenen kurallar
    python experiments/demo.py fis 0.9 0.3 0.4 0.95 --adaptive 0.85 0.98
                                                         # enerji bölümlemesi dar bir banda (0.85–0.98) uyarlanmış
    python experiments/demo.py route --nodes 50 --seed 3  # bir CH için Dijkstra, PSO-GA ve PD karşılaştırması
    python experiments/demo.py sim --nodes 20 --dataset data3 --rounds 50 --seed 7
                                                         # P, B2, B1, B0 ve PD'yi aynı ağda koştur
    python experiments/demo.py                           # üçünün kısa bir turu

Veri dosyaları yoksa sim komutu sentetik akışla çalışır (--dataset synthetic).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from afl_wsn.clustering import FuzzyClustering, form_clusters  # noqa: E402
from afl_wsn.config import SimConfig  # noqa: E402
from afl_wsn.experiment import METHODS  # noqa: E402
from afl_wsn.fuzzy import INPUTS, OUTPUT_TERMS, TERMS, FuzzyCHSystem, ThreeTermPartition, static_partition  # noqa: E402
from afl_wsn.network import deploy  # noqa: E402
from afl_wsn.routing import build_graph, reachable, route_dijkstra, route_pso_ga, route_pso_ga_ds  # noqa: E402
from afl_wsn.simulator import Simulation  # noqa: E402
from afl_wsn.traffic import get_stream  # noqa: E402

TR_IN = {"energy": "Kalan enerji Er", "distance": "BS'ye uzaklık DBS", "density": "Yoğunluk Nd",
         "link": "Bağlantı Ls"}
TR_T = {"Low": "Düşük", "Medium": "Orta", "High": "Yüksek", "VeryLow": "Çok Düşük", "VeryHigh": "Çok Yüksek"}


def cmd_fis(a):
    x = np.array([[a.er, a.dbs, a.nd, a.ls]])
    parts = {name: static_partition() for name in INPUTS}
    if a.adaptive:
        lo, hi = a.adaptive
        parts["energy"] = ThreeTermPartition(lo, (lo + hi) / 2, hi)
    fis = FuzzyCHSystem(parts)
    print("\n== Bulanıklaştırma ==")
    mu = fis.fuzzify(x)
    for i, name in enumerate(INPUTS):
        p = parts[name]
        m = ", ".join(f"{TR_T[t]} {v:.2f}" for t, v in zip(TERMS, mu[i][0]))
        print(f"  {TR_IN[name]:<20} = {x[0, i]:.2f}   (a, b, c) = ({p.a:.2f}, {p.b:.2f}, {p.c:.2f})   →  {m}")
    alpha = fis.firing_strengths(x)[0]
    order = np.argsort(-alpha)
    print("\n== Ateşlenen kurallar (min-AND) ==")
    for k in order[:8]:
        if alpha[k] <= 0:
            break
        r = fis.rules[k]
        cond = " VE ".join(f"{TR_IN[n].split()[-1]} {TR_T[TERMS[t]]}" for n, t in zip(INPUTS, r.antecedent))
        print(f"  α = {alpha[k]:.2f}   EĞER {cond}  →  CH {TR_T[OUTPUT_TERMS[r.consequent]]}")
    print(f"  ({(alpha > 0).sum()} kural ateşlendi)")
    wa = fis.score(x)[0]
    ce = FuzzyCHSystem(parts, defuzz="centroid").score(x)[0]
    print("\n== Durulaştırma ==")
    print(f"  Ağırlıklı ortalama (makale Denk. 10): CH skoru = {wa:.3f}")
    print(f"  Mamdani centroid (karşılaştırma)    : CH skoru = {ce:.3f}")


def cmd_route(a):
    cfg = SimConfig().with_(n_nodes=a.nodes)
    topo = deploy(cfg, np.random.default_rng(a.seed))
    alive = np.ones(a.nodes, dtype=bool)
    ls = np.random.default_rng(a.seed + 1).uniform(0.7, 1.0, a.nodes)
    ch = FuzzyClustering(cfg).select(np.full(a.nodes, cfg.e_init), ls, alive, topo, None, 0)
    _, ch = form_clusters(ch, alive, topo, cfg)
    g = build_graph(topo, alive, ls, cfg)
    heads = [int(h) for h in np.flatnonzero(ch) if reachable(int(h), g)]
    if not heads:
        print("Bu topolojide BS'ye bağlı CH yok; başka bir --seed deneyin.")
        return
    h = max(heads, key=lambda i: topo.dist[i, topo.bs_index])  # BS'ye en uzak bağlı CH
    print(f"\nN = {a.nodes}, tohum {a.seed}: {int(ch.sum())} CH; BS'ye en uzak bağlı CH = düğüm {h} "
          f"({topo.dist[h, topo.bs_index]:.1f} m)\n")
    rng = np.random.default_rng(a.seed)
    rows = [("Dijkstra (R1)", route_dijkstra(h, g, cfg)),
            ("PSO-GA (P, makale)", route_pso_ga(h, g, cfg, rng)),
            ("Dijkstra başlatmalı PSO-GA (PD)", route_pso_ga_ds(h, g, cfg, rng))]
    print(f"  {'Yöntem':<33}{'uygunluk f':>11}{'değerlendirme':>15}{'süre (ms)':>11}   yol")
    for name, r in rows:
        print(f"  {name:<33}{r.fitness:>11.4f}{r.evals:>15}{1e3 * r.seconds:>11.2f}   {' → '.join(map(str, r.path))}")
    print("\n  (f düşük daha iyi; son düğüm BS. PD hiçbir zaman Dijkstra'dan kötü olamaz.)")


def cmd_sim(a):
    stream = get_stream(a.dataset, np.random.default_rng([a.seed, 9]))
    print(f"\n{a.dataset}, N = {a.nodes}, {a.rounds} tur, tohum {a.seed} (bütün yöntemler aynı topoloji ve trafik)\n")
    print(f"  {'Yöntem':<40}{'PDR':>7}{'gecikme ms':>12}{'EE Mbit/J':>11}{'CH':>6}{'bağlantısız CH':>16}{'süre s':>8}")
    for m in a.methods:
        spec = METHODS[m]
        cfg = SimConfig().with_(n_nodes=a.nodes, n_rounds=a.rounds, clustering=spec["clustering"],
                                routing=spec["routing"], **spec.get("config", {}))
        t0 = time.perf_counter()
        s = Simulation(cfg, stream, a.seed).run().summary
        print(f"  {m + ' — ' + spec['label']:<40}{s['pdr']:>7.3f}{s['delay_ms']:>12.1f}{s['ee_bit_per_j'] / 1e6:>11.2f}"
              f"{s['n_ch_mean']:>6.1f}{s['disconnected_ch_frac']:>16.2f}{time.perf_counter() - t0:>8.1f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fis", help="tek bir düğüm için CH skoru")
    for n, d in (("er", 0.9), ("dbs", 0.3), ("nd", 0.4), ("ls", 0.95)):
        f.add_argument(n, type=float, nargs="?", default=d)
    f.add_argument("--adaptive", type=float, nargs=2, metavar=("MIN", "MAX"),
                   help="enerji bölümlemesini bu banda uyarla (adaptif MF'nin etkisini görmek için)")
    r = sub.add_parser("route", help="bir CH için yönlendirme karşılaştırması")
    r.add_argument("--nodes", type=int, default=50)
    r.add_argument("--seed", type=int, default=3)
    s = sub.add_parser("sim", help="küçük ağ simülasyonu")
    s.add_argument("--nodes", type=int, default=20)
    s.add_argument("--rounds", type=int, default=50)
    s.add_argument("--seed", type=int, default=7)
    s.add_argument("--dataset", default="data3", choices=["data1", "data2", "data3", "synthetic"])
    s.add_argument("--methods", nargs="+", default=["P", "B2", "B1", "B0", "PD"], choices=list(METHODS))
    a = ap.parse_args()

    if a.cmd is None:  # kısa tur
        print("### 1) Bulanık sistem: enerjisi yüksek, BS'ye yakın, bağlantısı iyi bir düğüm")
        cmd_fis(ap.parse_args(["fis", "0.9", "0.3", "0.4", "0.95"]))
        print("\n### 2) Aynı düğüm, enerji bölümlemesi dar bir banda (0.85–0.98) uyarlanmışken")
        cmd_fis(ap.parse_args(["fis", "0.9", "0.3", "0.4", "0.95", "--adaptive", "0.85", "0.98"]))
        print("\n### 3) Yönlendirme")
        cmd_route(ap.parse_args(["route"]))
        print("\n### 4) Küçük ağ simülasyonu")
        try:
            cmd_sim(ap.parse_args(["sim"]))
        except FileNotFoundError:
            cmd_sim(ap.parse_args(["sim", "--dataset", "synthetic"]))
        return
    {"fis": cmd_fis, "route": cmd_route, "sim": cmd_sim}[a.cmd](a)


if __name__ == "__main__":
    main()
