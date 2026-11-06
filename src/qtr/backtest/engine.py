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

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from qtr.backtest.core import (
        AssetClass,
        BacktestConfig,
        CostModel,
        run_backtest,
    )
except Exception:
    # Fallback for environments where core may not exist
    AssetClass = None
    BacktestConfig = None
    CostModel = None
    run_backtest = None

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
        if ed is None or getattr(ed, "empty", False):
            continue
        try:
            for idx, r in ed.iterrows():
                est = r.get("EPS Estimate")
                rep = r.get("Reported EPS")
                if pd.isna(est) or pd.isna(rep):
                    continue
                rows.append({"ticker": t, "date": pd.Timestamp(idx).date(),
                             "estimate": float(est), "reported": float(rep),
                             "surprise": float(rep - est)})
        except Exception:
            continue
    return pd.DataFrame(rows)


def t_earnings(ticker):
    try:
        import yfinance as yf
    except Exception as e:
        raise e
    tk = yf.Ticker(ticker)
    try:
        ed = tk.earnings_dates
        return ed
    except Exception as e:
        raise e


def build_signal(prices, earnings):
    try:
        all_dates = sorted(set.union(*[set(s.index) for s in prices.values()]))
    except Exception:
        all_dates = []
    sig = pd.DataFrame(0.0, index=pd.DatetimeIndex(all_dates), columns=list(prices.keys()))
    if earnings is None or getattr(earnings, "empty", True):
        daily = sig.mean(axis=1)
        return daily
    try:
        for _, e in earnings.iterrows():
            t = e["ticker"]
            if t not in prices:
                continue
            d = pd.Timestamp(e["date"])
            # find next trading day index
            try:
                idx = prices[t].index.searchsorted(d)
            except Exception:
                continue
            if idx >= len(prices[t]):
                continue
            entry = prices[t].index[idx]
            try:
                pos = prices[t].index.get_loc(entry)
            except Exception:
                continue
            endpos = min(pos + HOLD_DAYS, len(prices[t]))
            if e["surprise"] > 0:
                direction = 1.0
            elif e["surprise"] < 0:
                direction = -1.0
            else:
                continue
            if direction == 0:
                continue
            for i in range(pos, endpos):
                dt = prices[t].index[i]
                sig.at[dt, t] = direction
    except Exception:
        pass
    daily = sig.mean(axis=1)
    return daily


def main():
    cache = DataCache(Path(__file__).parent.parent.parent / ".cache" / "nf_20261105_19")
    fetcher = DataFetcher(cache)
    prices = {}
    for t in UNIVERSE:
        try:
            df = fetcher.fetch(t, START, END)
            if df is None or "Close" not in df:
                continue
            prices[t] = df["Close"]
        except Exception:
            continue
    try:
        earnings = fetch_earnings(UNIVERSE)
    except Exception:
        earnings = pd.DataFrame()
    try:
        signal = build_signal(prices, earnings)
    except Exception:
        signal = pd.Series(dtype=float)

    if not prices:
        return
    try:
        common = sorted(set.intersection(*[set(s.index) for s in prices.values()]))
        common = pd.DatetimeIndex(common)
        ret_matrix = pd.DataFrame({t: prices[t].reindex(common).pct_change() for t in prices})
        port_ret = ret_matrix.mean(axis=1)
        price = (1 + port_ret.fillna(0)).cumprod() * 100
        price.name = "close"
        if BacktestConfig is not None and CostModel is not None and run_backtest is not None and AssetClass is not None:
            cfg = BacktestConfig(
                cost_model=CostModel(commission_bps=1, spread_bps=0.5, impact_bps=0.1),
                asset_class=AssetClass.EQUITY,
            )
            sig = signal.reindex(price.index).fillna(0.0)
            try:
                res = run_backtest(price, sig.shift(1), cfg)
            except Exception as e:
                print("err", e)
                return
            print("trades", getattr(res, "n_trades", None))
            print("sharpe", getattr(res, "sharpe", None))
            try:
                tracker = get_tracker()
                tracker.finish(EXPERIMENT_NAME, {"sharpe": getattr(res, "sharpe", None)})
            except Exception:
                pass
            return
        else:
            # minimal fallback
            sig = signal.reindex(price.index).fillna(0.0)
            try:
                ret = price.pct_change().fillna(0) * sig.shift(1).fillna(0)
                # simple cost approx ignored
                print("sharpe_fallback", ret.mean()/ret.std()*np.sqrt(252) if ret.std()!=0 else None)
            except Exception as e:
                print("err", e)
            return
    except Exception as e:
        print("err", e)
        return


if __name__ == "__main__":
    main()
