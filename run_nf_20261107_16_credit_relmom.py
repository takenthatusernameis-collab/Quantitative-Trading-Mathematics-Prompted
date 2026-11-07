"""NF-20261107-16 / H128 (Cycle 42): SPY timing from credit-quality relative
momentum (HYG vs LQD trailing return spread). Distinct mechanism: credit
risk-appetite transmission from high-yield vs investment-grade relative
performance to equity risk premium. Free yfinance data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from qtr.backtest.engine import AssetClass, BacktestConfig, CostModel, run_backtest
from qtr.validation.statistics import sharpe_ratio

SPY, HYG, LQD = "SPY", "HYG", "LQD"
UNIVERSE = [SPY, HYG, LQD]
DATA_START, DATA_END = "2010-01-01", "2025-01-05"
TRAIN_END, VAL_END = "2019-12-31", "2021-12-31"
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS = 4

CORR_WINDOWS = [21, 63]
Z_WINDOWS = [63, 126]
ENTRY_ZS = [1.0, 1.5]
EXIT_ZS = [0.0, 0.5]
VOL_TARGETS = [0.10]


def _fetch() -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END, progress=False, auto_adjust=True)[
        "Close"
    ]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    raw = raw.dropna()
    for c in UNIVERSE:
        raw = raw[raw[c] > 0]
    return raw.sort_index()


def _splits(idx):
    train = pd.Series(idx <= pd.Timestamp(TRAIN_END), index=idx)
    val = pd.Series((idx > pd.Timestamp(TRAIN_END)) & (idx <= pd.Timestamp(VAL_END)), index=idx)
    test = pd.Series(idx > pd.Timestamp(VAL_END), index=idx)
    return train, val, test


def relmom_z(hyg, lqd, mom_window, z_window):
    hr = hyg.astype(float).pct_change(mom_window)
    lr = lqd.astype(float).pct_change(mom_window)
    spread = hr - lr
    m = spread.rolling(z_window, min_periods=z_window).mean()
    s = spread.rolling(z_window, min_periods=z_window).std(ddof=0)
    return (spread - m) / s.replace(0.0, np.nan)


def vol_scale(spy_ret, vol_target, window=21):
    rv = spy_ret.rolling(window, min_periods=window).std(ddof=0) * np.sqrt(252)
    scale = vol_target / rv.replace(0.0, np.nan)
    return scale.clip(0.0, 1.0).fillna(0.0)


def build_exposure(z, entry_z, exit_z, vol_target):
    sig = pd.Series(np.nan, index=z.index, dtype=float)
    sig[z > entry_z] = 0.0
    sig[z < exit_z] = 1.0
    sig = sig.ffill().fillna(1.0)
    sig[z.isna()] = 0.0
    return (sig * float(vol_target)).clip(0.0, float(vol_target))


def run_one(prices, params):
    z = relmom_z(prices[HYG], prices[LQD], int(params["mom_window"]), int(params["z_window"]))
    spy_ret = prices[SPY].pct_change().fillna(0.0)
    exposure = build_exposure(
        z, float(params["entry_z"]), float(params["exit_z"]), float(params["vol_target"])
    )
    signals = pd.DataFrame(
        {SPY: (exposure * MAX_POS / float(params["vol_target"])).clip(0.0, MAX_POS)},
        index=prices.index,
    )
    bt = run_backtest(
        prices[[SPY]],
        signals,
        config=BacktestConfig(
            initial_capital=INITIAL_CAPITAL,
            asset_class=AssetClass.EQUITY,
            cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        ),
    )
    return {"backtest": bt, "z": z, "signals": signals}


def _returns(bt, idx):
    eq = bt.equity_curve
    return pd.Series(eq, index=idx[: len(eq)]).pct_change().fillna(0.0)


def metrics_from(bt, mask):
    idx = mask.index
    r = _returns(bt, idx)[mask].dropna()
    if r.empty:
        return {"sharpe": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "trades": 0, "n": 0}
    sh = float(sharpe_ratio(r.values))
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    pf = float(pos / neg) if neg > 1e-12 else (10.0 if pos > 0 else 0.0)
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    tc = int(getattr(bt, "trade_count", 0) or 0)
    if tc == 0 and isinstance(getattr(bt, "metrics", None), dict):
        tc = int(bt.metrics.get("n_trades", bt.metrics.get("num_trades", 0)) or 0)
    return {"sharpe": sh, "profit_factor": pf, "max_drawdown": dd, "trades": tc, "n": int(len(r))}


def main():
    prices = _fetch()
    train_mask, val_mask, test_mask = _splits(prices.index)
    oos_mask = val_mask | test_mask
    best = None
    for mw in CORR_WINDOWS:
        for zw in Z_WINDOWS:
            for ez in ENTRY_ZS:
                for xz in EXIT_ZS:
                    if xz >= ez:
                        continue
                    for vt in VOL_TARGETS:
                        params = {
                            "mom_window": mw,
                            "z_window": zw,
                            "entry_z": ez,
                            "exit_z": xz,
                            "vol_target": vt,
                        }
                        res = run_one(prices, params)
                        m = metrics_from(res["backtest"], train_mask)
                        key = m["sharpe"]
                        if best is None or key > best[0]:
                            best = (key, params, res)
    params = best[1]
    res = best[2]
    oos = metrics_from(res["backtest"], oos_mask)
    out = {"params": params, "oos": oos}
    Path(".experiments/nf_runs").mkdir(parents=True, exist_ok=True)
    Path(".experiments/nf_runs/nf_20261107_16_credit_relmom").mkdir(parents=True, exist_ok=True)
    Path(".experiments/nf_runs/nf_20261107_16_credit_relmom/summary.json").write_text(
        json.dumps(out, indent=2, default=str)
    )
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
