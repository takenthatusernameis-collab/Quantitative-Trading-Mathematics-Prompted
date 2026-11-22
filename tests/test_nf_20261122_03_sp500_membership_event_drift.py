"""Tests for ``run_nf_20261122_03_sp500_membership_event_drift.py`` (H198).

The runner tests the S&P 500 index-membership inclusion/deletion event drift
(long announced additions / short tradeable deletions around the effective
date).  The synthetic fixtures below exercise the event-list construction,
the event-basket weights, the walk-forward selector and the artifact schema
without network access; one test checks the committed artifact.
"""

from __future__ import annotations

import glob
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261122_03", ROOT / "run_nf_20261122_03_sp500_membership_event_drift.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _synthetic_closes(n_days=400, n_names=4, seed=0, start="2020-01-01"):
    rng = np.random.default_rng(seed)
    calendar = pd.bdate_range(start, periods=n_days)
    rets = rng.normal(0.0, 0.01, size=(n_days, n_names))
    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    columns = [f"S{i}" for i in range(n_names)]
    closes = pd.DataFrame(prices, index=calendar, columns=columns)
    return closes, calendar


def _synthetic_changes_frame():
    return pd.DataFrame(
        {
            "effective_date": pd.to_datetime(
                ["2020-09-01", "2020-10-01", "2021-01-04", "2021-02-01"]
            ),
            "added_ticker": ["S0", "S1", "S2", None],
            "added_security": ["Alpha", "Beta", "Gamma", None],
            "removed_ticker": ["S3", "DELISTED", None, "S0"],
            "removed_security": ["Delta", "Gone", None, "Alpha"],
            "reason": [
                "Market capitalization changes.",
                "Acme acquired Gone.",
                "",
                "Market capitalization changes.",
            ],
            "reason_bucket": ["market_cap", "acquisition", "other", "market_cap"],
        }
    )


# --------------------------------------------------------------------------- #
# Constants / pre-registration
# --------------------------------------------------------------------------- #


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261122_03_sp500_membership_event_drift"
    assert mod.NF_ID == "NF-20261122-03"
    assert mod.HYPOTHESIS == "H198"
    assert mod.START == "2005-01-01"
    assert mod.END == "2026-11-21"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_EVENTS == 30
    assert mod.MIN_PRICE_OBSERVATIONS == 126
    assert mod.EVENT_WINDOW_DAYS == 252
    assert mod.TRADEABLE_REMOVED_BUCKETS == ("market_cap", "spin_off", "reorganization")
    assert mod.GATES == mod.h184.GATES
    assert mod.GRID == {
        "holding_days": [21, 42, 63],
        "entry_delay": [0, 1],
        "vol_target": [0.10, 0.15],
    }
    assert mod.DAYS_PER_YEAR == 252
    assert mod.VOL_LOOKBACK == 60


def test_bounded_grid_is_twelve_declared_combos():
    combos = list(mod.iter_grid())
    assert len(combos) == 3 * 2 * 2 == 12
    assert {row["holding_days"] for row in combos} == {21, 42, 63}
    assert {row["entry_delay"] for row in combos} == {0, 1}
    assert {row["vol_target"] for row in combos} == {0.10, 0.15}


# --------------------------------------------------------------------------- #
# Event-list construction (offline)
# --------------------------------------------------------------------------- #


def test_clean_ticker_strips_whitespace_and_stray_pipes():
    assert mod._clean_ticker("  AAPL ") == "AAPL"
    assert mod._clean_ticker("JCP |") == "JCP"
    assert mod._clean_ticker(None) == ""


def test_build_event_list_keeps_added_and_tradeable_removed():
    events = mod.build_event_list(_synthetic_changes_frame(), min_year=2000, max_year=2030)
    assert len(events) == 4
    first = events[0]
    assert first["event_date"] == pd.Timestamp("2020-09-01").date()
    assert first["added_ticker"] == "S0"
    assert first["removed_ticker"] == "S3"
    assert first["removed_reason_bucket"] == "market_cap"
    # acquisition removal ('DELISTED' on 2020-10-01) is excluded from the short leg
    second = events[1]
    assert second["added_ticker"] == "S1"
    assert second["removed_ticker"] is None
    # long-only market-cap addition
    third = events[2]
    assert third["added_ticker"] == "S2"
    assert third["removed_ticker"] is None
    # short-only market-cap removal of an already-added name
    fourth = events[3]
    assert fourth["added_ticker"] is None
    assert fourth["removed_ticker"] == "S0"
    assert fourth["removed_reason_bucket"] == "market_cap"


