from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261121_01", ROOT / "run_nf_20261121_01_equity_value.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _usd(end, value, filed, *, form="10-K"):
    return {"end": end, "val": value, "filed": filed, "form": form}


def _share(end, value, filed):
    return {"end": end, "val": value, "filed": filed}


def _value_bundle(*, equity_tag="StockholdersEquity", shares_tag="CommonStockSharesOutstanding"):
    """Synthetic three-year 10-K valuation bundle (no network, no cache).

    Equity, operating cash flow and the share count are reported on the same
    fiscal ``end``.  Each tag carries a *distinct* ``filed`` date so the
    latest-contributing-fact rule is observable.
    """
    equity = [
        _usd("2022-12-31", 1000.0, "2023-02-20"),
        _usd("2023-12-31", 1100.0, "2024-02-15"),
        _usd("2024-12-31", 1210.0, "2025-02-14"),
    ]
    cfo = [
        _usd("2022-12-31", 200.0, "2023-02-22"),
        _usd("2023-12-31", 220.0, "2024-02-20"),
        _usd("2024-12-31", 240.0, "2025-02-20"),
    ]
    shares = [
        _share("2022-12-31", 100.0, "2023-02-25"),
        _share("2023-12-31", 110.0, "2024-02-25"),
        _share("2024-12-31", 121.0, "2025-02-25"),
    ]
    return {
        "facts": {
            "us-gaap": {
                equity_tag: {"units": {"USD": equity}},
                "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": cfo}},
                shares_tag: {"units": {"shares": shares}},
            }
        }
    }


def _single_year_obs():
    """One fiscal-year valuation row (filed 2023-02-25) for panel tests."""
    bundle = {
        "facts": {
            "us-gaap": {
                "StockholdersEquity": {
                    "units": {"USD": [_usd("2022-12-31", 1000.0, "2023-02-20")]}
                },
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {"USD": [_usd("2022-12-31", 200.0, "2023-02-22")]}
                },
                "CommonStockSharesOutstanding": {
                    "units": {"shares": [_share("2022-12-31", 100.0, "2023-02-25")]}
                },
            }
        }
    }
    return mod.value_observations(bundle)


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261121_01_equity_value"
    assert mod.NF_ID == "NF-20261121-01"
    assert mod.HYPOTHESIS == "H191"
    assert mod.START == "2011-01-03"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.GATES == mod.h184.GATES
    assert mod.FEATURES == ["book_to_price", "cash_flow_yield"]
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
    assert {row["feature"] for row in combos} == {"book_to_price", "cash_flow_yield"}
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {10, 20}
        assert row["vol_target"] in {0.10, 0.15}


def test_value_observations_computes_columns_and_filed():
    obs = mod.value_observations(_value_bundle())
    assert not obs.empty
    expected_cols = {"end", "filed", "equity", "cfo", "shares"}
    assert set(obs.columns) == expected_cols
    assert obs["equity"].notna().any()
    assert obs["cfo"].notna().any()
    assert obs["shares"].notna().any()
    # ``filed`` is the latest of the three contributing acceptance dates.
    filed_by_end = dict(
        zip(obs["end"].dt.strftime("%Y-%m-%d"), obs["filed"].dt.strftime("%Y-%m-%d"))
    )
    assert filed_by_end["2022-12-31"] == "2023-02-25"
    assert filed_by_end["2023-12-31"] == "2024-02-25"
    assert filed_by_end["2024-12-31"] == "2025-02-25"


def test_value_observations_prefers_primary_equity_tag():
    bundle = _value_bundle()
    fallback = dict(bundle["facts"]["us-gaap"])
    fallback["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"] = {
        "units": {"USD": [_usd("2022-12-31", 9.0, "2023-02-20")]}
    }
    obs = mod.value_observations({"facts": {"us-gaap": fallback}})
    # The first tag with rows wins, so equity must come from StockholdersEquity.
    assert obs["equity"].iloc[0] == 1000.0


def test_value_observations_falls_back_when_primary_equity_absent():
    bundle = _value_bundle(
        equity_tag="StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"
    )
    obs = mod.value_observations(bundle)
    assert not obs.empty
    assert obs["equity"].notna().any()


def test_value_observations_empty_when_cfo_missing():
    bundle = _value_bundle()
    facts = bundle["facts"]["us-gaap"]
    del facts["NetCashProvidedByUsedInOperatingActivities"]
    obs = mod.value_observations({"facts": {"us-gaap": facts}})
    assert obs.empty
    assert list(obs.columns) == ["end", "filed", "equity", "cfo", "shares"]


def test_value_observations_ignores_non_10k_filings():
    bundle = _value_bundle()
    bundle["facts"]["us-gaap"]["StockholdersEquity"]["units"]["USD"] = [
        _usd("2022-12-31", 1000.0, "2023-02-20", form="10-Q")
    ]
    obs = mod.value_observations(bundle)
    assert obs.empty


def test_share_count_falls_back_to_weighted_average_tag():
    bundle = _value_bundle(shares_tag="WeightedAverageNumberOfSharesOutstandingBasic")
    obs = mod.value_observations(bundle)
    assert not obs.empty
    assert obs["shares"].notna().any()


