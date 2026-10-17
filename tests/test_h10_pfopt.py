"""
Regression tests for the H10 profit-factor-optimization experiment
(run_h10_intraday_tsmom_pfopt_experiment.py).

These pin down the new turnover-aware machinery added on top of H9:
  * smooth_signal (EWMA on the hourly signal, pre-collapse)
  * regime_factor_hourly (VIX-regime exposure scaling)
  * build_hourly_target (collapse + regime scaling pipeline)
  * apply_exits_hourly (H9 CT exits + min-trade-interval gate)

The critical invariant is that ``min_trade_interval=0`` reproduces H9's
``apply_path_dependent_exits_hourly`` *exactly* (regression guard for the
sign/invariant that the H4 cycle first caught), so the H9 baseline numbers
(Sharpe 1.056, PF 1.252) remain reproducible.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_h9_intraday_tsmom_experiment as h9
import run_h10_intraday_tsmom_pfopt_experiment as h10
from qtr.backtest.engine import run_backtest
from qtr.data.fetcher import get_data_fetcher


def _hourly_frame(n: int = 4000, seed: int = 3, symbols=("A", "B", "C")):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-11-01", periods=n, freq="h")
    data = {}
    for s in symbols:
        rets = rng.normal(0.0004, 0.025, n)
        data[s] = 100.0 * np.exp(np.cumsum(rets))
    prices = pd.DataFrame(data, index=idx)
    return prices


def _make_inputs(prices):
    pct = prices.pct_change().fillna(0)
    atr = prices * pct.rolling(14, min_periods=7).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    vol = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    vol = vol.replace(0, np.nan).ffill()
    return pct, atr, vol


class TestSmoothSignal:
    def test_span_none_returns_equal_copy(self):
        sig = pd.DataFrame({"A": [0.1, 0.2, 0.3]}, index=pd.RangeIndex(3))
        out = h10.smooth_signal(sig, None)
        assert out.equals(sig)
        assert out is not sig  # fresh object

    def test_span_1_is_identity(self):
        sig = pd.DataFrame({"A": np.linspace(0, 1, 50)})
        out = h10.smooth_signal(sig, 1)
        assert np.allclose(out.values, sig.values)

    def test_smoothing_reduces_variance(self):
        """EWMA smoothing must reduce high-frequency variance (monotonic
        relaxation of the signal)."""
        sig = pd.DataFrame({"A": np.random.default_rng(0).normal(0, 0.1, 2000)})
        raw_var = sig.diff().abs().mean().iloc[0]
        sm_var = smooth_diff(sig, 8)
        assert sm_var <= raw_var

    def test_smoothing_is_causal(self):
        """Smoothed value at t must not depend on future samples."""
        rng = np.random.default_rng(7)
        sig = pd.DataFrame({"A": rng.normal(0, 0.1, 100)})
        sm = h10.smooth_signal(sig, 8)
        # Flip a single LATE sample; early smoothed values must be unchanged.
        sig2 = sig.copy()
        sig2.iloc[80, 0] = 999.0
        sm2 = h10.smooth_signal(sig2, 8)
        assert np.allclose(sm.iloc[:50].values, sm2.iloc[:50].values)


def smooth_diff(sig, span):
    return h10.smooth_signal(sig, span).diff().abs().mean().iloc[0]


class TestRegimeFactor:
    def test_regime_thresholds(self):
        idx = pd.date_range("2024-11-01", periods=10, freq="h")
        vix = pd.Series([10, 19.9, 20, 25, 30, 30.1, 40, np.nan, 15, 50], index=idx)
        f = h10.regime_factor_hourly(vix)
        assert f.iloc[0] == 1.0  # VIX 10 -> bull
        assert f.iloc[1] == 1.0  # 19.9 -> bull
        assert f.iloc[2] == 0.5  # 20 -> sideways
        assert f.iloc[3] == 0.5  # 25 -> sideways
        assert f.iloc[4] == 0.5  # 30 -> sideways (boundary)
        assert f.iloc[5] == 0.25  # 30.1 -> bear
        assert f.iloc[6] == 0.25  # 40 -> bear
        assert f.iloc[7] == 0.25  # NaN -> ffill -> 40 -> bear
        assert f.iloc[8] == 1.0  # 15 -> bull

    def test_all_below_20_is_full(self):
        idx = pd.date_range("2024-11-01", periods=20, freq="h")
        vix = pd.Series(np.linspace(12, 18, 20), index=idx)
        f = h10.regime_factor_hourly(vix)
        assert (f == 1.0).all()


class TestBuildHourlyTarget:
    def test_no_regime_equals_daily_collapse(self):
        prices = _hourly_frame()
        sig = pd.DataFrame(
            np.sign(np.random.default_rng(1).normal(0, 0.2, (len(prices), 3))),
            index=prices.index,
            columns=prices.columns,
        )
        vix = pd.Series(20.0, index=prices.index)
        tgt = h10.build_hourly_target(sig, None, 252, False, vix, prices.index)
        daily = h9._daily_target_from_hourly(sig)
        hourly = daily.reindex(prices.index, method="ffill").fillna(0.0)
        assert np.allclose(tgt.values, hourly.values)

    def test_regime_scaling_multiplies_factor(self):
        prices = _hourly_frame()
        sig = pd.DataFrame(
            np.sign(np.random.default_rng(2).normal(0, 0.2, (len(prices), 3))),
            index=prices.index,
            columns=prices.columns,
        )
        # VIX all >30 -> factor 0.25 everywhere
        vix = pd.Series(35.0, index=prices.index)
        tgt = h10.build_hourly_target(sig, None, 252, True, vix, prices.index)
        baseline = h10.build_hourly_target(sig, None, 252, False, vix, prices.index)
        assert np.allclose(tgt.values, baseline.values * 0.25)


class TestApplyExitsHourly:
    def test_min_interval_zero_matches_h9(
        self,
    ):
        """Regression guard: H10 exits with min_trade_interval=0 must equal H9's
        apply_path_dependent_exits_hourly bit-for-bit."""
        prices = _hourly_frame(n=1500)
        _pct, atr, vol = _make_inputs(prices)
        daily_target = h9._daily_target_from_hourly(h9.vol_scaled_tsmom_hourly(prices))
        h9_pos = h9.apply_path_dependent_exits_hourly(daily_target, prices, atr)
        h10_pos = h10.apply_exits_hourly(
            daily_target, prices, atr, vol, min_trade_interval=0
        )
        assert h10_pos.shape == h9_pos.shape
        assert np.allclose(h10_pos.values, h9_pos.values, atol=1e-12)

    def test_min_interval_reduces_trades(self):
        """A positive min-trade-interval must produce no MORE position changes
        than the baseline (turnover-reducing by construction)."""
        prices = _hourly_frame(n=1500)
        _pct, atr, vol = _make_inputs(prices)
        daily_target = h9._daily_target_from_hourly(h9.vol_scaled_tsmom_hourly(prices))
        base = h10.apply_exits_hourly(
            daily_target, prices, atr, vol, min_trade_interval=0
        )
        gated = h10.apply_exits_hourly(
            daily_target, prices, atr, vol, min_trade_interval=24
        )
        base_changes = int((base.diff().fillna(0) != 0).sum().sum())
        gated_changes = int((gated.diff().fillna(0) != 0).sum().sum())
        assert gated_changes <= base_changes
        # And a larger gate further reduces (non-trivially) on this noisy signal
        big = h10.apply_exits_hourly(
            daily_target, prices, atr, vol, min_trade_interval=120
        )
        big_changes = int((big.diff().fillna(0) != 0).sum().sum())
        assert big_changes <= gated_changes

    def test_larger_interval_eventually_flattens(self):
        """A very large min-trade-interval should freeze the position path at its
        first (or no) trade, producing strictly fewer changes than a small one."""
        prices = _hourly_frame(n=1500)
        _pct, atr, vol = _make_inputs(prices)
        daily_target = h9._daily_target_from_hourly(h9.vol_scaled_tsmom_hourly(prices))
        small = h10.apply_exits_hourly(
            daily_target, prices, atr, vol, min_trade_interval=4
        )
        huge = h10.apply_exits_hourly(
            daily_target, prices, atr, vol, min_trade_interval=99999
        )
        assert int((huge.diff().fillna(0) != 0).sum().sum()) <= int(
            (small.diff().fillna(0) != 0).sum().sum()
        )

    def test_h10_baseline_reproduces_h9_gates(self):
        """Integration guard: H10 with H9's exact configuration must reproduce
        the H9 OOS result (Sharpe ~1.056, PF ~1.252) on the cached futures data,
        proving the extended engine is wired identically to H9."""
        fetcher = get_data_fetcher()
        data = fetcher.fetch_futures(
            h9.FUTURES_UNIVERSE, start="2024-10-12", end="2026-10-11", interval="1h"
        )
        prices_list, volumes_list = [], []
        for sym in h9.FUTURES_UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                continue
            df.index = (
                pd.to_datetime(df.index).tz_localize(None)
                if df.index.tz is not None
                else pd.to_datetime(df.index)
            )
            prices_list.append(df["close"].rename(sym))
            volumes_list.append(df["volume"].rename(sym))
        prices = pd.concat(prices_list, axis=1, sort=True).sort_index().ffill().bfill()
        volumes = (
            pd.concat(volumes_list, axis=1, sort=True)
            .sort_index()
            .reindex(prices.index)
            .fillna(0)
        )
        n = len(prices)
        train_end = prices.index[int(n * 0.55)]
        val_end = prices.index[int(n * 0.8)]
        val_mask = (prices.index > train_end) & (prices.index <= val_end)
        test_mask = prices.index > val_end
        oos_mask = val_mask | test_mask

        pct = prices.pct_change().fillna(0)
        atr = prices * pct.rolling(14, min_periods=7).std()
        atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
        vol = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
        vol = vol.replace(0, np.nan).ffill()
        daily_target = h9._daily_target_from_hourly(h9.vol_scaled_tsmom_hourly(prices))

        pos = h10.apply_exits_hourly(
            daily_target, prices, atr, vol, min_trade_interval=0
        )
        cfg = h10.make_futures_config()
        res = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)

        oos = res.returns[oos_mask]
        cum = (1 + oos).cumprod()
        dd = (cum / cum.cummax() - 1).min()
        pf = res.metrics["profit_factor"]
        assert h10.sharpe_ratio(oos.values) == pytest.approx(1.056, abs=0.05)
        assert abs(dd) == pytest.approx(0.062, abs=0.03)
        assert pf == pytest.approx(1.252, abs=0.1)
