"""E3 — Küçük ağ senaryosu (makaledeki "5 düğüm" durumu).

100 × 100 m alanda 25 m menzille 5 düğüm çoğunlukla bağlantısızdır (CP1, T9).
Bu deney bunu ölçer: bağlantısız CH oranı ve buna bağlı PDR.

Çıktılar:  results/tables/e3_raw.csv, e3_summary.csv
Çalıştırma (repo kökünden):  python experiments/baseline/run_e3.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from afl_wsn.experiment import METRICS, make_tasks, run_many, summarize  # noqa: E402
from afl_wsn.plotting import METHOD_ORDER  # noqa: E402

TAB = ROOT / "results" / "tables"
DATASETS = ["data1", "data2", "data3"]
SEEDS = range(30)


def main() -> None:
    t0 = time.perf_counter()
    tasks = make_tasks(METHOD_ORDER, DATASETS, SEEDS, overrides={"n_nodes": 5}, tag={"n_nodes": 5})
    df = pd.DataFrame(run_many(tasks))
    print(f"{len(df)} koşu, {time.perf_counter() - t0:.1f} s")
    df.to_csv(TAB / "e3_raw.csv", index=False)
    extra = ["disconnected_ch_frac", "n_ch_mean", "route_hops_mean"]
    summ = summarize(df, ["method"], METRICS + extra)  # 3 veri seti birlikte
    summ.to_csv(TAB / "e3_summary.csv", index=False)
    pd.set_option("display.width", 200)
    cols = ["method", "n"] + [f"{m}_mean" for m in METRICS + extra]
    print(summ[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
