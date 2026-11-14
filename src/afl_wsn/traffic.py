"""Veri setlerinden paket üretimi (trafik kaynağı).

Makale Kaggle verisinin ağa nasıl eşlendiğini açıklamaz (CP1, E7). Bu projede veri
setleri trafik kaynağıdır (CP2 §3.5, data/README.md):

  * Ön işleme: geçersiz ölçümler → eksik; medyanla doldurma; z-skor; |z| > 3 → medyan.
  * Her düğüm zamana göre sıralı akışı kendine özgü bir ofsetten okur:
    tur t'de (ofset_i + t) mod L satırı.
  * Paket üretimi (send-on-delta + kalp atışı): bir ölçüm son gönderilen değerden
    `delta_threshold` (z birimi) fazla değişirse, |z| > `abnormal_z` ise ya da
    `heartbeat` tur boyunca paket gönderilmemişse.

Makalenin şekillerindeki yorum için (CP3 §11) veri kayıtları düğüm konumu olarak da
kullanılabilir: `load_placement` iki sütunu [0, 1]'e ölçekler; her düğüm bir kayda
oturur ve akışı o kayıttan itibaren okur.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import SimConfig

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

DATASETS: dict[str, dict] = {
    "data1": {
        "file": "data1_healthcare_iot_5000.csv",
        "columns": ["Temperature (°C)", "Systolic_BP (mmHg)", "Diastolic_BP (mmHg)", "Heart_Rate (bpm)"],
        "sort": "Timestamp",
        "invalid": {},
        "placement": ("Heart_Rate (bpm)", "Systolic_BP (mmHg)"),  # şekillerdeki "yaş" sütunu yok
    },
    "data2": {
        "file": "data2_health_monitoring.csv",
        "columns": ["Temperature Data", "ECG Data", "Pressure Data"],
        "sort": "Sl.No",
        "invalid": {"Temperature Data": lambda s: s > 42},  # fizyolojik olmayan sıcaklık
        "placement": ("Temperature Data", "ECG Data"),
    },
    "data3": {
        "file": "data3_patient_temp_pulse.csv",
        "columns": ["Temp", "Pulse"],
        "sort": None,  # dosya zaten kronolojik (tek oturum)
        "invalid": {"Pulse": lambda s: (s <= 0) | (s >= 4095)},  # sensör kopması / ADC doyması
        "placement": ("Temp", "Pulse"),
    },
}


def clean(df: pd.DataFrame, columns: list[str], invalid: dict) -> pd.DataFrame:
    """Geçersiz ölçümleri eksik sayar ve medyanla doldurur (ham birimlerde)."""
    X = df[columns].astype(float).copy()
    for col, rule in invalid.items():
        X.loc[rule(X[col]), col] = np.nan
    return X.fillna(X.median())


def preprocess(df: pd.DataFrame, columns: list[str], invalid: dict) -> np.ndarray:
    """Makalenin tarif ettiği ön işleme (s. 9). Çıktı: z-skor matrisi (L, F)."""
    X = clean(df, columns, invalid)
    mu, sd = X.mean(), X.std(ddof=0).replace(0, 1.0)
    Z = (X - mu) / sd
    Z = Z.mask(Z.abs() > 3, 0.0)  # aykırı değer → medyan civarı (z ≈ 0)
    return Z.to_numpy()


@lru_cache(maxsize=None)
def _load_sorted(name: str, data_dir: str | None = None) -> pd.DataFrame:
    spec = DATASETS[name]
    path = Path(data_dir) if data_dir else DATA_DIR
    df = pd.read_csv(path / spec["file"])
    if spec["sort"]:
        df = df.sort_values(spec["sort"], kind="stable").reset_index(drop=True)
    return df


@lru_cache(maxsize=None)
def load_stream(name: str, data_dir: str | None = None) -> np.ndarray:
    """Ön işlenmiş akışı döndürür. Dosya yoksa FileNotFoundError."""
    spec = DATASETS[name]
    return preprocess(_load_sorted(name, data_dir), spec["columns"], spec["invalid"])


@lru_cache(maxsize=None)
def load_placement(name: str, data_dir: str | None = None) -> np.ndarray:
    """Kayıt başına iki boyutlu konum, [0, 1]² içinde (min-max ölçekleme). Satır sırası akışla aynı."""
    spec = DATASETS[name]
    cols = list(spec["placement"])
    invalid = {c: r for c, r in spec["invalid"].items() if c in cols}
    X = clean(_load_sorted(name, data_dir), cols, invalid).to_numpy()
    lo, hi = X.min(axis=0), X.max(axis=0)
    return (X - lo) / np.where(hi > lo, hi - lo, 1.0)


def synthetic_stream(rng: np.random.Generator, length: int = 2000, n_features: int = 3) -> np.ndarray:
    """Veri yokken kullanılan sentetik akış: AR(1) süreçleri + ara sıra anormal sıçramalar."""
    z = np.zeros((length, n_features))
    for t in range(1, length):
        z[t] = 0.9 * z[t - 1] + rng.normal(0, 0.45, n_features)
    spikes = rng.random(length) < 0.02
    z[spikes] += rng.choice([-3.0, 3.0], size=(spikes.sum(), n_features))
    return z


def get_stream(name: str, rng: np.random.Generator) -> np.ndarray:
    if name == "synthetic":
        return synthetic_stream(rng)
    return load_stream(name)


class TrafficSource:
    """Her tur hangi düğümlerin paket ürettiğini belirler."""

    def __init__(self, stream: np.ndarray, cfg: SimConfig, rng: np.random.Generator,
                 offsets: np.ndarray | None = None) -> None:
        self.stream = stream
        self.cfg = cfg
        n = cfg.n_nodes
        # offsets verilmezse rastgele; veriden yerleşimde düğüm kendi kaydından okumaya başlar
        self.offsets = rng.integers(0, stream.shape[0], size=n) if offsets is None else np.asarray(offsets)
        self.last_sent = np.full((n, stream.shape[1]), np.nan)
        self.since_sent = np.full(n, cfg.heartbeat)  # ilk turda herkes gönderir

    def generate(self, t: int, alive: np.ndarray) -> np.ndarray:
        cfg = self.cfg
        if cfg.traffic_mode == "periodic":
            return alive.copy()

        rows = self.stream[(self.offsets + t) % self.stream.shape[0]]  # (N, F)
        changed = np.nan_to_num(np.abs(rows - self.last_sent), nan=np.inf).max(axis=1) > cfg.delta_threshold
        abnormal = np.abs(rows).max(axis=1) > cfg.abnormal_z
        heartbeat = self.since_sent >= cfg.heartbeat
        send = alive & (changed | abnormal | heartbeat)

        self.last_sent[send] = rows[send]
        self.since_sent[send] = 0
        self.since_sent[~send] += 1
        return send
