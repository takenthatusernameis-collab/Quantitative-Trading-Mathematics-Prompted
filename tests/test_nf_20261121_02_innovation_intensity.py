from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261121_02", ROOT / "run_nf_20261121_02_innovation_intensity.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _dur(end, value, filed, *, form="10-K", start=None):
    """A ~1-year us-gaap duration fact (R&D / revenue)."""
    end_ts = pd.Timestamp(end)
    start_ts = pd.Timestamp(start) if start is not None else end_ts - pd.Timedelta(days=364)
    return {
        "start": start_ts.strftime("%Y-%m-%d"),
        "end": end,
        "val": value,
        "filed": filed,
        "form": form,
    }


def _instant(end, value, filed, *, form="10-K"):
    """A us-gaap instant fact (balance-sheet, e.g. Assets): no duration start."""
    return {"end": end, "val": value, "filed": filed, "form": form}


def _rd_bundle(*, rd_tag="ResearchAndDevelopmentExpense", revenue_tag="Revenues"):
    """Synthetic three-year 10-K innovation bundle (no network, no cache).

    R&D and revenue are duration facts on the same fiscal ``end``; assets is an
    instant fact.  Each tag carries a *distinct* ``filed`` date so the
    latest-contributing-fact rule is observable.
    """
    rd = [
        _dur("2022-12-31", 100.0, "2023-02-20"),
        _dur("2023-12-31", 120.0, "2024-02-15"),
        _dur("2024-12-31", 140.0, "2025-02-14"),
    ]
    revenue = [
        _dur("2022-12-31", 1000.0, "2023-02-22"),
        _dur("2023-12-31", 1100.0, "2024-02-20"),
        _dur("2024-12-31", 1200.0, "2025-02-20"),
    ]
    assets = [
        _instant("2022-12-31", 5000.0, "2023-02-25"),
        _instant("2023-12-31", 5500.0, "2024-02-25"),
        _instant("2024-12-31", 6000.0, "2025-02-25"),
    ]
    return {
        "facts": {
            "us-gaap": {
                rd_tag: {"units": {"USD": rd}},
                revenue_tag: {"units": {"USD": revenue}},
                "Assets": {"units": {"USD": assets}},
            }
        }
    }


def _single_year_obs():
    """One fiscal-year innovation row (filed 2023-02-25) for panel tests."""
    bundle = {
        "facts": {
            "us-gaap": {
                "ResearchAndDevelopmentExpense": {
                    "units": {"USD": [_dur("2022-12-31", 100.0, "2023-02-20")]}
                },
                "Revenues": {"units": {"USD": [_dur("2022-12-31", 1000.0, "2023-02-22")]}},
                "Assets": {"units": {"USD": [_instant("2022-12-31", 5000.0, "2023-02-25")]}},
            }
        }
    }
    return mod.innovation_observations(bundle)


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261121_02_innovation_intensity"
    assert mod.NF_ID == "NF-20261121-02"
    assert mod.HYPOTHESIS == "H192"
    assert mod.START == "2011-01-03"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.MIN_OBSERVATIONS == 2
    assert mod.GATES == mod.h184.GATES
    assert mod.FEATURES == ["rd_intensity", "rd_to_assets"]
    assert mod.RD_TAG == "ResearchAndDevelopmentExpense"
    assert mod.REVENUE_TAGS[0] == "Revenues"
    assert mod.ASSETS_TAG == "Assets"
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
    assert {row["feature"] for row in combos} == {"rd_intensity", "rd_to_assets"}
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {5, 10}
        assert row["vol_target"] in {0.10, 0.15}


def test_innovation_observations_computes_columns_and_filed():
    obs = mod.innovation_observations(_rd_bundle())
    assert not obs.empty
    assert set(obs.columns) == {
        "end",
        "filed",
        "rd",
        "revenue",
        "assets",
        "rd_intensity",
        "rd_to_assets",
    }
    assert obs["rd_intensity"].notna().any()
    assert obs["rd_to_assets"].notna().any()
    # ``filed`` is the latest of the three contributing acceptance dates.
    filed_by_end = dict(
        zip(obs["end"].dt.strftime("%Y-%m-%d"), obs["filed"].dt.strftime("%Y-%m-%d"))
    )
    assert filed_by_end["2022-12-31"] == "2023-02-25"
    assert filed_by_end["2023-12-31"] == "2024-02-25"
    assert filed_by_end["2024-12-31"] == "2025-02-25"


