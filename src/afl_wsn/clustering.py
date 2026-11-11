"""Küme başı (CH) seçimi ve küme oluşumu.

* FuzzyClustering — makalenin AFL yöntemi (adaptive=True) ve statik bulanık
  karşılaştırması (adaptive=False). Girdiler Denk. 2–5, çıkarım Denk. 9–10,
  seçim: yerel bölgesinde en yüksek skor (CP2 §4.7).
* LeachClustering — klasik LEACH eşik fonksiyonu (Heinzelman et al., 2000).
* form_clusters — CH olmayan düğümleri menzildeki en iyi CH'ye bağlar; menzilinde
  CH olmayan düğüm kendi kümesinin CH'si olur.
"""

from __future__ import annotations

import numpy as np

from .config import SimConfig
from .fuzzy import INPUTS, AdaptivePartition, FuzzyCHSystem, static_partition
from .network.link import p_success


def fuzzy_inputs(energy, ls, alive, topo, cfg: SimConfig) -> np.ndarray:
    """Denk. 2–5: her düğüm için [E_r, D_BS, N_d, L_s] (şekil (N, 4))."""
    n = topo.n
    d = topo.dist[:n, :n]
    er = np.clip(energy / cfg.e_init, 0.0, 1.0)
    dbs = topo.dist[:n, n] / topo.d_max_bs
    neigh = (d <= cfg.comm_range) & alive[None, :] & ~np.eye(n, dtype=bool)
    nd = neigh.sum(axis=1) / n
    return np.column_stack([er, dbs, nd, ls])


class FuzzyClustering:
    def __init__(self, cfg: SimConfig, adaptive: bool = True) -> None:
        self.cfg = cfg
        self.adaptive = adaptive
        make = (lambda: AdaptivePartition(lam=cfg.mf_lambda)) if adaptive else static_partition
        self.fis = FuzzyCHSystem({name: make() for name in INPUTS}, defuzz=cfg.defuzz)
        self.last_scores: np.ndarray | None = None

    def select(self, energy, ls, alive, topo, rng, epoch: int) -> np.ndarray:
        cfg, n = self.cfg, topo.n
        X = fuzzy_inputs(energy, ls, alive, topo, cfg)
        if self.adaptive:
            self.fis.update_partitions(X[alive])
        scores = np.full(n, -np.inf)
        scores[alive] = self.fis.score(X[alive])
        self.last_scores = scores

        # "Yerel bölgesinde en yüksek skor" kuralının açgözlü uygulaması: adaylar skora göre
        # azalan sırada gezilir; menzilinde (R) henüz seçilmiş bir CH yoksa düğüm CH olur.
        # Katı yerel-maksimum kuralı, en iyi komşusu CH olmayan düğümleri tek başına
        # bırakıp çok sayıda tekil küme üretiyordu (bkz. docs/checkpoint3_baseline.md §2).
        cand = np.flatnonzero(alive & (X[:, 0] >= cfg.ch_min_energy))
        order = cand[np.lexsort((cand, -energy[cand], -scores[cand]))]  # skor > enerji > küçük indeks
        within = topo.dist[:n, :n] <= cfg.comm_range
        ch = np.zeros(n, dtype=bool)
        for i in order:
            if not (within[i] & ch).any():
                ch[i] = True
        return ch


class LeachClustering:
    """LEACH: T(n) = p / (1 - p·(r mod 1/p)), son 1/p dönemde CH olmamış düğümler için."""

    def __init__(self, cfg: SimConfig) -> None:
        self.cfg = cfg
        self.period = max(1, int(round(1.0 / cfg.leach_p)))
        self.last_ch_epoch = np.full(cfg.n_nodes, -10**9)

    def select(self, energy, ls, alive, topo, rng, epoch: int) -> np.ndarray:
        p = self.cfg.leach_p
        r = epoch % self.period
        threshold = p / (1.0 - p * r)
        eligible = alive & (epoch - self.last_ch_epoch >= self.period)
        ch = eligible & (rng.random(topo.n) < threshold)
        self.last_ch_epoch[ch] = epoch
        return ch


def form_clusters(ch: np.ndarray, alive: np.ndarray, topo, cfg: SimConfig) -> tuple[np.ndarray, np.ndarray]:
    """Her canlı düğüm için bağlı olduğu CH'yi döndürür (CH'nin kendisi = kendi indeksi).

    Menzilindeki CH'ler arasından başarı olasılığı p(d) en yüksek olana (en yakına)
    katılır; menzilinde CH yoksa kendisi CH olur. Döndürür: (parent, ch_mask).
    """
    n = topo.n
    ch = ch.copy() & alive
    parent = np.full(n, -1)
    parent[ch] = np.flatnonzero(ch)
    d = topo.dist[:n, :n]
    elected = ch.copy()  # sonradan tek başına CH olan düğümler başkalarını kabul etmez
    for i in np.flatnonzero(alive & ~elected):
        heads = np.flatnonzero(elected & (d[i] <= cfg.comm_range))
        if heads.size == 0:
            ch[i] = True
            parent[i] = i
        else:
            parent[i] = heads[np.argmax(p_success(cfg, d[i, heads]))]
    return parent, ch
