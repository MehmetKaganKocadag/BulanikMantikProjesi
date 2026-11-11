"""CH uygunluğu için kural tabanı.

Makale kural biçimini verir ama kuralların kendisini vermez:
    IF Er is A AND DBS is B AND Nd is C AND Ls is D THEN CH suitability is Z

Bu projede tam kural tabanı (3^4 = 81 kural) belgelenmiş tek bir formülle
sistematik olarak üretilir; böylece her kural keyfi değil, açıklanabilir olur:

1. Her girdi terimine bir "iyilik" seviyesi g ∈ {0, 1, 2} verilir.
   Enerji, yoğunluk ve bağlantı kararlılığında Yüksek = 2 (iyi), mesafede
   ise ters yön: Düşük mesafe = 2 (BS'ye yakın olmak iyi).
2. Ağırlıklı toplam s = Σ v_i · g_i hesaplanır (v = girdi önem ağırlıkları).
   Varsayılan: enerji 2, diğerleri 1. Gerekçe: enerjisi tükenmek üzere olan bir
   düğümün CH olması (veri birleştirme ve iletim yükü) ağ ömrünü doğrudan
   kısaltır; bu nedenle enerji en kritik ölçüttür.
3. s, [0, 1]'e normalize edilip 5 çıktı teriminden en yakınına yuvarlanır:
   Z = round(4 · s / s_max) → {ÇD, D, O, Y, ÇY}.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

INPUTS: tuple[str, ...] = ("energy", "distance", "density", "link")
TERMS: tuple[str, ...] = ("Low", "Medium", "High")
OUTPUT_TERMS: tuple[str, ...] = ("VeryLow", "Low", "Medium", "High", "VeryHigh")

# Girdinin yüksek değeri CH olmak için iyi mi?
GOOD_WHEN_HIGH: dict[str, bool] = {
    "energy": True,
    "distance": False,  # BS'ye yakın olan tercih edilir
    "density": True,
    "link": True,
}

DEFAULT_IMPORTANCE: dict[str, float] = {
    "energy": 2.0,
    "distance": 1.0,
    "density": 1.0,
    "link": 1.0,
}


@dataclass(frozen=True)
class Rule:
    antecedent: tuple[int, ...]  # INPUTS sırasıyla terim indeksleri (0=Low, 1=Medium, 2=High)
    consequent: int  # OUTPUT_TERMS indeksi
    weight: float = 1.0  # w_k (makale Denk. 8, 10)

    def describe(self) -> str:
        parts = [f"{name} is {TERMS[t]}" for name, t in zip(INPUTS, self.antecedent)]
        return "IF " + " AND ".join(parts) + f" THEN CH is {OUTPUT_TERMS[self.consequent]}"


def goodness(input_name: str, term_index: int) -> int:
    """Terimin CH olmak açısından iyilik seviyesi: 0 (kötü) .. 2 (iyi)."""
    return term_index if GOOD_WHEN_HIGH[input_name] else 2 - term_index


def generate_rules(importance: dict[str, float] | None = None) -> list[Rule]:
    """81 kuralın tamamını üretir."""
    v = DEFAULT_IMPORTANCE if importance is None else importance
    s_max = 2.0 * sum(v[name] for name in INPUTS)
    n_out = len(OUTPUT_TERMS) - 1
    rules = []
    for antecedent in itertools.product(range(len(TERMS)), repeat=len(INPUTS)):
        s = sum(v[name] * goodness(name, t) for name, t in zip(INPUTS, antecedent))
        # round-half-up (Python'un round()'u bankacı yuvarlaması yapar)
        consequent = int(n_out * s / s_max + 0.5 + 1e-12)
        rules.append(Rule(antecedent=tuple(antecedent), consequent=consequent))
    return rules
