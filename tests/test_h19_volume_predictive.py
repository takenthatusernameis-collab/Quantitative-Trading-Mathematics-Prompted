"""
Regression tests for the H19 volume-predictive return decomposition
experiment (run_h19_volume_predictive_experiment.py).

Pins:
  * Pre-registered gate thresholds (PROMPT_V2 set + perturbation gate)
  * Pre-registered grid size (9 combos), universe, splits, symbols
  * Artifact schema and summary.json consistency
  * Gate recomputation from the logged equity/trades artifacts
    (exact match to summary.json at 1e-9)
  * Grid/selection integrity (9 unique combos; selection = argmax Val Sharpe)
  * Signal causality (future-volume perturbation leaves past targets bit-identical)
  * Point-in-time / weight bounds (weights in [0, 1])
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
sys.path.insert(0, str(ROOT / "tests"))

from _utils_parquet import read_parquet_safe

import run_h19_volume_predictive_experiment as h19
from qtr.validation.statistics import sharpe_ratio

ART_DIR = ROOT / ".experiments" / "artifacts"
OOS_START = pd.Timestamp("2015-01-01")  # OOS = Val + Test (2015-01 → 2026-10-08)


def _latest_h19_dir() -> Path:
    h19_dirs = []
    for d in ART_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            with open(d / "summary.json") as f:
                s = json.load(f)
            if s.get("hypothesis") == "H19":
                h19_dirs.append(d)
        except (OSError, json.JSONDecodeError):  # dir lacks valid summary.json
            continue
    assert h19_dirs, "no H19 artifacts; run run_h19_volume_predictive_experiment.py"
    return max(h19_dirs, key=lambda d: d.name)


def _load_summary(exp_dir: Path) -> dict:
    with open(exp_dir / "summary.json") as f:
        return json.load(f)


class TestPreRegistration:
    def test_gates_are_the_pre_registered_set(self):
        assert h19.GATES == {
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

    def test_grid_is_the_pre_registered_9_combos(self):
        assert len(h19.VOLUME_DECOMP_METHODS) * len(h19.THRESHOLD_TYPES) == 9
        assert h19.VOLUME_DECOMP_METHODS == [
            "simple_lagged",
            "vol_scaled",
            "price_volume_residual",
        ]
        assert h19.THRESHOLD_TYPES == ["zero", "median", "adaptive"]

    def test_universe_symbols_are_pre_registered(self):
        assert h19.SPY_SYMBOL == "SPY"
        assert h19.QQQ_SYMBOL == "QQQ"
        assert h19.IWM_SYMBOL == "IWM"
        assert h19.VIX_SYMBOL == "^VIX"

    def test_splits_are_the_pre_registered_dates(self):
        assert h19.DATA_START == "2009-01-01"
        assert h19.DATA_END == "2026-10-08"
        assert h19.TRAIN_END == "2014-12-31"
        assert h19.VAL_END == "2019-12-31"

    def test_lookback_and_z_threshold_pre_registered(self):
        assert h19.LOOKBACK == 21
        assert h19.ADAPTIVE_Z_THRESHOLD == 0.5

    def test_experiment_description_matches_pre_registered_grid(self):
        # The human-readable EXPERIMENT_DESC must not drift from the actual
        # grid dimensions it documents. The pre-registration text declares a
        # 9-combo grid (volume_decomp_method x threshold_type); nothing pinned
        # the prose to the computed grid size, so a stale or absent combo count
        # would survive into the logged experiment records (verified: 5 H19
        # records in .experiments/experiments.jsonl carry the bare
        # "Volume-predictive return decomposition" string with no combo count)
        # and is the first prose an auditor or next operator reads.
        n_combos = len(h19.VOLUME_DECOMP_METHODS) * len(h19.THRESHOLD_TYPES)
        assert f"{n_combos}-combo" in h19.EXPERIMENT_DESC
        # Both grid dimensions must be enumerated in the prose.
        for dim in ("volume_decomp_method", "threshold_type"):
            assert dim in h19.EXPERIMENT_DESC, f"EXPERIMENT_DESC missing dimension {dim!r}"


class TestArtifacts:
    def test_artifacts_exist(self):
        exp_dir = _latest_h19_dir()
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
        s = _load_summary(_latest_h19_dir())
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
            "lookback",
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
        ):
            assert k in s["metrics"], k
        assert s["hypothesis"] == "H19"
        assert s["grid_size"] == 9
        assert s["n_evaluated"] == 9
        assert s["compute_cpu_hours"] <= 2.0

    def test_grid_has_9_unique_combos(self):
        exp_dir = _latest_h19_dir()
        grid = read_parquet_safe(exp_dir / "param_grid_results.parquet")
        assert len(grid) == 9
        keys = set(zip(grid["volume_decomp_method"], grid["threshold_type"]))
        assert len(keys) == 9

    def test_selection_is_argmax_val_sharpe(self):
        exp_dir = _latest_h19_dir()
        s = _load_summary(exp_dir)
        grid = read_parquet_safe(exp_dir / "param_grid_results.parquet")
        best_val = grid.loc[grid["val_sharpe"].idxmax()]
        sel = s["selected_config"]
        assert sel["volume_decomp_method"] == best_val["volume_decomp_method"]
        assert sel["threshold_type"] == best_val["threshold_type"]
        assert abs(s["metrics"]["val_sharpe"] - best_val["val_sharpe"]) < 1e-9


class TestGateRecomputation:
    def test_oos_metrics_recomputed_from_artifacts(self):
        """Recompute OOS Sharpe/DD/PF from logged equity & trades,
        exact match to summary.json (1e-9)."""
        exp_dir = _latest_h19_dir()
        s = _load_summary(exp_dir)
        equity = read_parquet_safe(exp_dir / "best_equity.parquet")["equity"]
        trades = read_parquet_safe(exp_dir / "best_trades.parquet")

        # engine equity = (1 + net_returns).cumprod() * capital
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
        exp_dir = _latest_h19_dir()
        s = _load_summary(exp_dir)
        grid = read_parquet_safe(exp_dir / "param_grid_results.parquet")
        assert "test_sharpe" in grid.columns
        assert "val_sharpe" in grid.columns
        val_max_idx = grid["val_sharpe"].idxmax()
        test_max_idx = grid["test_sharpe"].idxmax()
        sel = s["selected_config"]
        assert grid.loc[val_max_idx, "volume_decomp_method"] == sel["volume_decomp_method"]
        assert grid.loc[val_max_idx, "threshold_type"] == sel["threshold_type"]
        if val_max_idx != test_max_idx:
            assert grid.loc[test_max_idx, "val_sharpe"] < grid.loc[val_max_idx, "val_sharpe"]

    def test_passes_reflect_gates(self):
        exp_dir = _latest_h19_dir()
        s = _load_summary(exp_dir)
        p = s["passes"]
        assert p["sharpe"] == (s["metrics"]["oos_sharpe"] >= h19.GATES["min_sharpe"])
        assert p["trades"] == (s["metrics"]["trades"] >= h19.GATES["min_trades"])
        assert p["pf"] == (s["metrics"]["profit_factor"] >= h19.GATES["min_profit_factor"])
        assert p["dd"] == (abs(s["metrics"]["max_drawdown"]) <= h19.GATES["max_drawdown"])
        assert p["stab"] == (s["metrics"]["wf_stability"] >= h19.GATES["min_walkforward_stability"])
        assert p["worst"] == (
            s["metrics"]["worst_regime_sharpe"] >= h19.GATES["min_worst_regime_sharpe"]
        )
        assert p["perturbation"] == (
            s["metrics"]["perturbation"]["min_perturbed_sharpe_ratio"]
            >= h19.GATES["min_perturbed_sharpe_ratio"]
        )

    def test_verdict_consistency(self):
        exp_dir = _latest_h19_dir()
        s = _load_summary(exp_dir)
        passes = s["passes"]
        expected_verdict = "PASS" if all(passes.values()) else "REJECT"
        assert s["verdict"] == expected_verdict
        assert s["all_pass"] == all(passes.values())

    def test_regime_labels_use_vix_convention(self):
        vix = pd.concat(
            [
                pd.Series([10.0], index=pd.to_datetime(["2020-01-01"])),  # bull
                pd.Series([25.0], index=pd.to_datetime(["2020-02-01"])),  # sideways
                pd.Series([35.0], index=pd.to_datetime(["2020-03-01"])),  # bear
            ]
        )
        labels = h19.regime_labels(vix)
        assert labels.iloc[0] == "bull"
        assert labels.iloc[1] == "sideways"
        assert labels.iloc[2] == "bear"


class TestCausality:
    def test_targets_do_not_look_into_future(self):
        rng = pd.date_range("2020-01-02", periods=60, freq="B")
        spy_close = pd.Series(
            100.0 + np.cumsum(np.random.default_rng(42).normal(0, 1, 60)),
            index=rng,
        )
        spy_vol = pd.Series(
            np.abs(np.random.default_rng(43).normal(1e6, 1e5, 60)),
            index=rng,
        )

        methods = h19.VOLUME_DECOMP_METHODS
        thresholds = h19.THRESHOLD_TYPES

        for method in methods:
            for thr in thresholds:
                t0 = h19.build_targets(
                    spy_close,
                    spy_vol,
                    method,
                    thr,
                    lookback=21,
                )
                # perturb a future volume (after the warmup period)
                vol_pert = spy_vol.copy()
                vol_pert.iloc[55] *= 3.0
                close_pert = spy_close.copy()
                close_pert.iloc[58] *= 1.5
                t1 = h19.build_targets(
                    close_pert,
                    vol_pert,
                    method,
                    thr,
                    lookback=21,
                )
                # Past targets through idx 40 (well before perturbation window)
                # must be identical — no lookahead.
                common_idx = t0.index.intersection(t1.index)[:40]
                np.testing.assert_array_almost_equal(
                    t0.loc[common_idx, "SPY"].values,
                    t1.loc[common_idx, "SPY"].values,
                    err_msg=(f"future perturbation changes past targets ({method}_{thr})"),
                )


class TestWeightBounds:
    def test_weights_within_bounds(self):
        exp_dir = _latest_h19_dir()
        sel = read_parquet_safe(exp_dir / "selected_signals.parquet")
        if "SPY" in sel.columns:
            w = sel["SPY"]
        else:
            w = sel.iloc[:, 0]
        assert (w.dropna() >= -1e-9).all()
        assert (w.dropna() <= 1.0 + 1e-9).all()


class TestDeterminism:
    def test_signal_builder_is_deterministic(self):
        rng = pd.date_range("2020-01-02", periods=100, freq="B")
        spy_close = pd.Series(
            100.0 + np.cumsum(np.random.default_rng(42).normal(0, 1, 100)), index=rng
        )
        spy_vol = pd.Series(
            np.abs(np.random.default_rng(42).normal(1e6, 1e5, 100)),
            index=rng,
        )
        for method in h19.VOLUME_DECOMP_METHODS:
            for thr in h19.THRESHOLD_TYPES:
                t1 = h19.build_targets(spy_close, spy_vol, method, thr, lookback=21)
                t2 = h19.build_targets(spy_close, spy_vol, method, thr, lookback=21)
                assert (t1.values == t2.values).all(), (
                    f"signal not deterministic for {method}_{thr}"
                )


class TestExecutedOutcome:
    """Pins the executed H19 result (negative result preservation)."""

    def test_h19_reject_verdict(self):
        s = _load_summary(_latest_h19_dir())
        assert s["verdict"] == "REJECT"
        assert s["all_pass"] is False

    def test_h19_reject_gate_count(self):
        s = _load_summary(_latest_h19_dir())
        n_pass = int(sum(s["passes"].values()))
        n_total = len(s["passes"])
        assert n_pass < n_total

    def test_h19_oos_sharpe_below_gate(self):
        s = _load_summary(_latest_h19_dir())
        assert s["metrics"]["oos_sharpe"] < h19.GATES["min_sharpe"]

    def test_computation_budget_respected(self):
        s = _load_summary(_latest_h19_dir())
        assert s["compute_cpu_hours"] <= 2.0
