"""
Regression tests for the H11 robustness / certification experiment
(run_h11_robustness_experiment.py).

Pins the new machinery added on top of H10:
  * make_cost_stressed_config (cost-model stress scaling)
  * per_symbol_contributions (E5 decomposition; must reconstruct
    the engine's net returns exactly)
  * bootstrap_sharpe_distribution (E1 seed-dependent CI)
  * build_positions (frozen-config pipeline composition)
  * probe_live_extension (failure handling)
  * PERTURBATIONS list integrity (exactly ±20% of the frozen config)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_h11_robustness_experiment as h11
from qtr.backtest.engine import run_backtest


def _hourly_frame(n: int = 2600, seed: int = 11, symbols=("A", "B", "C")):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-11-01", periods=n, freq="h")
    data = {}
    for s in symbols:
        rets = rng.normal(0.0004, 0.025, n)
        data[s] = 100.0 * np.exp(np.cumsum(rets))
    return pd.DataFrame(data, index=idx)


def _exit_inputs(prices):
    pct = prices.pct_change().fillna(0)
    atr = prices * pct.rolling(14, min_periods=7).std()
    atr = atr.replace(0, np.nan).ffill().fillna(prices * 0.001)
    vol = pct.rolling(20, min_periods=10).std() * np.sqrt(252 * 6.5)
    vol = vol.replace(0, np.nan).ffill()
    return atr, vol


def _vix_flat(prices):
    return pd.Series(15.0, index=prices.index)


class TestCostStress:
    def test_scales_commission_spread_slippage(self):
        cfg = h11.make_cost_stressed_config(1.5)
        for sym, spec in cfg.cost_model.futures_specs.items():
            base = h11.FUTURES_SPECS[sym]
            assert spec["commission"] == pytest.approx(base["commission"] * 1.5)
            assert spec["spread_ticks"] == pytest.approx(base["spread_ticks"] * 1.5)
            assert spec["slippage_ticks"] == pytest.approx(base["slippage_ticks"] * 1.5)
            assert spec["multiplier"] == base["multiplier"]
            assert spec["tick_value"] == base["tick_value"]

    def test_cost_multiplier_1_is_base_config(self):
        stressed = h11.make_cost_stressed_config(1.0)
        base = h11.make_futures_config()
        for sym in h11.FUTURES_UNIVERSE:
            assert stressed.cost_model.future_cost_per_contract(sym) == pytest.approx(
                base.cost_model.future_cost_per_contract(sym)
            )

    def test_pf_monotone_nonincreasing_in_cost(self):
        """Higher cost multipliers cannot increase profit factor."""
        prices = _hourly_frame(n=1200)
        atr, vol_exit = _exit_inputs(prices)
        volumes = pd.DataFrame(1e6, index=prices.index, columns=prices.columns)
        vix = _vix_flat(prices)
        pos = h11.build_positions(prices, atr, vol_exit, vix, **h11.FROZEN_CONFIG)
        pfs = []
        for mult in (0.5, 1.0, 1.5, 2.0):
            cfg = h11.make_cost_stressed_config(mult)
            res = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
            pfs.append(res.metrics["profit_factor"])
        assert pfs == sorted(pfs, reverse=True)


class TestPerSymbolContributions:
    def test_sums_to_engine_net_returns(self):
        prices = _hourly_frame(n=1500)
        atr, vol_exit = _exit_inputs(prices)
        volumes = pd.DataFrame(1e6, index=prices.index, columns=prices.columns)
        vix = _vix_flat(prices)
        pos = h11.build_positions(prices, atr, vol_exit, vix, **h11.FROZEN_CONFIG)
        cfg = h11.make_futures_config()
        res = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
        contrib = h11.per_symbol_contributions(res, prices, cfg)
        assert contrib.shape == prices.shape
        recon = contrib.sum(axis=1)
        assert np.max(np.abs(recon.values - res.returns.values)) < 1e-12

    def test_flat_positions_give_zero_contribution(self):
        prices = _hourly_frame(n=800)
        atr, vol_exit = _exit_inputs(prices)
        volumes = pd.DataFrame(1e6, index=prices.index, columns=prices.columns)
        vix = _vix_flat(prices)
        pos = h11.build_positions(prices, atr, vol_exit, vix, **h11.FROZEN_CONFIG)
        cfg = h11.make_futures_config()
        res = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
        contrib = h11.per_symbol_contributions(res, prices, cfg)
        # Bars flat both before and after: no gross P&L and no trade cost.
        prev = res.positions.shift(1).fillna(0)
        flat_both = (prev == 0) & (res.positions == 0)
        masked = contrib.values[flat_both.values]
        assert np.allclose(masked, 0.0, atol=1e-15)


class TestBootstrap:
    def test_deterministic_per_seed(self):
        rets = pd.Series(np.random.default_rng(0).normal(0.0002, 0.01, 3000))
        a = h11.bootstrap_sharpe_distribution(rets, seed=42, n_bootstrap=200)
        b = h11.bootstrap_sharpe_distribution(rets, seed=42, n_bootstrap=200)
        c = h11.bootstrap_sharpe_distribution(rets, seed=7, n_bootstrap=200)
        assert np.array_equal(a, b)
        assert not np.array_equal(a, c)

    def test_point_estimate_within_ci(self):
        rets = pd.Series(np.random.default_rng(1).normal(0.0002, 0.01, 3000))
        sharpes = h11.bootstrap_sharpe_distribution(rets, seed=42, n_bootstrap=1000)
        point = h11.sharpe_ratio(rets.values)
        assert np.percentile(sharpes, 2.5) <= point <= np.percentile(sharpes, 97.5)


class TestBuildPositions:
    def test_frozen_config_produces_active_positions(self):
        prices = _hourly_frame(n=2000)
        atr, vol_exit = _exit_inputs(prices)
        vix = _vix_flat(prices)
        pos = h11.build_positions(prices, atr, vol_exit, vix, **h11.FROZEN_CONFIG)
        assert pos.shape == prices.shape
        assert (pos > 0).any().any()
        assert (pos == 0).any().any()
        assert pos.max().max() <= h11.MAX_POSITION_SIZE + 1e-12
        assert (pos >= 0).all().all()  # allow_short=False

    def test_deterministic(self):
        prices = _hourly_frame(n=1200)
        atr, vol_exit = _exit_inputs(prices)
        vix = _vix_flat(prices)
        p1 = h11.build_positions(prices, atr, vol_exit, vix, **h11.FROZEN_CONFIG)
        p2 = h11.build_positions(prices, atr, vol_exit, vix, **h11.FROZEN_CONFIG)
        assert np.array_equal(p1.values, p2.values)


class TestProbeLiveExtension:
    def test_handles_fetch_failure(self):
        class _BrokenFetcher:
            def fetch_futures(self, *a, **k):
                raise RuntimeError("network down")

        probe = h11.probe_live_extension(_BrokenFetcher())
        assert probe["fresh_bars_beyond_cached"] is False
        assert "error" in probe

    def test_detects_fresh_bars(self):
        class _FakeFetcher:
            def fetch_futures(self, symbols, *a, **k):
                idx = pd.date_range("2026-10-01", periods=250, freq="h")
                return {
                    s: pd.DataFrame({"close": 100.0 + np.arange(250)}, index=idx)
                    for s in symbols
                }

        probe = h11.probe_live_extension(_FakeFetcher())
        assert probe["fresh_bars_beyond_cached"] is True


class TestPerturbationList:
    def test_all_perturbations_are_exactly_20pct(self):
        for param, value in h11.PERTURBATIONS:
            frozen = h11.FROZEN_CONFIG[param]
            ratio = value / frozen
            assert abs(ratio - 0.8) < 0.005 or abs(ratio - 1.2) < 0.005, (
                f"{param}={value} is not ±20% of {frozen}"
            )

    def test_joint_perturbations_cover_all_numeric_params(self):
        numeric = {
            "vol_window_long",
            "trailing_mult",
            "max_hold_bars",
            "vol_limit_mult",
            "vol_floor_fraction",
            "target_vol",
        }
        for _, overrides in h11.JOINT_PERTURBATIONS:
            assert set(overrides) == numeric
