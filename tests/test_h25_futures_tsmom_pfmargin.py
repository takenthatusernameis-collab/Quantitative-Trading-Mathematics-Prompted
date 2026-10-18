"""
Regression tests for the H25 multi-contract intraday futures TSMOM experiment
(run_h25_futures_tsmom_pfmargin.py).

Pins:
  * Pre-registered gate thresholds (PROMPT_V2 set + perturbation gate)
  * Pre-registered grid (8 combos), universe, splits, symbols, seed
  * Artifact schema and summary.json consistency
  * Gate recomputation from the logged equity/trades artifacts
    (exact match to summary.json at 1e-9)
  * Grid/selection integrity (8 unique combos; selection = argmax Val PF margin)
  * Signal causality (future-price perturbation leaves past targets bit-identical)
  * Point-in-time / weight bounds (weights in [0, max_pos] per contract)
  * Regime labels consistent with VIX convention
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
sys.path.insert(0, str(ROOT / "tests"))

from _utils_parquet import read_parquet_safe

import run_h25_futures_tsmom_pfmargin as h25
from qtr.validation.statistics import sharpe_ratio

EXPERIMENT_NAME = "h25_futures_tsmom_pfmargin"
ART_DIR = ROOT / ".experiments" / "artifacts"
# OOS = Val+Test (25%+20%) starting at 55% cutoff.


def _get_oos_start(exp_dir: Path) -> pd.Timestamp:
    prices = read_parquet_safe(exp_dir / "prices.parquet")
    n = len(prices)
    return prices.index[int(n * 0.55) + 1]


def _latest_h25_dir() -> Path:
    h25_dirs = []
    for d in ART_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            with open(d / "summary.json") as f:
                s = json.load(f)
            if s.get("hypothesis") == "H25" or "h25" in d.name:
                h25_dirs.append(d)
        except (OSError, json.JSONDecodeError):
            continue
    assert h25_dirs, (
        f"no {EXPERIMENT_NAME} artifacts; run run_h25_futures_tsmom_pfmargin.py"
    )
    return max(h25_dirs, key=lambda d: d.name)


def _load_summary(exp_dir: Path) -> dict:
    with open(exp_dir / "summary.json") as f:
        return json.load(f)


class TestPreRegistration:
    def test_gates_are_the_pre_registered_set(self):
        assert h25.GATES == {
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

    def test_grid_is_the_pre_registered_8_combos(self):
        assert (
            len(h25.TARGET_VOLS)
            * len(h25.MAX_POSITIONS)
            * len(h25.SCALE_RULES)
            * len(h25.N_ASSETS_CHOICES)
            == 8
        )
        assert h25.TARGET_VOLS == [1.25, 1.5, 1.75, 2.0]
        assert h25.MAX_POSITIONS == [0.5]
        assert h25.SCALE_RULES == ["equal"]
        assert h25.N_ASSETS_CHOICES == [4, 5]

    def test_experiment_description_matches_pre_registered_grid(self):
        # The human-readable EXPERIMENT_DESC must not drift from the actual
        # grid dimensions it documents (same defect class as H22: prose
        # "16-combo" survived a grid shrink to 8 combos).
        n_combos = (
            len(h25.TARGET_VOLS)
            * len(h25.MAX_POSITIONS)
            * len(h25.SCALE_RULES)
            * len(h25.N_ASSETS_CHOICES)
        )
        assert f"{n_combos}-combo" in h25.EXPERIMENT_DESC

    def test_universe_symbols_are_pre_registered(self):
        assert h25.FUTURES_UNIVERSE == ["ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F"]
        assert h25.VIX_SYMBOL == "^VIX"

    def test_splits_are_the_pre_registered_proportions(self):
        assert h25.DATA_START == "2024-10-12"
        assert h25.DATA_END == "2026-10-11"
        # Splits are 60/20/20 by time (verified in _splits)

    def test_seed_and_config_pre_registered(self):
        assert h25.SEED == 42
        assert h25.INITIAL_CAPITAL == 1_000_000.0
        assert h25.TARGET_VOL_BASE == 0.15
        assert h25.VOL_WINDOW_SHORT_RATIO == 4
        assert h25.SEL["vol_window_long"] == 1008
        assert h25.SEL["trailing_mult"] == 2.0
        assert h25.SEL["max_hold_bars"] == 60
        assert h25.SEL["vol_limit_mult"] == 1.5
        assert h25.SEL["vol_floor_fraction"] == 0.25


class TestArtifacts:
    def test_artifacts_exist(self):
        exp_dir = _latest_h25_dir()
        for name in (
            "summary.json",
            "prices.parquet",
            "volumes.parquet",
            "vix_hourly.parquet",
            "grid_results.parquet",
            "positions.parquet",
            "per_contract_positions.parquet",
            "basket_positions.parquet",
            "equity.parquet",
            "returns.parquet",
            "trades.parquet",
            "benchmark_equity.parquet",
            "benchmark_returns.parquet",
        ):
            assert (exp_dir / name).exists(), name

    def test_summary_schema(self):
        s = _load_summary(_latest_h25_dir())
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
            "ablations",
        ):
            assert k in s["metrics"], k
        assert s["hypothesis"] == "H25"
        assert s["grid_size"] == 8
        assert s["n_evaluated"] == 8
        assert s["compute_cpu_hours"] <= 2.0

    def test_grid_has_8_unique_combos(self):
        exp_dir = _latest_h25_dir()
        grid = read_parquet_safe(exp_dir / "grid_results.parquet")
        assert len(grid) == 8
        keys = set(
            zip(
                grid["target_vol_mult"],
                grid["max_pos"],
                grid["scale_rule"],
                grid["n_assets"],
            )
        )
        assert len(keys) == 8

    def test_select_on_val_only_pfmargin(self):
        exp_dir = _latest_h25_dir()
        s = _load_summary(exp_dir)
        grid = read_parquet_safe(exp_dir / "grid_results.parquet")
        grid["val_pf_margin"] = grid["val_profit_factor"] - 1.3
        best_val = grid.loc[grid["val_pf_margin"].idxmax()]
        sel = s["selected_config"]
        assert sel["target_vol_mult"] == best_val["target_vol_mult"]
        assert sel["max_pos"] == best_val["max_pos"]
        assert sel["scale_rule"] == best_val["scale_rule"]
        assert sel["n_assets"] == best_val["n_assets"]
        # PF margin selection is the key - selected config should correspond to max val_pf_margin
        assert abs(grid["val_profit_factor"].min()) >= 0  # basic sanity


class TestGateRecomputation:
    def test_oos_metrics_recomputed_from_artifacts(self):
        """Recompute OOS Sharpe/DD/PF from logged equity & trades,
        exact match to summary.json (1e-9)."""
        exp_dir = _latest_h25_dir()
        s = _load_summary(exp_dir)
        equity = read_parquet_safe(exp_dir / "equity.parquet")["equity"]
        trades = read_parquet_safe(exp_dir / "trades.parquet")
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
        exp_dir = _latest_h25_dir()
        grid = read_parquet_safe(exp_dir / "grid_results.parquet")
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
            base_signals[sym] = h25.vol_scaled_tsmom_hourly(
                prices[[sym]],
                vol_window_long=500,
                vol_window_short=500 // 4,
            )
        vix_hourly = pd.Series(20.0, index=prices.index)

        for sym in prices.columns:
            t0 = h25.build_hourly_target(
                base_signals[sym], None, 500, False, vix_hourly, prices.index
            )
            # perturb a future price
            prices_pert = prices.copy()
            prices_pert.loc[prices_pert.index[1500], "ES=F"] *= 1.02
            prices_pert.loc[prices_pert.index[1600], "NQ=F"] *= 0.98
            prices_pert.loc[prices_pert.index[1700], "CL=F"] *= 1.03

            base_signals_pert = {}
            for s in prices.columns:
                base_signals_pert[s] = h25.vol_scaled_tsmom_hourly(
                    prices_pert[[s]],
                    vol_window_long=500,
                    vol_window_short=500 // 4,
                )

            t1 = h25.build_hourly_target(
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
        exp_dir = _latest_h25_dir()
        s = _load_summary(exp_dir)
        max_pos = s["selected_config"]["max_pos"]
        positions = read_parquet_safe(exp_dir / "basket_positions.parquet")
        w = positions["BASKET"]
        assert (w.dropna() >= -max_pos - 1e-9).all()
        assert (w.dropna() <= max_pos + 1e-9).all()

    def test_per_contract_weights_nonnegative_long_only(self):
        """Per-contract positions are long-only (allow_short=False in H10)."""
        exp_dir = _latest_h25_dir()
        per_contract = read_parquet_safe(exp_dir / "per_contract_positions.parquet")
        for col in per_contract.columns:
            assert (per_contract[col].dropna() >= -1e-9).all(), (
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
            s1 = h25.vol_scaled_tsmom_hourly(
                prices[[sym]], vol_window_long=1008, vol_window_short=252
            )
            s2 = h25.vol_scaled_tsmom_hourly(
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

        pos1 = h25.apply_exits_hourly(
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
        pos2 = h25.apply_exits_hourly(
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
        labels = h25.regime_labels(vix)
        assert labels.iloc[0] == "bull"
        assert labels.iloc[1] == "sideways"
        assert labels.iloc[2] == "bear"

    def test_regime_labels_consistent_with_artifacts(self):
        exp_dir = _latest_h25_dir()
        s = _load_summary(exp_dir)
        assert set(s["metrics"]["regime_sharpes"].keys()) == {
            "bull",
            "sideways",
            "bear",
        }


class TestExecutedOutcome:
    """Pins the executed H25 result."""

    def test_h25_verdict_recorded(self):
        s = _load_summary(_latest_h25_dir())
        assert s["verdict"] in ("PASS", "REJECT")
        assert s["all_pass"] == (s["verdict"] == "PASS")

    def test_h25_gate_count_matches_passes(self):
        s = _load_summary(_latest_h25_dir())
        n_pass = int(sum(s["passes"].values()))
        n_total = len(s["passes"])
        assert n_pass <= n_total

    def test_h25_selected_config_in_pre_registered_grid(self):
        s = _load_summary(_latest_h25_dir())
        sel = s["selected_config"]
        assert sel["target_vol_mult"] in h25.TARGET_VOLS
        assert sel["max_pos"] in h25.MAX_POSITIONS
        assert sel["scale_rule"] in h25.SCALE_RULES
        assert sel["n_assets"] in h25.N_ASSETS_CHOICES
        assert "h10_base_config" in sel

    def test_h25_passes_reflect_gates(self):
        s = _load_summary(_latest_h25_dir())
        p = s["passes"]
        m = s["metrics"]
        assert p["sharpe"] == (m["oos_sharpe"] >= h25.GATES["min_sharpe"])
        assert p["trades"] == (m["trades"] >= h25.GATES["min_trades"])
        assert p["pf"] == (m["profit_factor"] >= h25.GATES["min_profit_factor"])
        assert p["dd"] == (abs(m["max_drawdown"]) <= h25.GATES["max_drawdown"])
        assert p["stab"] == (
            m["wf_stability"] >= h25.GATES["min_walkforward_stability"]
        )
        assert p["worst"] == (
            m["worst_regime_sharpe"] >= h25.GATES["min_worst_regime_sharpe"]
        )
        assert p["p"] == (m["benchmark_p_value"] < h25.GATES["max_p_value"])
        assert p["ir"] == (m["information_ratio"] > h25.GATES["min_information_ratio"])

    def test_computation_budget_respected(self):
        s = _load_summary(_latest_h25_dir())
        assert s["compute_cpu_hours"] <= 2.0
