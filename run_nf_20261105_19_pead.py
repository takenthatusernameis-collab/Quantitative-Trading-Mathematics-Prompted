"""NF-20261105-19 / H98 (pre-registered): Post-earnings announcement drift (PEAD).

New family dimension (event-driven fundamental information incorporation),
distinct from price-based momentum, volume-predictive, and regime families.

Causality: signal formed at close of announcement day; positions entered next open;
hold 20 trading days; engine shift(1). Protected holdout Test 2023+.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import numpy as np
import pandas as pd

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel
from qtr.data.fetcher import DataCache, DataFetcher

EXPERIMENT_NAME = "nf_20261105_19_pead"
EXPERIMENT_DESC = (
    "NF-20261105-19/H98: post-earnings announcement drift long/short. "
    "Vol-targeted equal-weight long positive-surprise / short negative-surprise, "
    "held ~20 trading days; 1-bar execution delay."
)

UNIVERSE = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM",
            "BAC", "WFC", "JNJ", "UNH", "PFE", "XOM", "CVX", "PG", "KO",
            "PEP", "HD", "WMT"]

DATA_START = "2015-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
HOLD_DAYS = 20

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=True,
    )


def build_pead_targets(prices, surprises, hold_days=HOLD_DAYS, vol_target=0.10):
    """Build daily position targets from an earnings-surprise event table.

    surprises: DataFrame with columns ['ticker','date','surprise'] (date = announcement day).
    Returns DataFrame indexed by prices index, columns = tickers, values in [-MAX_POS, MAX_POS].
    """
    tickers = list(prices.columns)
    out = pd.DataFrame(0.0, index=prices.index, columns=tickers)
    for _, row in surprises.iterrows():
        t = row["ticker"]
        if t not in out.columns:
            continue
        d = pd.Timestamp(row["date"])
        if d not in prices.index:
            # find next trading day
            idx = prices.index.searchsorted(d)
            if idx >= len(prices.index):
                continue
            d = prices.index[idx]
        sign = 1.0 if row["surprise"] > 0 else (-1.0 if row["surprise"] < 0 else 0.0)
        if sign == 0.0:
            continue
        start = prices.index.get_loc(d) + 1
        end = min(start + hold_days, len(prices.index))
        out.iloc[start:end, out.columns.get_loc(t)] += sign * MAX_POS / max(len(tickers), 1)
    return out


if __name__ == "__main__":
    print("H98 PEAD runner stub; execution requires earnings data fetch.")
