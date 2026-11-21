from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261121_05", ROOT / "run_nf_20261121_05_price_delay.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _synthetic_closes(n_days=900, n_names=6, seed=0):
    """Geometric price paths with a controllable delay structure (no network).

    The first ``n_names - 1`` names respond to the market only contemporaneously
    (low delay); the last name responds only with a ``DELAY_LAGS``-day lag (high
    delay). The contemporaneous names dominate the equal-weight market proxy, so
    the lagged name's delay is measured against a proxy that is mostly its
    contemporaneous market factor -- exactly the Hou-Moskowitz setup. This yields
    a trailing-delay panel that is observable, non-degenerate, and ordered as
    ``delay(S0) < delay(S5)``.
    """
    rng = np.random.default_rng(seed)
    calendar = pd.bdate_range("2020-01-01", periods=n_days)
    market = rng.normal(0.0, 0.01, size=n_days)
    market_lag = np.concatenate([np.zeros(mod.DELAY_LAGS), market[: -mod.DELAY_LAGS]])

    idio = rng.normal(0.0, 0.004, size=(n_days, n_names))
    rets = np.zeros((n_days, n_names))
    for j in range(n_names):
        if j == n_names - 1:
            rets[:, j] = market_lag + idio[:, j]  # pure lagged response (high delay)
        else:
            rets[:, j] = market + idio[:, j]  # contemporaneous response (low delay)

    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    closes = pd.DataFrame(prices, index=calendar, columns=[f"S{i}" for i in range(n_names)])
    return closes, calendar


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261121_05_price_delay"
    assert mod.NF_ID == "NF-20261121-05"
    assert mod.HYPOTHESIS == "H195"
    assert mod.START == "2011-01-03"
    assert mod.END == "2026-11-21"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.MIN_PRICE_OBSERVATIONS == 252
    assert mod.GATES == mod.h184.GATES
    assert mod.DELAY_WINDOWS == [126, 252]
    assert mod.FEATURES == ["delay_126", "delay_252"]
    assert mod.DELAY_LAGS == 5
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
    assert {row["feature"] for row in combos} == {"delay_126", "delay_252"}
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


def test_trailing_delay_produces_values():
    closes, _ = _synthetic_closes(n_days=900, n_names=6, seed=1)
    returns = mod.returns_from_closes(closes)
    delay = mod.trailing_delay(returns, 252)
    last = delay.iloc[-1].dropna()
    # First name responds contemporaneously (low delay); last responds with a
    # lag (high delay).
    assert last["S0"] < last["S5"]
    # Delay is estimated only where the full design window exists.
    warmup = 252 - 1 + mod.DELAY_LAGS
    assert delay.iloc[:warmup].isna().all().all()
    assert delay.iloc[warmup:].notna().any().any()
    # Delay is bounded in [0, 1].
    assert delay.min().min() >= 0.0
    assert delay.max().max() <= 1.0


def test_build_delay_panels_shape_and_values():
    closes, calendar = _synthetic_closes(n_days=800, n_names=6, seed=2)
    returns = mod.returns_from_closes(closes)
    products = list(closes.columns)
    panels = mod.build_delay_panels(returns, calendar, products)
    assert set(panels.keys()) == {"delay_126", "delay_252"}
    for feat in panels:
        assert panels[feat].index.equals(calendar)
        assert list(panels[feat].columns) == products
    # Monthly refresh -> panel is piecewise-constant within a month.
    delay252 = panels["delay_252"]["S5"]
    valid = delay252.dropna()
    assert len(valid) > 0
    # Within one calendar month the forward-filled value does not change.
    first_ts = valid.index[0]
    same_month = valid.index[
        (valid.index.year == first_ts.year) & (valid.index.month == first_ts.month)
    ]
    assert len(same_month) >= 1
    assert delay252.loc[same_month].nunique() == 1


def test_build_delay_panels_is_not_all_nan_regression():
    """Guard the monthly panel must not be all-NaN (a vacuous flat strategy)."""
    closes, calendar = _synthetic_closes(n_days=800, n_names=6, seed=3)
    returns = mod.returns_from_closes(closes)
    products = list(closes.columns)
    panels = mod.build_delay_panels(returns, calendar, products)
    for feat in panels:
        assert panels[feat].notna().any().any()


