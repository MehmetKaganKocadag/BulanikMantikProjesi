"""CH uygunluk skoru için bulanık çıkarım sistemi.

Makaledeki adımlar:
    Denk. 9  — ateşleme gücü: α_k = min(μ_Er, μ_DBS, μ_Nd, μ_Ls)
    Denk. 10 — CH_score = Σ α_k·z_k·w_k / Σ α_k·w_k
               (z_k: k. kuralın çıktı kümesinin ağırlık merkezi)

Denk. 10'a makalede "centroid method" denir, ancak formül ağırlıklı ortalama
(height / Sugeno-tipi) durulaştırmadır. Varsayılan `defuzz="weighted_average"`
makaleyi birebir uygular. `defuzz="centroid"` ise gerçek Mamdani centroid'ini
(kırpılmış çıktı kümelerinin max-birleşiminin ağırlık merkezi) hesaplar;
bu seçenek özgün katkı K2'deki karşılaştırma için vardır.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .membership import ThreeTermPartition, tri
from .rulebase import INPUTS, OUTPUT_TERMS, Rule, generate_rules


@dataclass
class OutputSet:
    """[0, 1] evreninde 5 eşit aralıklı çıktı terimi (tepe noktaları 0, .25, .5, .75, 1)."""

    resolution: int = 1001
    grid: np.ndarray = field(init=False)
    mfs: np.ndarray = field(init=False)  # şekil (5, resolution)
    centroids: np.ndarray = field(init=False)  # z_k değerleri, şekil (5,)

    def __post_init__(self) -> None:
        self.grid = np.linspace(0.0, 1.0, self.resolution)
        peaks = np.linspace(0.0, 1.0, len(OUTPUT_TERMS))
        h = peaks[1] - peaks[0]
        # Uç terimler evrenin sınırında kesilen üçgenlerdir.
        self.mfs = np.stack([tri(self.grid, p - h, p, p + h) for p in peaks])
        self.centroids = (self.mfs * self.grid).sum(axis=1) / self.mfs.sum(axis=1)


class FuzzyCHSystem:
    """4 girdili CH uygunluk FIS'i.

    partitions : her girdi için bir ThreeTermPartition (statik ya da adaptif)
    rules      : kural listesi (varsayılan: generate_rules())
    defuzz     : "weighted_average" (makale Denk. 10) ya da "centroid" (Mamdani)
    """

    def __init__(
        self,
        partitions: dict[str, ThreeTermPartition],
        rules: list[Rule] | None = None,
        defuzz: str = "weighted_average",
        output: OutputSet | None = None,
    ) -> None:
        missing = set(INPUTS) - set(partitions)
        if missing:
            raise ValueError(f"Eksik girdi bölümlemesi: {sorted(missing)}")
        if defuzz not in ("weighted_average", "centroid"):
            raise ValueError(f"Bilinmeyen durulaştırma: {defuzz}")
        self.partitions = partitions
        self.rules = rules if rules is not None else generate_rules()
        self.defuzz = defuzz
        self.output = output if output is not None else OutputSet()

        self._antecedents = np.array([r.antecedent for r in self.rules])  # (R, 4)
        self._consequents = np.array([r.consequent for r in self.rules])  # (R,)
        self.rule_weights = np.array([r.weight for r in self.rules], dtype=float)  # w_k

    # ---- adımlar -----------------------------------------------------------
    def fuzzify(self, X: np.ndarray) -> list[np.ndarray]:
        """X şekli (n, 4) → her girdi için (n, 3) üyelik matrisi."""
        X = np.atleast_2d(np.asarray(X, dtype=float))
        return [self.partitions[name].memberships(X[:, i]) for i, name in enumerate(INPUTS)]

    def firing_strengths(self, X: np.ndarray) -> np.ndarray:
        """Denk. 9: α_k = min_i μ_i. Çıktı şekli (n, R)."""
        mu = self.fuzzify(X)
        per_input = [mu[i][:, self._antecedents[:, i]] for i in range(len(INPUTS))]
        return np.minimum.reduce(per_input)

    def score(self, X: np.ndarray) -> np.ndarray:
        """Her düğüm için CH_score ∈ [0, 1]. X şekli (n, 4), sütunlar INPUTS sırasında."""
        alpha = self.firing_strengths(X)
        w = self.rule_weights
        if self.defuzz == "weighted_average":
            z = self.output.centroids[self._consequents]  # (R,)
            num = alpha @ (z * w)
            den = alpha @ w
            return np.divide(num, den, out=np.full_like(num, 0.5), where=den > 1e-12)

        # Mamdani: her çıktı terimi için en güçlü kuralın ateşleme gücü (max),
        # terim MF'sinin bu seviyede kırpılması, max-birleşim ve centroid.
        n_out = len(self.output.centroids)
        strength = np.zeros((alpha.shape[0], n_out))
        for t in range(n_out):
            mask = self._consequents == t
            if mask.any():
                strength[:, t] = (alpha[:, mask] * w[mask]).max(axis=1)
        clipped = np.minimum(strength[:, :, None], self.output.mfs[None, :, :])
        agg = clipped.max(axis=1)  # (n, G)
        num = agg @ self.output.grid
        den = agg.sum(axis=1)
        return np.divide(num, den, out=np.full_like(num, 0.5), where=den > 1e-12)

    # ---- yardımcılar --------------------------------------------------------
    def update_partitions(self, X: np.ndarray) -> None:
        """Adaptif bölümlemeleri bu turun düğüm değerleriyle günceller (statikler etkilenmez)."""
        X = np.atleast_2d(np.asarray(X, dtype=float))
        for i, name in enumerate(INPUTS):
            p = self.partitions[name]
            if hasattr(p, "update"):
                p.update(X[:, i])
