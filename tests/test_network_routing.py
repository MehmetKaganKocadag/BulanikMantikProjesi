"""Ağ modelleri, yönlendirme ve simülatör testleri.

Çalıştırma (repo kökünden):  python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from afl_wsn.clustering import FuzzyClustering, form_clusters  # noqa: E402
from afl_wsn.config import SimConfig  # noqa: E402
from afl_wsn.network import deploy, e_rx, e_tx, hop_delay, p_success  # noqa: E402
from afl_wsn.routing import (  # noqa: E402
    build_graph,
    decode,
    route_dijkstra,
    route_pso_ga,
    single_path_fitness,
)
from afl_wsn.simulator import Simulation  # noqa: E402
from afl_wsn.traffic import TrafficSource, synthetic_stream  # noqa: E402


def all_simple_paths(g, src):
    """Küçük grafiklerde kaba kuvvet: src'den BS'ye bütün basit yollar."""
    out, stack = [], [(src, [src])]
    while stack:
        u, path = stack.pop()
        if u == g.bs:
            out.append(path)
            continue
        for v in np.flatnonzero(g.adj[u]):
            if v not in path:
                stack.append((int(v), path + [int(v)]))
    return out


class TestRadioAndLink(unittest.TestCase):
    def setUp(self):
        self.cfg = SimConfig()

    def test_first_order_radio_model(self):
        k = 4096
        # 25 m: 4096 · (50 nJ + 100 pJ · 625) = 4096 · 112.5 nJ
        self.assertAlmostEqual(float(e_tx(self.cfg, k, 25.0)), k * 112.5e-9, places=12)
        self.assertAlmostEqual(e_rx(self.cfg, k), k * 50e-9, places=12)

    def test_link_probability_values(self):
        p = p_success(self.cfg, [10, 20, 25, 30, 40])
        np.testing.assert_allclose(p, [0.979, 0.946, 0.824, 0.49, 0.034], atol=2e-3)

    def test_hop_delay(self):
        t = 4096 / 250e3
        self.assertAlmostEqual(float(hop_delay(self.cfg, 0.0)), t + 1e-3)
        self.assertAlmostEqual(float(hop_delay(self.cfg, 0.0, 2)), 3 * t + 1e-3)


class TestRouting(unittest.TestCase):
    def _graph(self, n, seed):
        cfg = SimConfig().with_(n_nodes=n)
        topo = deploy(cfg, np.random.default_rng(seed))
        alive = np.ones(n, dtype=bool)
        ls = np.random.default_rng(seed + 100).uniform(0.7, 1.0, n)
        return cfg, topo, build_graph(topo, alive, ls, cfg)

    def test_decode_produces_valid_paths(self):
        cfg, topo, g = self._graph(20, 3)
        src = int(np.argmax(topo.dist[:20, 20]))  # BS'ye en uzak düğüm
        keys = np.random.default_rng(0).uniform(0, 10, (50, g.m))
        paths, valid = decode(keys, src, g)
        for row, ok in zip(paths, valid):
            p = [x for x in row if x >= 0]
            self.assertEqual(p[0], src)
            self.assertEqual(len(p), len(set(p)))  # döngü yok
            for u, v in zip(p[:-1], p[1:]):
                self.assertTrue(g.adj[u, v])
            self.assertEqual(ok, p[-1] == g.bs)

    def test_pso_ga_near_brute_force_optimum(self):
        # PSO-GA sezgiseldir; her durumda optimumu bulması beklenmez. Ölçülen oran
        # (15 topoloji, 12 düğüm): 69/71. Burada en az %90 isteniyor.
        found = total = 0
        for seed in range(15):
            cfg, topo, g = self._graph(12, seed)
            for src in range(12):
                paths = all_simple_paths(g, src)
                if not paths or len(paths) > 5000:
                    continue
                best = min(single_path_fitness(p, g, cfg) for p in paths)
                res = route_pso_ga(src, g, cfg, np.random.default_rng(seed))
                total += 1
                found += res.fitness <= best + 1e-9
        self.assertGreater(total, 20)
        self.assertGreaterEqual(found / total, 0.9, f"PSO-GA optimumu {found}/{total} durumda buldu")

    def test_dijkstra_never_better_than_true_optimum(self):
        cfg, topo, g = self._graph(12, 5)
        for src in range(12):
            paths = all_simple_paths(g, src)
            if not paths:
                continue
            best = min(single_path_fitness(p, g, cfg) for p in paths)
            self.assertGreaterEqual(route_dijkstra(src, g, cfg).fitness, best - 1e-9)


class TestClusteringAndSimulation(unittest.TestCase):
    def test_every_alive_node_has_a_head_in_range(self):
        cfg = SimConfig().with_(n_nodes=50)
        topo = deploy(cfg, np.random.default_rng(1))
        alive = np.ones(50, dtype=bool)
        ch = FuzzyClustering(cfg).select(np.full(50, 2.0), np.ones(50), alive, topo, None, 0)
        parent, ch = form_clusters(ch, alive, topo, cfg)
        for i in range(50):
            self.assertTrue(ch[parent[i]])
            self.assertLessEqual(topo.dist[i, parent[i]], cfg.comm_range + 1e-9)
        # açgözlü seçim: hiçbir iki seçilmiş CH birbirinin menzilinde değil
        heads = np.flatnonzero(ch)
        d = topo.dist[np.ix_(heads, heads)] + np.eye(heads.size) * 1e9
        self.assertTrue((d > cfg.comm_range).all())

    def test_energy_accounting(self):
        cfg = SimConfig().with_(n_nodes=20, n_rounds=30)
        stream = synthetic_stream(np.random.default_rng(0))
        sim = Simulation(cfg, stream, seed=4)
        res = sim.run()
        spent_nodes = cfg.n_nodes * cfg.e_init - sim.energy.sum()
        self.assertAlmostEqual(spent_nodes, res.summary["energy_j"], places=9)

    def test_perfect_links_deliver_everything_when_connected(self):
        cfg = SimConfig().with_(n_nodes=60, n_rounds=20, p_max=1.0, d50=1e6, sigma=1.0,
                                traffic_mode="periodic", routing="dijkstra")
        sim = Simulation(cfg, synthetic_stream(np.random.default_rng(0)), seed=2)
        res = sim.run()
        if res.summary["disconnected_ch_frac"] == 0:
            self.assertAlmostEqual(res.summary["pdr"], 1.0)

    def test_periodic_traffic_all_alive_send(self):
        cfg = SimConfig().with_(traffic_mode="periodic")
        ts = TrafficSource(np.zeros((10, 2)), cfg, np.random.default_rng(0))
        alive = np.ones(cfg.n_nodes, dtype=bool)
        alive[3] = False
        np.testing.assert_array_equal(ts.generate(0, alive), alive)


if __name__ == "__main__":
    unittest.main()
