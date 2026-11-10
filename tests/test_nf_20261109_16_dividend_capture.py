from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261109_16", ROOT / "run_nf_20261109_16_dividend_capture.py"
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
    return pd.DataFrame({"SPY": close, "XLF": close * 0.9}, index=dates)


def _make_divs(n: int = 500, seed: int = 3) -> dict[str, pd.Series]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-02", periods=n)
    div_spy = pd.Series(0.0, index=dates)
    div_spy.iloc[50] = 1.0  # ex-date at loc 50
    div_spy.iloc[120] = 1.0  # ex-date at loc 120
    div_xlf = pd.Series(0.0, index=dates)
    div_xlf.iloc[80] = 0.5
    return {"SPY": div_spy, "XLF": div_xlf}


def test_compute_weights_bounded_and_finite():
    prices = _make_prices(400)
    divs = _make_divs(400)
    aligned = {t: divs[t].reindex(prices.index).fillna(0.0) for t in prices.columns}
    w = mod._compute_weights(prices, aligned, 1, 0.10, "SPY")
    assert len(w) == len(prices)
    assert (w >= -1e-12).all().all()
    assert (w <= mod.MAX_POS + 1e-12).all().all()
    assert np.isfinite(w.fillna(0.0)).all().all()
    # XLF must be zero under SPY-only universe
    assert (w["XLF"] == 0).all()


def test_capture_days_only():
    prices = _make_prices(300)
    divs = _make_divs(300)
    aligned = {t: divs[t].reindex(prices.index).fillna(0.0) for t in prices.columns}
    w = mod._compute_weights(prices, aligned, 0, 0.10, "SPY")
    # Active on day before each SPY ex-date (locs 49 and 119), flat elsewhere
    assert float(w["SPY"].iloc[49]) > 0
    assert float(w["SPY"].iloc[50]) == 0  # hold_days=0 -> exit at ex-date close
    assert float(w["SPY"].iloc[119]) > 0
    off = w["SPY"][(w["SPY"].index != prices.index[49]) & (w["SPY"].index != prices.index[119])]
    assert (off == 0).all()


def test_hold_days_extends_position():
    prices = _make_prices(300)
    divs = _make_divs(300)
    aligned = {t: divs[t].reindex(prices.index).fillna(0.0) for t in prices.columns}
    w0 = mod._compute_weights(prices, aligned, 0, 0.10, "SPY")
    w2 = mod._compute_weights(prices, aligned, 2, 0.10, "SPY")
    # hold_days=2 active on locs 49,50,51 and 119,120,121
    assert (
        float(w2["SPY"].iloc[49]) > 0
        and float(w2["SPY"].iloc[50]) > 0
        and float(w2["SPY"].iloc[51]) > 0
    )
    assert float(w2["SPY"].iloc[52]) == 0
    assert float(w0["SPY"].iloc[50]) == 0


def test_universe_sectors_active():
    prices = _make_prices(300)
    divs = _make_divs(300)
    aligned = {t: divs[t].reindex(prices.index).fillna(0.0) for t in prices.columns}
    w = mod._compute_weights(prices, aligned, 1, 0.10, "SPY_SECTORS")
    # XLF active around its ex-date loc 80 (and 79 day before)
    assert float(w["XLF"].iloc[79]) > 0 or float(w["XLF"].iloc[80]) > 0


def test_run_bt_and_metrics_shapes():
    prices = _make_prices(300)
    divs = _make_divs(300)
    aligned = {t: divs[t].reindex(prices.index).fillna(0.0) for t in prices.columns}
    w = mod._compute_weights(prices, aligned, 1, 0.10, "SPY")
    strat_ret, eq, trades, pos = mod._run_bt(prices, w)
    m = mod._metrics(strat_ret, eq, trades)
    assert len(strat_ret) == len(prices)
    assert len(eq) == len(prices)
    assert len(pos) == len(prices)
    assert isinstance(trades, int)
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


def test_credit_dividends_boosts_on_ex_date():
    prices = _make_prices(200)
    divs = _make_divs(200)
    aligned = {t: divs[t].reindex(prices.index).fillna(0.0) for t in prices.columns}
    w = mod._compute_weights(prices, aligned, 1, 0.15, "SPY")
    ret, eq, trades, pos = mod._run_bt(prices, w)
    credited = mod._credit_dividends(ret, pos.reindex(prices.index), prices, aligned)
    # On SPY ex-date loc 50, position held from loc 49 -> dividend credit > 0
    assert float(credited.iloc[50]) > float(ret.iloc[50])
    # Non-ex-date loc 51 unchanged
    assert float(credited.iloc[51]) == float(ret.iloc[51])


def test_wf_score_shape():
    prices = _make_prices(400)
    divs = _make_divs(400)
    aligned = {t: divs[t].reindex(prices.index).fillna(0.0) for t in prices.columns}
    score = mod._wf_score(prices, aligned, {"hold_days": 1, "vol_target": 0.10, "universe": "SPY"})
    assert np.isfinite(score) or score == -999.0


def test_grid_structure():
    assert "hold_days" in mod.GRID
    assert "vol_target" in mod.GRID
    assert "universe" in mod.GRID
    assert mod.GRID["hold_days"] == [0, 1, 2]
    assert mod.GRID["vol_target"] == [0.10, 0.15]
    assert mod.GRID["universe"] == ["SPY", "SPY_SECTORS"]


def test_constants():
    assert mod.EXPERIMENT == "nf_20261109_16_dividend_capture"
    assert mod.NF_ID == "NF-20261109-16"
    assert mod.HYPOTHESIS == "H180"
    assert mod.MAX_POS == 0.5
    assert mod.SEED == 42


def test_perturbation_oos_sharpes():
    prices = _make_prices(400)
    divs = _make_divs(400)
    aligned = {t: divs[t].reindex(prices.index).fillna(0.0) for t in prices.columns}
    out = mod._perturbation_oos_sharpes(
        prices,
        aligned,
        {"hold_days": 1, "vol_target": 0.10, "universe": "SPY"},
        str(prices.index[200].date()),
        str(prices.index[-1].date()),
    )
    assert isinstance(out, list)
    assert all(np.isfinite(s) for s in out)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
