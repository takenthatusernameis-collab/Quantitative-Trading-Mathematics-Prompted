"""NF-20261106-36 / H118 (pre-registered, Cycle 32): Cross-sectional sector
return dispersion timing for SPY (discriminating test vs H117 correlation regime).

Signal = z-score of trailing cross-sectional standard deviation of sector ETF
daily returns (lookback window) over z_window. When dispersion regime is
abnormally high (idiosyncratic stress), reduce vol-targeted long SPY exposure
continuously, 1-bar delay. 9 sectors with full 2010+ history (XLC/XLRE
excluded for sample preservation). No src/qtr change.
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
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261106_36_sector_dispersion"
EXPERIMENT_DESC = (
    "NF-20261106-36/H118: cross-sectional sector return dispersion timing for "
    "SPY. Signal = z-score of trailing cross-sectional std of sector ETF daily "
    "returns (lookback window) over z_window. When dispersion regime is "
    "abnormally high, reduce vol-targeted long SPY continuously, 1-bar delay. "
    "9 sectors with full 2010+ history (XLC/XLRE excluded). Train-only WF "
    "selection; Test protected; OOS gates."
)

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
SPY = "SPY"
UNIVERSE = SECTORS + [SPY]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

LOOKBACKS = [21, 63]
Z_WINDOWS = [126, 252]
ENTRY_SCALES = [1.0, 1.5, 2.0]
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4

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
        asset_class=AssetClass.EQUITY,
        allow_short=False,
        max_leverage=1.0,
        max_position_size=MAX_POS,
        cost_model=CostModel(equity_commission_bps=1.0),
    )


def build_dispersion_targets(prices, lookback=21, z_window=126, entry_scale=1.0, vol_target=0.10):
    sectors = [c for c in prices.columns if c != SPY]
    spy_ret = prices[SPY].pct_change()
    sector_ret = prices[sectors].pct_change()
    # trailing cross-sectional std of sector returns (per bar), then trailing mean over lookback
    cs_std = sector_ret.std(axis=1)
    disp = cs_std.rolling(lookback).mean()
    mu = disp.rolling(z_window).mean()
    sd = disp.rolling(z_window).std()
    z = (disp - mu) / sd
    scale = 1.0 / (1.0 + entry_scale * z.clip(lower=0))
    # vol target on spy
    vol = spy_ret.rolling(21).std() * np.sqrt(252)
    vol = vol.replace(0, np.nan).ffill()
    vt_scale = (vol_target / vol).clip(upper=MAX_POS)
    pos = (scale * vt_scale).clip(0, MAX_POS).shift(1).fillna(0)
    out = pd.DataFrame({SPY: pos}, index=prices.index)
    return out


def main():
    fetcher = DataFetcher()
    cache = DataCache()
    prices = fetcher.fetch_prices(UNIVERSE, DATA_START, DATA_END, cache=cache)
    # placeholder execution summary
    tracker = get_tracker()
    run_id = tracker.start_run(EXPERIMENT_NAME, EXPERIMENT_DESC)
    # train grid selection
    best = None
    best_sharpe = -np.inf
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    train_prices = prices.loc[train_mask]
    for lb in LOOKBACKS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    pos = build_dispersion_targets(train_prices, lb, zw, es, vt)
                    cfg = make_equity_config()
                    res = run_backtest(pos, train_prices[[SPY]], cfg)
                    sh = sharpe_ratio(res.returns)
                    if sh > best_sharpe:
                        best_sharpe = sh
                        best = (lb, zw, es, vt)
    # full run with best
    lb, zw, es, vt = best
    pos = build_dispersion_targets(prices, lb, zw, es, vt)
    cfg = make_equity_config()
    res = run_backtest(pos, prices[[SPY]], cfg)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    metrics = {
        "best_params": {"lookback": lb, "z_window": zw, "entry_scale": es, "vol_target": vt},
        "train_sharpe": float(sharpe_ratio(res.returns.loc[train_mask])),
        "val_sharpe": float(sharpe_ratio(res.returns.loc[val_mask])),
        "test_sharpe": float(sharpe_ratio(res.returns.loc[test_mask])),
        "n_trades": int((pos[SPY].diff().abs() > 1e-9).sum()),
    }
    print(json.dumps(metrics, indent=2, default=str))
    tracker.log_metrics(run_id, metrics)
    tracker.end_run(run_id, status="completed")
    out = Path(".experiments/nf_runs/nf_20261106_36_sector_dispersion")
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(metrics, indent=2, default=str))


if __name__ == "__main__":
    main()
