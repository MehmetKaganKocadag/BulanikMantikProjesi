"""CH → BS yönlendirme: yol grafiği, uygunluk fonksiyonu, PSO-GA, Dijkstra.

Yol kodlaması (CP2 §5.1): her parçacık M = N+1 boyutlu bir öncelik (rastgele
anahtar) vektörüdür. Çözümleme: CH'den başla; menzildeki ziyaret edilmemiş canlı
komşular (ve menzildeyse BS) arasından önceliği en yüksek olana git; BS'ye
ulaşınca dur. Böylece makalenin sürekli PSO güncellemesi (Denk. 20–21) ve
Tablo 3'teki iki noktalı çaprazlama/mutasyon doğrudan uygulanabilir.

Uygunluk (Denk. 14–19, normalize; minimize edilir):
    f = α·E/E_ref + β·D/D_ref + γ·(1 − L) + δ·(1 − PDR)
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass

import numpy as np

from .config import PSOConfig, SimConfig
from .network.link import hop_delay, p_success
from .network.radio import e_rx, e_tx


# --------------------------------------------------------------------------- grafik
@dataclass
class RoutingGraph:
    adj: np.ndarray  # (M, M) bool — menzil içinde ve iki ucu da canlı
    e_edge: np.ndarray  # (M, M) J — gönderim + (alıcı BS değilse) alım enerjisi
    d_edge: np.ndarray  # (M, M) s — kuyruksuz atlama gecikmesi
    logp: np.ndarray  # (M, M) log p(d)
    ls: np.ndarray  # (M,) gönderenin bağlantı kararlılığı (BS için 1)
    bs: int
    e_ref: float
    d_ref: float

    @property
    def m(self) -> int:
        return self.adj.shape[0]


def build_graph(topo, alive: np.ndarray, ls: np.ndarray, cfg: SimConfig) -> RoutingGraph:
    n, bs = topo.n, topo.bs_index
    k = cfg.packet_bits
    D = topo.dist
    up = np.append(alive, True)
    adj = (D <= cfg.comm_range) & up[:, None] & up[None, :]
    np.fill_diagonal(adj, False)
    adj[bs, :] = False  # BS'den çıkış yok

    e_edge = e_tx(cfg, k, D) + e_rx(cfg, k)
    e_edge[:, bs] -= e_rx(cfg, k)  # BS'nin alım enerjisi ağ bütçesine dahil değil
    d_edge = hop_delay(cfg, D)
    with np.errstate(divide="ignore"):
        logp = np.log(p_success(cfg, D))
    ls_all = np.append(ls, 1.0)

    e_ref = float(e_tx(cfg, k, topo.d_max_bs))
    d_ref = float(10 * hop_delay(cfg, 0.0))
    return RoutingGraph(adj, e_edge, d_edge, logp, ls_all, bs, e_ref, d_ref)


# --------------------------------------------------------------------------- uygunluk
def path_fitness(paths: np.ndarray, valid: np.ndarray, g: RoutingGraph, cfg: SimConfig):
    """paths: (P, H+1) düğüm indeksleri, -1 dolgu. Döndürür: f (P,), bileşenler sözlüğü."""
    a, b, c, d = cfg.fitness_weights
    u, v = paths[:, :-1], paths[:, 1:]
    hop = (u >= 0) & (v >= 0)
    uu, vv = np.where(hop, u, 0), np.where(hop, v, 0)
    n_hops = hop.sum(axis=1)
    E = (g.e_edge[uu, vv] * hop).sum(axis=1)
    D = (g.d_edge[uu, vv] * hop).sum(axis=1)
    L = (g.ls[uu] * hop).sum(axis=1) / np.maximum(n_hops, 1)
    PDR = np.exp((g.logp[uu, vv] * hop).sum(axis=1))
    f = a * E / g.e_ref + b * D / g.d_ref + c * (1 - L) + d * (1 - PDR)
    f = np.where(valid, f, cfg.infeasible_fitness)
    return f, {"E": E, "D": D, "L": L, "PDR": PDR, "hops": n_hops}


def path_to_array(path: list[int], width: int) -> np.ndarray:
    arr = np.full((1, width), -1)
    arr[0, : len(path)] = path
    return arr


def single_path_fitness(path: list[int], g: RoutingGraph, cfg: SimConfig) -> float:
    f, _ = path_fitness(path_to_array(path, max(len(path), 2)), np.array([True]), g, cfg)
    return float(f[0])


# --------------------------------------------------------------------------- kodlama
def decode(keys: np.ndarray, src: int, g: RoutingGraph) -> tuple[np.ndarray, np.ndarray]:
    """Öncelik vektörlerini (P, M) yollara çevirir. Döndürür: paths (P, M), valid (P,)."""
    P, M = keys.shape
    rows = np.arange(P)
    cur = np.full(P, src)
    visited = np.zeros((P, M), dtype=bool)
    visited[:, src] = True
    paths = np.full((P, M), -1)
    paths[:, 0] = src
    done = np.zeros(P, dtype=bool)
    valid = np.zeros(P, dtype=bool)
    for step in range(1, M):
        cand = g.adj[cur] & ~visited
        cand[done] = False
        has = cand.any(axis=1)
        done |= ~has
        if done.all():
            break
        sel = np.where(cand, keys, -np.inf).argmax(axis=1)
        mv = ~done
        paths[mv, step] = sel[mv]
        visited[rows[mv], sel[mv]] = True
        cur = np.where(mv, sel, cur)
        reached = mv & (sel == g.bs)
        valid |= reached
        done |= reached
    return paths, valid


def reachable(src: int, g: RoutingGraph) -> bool:
    seen, stack = {src}, [src]
    while stack:
        u = stack.pop()
        if u == g.bs:
            return True
        for v in np.flatnonzero(g.adj[u]):
            if v not in seen:
                seen.add(int(v))
                stack.append(int(v))
    return False


# --------------------------------------------------------------------------- algoritmalar
@dataclass
class RouteResult:
    path: list[int]
    fitness: float
    evals: int
    iters: int
    seconds: float
    connected: bool
    history: list[float] | None = None


def _trim(path_row: np.ndarray) -> list[int]:
    return [int(x) for x in path_row if x >= 0]


def route_direct(src: int, g: RoutingGraph, cfg: SimConfig) -> RouteResult:
    t0 = time.perf_counter()
    path = [src, g.bs]
    return RouteResult(path, single_path_fitness(path, g, cfg), 1, 0, time.perf_counter() - t0, bool(g.adj[src, g.bs]))


def route_dijkstra(src: int, g: RoutingGraph, cfg: SimConfig) -> RouteResult:
    """Kenar maliyeti: uygunluğun toplamsal yaklaşımı (1−PDR ≈ −log p, L ortalaması yerine toplam)."""
    t0 = time.perf_counter()
    a, b, c, d = cfg.fitness_weights
    cost = a * g.e_edge / g.e_ref + b * g.d_edge / g.d_ref + c * (1 - g.ls)[:, None] - d * g.logp
    dist = {src: 0.0}
    prev: dict[int, int] = {}
    pq = [(0.0, src)]
    while pq:
        du, u = heapq.heappop(pq)
        if u == g.bs:
            break
        if du > dist.get(u, np.inf):
            continue
        for v in np.flatnonzero(g.adj[u]):
            nd = du + cost[u, v]
            if nd < dist.get(int(v), np.inf):
                dist[int(v)] = nd
                prev[int(v)] = u
                heapq.heappush(pq, (nd, int(v)))
    if g.bs not in dist:
        res = route_direct(src, g, cfg)
        res.seconds = time.perf_counter() - t0
        return res
    path = [g.bs]
    while path[-1] != src:
        path.append(prev[path[-1]])
    path.reverse()
    return RouteResult(path, single_path_fitness(path, g, cfg), 0, 0, time.perf_counter() - t0, True)


def _tournament(F: np.ndarray, k: int, n: int, rng) -> np.ndarray:
    idx = rng.integers(0, F.size, size=(n, k))
    return idx[np.arange(n), F[idx].argmin(axis=1)]


def _ga_offspring(X: np.ndarray, F: np.ndarray, pc: PSOConfig, rng) -> np.ndarray:
    """Turnuva seçimi + iki noktalı çaprazlama + gen başına rastgele sıfırlama mutasyonu."""
    n_off, M = pc.n_offspring, X.shape[1]
    parents = _tournament(F, pc.tournament, n_off + (n_off % 2), rng)
    kids = X[parents].copy()
    for j in range(0, kids.shape[0] - 1, 2):
        if rng.random() < pc.pc:
            i1, i2 = np.sort(rng.choice(M + 1, size=2, replace=False))
            seg = kids[j, i1:i2].copy()
            kids[j, i1:i2] = kids[j + 1, i1:i2]
            kids[j + 1, i1:i2] = seg
    kids = kids[:n_off]
    mut = rng.random(kids.shape) < pc.pm
    kids[mut] = rng.uniform(*pc.pos_range, size=mut.sum())
    return kids


def route_pso_ga(src: int, g: RoutingGraph, cfg: SimConfig, rng, record: bool = False) -> RouteResult:
    """Hibrit PSO-GA (mode="pso_ga"), yalnız PSO (mode="pso") ya da yalnız GA (mode="ga")."""
    t0 = time.perf_counter()
    pc = cfg.pso
    if not reachable(src, g):
        res = route_direct(src, g, cfg)
        res.connected, res.seconds = False, time.perf_counter() - t0
        return res

    lo, hi = pc.pos_range
    P, M = pc.n_particles, g.m

    def evaluate(K):
        paths, valid = decode(K, src, g)
        f, _ = path_fitness(paths, valid, g, cfg)
        return f, paths

    X = rng.uniform(lo, hi, size=(P, M))
    V = rng.uniform(-pc.vmax, pc.vmax, size=(P, M))
    F, paths = evaluate(X)
    evals = P
    Pb, Fb, Pb_paths = X.copy(), F.copy(), paths.copy()
    gi = int(F.argmin())
    G, Gf, G_path = X[gi].copy(), float(F[gi]), paths[gi].copy()
    history = [Gf] if record else None
    stall, it = 0, 0

    for it in range(1, pc.max_iter + 1):
        prev_best = Gf
        if pc.mode in ("pso_ga", "pso"):
            r1, r2 = rng.random((P, M)), rng.random((P, M))
            V = pc.w * V + pc.c1 * r1 * (Pb - X) + pc.c2 * r2 * (G - X)  # Denk. 20
            V = np.clip(V, -pc.vmax, pc.vmax)
            X = np.clip(X + V, lo, hi)  # Denk. 21
            F, paths = evaluate(X)
            evals += P

        if pc.mode == "ga" or (pc.mode == "pso_ga" and it % pc.ga_interval == 0):
            kids = _ga_offspring(X, F, pc, rng)
            Fk, kpaths = evaluate(kids)
            evals += kids.shape[0]
            # Elitist yer değiştirme: en kötü parçacıklar yalnızca daha iyi yavrularla değişir.
            worst = np.argsort(-F)
            best_k = np.argsort(Fk)
            for w_i, k_i in zip(worst, best_k):
                if Fk[k_i] >= F[w_i]:
                    break
                X[w_i], F[w_i], paths[w_i] = kids[k_i], Fk[k_i], kpaths[k_i]
                V[w_i] = 0.0
                Pb[w_i], Fb[w_i], Pb_paths[w_i] = kids[k_i], Fk[k_i], kpaths[k_i]

        improved = F < Fb
        Pb[improved], Fb[improved], Pb_paths[improved] = X[improved], F[improved], paths[improved]
        gi = int(Fb.argmin())
        if Fb[gi] < Gf:
            G, Gf, G_path = Pb[gi].copy(), float(Fb[gi]), Pb_paths[gi].copy()
        if record:
            history.append(Gf)
        stall = 0 if Gf < prev_best - 1e-12 else stall + 1
        if stall >= pc.patience:
            break

    return RouteResult(_trim(G_path), Gf, evals, it, time.perf_counter() - t0, True, history)


def find_route(src: int, g: RoutingGraph, cfg: SimConfig, rng) -> RouteResult:
    if cfg.routing == "direct":
        return route_direct(src, g, cfg)
    if cfg.routing == "dijkstra":
        return route_dijkstra(src, g, cfg)
    if cfg.routing in ("pso_ga", "pso", "ga"):
        return route_pso_ga(src, g, cfg.with_(pso__mode=cfg.routing), rng)
    raise ValueError(f"Bilinmeyen yönlendirme: {cfg.routing}")
