"""NF-20261105-19 / H98 (pre-registered): Post-earnings announcement drift (PEAD).

Cross-sectional long/short on positive/negative earnings surprises.

Mechanism: stocks with positive EPS surprises drift up ~20 trading days post
announcement; negative surprises drift down. Long positive-surprise / short
negative-surprise, equal-weight, vol-targeted.

Data: yfinance earnings dates + EPS estimate/reported for fixed large-cap
universe; daily prices yfinance. Free, point-in-time (next-day open execution).

Timing: signal formed at close of announcement day; positions entered next open;
hold 20 trading days; engine shift(1).

Splits: Train 2015-2019; Val 2020-2022; Test 2023-2026 (protected).

Gates: standard PROMPT_V2 Phase 4 OOS Val+Test.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import DataCache, DataFetcher
from qtr.tracking.experiment import get_tracker

EXPERIMENT_NAME = "nf_20261105_19_pead"
UNIVERSE = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "V",
            "JNJ", "WMT", "PG", "UNH", "HD", "MA", "BAC", "XOM", "CVX",
            "PFE", "KO", "PEP"]
HOLD_DAYS = 20
START = "2015-01-01"
END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"


def fetch_earnings(universe):
    rows = []
    for t in universe:
        try:
            ed = t_earnings(t)
        except Exception:
            continue
        if ed is None or ed.empty:
            continue
        for idx, r in ed.iterrows():
            est = r.get("EPS Estimate")
            rep = r.get("Reported EPS")
            if pd.isna(est) or pd.isna(rep):
                continue
            rows.append({"ticker": t, "date": pd.Timestamp(idx).date(),
                         "estimate": float(est), "reported": float(rep),
                         "surprise": float(rep - est)})
    return pd.DataFrame(rows)


def t_earnings(ticker):
    import yfinance as yf
    return yf.Ticker(ticker).earnings_dates


def build_signal(prices, earnings):
    # prices: dict ticker -> Series
    # returns daily signal DataFrame aligned to common dates
    all_dates = sorted(set().union(*[set(s.index) for s in prices.values()]))
    sig = pd.DataFrame(0.0, index=pd.DatetimeIndex(all_dates), columns=list(prices.keys()))
    for _, e in earnings.iterrows():
        t = e["ticker"]
        if t not in prices:
            continue
        d = pd.Timestamp(e["date"])
        # find next trading day on/after announcement date
        idx = prices[t].index.searchsorted(d)
        if idx >= len(prices[t]):
            continue
        entry = prices[t].index[idx]
        # hold window
        pos = prices[t].index.get_loc(entry)
        endpos = min(pos + HOLD_DAYS, len(prices[t]))
        direction = 1.0 if e["surprise"] > 0 else (-1.0 if e["surprise"] < 0 else 0.0)
        if direction == 0:
            continue
        for i in range(pos, endpos):
            dt = prices[t].index[i]
            sig.loc[dt, t] = direction
    # aggregate daily portfolio signal = mean across tickers with active positions
    daily = sig.mean(axis=1)
    return daily


def main():
    cache = DataCache(str(Path(__file__).parent / ".cache" / "nf_20261105_19"))
    fetcher = DataFetcher(cache)
    prices = {}
    for t in UNIVERSE:
        try:
            df = fetcher.fetch(t, START, END)
            prices[t] = df["Close"]
        except Exception as ex:
            print("fetch fail", t, ex)
    earnings = fetch_earnings(UNIVERSE)
    signal = build_signal(prices, earnings)
    # common index
    common = sorted(set.intersection(*[set(s.index) for s in prices.values()]))
    common = pd.DatetimeIndex(common)
    # build a synthetic single-asset price for engine: use SPY? Use equal-weight portfolio proxy = first ticker
    # Engine expects a single price series; use SPY proxy via mean returns
    ret_matrix = pd.DataFrame({t: prices[t].reindex(common).pct_change() for t in prices})
    port_ret = ret_matrix.mean(axis=1)
    price = (1 + port_ret.fillna(0)).cumprod() * 100
    price.name = "close"
    cfg = BacktestConfig(
        cost_model=CostModel(commission_bps=1, spread_bps=0.5, impact_bps=0.1),
        asset_class=AssetClass.EQUITY,
    )
    # align signal to price index
    sig = signal.reindex(price.index).fillna(0.0)
    res = run_backtest(price, sig.shift(1), cfg)
    print("trades", getattr(res, "n_trades", None))
    print("sharpe", getattr(res, "sharpe", None))
    tracker = get_tracker()
    tracker.finish(EXPERIMENT_NAME, {"sharpe": getattr(res, "sharpe", None)})


if __name__ == "__main__":
    main()
```

Wait, I used t_earnings before defined? It's defined. fetch_earnings calls t_earnings. Fine. But `t` loop variable shadows; okay.

This is rough. The engine API may differ. Let me check run_backtest signature.<|end|><|start|><|start|>assistant to=bash<|channel|>analysis <|constrain|>xml<|message|><rfl:parameter name="command">
grep -n "def run_backtest" src/qtr/backtest/engine.py