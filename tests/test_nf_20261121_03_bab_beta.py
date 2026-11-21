from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261121_03", ROOT / "run_nf_20261121_03_bab_beta.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _synthetic_closes(n_days=800, n_names=6, seed=0):
    """Geometric price paths with a controllable common factor (no network).

    Returns a closes frame (business-day index, one column per name). The first
    name is a strong market-beta name; the last is a near-zero-beta name, so a
    trailing-beta panel is observable and non-degenerate.
    """
    rng = np.random.default_rng(seed)
    calendar = pd.bdate_range("2020-01-01", periods=n_days)
    market = rng.normal(0.0, 0.01, size=n_days)
    betas = np.linspace(1.8, 0.1, n_names)  # first name high-beta, last low-beta
    idio = rng.normal(0.0, 0.005, size=(n_days, n_names))
    rets = market[:, None] * betas[None, :] + idio
    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    closes = pd.DataFrame(prices, index=calendar, columns=[f"S{i}" for i in range(n_names)])
    return closes, calendar


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261121_03_bab_beta"
    assert mod.NF_ID == "NF-20261121-03"
    assert mod.HYPOTHESIS == "H193"
    assert mod.START == "2011-01-03"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.MIN_PRICE_OBSERVATIONS == 252
    assert mod.GATES == mod.h184.GATES
    assert mod.BETA_WINDOWS == [126, 252]
    assert mod.FEATURES == ["beta_126", "beta_252"]
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
    assert {row["feature"] for row in combos} == {"beta_126", "beta_252"}
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {5, 10}
        assert row["vol_target"] in {0.10, 0.15}


def test_returns_from_closes_first_row_nan():
    closes, _ = _synthetic_closes(n_days=10, n_names=3)
    returns = mod.returns_from_closes(closes)
    assert returns.iloc[0].isna().all()
    assert np.isfinite(returns.iloc[1:].to_numpy()).all()
    # Simple return check on the second row.
    expected = closes.iloc[1] / closes.iloc[0] - 1.0
    assert np.allclose(returns.iloc[1].to_numpy(), expected.to_numpy())


def test_trailing_beta_recovers_known_betas():
    closes, _ = _synthetic_closes(n_days=900, n_names=6, seed=1)
    returns = mod.returns_from_closes(closes)
    beta = mod.trailing_beta(returns, 252)
    last = beta.iloc[-1].dropna()
    # First name is high-beta (~1.8), last is low-beta (~0.1); recovery is loose
    # but the ordering must hold strongly.
    assert last["S0"] > 1.0
    assert last["S5"] < 0.5
    assert last["S0"] > last["S5"]
    # Beta must be estimated only where a full window exists.
    assert beta.iloc[:251].isna().all().all()
    assert beta.iloc[251:].notna().any().any()


def test_build_beta_panels_shape_and_values():
    closes, calendar = _synthetic_closes(n_days=800, n_names=6, seed=2)
    returns = mod.returns_from_closes(closes)
    products = list(closes.columns)
    panels = mod.build_beta_panels(returns, calendar, products)
    assert set(panels.keys()) == {"beta_126", "beta_252"}
    for feat in panels:
        assert panels[feat].index.equals(calendar)
        assert list(panels[feat].columns) == products
    # Monthly refresh -> panel is piecewise-constant within a month.
    beta126 = panels["beta_126"]["S0"]
    valid = beta126.dropna()
    assert len(valid) > 0
    # Within one calendar month the forward-filled value does not change.
    first_ts = valid.index[0]
    same_month = valid.index[
        (valid.index.year == first_ts.year) & (valid.index.month == first_ts.month)
    ]
    assert len(same_month) >= 1
    assert beta126.loc[same_month].nunique() == 1


def test_build_beta_panels_is_not_all_nan_regression():
    """Guard the monthly panel must not be all-NaN (a vacuous flat strategy)."""
    closes, calendar = _synthetic_closes(n_days=800, n_names=6, seed=3)
    returns = mod.returns_from_closes(closes)
    products = list(closes.columns)
    panels = mod.build_beta_panels(returns, calendar, products)
    for feat in panels:
        assert panels[feat].notna().any().any()


