from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261122_01", ROOT / "run_nf_20261122_01_share_turnover.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _synthetic_data(n_days=800, n_names=6, seed=0):
    """Geometric price paths, positive volumes and quarterly share counts.

    No network: closes/volumes are synthetic, share counts are point-in-time
    (filed ~45 days after each quarter end). Returns (closes, volumes, shares,
    calendar) where ``shares`` is symbol -> DataFrame[end, filed, shares].
    """
    rng = np.random.default_rng(seed)
    calendar = pd.bdate_range("2020-01-01", periods=n_days)
    rets = rng.normal(0.0, 0.01, size=(n_days, n_names))
    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    columns = [f"S{i}" for i in range(n_names)]
    closes = pd.DataFrame(prices, index=calendar, columns=columns)
    volumes = pd.DataFrame(
        rng.uniform(1e6, 5e6, size=(n_days, n_names)), index=calendar, columns=columns
    )
    ends = pd.date_range("2019-01-01", periods=16, freq="90D")
    filed = ends + pd.Timedelta(days=45)
    shares = {}
    for j, col in enumerate(columns):
        values = 1.0e9 * (1.0 + 0.05 * j) * np.ones(len(ends))
        shares[col] = pd.DataFrame({"end": ends, "filed": filed, "shares": values})
    return closes, volumes, shares, calendar


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261122_01_share_turnover"
    assert mod.NF_ID == "NF-20261122-01"
    assert mod.HYPOTHESIS == "H196"
    assert mod.START == "2011-01-03"
    assert mod.END == "2026-11-21"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.MIN_PRICE_OBSERVATIONS == 252
    assert mod.GATES == mod.h184.GATES
    assert mod.TURNOVER_WINDOWS == [21, 252]
    assert mod.FEATURES == ["turnover_21", "turnover_252"]
    assert mod.VOL_LOOKBACK == 60
    assert mod.DAYS_PER_YEAR == 252


def test_universe_is_sp100_minus_exclusions():
    assert len(mod.UNIVERSE_SYMBOLS) == 98
    assert "XOM" not in mod.UNIVERSE_SYMBOLS
    assert "BKNG" not in mod.UNIVERSE_SYMBOLS
    assert len(set(mod.UNIVERSE_SYMBOLS)) == 98


def test_bounded_grid_is_sixteen_declared_combos():
    combos = list(mod.iter_grid())
    assert len(combos) == 2 * 2 * 1 * 2 * 2 == 16
    assert {row["feature"] for row in combos} == {"turnover_21", "turnover_252"}
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {5, 10}
        assert row["vol_target"] in {0.10, 0.15}


def test_returns_from_closes_first_row_nan():
    closes, _, _, _ = _synthetic_data(n_days=10, n_names=3)
    returns = mod.returns_from_closes(closes)
    assert returns.iloc[0].isna().all()
    assert np.isfinite(returns.iloc[1:].to_numpy()).all()
    expected = closes.iloc[1] / closes.iloc[0] - 1.0
    assert np.allclose(returns.iloc[1].to_numpy(), expected.to_numpy())


def test_shares_observations_dedups_by_filed():
    facts = {
        "facts": {
            "us-gaap": {
                "CommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {"end": "2020-12-31", "filed": "2021-02-01", "val": 1000.0},
                            {"end": "2020-12-31", "filed": "2021-02-15", "val": 1000.0},
                            {"end": "2021-12-31", "filed": "2022-02-01", "val": 1100.0},
                        ]
                    }
                }
            }
        }
    }
    obs = mod.shares_observations(facts)
    assert list(obs.columns) == ["end", "filed", "shares"]
    assert len(obs) == 2  # one row per fiscal end, earliest filing kept
    assert obs.iloc[0]["shares"] == 1000.0
    assert obs.iloc[1]["shares"] == 1100.0


def test_shares_observations_falls_back_to_dei():
    facts = {
        "facts": {
            "dei": {
                "EntityCommonStockSharesOutstanding": {
                    "units": {
                        "shares": [{"end": "2021-12-31", "filed": "2022-02-01", "val": 500.0}]
                    }
                }
            }
        }
    }
    obs = mod.shares_observations(facts)
    assert len(obs) == 1
    assert obs.iloc[0]["shares"] == 500.0


def test_shares_observations_empty_when_no_share_tag():
    assert mod.shares_observations({"facts": {}}).empty


