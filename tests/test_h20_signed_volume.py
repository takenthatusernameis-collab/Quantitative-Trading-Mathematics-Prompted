"""
Regression tests for the H20 signed-volume / order-flow-imbalance experiment
(run_h20_signed_volume_experiment.py).

Pins:
  * Pre-registered gate thresholds (PROMPT_V2 set + perturbation gate)
  * Pre-registered grid (36 combos), universe, splits, symbols, seed,
    allow_short long/short
  * Artifact schema and summary.json consistency
  * Gate recomputation from the logged equity/trades artifacts
    (exact match to summary.json at 1e-9)
  * Grid/selection integrity (36 unique combos; selection = argmax Val Sharpe)
  * Signal causality (future-volume/price perturbation leaves past targets
    bit-identical)
  * Point-in-time / weight bounds (weights in [-1, +1], long/short allowed)
  * Regime labels consistent with VIX convention
  * Determinism
  * The executed negative result (REJECT)
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

import run_h20_signed_volume_experiment as h20
from qtr.validation.statistics import sharpe_ratio

ART_DIR = ROOT / ".experiments" / "artifacts"
OOS_START = pd.Timestamp("2015-01-01")  # OOS = Val + Test (2015-01 -> 2026-10-08)


def _latest_h20_dir() -> Path:
    h20_dirs = []
    for d in ART_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            with open(d / "summary.json") as f:
                s = json.load(f)
            if s.get("hypothesis") == "H20":
                h20_dirs.append(d)
        except (OSError, json.JSONDecodeError):
            continue
    assert h20_dirs, "no H20 artifacts; run run_h20_signed_volume_experiment.py"
    return max(h20_dirs, key=lambda d: d.name)


def _load_summary(exp_dir: Path) -> dict:
    with open(exp_dir / "summary.json") as f:
        return json.load(f)


class TestPreRegistration:
    def test_gates_are_the_pre_registered_set(self):
        assert h20.GATES == {
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
        assert (
            len(h20.SIGN_RULES)
            * len(h20.TARGET_VOLS)
            * len(h20.MAX_POSITIONS)
            * len(h20.IMBALANCE_LAGS)
            == 36
        )
        assert h20.SIGN_RULES == ["tick", "lee_ready"]
        assert h20.TARGET_VOLS == [0.05, 0.10, 0.15]
        assert h20.MAX_POSITIONS == [0.5, 1.0]
        assert h20.IMBALANCE_LAGS == [1, 3, 5]

    def test_universe_symbols_are_pre_registered(self):
        assert h20.SPY_SYMBOL == "SPY"
        assert h20.QQQ_SYMBOL == "QQQ"
        assert h20.IWM_SYMBOL == "IWM"
        assert h20.VIX_SYMBOL == "^VIX"

    def test_splits_are_the_pre_registered_dates(self):
        assert h20.DATA_START == "2009-01-01"
        assert h20.DATA_END == "2026-10-08"
        assert h20.TRAIN_END == "2014-12-31"
        assert h20.VAL_END == "2019-12-31"

    def test_seed_and_shorting_pre_registered(self):
        assert h20.SEED == 42
        assert h20.INITIAL_CAPITAL == 1_000_000.0
        assert h20.VOL_WINDOW == 63
        assert h20.ALLOW_SHORT is True


class TestArtifacts:
    def test_artifacts_exist(self):
        exp_dir = _latest_h20_dir()
        for name in (
            "summary.json",
            "metadata.json",
            "prices.parquet",
            "volumes.parquet",
            "vix_close.parquet",
            "param_grid_results.parquet",
            "selected_signals.parquet",
            "best_equity.parquet",
            "best_trades.parquet",
            "benchmark_equity.parquet",
            "benchmark_returns.parquet",
        ):
            assert (exp_dir / name).exists(), name

    def test_summary_schema(self):
        s = _load_summary(_latest_h20_dir())
        for k in (
            "experiment_id",
            "hypothesis",
            "selected_config",
            "selection_rule",
            "grid_size",
            "n_evaluated",
            "compute_cpu_hours",
            "vol_window",
            "allow_short",
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
            "benchmark_alpha_annual",
            "perturbation",
            "ablations",
            "cross_validation",
        ):
            assert k in s["metrics"], k
        assert s["hypothesis"] == "H20"
        assert s["grid_size"] == 36
        assert s["n_evaluated"] == 36
        assert s["allow_short"] is True
        assert s["compute_cpu_hours"] <= 2.0

    def test_grid_has_36_unique_combos(self):
        exp_dir = _latest_h20_dir()
        grid = pd.read_parquet(exp_dir / "param_grid_results.parquet")
        assert len(grid) == 36
        keys = set(
            zip(grid["sign_rule"], grid["target_vol"], grid["max_pos"], grid["imbalance_lag"])
        )
        assert len(keys) == 36

    def test_select_on_val_only(self):
        exp_dir = _latest_h20_dir()
        s = _load_summary(exp_dir)
        grid = pd.read_parquet(exp_dir / "param_grid_results.parquet")
        best_val = grid.loc[grid["val_sharpe"].idxmax()]
        sel = s["selected_config"]
        assert sel["sign_rule"] == best_val["sign_rule"]
        assert sel["target_vol"] == best_val["target_vol"]
        assert sel["max_pos"] == best_val["max_pos"]
        assert sel["imbalance_lag"] == best_val["imbalance_lag"]
        assert abs(s["metrics"]["val_sharpe"] - best_val["val_sharpe"]) < 1e-9


class TestGateRecomputation:
    def test_oos_metrics_recomputed_from_artifacts(self):
        """Recompute OOS Sharpe/DD/PF from logged equity & trades,
        exact match to summary.json (1e-9)."""
        exp_dir = _latest_h20_dir()
        s = _load_summary(exp_dir)
        equity = pd.read_parquet(exp_dir / "best_equity.parquet")["equity"]
        trades = pd.read_parquet(exp_dir / "best_trades.parquet")

        rets = equity.pct_change()
        rets.iloc[0] = 0.0
        oos = rets[rets.index >= OOS_START]

        sr = float(sharpe_ratio(oos.values))
        cum = (1 + oos).cumprod()
        dd = float((cum / cum.cummax() - 1.0).min())
        gp = float(oos[oos > 0].sum())
        gl = float(abs(oos[oos < 0].sum()))
        pf = gp / gl if gl > 0 else float("inf")
        ts = pd.to_datetime(trades["timestamp"])
        n_trades = int((ts >= OOS_START).sum())

        m = s["metrics"]
        assert sr == pytest.approx(m["oos_sharpe"], abs=1e-9)
        assert dd == pytest.approx(m["max_drawdown"], abs=1e-9)
        assert pf == pytest.approx(m["profit_factor"], abs=1e-9)
        assert n_trades == m["trades"]

    def test_oos_window_is_protected(self):
        """Test (after VAL_END) is never used for selection."""
        exp_dir = _latest_h20_dir()
        s = _load_summary(exp_dir)
        grid = pd.read_parquet(exp_dir / "param_grid_results.parquet")
        assert "test_sharpe" in grid.columns
        assert "val_sharpe" in grid.columns
        val_max_idx = grid["val_sharpe"].idxmax()
        test_max_idx = grid["test_sharpe"].idxmax()
        sel = s["selected_config"]
        assert grid.loc[val_max_idx, "sign_rule"] == sel["sign_rule"]
        assert grid.loc[val_max_idx, "target_vol"] == sel["target_vol"]
        assert grid.loc[val_max_idx, "max_pos"] == sel["max_pos"]
        assert grid.loc[val_max_idx, "imbalance_lag"] == sel["imbalance_lag"]
        if val_max_idx != test_max_idx:
            assert (
                grid.loc[test_max_idx, "val_sharpe"]
                < grid.loc[val_max_idx, "val_sharpe"]
            )


class TestCausality:
    def test_targets_do_not_look_into_future(self):
        rng = pd.date_range("2020-01-02", periods=80, freq="B")
        ohlc = pd.DataFrame(
            {
                "open": 100.0 + np.cumsum(np.random.default_rng(42).normal(0, 1, 80)),
                "high": 100.0 + np.cumsum(np.random.default_rng(43).normal(0, 1, 80)),
                "low": 100.0 + np.cumsum(np.random.default_rng(44).normal(0, 1, 80)),
                "close": 100.0 + np.cumsum(np.random.default_rng(45).normal(0, 1, 80)),
                "volume": np.abs(np.random.default_rng(46).normal(1e6, 1e5, 80)),
            },
            index=rng,
        )
        # fix high>=close>=low ordering so sign rules are well-defined
        ohlc["high"] = ohlc[["open", "high", "close"]].max(axis=1)
        ohlc["low"] = ohlc[["open", "high", "close", "low"]].min(axis=1)

        for rule in h20.SIGN_RULES:
            for lag in h20.IMBALANCE_LAGS:
                for tv in h20.TARGET_VOLS:
                    for mp in h20.MAX_POSITIONS:
                        t0 = h20.build_targets(
                            ohlc, rule, tv, mp, lag, vol_window=10
                        )
                        # perturb a future volume and a future close price
                        ohlc_pert = ohlc.copy()
                        vol_idx = ohlc_pert.index[55]
                        close_idx = ohlc_pert.index[58]
                        ohlc_pert.loc[vol_idx, "volume"] = ohlc.loc[vol_idx, "volume"] * 3.0
                        ohlc_pert.loc[close_idx, "close"] = ohlc.loc[close_idx, "close"] * 1.5
                        ohlc_pert.loc[close_idx, "high"] = max(
                            ohlc_pert.loc[close_idx, "high"],
                            ohlc_pert.loc[close_idx, "close"],
                        )
                        t1 = h20.build_targets(
                            ohlc_pert, rule, tv, mp, lag, vol_window=10
                        )
                        # Past targets (well before the perturbation window)
                        # must be identical - no lookahead.
                        common_idx = t0.index.intersection(t1.index)[:40]
                        np.testing.assert_array_almost_equal(
                            t0.loc[common_idx, "SPY"].values,
                            t1.loc[common_idx, "SPY"].values,
                            err_msg=(
                                f"future perturbation changes past targets "
                                f"({rule}_tv{tv}_mp{mp}_lag{lag})"
                            ),
                        )
                        # The perturbation must itself propagate to at least
                        # one future target, otherwise the test would be vacuous.
                        future_idx = t0.index.intersection(t1.index)[55:]
                        if len(future_idx) > 0:
                            diff = np.abs(
                                t0.loc[future_idx, "SPY"].values
                                - t1.loc[future_idx, "SPY"].values
                            )
                            assert diff.max() > 0, (
                                f"future perturbation had no effect "
                                f"({rule}_tv{tv}_mp{mp}_lag{lag})"
                            )


class TestWeightBounds:
    def test_weights_within_bounds(self):
        """Long/short strategy: weights in [-1, +1]."""
        exp_dir = _latest_h20_dir()
        sel = pd.read_parquet(exp_dir / "selected_signals.parquet")
        w = sel["SPY"] if "SPY" in sel.columns else sel.iloc[:, 0]
        assert (w.dropna() >= -1.0 - 1e-9).all()
        assert (w.dropna() <= 1.0 + 1e-9).all()


class TestDeterminism:
    def test_signal_builder_is_deterministic(self):
        rng = pd.date_range("2020-01-02", periods=100, freq="B")
        ohlc = pd.DataFrame(
            {
                "open": 100.0 + np.cumsum(np.random.default_rng(42).normal(0, 1, 100)),
                "high": 100.0 + np.cumsum(np.random.default_rng(43).normal(0, 1, 100)),
                "low": 100.0 + np.cumsum(np.random.default_rng(44).normal(0, 1, 100)),
                "close": 100.0 + np.cumsum(np.random.default_rng(45).normal(0, 1, 100)),
                "volume": np.abs(np.random.default_rng(46).normal(1e6, 1e5, 100)),
            },
            index=rng,
        )
        ohlc["high"] = ohlc[["open", "high", "close"]].max(axis=1)
        ohlc["low"] = ohlc[["open", "high", "close", "low"]].min(axis=1)
        for rule in h20.SIGN_RULES:
            for lag in h20.IMBALANCE_LAGS:
                for tv in h20.TARGET_VOLS:
                    for mp in h20.MAX_POSITIONS:
                        t1 = h20.build_targets(ohlc, rule, tv, mp, lag, vol_window=10)
                        t2 = h20.build_targets(ohlc, rule, tv, mp, lag, vol_window=10)
                        assert (t1.values == t2.values).all(), (
                            f"signal not deterministic for "
                            f"{rule}_tv{tv}_mp{mp}_lag{lag}"
                        )

    def test_sign_rule_directions_bounded(self):
        rng = pd.date_range("2020-01-02", periods=60, freq="B")
        ohlc = pd.DataFrame(
            {
                "open": 100.0 + np.cumsum(np.random.default_rng(42).normal(0, 1, 60)),
                "high": 100.0 + np.cumsum(np.random.default_rng(43).normal(0, 1, 60)),
                "low": 100.0 + np.cumsum(np.random.default_rng(44).normal(0, 1, 60)),
                "close": 100.0 + np.cumsum(np.random.default_rng(45).normal(0, 1, 60)),
                "volume": np.abs(np.random.default_rng(46).normal(1e6, 1e5, 60)),
            },
            index=rng,
        )
        ohlc["high"] = ohlc[["open", "high", "close"]].max(axis=1)
        ohlc["low"] = ohlc[["open", "high", "close", "low"]].min(axis=1)
        for rule in h20.SIGN_RULES:
            d = h20.sign_rule_direction(ohlc, rule)
            assert d.isin([-1.0, 0.0, 1.0]).all()


class TestRegimeLabels:
    def test_regime_labels_use_vix_convention(self):
        vix = pd.concat(
            [
                pd.Series([10.0], index=pd.to_datetime(["2020-01-01"])),
                pd.Series([25.0], index=pd.to_datetime(["2020-02-01"])),
                pd.Series([35.0], index=pd.to_datetime(["2020-03-01"])),
            ]
        )
        labels = h20.regime_labels(vix)
        assert labels.iloc[0] == "bull"
        assert labels.iloc[1] == "sideways"
        assert labels.iloc[2] == "bear"

    def test_regime_labels_consistent_with_artifacts(self):
        exp_dir = _latest_h20_dir()
        s = _load_summary(exp_dir)
        assert set(s["metrics"]["regime_sharpes"].keys()) == {
            "bull",
            "sideways",
            "bear",
        }


class TestExecutedOutcome:
    """Pins the executed H20 result (negative result preservation)."""

    def test_h20_reject_verdict(self):
        s = _load_summary(_latest_h20_dir())
        assert s["verdict"] == "REJECT"
        assert s["all_pass"] is False

    def test_h20_reject_gate_count(self):
        s = _load_summary(_latest_h20_dir())
        n_pass = int(sum(s["passes"].values()))
        n_total = len(s["passes"])
        assert n_pass < n_total

    def test_h20_oos_sharpe_below_gate(self):
        s = _load_summary(_latest_h20_dir())
        assert s["metrics"]["oos_sharpe"] < h20.GATES["min_sharpe"]

    def test_h20_selected_config_pre_registered(self):
        s = _load_summary(_latest_h20_dir())
        sel = s["selected_config"]
        assert sel["sign_rule"] in h20.SIGN_RULES
        assert sel["target_vol"] in h20.TARGET_VOLS
        assert sel["max_pos"] in h20.MAX_POSITIONS
        assert sel["imbalance_lag"] in h20.IMBALANCE_LAGS
        assert sel["vol_window"] == h20.VOL_WINDOW

    def test_h20_passes_reflect_gates(self):
        s = _load_summary(_latest_h20_dir())
        p = s["passes"]
        m = s["metrics"]
        assert p["sharpe"] == (m["oos_sharpe"] >= h20.GATES["min_sharpe"])
        assert p["trades"] == (m["trades"] >= h20.GATES["min_trades"])
        assert p["pf"] == (m["profit_factor"] >= h20.GATES["min_profit_factor"])
        assert p["dd"] == (abs(m["max_drawdown"]) <= h20.GATES["max_drawdown"])
        assert p["stab"] == (
            m["wf_stability"] >= h20.GATES["min_walkforward_stability"]
        )
        assert p["worst"] == (
            m["worst_regime_sharpe"] >= h20.GATES["min_worst_regime_sharpe"]
        )
        assert p["p"] == (m["benchmark_p_value"] < h20.GATES["max_p_value"])
        assert p["ir"] == (m["information_ratio"] > h20.GATES["min_information_ratio"])
        assert p["perturbation"] == (
            m["perturbation"]["min_perturbed_sharpe_ratio"]
            >= h20.GATES["min_perturbed_sharpe_ratio"]
        )

    def test_computation_budget_respected(self):
        s = _load_summary(_latest_h20_dir())
        assert s["compute_cpu_hours"] <= 2.0