def test_innovation_observations_intensity_values():
    obs = mod.innovation_observations(_rd_bundle())
    row = obs.iloc[0]
    # R&D 100 / revenue 1000 = 0.10; R&D 100 / assets 5000 = 0.02.
    assert row["rd_intensity"] == 0.10
    assert row["rd_to_assets"] == 0.02


def test_innovation_observations_revenue_fallback_tag():
    bundle = _rd_bundle(revenue_tag="RevenueFromContractWithCustomerExcludingAssessedTax")
    obs = mod.innovation_observations(bundle)
    assert not obs.empty
    assert obs["revenue"].notna().any()


def test_innovation_observations_empty_when_rd_missing():
    bundle = _rd_bundle()
    del bundle["facts"]["us-gaap"]["ResearchAndDevelopmentExpense"]
    obs = mod.innovation_observations(bundle)
    assert obs.empty
    assert list(obs.columns) == [
        "end",
        "filed",
        "rd",
        "revenue",
        "assets",
        "rd_intensity",
        "rd_to_assets",
    ]


def test_innovation_observations_empty_when_revenue_missing():
    bundle = _rd_bundle()
    del bundle["facts"]["us-gaap"]["Revenues"]
    obs = mod.innovation_observations(bundle)
    assert obs.empty


def test_innovation_observations_ignores_non_10k_filings():
    bundle = _rd_bundle()
    bundle["facts"]["us-gaap"]["ResearchAndDevelopmentExpense"]["units"]["USD"] = [
        _dur("2022-12-31", 100.0, "2023-02-20", form="10-Q")
    ]
    obs = mod.innovation_observations(bundle)
    assert obs.empty


def test_instant_usd_reads_assets_without_duration_filter():
    """Assets is an instant tag: _duration_usd empties it, _instant_usd must not."""
    facts = _rd_bundle()
    assert mod._duration_usd(facts, "Assets").empty  # no duration -> empty
    assets = mod._instant_usd(facts, "Assets")
    assert len(assets) == 3
    assert assets["val"].notna().all()


def test_build_innovation_panel_shape_and_values():
    obs = _single_year_obs()
    calendar = pd.bdate_range("2023-01-01", "2023-12-31")
    panels = mod.build_innovation_panel({"AAPL": obs}, calendar, ["AAPL"])
    assert set(panels.keys()) == {"rd_intensity", "rd_to_assets"}
    for feat in panels:
        assert panels[feat].index.equals(calendar)
        assert "AAPL" in panels[feat].columns
    rd_intensity = panels["rd_intensity"]["AAPL"]
    first_valid = rd_intensity.first_valid_index()
    assert first_valid is not None and first_valid >= pd.Timestamp("2023-03-01")
    # R&D 100 / revenue 1000 = 0.10; R&D 100 / assets 5000 = 0.02.
    assert rd_intensity.loc[first_valid] == 0.10
    assert panels["rd_to_assets"]["AAPL"].loc[first_valid] == 0.02


def test_build_innovation_panel_is_not_all_nan_regression():
    """Guard the dict-of-series panel must not be transposed.

    Transposing would put symbols on the index and every ``reindex(calendar)``
    would match nothing, producing an all-NaN panel and a vacuous flat strategy.
    """
    obs = _single_year_obs()
    calendar = pd.bdate_range("2023-01-01", "2023-12-31")
    panels = mod.build_innovation_panel({"AAPL": obs}, calendar, ["AAPL"])
    assert panels["rd_intensity"]["AAPL"].notna().any()
    assert panels["rd_to_assets"]["AAPL"].notna().any()


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


