"""
Regression tests for the H16 cross-sectional equity factor-timing
experiment (run_h16_factor_timing_experiment.py).

Pins:
  * Pre-registered gate thresholds (unchanged PROMPT_V2 set +
    the +/-20% perturbation gate)
  * Artifact schema and verdict consistency (summary.json)
  * Gate recomputation from the logged equity/trades artifacts
  * Grid integrity (54 combos; selection = argmax train-only WF Sharpe)
  * Signal causality (no look-ahead into future prices)
  * Point-in-time universe (zero weight before ETF inception)
  * Monthly rebalancing (positions constant within each month)
  * Weight bounds, exposure cap, and top-1-per-family invariant
  * Determinism of the signal builder
  * The executed negative result (REJECT, 2/9 gates)
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

import run_h16_factor_timing_experiment as h16
from qtr.validation.statistics import sharpe_ratio

ART_DIR = ROOT / ".experiments" / "artifacts"
VAL_START = pd.Timestamp("2018-01-01")  # OOS = Val + Test


def _latest_h16_dir() -> Path:
    h16_dirs = []
    for d in ART_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            with open(d / "summary.json") as f:
                s = json.load(f)
            if s.get("hypothesis") == "H16":
                h16_dirs.append(d)
        except Exception:  # noqa: BLE001, S112 -- skip non-conforming artifact dirs during discovery
            continue
    assert h16_dirs, "no H16 artifacts; run run_h16_factor_timing_experiment.py"
    return max(h16_dirs, key=lambda d: d.name)


def _load_summary(exp_dir: Path) -> dict:
    with open(exp_dir / "summary.json") as f:
        return json.load(f)


class TestPreRegistration:
    def test_gates_are_the_pre_registered_set(self):
        assert h16.GATES == {
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

    def test_grid_is_the_pre_registered_54_combos(self):
        assert len(h16.LOOKBACKS) * len(h16.SKIPS) * len(h16.REGIME_EXPOSURES) * len(h16.N_FACTORS_OPTS) == 54
        assert h16.LOOKBACKS == [63, 126, 252]
        assert h16.SKIPS == [1, 5, 21]
        assert h16.REGIME_EXPOSURES == [(1.0, 0.5, 0.25), (1.0, 0.25, 0.10)]
        assert h16.N_FACTORS_OPTS == [1, 2, 3]

    def test_universe_is_the_pre_registered_9_etfs(self):
        assert set(h16.UNIVERSE) == {
            "VLUE", "IJS", "VTV", "MTUM", "QQQ", "SPYG", "QUAL", "SPHQ", "USMF",
        }
        assert h16.FACTOR_FAMILIES == {
            "value": ["VLUE", "IJS", "VTV"],
            "momentum": ["MTUM", "QQQ", "SPYG"],
            "quality": ["QUAL", "SPHQ", "USMF"],
        }

    def test_splits_are_the_pre_registered_dates(self):
        assert h16.TRAIN_END == "2017-12-31"
        assert h16.VAL_END == "2020-12-31"
        assert h16.DATA_START == "2010-01-01"
        assert h16.DATA_END == "2024-12-31"


class TestArtifacts:
    def test_artifacts_exist(self):
        exp_dir = _latest_h16_dir()
        for name in (
            "summary.json", "prices.parquet", "volumes.parquet",
            "vix_close.parquet", "param_grid_results.parquet",
            "selected_signals.parquet", "best_equity.parquet",
            "best_trades.parquet", "benchmark_equity.parquet",
            "benchmark_returns.parquet", "family_exposure.parquet",
        ):
            assert (exp_dir / name).exists(), name

    def test_summary_schema(self):
        s = _load_summary(_latest_h16_dir())
        for k in (
            "experiment_id", "hypothesis", "selected_config",
            "selection_rule", "grid_size", "n_evaluated",
            "compute_cpu_hours", "metrics", "passes", "all_pass",
            "verdict", "inception_dates",
        ):
            assert k in s, k
        for k in (
            "train_sharpe", "val_sharpe", "test_sharpe", "oos_sharpe",
            "profit_factor", "max_drawdown", "trades", "wf_stability",
            "worst_regime_sharpe", "regime_sharpes", "benchmark_p_value",
            "information_ratio", "perturbation", "ablations",
        ):
            assert k in s["metrics"], k
        assert s["hypothesis"] == "H16"
        assert s["grid_size"] == 54
        assert s["n_evaluated"] == 54
        assert s["compute_cpu_hours"] <= 2.0  # pre-registered budget

    def test_verdict_consistency(self):
        s = _load_summary(_latest_h16_dir())
        assert s["all_pass"] == all(s["passes"].values())
        assert s["verdict"] == ("PASS" if s["all_pass"] else "REJECT")
        assert set(s["passes"]) == {
            "sharpe", "trades", "pf", "dd", "stab",
            "worst", "p", "ir", "perturbation",
        }


class TestGateRecomputation:
    def test_oos_metrics_recomputed_from_artifacts(self):
        exp_dir = _latest_h16_dir()
        s = _load_summary(exp_dir)
        equity = pd.read_parquet(exp_dir / "best_equity.parquet")["equity"]
        trades = pd.read_parquet(exp_dir / "best_trades.parquet")

        # engine equity = (1 + net_returns).cumprod() * capital
        rets = equity.pct_change()
        rets.iloc[0] = 0.0
        oos = rets[rets.index >= VAL_START]

        sr = float(sharpe_ratio(oos.values))
        cum = (1 + oos).cumprod()
        dd = float((cum / cum.cummax() - 1.0).min())
        gp = float(oos[oos > 0].sum())
        gl = float(abs(oos[oos < 0].sum()))
        pf = gp / gl
        ts = pd.to_datetime(trades["timestamp"])
        n_trades = int((ts >= VAL_START).sum())

        m = s["metrics"]
        assert sr == pytest.approx(m["oos_sharpe"], abs=1e-9)
        assert dd == pytest.approx(m["max_drawdown"], abs=1e-9)
        assert pf == pytest.approx(m["profit_factor"], abs=1e-9)
        assert n_trades == m["trades"]

    def test_oos_window_is_protected_val_plus_test(self):
        exp_dir = _latest_h16_dir()
        equity = pd.read_parquet(exp_dir / "best_equity.parquet")["equity"]
        oos = equity[equity.index >= VAL_START]
        # Val 2018-01-01 .. Test end 2024-12-30
        assert oos.index[0] >= VAL_START
        assert oos.index[-1] <= pd.Timestamp("2024-12-31")
        assert len(oos) > 1500  # ~7 years of daily bars


class TestGridAndSelection:
    def test_grid_has_54_unique_combos(self):
        exp_dir = _latest_h16_dir()
        grid = pd.read_parquet(exp_dir / "param_grid_results.parquet")
        assert len(grid) == 54
        assert set(grid["lookback"]) == {63, 126, 252}
        assert set(grid["skip"]) == {1, 5, 21}
        assert set(grid["n_factors"]) == {1, 2, 3}
        assert len(set(grid["regime_exposure"])) == 2
        assert grid.duplicated(
            ["lookback", "skip", "regime_exposure", "n_factors"]
        ).sum() == 0

    def test_selection_is_argmax_train_wf_sharpe(self):
        exp_dir = _latest_h16_dir()
        s = _load_summary(exp_dir)
        grid = pd.read_parquet(exp_dir / "param_grid_results.parquet")
        best = grid.loc[grid["train_wf_sharpe"].idxmax()]
        sel = s["selected_config"]
        assert int(best["lookback"]) == sel["lookback"]
        assert int(best["skip"]) == sel["skip"]
        assert int(best["n_factors"]) == sel["n_factors"]
        assert list(eval(best["regime_exposure"])) == sel["regime_exposure"]

    def test_selection_rule_documentation(self):
        s = _load_summary(_latest_h16_dir())
        assert "train-only" in s["selection_rule"]
        assert "protected" in s["selection_rule"]


class TestSignalInvariants:
    def _prices_vix(self):
        exp_dir = _latest_h16_dir()
        prices = pd.read_parquet(exp_dir / "prices.parquet")
        vix = pd.read_parquet(exp_dir / "vix_close.parquet")["close"]
        return prices, vix

    def test_factor_momentum_is_exactly_causal(self):
        rng = np.random.default_rng(0)
        n = 600
        idx = pd.bdate_range("2015-01-01", periods=n)
        px = pd.DataFrame(
            {"A": 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, n)))},
            index=idx,
        )
        mom = h16.factor_momentum(px, 63, 5)
        for t in range(100, n - 50):
            expected = px["A"].iloc[t - 5] / px["A"].iloc[t - 5 - 63] - 1.0
            assert mom["A"].iloc[t] == pytest.approx(expected, abs=1e-12)

    def test_targets_do_not_look_into_the_future(self):
        prices, vix = self._prices_vix()
        t1 = h16.build_daily_targets(
            prices, vix, 63, 5, (1.0, 0.5, 0.25), 2
        )
        p2 = prices.copy()
        p2.iloc[-100:] = p2.iloc[-100:] * 1.07  # perturb the future
        t2 = h16.build_daily_targets(
            p2, vix, 63, 5, (1.0, 0.5, 0.25), 2
        )
        # targets at t use prices only through t - skip - lookback;
        # with the last 100 days perturbed, everything before
        # index[-100] is provably unaffected (conservative cut).
        cut = prices.index[-100]
        assert (t1.loc[:cut].values == t2.loc[:cut].values).all()

    def test_point_in_time_universe_zero_before_inception(self):
        exp_dir = _latest_h16_dir()
        pos = pd.read_parquet(exp_dir / "selected_signals.parquet")
        prices = pd.read_parquet(exp_dir / "prices.parquet")
        for etf in h16.UNIVERSE:
            inc = prices[etf].first_valid_index()
            assert (pos[etf].loc[:inc] == 0).all(), etf

    def test_monthly_rebalance_positions_constant_within_month(self):
        exp_dir = _latest_h16_dir()
        pos = pd.read_parquet(exp_dir / "selected_signals.parquet")
        changes = pos.diff().abs().sum(axis=1)
        change_dates = changes[changes > 1e-12].index
        for d in change_dates:
            month_rows = pos.loc[pos.index.to_period("M") == d.to_period("M")]
            assert d == month_rows.index[-1], (
                f"position changed on non-month-end date {d}"
            )

    def test_weight_bounds_and_exposure_cap(self):
        exp_dir = _latest_h16_dir()
        pos = pd.read_parquet(exp_dir / "selected_signals.parquet")
        assert (pos.values >= -1e-12).all()
        assert (pos.values <= 1.0 + 1e-9).all()
        assert (pos.sum(axis=1).values <= 1.0 + 1e-9).all()

    def test_at_most_one_etf_per_family(self):
        exp_dir = _latest_h16_dir()
        pos = pd.read_parquet(exp_dir / "selected_signals.parquet")
        for fam, etfs in h16.FACTOR_FAMILIES.items():
            nonzero = (pos[etfs].abs() > 0).sum(axis=1)
            assert (nonzero <= 1).all(), fam

    def test_signal_builder_is_deterministic(self):
        prices, vix = self._prices_vix()
        t1 = h16.build_daily_targets(prices, vix, 126, 21, (1.0, 0.25, 0.10), 3)
        t2 = h16.build_daily_targets(prices, vix, 126, 21, (1.0, 0.25, 0.10), 3)
        assert (t1.values == t2.values).all()

    def test_regime_factor_thresholds(self):
        vix = pd.Series([15.0, 25.0, 35.0], index=pd.bdate_range("2020-01-01", periods=3))
        f = h16.regime_factor_series(vix, (1.0, 0.5, 0.25))
        assert f.iloc[0] == 1.0
        assert f.iloc[1] == 0.5
        assert f.iloc[2] == 0.25


class TestExecutedOutcome:
    """Pins the executed H16 result (negative result preservation)."""

    def test_h16_reject_verdict(self):
        s = _load_summary(_latest_h16_dir())
        assert s["verdict"] == "REJECT"
        # only the perturbation gate passed; the monthly-rebalance
        # turnover structure (184 trades < 200) fails the trades
        # gate as well as the Sharpe/PF/DD/stability/regime/
        # benchmark gates.
        assert s["passes"]["perturbation"] is True
        for g in ("sharpe", "trades", "pf", "dd", "stab",
                  "worst", "p", "ir"):
            assert s["passes"][g] is False, g

    def test_oos_sharpe_below_gate(self):
        s = _load_summary(_latest_h16_dir())
        assert s["metrics"]["oos_sharpe"] < h16.GATES["min_sharpe"]

    def test_family_ablations_are_distinct(self):
        # per-family ablations must restrict the universe to the
        # single family (regression pin for the ablation fix)
        s = _load_summary(_latest_h16_dir())
        abl = s["metrics"]["ablations"]
        sharpes = [
            abl[f"family_{f}"]["oos_metrics"]["sharpe"]
            for f in ("value", "momentum", "quality")
        ]
        assert len({round(x, 6) for x in sharpes}) == 3

    def test_perturbation_gate_evaluated(self):
        s = _load_summary(_latest_h16_dir())
        pert = s["metrics"]["perturbation"]
        assert set(pert["variants"]) == {
            "lookback=50", "lookback=76", "skip=4", "skip=6",
        } or len(pert["variants"]) == 4
        assert 0.0 <= pert["min_perturbed_sharpe_ratio"] <= 1.0
