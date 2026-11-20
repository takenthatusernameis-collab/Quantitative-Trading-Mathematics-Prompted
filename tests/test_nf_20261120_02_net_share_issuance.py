from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261120_02", ROOT / "run_nf_20261120_02_net_share_issuance.py"
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


def _share_bundle():
    """Synthetic three-year 10-K bundle (no network, no cache).

    Shares outstanding grow each year (net issuance) and share repurchases are
    positive (buybacks). Each tag carries a *distinct* ``filed`` date so the
    latest-contributing-fact rule is observable, and the balance-sheet dates are
    deliberately later than the share/buyback dates.
    """
    shares = [
        _fact(None, "2022-12-31", 1000.0, "2023-02-20"),
        _fact(None, "2023-12-31", 1100.0, "2024-02-15"),
        _fact(None, "2024-12-31", 1210.0, "2025-02-14"),
    ]
    buybacks = [
        _fact("2022-01-01", "2022-12-31", 50.0, "2023-02-20"),
        _fact("2023-01-01", "2023-12-31", 60.0, "2024-02-15"),
        _fact("2024-01-01", "2024-12-31", 70.0, "2025-02-14"),
    ]
    assets = [
        _fact(None, "2022-12-31", 10000.0, "2023-02-25"),
        _fact(None, "2023-12-31", 11000.0, "2024-02-25"),
        _fact(None, "2024-12-31", 12100.0, "2025-02-14"),
    ]
    return {
        "facts": {
            "us-gaap": {
                "CommonStockSharesOutstanding": {"units": {"shares": shares}},
                "PaymentsForRepurchaseOfCommonStock": {"units": {"USD": buybacks}},
                "Assets": {"units": {"USD": assets}},
            }
        }
    }


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261120_02_net_share_issuance"
    assert mod.NF_ID == "NF-20261120-02"
    assert mod.HYPOTHESIS == "H188"
    assert mod.START == "2011-01-03"
    assert mod.END == "2026-11-17"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.GATES == mod.h184.GATES
    assert mod.FEATURES == ["net_issuance", "buyback_intensity"]
    assert mod.VOL_LOOKBACK == 60
    assert mod.DAYS_PER_YEAR == 252


def test_universe_is_sp100_minus_exclusions():
    assert len(mod.UNIVERSE_SYMBOLS) == 91
    excluded = {"ACN", "CMCSA", "MA", "META", "RTX", "SNDK", "UPS", "V", "XOM"}
    for sym in excluded:
        assert sym not in mod.UNIVERSE_SYMBOLS
    # BKNG should be included (usable for share counts)
    assert "BKNG" in mod.UNIVERSE_SYMBOLS
    assert len(set(mod.UNIVERSE_SYMBOLS)) == 91


def test_bounded_grid_is_sixteen_declared_combos():
    combos = list(mod.iter_grid())
    assert len(combos) == 2 * 2 * 1 * 2 * 2 == 16
    assert {row["feature"] for row in combos} == {"net_issuance", "buyback_intensity"}
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {10, 20}
        assert row["vol_target"] in {0.10, 0.15}


def test_annual_share_observations_compute_net_issuance_and_buyback():
    obs = mod.annual_share_observations(_share_bundle())
    assert not obs.empty
    expected_cols = {
        "end",
        "filed",
        "shares",
        "buybacks",
        "assets",
        "net_issuance",
        "buyback_intensity",
    }
    assert set(obs.columns) == expected_cols
    assert obs["net_issuance"].notna().any()
    assert obs["buyback_intensity"].notna().any()
    # Verify net_issuance formula: shares_t / shares_{t-1} - 1 where shares_{t-1} > 0
    prev_shares = obs["shares"].shift(1)
    expected_net_issuance = (obs["shares"] / prev_shares - 1.0).where(prev_shares > 0)
    expected_net_issuance.name = "net_issuance"
    pd.testing.assert_series_equal(
        obs["net_issuance"], expected_net_issuance, check_exact=False, rtol=1e-10
    )
    # Verify buyback_intensity formula: buybacks_t / assets_{t-1} where assets_{t-1} > 0
    prev_assets = obs["assets"].shift(1)
    expected_buyback = (obs["buybacks"] / prev_assets).where(prev_assets > 0)
    expected_buyback.name = "buyback_intensity"
    pd.testing.assert_series_equal(
        obs["buyback_intensity"], expected_buyback, check_exact=False, rtol=1e-10
    )


def test_filed_date_is_max_of_relevant_tags():
    obs = mod.annual_share_observations(_share_bundle())
    # Each row's ``filed`` is the latest of shares(t), shares(t-1), buybacks,
    # assets(t) and assets(t-1) acceptance dates.
    filed_by_end = dict(
        zip(obs["end"].dt.strftime("%Y-%m-%d"), obs["filed"].dt.strftime("%Y-%m-%d"))
    )
    assert filed_by_end["2022-12-31"] == "2023-02-25"
    assert filed_by_end["2023-12-31"] == "2024-02-25"
    assert filed_by_end["2024-12-31"] == "2025-02-14"


