from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261104_03", ROOT / "run_nf_20261104_03_es_spy_basis.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _make_prices(n: int = 500, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=n)
    ret_spy = rng.normal(0.0003, 0.01, size=n)
    spy = 200.0 * np.exp(np.cumsum(ret_spy))
    basis = 0.002 + 0.001 * rng.standard_normal(n)
    es = spy * (1.0 + basis)
    return pd.DataFrame({"ES=F": es, "SPY": spy}, index=dates)


def test_zscore_no_lookahead_length():
    s = pd.Series(np.linspace(0.0, 1.0, 50), index=pd.bdate_range("2020-01-01", periods=50))
    z = mod._zscore(s, window=10)
    assert len(z) == len(s)
    assert np.isnan(z.iloc[:9]).all()


def test_compute_weights_bounded_and_finite():
    prices = _make_prices(400)
    z = mod._basis_z(prices, 21)
    w = mod._compute_weights(prices, z, 21, 1.0, 0.0, 0.10)
    assert (w >= -mod.MAX_POS - 1e-12).all().all()
    assert (w <= mod.MAX_POS + 1e-12).all().all()
    assert np.isfinite(w.fillna(0.0)).all().all()
    assert (w["ES=F"] == 0).all()


def test_basis_z_shape():
    prices = _make_prices(300)
    z = mod._basis_z(prices, 21)
    assert len(z) == len(prices)
    assert z.index.equals(prices.index)


def test_run_bt_and_metrics_shapes():
    prices = _make_prices(350)
    z = mod._basis_z(prices, 21)
    w = mod._compute_weights(prices, z, 21, 1.0, 0.0, 0.10)
    strat_ret, eq, trades = mod._run_bt(prices, w)
    m = mod._metrics(strat_ret, eq, trades)
    assert len(strat_ret) == len(prices)
    assert len(eq) == len(prices)
    for k in [
        "sharpe",
        "profit_factor",
        "max_drawdown",
        "trades",
        "periods",
        "total_return",
        "worst_regime_rolling252_sharpe",
    ]:
        assert k in m
    assert m["trades"] >= 0


def test_wf_score_returns_finite_or_sentinel():
    prices = _make_prices(500)
    params = {"basis_window": 21, "entry_z": 1.0, "exit_z": 0.0, "vol_target": 0.10}
    score = mod._wf_score(prices, params)
    assert np.isfinite(score) or score == -999.0


def test_grid_count():
    params = list(mod._iter_grid())
    assert len(params) == 36
    assert all(p["exit_z"] <= p["entry_z"] for p in params)


def test_constants():
    assert mod.EXPERIMENT == "nf_20261104_03_es_spy_basis"
    assert mod.NF_ID == "NF-20261104-03"
    assert mod.HYPOTHESIS == "H181"
    assert mod.MAX_POS == 0.5
    assert mod.SEED == 42


def test_perturbation_oos_sharpes():
    prices = _make_prices(500)
    selected = {"basis_window": 21, "entry_z": 1.0, "exit_z": 0.0, "vol_target": 0.10}
    out = mod._perturbation_oos_sharpes(
        prices, selected, str(prices.index[300].date()), str(prices.index[-1].date())
    )
    assert isinstance(out, list)
    assert len(out) > 0
    assert all(np.isfinite(s) for s in out)
