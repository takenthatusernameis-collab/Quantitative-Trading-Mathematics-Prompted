"""NF-20261105-08 / H90 (pre-registration): FOMC announcement event drift.

Pre-scheduled macro announcement (FOMC statement release) event windows on SPY.
"""

import json
import sys
from pathlib import Path

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
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261105_08_fomc_event_drift"
EXPERIMENT_DESC = "NF-20261105-08/H90: FOMC announcement event drift on SPY."

SPY = "SPY"
UNIVERSE = [SPY]

DATA_START = "2015-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

# Public Fed calendar FOMC meeting dates (statement release days), point-in-time audited.
FOMC_DATES = [
    "2015-01-28",
    "2015-03-18",
    "2015-04-29",
    "2015-06-17",
    "2015-07-29",
    "2015-09-17",
    "2015-10-28",
    "2015-12-16",
]

MAX_POS = 1.0

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        asset_class=AssetClass.EQUITY,
        allow_short=False,
        max_leverage=1.0,
        max_position_size=MAX_POS,
    )


def is_fomc_date(idx: pd.DatetimeIndex) -> pd.Series:
    s = pd.Series(False, index=idx)
    for d in FOMC_DATES:
        s = s | (idx.normalize() == pd.Timestamp(d))
    return s


def build_daily_targets(prices: pd.DataFrame, hold_days: int = 1) -> pd.DataFrame:
    close = prices[SPY]
    ret = close.pct_change().fillna(0.0)
    fomc = is_fomc_date(prices.index)
    target = pd.Series(0.0, index=prices.index)
    for i in range(len(prices)):
        if fomc.iloc[i]:
            for j in range(1, hold_days + 1):
                if i + j < len(prices):
                    target.iloc[i + j] = 1.0
    return pd.DataFrame({"target": target}, index=prices.index)


def main():
    pass


if __name__ == "__main__":
    main()
