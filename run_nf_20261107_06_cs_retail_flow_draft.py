"""SUPERSEDED UNEXECUTED DRAFT — NOT NF-20261107-06 / H122 EVIDENCE.

This file is a renamed, incomplete, test-less draft (previously
run_nf_20261107_06_cs_retail_flow.py). It was never executed: it has no
main(), no run_backtest call, no experiment tracking, no focused tests, and no
committed summary.json artifact. It must not be treated as NF-20261107-06 or
H122 evidence.

NF-20261107-06 itself (VIX futures term-structure contango/backwardation carry
timing on SPY, ^VIX/^VIX3M) is a DUPLICATE of H86 (NF-20261104-01, VIX term
structure slope VIX3M/VIX on SPY, executed REJECT 2/9). It is not a repo-new
family and must not be pre-registered as H123. See NEW_FAMILY_RESEARCH_REGISTER.md
Cycle 37.

Original (unexecuted) draft mechanism: cross-sectional rank of trailing
lookback-day signed retail flow (volume * direction, direction inferred from
close vs prior close). Each week (fixed 5-bar rebalance cadence) go long-only
the three sectors with the weakest signed retail flow (most net selling), equal
weight, each vol-targeted to vol_target, max_position 0.5, hold until the next
weekly rebalance. Engine signals.shift(1) gives t->t+1 causality.
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

EXPERIMENT_NAME = "nf_20261107_06_cs_retail_flow"
EXPERIMENT_DESC = (
    "NF-20261107-06/H122: cross-sectional retail-flow timing across sector "
    "ETFs. Weekly long-only the three sectors with the weakest signed retail "
    "flow (most net selling), equal weight, vol-targeted, fixed 5-bar "
    "rebalance cadence. Train-only WF selection; Test protected; OOS gates vs "
    "buy-hold SPY benchmark."
)

SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
SPY = "SPY"
UNIVERSE = SECTORS
BENCHMARK = SPY

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
MAX_LEVERAGE = 1.0
N_LONG = 3  # weakest tercile of 9 sectors
REBALANCE_EVERY = 5  # bars; fixed weekly cadence, not price-tuned

LOOKBACKS = [5, 10]
FLOW_SCALES = [1.0, 1e6]  # signed volume / average dollar volume scale
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4
VOL_WINDOW = 63
VOL_MIN_PERIODS = 21

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
        max_leverage=MAX_LEVERAGE,
        allow_short=False,
    )


def _align_prices(fetcher: DataFetcher, symbols, start: str, end: str) -> pd.DataFrame:
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")
    frames = {}
    for s in symbols:
        df = raw.get(s)
        if df is None or df.empty:
            raise RuntimeError(f"Data fetch failed for {s}")
        col = (
            "adj_close"
            if "adj_close" in df.columns
            else (
                "close"
                if "close" in df.columns
                else ("Close" if "Close" in df.columns else df.columns[0])
            )
        )
        c = df[col].astype(float)
        if (c <= 0).any():
            raise RuntimeError(f"Non-positive prices in {s}")
        frames[s] = c.rename(s)
    prices = pd.concat(frames.values(), axis=1).dropna()
    if prices.empty:
        raise RuntimeError("No aligned data")
    return prices


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _signed_flow_rank(
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    lookback: int,
    flow_scale: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cross-sectional rank of trailing signed retail flow (past-only).

    Signed flow per sector per bar = volume[t] * sign(close[t] - close[t-1]),
    accumulated over the trailing `lookback` bars and normalized by the sector's
    average dollar volume over the same window (so the measure is scale-free
    across sectors). Rank 1 = weakest flow (most net selling); computed
    exclusively from data strictly before each bar so the signal is causal at
    the close of bar t-1.
    """
    close = prices[SECTORS].astype(float)
    vol = volumes[SECTORS].astype(float)
    direction = np.sign(close.diff()).fillna(0.0)
    signed = vol.multiply(direction, axis=0)
    flow = signed.rolling(lookback, min_periods=max(5, lookback // 2)).sum()
    dollar_vol = (close * vol).rolling(lookback, min_periods=max(5, lookback // 2)).mean()
    norm = (flow * flow_scale) / dollar_vol.replace(0.0, np.nan)
    rank = norm.rank(axis=1, ascending=True, method="first")
    return rank, norm


def _realized_vol_scale(prices: pd.DataFrame, vol_target: float) -> pd.DataFrame:
    rets = prices[SECTORS].pct_change()
    vol = rets.rolling(VOL_WINDOW, min_periods=VOL_MIN_PERIODS).std() * np.sqrt(252.0)
    scale = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 1.0)
    return scale.fillna(0.0)


def build_flow_signal(
    prices: pd.DataFrame,
    volumes: pd.DataFrame,
    lookback: int,
    flow_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    for sym in SECTORS:
        if sym not in prices.columns or sym not in volumes.columns:
            raise ValueError(f"Missing {sym}")
    rank, _ = _signed_flow_rank(prices, volumes, lookback, flow_scale)
    vol_scale = _realized_vol_scale(prices, vol_target)

    selected = rank.le(N_LONG)
    base_weight = (1.0 / N_LONG) * vol_scale[SECTORS]
    raw = selected.astype(float).multiply(base_weight, axis=0).clip(0.0, MAX_POS)

    rebalance = pd.Series(False, index=prices.index)
    warmup = lookback + VOL_WINDOW
    rebalance.iloc[warmup::REBALANCE_EVERY] = True
    sig = raw.where(rebalance, np.nan)
    sig = sig.reindex(index=prices.index, columns=SECTORS)
    sig.iloc[:warmup] = np.nan
    return sig


def _profit_factor(returns: np.ndarray) -> float:
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 1e-12:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def _max_drawdown(returns: np.ndarray) -> float:
    equity = (1.0 + returns).cumprod()
    roll = pd.Series(equity).expanding().max().to_numpy()
    safe = np.where(roll > 0.0, roll, 1.0)
    dd = (equity - roll) / safe
    return float(abs(dd.min())) if dd.size > 0 else 0.0


def _dict_metrics(returns: np.ndarray) -> dict:
    pf = _profit_factor(returns)
    dd = _max_drawdown(returns)
    return {
        "sharpe": float(sharpe_ratio(returns)),
        "profit_factor": pf,
        "max_drawdown": dd,
        "num_trades": float(len(returns)),
    }
