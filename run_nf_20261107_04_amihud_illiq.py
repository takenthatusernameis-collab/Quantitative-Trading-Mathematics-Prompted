"""NF-20261107-04 / H121 (pre-registered, Cycle 35): SPY Amihud
illiquidity-stress regime timing.

Signal = trailing Amihud illiquidity = |ret| / dollar_volume (close*volume),
z-scored over `window`. Reduce vol-targeted long SPY when z > entry_z
(extreme illiquidity stress), flat otherwise; hysteresis exit at exit_z.
Engine signals.shift(1) gives t->t+1 causality. No src/qtr change.
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
from qtr.data.fetcher import DataFetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261107_04_amihud_illiq"
EXPERIMENT_DESC = "NF-20261107-04/H121: SPY Amihud illiquidity-stress regime timing."

SPY = "SPY"
UNIVERSE = [SPY]
BENCHMARK = SPY

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

MAX_POS = 1.0
COSTS = CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0)


def amihud_series(close, volume):
    ret = close.pct_change().abs()
    dv = (close * volume).replace(0, np.nan)
    return (ret / dv).replace([np.inf, -np.inf], np.nan)


def amihud_z(close, volume, window):
    a = amihud_series(close, volume)
    m = a.rolling(window, min_periods=window).mean()
    s = a.rolling(window, min_periods=window).std(ddof=0)
    return (a - m) / s.replace(0, np.nan)


def build_exposure(illiq_z, entry_z, exit_z, vol_target):
    z = illiq_z.fillna(0.0)
    n = len(z)
    exp = np.zeros(n)
    in_pos = False
    for i in range(n):
        if not in_pos:
            if z.iloc[i] <= entry_z:
                in_pos = True
        else:
            if z.iloc[i] > exit_z:
                in_pos = False
        exp[i] = vol_target if in_pos else 0.0
    return pd.Series(exp, index=z.index)


def vol_scale(ret, vol_target):
    rv = ret.rolling(20, min_periods=20).std(ddof=0) * np.sqrt(252)
    sc = vol_target / rv.replace(0, np.nan)
    return sc.clip(upper=1.0).fillna(0.0)


def run_one(prices, params, volume):
    close = prices["SPY"]
    z = amihud_z(close, volume, params["window"])
    ret = close.pct_change().fillna(0.0)
    base = build_exposure(z, params["entry_z"], params["exit_z"], params["vol_target"])
    vs = vol_scale(ret, params["vol_target"])
    exposure = (base * vs).clip(0, MAX_POS)
    exposure = exposure.shift(1).fillna(0.0)
    cfg = BacktestConfig(cost_model=COSTS, asset_class=AssetClass.EQUITY)
    bt = run_backtest(prices[["SPY"]], exposure.to_frame("SPY"), cfg)
    return {"backtest": bt, "params": params}


def metrics_from(bt, mask):
    r = bt.returns.fillna(0.0)
    sel = r[mask.reindex(r.index).fillna(False)]
    if len(sel) == 0:
        return {"sharpe": 0.0, "trades": 0, "profit_factor": 0.0, "max_drawdown": 0.0, "n": 0}
    sh = sharpe_ratio(sel)
    pf = (sel[sel > 0].sum() / max(-sel[sel < 0].sum(), 1e-12)) if (sel < 0).any() else float("inf")
    eq = (1 + sel).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    trades = int((bt.trades > 0).sum()) if hasattr(bt, "trades") else 0
    return {
        "sharpe": float(sh),
        "trades": trades,
        "profit_factor": float(pf),
        "max_drawdown": float(dd),
        "n": len(sel),
    }


def evaluate_gates(train, oos, wf_stability, worst_regime_sharpe, bench, pert):
    gates = {}
    gates["sharpe"] = oos["sharpe"] >= 1.0
    gates["trades"] = oos["trades"] >= 200
    gates["pf"] = oos["profit_factor"] >= 1.3
    gates["dd"] = oos["max_drawdown"] >= -0.15
    gates["wf"] = wf_stability >= 0.7
    gates["worst_regime"] = worst_regime_sharpe >= 0.3
    gates["bench_p"] = bench.get("p_value", 1.0) < 0.05
    gates["perturbation"] = pert.get("min_ratio_vs_optimum", 0.0) >= 0.5
    return all(gates.values()), gates


def _ablations(prices, params, mask):
    return {"buy_hold_spy": {"sharpe": 0.0}}


def main():
    fetcher = DataFetcher()
    df = fetcher.fetch(SPY, DATA_START, DATA_END)
    prices = pd.DataFrame({SPY: df["Close"]})
    volume = df["Volume"]
    print("rows", len(prices))
    res = run_one(prices, {"window": 20, "entry_z": 1.5, "exit_z": 0.5, "vol_target": 0.10}, volume)
    print(res["backtest"].returns.describe())


if __name__ == "__main__":
    main()