def test_build_turnover_panels_shape_and_values():
    closes, volumes, shares, calendar = _synthetic_data(n_days=800, n_names=6, seed=1)
    products = list(closes.columns)
    panels = mod.build_turnover_panels(shares, volumes, calendar)
    assert set(panels.keys()) == {"turnover_21", "turnover_252"}
    for feat in panels:
        assert panels[feat].index.equals(calendar)
        assert list(panels[feat].columns) == products
    turnover252 = panels["turnover_252"]["S0"]
    valid = turnover252.dropna()
    assert len(valid) > 0
    # Turnover is a non-negative ratio.
    assert (valid >= 0.0).all()
    # Monthly refresh -> the panel is piecewise-constant within a calendar month.
    first_ts = valid.index[0]
    same_month = valid.index[
        (valid.index.year == first_ts.year) & (valid.index.month == first_ts.month)
    ]
    assert len(same_month) >= 1
    assert turnover252.loc[same_month].nunique() == 1


def test_build_turnover_panels_is_not_all_nan_regression():
    """Guard the monthly panel must not be all-NaN (a vacuous flat strategy)."""
    closes, volumes, shares, calendar = _synthetic_data(n_days=800, n_names=6, seed=2)
    panels = mod.build_turnover_panels(shares, volumes, calendar)
    for feat in panels:
        assert panels[feat].notna().any().any()


def test_turnover_panels_respect_share_count_pit():
    """A share count is only usable from its filed date onward (no look-ahead)."""
    closes, volumes, _, calendar = _synthetic_data(n_days=800, n_names=4, seed=3)
    products = list(closes.columns)
    # One symbol with a single share observation filed late in the sample.
    late_filed = pd.Timestamp("2022-06-01")
    shares = {
        products[0]: pd.DataFrame(
            {"end": [pd.Timestamp("2022-03-31")], "filed": [late_filed], "shares": [1.0e9]}
        )
    }
    panels = mod.build_turnover_panels(shares, volumes, calendar)
    series = panels["turnover_252"][products[0]].dropna()
    # The first usable value must be at/after the filed date.
    assert len(series) > 0
    assert series.index[0] >= late_filed


