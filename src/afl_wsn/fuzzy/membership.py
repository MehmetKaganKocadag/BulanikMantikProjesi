"""Üyelik fonksiyonları ve (adaptif) üç terimli bölümlemeler.

Makale (Denk. 6) üçgen MF kullanır ve her dilsel değişkenin Düşük/Orta/Yüksek
terimlerinin (a, b, c) sınırlarının her turda güncellendiğini söyler:
    a = aktif düğümlerdeki minimum değer
    c = maksimum değer
    b = ortalama ya da medyan, λ ile yumuşatılmış (Denk. 1)

Bu projede tek bir (a, b, c) üçlüsü üç terimi birlikte tanımlar:
    Düşük  = sol omuz   : x <= a için 1, b'de 0
    Orta   = üçgen      : (a, b, c)
    Yüksek = sağ omuz   : b'de 0, x >= c için 1

Uç terimlerin omuz (açık uçlu) olması gerekir. Saf üçgen kullanılsaydı c = max
seçildiğinde en yüksek değerli düğümün "Yüksek" üyeliği μ(c) = 0 olurdu
(bkz. docs/checkpoint2_uygulama_plani.md, bölüm 4.2). Bu bölümleme [a, c]
aralığında Ruspini bölümlemesidir: üç üyeliğin toplamı her x için 1'dir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

_EPS = 1e-9


def tri(x, a: float, b: float, c: float) -> np.ndarray:
    """Üçgen MF μ(x; a, b, c) — makale Denk. 6."""
    x = np.asarray(x, dtype=float)
    left = (x - a) / max(b - a, _EPS)
    right = (c - x) / max(c - b, _EPS)
    return np.clip(np.minimum(left, right), 0.0, 1.0)


def left_shoulder(x, a: float, b: float) -> np.ndarray:
    """x <= a için 1, a..b arasında doğrusal azalan, x >= b için 0."""
    x = np.asarray(x, dtype=float)
    return np.clip((b - x) / max(b - a, _EPS), 0.0, 1.0)


def right_shoulder(x, b: float, c: float) -> np.ndarray:
    """x <= b için 0, b..c arasında doğrusal artan, x >= c için 1."""
    x = np.asarray(x, dtype=float)
    return np.clip((x - b) / max(c - b, _EPS), 0.0, 1.0)


@dataclass
class ThreeTermPartition:
    """(a, b, c) ile tanımlanan Düşük / Orta / Yüksek bölümlemesi."""

    a: float
    b: float
    c: float

    def memberships(self, x) -> np.ndarray:
        """Girdi şekli (...) → çıktı şekli (..., 3): [Düşük, Orta, Yüksek]."""
        x = np.asarray(x, dtype=float)
        return np.stack(
            [
                left_shoulder(x, self.a, self.b),
                tri(x, self.a, self.b, self.c),
                right_shoulder(x, self.b, self.c),
            ],
            axis=-1,
        )

    def params(self) -> tuple[float, float, float]:
        return (self.a, self.b, self.c)


def static_partition() -> ThreeTermPartition:
    """Adaptif olmayan (statik) bölümleme: [0, 1] evreninde sabit (0, 0.5, 1)."""
    return ThreeTermPartition(0.0, 0.5, 1.0)


@dataclass
class AdaptivePartition(ThreeTermPartition):
    """Her turda düğüm değerlerinin dağılımına göre güncellenen bölümleme.

    Parametreler
    ------------
    lam : Denk. 1'deki yumuşatma katsayısı λ (yalnızca merkez b'ye uygulanır).
    center : "median" ya da "mean" (makale ikisini de anar; varsayılan medyan,
        çünkü aykırı değerlere daha dayanıklıdır).
    min_width : c - a için alt sınır. Tüm düğümler aynı değere sahipken
        (ör. ilk turda bütün enerjiler 1.0) bölümlemenin çökmesini önler.
    domain : Değişkenin evreni; normalize girdiler için [0, 1].
    """

    a: float = 0.0
    b: float = 0.5
    c: float = 1.0
    lam: float = 0.7
    center: str = "median"
    min_width: float = 0.05
    domain: tuple[float, float] = (0.0, 1.0)
    _initialized: bool = field(default=False, repr=False)

    def update(self, values) -> None:
        """Bir turun başında aktif düğümlerin değerleriyle (a, b, c)'yi günceller."""
        v = np.asarray(values, dtype=float)
        v = v[np.isfinite(v)]
        if v.size == 0:
            return

        a, c = float(v.min()), float(v.max())
        b_new = float(np.median(v) if self.center == "median" else v.mean())

        # Dar dağılımda bölümlemeyi minimum genişliğe aç (evren içinde kalarak).
        if c - a < self.min_width:
            mid = 0.5 * (a + c)
            lo, hi = self.domain
            a = max(lo, mid - self.min_width / 2)
            c = min(hi, a + self.min_width)
            a = c - self.min_width

        # Denk. 1: b(t+1) = λ·b(t) + (1-λ)·b_new  (ilk güncellemede b = b_new)
        b = b_new if not self._initialized else self.lam * self.b + (1 - self.lam) * b_new

        # b, (a, c) aralığının içinde kalmalı.
        margin = 0.05 * (c - a)
        b = float(np.clip(b, a + margin, c - margin))

        self.a, self.b, self.c = a, b, c
        self._initialized = True
