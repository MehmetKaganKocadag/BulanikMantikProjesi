"""Birinci derece radyo enerji modeli (Heinzelman et al., 2000).

Makaledeki Denk. 16 (E = E_elec·d + ε_amp·d^n) bit sayısını içermediği ve E_elec'i
mesafeyle çarptığı için kullanılmaz (CP1, T4). Standart model:

    E_TX(k, d) = E_elec·k + ε_fs·k·d²   (d <  d0)
               = E_elec·k + ε_mp·k·d⁴   (d >= d0),   d0 = sqrt(ε_fs / ε_mp)
    E_RX(k)    = E_elec·k
"""

from __future__ import annotations

import numpy as np

from ..config import SimConfig


def d0(cfg: SimConfig) -> float:
    return float(np.sqrt(cfg.eps_fs / cfg.eps_mp))


def e_tx(cfg: SimConfig, bits: float, d) -> np.ndarray:
    d = np.asarray(d, dtype=float)
    amp = np.where(d < d0(cfg), cfg.eps_fs * d**2, cfg.eps_mp * d**4)
    return cfg.e_elec * bits + amp * bits


def e_rx(cfg: SimConfig, bits: float) -> float:
    return cfg.e_elec * bits