def test_build_event_list_treats_nan_ticker_cells_as_missing():
    frame = _synthetic_changes_frame()
    frame.loc[0, "added_ticker"] = float("nan")
    events = mod.build_event_list(frame, min_year=2000, max_year=2030)
    assert events[0]["added_ticker"] is None
    assert events[0]["removed_ticker"] == "S3"


def test_build_event_list_filters_by_year_window():
    events = mod.build_event_list(_synthetic_changes_frame(), min_year=2021, max_year=2021)
    assert len(events) == 2
    assert all(event["event_date"].year == 2021 for event in events)


def test_build_event_list_drops_rows_with_no_usable_leg():
    frame = pd.DataFrame(
        {
            "effective_date": pd.to_datetime(["2020-09-01"]),
            "added_ticker": [None],
            "removed_ticker": ["DELISTED"],
            "reason": ["Acme acquired Delisted."],
            "reason_bucket": ["acquisition"],
        }
    )
    assert mod.build_event_list(frame, min_year=2000, max_year=2030) == []


def test_event_tickers_is_sorted_unique_union():
    events = mod.build_event_list(_synthetic_changes_frame(), min_year=2000, max_year=2030)
    tickers = mod.event_tickers(events)
    assert tickers == sorted(set(tickers))
    assert "S0" in tickers and "S3" in tickers
    assert "DELISTED" not in tickers


# --------------------------------------------------------------------------- #
# Price helpers (offline)
# --------------------------------------------------------------------------- #


def test_returns_from_closes_first_row_nan_and_calendar_aligned():
    closes, calendar = _synthetic_closes(n_days=20, n_names=3)
    returns = mod.returns_from_closes(closes, calendar)
    assert returns.iloc[0].isna().all()
    assert np.isfinite(returns.iloc[1:].to_numpy()).all()
    expected = closes.iloc[1] / closes.iloc[0] - 1.0
    assert np.allclose(returns.iloc[1].to_numpy(), expected.to_numpy())


def test_returns_from_closes_reindexes_missing_days():
    closes, calendar = _synthetic_closes(n_days=20, n_names=3)
    sparse = closes.drop(closes.index[5])
    returns = mod.returns_from_closes(sparse, calendar)
    # the missing day is forward-filled, so its return is exactly zero
    assert returns.iloc[5].abs().max() == 0.0


def test_event_usable_requires_min_observations_and_window():
    closes, calendar = _synthetic_closes(n_days=400, n_names=3)
    # enough history before the event
    assert mod.event_usable(closes, "S0", pd.Timestamp("2020-09-01"))
    # too early in the sample (fewer than MIN_PRICE_OBSERVATIONS closes)
    assert not mod.event_usable(closes, "S0", pd.Timestamp("2020-02-03"))
    # unknown ticker
    assert not mod.event_usable(closes, "NOPE", pd.Timestamp("2020-09-01"))


# --------------------------------------------------------------------------- #
# Event-basket weights (the only new portfolio construction)
# --------------------------------------------------------------------------- #


def test_build_event_weights_gross_normalised_and_directional():
    closes, calendar = _synthetic_closes(n_days=400, n_names=4)
    events = [
        {
            "event_date": pd.Timestamp("2020-09-01").date(),
            "added_ticker": "S0",
            "removed_ticker": "S3",
            "removed_reason_bucket": "market_cap",
        },
        {
            "event_date": pd.Timestamp("2020-10-01").date(),
            "added_ticker": "S1",
            "removed_ticker": None,
            "removed_reason_bucket": None,
        },
    ]
    weights = mod.build_event_weights(events, closes, calendar, holding_days=21)
    active = weights[weights.abs().sum(axis=1) > 0]
    assert len(active) == 42  # two 21-day non-overlapping baskets
    assert np.allclose(active.abs().sum(axis=1), 1.0)
    first = active.iloc[0]
    assert first["S0"] > 0 and first["S3"] < 0
    assert first["S1"] == 0


