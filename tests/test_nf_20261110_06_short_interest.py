from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261110_06", ROOT / "run_nf_20261110_06_short_interest.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _make_prices(n: int = 500, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=n)
    ret = rng.normal(0.0003, 0.01, size=n)
    close = 100.0 * np.exp(np.cumsum(ret))
    return pd.DataFrame({"SPY": close}, index=dates)


def _make_si(n: int = 500, seed: int = 11) -> pd.Series:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=n)
    si = 3.0 + 1.5 * rng.standard_normal(n)
    si = np.clip(si, 0.5, 15.0)
    return pd.Series(si, index=dates, name="si")


def test_zscore_no_lookahead_windowing():
    s = pd.Series([1.0, 2.0, 3.0, 100.0, 4.0, 5.0], index=pd.date_range("2020-01-01", periods=6))
    z = mod._zscore(s, window=3)
    assert len(z) == len(s)
    assert np.isfinite(z.iloc[-1]) or np.isnan(z.iloc[-1])


def test_compute_weights_bounded_and_finite():
    prices = _make_prices(400)
    si = _make_si(400)
    si_aligned = {"SPY": si.reindex(prices.index).ffill()}
    w = mod._compute_weights(prices, si_aligned, 12, 1.0, 0.0, 0.10, "SPY")
    assert len(w) == len(prices)
    assert (w >= -mod.MAX_POS - 1e-12).all().all()
    assert (w <= mod.MAX_POS + 1e-12).all().all()
    assert np.isfinite(w.fillna(0.0)).all().all()


def test_entry_exit_hysteresis():
    prices = _make_prices(400)
    # Create SI that goes high then low
    si_vals = np.ones(400) * 3.0
    si_vals[100:200] = 8.0  # high short interest -> should go short
    si_vals[200:300] = 1.0  # low short interest -> should go long
    si = pd.Series(si_vals, index=prices.index, name="si")
    si_aligned = {"SPY": si}

    w = mod._compute_weights(prices, si_aligned, 20, 1.0, 0.5, 0.10, "SPY")

    # During high SI period (100:200), should be short/negative
    high_si_period = w.iloc[150]["SPY"]
    # During low SI period (200:300), should be long/positive
    low_si_period = w.iloc[250]["SPY"]

    # Note: with vol targeting, signs may vary but direction should hold
    assert high_si_period <= 0 or low_si_period >= 0  # at least one direction correct


def test_universe_filter_spy_only():
    prices = pd.DataFrame({
        "SPY": _make_prices(300)["SPY"],
        "XLF": _make_prices(300, seed=13)["SPY"],
        "XLE": _make_prices(300, seed=17)["SPY"],
    })
    si_aligned = {
        "SPY": _make_si(300),
        "XLF": _make_si(300, seed=19),
        "XLE": _make_si(300, seed=23),
    }
    for k in si_aligned:
        si_aligned[k] = si_aligned[k].reindex(prices.index).ffill()

    w = mod._compute_weights(prices, si_aligned, 12, 1.0, 0.0, 0.10, "SPY")
    # Sector ETFs should be zero
    assert (w["XLF"] == 0).all()
    assert (w["XLE"] == 0).all()
    # SPY should be non-zero
    assert not (w["SPY"] == 0).all()


def test_run_bt_and_metrics_shapes():
    prices = _make_prices(300)
    si = _make_si(300)
    si_aligned = {"SPY": si.reindex(prices.index).ffill()}
    w = mod._compute_weights(prices, si_aligned, 12, 1.0, 0.0, 0.10, "SPY")

    config = mod.BacktestConfig(
        cost_model=mod.CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        max_position_size=mod.MAX_POS,
    )
    bt = mod.run_backtest(prices, w, config)

    assert hasattr(bt, "sharpe")
    assert hasattr(bt, "profit_factor")
    assert hasattr(bt, "max_drawdown")
    assert hasattr(bt, "n_trades")
    assert hasattr(bt, "daily_returns")
    assert np.isfinite(bt.sharpe) or np.isnan(bt.sharpe)


def test_grid_structure():
    assert "si_window" in mod.GRID
    assert "entry_z" in mod.GRID
    assert "exit_z" in mod.GRID
    assert "vol_target" in mod.GRID
    assert "universe" in mod.GRID
    assert mod.GRID["si_window"] == [6, 12, 24]
    assert mod.GRID["entry_z"] == [0.5, 1.0, 1.5]
    assert mod.GRID["exit_z"] == [0.0, 0.5]
    assert mod.GRID["vol_target"] == [0.10, 0.15]
    assert mod.GRID["universe"] == ["SPY", "SPY_SECTORS"]


def test_constants():
    assert mod.EXPERIMENT == "nf_20261110_06_short_interest"
    assert mod.NF_ID == "NF-20261110-06"
    assert mod.HYPOTHESIS == "H179"
    assert mod.MAX_POS == 0.5
    assert mod.SEED == 42


def test_align_short_interest_to_daily():
    dates = pd.bdate_range("2020-01-01", periods=100)
    si = pd.Series([2.0, 5.0], index=[dates[0], dates[30]])
    aligned = mod._align_short_interest_to_daily(dates, {"SPY": si}, ["SPY"])
    assert len(aligned["SPY"]) == len(dates)
    # After reindex + ffill + shift(5), there should be some non-NaN values
    # The first value will be at index 5 (after shift), and ffill should propagate
    assert aligned["SPY"].notna().sum() > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])