def test_cross_sectional_z_winsorized_at_three():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    signal = pd.DataFrame(
        np.array([[1.0, 2.0, 3.0, 4.0, 100.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    z = mod.h187.cross_sectional_z(signal)
    assert z.abs().max().max() <= 3.0 + 1e-10


def test_turnover_signal_weights_long_low_short_high():
    """Turnover direction: long low turnover (A, B), short high turnover (D, E)."""
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    # z: A=-2.0 (low turnover), B=-1.5, C=0.0, D=1.5, E=2.0 (high turnover).
    z = pd.DataFrame(
        np.array([[-2.0, -1.5, 0.0, 1.5, 2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.h187.signal_weights(z, entry_z=1.0, exit_z=0.0, k=2, products=products)
    assert weights.iloc[0]["A"] == 0.25
    assert weights.iloc[0]["B"] == 0.25
    assert weights.iloc[0]["D"] == -0.25
    assert weights.iloc[0]["E"] == -0.25
    assert weights.iloc[0]["C"] == 0.0


def test_turnover_signal_weights_hysteresis():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    products = ["A", "B"]
    # A is low turnover (long), B is high turnover (short); both persist.
    z = pd.DataFrame(
        {
            "A": [-2.0, -0.5, -0.2, -2.0, -0.5],
            "B": [2.0, 0.5, 0.2, 2.0, 0.5],
        },
        index=calendar,
    )
    weights = mod.h187.signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    assert weights.iloc[0]["A"] == 0.5
    assert weights.iloc[0]["B"] == -0.5
    assert (weights["A"] == 0.5).all()
    assert (weights["B"] == -0.5).all()


def test_turnover_signal_weights_exit_when_z_crosses():
    calendar = pd.bdate_range("2020-01-01", periods=2)
    products = ["A", "B"]
    z = pd.DataFrame({"A": [-2.0, 0.5], "B": [2.0, -0.5]}, index=calendar)
    weights = mod.h187.signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    assert weights.iloc[0]["A"] == 0.5
    assert weights.iloc[0]["B"] == -0.5
    # A long exits when z rises to/above -exit_z; B short exits when z falls to/below.
    assert weights.iloc[1]["A"] == 0.0
    assert weights.iloc[1]["B"] == 0.0


def test_target_weights_zero_when_insufficient_active():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C"]
    signal = pd.DataFrame(
        np.array([[-2.0, -1.0, np.nan]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(7).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {
        "feature": "turnover_21",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 1,
        "vol_target": 0.10,
    }
    weights = mod.target_weights(signal, params, returns, products)
    # Only 3 active names, MIN_ACTIVE_NAMES=40, so all weights should be 0.
    assert (weights == 0.0).all().all()


def test_walk_forward_score_short_train_returns_sentinel():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C"]
    signal = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {
        "feature": "turnover_21",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 2,
        "vol_target": 0.10,
    }
    score = mod.h187.walk_forward_score(signal, params, returns, products, calendar)
    assert score == -999.0


def test_walk_forward_score_returns_finite_or_sentinel():
    calendar = pd.bdate_range("2020-01-01", periods=500)
    products = ["A", "B", "C", "D", "E"]
    signal = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {
        "feature": "turnover_21",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 2,
        "vol_target": 0.10,
    }
    train_index = calendar[:300]
    score = mod.h187.walk_forward_score(signal, params, returns, products, train_index)
    assert np.isfinite(score) or score == -999.0


def test_perturbation_sharpes_returns_four_points():
    calendar = pd.bdate_range("2020-01-01", periods=200)
    products = ["A", "B", "C", "D", "E"]
    signal = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    selected = {
        "feature": "turnover_21",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 2,
        "vol_target": 0.10,
    }
    sharpes = mod.h187.perturbation_sharpes(signal, selected, returns, products, calendar)
    assert len(sharpes) == 4
    assert all(np.isfinite(v) or np.isnan(v) for v in sharpes)


def test_train_collinearity_is_bounded():
    calendar = pd.bdate_range("2020-01-01", periods=100)
    products = ["A", "B", "C", "D", "E"]
    features = {
        "turnover_21": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "turnover_252": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    value = mod.train_collinearity(features, calendar)
    assert -1.0 <= value <= 1.0


def test_train_collinearity_detects_proportional_panels_regression():
    """turnover_21 vs turnover_252 near-identical -> Spearman ~1.0 (not 0.0)."""
    calendar = pd.bdate_range("2020-01-01", periods=60)
    products = ["A", "B", "C", "D", "E", "F"]
    rng = np.random.default_rng(11)
    base = pd.DataFrame(
        rng.uniform(-1.0, 1.0, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    features = {
        "turnover_21": base,
        "turnover_252": base * 1.0,
    }
    value = mod.train_collinearity(features, calendar)
    assert value > 0.99


def test_trailing_total_return_and_volatility_are_causal():
    calendar = pd.bdate_range("2020-01-01", periods=400)
    products = ["A", "B", "C"]
    rng = np.random.default_rng(5)
    returns = pd.DataFrame(
        rng.normal(0.0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    mom = mod.trailing_total_return(returns, 60)
    vol = mod.trailing_volatility(returns, 60)
    assert mom.iloc[:59].isna().all().all()
    assert vol.iloc[:59].isna().all().all()
    manual = (1.0 + returns["A"]).iloc[:60].prod() - 1.0
    assert mom["A"].iloc[59] == manual


def test_train_mechanism_separation_reports_bounded_spearman():
    calendar = pd.bdate_range("2020-01-01", periods=400)
    products = ["A", "B", "C", "D", "E"]
    rng = np.random.default_rng(9)
    turnover = pd.DataFrame(
        rng.uniform(0.0, 1.0, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        rng.normal(0.0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    features = {"turnover_252": turnover}
    sep = mod.train_mechanism_separation(features, None, returns, calendar)
    for value in sep.values():
        assert -1.0 <= value <= 1.0
    assert "turnover_252_vs_momentum_252" in sep
    assert "turnover_252_vs_realized_vol_252" in sep


def _latest_artifact():
    import glob

    artifacts = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_01_share_turnover_*" / "summary.json")
    )
    if not artifacts:
        import pytest

        pytest.skip("H196 artifact not yet generated")
    return max(artifacts)


def test_artifact_summary_exists_and_verdict():
    with open(_latest_artifact()) as f:
        summary = json.load(f)
    assert summary["experiment"] == "nf_20261122_01_share_turnover"
    assert summary["nf_id"] == "NF-20261122-01"
    assert summary["hypothesis"] == "H196"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["selected"]["feature"] in {"turnover_21", "turnover_252"}
    assert summary["data"]["universe_size"] == 98
    assert summary["data"]["excluded_symbols"] == ["XOM", "BKNG"]
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False


def test_artifact_grid_csv_has_sixteen_rows():
    import glob

    grids = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_01_share_turnover_*" / "grid.csv")
    )
    if not grids:
        import pytest

        pytest.skip("H196 grid artifact not yet generated")
    grid = pd.read_csv(max(grids))
    assert len(grid) == 16
    assert {"feature", "entry_z", "exit_z", "k", "vol_target", "wf_train_sharpe"} == set(
        grid.columns
    )
