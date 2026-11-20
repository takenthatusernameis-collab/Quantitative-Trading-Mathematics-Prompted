from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261120_01", ROOT / "run_nf_20261120_01_equity_accruals.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _fact(start, end, value, filed, *, form="10-K"):
    row = {"end": end, "val": value, "filed": filed, "form": form}
    if start is not None:
        row["start"] = start
    return row


def _accruals_bundle():
    """Synthetic two-year 10-K companyfacts bundle (no network, no cache).

    FY2022 has no prior assets, so its ``accruals`` / ``asset_growth`` are NaN;
    FY2023 is fully derived. Each tag carries a *distinct* ``filed`` date so the
    latest-contributing-fact rule is observable, and the balance-sheet dates are
    deliberately later than the income-statement dates.
    """
    ni = [
        _fact("2022-01-01", "2022-12-31", 100.0, "2023-02-20"),
        _fact("2023-01-01", "2023-12-31", 120.0, "2024-02-15"),
    ]
    cfo = [
        _fact("2022-01-01", "2022-12-31", 90.0, "2023-03-01"),
        _fact("2023-01-01", "2023-12-31", 100.0, "2024-03-01"),
    ]
    assets = [
        _fact(None, "2022-12-31", 1000.0, "2023-02-25"),
        _fact(None, "2023-12-31", 1200.0, "2024-02-25"),
    ]
    return {
        "facts": {
            "us-gaap": {
                "NetIncomeLoss": {"units": {"USD": ni}},
                "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": cfo}},
                "Assets": {"units": {"USD": assets}},
            }
        }
    }


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261120_01_equity_accruals"
    assert mod.NF_ID == "NF-20261120-01"
    assert mod.HYPOTHESIS == "H187"
    assert mod.START == "2011-01-03"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.GATES == mod.h184.GATES
    assert mod.FEATURES == ["accruals", "asset_growth"]
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
    assert {row["feature"] for row in combos} == {"accruals", "asset_growth"}
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {10, 20}
        assert row["vol_target"] in {0.10, 0.15}


def test_annual_observations_compute_accruals_and_asset_growth():
    obs = mod.xbrl.annual_observations(_accruals_bundle())
    assert not obs.empty
    assert set(obs.columns) == {"end", "filed", "ni", "cfo", "assets", "accruals", "asset_growth"}
    assert obs["accruals"].notna().any()
    assert obs["asset_growth"].notna().any()
    # Verify accruals formula: (NI - CFO) / avg(Assets) where avg(Assets) > 0
    avg_assets = (obs["assets"] + obs["assets"].shift(1)) / 2.0
    expected_accruals = ((obs["ni"] - obs["cfo"]) / avg_assets).where(avg_assets > 0)
    expected_accruals.name = "accruals"
    pd.testing.assert_series_equal(
        obs["accruals"], expected_accruals, check_exact=False, rtol=1e-10
    )
    # Verify asset_growth formula: Assets_t / Assets_{t-1} - 1 where Assets_{t-1} > 0
    expected_asset_growth = (obs["assets"] / obs["assets"].shift(1) - 1.0).where(
        obs["assets"].shift(1) > 0
    )
    expected_asset_growth.name = "asset_growth"
    pd.testing.assert_series_equal(
        obs["asset_growth"], expected_asset_growth, check_exact=False, rtol=1e-10
    )


def test_filed_date_is_max_of_three_tags():
    obs = mod.xbrl.annual_observations(_accruals_bundle())
    # Each row's ``filed`` is the latest contributing tag acceptance date:
    # FY2022 -> max(2023-02-20, 2023-03-01, 2023-02-25) = 2023-03-01
    # FY2023 -> max(2024-02-15, 2024-03-01, 2024-02-25) = 2024-03-01
    filed_by_end = dict(
        zip(obs["end"].dt.strftime("%Y-%m-%d"), obs["filed"].dt.strftime("%Y-%m-%d"))
    )
    assert filed_by_end["2022-12-31"] == "2023-03-01"
    assert filed_by_end["2023-12-31"] == "2024-03-01"


def test_build_monthly_signal_panel_shape():
    obs = mod.xbrl.annual_observations(_accruals_bundle())
    calendar = pd.bdate_range(mod.START, mod.END)
    panels = mod.build_monthly_signal_panel({"AAPL": obs}, calendar)
    assert set(panels.keys()) == {"accruals", "asset_growth"}
    for feat in ["accruals", "asset_growth"]:
        assert panels[feat].index.equals(calendar)
        assert "AAPL" in panels[feat].columns
        assert panels[feat]["AAPL"].notna().any()


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