def test_cross_sectional_z_winsorized_at_three():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    signal = pd.DataFrame(
        np.array([[1.0, 2.0, 3.0, 4.0, 100.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    z = mod.cross_sectional_z(signal)
    assert z.abs().max().max() <= 3.0 + 1e-10


def test_beta_signal_weights_long_low_short_high():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    # z: A=-2.0, B=-1.5, C=0.0, D=1.5, E=2.0
    z = pd.DataFrame(
        np.array([[-2.0, -1.5, 0.0, 1.5, 2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.beta_signal_weights(z, entry_z=1.0, exit_z=0.0, k=2, products=products)
    # BAB direction: long the low beta (A, B), short the high beta (D, E).
    assert weights.iloc[0]["A"] == 0.25
    assert weights.iloc[0]["B"] == 0.25
    assert weights.iloc[0]["D"] == -0.25
    assert weights.iloc[0]["E"] == -0.25
    assert weights.iloc[0]["C"] == 0.0


def test_beta_signal_weights_hysteresis():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    products = ["A", "B"]
    z = pd.DataFrame(
        {
            "A": [-2.0, -0.5, -0.2, -2.0, -0.5],
            "B": [2.0, 0.5, 0.2, 2.0, 0.5],
        },
        index=calendar,
    )
    weights = mod.beta_signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    assert weights.iloc[0]["A"] == 0.5
    assert weights.iloc[0]["B"] == -0.5
    assert (weights["A"] == 0.5).all()
    assert (weights["B"] == -0.5).all()


def test_beta_signal_weights_exit_when_z_crosses():
    calendar = pd.bdate_range("2020-01-01", periods=2)
    products = ["A", "B"]
    z = pd.DataFrame({"A": [-2.0, 0.5], "B": [2.0, -0.5]}, index=calendar)
    weights = mod.beta_signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    assert weights.iloc[0]["A"] == 0.5
    assert weights.iloc[0]["B"] == -0.5
    # A long exits when z rises to/above exit_z; B short exits when z falls to/below.
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
        "feature": "beta_126",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 1,
        "vol_target": 0.10,
    }
    weights = mod.target_weights(signal, params, returns, products)
    # Only 2 active names, MIN_ACTIVE_NAMES=40, so all weights should be 0.
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
        "feature": "beta_126",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 2,
        "vol_target": 0.10,
    }
    score = mod.walk_forward_score(signal, params, returns, products, calendar)
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
        "feature": "beta_126",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 2,
        "vol_target": 0.10,
    }
    train_index = calendar[:300]
    score = mod.walk_forward_score(signal, params, returns, products, train_index)
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
        "feature": "beta_126",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 2,
        "vol_target": 0.10,
    }
    sharpes = mod.perturbation_sharpes(signal, selected, returns, products, calendar)
    assert len(sharpes) == 4
    assert all(np.isfinite(v) or np.isnan(v) for v in sharpes)


def test_train_collinearity_is_bounded():
    calendar = pd.bdate_range("2020-01-01", periods=100)
    products = ["A", "B", "C", "D", "E"]
    features = {
        "beta_126": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "beta_252": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    value = mod.train_collinearity(features, calendar)
    assert -1.0 <= value <= 1.0


def test_train_collinearity_detects_proportional_panels_regression():
    """beta_126 vs beta_252 are near-identical -> Spearman ~1.0.

    A proportional panel must yield Spearman ~1.0, not the 0.0 produced by an
    all-NaN panel (e.g. a beta window that never fills -> no usable pairs).
    """
    calendar = pd.bdate_range("2020-01-01", periods=60)
    products = ["A", "B", "C", "D", "E", "F"]
    rng = np.random.default_rng(11)
    base = pd.DataFrame(
        rng.uniform(0.2, 2.0, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    features = {
        "beta_126": base,
        "beta_252": base * 1.0,  # identical panels -> perfectly monotone
    }
    value = mod.train_collinearity(features, calendar)
    assert value > 0.99


def _latest_artifact():
    import glob

    artifacts = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261121_03_bab_beta_*" / "summary.json")
    )
    if not artifacts:
        import pytest

        pytest.skip("H193 artifact not yet generated")
    return max(artifacts)


def test_artifact_summary_exists_and_verdict():
    with open(_latest_artifact()) as f:
        summary = json.load(f)
    assert summary["experiment"] == "nf_20261121_03_bab_beta"
    assert summary["nf_id"] == "NF-20261121-03"
    assert summary["hypothesis"] == "H193"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["selected"]["feature"] in {"beta_126", "beta_252"}
    assert summary["data"]["universe_size"] == 98
    assert summary["data"]["excluded_symbols"] == ["XOM", "BKNG"]
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False


def test_artifact_grid_csv_has_sixteen_rows():
    import glob

    grids = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261121_03_bab_beta_*" / "grid.csv")
    )
    if not grids:
        import pytest

        pytest.skip("H193 grid artifact not yet generated")
    grid = pd.read_csv(max(grids))
    assert len(grid) == 16
    assert {"feature", "entry_z", "exit_z", "k", "vol_target", "wf_train_sharpe"} == set(
        grid.columns
    )