def test_trailing_delay_handles_per_stock_gaps():
    """A gapped name must not erase the whole day's delay (all-or-nothing guard).

    Reproduces the bug where ``if np.isnan(returns_window).any(): continue``
    discarded an entire day whenever *any* name had a missing observation,
    leaving ~95% of the real 98-name panel NaN and producing a vacuous flat
    strategy (zero positions, zero in-sample Sharpe). Here one name (S5) has a
    long NaN gap; the complete names (S0..S4) must still be estimated on days
    where S5 is incomplete, and S5 itself must fill once it accumulates enough
    valid rows.
    """
    closes, _ = _synthetic_closes(n_days=900, n_names=6, seed=4)
    returns = mod.returns_from_closes(closes)
    s5 = returns.columns.get_loc("S5")
    returns.iloc[:200, s5] = np.nan  # S5 not yet public for the first 200 rows
    window = 252
    delay = mod.trailing_delay(returns, window)
    min_valid = max(mod.DELAY_LAGS + 5, window // 2)

    # Day 300: window rows 49..300 straddle S5's NaN gap (49..199), leaving S5
    # only ~101 valid rows < min_valid -> S5 is NaN, but S0..S4 are complete in
    # the window and MUST still be estimated (the old code zeroed all of them).
    day = delay.index[300]
    assert pd.isna(delay.loc[day, "S5"])
    assert delay.loc[day, ["S0", "S1", "S2", "S3", "S4"]].notna().all()
    assert delay.loc[day, ["S0", "S1", "S2", "S3", "S4"]].between(0.0, 1.0).all()

    # Day 400: S5 now has ~201 valid rows >= min_valid -> it is estimated too.
    day2 = delay.index[400]
    assert pd.notna(delay.loc[day2, "S5"])
    assert np.isfinite(delay.loc[day2, "S5"])

    # Warm-up (complete names NaN until row window-1+n_lags) and bounds hold.
    assert delay.iloc[: window - 1 + mod.DELAY_LAGS].isna().all().all()
    assert delay.min().min() >= 0.0
    assert delay.max().max() <= 1.0


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


def test_delay_signal_weights_long_high_short_low():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    # z: A=-2.0, B=-1.5, C=0.0, D=1.5, E=2.0
    z = pd.DataFrame(
        np.array([[-2.0, -1.5, 0.0, 1.5, 2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.delay_signal_weights(z, entry_z=1.0, exit_z=0.0, k=2, products=products)
    # Delay direction (Hou & Moskowitz): long high delay (D, E), short low delay (A, B).
    assert weights.iloc[0]["D"] == 0.25
    assert weights.iloc[0]["E"] == 0.25
    assert weights.iloc[0]["A"] == -0.25
    assert weights.iloc[0]["B"] == -0.25
    assert weights.iloc[0]["C"] == 0.0


def test_delay_signal_weights_hysteresis():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    products = ["A", "B"]
    z = pd.DataFrame(
        {
            "A": [-2.0, -0.5, -0.2, -2.0, -0.5],
            "B": [2.0, 0.5, 0.2, 2.0, 0.5],
        },
        index=calendar,
    )
    weights = mod.delay_signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    assert weights.iloc[0]["B"] == 0.5
    assert weights.iloc[0]["A"] == -0.5
    assert (weights["B"] == 0.5).all()
    assert (weights["A"] == -0.5).all()


def test_delay_signal_weights_exit_when_z_crosses():
    calendar = pd.bdate_range("2020-01-01", periods=2)
    products = ["A", "B"]
    z = pd.DataFrame({"A": [-2.0, 0.5], "B": [2.0, -0.5]}, index=calendar)
    weights = mod.delay_signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    assert weights.iloc[0]["B"] == 0.5
    assert weights.iloc[0]["A"] == -0.5
    # B long exits when z falls to/below exit_z; A short exits when z rises to/above.
    assert weights.iloc[1]["B"] == 0.0
    assert weights.iloc[1]["A"] == 0.0


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
        "feature": "delay_126",
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
        "feature": "delay_126",
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
        "feature": "delay_126",
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
        "feature": "delay_126",
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
        "delay_126": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "delay_252": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    value = mod.train_collinearity(features, calendar)
    assert -1.0 <= value <= 1.0


def test_train_collinearity_detects_proportional_panels_regression():
    """delay_126 vs delay_252 are near-identical -> Spearman ~1.0.

    A proportional panel must yield Spearman ~1.0, not the 0.0 produced by an
    all-NaN panel (e.g. a delay window that never fills -> no usable pairs).
    """
    calendar = pd.bdate_range("2020-01-01", periods=60)
    products = ["A", "B", "C", "D", "E", "F"]
    rng = np.random.default_rng(11)
    base = pd.DataFrame(
        rng.uniform(-1.0, 1.0, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    features = {
        "delay_126": base,
        "delay_252": base * 1.0,  # identical panels -> perfectly monotone
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
    # Warmup rows are NaN (need a full window).
    assert mom.iloc[:59].isna().all().all()
    assert vol.iloc[:59].isna().all().all()
    # The trailing total return equals the compounded window return.
    manual = (1.0 + returns["A"]).iloc[:60].prod() - 1.0
    assert mom["A"].iloc[59] == manual


def test_train_mechanism_separation_reports_bounded_spearman():
    calendar = pd.bdate_range("2020-01-01", periods=400)
    products = ["A", "B", "C", "D", "E"]
    rng = np.random.default_rng(9)
    delay = pd.DataFrame(
        rng.uniform(0.0, 1.0, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        rng.normal(0.0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    features = {"delay_252": delay}
    sep = mod.train_mechanism_separation(features, None, returns, calendar)
    for value in sep.values():
        assert -1.0 <= value <= 1.0
    assert "delay_252_vs_momentum_252" in sep
    assert "delay_252_vs_realized_vol_252" in sep


def _latest_artifact():
    import glob

    artifacts = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261121_05_price_delay_*" / "summary.json")
    )
    if not artifacts:
        import pytest

        pytest.skip("H195 artifact not yet generated")
    return max(artifacts)


def test_artifact_summary_exists_and_verdict():
    with open(_latest_artifact()) as f:
        summary = json.load(f)
    assert summary["experiment"] == "nf_20261121_05_price_delay"
    assert summary["nf_id"] == "NF-20261121-05"
    assert summary["hypothesis"] == "H195"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["selected"]["feature"] in {"delay_126", "delay_252"}
    assert summary["data"]["universe_size"] == 98
    assert summary["data"]["excluded_symbols"] == ["XOM", "BKNG"]
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False


def test_artifact_grid_csv_has_sixteen_rows():
    import glob

    grids = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261121_05_price_delay_*" / "grid.csv")
    )
    if not grids:
        import pytest

        pytest.skip("H195 grid artifact not yet generated")
    grid = pd.read_csv(max(grids))
    assert len(grid) == 16
    assert {"feature", "entry_z", "exit_z", "k", "vol_target", "wf_train_sharpe"} == set(
        grid.columns
    )