def test_build_value_panel_shape_and_values():
    obs = _single_year_obs()
    calendar = pd.bdate_range("2023-01-01", "2023-12-31")
    closes = pd.DataFrame({"AAPL": 10.0}, index=calendar)
    panels = mod.build_value_panel({"AAPL": obs}, closes, calendar)
    assert set(panels.keys()) == {"book_to_price", "cash_flow_yield"}
    for feat in ("book_to_price", "cash_flow_yield"):
        assert panels[feat].index.equals(calendar)
        assert "AAPL" in panels[feat].columns
    bp = panels["book_to_price"]["AAPL"]
    cfy = panels["cash_flow_yield"]["AAPL"]
    # First usable refresh is the first business day after the 2023-02-25 filing.
    first_valid = bp.first_valid_index()
    assert first_valid is not None and first_valid >= pd.Timestamp("2023-03-01")
    # market cap = 100 shares * 10.0 close = 1000; equity 1000 -> B/P 1.0; CFO 200 -> 0.2.
    assert bp.loc[first_valid] == 1.0
    assert cfy.loc[first_valid] == 0.2


def test_build_value_panel_is_not_all_nan_regression():
    """Guard the Cycle 245 fix: the dict-of-series panel must not be transposed.

    Transposing would put symbols on the index and every ``reindex(calendar)``
    would match nothing, producing an all-NaN panel and a vacuous flat strategy.
    """
    obs = _single_year_obs()
    calendar = pd.bdate_range("2023-01-01", "2023-12-31")
    closes = pd.DataFrame({"AAPL": 10.0}, index=calendar)
    panels = mod.build_value_panel({"AAPL": obs}, closes, calendar)
    assert panels["book_to_price"]["AAPL"].notna().any()
    assert panels["cash_flow_yield"]["AAPL"].notna().any()


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


def test_value_signal_weights_long_high_short_low():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    # z: A=-2.0, B=-1.5, C=0.0, D=1.5, E=2.0
    z = pd.DataFrame(
        np.array([[-2.0, -1.5, 0.0, 1.5, 2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.value_signal_weights(z, entry_z=1.0, exit_z=0.0, k=2, products=products)
    # Value direction: long the high book-to-price (D, E), short the low (A, B).
    assert weights.iloc[0]["D"] == 0.25
    assert weights.iloc[0]["E"] == 0.25
    assert weights.iloc[0]["A"] == -0.25
    assert weights.iloc[0]["B"] == -0.25
    assert weights.iloc[0]["C"] == 0.0


def test_value_signal_weights_hysteresis():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    products = ["A", "B"]
    z = pd.DataFrame(
        {
            "A": [-2.0, -0.5, -0.2, -2.0, -0.5],
            "B": [2.0, 0.5, 0.2, 2.0, 0.5],
        },
        index=calendar,
    )
    weights = mod.value_signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    # Day 0: B (z=2) enters long, A (z=-2) enters short.
    assert weights.iloc[0]["B"] == 0.5
    assert weights.iloc[0]["A"] == -0.5
    # A stays short while z < exit_z(0); B stays long while z > exit_z(0).
    assert (weights["A"] == -0.5).all()
    assert (weights["B"] == 0.5).all()


def test_value_signal_weights_exit_when_z_crosses():
    calendar = pd.bdate_range("2020-01-01", periods=2)
    products = ["A", "B"]
    z = pd.DataFrame(
        {"A": [-2.0, 0.5], "B": [2.0, -0.5]},
        index=calendar,
    )
    weights = mod.value_signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    assert weights.iloc[0]["A"] == -0.5
    assert weights.iloc[0]["B"] == 0.5
    # A short exits when z rises to/above exit_z; B long exits when z falls to/below.
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
        "feature": "book_to_price",
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
        "feature": "book_to_price",
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
        "feature": "book_to_price",
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
        "feature": "book_to_price",
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
        "book_to_price": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "cash_flow_yield": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    value = mod.train_collinearity(features, calendar)
    assert -1.0 <= value <= 1.0


def _latest_artifact():
    import glob

    artifacts = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261121_01_equity_value_*" / "summary.json")
    )
    if not artifacts:
        import pytest

        pytest.skip("H191 artifact not yet generated")
    return max(artifacts)


def test_artifact_summary_exists_and_verdict():
    with open(_latest_artifact()) as f:
        summary = json.load(f)
    assert summary["experiment"] == "nf_20261121_01_equity_value"
    assert summary["nf_id"] == "NF-20261121-01"
    assert summary["hypothesis"] == "H191"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["selected"]["feature"] in {"book_to_price", "cash_flow_yield"}
    assert summary["data"]["universe_size"] == 98
    assert summary["data"]["excluded_symbols"] == ["XOM", "BKNG"]
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False


def test_artifact_grid_csv_has_sixteen_rows():
    import glob

    grids = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261121_01_equity_value_*" / "grid.csv")
    )
    if not grids:
        import pytest

        pytest.skip("H191 grid artifact not yet generated")
    grid = pd.read_csv(max(grids))
    assert len(grid) == 16
    assert {"feature", "entry_z", "exit_z", "k", "vol_target", "wf_train_sharpe"} == set(
        grid.columns
    )