def test_innovation_signal_weights_long_high_short_low():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    # z: A=-2.0, B=-1.5, C=0.0, D=1.5, E=2.0
    z = pd.DataFrame(
        np.array([[-2.0, -1.5, 0.0, 1.5, 2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.innovation_signal_weights(z, entry_z=1.0, exit_z=0.0, k=2, products=products)
    # Innovation direction: long the high R&D intensity (D, E), short the low (A, B).
    assert weights.iloc[0]["D"] == 0.25
    assert weights.iloc[0]["E"] == 0.25
    assert weights.iloc[0]["A"] == -0.25
    assert weights.iloc[0]["B"] == -0.25
    assert weights.iloc[0]["C"] == 0.0


def test_innovation_signal_weights_hysteresis():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    products = ["A", "B"]
    z = pd.DataFrame(
        {
            "A": [-2.0, -0.5, -0.2, -2.0, -0.5],
            "B": [2.0, 0.5, 0.2, 2.0, 0.5],
        },
        index=calendar,
    )
    weights = mod.innovation_signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    assert weights.iloc[0]["B"] == 0.5
    assert weights.iloc[0]["A"] == -0.5
    assert (weights["A"] == -0.5).all()
    assert (weights["B"] == 0.5).all()


def test_innovation_signal_weights_exit_when_z_crosses():
    calendar = pd.bdate_range("2020-01-01", periods=2)
    products = ["A", "B"]
    z = pd.DataFrame({"A": [-2.0, 0.5], "B": [2.0, -0.5]}, index=calendar)
    weights = mod.innovation_signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
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
        "feature": "rd_intensity",
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
        "feature": "rd_intensity",
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
        "feature": "rd_intensity",
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
        "feature": "rd_intensity",
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
        "rd_intensity": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "rd_to_assets": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    value = mod.train_collinearity(features, calendar)
    assert -1.0 <= value <= 1.0


def test_train_collinearity_detects_proportional_panels_regression():
    """rd_intensity vs rd_to_assets are near-identical (assets ~ revenue scale).

    A proportional panel must yield Spearman ~1.0, not the 0.0 produced by the
    Cycle 246 instant-tag bug (Assets loaded via the duration filter -> all-NaN
    rd_to_assets -> no usable pairs -> 0.0).
    """
    calendar = pd.bdate_range("2020-01-01", periods=60)
    products = ["A", "B", "C", "D", "E", "F"]
    rng = np.random.default_rng(11)
    base = pd.DataFrame(
        rng.uniform(0.02, 0.20, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    features = {
        "rd_intensity": base,
        "rd_to_assets": base * 50.0,  # assets = revenue / 50 -> perfectly monotone
    }
    value = mod.train_collinearity(features, calendar)
    assert value > 0.99


def _latest_artifact():
    import glob

    artifacts = glob.glob(
        str(
            ROOT
            / ".experiments"
            / "nf_runs"
            / "nf_20261121_02_innovation_intensity_*"
            / "summary.json"
        )
    )
    if not artifacts:
        import pytest

        pytest.skip("H192 artifact not yet generated")
    return max(artifacts)


def test_artifact_summary_exists_and_verdict():
    with open(_latest_artifact()) as f:
        summary = json.load(f)
    assert summary["experiment"] == "nf_20261121_02_innovation_intensity"
    assert summary["nf_id"] == "NF-20261121-02"
    assert summary["hypothesis"] == "H192"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["selected"]["feature"] in {"rd_intensity", "rd_to_assets"}
    assert summary["data"]["universe_size"] == 57
    assert summary["data"]["excluded_symbols"] == ["XOM", "BKNG"]
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False


def test_artifact_grid_csv_has_sixteen_rows():
    import glob

    grids = glob.glob(
        str(
            ROOT / ".experiments" / "nf_runs" / "nf_20261121_02_innovation_intensity_*" / "grid.csv"
        )
    )
    if not grids:
        import pytest

        pytest.skip("H192 grid artifact not yet generated")
    grid = pd.read_csv(max(grids))
    assert len(grid) == 16
    assert {"feature", "entry_z", "exit_z", "k", "vol_target", "wf_train_sharpe"} == set(
        grid.columns
    )
