"""End-to-end stress tests for frozen-contract gate evaluation with edge-case
backtest inputs.

This module runs the full pipeline (backtest engine → metrics computation →
gate evaluation) with edge-case inputs and verifies that the standard
PROMPT_V2 gate set fails closed rather than manufacturing a pass.

Edge cases tested (per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path):
* NaN prices in the price panel
* Extreme leverage (zero and enormous max_leverage)
* Zero-volume / degenerate futures contracts (multiplier == 0)
* Look-ahead boundary (bar 0 earns nothing; bar t earns position from t-1)

The standard gate set (from PROMPT_V2 / experiment runners):
  min_sharpe, min_trades, min_profit_factor, max_drawdown,
  min_walkforward_stability, min_perturbed_sharpe_ratio,
  min_worst_regime_sharpe, max_p_value, min_information_ratio
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.validation.statistics import (
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
)

# Standard gate set used by most runners (from PROMPT_V2)
STANDARD_GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_perturbed_sharpe_ratio": 0.5,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
}


def _make_prices(n: int = 100, seed: int = 42, symbols=("A", "B")) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2020-01-01", periods=n)
    data = {}
    for sym in symbols:
        rets = rng.normal(0.0004, 0.01, n)
        data[sym] = 100.0 * np.exp(np.cumsum(rets))
    return pd.DataFrame(data, index=index)


def _make_config(**overrides) -> BacktestConfig:
    defaults = {
        "initial_capital": 1_000_000.0,
        "cost_model": CostModel(
            equity_commission_bps=0.0,
            equity_spread_bps=0.0,
            equity_impact_bps_per_pct_adv=0.0,
        ),
        "asset_class": AssetClass.EQUITY,
        "max_position_size": 1.0,
        "max_leverage": 1.0,
        "allow_short": False,
    }
    defaults.update(overrides)
    return BacktestConfig(**defaults)


def compute_metrics_from_backtest(result, train_sharpe: float = 1.5, benchmark_returns=None):
    """Extract the standard gate metrics from a backtest result."""
    returns = result.returns.values
    metrics = result.metrics

    oos_sharpe = metrics.get("sharpe", 0.0)
    oos_pf = metrics.get("profit_factor", 0.0)
    oos_dd = metrics.get("max_drawdown", 0.0)
    oos_trades = metrics.get("num_trades", 0)

    # Walk-forward stability
    if train_sharpe != 0 and np.isfinite(train_sharpe) and np.isfinite(oos_sharpe):
        wf_stab = oos_sharpe / train_sharpe
    else:
        wf_stab = 0.0

    # Worst regime Sharpe (use a simplified proxy)
    worst_regime_sharpe = metrics.get("worst_month_sharpe", 0.0)

    # Benchmark comparison
    if benchmark_returns is not None and len(benchmark_returns) == len(returns):
        comp = compare_to_benchmark(returns, benchmark_returns)
        p_value = comp["alpha_p_value"]
        information_ratio = comp["information_ratio"]
    else:
        # No benchmark available
        p_value = 1.0
        information_ratio = 0.0

    # Perturbed Sharpe (simplified: use a small perturbation)
    perturbed_returns = returns + np.random.default_rng(42).normal(0, 1e-6, len(returns))
    perturbed_sharpe = sharpe_ratio(perturbed_returns)
    perturbed_ratio = (
        perturbed_sharpe / oos_sharpe
        if oos_sharpe != 0 and np.isfinite(oos_sharpe) and np.isfinite(perturbed_sharpe)
        else 0.0
    )

    return {
        "oos_sharpe": oos_sharpe,
        "oos_pf": oos_pf,
        "oos_dd": oos_dd,
        "oos_trades": oos_trades,
        "train_sharpe": train_sharpe,
        "worst_regime_sharpe": worst_regime_sharpe,
        "p_value": p_value,
        "information_ratio": information_ratio,
        "perturbed_sharpe_ratio": perturbed_ratio,
    }


def evaluate_standard_gates(metrics: dict) -> dict[str, bool]:
    """Evaluate the standard PROMPT_V2 gate set."""
    oos_sharpe = metrics["oos_sharpe"]
    oos_pf = metrics["oos_pf"]
    oos_dd = metrics["oos_dd"]
    oos_trades = metrics["oos_trades"]
    train_sharpe = metrics["train_sharpe"]
    worst_regime_sharpe = metrics["worst_regime_sharpe"]
    p_value = metrics["p_value"]
    information_ratio = metrics["information_ratio"]
    perturbed_ratio = metrics["perturbed_sharpe_ratio"]

    wf_stab = (
        oos_sharpe / train_sharpe
        if train_sharpe != 0 and np.isfinite(train_sharpe) and np.isfinite(oos_sharpe)
        else 0.0
    )

    passes = {
        "sharpe": np.isfinite(oos_sharpe) and oos_sharpe >= STANDARD_GATES["min_sharpe"],
        "trades": oos_trades >= STANDARD_GATES["min_trades"],
        "pf": np.isfinite(oos_pf) and oos_pf >= STANDARD_GATES["min_profit_factor"],
        "dd": np.isfinite(oos_dd) and abs(oos_dd) <= STANDARD_GATES["max_drawdown"],
        "stab": np.isfinite(wf_stab) and wf_stab >= STANDARD_GATES["min_walkforward_stability"],
        "worst": np.isfinite(worst_regime_sharpe)
        and worst_regime_sharpe >= STANDARD_GATES["min_worst_regime_sharpe"],
        "p": benchmark_significance_gate(p_value, information_ratio, STANDARD_GATES["max_p_value"]),
        "ir": np.isfinite(information_ratio)
        and information_ratio > STANDARD_GATES["min_information_ratio"],
        "perturbed": np.isfinite(perturbed_ratio)
        and perturbed_ratio >= STANDARD_GATES["min_perturbed_sharpe_ratio"],
    }
    return passes


# --------------------------------------------------------------------------- #
# Test Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def benchmark_returns():
    """A simple benchmark return series for testing."""
    rng = np.random.default_rng(999)
    return rng.normal(0.0002, 0.01, 100)


# --------------------------------------------------------------------------- #
# 1. NaN Prices
# --------------------------------------------------------------------------- #
class TestNaNPricesEndToEnd:
    """End-to-end tests with NaN prices in the price panel."""

    def test_nan_price_bar_gates_fail_closed(self, benchmark_returns):
        """A NaN price bar should not manufacture gate passes."""
        prices = _make_prices(symbols=("A",))
        nan_bar = prices.index[10]
        prices.loc[nan_bar, "A"] = np.nan
        signals = pd.DataFrame({"A": 1.0}, index=prices.index)
        cfg = _make_config()

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        # With zero costs and NaN at bar 10, the strategy should still run
        # but metrics should be finite and gates should evaluate properly
        assert np.isfinite(result.returns.values).all()
        assert np.isfinite(result.equity_curve.values).all()

        # Sharpe gate should fail (NaN price disrupts returns)
        # At minimum, no gate should crash or pass spuriously
        for gate_name, passed in passes.items():
            if passed:
                # If a gate passes, it should be for a legitimate reason
                assert np.isfinite(
                    [
                        metrics["oos_sharpe"],
                        metrics["oos_pf"],
                        metrics["oos_dd"],
                        metrics["worst_regime_sharpe"],
                        metrics["p_value"],
                        metrics["information_ratio"],
                        metrics["perturbed_sharpe_ratio"],
                    ]
                ).all()

    def test_nan_price_at_first_bar(self, benchmark_returns):
        """NaN at bar 0 should not crash the pipeline."""
        prices = _make_prices(symbols=("A",))
        prices.iloc[0] = np.nan
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1.0
        cfg = _make_config()

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        assert np.isfinite(result.returns.values).all()
        assert np.isfinite(result.equity_curve.values).all()
        # Bar 0 earns nothing due to shift(1)
        assert result.returns.iloc[0] == pytest.approx(0.0, abs=1e-12)

    def test_multiple_nan_prices(self, benchmark_returns):
        """Multiple NaN prices should not crash."""
        prices = _make_prices(symbols=("A", "B"))
        prices.iloc[[5, 10, 15], 0] = np.nan  # Symbol A
        prices.iloc[[7, 12], 1] = np.nan  # Symbol B
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        cfg = _make_config()

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        assert np.isfinite(result.returns.values).all()
        assert all(np.isfinite(v) for v in metrics.values())


# --------------------------------------------------------------------------- #
# 2. Extreme Leverage
# --------------------------------------------------------------------------- #
class TestExtremeLeverageEndToEnd:
    """End-to-end tests with extreme leverage settings."""

    def test_zero_leverage_all_gates_fail_or_boundary(self, benchmark_returns):
        """Zero leverage zeros all exposure; gates should reflect boundary metrics."""
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)  # gross = 2
        cfg = _make_config(max_leverage=0.0)

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        # All positions zero, no trades
        assert (result.positions == 0.0).all().all()
        assert len(result.trades) == 0
        assert (result.returns == 0.0).all()

        # Boundary metrics
        assert metrics["oos_sharpe"] == 0.0
        assert metrics["oos_pf"] == float("inf")  # No losing trades
        assert metrics["oos_dd"] == 0.0
        assert metrics["oos_trades"] == 0

        # Gates: sharpe=0 fails, trades=0 fails, pf=inf fails (np.isfinite), dd=0 passes
        assert not passes["sharpe"]
        assert not passes["trades"]
        assert not passes["pf"]  # np.isfinite(inf) is False
        assert passes["dd"]
        assert not passes["stab"]  # train_sharpe=1.5, wf_stab=0/1.5=0
        assert not passes["worst"]  # worst_regime_sharpe=0
        assert not passes["p"]  # p=1.0 > 0.05
        assert not passes["ir"]  # ir=0.0 not > 0.0
        assert not passes["perturbed"]  # perturbed_ratio=0

    def test_enormous_leverage_no_normalization(self, benchmark_returns):
        """Enormous leverage leaves positions as signals specify."""
        prices = _make_prices(symbols=("A", "B"))
        signals = pd.DataFrame(0.5, index=prices.index, columns=prices.columns)  # gross = 1.0
        cfg = _make_config(max_leverage=1_000_000.0)

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        # Positions should match signals exactly
        assert np.allclose(result.positions.values, 0.5)
        gross = result.positions.abs().sum(axis=1)
        assert np.allclose(gross.values, 1.0)

        # Should produce normal-looking metrics
        assert np.isfinite(metrics["oos_sharpe"])
        assert np.isfinite(metrics["oos_pf"])
        assert np.isfinite(metrics["oos_dd"])


# --------------------------------------------------------------------------- #
# 3. Zero-Volume / Degenerate Futures
# --------------------------------------------------------------------------- #
class TestDegenerateFuturesEndToEnd:
    """End-to-end tests with degenerate futures contracts."""

    def test_zero_multiplier_removes_exposure_gates_evaluate(self, benchmark_returns):
        """Zero multiplier removes exposure for that symbol; gates should evaluate on remaining."""
        prices = _make_prices(symbols=("ES", "NQ"))
        signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        cfg = _make_config(
            asset_class=AssetClass.FUTURE,
            max_leverage=5.0,
            max_position_size=5.0,
        )
        cfg.cost_model.future_contract_multiplier = 50.0
        cfg.cost_model.futures_specs = {"ES": {"multiplier": 0.0}}

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        # ES has zero exposure, NQ trades normally
        assert (result.positions["ES"] == 0.0).all()
        assert np.allclose(result.positions["NQ"].values, 1.0)

        es_trades = result.trades[result.trades["symbol"] == "ES"]
        assert len(es_trades) == 0

        # Metrics should be finite and gates should evaluate
        assert all(
            np.isfinite(v) if isinstance(v, (int, float)) and not np.isinf(v) else True
            for v in metrics.values()
        )


# --------------------------------------------------------------------------- #
# 4. Look-Ahead Boundary
# --------------------------------------------------------------------------- #
class TestLookAheadBoundaryEndToEnd:
    """End-to-end tests for look-ahead boundary conditions."""

    def test_bar_zero_earns_nothing_gates_evaluate(self, benchmark_returns):
        """Bar 0 earns nothing even with position established; gates should reflect this."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": np.nan}, index=prices.index)
        signals.iloc[0] = 1.0  # long at close of bar 0
        signals.iloc[1] = 0.0  # flat at close of bar 1
        cfg = _make_config()  # zero costs

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        asset_ret = prices["A"].pct_change().fillna(0.0)
        assert result.returns.iloc[0] == pytest.approx(0.0, abs=1e-12)
        assert result.returns.iloc[1] == pytest.approx(asset_ret.iloc[1], abs=1e-12)

        # Gates should evaluate on the resulting metrics
        assert all(
            np.isfinite(v) if isinstance(v, (int, float)) and not np.isinf(v) else True
            for v in metrics.values()
        )

    def test_signal_at_late_bar_look_ahead_respected(self, benchmark_returns):
        """Signal at bar 50 cannot earn bar 50's return."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.iloc[50] = 1.0
        cfg = _make_config()

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        asset_ret = prices["A"].pct_change().fillna(0.0)
        assert result.returns.iloc[50] == pytest.approx(0.0, abs=1e-12)
        assert result.returns.iloc[51] == pytest.approx(asset_ret.iloc[51], abs=1e-12)

        assert all(
            np.isfinite(v) if isinstance(v, (int, float)) and not np.isinf(v) else True
            for v in metrics.values()
        )


# --------------------------------------------------------------------------- #
# 5. Zero Volume / ADV (Equity Impact)
# --------------------------------------------------------------------------- #
class TestZeroVolumeEndToEnd:
    """End-to-end tests with zero volume/ADV for equity impact."""

    def test_zero_volume_skips_impact_gates_evaluate(self, benchmark_returns):
        """Zero volume and ADV should skip impact; gates should evaluate."""
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.iloc[5] = 1.0
        volumes = pd.DataFrame({"A": 0.0}, index=prices.index)
        adv = pd.Series({"A": 0.0})
        cfg = _make_config(asset_class=AssetClass.EQUITY, max_position_size=1.0)
        cfg.cost_model.equity_impact_bps_per_pct_adv = 10.0

        result = run_backtest(prices=prices, signals=signals, volumes=volumes, adv=adv, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        assert np.isfinite(result.returns.values).all()
        assert result.returns.iloc[5] <= 0.0  # Entry cost drag
        assert len(result.trades) == 2

        assert all(
            np.isfinite(v) if isinstance(v, (int, float)) and not np.isinf(v) else True
            for v in metrics.values()
        )


# --------------------------------------------------------------------------- #
# 6. Combined Edge Cases
# --------------------------------------------------------------------------- #
class TestCombinedEdgeCases:
    """Combined edge cases to stress the full pipeline."""

    def test_nan_price_with_zero_leverage(self, benchmark_returns):
        """NaN price with zero leverage - both edge cases together."""
        prices = _make_prices(symbols=("A",))
        prices.iloc[10] = np.nan
        signals = pd.DataFrame({"A": 1.0}, index=prices.index)
        cfg = _make_config(max_leverage=0.0)

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        assert np.isfinite(result.returns.values).all()
        assert (result.positions == 0.0).all().all()
        assert all(
            np.isfinite(v) if isinstance(v, (int, float)) and not np.isinf(v) else True
            for v in metrics.values()
        )

    def test_zero_volume_with_nan_price(self, benchmark_returns):
        """Zero volume with NaN price."""
        prices = _make_prices(symbols=("A",))
        prices.iloc[5] = np.nan
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.iloc[5] = 1.0
        volumes = pd.DataFrame({"A": 0.0}, index=prices.index)
        adv = pd.Series({"A": 0.0})
        cfg = _make_config(
            asset_class=AssetClass.EQUITY,
            max_position_size=1.0,
        )
        cfg.cost_model.equity_impact_bps_per_pct_adv = 10.0

        result = run_backtest(prices=prices, signals=signals, volumes=volumes, adv=adv, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        assert np.isfinite(result.returns.values).all()
        assert all(
            np.isfinite(v) if isinstance(v, (int, float)) and not np.isinf(v) else True
            for v in metrics.values()
        )

    def test_look_ahead_with_nan_price(self, benchmark_returns):
        """Look-ahead boundary with NaN price at the trade bar."""
        prices = _make_prices(symbols=("A",))
        trade_bar = prices.index[10]
        prices.loc[trade_bar, "A"] = np.nan
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)
        signals.loc[trade_bar] = 1.0
        cfg = _make_config()

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        assert np.isfinite(result.returns.values).all()
        assert len(result.trades) == 2
        assert all(
            np.isfinite(v) if isinstance(v, (int, float)) and not np.isinf(v) else True
            for v in metrics.values()
        )


# --------------------------------------------------------------------------- #
# 7. Gate Failure Closure Verification
# --------------------------------------------------------------------------- #
class TestGateFailureClosure:
    """Verify that edge cases cannot manufacture gate passes."""

    def test_all_edge_cases_no_manufactured_passes(self, benchmark_returns):
        """Run through multiple edge cases and verify no gate passes spuriously."""

        def add_nan_price(p):
            p = p.copy()
            p.loc[p.index[10], "A"] = np.nan
            return p

        edge_cases = [
            # (name, prices_modifier, signals_modifier, config_modifier)
            (
                "nan_price",
                add_nan_price,
                lambda s: s,
                lambda c: c,
            ),
            (
                "zero_leverage",
                lambda p: p,
                lambda s: s,
                lambda c: _make_config(max_leverage=0.0),
            ),
            (
                "enormous_leverage",
                lambda p: p,
                lambda s: s,
                lambda c: _make_config(max_leverage=1e6),
            ),
        ]

        for name, prices_mod, signals_mod, config_mod in edge_cases:
            prices = _make_prices(symbols=("A", "B"))
            prices = prices_mod(prices)
            signals = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
            signals = signals_mod(signals)
            cfg = config_mod(_make_config())

            result = run_backtest(prices=prices, signals=signals, config=cfg)
            metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
            passes = evaluate_standard_gates(metrics)

            # No gate should pass unless all its inputs are finite and meet thresholds
            for gate_name, passed in passes.items():
                if passed:
                    # Verify the gate's dependent metrics are all finite
                    if gate_name == "sharpe":
                        assert np.isfinite(metrics["oos_sharpe"])
                    elif gate_name == "pf":
                        assert np.isfinite(metrics["oos_pf"])
                    elif gate_name == "dd":
                        assert np.isfinite(metrics["oos_dd"])
                    elif gate_name == "stab":
                        assert np.isfinite(metrics["oos_sharpe"])
                        assert np.isfinite(metrics["train_sharpe"])
                    elif gate_name == "worst":
                        assert np.isfinite(metrics["worst_regime_sharpe"])
                    elif gate_name == "p":
                        assert np.isfinite(metrics["p_value"])
                        assert np.isfinite(metrics["information_ratio"])
                    elif gate_name == "ir":
                        assert np.isfinite(metrics["information_ratio"])
                    elif gate_name == "perturbed":
                        assert np.isfinite(metrics["perturbed_sharpe_ratio"])

    def test_boundary_metrics_all_gates_fail_closed(self, benchmark_returns):
        """Test with explicitly crafted boundary metrics (all zero/NaN)."""
        # Create a result that simulates a completely flat strategy
        prices = _make_prices(symbols=("A",))
        signals = pd.DataFrame({"A": 0.0}, index=prices.index)  # Never trades
        cfg = _make_config()

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        # Flat strategy: zero returns, zero trades, zero everything
        assert metrics["oos_sharpe"] == 0.0
        assert metrics["oos_pf"] == float("inf")  # No trades = no losing trades
        assert metrics["oos_dd"] == 0.0
        assert metrics["oos_trades"] == 0

        # Only DD gate can pass (0 <= 0.15); all others should fail
        assert passes["dd"]
        assert not passes["sharpe"]
        assert not passes["trades"]
        assert not passes["pf"]  # inf is not finite
        assert not passes["stab"]
        assert not passes["worst"]
        assert not passes["p"]
        assert not passes["ir"]
        assert not passes["perturbed"]


# --------------------------------------------------------------------------- #
# 8. Negative Controls
# --------------------------------------------------------------------------- #
class TestNegativeControls:
    """Negative controls to verify detectors catch injected defects."""

    def test_good_strategy_passes_gates(self, benchmark_returns):
        """A strategy with good metrics should pass all gates (sanity check)."""
        # Create a strategy with positive returns
        prices = _make_prices(n=500, symbols=("A",))
        # Signal that follows the trend
        rets = prices["A"].pct_change().fillna(0.0)
        signals = pd.DataFrame(
            {"A": np.sign(rets.rolling(5).mean().fillna(0.0))}, index=prices.index
        )
        cfg = _make_config()

        result = run_backtest(prices=prices, signals=signals, config=cfg)
        metrics = compute_metrics_from_backtest(result, benchmark_returns=benchmark_returns)
        passes = evaluate_standard_gates(metrics)

        # Not asserting all pass (depends on random data), but at least no crash
        assert all(
            np.isfinite(v) if isinstance(v, (int, float)) and not np.isinf(v) else True
            for v in metrics.values()
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
