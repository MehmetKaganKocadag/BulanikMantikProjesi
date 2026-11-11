"""Checkpoint 2 — bulanık CH sisteminin tasarım çıktıları.

Üretilenler:
    results/tables/rule_base.csv              81 kuralın tamamı
    results/tables/rule_consequent_counts.csv çıktı terimi başına kural sayısı
    results/figures/cp2_mf_static.png         statik MF'ler (4 girdi + çıktı)
    results/figures/cp2_mf_adaptive.png       adaptif ve statik MF karşılaştırması (enerji)
    results/figures/cp2_control_surface.png   CH skoru yüzeyi (enerji × mesafe)
    results/figures/cp2_adaptive_vs_static.png ayırt edicilik örneği

Çalıştırma (repo kökünden):  python experiments/baseline/fis_design.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from afl_wsn.fuzzy import (  # noqa: E402
    INPUTS,
    OUTPUT_TERMS,
    TERMS,
    AdaptivePartition,
    FuzzyCHSystem,
    OutputSet,
    generate_rules,
    static_partition,
)

FIG = ROOT / "results" / "figures"
TAB = ROOT / "results" / "tables"
LABELS_TR = {
    "energy": "Kalan enerji $E_r$",
    "distance": "BS'ye uzaklık $D_{BS}$",
    "density": "Düğüm yoğunluğu $N_d$",
    "link": "Bağlantı kararlılığı $L_s$",
}
TERM_COLORS = ["#2b6cb0", "#d69e2e", "#2f855a"]
SEED = 42


def export_rules() -> pd.DataFrame:
    rules = generate_rules()
    df = pd.DataFrame(
        [
            {
                "rule": k + 1,
                **{name: TERMS[t] for name, t in zip(INPUTS, r.antecedent)},
                "ch_suitability": OUTPUT_TERMS[r.consequent],
                "weight": r.weight,
            }
            for k, r in enumerate(rules)
        ]
    )
    df.to_csv(TAB / "rule_base.csv", index=False)
    counts = df["ch_suitability"].value_counts().reindex(OUTPUT_TERMS).rename("n_rules")
    counts.to_csv(TAB / "rule_consequent_counts.csv")
    return counts


def plot_partition(ax, p, title, xs=np.linspace(0, 1, 501)):
    mu = p.memberships(xs)
    for t in range(3):
        ax.plot(xs, mu[:, t], color=TERM_COLORS[t], lw=2, label=TERMS[t])
    ax.set_title(title, fontsize=10)
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.02, 1.05)
    ax.grid(alpha=0.3)


def plot_static_mfs() -> None:
    fig, axes = plt.subplots(1, 5, figsize=(17, 3.2))
    for ax, name in zip(axes[:4], INPUTS):
        plot_partition(ax, static_partition(), LABELS_TR[name])
    axes[0].set_ylabel("Üyelik derecesi μ")
    axes[0].legend(fontsize=8, loc="center left")
    out = OutputSet()
    for k, term in enumerate(OUTPUT_TERMS):
        axes[4].plot(out.grid, out.mfs[k], lw=2, label=f"{term} (z={out.centroids[k]:.3f})")
    axes[4].set_title("Çıktı: CH uygunluğu", fontsize=10)
    axes[4].legend(fontsize=7)
    axes[4].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / "cp2_mf_static.png", dpi=150)
    plt.close(fig)


def clustered_energies(rng) -> np.ndarray:
    # Ağ bir süre çalıştıktan sonraki tipik durum: enerjiler dar bir bantta toplanır.
    return np.clip(rng.normal(0.60, 0.04, 20), 0, 1)


def plot_adaptive_mfs(energies) -> AdaptivePartition:
    ap = AdaptivePartition()
    ap.update(energies)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
    plot_partition(axes[0], static_partition(), "Statik MF (a, b, c) = (0, 0.5, 1)")
    plot_partition(
        axes[1], ap, f"Adaptif MF (a, b, c) = ({ap.a:.2f}, {ap.b:.2f}, {ap.c:.2f})"
    )
    for ax in axes:
        ax.plot(energies, np.zeros_like(energies) - 0.0, "k|", ms=14, label="Düğüm enerjileri")
        ax.set_xlabel("Kalan enerji $E_r$")
    axes[0].set_ylabel("Üyelik derecesi μ")
    axes[1].legend(fontsize=8, loc="center left")
    fig.tight_layout()
    fig.savefig(FIG / "cp2_mf_adaptive.png", dpi=150)
    plt.close(fig)
    return ap


def plot_control_surface() -> None:
    fis = FuzzyCHSystem({n: static_partition() for n in INPUTS})
    g = np.linspace(0, 1, 61)
    E, D = np.meshgrid(g, g)
    X = np.column_stack([E.ravel(), D.ravel(), np.full(E.size, 0.5), np.full(E.size, 0.5)])
    S = fis.score(X).reshape(E.shape)
    fig = plt.figure(figsize=(6.5, 5))
    ax = fig.add_subplot(projection="3d")
    ax.plot_surface(E, D, S, cmap="viridis", linewidth=0, antialiased=True)
    ax.set_xlabel("$E_r$")
    ax.set_ylabel("$D_{BS}$")
    ax.set_zlabel("CH skoru")
    ax.set_title("Kontrol yüzeyi ($N_d$ = $L_s$ = 0.5, statik MF)", fontsize=10)
    ax.view_init(elev=28, azim=-130)
    fig.tight_layout()
    fig.savefig(FIG / "cp2_control_surface.png", dpi=150)
    plt.close(fig)


def adaptive_vs_static(energies, rng) -> dict:
    """Aynı ağ durumunda statik ve adaptif FIS'in skor dağılımını karşılaştırır."""
    n = energies.size
    X = np.column_stack([energies, rng.random(n), rng.random(n) * 0.3, rng.uniform(0.85, 1.0, n)])

    static = FuzzyCHSystem({name: static_partition() for name in INPUTS})
    adaptive = FuzzyCHSystem({name: AdaptivePartition() for name in INPUTS})
    adaptive.update_partitions(X)

    s_static, s_adapt = static.score(X), adaptive.score(X)

    fig, ax = plt.subplots(figsize=(6.5, 4))
    order = np.argsort(energies)
    ax.plot(energies[order], s_static[order], "o-", label="Statik MF")
    ax.plot(energies[order], s_adapt[order], "s-", label="Adaptif MF")
    ax.set_xlabel("Kalan enerji $E_r$ (dar bantta toplanmış)")
    ax.set_ylabel("CH skoru")
    ax.set_title("Aynı 20 düğüm için CH skorları", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "cp2_adaptive_vs_static.png", dpi=150)
    plt.close(fig)

    corr = lambda s: float(np.corrcoef(energies, s)[0, 1])  # noqa: E731
    return {
        "score_std_static": float(s_static.std()),
        "score_std_adaptive": float(s_adapt.std()),
        "corr_energy_static": corr(s_static),
        "corr_energy_adaptive": corr(s_adapt),
        "partitions": {n: tuple(round(v, 3) for v in adaptive.partitions[n].params()) for n in INPUTS},
    }


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    TAB.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    counts = export_rules()
    plot_static_mfs()
    energies = clustered_energies(rng)
    plot_adaptive_mfs(energies)
    plot_control_surface()
    stats = adaptive_vs_static(energies, rng)

    print("Çıktı terimi başına kural sayısı:")
    print(counts.to_string())
    print("\nÇıktı kümesi ağırlık merkezleri z_k:", np.round(OutputSet().centroids, 4))
    print("\nAdaptif ve statik (enerjiler dar bantta):")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
