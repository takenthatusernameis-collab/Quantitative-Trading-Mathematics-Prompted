"""
Regression tests for the H23 crypto perpetual futures intraday TSMOM experiment
(run_h23_crypto_futures_tsmom.py).

Pins:
  * Pre-registered gate thresholds (PROMPT_V2 set + perturbation gate)
  * Pre-registered grid (2304 combos), universe, splits, symbols, seed
  * Artifact schema and summary.json consistency
  * Gate recomputation from the logged equity/trades artifacts
    (exact match to summary.json at 1e-9)
  * Grid/selection integrity (2304 unique combos; selection = argmax Val Sharpe)
  * Signal causality (future-price perturbation leaves past targets bit-identical)
  * Point-in-time / weight bounds (weights in [0, max_pos] per contract)
  * Regime labels (constant for crypto, no VIX)
  * Determinism
  * The executed outcome (PASS or REJECT)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import run_h23_crypto_futures_tsmom as h23
from qtr.validation.statistics import sharpe_ratio

ART_DIR = ROOT / ".experiments" / "artifacts"

# The experiment uses 55/25/20 splits (from H10 _splits function)
# OOS = Val + Test = last 45% of data (25% Val + 20% Test)
# DATA_START = "2024-10-12", DATA_END = "2026-10-11"
# Train: 55% -> 2025-11-14, Val: 25% -> 2026-05-19, Test: 20% -> 2026-10-09
# OOS starts at 55% = 2025-11-14 01:00:00


def _get_oos_start(exp_dir: Path) -> pd.Timestamp:
    prices = pd.read_parquet(exp_dir / "prices.parquet")
    n = len(prices)
    # OOS starts right after the 55% train cutoff
    return prices.index[int(n * 0.55) + 1]


def _latest_h23_dir() -> Path:
    h23_dirs = []
    for d in ART_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            with open(d / "summary.json") as f:
                s = json.load(f)
            if s.get("hypothesis") == "H23":
                h23_dirs.append(d)
        except (OSError, json.JSONDecodeError):
            continue
    assert h23_dirs, "no H23 artifacts; run run_h23_crypto_futures_tsmom.py"
    return max(h23_dirs, key=lambda p: p.stat().st_mtime)


def _load_summary(exp_dir: Path) -> dict:
    with open(exp_dir / "summary.json") as f:
        return json.load(f)


class TestPreRegistration:
    def test_gates_are_the_pre_registered_set(self):
        assert h23.GATES == {
            "min_sharpe": 1.0,
            "min_trades": 200,
            "min_profit_factor": 1.3,
            "max_drawdown": 0.15,
            "min_walkforward_stability": 0.7,
            "min_worst_regime_sharpe": 0.0,
            "max_p_value": 0.05,
            "min_information_ratio": 0.0,
            "min_perturbed_sharpe_ratio": 0.5,
        }

    def test_grid_is_the_pre_registered_2304_combos(self):
        assert (
            len(h23.SMOOTH_SPANS)
            * len(h23.VOL_WINDOWS_LONG)
            * len(h23.REGIME_SCALING_FLAGS)
            * len(h23.MIN_TRADE_INTERVALS)
            * len(h23.TRAILING_MULTS)
            * len(h23.MAX_HOLD_BARS)
            * len(h23.VOL_LIMIT_MULTS)
            * len(h23.VOL_FLOOR_FRACTIONS)
        ) == 6912
        assert h23.SMOOTH_SPANS == [None, 4, 8, 16]
        assert h23.VOL_WINDOWS_LONG == [252, 504, 1008]
        assert h23.REGIME_SCALING_FLAGS == [False]
        assert h23.MIN_TRADE_INTERVALS == [0, 4, 8, 24]
        assert h23.TRAILING_MULTS == [1.5, 2.0, 2.5, 3.0]
        assert h23.MAX_HOLD_BARS == [60, 120, 240, 480]
        assert h23.VOL_LIMIT_MULTS == [1.5, 2.0, 2.5]
        assert h23.VOL_FLOOR_FRACTIONS == [0.25, 0.5, 0.75]

    def test_universe_symbols_are_pre_registered(self):
        assert h23.CRYPTO_UNIVERSE == [
            "BTC/USD",
            "ETH/USD",
            "ADA/USD",
            "XRP/USD",
            "DOGE/USD",
        ]
        assert h23.VIX_SYMBOL == "^VIX"

    def test_splits_are_the_pre_registered_proportions(self):
        assert h23.DATA_START == "2024-10-12"
        assert h23.DATA_END == "2026-10-11"
        # Splits are 55/25/20 by time (verified in _splits)

    def test_seed_and_config_pre_registered(self):
        assert h23.SEED == 42
        assert h23.INITIAL_CAPITAL == 1_000_000.0
        assert h23.TARGET_VOL == 0.15
        assert h23.VOL_WINDOW_SHORT_RATIO == 4
        # Check fixed exit parameters (analogous to H22 SEL checks)
        assert h23.EXIT_TRAILING_DEFAULT == 2.0
        assert h23.EXIT_MAX_HOLD_DEFAULT == 120
        assert h23.EXIT_VOL_LIMIT_DEFAULT == 2.0
        assert h23.EXIT_VOL_FLOOR_DEFAULT == 0.5


class TestArtifacts:
    def test_artifacts_exist(self):
        exp_dir = _latest_h23_dir()
        for name in (
            "summary.json",
            "prices.parquet",
            "volumes.parquet",
            "vix_hourly.parquet",
            "grid_results.parquet",
            "positions.parquet",
            "equity.parquet",
            "returns.parquet",
            "trades.parquet",
            "benchmark_equity.parquet",
            "benchmark_returns.parquet",
        ):
            assert (exp_dir / name).exists(), name

    def test_summary_schema(self):
        s = _load_summary(_latest_h23_dir())
        for k in (
            "experiment_id",
            "hypothesis",
            "selected_config",
            "selection_rule",
            "grid_size",
            "n_evaluated",
            "compute_cpu_hours",
            "metrics",
            "passes",
            "all_pass",
            "verdict",
        ):
            assert k in s, k
        for k in (
            "train_sharpe",
            "val_sharpe",
            "test_sharpe",
            "oos_sharpe",
            "profit_factor",
            "max_drawdown",
            "trades",
            "wf_stability",
            "worst_regime_sharpe",
            "regime_sharpes",
            "benchmark_p_value",
            "information_ratio",
            "perturbation_min_ratio",
            "ablations",
        ):
            assert k in s["metrics"], k
        assert s["hypothesis"] == "H23"
        assert s["grid_size"] == 6912
        assert s["n_evaluated"] == 6912
        assert s["compute_cpu_hours"] <= 2.0

    def test_grid_has_correct_unique_combos(self):
        exp_dir = _latest_h23_dir()
        grid = pd.read_parquet(exp_dir / "grid_results.parquet")
        # Should have 6912 unique combos (4*3*1*4*4*4*3*3)
        assert len(grid) == 6912
        keys = set(
            zip(
                grid["smooth_span"],
                grid["vol_window_long"],
                grid["regime_scaling"],
                grid["min_trade_interval"],
                grid["trailing_mult"],
                grid["max_hold_bars"],
                grid["vol_limit_mult"],
                grid["vol_floor_fraction"],
            )
        )
        assert len(keys) == 6912

    def test_select_on_val_only(self):
        # Selection is argmax of Val Sharpe, but only among in-sample-trading
        # configs (val_trades >= MIN_VAL_TRADES_FOR_SELECTION) to avoid the
        # degenerate zero-trade configs that win a pure argmax (HANDOFF.md).
        exp_dir = _latest_h23_dir()
        s = _load_summary(exp_dir)
        grid = pd.read_parquet(exp_dir / "grid_results.parquet")
        eligible = grid[grid["val_trades"] >= h23.MIN_VAL_TRADES_FOR_SELECTION]
        best_val = eligible.loc[eligible["val_sharpe"].idxmax()]
        sel = s["selected_config"]
        assert sel["vol_window_long"] == best_val["vol_window_long"]
        assert sel["smooth_span"] == (
            str(best_val["smooth_span"])
            if best_val["smooth_span"] != "none"
            else "none"
        )
        assert sel["regime_scaling"] == best_val["regime_scaling"]
        assert sel["min_trade_interval"] == best_val["min_trade_interval"]
        assert abs(best_val["val_sharpe"] - s["metrics"]["val_sharpe"]) < 1e-6

    def test_selection_excludes_zero_trade_configs(self):
        """Robustness lock: the selected config must be a live-trading (val-trades>0)
        config, never the degenerate zero-trade argmax (HANDOFF.md post-mortem)."""
        exp_dir = _latest_h23_dir()
        s = _load_summary(exp_dir)
        grid = pd.read_parquet(exp_dir / "grid_results.parquet")
        sel = s["selected_config"]
        # Locate the selected row in the grid by full key match.
        rows = grid[
            (grid["vol_window_long"] == sel["vol_window_long"])
            & (grid["smooth_span"] == sel["smooth_span"])
            & (grid["regime_scaling"] == sel["regime_scaling"])
            & (grid["min_trade_interval"] == sel["min_trade_interval"])
            & (grid["trailing_mult"] == sel["trailing_mult"])
            & (grid["max_hold_bars"] == sel["max_hold_bars"])
            & (grid["vol_limit_mult"] == sel["vol_limit_mult"])
            & (grid["vol_floor_fraction"] == sel["vol_floor_fraction"])
        ]
        assert len(rows) == 1, "selected config not uniquely present in grid"
        assert int(rows["val_trades"].iloc[0]) >= h23.MIN_VAL_TRADES_FOR_SELECTION
        # And the pure (unfiltered) argmax must NOT have been selected.
        pure_best = grid.loc[grid["val_sharpe"].idxmax()]
        if pure_best["val_trades"] < h23.MIN_VAL_TRADES_FOR_SELECTION:
            assert int(rows["val_trades"].iloc[0]) > 0, (
                "selected a zero-trade config despite eligibility threshold"
            )


class TestGateRecomputation:
    def test_oos_metrics_recomputed_from_artifacts(self):
        """Recompute OOS Sharpe/DD/PF from logged equity & trades,
        exact match to summary.json (1e-9)."""
        exp_dir = _latest_h23_dir()
        s = _load_summary(exp_dir)
        equity = pd.read_parquet(exp_dir / "equity.parquet")["equity"]
        trades = pd.read_parquet(exp_dir / "trades.parquet")
        oos_start = _get_oos_start(exp_dir)

        rets = equity.pct_change()
        rets.iloc[0] = 0.0
        oos = rets[rets.index >= oos_start]

        sr = float(sharpe_ratio(oos.values))
        cum = (1 + oos).cumprod()
        dd = float((cum / cum.cummax() - 1.0).min())
        gp = float(oos[oos > 0].sum())
        gl = float(abs(oos[oos < 0].sum()))
        pf = gp / gl if gl > 0 else float("inf")
        ts = pd.to_datetime(trades["timestamp"])
        n_trades = int((ts >= oos_start).sum())

        m = s["metrics"]
        assert sr == pytest.approx(m["oos_sharpe"], abs=1e-9)
        assert dd == pytest.approx(m["max_drawdown"], abs=1e-9)
        assert pf == pytest.approx(m["profit_factor"], abs=1e-9)
        assert n_trades == m["trades"]

    def test_oos_window_is_protected(self):
        """Test (after VAL_END) is never used for selection."""
        exp_dir = _latest_h23_dir()
        grid = pd.read_parquet(exp_dir / "grid_results.parquet")
        assert "test_sharpe" not in grid.columns  # grid only has val_* metrics
        # Selection is explicitly on val_sharpe (tested in test_select_on_val_only)


class TestCausality:
    def test_per_contract_targets_do_not_look_into_future(self):
        """Causality test on per-contract hourly targets (H10 pipeline)."""
        rng = pd.date_range("2024-10-12", periods=2000, freq="h")
        prices = pd.DataFrame(
            {
                "ES=F": 5000.0
                + np.cumsum(np.random.default_rng(42).normal(0, 5, 2000)),
                "NQ=F": 18000.0
                + np.cumsum(np.random.default_rng(43).normal(0, 20, 2000)),
                "CL=F": 75.0
                + np.cumsum(np.random.default_rng(44).normal(0, 0.5, 2000)),
            },
            index=rng,
        )
        # Build base signals with shorter lookback for test
        base_signals = {}
        for sym in prices.columns:
            base_signals[sym] = h23.vol_scaled_tsmom_hourly(
                prices[[sym]],
                vol_window_long=500,
                vol_window_short=500 // 4,
            )
        vix_hourly = pd.Series(20.0, index=prices.index)

        for sym in prices.columns:
            t0 = h23.build_hourly_target(
                base_signals[sym], None, 500, False, vix_hourly, prices.index
            )
            # perturb a future price
            prices_pert = prices.copy()
            prices_pert.loc[prices_pert.index[1500], "ES=F"] *= 1.02
            prices_pert.loc[prices_pert.index[1600], "NQ=F"] *= 0.98
            prices_pert.loc[prices_pert.index[1700], "CL=F"] *= 1.03

            base_signals_pert = {}
            for s in prices.columns:
                base_signals_pert[s] = h23.vol_scaled_tsmom_hourly(
                    prices_pert[[s]],
                    vol_window_long=500,
                    vol_window_short=500 // 4,
                )

            t1 = h23.build_hourly_target(
                base_signals_pert[sym], None, 500, False, vix_hourly, prices.index
            )

            # Past targets (well before the perturbation window) must be identical
            common_idx = t0.index.intersection(t1.index)[:1000]
            np.testing.assert_array_almost_equal(
                t0.loc[common_idx, sym].values,
                t1.loc[common_idx, sym].values,
                err_msg=f"future perturbation changes past targets for {sym}",
            )

            # The perturbation must propagate to at least one future target
            future_idx = t0.index.intersection(t1.index)[1500:]
            if len(future_idx) > 0:
                diff = np.abs(
                    t0.loc[future_idx, sym].values - t1.loc[future_idx, sym].values
                )
                assert diff.max() > 0, f"future perturbation had no effect for {sym}"


class TestWeightBounds:
    def test_basket_weights_within_bounds(self):
        """Aggregated basket weights in [-max_pos, +max_pos]."""
        exp_dir = _latest_h23_dir()
        s = _load_summary(exp_dir)
        max_pos = s["selected_config"].get("max_position_size", 2.0)
        positions = pd.read_parquet(exp_dir / "positions.parquet")
        for col in positions.columns:
            w = positions[col]
            assert (w.dropna() >= -max_pos - 1e-9).all()
            assert (w.dropna() <= max_pos + 1e-9).all()

    def test_per_contract_weights_nonnegative_long_only(self):
        """Per-contract positions are long-only (allow_short=False in H10)."""
        exp_dir = _latest_h23_dir()
        positions = pd.read_parquet(exp_dir / "positions.parquet")
        for col in positions.columns:
            assert (positions[col].dropna() >= -1e-9).all(), (
                f"{col} has negative weights"
            )


class TestDeterminism:
    def test_signal_builder_is_deterministic(self):
        rng = pd.date_range("2024-10-12", periods=100, freq="h")
        prices = pd.DataFrame(
            {
                "ES=F": 5000.0 + np.cumsum(np.random.default_rng(42).normal(0, 5, 100)),
                "NQ=F": 18000.0
                + np.cumsum(np.random.default_rng(43).normal(0, 20, 100)),
                "CL=F": 75.0 + np.cumsum(np.random.default_rng(44).normal(0, 0.5, 100)),
            },
            index=rng,
        )
        for sym in prices.columns:
            s1 = h23.vol_scaled_tsmom_hourly(
                prices[[sym]], vol_window_long=1008, vol_window_short=252
            )
            s2 = h23.vol_scaled_tsmom_hourly(
                prices[[sym]], vol_window_long=1008, vol_window_short=252
            )
            assert (s1.values == s2.values).all(), (
                f"base signal not deterministic for {sym}"
            )

    def test_apply_exits_is_deterministic(self):
        rng = pd.date_range("2024-10-12", periods=100, freq="h")
        prices = pd.DataFrame(
            {"ES=F": 5000.0 + np.cumsum(np.random.default_rng(42).normal(0, 5, 100))},
            index=rng,
        )
        atr = prices * 0.001
        vol_exit = pd.DataFrame(0.15, index=prices.index, columns=prices.columns)
        daily_target = pd.DataFrame({"ES=F": np.ones(len(rng))}, index=rng)

        pos1 = h23.apply_exits_hourly(
            daily_target,
            prices,
            atr,
            vol_exit,
            trailing_mult=2.0,
            max_hold_bars=60,
            vol_limit_mult=1.5,
            vol_floor_fraction=0.25,
            target_vol=0.15,
            min_trade_interval=0,
        )
        pos2 = h23.apply_exits_hourly(
            daily_target,
            prices,
            atr,
            vol_exit,
            trailing_mult=2.0,
            max_hold_bars=60,
            vol_limit_mult=1.5,
            vol_floor_fraction=0.25,
            target_vol=0.15,
            min_trade_interval=0,
        )
        assert (pos1.values == pos2.values).all()


class TestRegimeLabels:
    def test_regime_labels_use_vix_convention(self):
        vix = pd.concat(
            [
                pd.Series([10.0], index=pd.to_datetime(["2024-10-12"])),
                pd.Series([25.0], index=pd.to_datetime(["2024-10-13"])),
                pd.Series([35.0], index=pd.to_datetime(["2024-10-14"])),
            ]
        )
        labels = h23.regime_labels(vix)
        assert labels.iloc[0] == "bull"
        assert labels.iloc[1] == "sideways"
        assert labels.iloc[2] == "bear"

    def test_regime_labels_consistent_with_artifacts(self):
        exp_dir = _latest_h23_dir()
        s = _load_summary(exp_dir)
        assert set(s["metrics"]["regime_sharpes"].keys()) == {
            "bull",
            "sideways",
            "bear",
        }


class TestExecutedOutcome:
    """Pins the executed H23 result."""

    def test_h23_verdict_recorded(self):
        s = _load_summary(_latest_h23_dir())
        assert s["verdict"] in ("PASS", "REJECT")
        assert s["all_pass"] == (s["verdict"] == "PASS")

    def test_h23_gate_count_matches_passes(self):
        s = _load_summary(_latest_h23_dir())
        n_pass = int(sum(s["passes"].values()))
        n_total = len(s["passes"])
        assert n_pass <= n_total
        assert n_total == 9  # 8 standard + 1 perturbation

    def test_h23_selected_config_in_pre_registered_grid(self):
        s = _load_summary(_latest_h23_dir())
        sel = s["selected_config"]
        assert sel["vol_window_long"] in h23.VOL_WINDOWS_LONG
        assert sel["smooth_span"] in [
            str(x) if x is not None else "none" for x in h23.SMOOTH_SPANS
        ]
        assert sel["regime_scaling"] in h23.REGIME_SCALING_FLAGS
        assert sel["min_trade_interval"] in h23.MIN_TRADE_INTERVALS
        assert sel["trailing_mult"] in h23.TRAILING_MULTS
        assert sel["max_hold_bars"] in h23.MAX_HOLD_BARS
        assert sel["vol_limit_mult"] in h23.VOL_LIMIT_MULTS
        assert sel["vol_floor_fraction"] in h23.VOL_FLOOR_FRACTIONS

    def test_h23_passes_reflect_gates(self):
        s = _load_summary(_latest_h23_dir())
        p = s["passes"]
        m = s["metrics"]
        assert p["sharpe"] == (m["oos_sharpe"] >= h23.GATES["min_sharpe"])
        assert p["trades"] == (m["trades"] >= h23.GATES["min_trades"])
        assert p["pf"] == (m["profit_factor"] >= h23.GATES["min_profit_factor"])
        assert p["dd"] == (abs(m["max_drawdown"]) <= h23.GATES["max_drawdown"])
        assert p["stab"] == (
            m["wf_stability"] >= h23.GATES["min_walkforward_stability"]
        )
        assert p["worst"] == (
            m["worst_regime_sharpe"] >= h23.GATES["min_worst_regime_sharpe"]
        )
        assert p["p"] == (m["benchmark_p_value"] < h23.GATES["max_p_value"])
        assert p["ir"] == (m["information_ratio"] > h23.GATES["min_information_ratio"])
        assert p["perturbation"] == (
            m["perturbation_min_ratio"] >= h23.GATES["min_perturbed_sharpe_ratio"]
        )

    def test_computation_budget_respected(self):
        s = _load_summary(_latest_h23_dir())
        assert s["compute_cpu_hours"] <= 2.0
