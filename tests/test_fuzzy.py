"""Bulanık çekirdek birim testleri.

Çalıştırma (repo kökünden):  python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from afl_wsn.fuzzy import (  # noqa: E402
    AdaptivePartition,
    FuzzyCHSystem,
    INPUTS,
    OutputSet,
    generate_rules,
    static_partition,
    tri,
)


def make_fis(defuzz="weighted_average"):
    return FuzzyCHSystem({name: static_partition() for name in INPUTS}, defuzz=defuzz)


class TestMembership(unittest.TestCase):
    def test_triangle_matches_eq6(self):
        x = np.array([-1.0, 0.0, 0.25, 0.5, 0.75, 1.0, 2.0])
        np.testing.assert_allclose(tri(x, 0.0, 0.5, 1.0), [0, 0, 0.5, 1, 0.5, 0, 0])

    def test_partition_is_ruspini(self):
        p = static_partition()
        x = np.linspace(-0.2, 1.2, 141)
        np.testing.assert_allclose(p.memberships(x).sum(axis=-1), 1.0)

    def test_extremes_are_fully_low_or_high(self):
        mu = static_partition().memberships(np.array([0.0, 1.0]))
        np.testing.assert_allclose(mu, [[1, 0, 0], [0, 0, 1]])


class TestAdaptivePartition(unittest.TestCase):
    def test_update_uses_min_median_max(self):
        p = AdaptivePartition()
        p.update([0.2, 0.4, 0.5, 0.9])
        self.assertAlmostEqual(p.a, 0.2)
        self.assertAlmostEqual(p.c, 0.9)
        self.assertAlmostEqual(p.b, 0.45)

    def test_lambda_smoothing_eq1(self):
        p = AdaptivePartition(lam=0.7)
        p.update([0.0, 0.5, 1.0])  # b = 0.5
        p.update([0.0, 0.8, 1.0])  # b_new = 0.8 → 0.7*0.5 + 0.3*0.8
        self.assertAlmostEqual(p.b, 0.59)

    def test_degenerate_distribution_keeps_min_width(self):
        p = AdaptivePartition(min_width=0.05)
        p.update([1.0, 1.0, 1.0])  # ilk turda tüm enerjiler eşit
        self.assertAlmostEqual(p.c - p.a, 0.05)
        self.assertLessEqual(p.c, 1.0)
        self.assertTrue(p.a < p.b < p.c)


class TestRuleBase(unittest.TestCase):
    def test_full_rule_base(self):
        rules = generate_rules()
        self.assertEqual(len(rules), 81)
        self.assertEqual(len({r.antecedent for r in rules}), 81)

    def test_best_and_worst_rules(self):
        by_ante = {r.antecedent: r.consequent for r in generate_rules()}
        # Yüksek enerji, düşük mesafe, yüksek yoğunluk, yüksek kararlılık → Çok Yüksek
        self.assertEqual(by_ante[(2, 0, 2, 2)], 4)
        # Düşük enerji, yüksek mesafe, düşük yoğunluk, düşük kararlılık → Çok Düşük
        self.assertEqual(by_ante[(0, 2, 0, 0)], 0)

    def test_low_energy_never_high(self):
        # Enerji ağırlığı 2 olduğundan düşük enerjili düğüm en fazla "Orta" olabilir.
        for r in generate_rules():
            if r.antecedent[0] == 0:
                self.assertLessEqual(r.consequent, 2)


class TestFIS(unittest.TestCase):
    def test_output_centroids(self):
        z = OutputSet().centroids
        np.testing.assert_allclose(z, [1 / 12, 0.25, 0.5, 0.75, 11 / 12], atol=1e-3)

    def test_monotonic_in_energy(self):
        fis = make_fis()
        e = np.linspace(0, 1, 21)
        X = np.column_stack([e, np.full(21, 0.3), np.full(21, 0.5), np.full(21, 0.8)])
        s = fis.score(X)
        self.assertTrue(np.all(np.diff(s) >= -1e-12))

    def test_monotonic_decreasing_in_distance(self):
        fis = make_fis()
        d = np.linspace(0, 1, 21)
        X = np.column_stack([np.full(21, 0.8), d, np.full(21, 0.5), np.full(21, 0.8)])
        s = fis.score(X)
        self.assertTrue(np.all(np.diff(s) <= 1e-12))

    def test_scores_in_unit_interval(self):
        rng = np.random.default_rng(0)
        X = rng.random((500, 4))
        for defuzz in ("weighted_average", "centroid"):
            s = make_fis(defuzz).score(X)
            self.assertTrue(np.all((s >= 0) & (s <= 1)))

    def test_at_least_one_rule_fires(self):
        rng = np.random.default_rng(1)
        alpha = make_fis().firing_strengths(rng.random((200, 4)))
        self.assertTrue(np.all(alpha.max(axis=1) > 0))

    def test_rule_weights_change_score(self):
        fis = make_fis()
        x = np.array([[0.5, 0.5, 0.5, 0.5]])
        before = fis.score(x)[0]
        fis.rule_weights[[r.consequent == 4 for r in fis.rules]] = 5.0
        self.assertGreater(fis.score(x)[0], before - 1e-12)


if __name__ == "__main__":
    unittest.main()
