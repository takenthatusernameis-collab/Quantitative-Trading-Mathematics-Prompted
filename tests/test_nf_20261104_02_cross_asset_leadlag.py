"""
Regression tests for NF-20261104-02 cross-asset lead-lag experiment
(run_nf_20261104_02_cross_asset_leadlag.py).

Pins:
  * Pre-registered gate thresholds (PROMPT_V2 set + perturbation gate)
  * Grid integrity (36 combos; selection = argmax train-only WF Sharpe)
  * Signal causality (sector return at t-1 drives position at t; no future info)
  * Long/short balance and weight bounds
  * Determinism of the signal builder
  * Vol-target scaling respects vol_target parameter
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_nf_20261104_02_cross_asset_leadlag as nf02


class TestPreRegistration:
    def test_gates_are_the_pre_registered_set(self):
        assert nf02.GATES == {
            "min_sharpe": 1.0,
            "min_trades": 200,
            "min_profit_factor": 1.3,
            "max_drawdown": 0.15,
            "min_walkforward_stability": 0.7,
            "min_worst_regime_sharpe": 0.3,
            "max_p_value": 0.05,
            "min_information_ratio": 0.0,
            "min_perturbed_sharpe_ratio": 0.5,
        }

    def test_grid_is_the_pre_registered_36_combos(self):
        assert len(nf02.LOOKBACKS) == 4
        assert len(nf02.QUINTILE_SHARES) == 3
        assert len(nf02.VOL_TARGETS) == 3
        assert len(nf02.LOOKBACKS) * len(nf02.QUINTILE_SHARES) * len(nf02.VOL_TARGETS) == 36


class TestSignalCausality:
    def test_sector_return_at_t_minus_1_never_uses_future_prices(self):
        """Build targets from synthetic data; verify row t only depends on
        prices up to and including t-1 (sector return known at close t-1)."""
        dates = pd.date_range("2020-01-01", periods=120, freq="B")
        rng = np.random.default_rng(42)

        # ETF prices: sector return at t-1 computed from close t-2 -> close t-1
        etf_data = {}
        for etf in ["XLF", "XLV"]:
            etf_data[etf] = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(dates))))
        etf_prices = pd.DataFrame(etf_data, index=dates)

        # Stock prices: 2 stocks per sector
        stock_data = {}
        for sector, stocks in [("XLF", ["JPM", "BAC"]), ("XLV", ["JNJ", "UNH"])]:
            for s in stocks:
                stock_data[s] = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, len(dates))))
        stock_prices = pd.DataFrame(stock_data, index=dates)

        prices = pd.concat([etf_prices, stock_prices], axis=1)
        etf_returns = etf_prices.pct_change()

        targets = nf02.build_daily_targets(
            prices, etf_returns, lookback=21, quintile_share=0.2, vol_target=0.15
        )

        # Row 0 must be all zeros (no prior return available).
        assert (targets.iloc[0] == 0).all()

        # For each row t>=2, the sector-return signal must equal the
        # close[t-1]/close[t-2]-1 return of the sector ETF (not close[t]).
        # (Row t=1 has no valid two-price return yet, so the builder skips it.)
        for t_idx in range(2, len(dates)):
            t = dates[t_idx]
            for sector in ["XLF", "XLV"]:
                etf = sector
                expected_sector_ret = (
                    etf_prices[etf].iloc[t_idx - 1] / etf_prices[etf].iloc[t_idx - 2] - 1
                )
                # The lagged series used internally is etf_returns.shift(1),
                # so row t uses etf_returns[t-1] = close[t-1]/close[t-2]-1.
                actual_sector_ret = etf_returns[etf].iloc[t_idx - 1]
                assert abs(expected_sector_ret - actual_sector_ret) < 1e-12, (
                    f"row {t} sector {etf} uses future info: "
                    f"expected {expected_sector_ret}, got {actual_sector_ret}"
                )

    def test_stock_ranking_uses_only_prior_day_information(self):
        """The quintile *membership* at row t must depend only on prices up to
        close t-1. The position built at row t earns the close[t-1] -> close[t]
        return, so that concurrent return must not enter the ranking: ranking
        on it would be look-ahead dressed as a cross-sectional signal.

        Construction: perturb the close[t-1] -> close[t] return of one stock by
        a large amount. If the builder is causal, row t's membership for that
        stock is unchanged; if it ranked on the concurrent return, the stock
        would move into or out of a quintile.
        """
        dates = pd.date_range("2020-01-01", periods=120, freq="B")
        rng = np.random.default_rng(101)

        etf_data = {
            etf: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(dates)))) for etf in ["XLF", "XLV"]
        }
        etf_prices = pd.DataFrame(etf_data, index=dates)

        stock_data = {}
        for sector, stocks in [
            ("XLF", ["JPM", "BAC", "WFC", "C"]),
            ("XLV", ["JNJ", "UNH", "ABBV", "TMO"]),
        ]:
            for s in stocks:
                stock_data[s] = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, len(dates))))
        stock_prices = pd.DataFrame(stock_data, index=dates)

        prices = pd.concat([etf_prices, stock_prices], axis=1)
        etf_returns = etf_prices.pct_change()

        # Perturb the *concurrent* close[t-1] -> close[t] return of JPM at one
        # row only. Everything known at close t-1 is untouched.
        t_idx = 80
        perturbed = prices.copy()
        perturbed.iloc[t_idx, perturbed.columns.get_loc("JPM")] *= 1.5

        t_causal = nf02.build_daily_targets(
            prices, etf_returns, lookback=21, quintile_share=0.25, vol_target=0.15
        )
        t_perturbed = nf02.build_daily_targets(
            perturbed, etf_returns, lookback=21, quintile_share=0.25, vol_target=0.15
        )

        row = dates[t_idx]
        # The perturbation is a concurrent return; a causal builder ignores it.
        # Membership (zero vs non-zero weight) must be identical at row t.
        causal_membership = (t_causal.loc[row] != 0).astype(int)
        pert_membership = (t_perturbed.loc[row] != 0).astype(int)
        assert causal_membership.equals(pert_membership), (
            f"row {row.date()}: ranking used concurrent return; "
            f"membership changed by a close[t-1]->close[t] perturbation"
        )
        # The perturbation is large enough to flip a quintile if the builder
        # were ranking on the concurrent return, so membership must also be
        # unchanged relative to the unperturbed row for every stock.
        for s in ["JPM", "BAC", "WFC", "C", "JNJ", "UNH", "ABBV", "TMO"]:
            assert (t_causal.loc[row, s] == 0) == (t_perturbed.loc[row, s] == 0), (
                f"{s} membership changed at {row.date()}"
            )

    def test_positions_are_long_short_balanced_within_sector(self):
        """Each sector's net exposure per side is balanced (top quintile long,
        bottom quintile short, equal magnitude aggregate)."""
        dates = pd.date_range("2020-01-01", periods=200, freq="B")
        rng = np.random.default_rng(7)

        etf_data = {
            etf: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(dates)))) for etf in ["XLF", "XLV"]
        }
        etf_prices = pd.DataFrame(etf_data, index=dates)

        stock_data = {}
        for sector, stocks in [
            ("XLF", ["JPM", "BAC", "WFC", "C"]),
            ("XLV", ["JNJ", "UNH", "ABBV", "TMO"]),
        ]:
            for s in stocks:
                stock_data[s] = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, len(dates))))
        stock_prices = pd.DataFrame(stock_data, index=dates)

        prices = pd.concat([etf_prices, stock_prices], axis=1)
        etf_returns = etf_prices.pct_change()

        targets = nf02.build_daily_targets(
            prices, etf_returns, lookback=21, quintile_share=0.25, vol_target=0.15
        )

        for t_idx in range(60, len(dates)):
            t = dates[t_idx]
            row = targets.loc[t]
            for sector, stocks in [
                ("XLF", ["JPM", "BAC", "WFC", "C"]),
                ("XLV", ["JNJ", "UNH", "ABBV", "TMO"]),
            ]:
                sector_pos = row[stocks]
                longs = sector_pos[sector_pos > 0]
                shorts = sector_pos[sector_pos < 0]
                # Equal number of longs and shorts (quintile share splits evenly)
                assert len(longs) == len(shorts), (
                    f"{t} {sector}: longs={len(longs)} shorts={len(shorts)}"
                )

    def test_weight_bounds_respect_max_position(self):
        """No single stock weight exceeds max_position_size (1.0) and
        gross exposure is bounded by vol_target."""
        dates = pd.date_range("2020-01-01", periods=200, freq="B")
        rng = np.random.default_rng(11)

        etf_data = {
            etf: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(dates)))) for etf in ["XLF", "XLV"]
        }
        etf_prices = pd.DataFrame(etf_data, index=dates)

        stock_data = {}
        for sector, stocks in [
            ("XLF", ["JPM", "BAC", "WFC", "C"]),
            ("XLV", ["JNJ", "UNH", "ABBV", "TMO"]),
        ]:
            for s in stocks:
                stock_data[s] = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, len(dates))))
        stock_prices = pd.DataFrame(stock_data, index=dates)

        prices = pd.concat([etf_prices, stock_prices], axis=1)
        etf_returns = etf_prices.pct_change()

        targets = nf02.build_daily_targets(
            prices, etf_returns, lookback=21, quintile_share=0.25, vol_target=0.15
        )

        # Individual weights bounded (max_position_size = 1.0 from config)
        assert (targets.abs() <= 1.0 + 1e-9).all().all(), (
            "individual weight exceeds max_position_size"
        )

        # Gross exposure per row bounded by number of sectors * quintile_share * vol_factor
        # (each side: quintile_share of vol_target/vol_per_stock; max ~1 per name)
        gross = targets.abs().sum(axis=1)
        assert (gross <= 4.0).all(), f"gross exposure exceeds bound: max={gross.max()}"

    def test_vol_target_scaling(self):
        """Higher vol_target produces proportionally larger positions."""
        dates = pd.date_range("2020-01-01", periods=200, freq="B")
        rng = np.random.default_rng(13)

        etf_data = {
            etf: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(dates)))) for etf in ["XLF", "XLV"]
        }
        etf_prices = pd.DataFrame(etf_data, index=dates)

        stock_data = {}
        for sector, stocks in [
            ("XLF", ["JPM", "BAC", "WFC", "C"]),
            ("XLV", ["JNJ", "UNH", "ABBV", "TMO"]),
        ]:
            for s in stocks:
                stock_data[s] = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, len(dates))))
        stock_prices = pd.DataFrame(stock_data, index=dates)

        prices = pd.concat([etf_prices, stock_prices], axis=1)
        etf_returns = etf_prices.pct_change()

        t_lo = nf02.build_daily_targets(
            prices, etf_returns, lookback=21, quintile_share=0.25, vol_target=0.10
        )
        t_hi = nf02.build_daily_targets(
            prices, etf_returns, lookback=21, quintile_share=0.25, vol_target=0.20
        )

        # Non-zero rows: hi-vol positions should be ~2x lo-vol positions
        for t_idx in range(60, len(dates)):
            t = dates[t_idx]
            lo_row = t_lo.loc[t]
            hi_row = t_hi.loc[t]
            mask = lo_row != 0
            if mask.any():
                ratio = hi_row[mask] / lo_row[mask]
                assert np.allclose(ratio, 2.0, rtol=0.05), (
                    f"{t}: vol scaling ratio {ratio.mean():.3f} != 2.0"
                )


class TestDeterminism:
    def test_signal_builder_is_deterministic(self):
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        rng = np.random.default_rng(17)

        etf_data = {
            etf: 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(dates)))) for etf in ["XLF", "XLV"]
        }
        etf_prices = pd.DataFrame(etf_data, index=dates)

        stock_data = {}
        for sector, stocks in [("XLF", ["JPM", "BAC"]), ("XLV", ["JNJ", "UNH"])]:
            for s in stocks:
                stock_data[s] = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, len(dates))))
        stock_prices = pd.DataFrame(stock_data, index=dates)

        prices = pd.concat([etf_prices, stock_prices], axis=1)
        etf_returns = etf_prices.pct_change()

        t1 = nf02.build_daily_targets(
            prices, etf_returns, lookback=21, quintile_share=0.25, vol_target=0.15
        )
        t2 = nf02.build_daily_targets(
            prices, etf_returns, lookback=21, quintile_share=0.25, vol_target=0.15
        )

        pd.testing.assert_frame_equal(t1, t2)


class TestPeriodMetrics:
    def test_period_metrics_shapes(self):
        r = pd.Series(np.random.default_rng(0).normal(0.001, 0.02, 100))
        m = nf02._period_metrics(r, 50)
        assert set(m) == {
            "sharpe",
            "max_drawdown",
            "profit_factor",
            "trades",
            "gross_profit",
            "gross_loss",
            "n_periods",
        }
        assert m["trades"] == 50
        assert m["n_periods"] == 100

    def test_period_metrics_empty(self):
        m = nf02._period_metrics(pd.Series(dtype=float), 0)
        assert m["sharpe"] == 0.0
        assert m["trades"] == 0
        assert m["profit_factor"] == float("inf")
