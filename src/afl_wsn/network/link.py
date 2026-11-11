"""Bağlantı başarı olasılığı ve atlama gecikmesi (varsayımsal modeller, CP2 §3.3–3.4)."""

from __future__ import annotations

import numpy as np

from ..config import SimConfig


def p_success(cfg: SimConfig, d) -> np.ndarray:
    """Mesafeye bağlı lojistik başarı olasılığı: p_max / (1 + exp((d - d50) / σ))."""
    d = np.asarray(d, dtype=float)
    return cfg.p_max / (1.0 + np.exp((d - cfg.d50) / cfg.sigma))


def tx_time(cfg: SimConfig) -> float:
    """Bir paketin iletim süresi k / R_b (s)."""
    return cfg.packet_bits / cfg.bitrate


def hop_delay(cfg: SimConfig, d, queue=0) -> np.ndarray:
    """Atlama gecikmesi (s) = iletim + yayılma + işlem + kuyruk (q · iletim)."""
    d = np.asarray(d, dtype=float)
    t = tx_time(cfg)
    return t + d / cfg.c_light + cfg.t_proc + np.asarray(queue, dtype=float) * t