def test_build_monthly_signal_panel_shape():
    obs = mod.annual_share_observations(_share_bundle())
    calendar = pd.bdate_range(mod.START, mod.END)
    panels = mod.build_monthly_signal_panel({"AAPL": obs}, calendar)
    assert set(panels.keys()) == {"net_issuance", "buyback_intensity"}
    for feat in ["net_issuance", "buyback_intensity"]:
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


def test_signal_weights_net_issuance_short_high_long_low():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    # z: A=-2.0, B=-1.5, C=0.0, D=1.5, E=2.0
    # For net_issuance: long low (negative z), short high (positive z)
    # At entry_z=1.0: long where z <= -1.0 (A, B), short where z >= 1.0 (D, E)
    z = pd.DataFrame(
        np.array([[-2.0, -1.5, 0.0, 1.5, 2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.signal_weights(
        z, entry_z=1.0, exit_z=0.0, k=2, products=products, feature="net_issuance"
    )
    # Gross normalized to 1/4 each
    assert weights.iloc[0]["A"] == 0.25
    assert weights.iloc[0]["B"] == 0.25
    assert weights.iloc[0]["D"] == -0.25
    assert weights.iloc[0]["E"] == -0.25
    assert weights.iloc[0]["C"] == 0.0


def test_signal_weights_buyback_intensity_long_high_short_low():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    # z: A=-2.0, B=-1.5, C=0.0, D=1.5, E=2.0
    # For buyback_intensity: long high (positive z), short low (negative z)
    # At entry_z=1.0: long where z >= 1.0 (D, E), short where z <= -1.0 (A, B)
    z = pd.DataFrame(
        np.array([[-2.0, -1.5, 0.0, 1.5, 2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.signal_weights(
        z, entry_z=1.0, exit_z=0.0, k=2, products=products, feature="buyback_intensity"
    )
    # Gross normalized to 1/4 each
    assert weights.iloc[0]["D"] == 0.25
    assert weights.iloc[0]["E"] == 0.25
    assert weights.iloc[0]["A"] == -0.25
    assert weights.iloc[0]["B"] == -0.25
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
    weights = mod.signal_weights(
        z, entry_z=1.0, exit_z=0.0, k=1, products=products, feature="net_issuance"
    )
    # Day 0: A enters long, B enters short
    assert weights.iloc[0]["A"] == 0.5
    assert weights.iloc[0]["B"] == -0.5
    # Day 1: A still long (exit_z=0.0, z=-0.5 >= -0.0? -0.5 >= 0.0 is False, so stays long)
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
    params = {"feature": "net_issuance", "entry_z": 1.0, "exit_z": 0.0, "k": 1, "vol_target": 0.10}
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
    params = {"feature": "net_issuance", "entry_z": 1.0, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
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
    params = {"feature": "net_issuance", "entry_z": 1.0, "exit_z": 0.0, "k": 2, "vol_target": 0.10}
    sharpes = mod.perturbation_sharpes(signal, params, returns, products, calendar)
    assert len(sharpes) == 4
    assert all(np.isfinite(v) or np.isnan(v) for v in sharpes)


def test_train_collinearity_is_bounded():
    calendar = pd.bdate_range("2020-01-01", periods=100)
    products = ["A", "B", "C", "D", "E"]
    features = {
        "net_issuance": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "buyback_intensity": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    value = mod.train_collinearity(features, calendar)
    assert -1.0 <= value <= 1.0


def test_train_collinearity_vs_h187_returns_dict():
    calendar = pd.bdate_range("2020-01-01", periods=100)
    products = ["A", "B", "C", "D", "E"]
    features = {
        "net_issuance": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "buyback_intensity": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    h187_features = {
        "accruals": pd.DataFrame(
            np.random.default_rng(9).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "asset_growth": pd.DataFrame(
            np.random.default_rng(10).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    result = mod.train_collinearity_vs_h187(features, h187_features, calendar)
    assert isinstance(result, dict)
    assert len(result) == 4  # 2 H188 features x 2 H187 features
    for key, value in result.items():
        assert -1.0 <= value <= 1.0


def test_artifact_summary_exists_and_verdict():
    import glob

    artifacts = glob.glob(
        str(
            ROOT
            / ".experiments"
            / "nf_runs"
            / "nf_20261120_02_net_share_issuance_*"
            / "summary.json"
        )
    )
    # Artifact may not exist yet if experiment hasn't run; skip if not found
    if not artifacts:
        import pytest

        pytest.skip("H188 artifact not yet generated")
    latest = max(artifacts)
    import json

    with open(latest) as f:
        summary = json.load(f)
    assert summary["experiment"] == "nf_20261120_02_net_share_issuance"
    assert summary["nf_id"] == "NF-20261120-02"
    assert summary["hypothesis"] == "H188"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["selected"]["feature"] in {"net_issuance", "buyback_intensity"}
    assert summary["data"]["universe_size"] == 91
    assert summary["data"]["excluded_symbols"] == [
        "ACN",
        "CMCSA",
        "MA",
        "META",
        "RTX",
        "SNDK",
        "UPS",
        "V",
        "XOM",
    ]
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False