def test_signal_weights_long_low_short_high():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    z = pd.DataFrame(
        np.array([[-2.0, -1.5, 0.0, 1.5, 2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.signal_weights(z, entry_z=1.0, exit_z=0.0, k=2, products=products)
    # At entry_z=1.0, long where z <= -1.0 (A, B), short where z >= 1.0 (D, E)
    # Gross normalized to 1/4 each
    assert weights.iloc[0]["A"] == 0.25
    assert weights.iloc[0]["B"] == 0.25
    assert weights.iloc[0]["D"] == -0.25
    assert weights.iloc[0]["E"] == -0.25
    assert weights.iloc[0]["C"] == 0.0


def test_signal_weights_hysteresis():
    calendar = pd.bdate_range("2020-01-01", periods=5)
    products = ["A", "B"]
    z = pd.DataFrame(
        {
            "A": [-2.0, -0.5, -0.2, -2.0, -0.5],
            "B": [2.0, 0.5, 0.2, 2.0, 0.5],
        },
        index=calendar,
    )
    weights = mod.signal_weights(z, entry_z=1.0, exit_z=0.0, k=1, products=products)
    # Day 0: A enters long, B enters short
    assert weights.iloc[0]["A"] == 0.5
    assert weights.iloc[0]["B"] == -0.5
    # Day 1: A still long (exit_z=0.0, z=-0.5 > -0.0? No, -0.5 <= 0.0 so stays long)
    # Wait, exit_z=0.0 means long exits when z >= 0.0
    # Day 1: z_A = -0.5 >= -0.0? -0.5 >= 0.0 is False, so stays long
    assert weights.iloc[1]["A"] == 0.5
    # Day 2: z_A = -0.2 >= 0.0 is False, still long
    assert weights.iloc[2]["A"] == 0.5
    # Day 3: z_A = -2.0, still long
    assert weights.iloc[3]["A"] == 0.5
    # Day 4: z_A = -0.5, still long
    assert weights.iloc[4]["A"] == 0.5


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
    params = {"feature": "accruals", "entry_z": 1.0, "exit_z": 0.0, "k": 1, "vol_target": 0.10}
    weights = mod.target_weights(signal, params, returns, products)
    # Only 2 active names, MIN_ACTIVE_NAMES=40, so all weights should be 0
    assert (weights == 0.0).all().all()


def test_zero_rolls_frame_shape():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C"]
    rolls = mod.zero_rolls(calendar, products)
    assert rolls.shape == (len(calendar), len(products))
    assert (rolls == 0.0).all().all()


def test_walk_forward_score_returns_finite_or_neg999():
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
    params = {"feature": "accruals", "entry_z": 1.0, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
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
    params = {"feature": "accruals", "entry_z": 1.0, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
    sharpes = mod.perturbation_sharpes(signal, params, returns, products, calendar)
    assert len(sharpes) == 4
    assert all(np.isfinite(v) or np.isnan(v) for v in sharpes)


def test_train_collinearity_is_bounded():
    calendar = pd.bdate_range("2020-01-01", periods=100)
    products = ["A", "B", "C", "D", "E"]
    features = {
        "accruals": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "asset_growth": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    value = mod.train_collinearity(features, calendar)
    assert -1.0 <= value <= 1.0


def test_artifact_summary_exists_and_reject():
    import glob

    artifacts = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261120_01_equity_accruals_*" / "summary.json")
    )
    assert len(artifacts) >= 1, "No artifact directory found"
    latest = max(artifacts)
    import json

    with open(latest) as f:
        summary = json.load(f)
    assert summary["experiment"] == "nf_20261120_01_equity_accruals"
    assert summary["nf_id"] == "NF-20261120-01"
    assert summary["hypothesis"] == "H187"
    assert summary["verdict"] == "REJECT"
    assert summary["gates_passed"] == 2
    assert summary["gates_total"] == 8
    assert summary["selected"]["feature"] in {"accruals", "asset_growth"}
    assert summary["data"]["universe_size"] == 98
    assert summary["data"]["excluded_symbols"] == ["XOM", "BKNG"]
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False