def test_build_event_weights_respects_holding_window_and_entry_delay():
    closes, calendar = _synthetic_closes(n_days=400, n_names=4)
    events = [
        {
            "event_date": pd.Timestamp("2020-09-01").date(),
            "added_ticker": "S0",
            "removed_ticker": None,
            "removed_reason_bucket": None,
        }
    ]
    base = mod.build_event_weights(events, closes, calendar, holding_days=21, entry_delay=0)
    assert base.loc["2020-08-31"].abs().sum().sum() == 0.0
    assert base.loc["2020-09-01"].abs().sum() == 1.0
    # holding_days=21 opens on 2020-09-01 and last non-zero day is 20 business days later
    nonzero_days = base.index[base.abs().sum(axis=1) > 0]
    assert len(nonzero_days) == 21

    delayed = mod.build_event_weights(events, closes, calendar, holding_days=21, entry_delay=1)
    assert delayed.loc["2020-09-01"].abs().sum() == 0.0
    assert delayed.loc["2020-09-02"].abs().sum() == 1.0


def test_build_event_weights_skips_unusable_names():
    closes, calendar = _synthetic_closes(n_days=400, n_names=4)
    events = [
        {
            "event_date": pd.Timestamp("2020-09-01").date(),
            "added_ticker": "UNKNOWN",
            "removed_ticker": "S3",
            "removed_reason_bucket": "market_cap",
        }
    ]
    weights = mod.build_event_weights(events, closes, calendar, holding_days=21)
    active = weights[weights.abs().sum(axis=1) > 0]
    assert len(active) == 21
    assert active["S3"].abs().sum() > 0  # the short leg is the whole basket


def test_build_event_weights_overlapping_baskets_split_gross():
    closes, calendar = _synthetic_closes(n_days=400, n_names=4)
    events = [
        {
            "event_date": pd.Timestamp("2020-09-01").date(),
            "added_ticker": "S0",
            "removed_ticker": None,
            "removed_reason_bucket": None,
        },
        {
            "event_date": pd.Timestamp("2020-09-15").date(),
            "added_ticker": "S1",
            "removed_ticker": None,
            "removed_reason_bucket": None,
        },
    ]
    weights = mod.build_event_weights(events, closes, calendar, holding_days=21)
    overlap = weights.loc["2020-09-15":"2020-09-18"]
    assert np.allclose(overlap.abs().sum(axis=1), 1.0)
    assert np.allclose(overlap["S0"], 0.5)
    assert np.allclose(overlap["S1"], 0.5)


def test_long_only_events_drops_short_legs():
    events = [
        {
            "event_date": pd.Timestamp("2020-09-01").date(),
            "added_ticker": "S0",
            "removed_ticker": "S3",
            "removed_reason_bucket": "market_cap",
        }
    ]
    long_events = mod.long_only_events(events)
    assert long_events[0]["removed_ticker"] is None
    assert long_events[0]["added_ticker"] == "S0"


def test_scaled_event_weights_delevers_only():
    closes, calendar = _synthetic_closes(n_days=400, n_names=4)
    events = [
        {
            "event_date": pd.Timestamp("2020-09-01").date(),
            "added_ticker": "S0",
            "removed_ticker": None,
            "removed_reason_bucket": None,
        }
    ]
    returns = mod.returns_from_closes(closes, calendar)
    weights = mod.build_event_weights(events, closes, calendar, holding_days=21)
    scaled = mod.scaled_event_weights(weights, returns, 0.10)
    # vol scaling never levers above gross 1.0
    assert scaled.abs().sum(axis=1).max() <= 1.0 + 1e-9


# --------------------------------------------------------------------------- #
# Walk-forward selector
# --------------------------------------------------------------------------- #


