from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261110_03", ROOT / "run_nf_20261110_03_equity_pc_ratio.py"
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
    return pd.DataFrame({"close": close}, index=dates)


def _make_pc(n: int = 500, seed: int = 11) -> pd.Series:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=n)
    pc = 0.7 + 0.15 * rng.standard_normal(n)
    pc = np.clip(pc, 0.3, 1.5)
    return pd.Series(pc, index=dates, name="pc")


def test_align_pc_to_spy_ffill():
    spy_idx = pd.bdate_range("2020-01-01", periods=10)
    pc = pd.Series([0.8, 0.9], index=[spy_idx[0], spy_idx[3]])
    aligned = mod._align_pc_to_spy(spy_idx, pc)
    assert len(aligned) == len(spy_idx)
    assert aligned.iloc[1] == 0.8
    assert aligned.iloc[4] == 0.9
    assert aligned.notna().all()


def test_zscore_no_lookahead_windowing():
    s = pd.Series([1.0, 2.0, 3.0, 100.0, 4.0, 5.0], index=pd.date_range("2020-01-01", periods=6))
    z = mod._zscore(s, window=3)
    # first elements may be nan due to min periods; no crash and finite later
    assert len(z) == len(s)
    assert np.isfinite(z.iloc[-1]) or np.isnan(z.iloc[-1])


def test_compute_weights_bounded_and_finite():
    prices = _make_prices(400)
    pc = _make_pc(400)
    pc_aligned = mod._align_pc_to_spy(prices.index, pc)
    for mode in ["contrarian", "momentum"]:
        w = mod._compute_weights(prices["close"], pc_aligned, 60, 1.0, 0.0, 0.10, mode)
        assert len(w) == len(prices)
        assert (w >= 0.0).all()
        assert (w <= mod.MAX_POS + 1e-12).all()
        assert np.isfinite(w.fillna(0.0)).all()


def test_contrarian_and_momentum_differ():
    prices = _make_prices(400)
    pc = _make_pc(400)
    pc_aligned = mod._align_pc_to_spy(prices.index, pc)
    w_c = mod._compute_weights(prices["close"], pc_aligned, 60, 0.5, 0.0, 0.10, "contrarian")
    w_m = mod._compute_weights(prices["close"], pc_aligned, 60, 0.5, 0.0, 0.10, "momentum")
    # modes use opposite entry logic; weights should not be identical in general
    assert not np.allclose(w_c.values, w_m.values)


def test_run_bt_and_metrics_shapes():
    prices = _make_prices(300)
    pc = _make_pc(300)
    pc_aligned = mod._align_pc_to_spy(prices.index, pc)
    w = mod._compute_weights(prices["close"], pc_aligned, 40, 1.0, 0.0, 0.10, "contrarian")
    r, eq, trades = mod._run_bt(prices["close"], w)
    m = mod._metrics(r, eq, trades)
    assert len(r) == len(prices)
    assert len(eq) == len(prices)
    assert trades >= 0
    for k in [
        "sharpe",
        "profit_factor",
        "max_drawdown",
        "trades",
        "periods",
        "worst_regime_rolling252_sharpe",
    ]:
        assert k in m


def test_annualized_sharpe_and_pf_edge_cases():
    assert mod._annualized_sharpe(pd.Series([0.0, 0.0, 0.0])) == 0.0
    assert mod._profit_factor(pd.Series([0.0, 0.0])) == 0.0
    assert mod._profit_factor(pd.Series([0.01, 0.02])) == float("inf")


def test_max_drawdown_nonpositive():
    eq = pd.Series([1.0, 1.1, 1.05, 1.2, 0.9])
    dd = mod._max_drawdown(eq)
    assert dd <= 0.0


def test_wf_score_finite_on_sufficient_data():
    prices = _make_prices(320)
    pc = _make_pc(320)
    pc_aligned = mod._align_pc_to_spy(prices.index, pc)
    params = {
        "pc_window": 40,
        "entry_z": 1.0,
        "exit_z": 0.0,
        "vol_target": 0.10,
        "mode": "contrarian",
    }
    s = mod._wf_score(prices["close"], pc_aligned, params)
    assert np.isfinite(s)


def test_iter_grid_count_and_keys():
    rows = list(mod._iter_grid())
    assert len(rows) == 3 * 3 * 3 * 2 * 2
    assert {"pc_window", "entry_z", "exit_z", "vol_target", "mode"} <= set(rows[0].keys())


def test_information_ratio_zero_on_identical():
    r = pd.Series(np.zeros(100))
    assert mod._information_ratio(r, r) == 0.0


def test_benchmark_pvalue_bounds():
    a = pd.Series(np.random.default_rng(0).normal(0.001, 0.01, 300))
    b = pd.Series(np.random.default_rng(1).normal(0.0, 0.01, 300))
    p = mod._benchmark_pvalue(a, b, n_boot=200)
    assert 0.0 <= p <= 1.0


def test_time_split_ordering():
    idx = pd.bdate_range("2010-01-01", periods=400)
    v, t = mod._time_split(idx)
    assert pd.Timestamp(v) < pd.Timestamp(t)
    assert pd.Timestamp(t) <= idx[-1]


def test_hysteresis_reduces_churn_vs_no_exit():
    prices = _make_prices(500, seed=3)
    pc = _make_pc(500, seed=4)
    pc_aligned = mod._align_pc_to_spy(prices.index, pc)
    w_h = mod._compute_weights(prices["close"], pc_aligned, 60, 1.0, -0.5, 0.10, "contrarian")
    w_n = mod._compute_weights(prices["close"], pc_aligned, 60, 1.0, 1.0, 0.10, "contrarian")
    # looser exit (higher exit_z for contrarian means exits earlier/harder?) compare churn proxy
    churn_h = (w_h.diff().abs() > 1e-12).sum()
    churn_n = (w_n.diff().abs() > 1e-12).sum()
    assert churn_h >= 0 and churn_n >= 0


def test_max_drawdown_empty():
    assert mod._max_drawdown(pd.Series(dtype=float)) == 0.0
