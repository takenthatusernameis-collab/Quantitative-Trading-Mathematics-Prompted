from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

import run_nf_20261108_15_es_mm_flow_spy as mod


def _fake_inputs(n: int = 2600, seed: int = 150) -> tuple[pd.DataFrame, pd.Series]:
    idx = pd.date_range("2014-01-02", periods=n, freq="B")
    rng = np.random.default_rng(seed)
    spy = 100 * (1 + pd.Series(rng.normal(0.0003, 0.012, n), index=idx)).cumprod()
    es = 100 * (1 + pd.Series(rng.normal(0.0003, 0.012, n), index=idx)).cumprod()
    prices = pd.DataFrame({mod.SPY: spy, mod.ES: es}, index=idx)
    fridays = idx[idx.day_of_week == 4]
    mm_net = pd.Series(100.0, index=fridays, name="mm_net")
    mm_net.iloc[len(mm_net) // 2 :] = 1000.0 + 50.0 * rng.standard_normal(len(mm_net) // 2)
    mm_net = mm_net.astype(float)
    return prices, mm_net


def test_mm_zscore_finite_after_warmup():
    _, mm_net = _fake_inputs()
    z = mod._mm_zscore(mm_net, mm_window=21, z_window=63)
    assert len(z) == len(mm_net)
    assert z.iloc[350:].notna().any()


def test_make_signals_bounds_and_es_zero():
    prices, mm_net = _fake_inputs()
    sig = mod.make_signals(
        prices, mm_net, {"mm_window": 21, "z_window": 63, "entry_scale": 1.5, "vol_target": 0.10}
    )
    assert list(sig.columns) == list(mod.UNIVERSE)
    assert (sig[mod.ES] == 0.0).all()
    assert (sig[mod.SPY] >= 0.0).all()
    assert (sig[mod.SPY] <= mod.MAX_POS + 1e-12).all()


def test_make_signals_no_future_look_ahead():
    prices, mm_net = _fake_inputs()
    sig = mod.make_signals(
        prices, mm_net, {"mm_window": 21, "z_window": 63, "entry_scale": 1.5, "vol_target": 0.10}
    )
    z = sig.attrs["z"]
    # Before the first weekly report, no de-risking (z treated as 0): full vol-targeted exposure.
    first_report = mm_net.index[0]
    pre = sig.loc[sig.index < first_report, mod.SPY]
    assert len(pre) > 0
    vscale = mod._vol_scale(prices, 0.10).reindex(pre.index).fillna(0.0)
    expected = (0.10 * vscale).clip(0.0, mod.MAX_POS)
    assert np.allclose(pre.values, expected.values, atol=1e-9)


def test_de_risks_when_mm_net_abnormally_high():
    prices, mm_net = _fake_inputs()
    params = {"mm_window": 21, "z_window": 63, "entry_scale": 1.0, "vol_target": 0.15}
    sig = mod.make_signals(prices, mm_net, params)
    dates = mm_net.index
    h = len(dates) // 2
    z = mod._mm_zscore(mm_net, params["mm_window"], params["z_window"])
    # z spikes positively right after the crowded long step (finite, elevated).
    assert float(z.iloc[h : h + 10].mean()) > 1.0
    # Corresponding daily exposure window de-risks vs pre-step exposure.
    early = float(sig[mod.SPY].loc[: dates[h - 1]].mean())
    trans = float(sig[mod.SPY].loc[dates[h] : dates[h + 39]].mean())
    assert 0.0 < trans < early * 0.7


def test_metrics_from_result_safe():
    prices, mm_net = _fake_inputs()
    out = mod.run_one(
        prices, mm_net, {"mm_window": 21, "z_window": 63, "entry_scale": 1.5, "vol_target": 0.10}
    )
    m = mod._metrics_from_result(out["result"], pd.Series(True, index=prices.index))
    assert set(m.keys()) == {"n", "sharpe", "profit_factor", "max_drawdown", "trades"}
    assert isinstance(m["trades"], int)


def test_inverse_differs_from_base():
    prices, mm_net = _fake_inputs()
    p = {"mm_window": 21, "z_window": 63, "entry_scale": 1.5, "vol_target": 0.10}
    base = mod.make_signals(prices, mm_net, p)[mod.SPY]
    z = mod._mm_zscore(mm_net, p["mm_window"], p["z_window"])
    z_daily = z.reindex(prices.index, method="ffill").fillna(0.0)
    # Inverse: de-risk when leveraged-money net is abnormally LOW (negative z).
    stress = ((-z_daily).clip(lower=0.0) / p["entry_scale"]).clip(0.0, 1.0)
    raw = (1.0 - stress) * p["vol_target"]
    inv = (raw * mod._vol_scale(prices, p["vol_target"])).fillna(0.0).clip(0.0, mod.MAX_POS)
    assert not np.allclose(base.values, inv.values)


def test_random_and_benchmark():
    prices, mm_net = _fake_inputs()
    mask = pd.Series(True, index=prices.index)
    r = mod.random_exposure_matched(prices, mask, 0.05, 150)
    assert "sharpe" in r and "trades" in r
    b = mod.benchmark_buy_hold(prices, mask)
    assert b["trades"] == 1
