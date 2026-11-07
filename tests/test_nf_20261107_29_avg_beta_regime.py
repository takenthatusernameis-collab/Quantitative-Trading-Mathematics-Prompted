"""Tests for NF-20261107-29 / H129: SPY timing from avg sector beta regime."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_29_avg_beta_regime",
    ROOT / "run_nf_20261107_29_avg_beta_regime.py",
)
assert _SPEC and _SPEC.loader
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)

SECS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]


def _prices(n=600, seed=11):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-02", periods=n)
    spy = 200 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    data = {"SPY": spy}
    for s in SECS:
        beta = 0.8 + rng.random() * 0.6
        data[s] = 50 * np.exp(
            np.cumsum(beta * np.diff(np.log(spy), prepend=np.log(spy[0])) + rng.normal(0, 0.006, n))
        )
    return pd.DataFrame(data, index=idx)


def test_avg_beta_z_finite():
    p = _prices()
    z = MOD.avg_beta_z(p, 21, 126)
    assert np.isfinite(z.dropna()).all()


def test_avg_beta_z_past_only():
    p = _prices()
    z1 = MOD.avg_beta_z(p, 21, 126)
    p2 = p.copy()
    p2.iloc[-1, 1:] *= 1.2
    z2 = MOD.avg_beta_z(p2, 21, 126)
    pd.testing.assert_series_equal(z1.iloc[:-60], z2.iloc[:-60])


def test_build_signals_bounded():
    p = _prices()
    sig = MOD.build_signals(
        p, {"beta_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.10}
    )
    assert (sig["SPY"] >= -1e-12).all()
    assert (sig["SPY"] <= 0.10 + 1e-12).all()
    assert (sig[SECS].abs().sum().sum()) < 1e-12


def test_run_backtest_finite():
    p = _prices()
    sig = MOD.build_signals(
        p, {"beta_window": 21, "z_window": 126, "entry_scale": 1.0, "vol_target": 0.10}
    )
    bt = MOD.run_backtest(p, sig, MOD.make_equity_config())
    assert np.isfinite(bt.returns.fillna(0.0)).all()
    assert np.isfinite(bt.equity_curve).all()
    assert (bt.equity_curve > 0).all()
