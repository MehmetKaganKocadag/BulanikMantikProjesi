"""Checkpoint 4 katkılarının testleri: hibrit adaptif MF (K1), heterojen enerji, Dijkstra
başlatmalı PSO-GA (K6).

Çalıştırma (repo kökünden):  python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from afl_wsn.clustering import FuzzyClustering, form_clusters  # noqa: E402
from afl_wsn.config import SimConfig  # noqa: E402
from afl_wsn.fuzzy import AdaptivePartition  # noqa: E402
from afl_wsn.network import deploy  # noqa: E402
from afl_wsn.routing import (  # noqa: E402
    build_graph,
    decode,
    route_dijkstra,
    route_pso_ga_ds,
    seed_keys,
)
from afl_wsn.simulator import Simulation  # noqa: E402
from afl_wsn.traffic import synthetic_stream  # noqa: E402


class TestHybridPartition(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.batches = [rng.uniform(0.9, 0.98, 30), rng.uniform(0.6, 0.95, 30), rng.uniform(0.1, 0.9, 30)]

    def run_batches(self, shrink):
        p = AdaptivePartition(shrink=shrink)
        out = []
        for v in self.batches:
            p.update(v)
            out.append(p.params())
        return np.array(out)

    def test_rho_zero_is_paper_adaptive(self):
        ref = AdaptivePartition()
        for v, row in zip(self.batches, self.run_batches(0.0)):
            ref.update(v)
            np.testing.assert_allclose(ref.params(), row)

    def test_rho_one_is_static(self):
        for row in self.run_batches(1.0):
            np.testing.assert_allclose(row, (0.0, 0.5, 1.0))

    def test_rho_half_is_midpoint_and_ordered(self):
        a0, a1, h = self.run_batches(0.0), self.run_batches(1.0), self.run_batches(0.5)
        np.testing.assert_allclose(h, 0.5 * (a0 + a1))
        self.assertTrue((h[:, 0] < h[:, 1]).all() and (h[:, 1] < h[:, 2]).all())

    def test_ruspini_kept(self):
        p = AdaptivePartition(shrink=0.5)
        p.update(self.batches[0])
        x = np.linspace(0, 1, 101)
        np.testing.assert_allclose(p.memberships(x).sum(axis=-1), 1.0, atol=1e-12)


class TestHeterogeneousEnergy(unittest.TestCase):
    def test_initial_energy_range_and_pairing(self):
        cfg = SimConfig().with_(n_nodes=40, e_init=0.25, e_init_spread=0.5)
        s1 = Simulation(cfg, synthetic_stream(np.random.default_rng(0)), seed=5)
        s2 = Simulation(cfg.with_(clustering="static_fuzzy"), synthetic_stream(np.random.default_rng(0)), seed=5)
        self.assertTrue(((s1.energy >= 0.125) & (s1.energy <= 0.375)).all())
        self.assertGreater(s1.energy.std(), 0.01)
        np.testing.assert_array_equal(s1.energy, s2.energy)  # yöntemler aynı enerjilerle başlar

    def test_energy_accounting_with_spread(self):
        cfg = SimConfig().with_(n_nodes=30, e_init=0.25, e_init_spread=0.5, n_rounds=40)
        sim = Simulation(cfg, synthetic_stream(np.random.default_rng(0)), seed=2)
        res = sim.run()
        self.assertAlmostEqual(sim.e_start.sum() - sim.energy.sum(), res.summary["energy_j"], places=9)


class TestSeededPSOGA(unittest.TestCase):
    def graphs(self, n=40, count=8):
        cfg = SimConfig().with_(n_nodes=n)
        for seed in range(count):
            topo = deploy(cfg, np.random.default_rng(seed))
            alive = np.ones(n, dtype=bool)
            ch = FuzzyClustering(cfg).select(np.full(n, 2.0), np.ones(n), alive, topo, None, 0)
            _, ch = form_clusters(ch, alive, topo, cfg)
            yield cfg, build_graph(topo, alive, np.ones(n), cfg), np.flatnonzero(ch)

    def test_seed_keys_decode_to_path(self):
        rng = np.random.default_rng(0)
        checked = 0
        for cfg, g, heads in self.graphs():
            for h in heads:
                dj = route_dijkstra(int(h), g, cfg)
                if not dj.connected:
                    continue
                keys = seed_keys(dj.path, g.m, cfg.pso, rng)[None, :]
                paths, valid = decode(keys, int(h), g)
                self.assertTrue(valid[0])
                self.assertEqual([int(x) for x in paths[0] if x >= 0], dj.path)
                checked += 1
        self.assertGreater(checked, 10)

    def test_never_worse_than_dijkstra(self):
        rng = np.random.default_rng(1)
        for cfg, g, heads in self.graphs():
            for h in heads:
                dj = route_dijkstra(int(h), g, cfg)
                ds = route_pso_ga_ds(int(h), g, cfg, rng)
                self.assertLessEqual(ds.fitness, dj.fitness + 1e-12)


if __name__ == "__main__":
    unittest.main()
