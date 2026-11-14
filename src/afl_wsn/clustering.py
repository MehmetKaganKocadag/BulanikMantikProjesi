"""Küme başı (CH) seçimi ve küme oluşumu.

* FuzzyClustering — makalenin AFL yöntemi (adaptive=True) ve statik bulanık
  karşılaştırması (adaptive=False). Girdiler Denk. 2–5, çıkarım Denk. 9–10,
  seçim: yerel bölgesinde en yüksek skor (CP2 §4.7).
* LeachClustering — klasik LEACH eşik fonksiyonu (Heinzelman et al., 2000).
* KMeansClustering — konumlar üzerinde k-means; her kümenin CH'si o kümedeki bir
  düğümdür. Makale şekillerindeki merkez tabanlı görüntünün karşılığı (CP1 T24).
* form_clusters — CH olmayan düğümleri menzildeki en iyi CH'ye bağlar; menzilinde
  CH olmayan düğüm kendi kümesinin CH'si olur.

`cfg.n_ch > 0` iken CH sayısı sabittir ("5/20 = küme sayısı" yorumu, CP3 §11):
bulanık seçim en yüksek skorlu K düğümü birbirinden en az r = A / sqrt(π·K) uzakta
olacak biçimde seçer, her düğüm de menzil dışında kalsa bile en yakın CH'ye katılır.
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
        if cfg.n_ch > 0:
            return _top_k_spread(order, topo, cfg)
        within = topo.dist[:n, :n] <= cfg.comm_range
        ch = np.zeros(n, dtype=bool)
        for i in order:
            if not (within[i] & ch).any():
                ch[i] = True
        return ch


def separation(cfg: SimConfig) -> float:
    """K dairenin alanı kaplaması için gereken yarıçap: K·π·r² = A."""
    return cfg.area / np.sqrt(np.pi * cfg.n_ch)


def _top_k_spread(order: np.ndarray, topo, cfg: SimConfig) -> np.ndarray:
    """Sabit K: sıralı adaylardan birbirine r'den yakın olmayan ilk K düğüm; eksik kalırsa sıradakiler."""
    n, k = topo.n, cfg.n_ch
    far = topo.dist[:n, :n] >= separation(cfg)
    ch = np.zeros(n, dtype=bool)
    for i in order:
        if ch.sum() >= k:
            break
        if far[i, ch].all():
            ch[i] = True
    for i in order:  # aralık koşulu K düğüm bırakmadıysa en yüksek skorlularla tamamla
        if ch.sum() >= k:
            break
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


class KMeansClustering:
    """k-means (k-means++ başlangıçlı Lloyd) ile K küme; CH = kümedeki en yüksek enerjili düğüm,
    eşitlikte merkeze en yakın olan. Merkezler `centroids` içinde saklanır (çizim için)."""

    def __init__(self, cfg: SimConfig, n_iter: int = 50) -> None:
        if cfg.n_ch <= 0:
            raise ValueError("kmeans kümelemesi n_ch > 0 gerektirir")
        self.cfg = cfg
        self.n_iter = n_iter
        self.centroids: np.ndarray | None = None
        self._cache: tuple[bytes, np.ndarray, np.ndarray] | None = None

    def _kmeans(self, X: np.ndarray, k: int, rng) -> tuple[np.ndarray, np.ndarray]:
        C = X[[rng.integers(len(X))]]
        while len(C) < k:  # k-means++
            d2 = ((X[:, None, :] - C[None]) ** 2).sum(-1).min(1)
            if d2.sum() == 0:
                C = np.vstack([C, X[rng.integers(len(X))]])
            else:
                C = np.vstack([C, X[rng.choice(len(X), p=d2 / d2.sum())]])
        for _ in range(self.n_iter):
            lab = ((X[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
            newC = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
            if np.allclose(newC, C):
                break
            C = newC
        lab = ((X[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
        return C, lab

    def select(self, energy, ls, alive, topo, rng, epoch: int) -> np.ndarray:
        cfg, n = self.cfg, topo.n
        cand = np.flatnonzero(alive & (energy / cfg.e_init >= cfg.ch_min_energy))
        ch = np.zeros(n, dtype=bool)
        if cand.size == 0:
            return ch
        key = cand.tobytes()
        if self._cache is None or self._cache[0] != key:  # konumlar sabit: aday kümesi değişince yeniden
            k = min(cfg.n_ch, cand.size)
            C, lab = self._kmeans(topo.pos[cand], k, rng)
            self._cache = (key, C, lab)
        _, C, lab = self._cache
        self.centroids = C
        for j in range(len(C)):
            members = cand[lab == j]
            if members.size == 0:
                continue
            dc = np.linalg.norm(topo.pos[members] - C[j], axis=1)
            ch[members[np.lexsort((dc, -energy[members]))[0]]] = True
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
    if cfg.n_ch > 0 and elected.any():  # sabit K: herkes en yakın CH'ye (menzil dışında olsa bile)
        heads = np.flatnonzero(elected)
        for i in np.flatnonzero(alive & ~elected):
            parent[i] = heads[np.argmin(d[i, heads])]
        return parent, ch
    for i in np.flatnonzero(alive & ~elected):
        heads = np.flatnonzero(elected & (d[i] <= cfg.comm_range))
        if heads.size == 0:
            ch[i] = True
            parent[i] = i
        else:
            parent[i] = heads[np.argmax(p_success(cfg, d[i, heads]))]
    return parent, ch
