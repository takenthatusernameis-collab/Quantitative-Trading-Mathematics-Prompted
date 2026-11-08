"""NF-20261108-12 / H147 (Cycle 61): SPY timing from sector breadth
participation (% of 9 SPDR sector ETFs above 200d MA).

Mechanism: low breadth (few sectors above trend) = weak participation /
narrow market = near-term drawdown risk; de-risk SPY when breadth z is low.
Observable past-only PIT daily adjusted Close via yfinance.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest
from qtr.validation.statistics import sharpe_ratio

SECTORS = ["XLF", "XLE", "XLV", "XLI", "XLK", "XLY", "XLP", "XLU", "XLB"]
TR = "SPY"
START, END = "2010-01-04", "2025-01-03"


def fetch(tickers):
    import yfinance as yf

    df = yf.download(tickers, start=START, end=END, auto_adjust=True, progress=False)
    px = df["Close"] if "Close" in df else df
    return px


def main():
    px = fetch([TR] + SECTORS)
    px = px.dropna(how="all").ffill()
    rets = px.pct_change()
    # breadth: fraction of sectors above 200d MA
    ma = px[SECTORS].rolling(200).mean()
    above = (px[SECTORS] > ma).astype(float)
    breadth = above.mean(axis=1)
    z = (breadth - breadth.rolling(126).mean()) / breadth.rolling(126).std()
    stress = (-z.clip(upper=0) / 1.0).clip(0, 1)
    exposure = (1 - stress) * 0.10
    signal = pd.DataFrame({"SPY": exposure}, index=px.index).shift(1).fillna(0)
    cfg = BacktestConfig(asset_class=AssetClass.EQUITY, cost_model=CostModel())
    res = run_backtest(px[[TR]], signal, cfg)
    sh = sharpe_ratio(res.returns)
    out = {"sharpe": float(sh), "n": int(len(res.returns))}
    Path(".experiments/nf_runs/nf_20261108_12_sector_breadth_spy").mkdir(
        parents=True, exist_ok=True
    )
    Path(".experiments/nf_runs/nf_20261108_12_sector_breadth_spy/summary.json").write_text(
        json.dumps(out, indent=2)
    )
    print(json.dumps(out))


if __name__ == "__main__":
    main()
