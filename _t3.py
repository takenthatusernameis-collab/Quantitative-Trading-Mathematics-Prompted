#!/usr/bin/env python3
"""H9 v2 main body - appended via write tool."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import json
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from qtr.data.fetcher import get_data_fetcher
from qtr.backtest.engine import run_backtest, BacktestConfig, AssetClass, CostModel
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    sharpe_ratio, walk_forward_splits, compare_to_benchmark,
)

FUTURES_UNIVERSE = ["ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F"]
VIX_SYMBOL = "^VIX"
SEED = 42
INITIAL_CAPITAL = 1_000_000.0
GATES = {
    "min_sharpe": 1.0, "min_trades": 200, "min_profit_factor": 1.3,
    "max_drawdown": 0.15, "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3, "max_p_value": 0.05, "min_information_ratio": 0.0,
}
EXPERIMENT_NAME = "h9_intraday_tsmom_ctexits_v2"
EXPERIMENT_DESC = "H9 v2: Intraday TSMOM with genuine CT-style path-dependent exits"
FUTURES_SPECS = {
    "ES=F": {"multiplier": 50.0, "tick_value": 12.50, "tick_size": 0.25, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "NQ=F": {"multiplier": 20.0, "tick_value": 5.0, "tick_size": 0.25, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "CL=F": {"multiplier": 1000.0, "tick_value": 10.0, "tick_size": 0.01, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "GC=F": {"multiplier": 100.0, "tick_value": 10.0, "tick_size": 0.10, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
    "ZB=F": {"multiplier": 1000.0, "tick_value": 31.25, "tick_size": 0.03125, "commission": 0.50, "spread_ticks": 0.25, "slippage_ticks": 0.5},
}


def regime_labels(vix_daily):
    regimes = pd.Series(index=vix_daily.index, dtype=object)
    vix_ff = vix_daily.ffill()
    regimes[vix_ff < 20] = "bull"
    regimes[(vix_ff >= 20) & (vix_ff <= 30)] = "sideways"
    regimes[vix_ff > 30] = "bear"
    return regimes


def make_futures_config():
    cm = CostModel(
        future_commission_per_contract=0.50,
        future_spread_ticks=0.25,
        future_slippage_ticks=0.5,
        futures_specs=FUTURES_SPECS,
    )
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        asset_class=AssetClass.FUTURE,
        max_position_size=2.0,
        max_leverage=5.0,
        allow_short=False,
        cost_model=cm,
    )


def main():
    np.random.seed(SEED)
    tracker = get_tracker()
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={"universe": FUTURES_UNIVERSE, "interval": "1h", "gates": GATES, "seed": SEED},
        data_sources={"source": "yahoo_futures", "symbols": FUTURES_UNIVERSE, "interval": "1h"},
        compute_budget={"max_cpu_hours": 4.0},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print("started", exp_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())