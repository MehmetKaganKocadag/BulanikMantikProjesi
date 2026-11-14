"""Tur tabanlı WSN simülatörü.

Bir tur:
  1. Gerekirse yeniden kümeleme (her `epoch_len` turda bir ya da bir CH'nin enerjisi
     dönem başının `ch_energy_drop` katının altına düşünce) ve her CH için rota hesabı.
  2. Trafik: hangi düğümlerin okuma (paket) ürettiği.
  3. Üye → CH iletimleri (rastgele sırayla; CH'de FIFO kuyruk).
  4. CH'de veri birleştirme (E_DA · k · okuma sayısı) ve birleştirilmiş paketin rota
     boyunca iletimi. Herhangi bir atlama başarısız olursa paketteki okumalar kaybolur.

Metrikler okuma (uygulama verisi) düzeyindedir: bir okuma ancak üye→CH ve CH→BS
rotasının bütün atlamaları başarılıysa BS'ye ulaşmış sayılır (CP2 §7).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from .clustering import FuzzyClustering, KMeansClustering, LeachClustering, form_clusters
from .config import SimConfig
from .network.link import hop_delay, p_success
from .network.radio import e_rx, e_tx
from .network.topology import Topology, deploy, from_positions
from .routing import RouteResult, build_graph, find_route
from .traffic import TrafficSource, load_placement


@dataclass
class RunResult:
    summary: dict
    per_round: dict[str, np.ndarray]
    route_history: list[RouteResult] = field(default_factory=list)


def make_clustering(cfg: SimConfig):
    if cfg.clustering == "afl":
        return FuzzyClustering(cfg, adaptive=True)
    if cfg.clustering == "static_fuzzy":
        return FuzzyClustering(cfg, adaptive=False)
    if cfg.clustering == "leach":
        return LeachClustering(cfg)
    if cfg.clustering == "kmeans":
        return KMeansClustering(cfg)
    raise ValueError(f"Bilinmeyen kümeleme: {cfg.clustering}")


def data_topology(cfg: SimConfig, dataset: str, seed: int) -> tuple[Topology, np.ndarray]:
    """Veriden yerleşim (CP3 §11): tohuma göre N kayıt seçilir (tekrarsız), iki sütunu alana
    ölçeklenip düğüm konumu olur. Döndürür: (topoloji, düğüm başına akış ofseti = kayıt indeksi)."""
    pts = load_placement(dataset)
    idx = np.random.default_rng([seed, 0]).choice(len(pts), size=cfg.n_nodes, replace=len(pts) < cfg.n_nodes)
    return from_positions(pts[idx] * cfg.area, cfg), idx


class Simulation:
    def __init__(self, cfg: SimConfig, stream: np.ndarray, seed: int, topo: Topology | None = None,
                 offsets: np.ndarray | None = None) -> None:
        self.cfg = cfg
        # Tohum akışları: topoloji ve trafik yöntemden bağımsızdır → yöntemler eşleştirilmiş karşılaştırılır.
        self.topo = topo if topo is not None else deploy(cfg, np.random.default_rng([seed, 0]))
        self.traffic = TrafficSource(stream, cfg, np.random.default_rng([seed, 1]), offsets=offsets)
        self.rng = np.random.default_rng([seed, 2])
        n = cfg.n_nodes
        self.energy = np.full(n, cfg.e_init, dtype=float)
        self.ls = np.ones(n)
        self.clustering = make_clustering(cfg)

    # ------------------------------------------------------------------ yardımcılar
    def _spend(self, i: int, joules: float) -> None:
        if i < self.cfg.n_nodes:
            self.energy[i] -= joules
            self.spent_round += joules

    def _ack(self, i: int, ok: bool) -> None:
        a = self.cfg.ls_alpha
        self.ls[i] = (1 - a) * self.ls[i] + a * float(ok)

    def _recluster(self, alive: np.ndarray, epoch: int) -> None:
        cfg, topo = self.cfg, self.topo
        t0 = time.perf_counter()
        ch = self.clustering.select(self.energy, self.ls, alive, topo, self.rng, epoch)
        self.parent, self.ch = form_clusters(ch, alive, topo, cfg)
        t1 = time.perf_counter()
        mem = np.flatnonzero(alive & ~self.ch)
        if mem.size:
            dm = topo.dist[mem, self.parent[mem]]
            self.cost["member_d"].append(float(dm.mean()))
            self.cost["member_oor"] += int((dm > cfg.comm_range).sum())
            self.cost["n_members"] += int(mem.size)
        self.graph = build_graph(topo, alive, self.ls, cfg)
        self.routes: dict[int, RouteResult] = {}
        for h in np.flatnonzero(self.ch):
            self.routes[int(h)] = find_route(int(h), self.graph, cfg, self.rng)
        t2 = time.perf_counter()
        self.epoch_energy = self.energy.copy()
        self.cost["cluster_s"] += t1 - t0
        self.cost["route_s"] += t2 - t1
        self.cost["epochs"] += 1
        self.cost["evals"] += sum(r.evals for r in self.routes.values())
        self.cost["route_fitness"].extend(r.fitness for r in self.routes.values())
        self.cost["disconnected"] += sum(not r.connected for r in self.routes.values())
        self.cost["n_routes"] += len(self.routes)
        self.cost["hops"].extend(len(r.path) - 1 for r in self.routes.values())

    def _reroute(self, h: int, alive: np.ndarray) -> None:
        self.graph = build_graph(self.topo, alive, self.ls, self.cfg)
        self.routes[h] = find_route(h, self.graph, self.cfg, self.rng)

    # ------------------------------------------------------------------ ana döngü
    def run(self) -> RunResult:
        cfg, topo, rng = self.cfg, self.topo, self.rng
        n, bs, k = cfg.n_nodes, topo.bs_index, cfg.packet_bits
        D = topo.dist
        max_rounds = cfg.n_rounds
        self.cost = {"cluster_s": 0.0, "route_s": 0.0, "epochs": 0, "evals": 0, "route_fitness": [],
                     "disconnected": 0, "n_routes": 0, "hops": [], "member_d": [], "member_oor": 0,
                     "n_members": 0}

        rec = {key: [] for key in ("generated", "delivered", "delay_sum", "energy", "alive", "n_ch")}
        delays_all: list[float] = []
        death_round = np.full(n, np.nan)
        need_recluster, epoch, since = True, 0, 0

        for t in range(max_rounds):
            alive = self.energy > 0
            newly_dead = ~alive & np.isnan(death_round)
            death_round[newly_dead] = t
            if not alive.any():
                break

            if need_recluster or since >= cfg.epoch_len:
                self._recluster(alive, epoch)
                epoch += 1
                since = 0
                need_recluster = False
            since += 1
            self.spent_round = 0.0

            gen = self.traffic.generate(t, alive)
            heads = [int(h) for h in np.flatnonzero(self.ch & alive)]
            buffers: dict[int, list[float]] = {h: [] for h in heads}
            ch_queue = {h: 0 for h in heads}

            # Üye → CH
            members = np.flatnonzero(gen & ~self.ch)
            rng.shuffle(members)
            for i in members:
                h = int(self.parent[i])
                if h < 0 or not alive[h]:
                    continue
                d = D[i, h]
                self._spend(i, float(e_tx(cfg, k, d)))
                self._spend(h, e_rx(cfg, k))
                ok = rng.random() < p_success(cfg, d)
                self._ack(i, ok)
                delay = float(hop_delay(cfg, d, ch_queue[h]))
                ch_queue[h] += 1
                if ok:
                    buffers[h].append(delay)
            for h in heads:
                if gen[h]:
                    buffers[h].append(0.0)

            # CH → BS
            relay_load = np.zeros(n + 1, dtype=int)
            delivered = 0
            delay_sum = 0.0
            order = [h for h in heads if buffers[h]]
            rng.shuffle(order)
            for h in order:
                readings = buffers[h]
                self._spend(h, cfg.e_da * k * len(readings))
                path = self.routes[h].path
                if any(v < n and not alive[v] for v in path[1:]):
                    self._reroute(h, alive)
                    path = self.routes[h].path
                route_delay, ok = 0.0, True
                for u, v in zip(path[:-1], path[1:]):
                    d = D[u, v]
                    self._spend(u, float(e_tx(cfg, k, d)))
                    if v != bs:
                        self._spend(v, e_rx(cfg, k))
                    route_delay += float(hop_delay(cfg, d, relay_load[u]))
                    relay_load[u] += 1
                    ok = rng.random() < p_success(cfg, d)
                    self._ack(u, ok)
                    if not ok:
                        break
                if ok:
                    delivered += len(readings)
                    for dl in readings:
                        delays_all.append(dl + route_delay)
                        delay_sum += dl + route_delay

            rec["generated"].append(int(gen.sum()))
            rec["delivered"].append(delivered)
            rec["delay_sum"].append(delay_sum)
            rec["energy"].append(self.spent_round)
            rec["alive"].append(int(alive.sum()))
            rec["n_ch"].append(len(heads))

            # CH enerji eşiği (makale Algoritma 1, satır 49–54)
            for h in heads:
                if self.energy[h] < cfg.ch_energy_drop * self.epoch_energy[h]:
                    need_recluster = True
                    break

            if not cfg.run_until_dead and t + 1 >= max_rounds:
                break

        alive_final = self.energy > 0
        death_round[~alive_final & np.isnan(death_round)] = len(rec["alive"])
        per_round = {key: np.asarray(v, dtype=float) for key, v in rec.items()}
        return RunResult(self._summarize(per_round, delays_all, death_round), per_round)

    # ------------------------------------------------------------------ özet
    def _summarize(self, pr: dict, delays: list[float], death_round: np.ndarray) -> dict:
        cfg, c = self.cfg, self.cost
        gen, dlv, energy = pr["generated"].sum(), pr["delivered"].sum(), pr["energy"].sum()
        rounds = len(pr["generated"])
        bits = dlv * cfg.packet_bits
        dr = np.sort(death_round[~np.isnan(death_round)])

        def nth_death(frac):
            need = int(np.ceil(frac * cfg.n_nodes))
            return float(dr[need - 1]) if dr.size >= need else np.nan

        return {
            "rounds": rounds,
            "pdr": dlv / gen if gen else np.nan,
            "delay_ms": 1e3 * float(np.mean(delays)) if delays else np.nan,
            "throughput_bps": bits / (rounds * cfg.t_round) if rounds else np.nan,
            "ee_bit_per_j": bits / energy if energy > 0 else np.nan,
            "energy_j": energy,
            "generated": int(gen),
            "delivered": int(dlv),
            "n_ch_mean": float(pr["n_ch"].mean()) if rounds else np.nan,
            "route_hops_mean": float(np.mean(c["hops"])) if c["hops"] else np.nan,
            "route_fitness_mean": float(np.mean(c["route_fitness"])) if c["route_fitness"] else np.nan,
            "disconnected_ch_frac": c["disconnected"] / c["n_routes"] if c["n_routes"] else np.nan,
            "member_dist_mean": float(np.mean(c["member_d"])) if c["member_d"] else np.nan,
            "member_out_of_range_frac": c["member_oor"] / c["n_members"] if c["n_members"] else np.nan,
            "cluster_ms_per_epoch": 1e3 * c["cluster_s"] / max(c["epochs"], 1),
            "route_ms_per_epoch": 1e3 * c["route_s"] / max(c["epochs"], 1),
            "fitness_evals_per_epoch": c["evals"] / max(c["epochs"], 1),
            "fnd": nth_death(1 / cfg.n_nodes),
            "hnd": nth_death(0.5),
            "lnd": nth_death(1.0),
        }
