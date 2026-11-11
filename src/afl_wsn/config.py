"""Simülasyon ve algoritma parametreleri.

Her parametrenin kaynağı (makale Tablo 3 ya da bu projedeki varsayım)
docs/checkpoint2_uygulama_plani.md içinde belgelenmiştir.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class PSOConfig:
    mode: str = "pso_ga"  # "pso_ga" | "pso" | "ga"
    n_particles: int = 30  # Tablo 3
    w: float = 0.7  # Tablo 3
    c1: float = 1.5  # Tablo 3
    c2: float = 1.5  # Tablo 3
    vmax: float = 4.0  # Tablo 3: hız sınırı [-4, 4]
    pos_range: tuple[float, float] = (0.0, 10.0)  # varsayım (rastgele anahtar aralığı)
    max_iter: int = 100  # Tablo 3
    patience: int = 20  # varsayım: G_best bu kadar iterasyon iyileşmezse dur
    ga_interval: int = 10  # varsayım: T (makalede yok)
    tournament: int = 3  # varsayım (Tablo 3: turnuva seçimi)
    pc: float = 0.8  # Tablo 3
    pm: float = 0.1  # Tablo 3
    n_offspring: int = 30  # Tablo 3: GA popülasyonu 30


@dataclass(frozen=True)
class SimConfig:
    # --- Ağ (Tablo 3) ---
    n_nodes: int = 20
    area: float = 100.0
    bs: tuple[float, float] = (50.0, 50.0)
    comm_range: float = 25.0
    e_init: float = 2.0
    packet_bits: int = 512 * 8

    # --- Radyo enerji modeli ---
    e_elec: float = 50e-9  # J/bit (Tablo 3)
    eps_fs: float = 100e-12  # J/bit/m^2 (Tablo 3, "ε_amp")
    eps_mp: float = 0.0013e-12  # J/bit/m^4 (varsayım, LEACH literatürü)
    e_da: float = 5e-9  # J/bit/sinyal (Tablo 3)

    # --- Bağlantı modeli (varsayım) ---
    p_max: float = 0.98
    d50: float = 30.0
    sigma: float = 3.0
    ls_alpha: float = 0.1  # L_s üstel hareketli ortalama katsayısı

    # --- Gecikme modeli (varsayım) ---
    bitrate: float = 250e3  # IEEE 802.15.4
    t_proc: float = 1e-3
    c_light: float = 3e8

    # --- Zamanlama ---
    t_round: float = 1.0
    n_rounds: int = 100  # Tablo 3: 100 iterasyon
    epoch_len: int = 10  # yeniden kümeleme aralığı (tur)
    ch_energy_drop: float = 0.8  # CH enerjisi dönem başının %80'inin altına düşerse yeniden kümele
    run_until_dead: bool = False  # True: ömür deneyi (LND'ye kadar, n_rounds üst sınır)

    # --- Trafik ---
    traffic_mode: str = "delta"  # "delta" (send-on-delta + kalp atışı) | "periodic"
    delta_threshold: float = 0.5  # z-skor biriminde değişim eşiği
    abnormal_z: float = 2.0
    heartbeat: int = 10

    # --- Kümeleme ---
    clustering: str = "afl"  # "afl" | "static_fuzzy" | "leach"
    ch_min_energy: float = 0.05  # CH adaylığı için E_r alt sınırı
    leach_p: float = 0.1
    mf_lambda: float = 0.7
    defuzz: str = "weighted_average"

    # --- Yönlendirme ---
    routing: str = "pso_ga"  # "direct" | "dijkstra" | "pso" | "ga" | "pso_ga"
    fitness_weights: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25)  # α, β, γ, δ
    infeasible_fitness: float = 10.0
    pso: PSOConfig = field(default_factory=PSOConfig)

    def with_(self, **kwargs) -> "SimConfig":
        """Değiştirilmiş bir kopya döndürür. PSO alanları 'pso__w=0.5' biçiminde verilebilir."""
        pso_kw = {k[5:]: v for k, v in kwargs.items() if k.startswith("pso__")}
        rest = {k: v for k, v in kwargs.items() if not k.startswith("pso__")}
        cfg = replace(self, **rest)
        if pso_kw:
            cfg = replace(cfg, pso=replace(cfg.pso, **pso_kw))
        return cfg