def test_walk_forward_score_short_train_returns_sentinel():
    closes, calendar = _synthetic_closes(n_days=300, n_names=4)
    returns = mod.returns_from_closes(closes, calendar)
    short = calendar[:200]
    score = mod.event_walk_forward_score(
        [], closes, returns, list(closes.columns), short, {"holding_days": 21, "entry_delay": 0, "vol_target": 0.10}
    )
    assert score == -999.0


def test_walk_forward_score_finite_on_synthetic_sample():
    closes, calendar = _synthetic_closes(n_days=800, n_names=4, seed=3)
    returns = mod.returns_from_closes(closes, calendar)
    events = [
        {
            "event_date": date,
            "added_ticker": "S0",
            "removed_ticker": "S1",
            "removed_reason_bucket": "market_cap",
        }
        for date in pd.date_range("2020-06-01", "2021-06-01", freq="45D").date
    ]
    train = calendar[calendar <= pd.Timestamp("2021-12-31")]
    score = mod.event_walk_forward_score(
        events, closes, returns, list(closes.columns), train, {"holding_days": 21, "entry_delay": 0, "vol_target": 0.10}
    )
    assert np.isfinite(score)


def test_perturbation_sharpes_returns_six_points():
    closes, calendar = _synthetic_closes(n_days=900, n_names=4, seed=4)
    returns = mod.returns_from_closes(closes, calendar)
    events = [
        {
            "event_date": date,
            "added_ticker": "S0",
            "removed_ticker": "S1",
            "removed_reason_bucket": "market_cap",
        }
        for date in pd.date_range("2020-01-01", "2021-12-01", freq="30D").date
    ]
    oos = calendar[calendar > pd.Timestamp("2021-12-31")]
    values = mod.perturbation_sharpes(
        events, closes, returns, list(closes.columns), {"holding_days": 21, "entry_delay": 0, "vol_target": 0.10}, oos
    )
    assert len(values) == 6
    assert all(np.isfinite(value) for value in values)


# --------------------------------------------------------------------------- #
# Committed artifact
# --------------------------------------------------------------------------- #


def _latest_artifact() -> Path:
    runs = sorted(glob.glob(str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_03_sp500_membership_event_drift_*")))
    if not runs:
        pytest.skip("H198 artifact not yet generated")
    return Path(runs[-1]) / "summary.json"


def test_artifact_summary_exists_and_verdict():
    with open(_latest_artifact()) as fh:
        summary = json.load(fh)
    assert summary["experiment"] == "nf_20261122_03_sp500_membership_event_drift"
    assert summary["nf_id"] == "NF-20261122-03"
    assert summary["hypothesis"] == "H198"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["selected"]["holding_days"] in {21, 42, 63}
    assert summary["selected"]["entry_delay"] in {0, 1}
    assert summary["selected"]["vol_target"] in {0.10, 0.15}
    assert summary["data"]["n_events"] >= mod.MIN_EVENTS
    assert summary["data"]["unique_tickers"] >= 40
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False


def test_artifact_grid_csv_has_twelve_rows():
    grids = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_03_sp500_membership_event_drift_*" / "grid.csv")
    )
    if not grids:
        pytest.skip("H198 grid artifact not yet generated")
    grid = pd.read_csv(max(grids))
    assert len(grid) == 12
    assert {"holding_days", "entry_delay", "vol_target", "wf_train_sharpe"} == set(grid.columns)


def test_artifact_has_data_meta_with_coverage():
    metas = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_03_sp500_membership_event_drift_*" / "data_meta.json")
    )
    if not metas:
        pytest.skip("H198 data_meta artifact not yet generated")
    meta = json.load(open(max(metas)))
    assert meta["event_source"].startswith("Wikipedia")
    assert meta["price_source"].startswith("yfinance")
    assert meta["n_events"] >= mod.MIN_EVENTS
    assert 0.0 < meta["population_coverage_added_frac"] <= 1.0
    assert 0.0 < meta["population_coverage_tradeable_removed_frac"] <= 1.0
    assert meta["borrow_cost_modelled"] is False
    assert meta["coverage_note"].startswith("survivorship-biased subset")