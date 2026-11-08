"""NF-20261107-52 / H148 (pre-registered, Cycle 62): SPY timing from EEM-vs-SPY
realized-volatility divergence (cross-asset volatility transmission).

Observable (past-only, PIT daily adjusted Close):
  rv_EEM_t = std(logret_EEM, rv_window); rv_SPY_t = std(logret_SPY, rv_window)
  div_t = rv_EEM_t - rv_SPY_t
  z_t = (div_t - rolling_mean(div, z_window)) / rolling_std(div, z_window)

Mechanism: abnormal EEM-vs-SPY vol divergence (EM stress) proxies global risk
transmission; de-risk vol-targeted long SPY when z abnormally high. 1-bar delay,
long-only.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.validation.statistics import sharpe_ratio  # noqa: E402

EXPERIMENT_DESC = (
    "NF-20261107-52/H148: SPY timing from EEM-vs-SPY realized-vol divergence. "
    "z-score of rolling RV difference; de-risk vol-targeted long SPY when z "
    "abnormally high. 1-bar delay."
)

SPY = "SPY"
EEM = "EEM"
UNIVERSE = [SPY, EEM]
DATA_START = "2010-01-01"
DATA_END = "2025-01-05"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

RV_WINDOWS = [21, 63]
Z_WINDOWS = [126, 252]
ENTRY_SCALES = [1.0, 2.0]
VOL_TARGETS = [0.10, 0.15]


def _fetch() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END, progress=False, auto_adjust=True)
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"][UNIVERSE]
    else:
        close = raw[UNIVERSE]
    df = close.dropna().sort_index()
    df = df[(df > 0).all(axis=1)]
    if df.empty:
        raise RuntimeError("empty price data")
    return df


def _splits(index: pd.DatetimeIndex):
    train = pd.Series(index <= pd.Timestamp(TRAIN_END), index=index)
    val = pd.Series(
        (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END)),
        index=index,
    )
    test = pd.Series(index > pd.Timestamp(VAL_END), index=index)
    return train, val, test


def rv_divergence(prices: pd.DataFrame, rv_window: int, z_window: int) -> pd.Series:
    lr = np.log(prices[[SPY, EEM]]).diff()
    rv_spy = lr[SPY].rolling(rv_window, min_periods=max(10, rv_window // 2)).std()
    rv_eem = lr[EEM].rolling(rv_window, min_periods=max(10, rv_window // 2)).std()
    div = rv_eem - rv_spy
    m = div.rolling(z_window, min_periods=max(30, z_window // 4)).mean()
    s = div.rolling(z_window, min_periods=max(30, z_window // 4)).std()
    z = (div - m) / s.replace(0, np.nan)
    return z


def build_signal(prices, rv_window, z_window, entry_scale, vol_target):
    z = rv_divergence(prices, rv_window, z_window)
    stress = ((z).clip(0) / entry_scale).clip(0, 1)
    exposure = (1 - stress) * vol_target
    exposure = exposure.clip(0, MAX_POS)
    # vol targeting scaling using SPY realized vol
    lr = np.log(prices[SPY]).diff()
    vscale = 1.0 / lr.rolling(21, min_periods=10).std().clip(lower=1e-6)
    vscale = vscale.clip(upper=5.0)
    exposure = (exposure * vscale).clip(0, MAX_POS)
    signal = pd.DataFrame({SPY: exposure}, index=prices.index)
    return signal, z


def run_one(prices, rv_window, z_window, entry_scale, vol_target, split_mask):
    signal, z = build_signal(prices, rv_window, z_window, entry_scale, vol_target)
    cfg = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        max_position_size=MAX_POS,
    )
    res = run_backtest(prices[[SPY]], signal, cfg)
    # filter by split mask on index
    ret = res.returns.loc[split_mask[split_mask].index] if False else res.returns
    # simpler: mask returns
    m = split_mask.reindex(res.returns.index).fillna(False).astype(bool)
    r = res.returns[m]
    return res, r


def main():
    prices = _fetch()
    train_m, val_m, test_m = _splits(prices.index)
    oos_mask = val_m | test_m
    best = None
    grid_rows = []
    for rv in RV_WINDOWS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    res, tr = run_one(prices, rv, zw, es, vt, train_m)
                    # train sharpe via returns
                    sh = sharpe_ratio(tr) if len(tr) else 0.0
                    grid_rows.append(
                        {"rv_window": rv, "z_window": zw, "entry_scale": es, "vol_target": vt, "train_sharpe": float(sh)}
                    )
                    if best is None or sh > best[0]:
                        best = (sh, rv, zw, es, vt)
    _, rv, zw, es, vt = best
    res, oos_ret = run_one(prices, rv, zw, es, vt, oos_mask)
    sh_oos = sharpe_ratio(oos_ret) if len(oos_ret) else 0.0
    summary = {
        "nf_id": "NF-20261107-52",
        "hypothesis": "H148",
        "selected": {"rv_window": rv, "z_window": zw, "entry_scale": es, "vol_target": vt},
        "oos_sharpe": float(sh_oos),
        "n_trades": int(res.n_trades) if hasattr(res, "n_trades") else None,
        "verdict": "REJECT" if sh_oos < 1.0 else "PASS",
    }
    outdir = Path(".experiments/nf_runs/nf_20261107_52_eem_spy_rvdiv")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    (outdir / "grid.csv").write_text(pd.DataFrame(grid_rows).to_csv(index=False))
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    t0 = time.time()
    main()
    print("elapsed", round(time.time() - t0, 2))