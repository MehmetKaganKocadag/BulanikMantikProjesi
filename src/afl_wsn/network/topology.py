"""Düğüm yerleşimi ve mesafe matrisi.

İndeksleme: 0..N-1 sensör düğümleri, N baz istasyonu (BS).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import SimConfig


@dataclass
class Topology:
    pos: np.ndarray  # (N, 2)
    bs: np.ndarray  # (2,)
    dist: np.ndarray  # (N+1, N+1), son satır/sütun BS
    d_max_bs: float  # alandaki herhangi bir noktanın BS'ye en büyük uzaklığı (Denk. 3'teki d_max)

    @property
    def n(self) -> int:
        return self.pos.shape[0]

    @property
    def bs_index(self) -> int:
        return self.n


def from_positions(pos: np.ndarray, cfg: SimConfig) -> Topology:
    """Verilen konumlardan (N, 2) topoloji kurar. BS ve d_max Tablo 3'e göre."""
    pos = np.asarray(pos, dtype=float)
    bs = np.asarray(cfg.bs, dtype=float)
    pts = np.vstack([pos, bs])
    dist = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=-1)
    corners = np.array([[0, 0], [0, cfg.area], [cfg.area, 0], [cfg.area, cfg.area]], dtype=float)
    d_max_bs = float(np.linalg.norm(corners - bs, axis=1).max())
    return Topology(pos=pos, bs=bs, dist=dist, d_max_bs=d_max_bs)


def deploy(cfg: SimConfig, rng: np.random.Generator) -> Topology:
    """Düzgün rastgele yerleşim (varsayılan, CP1 §9)."""
    return from_positions(rng.uniform(0.0, cfg.area, size=(cfg.n_nodes, 2)), cfg)
