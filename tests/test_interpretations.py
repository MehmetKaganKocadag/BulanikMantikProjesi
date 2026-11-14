"""Sabit CH sayısı, k-means kümeleme ve veriden yerleşim testleri (CP3 §11).

Çalıştırma (repo kökünden):  python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from afl_wsn.clustering import FuzzyClustering, KMeansClustering, form_clusters, separation  # noqa: E402
from afl_wsn.config import SimConfig  # noqa: E402
from afl_wsn.network import deploy  # noqa: E402
from afl_wsn.simulator import Simulation, data_topology  # noqa: E402
from afl_wsn.traffic import DATA_DIR, DATASETS, TrafficSource, synthetic_stream  # noqa: E402

HAVE_DATA = all((DATA_DIR / spec["file"]).exists() for spec in DATASETS.values())


def setup(k, n=100, seed=0):
    cfg = SimConfig().with_(n_nodes=n, n_ch=k)
    topo = deploy(cfg, np.random.default_rng(seed))
    return cfg, topo, np.ones(n, dtype=bool), np.full(n, cfg.e_init)


class TestFixedK(unittest.TestCase):
    def test_fuzzy_selects_exactly_k_spread_heads(self):
        for k in (5, 20):
            cfg, topo, alive, energy = setup(k)
            ch = FuzzyClustering(cfg).select(energy, np.ones(100), alive, topo, None, 0)
            self.assertEqual(ch.sum(), k)
            if k == 5:  # 100 düğümde 5 CH için aralık koşulu her zaman sağlanabiliyor
                h = np.flatnonzero(ch)
                d = topo.dist[np.ix_(h, h)] + np.eye(k) * 1e9
                self.assertTrue((d >= separation(cfg)).all())

    def test_every_node_joins_nearest_head_without_new_singletons(self):
        cfg, topo, alive, energy = setup(5)
        ch = FuzzyClustering(cfg).select(energy, np.ones(100), alive, topo, None, 0)
        parent, ch2 = form_clusters(ch, alive, topo, cfg)
        np.testing.assert_array_equal(ch, ch2)  # sabit K: tekil CH eklenmez
        heads = np.flatnonzero(ch)
        for i in np.flatnonzero(~ch):
            self.assertEqual(parent[i], heads[np.argmin(topo.dist[i, heads])])

    def test_kmeans_heads_are_nodes_one_per_cluster(self):
        cfg, topo, alive, energy = setup(20)
        km = KMeansClustering(cfg)
        ch = km.select(energy, np.ones(100), alive, topo, np.random.default_rng(0), 0)
        self.assertEqual(ch.sum(), 20)
        self.assertEqual(km.centroids.shape, (20, 2))
        # her merkez için en yakın CH farklı (kümeler ayrık)
        heads = np.flatnonzero(ch)
        nearest = {int(heads[np.argmin(np.linalg.norm(topo.pos[heads] - c, axis=1))]) for c in km.centroids}
        self.assertEqual(len(nearest), 20)

    def test_kmeans_requires_k(self):
        with self.assertRaises(ValueError):
            KMeansClustering(SimConfig())

    def test_fixed_k_simulation_runs(self):
        cfg = SimConfig().with_(n_nodes=60, n_ch=5, clustering="kmeans", routing="dijkstra", n_rounds=15)
        res = Simulation(cfg, synthetic_stream(np.random.default_rng(0)), seed=1).run()
        self.assertEqual(res.summary["n_ch_mean"], 5.0)
        self.assertGreaterEqual(res.summary["member_out_of_range_frac"], 0.0)


class TestDataPlacement(unittest.TestCase):
    def test_traffic_offsets_are_used(self):
        cfg = SimConfig().with_(n_nodes=3)
        ts = TrafficSource(np.zeros((10, 2)), cfg, np.random.default_rng(0), offsets=np.array([4, 0, 9]))
        np.testing.assert_array_equal(ts.offsets, [4, 0, 9])

    @unittest.skipUnless(HAVE_DATA, "veri dosyaları data/ altında yok")
    def test_positions_inside_area_and_deterministic(self):
        cfg = SimConfig().with_(n_nodes=100, placement="data")
        for name in DATASETS:
            topo, idx = data_topology(cfg, name, seed=3)
            self.assertEqual(topo.pos.shape, (100, 2))
            self.assertTrue(((topo.pos >= 0) & (topo.pos <= cfg.area)).all())
            self.assertEqual(len(set(idx.tolist())), 100)  # tekrarsız kayıt seçimi
            topo2, idx2 = data_topology(cfg, name, seed=3)
            np.testing.assert_array_equal(idx, idx2)
            np.testing.assert_array_equal(topo.pos, topo2.pos)


if __name__ == "__main__":
    unittest.main()
