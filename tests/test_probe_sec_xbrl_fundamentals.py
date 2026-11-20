"""Contract tests for ``scripts/probe_sec_xbrl_fundamentals.py`` (no network).

The probe is the evidence harness for the SEC XBRL availability claim that
unblocks the H187 accruals / asset-growth family.  Two behaviours matter:

* point-in-time correctness -- an annual observation is only usable from the
  ``filed`` acceptance date of the *latest* contributing fact, so a signal can
  never see a 10-K before it was public;
* honest coverage -- a downloaded companyfacts bundle that yields zero annual
  rows must be reported as zero, not counted as usable data.  (The live XOM
  ticker resolves to a 2026 successor entity with no 10-K history, and CAT
  stops reporting ``NetIncomeLoss`` as an annual 10-K fact after 2010.)
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "probe_sec_xbrl_fundamentals.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("probe_sec_xbrl_fundamentals", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script():
    return _load_script()


def _fact(
    start: str | None,
    end: str,
    value: float,
    filed: str,
    *,
    form: str = "10-K",
) -> dict:
    row = {"end": end, "val": value, "filed": filed, "form": form}
    if start is not None:
        row["start"] = start
    return row


def _bundle(
    *,
    ni: list[dict] | None = None,
    cfo: list[dict] | None = None,
    assets: list[dict] | None = None,
) -> dict:
    gaap = {}
    for tag, rows in (
        ("NetIncomeLoss", ni),
        ("NetCashProvidedByUsedInOperatingActivities", cfo),
        ("Assets", assets),
    ):
        if rows is not None:
            gaap[tag] = {"units": {"USD": rows}}
    return {"facts": {"us-gaap": gaap}}


def _two_year_bundle() -> dict:
    return _bundle(
        ni=[
            _fact("2022-01-01", "2022-12-31", 100.0, "2023-02-20"),
            _fact("2023-01-01", "2023-12-31", 120.0, "2024-02-15"),
        ],
        cfo=[
            _fact("2022-01-01", "2022-12-31", 90.0, "2023-02-20"),
            _fact("2023-01-01", "2023-12-31", 100.0, "2024-02-15"),
        ],
        assets=[
            _fact(None, "2022-12-31", 1000.0, "2023-02-20"),
            _fact(None, "2023-12-31", 1200.0, "2024-02-15"),
        ],
    )


def _three_year_bundle() -> dict:
    bundle = _two_year_bundle()
    bundle["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"].append(
        _fact("2024-01-01", "2024-12-31", 140.0, "2025-02-14")
    )
    bundle["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"].append(
        _fact("2024-01-01", "2024-12-31", 110.0, "2025-02-14")
    )
    bundle["facts"]["us-gaap"]["Assets"]["units"]["USD"].append(
        _fact(None, "2024-12-31", 1300.0, "2025-02-14")
    )
    return bundle


class TestTagRows:
    def test_flattens_usd_units_and_parses_dates(self, script):
        frame = script.tag_rows(
            _bundle(ni=[_fact("2022-01-01", "2022-12-31", 5.0, "2023-02-20")]),
            "NetIncomeLoss",
        )
        assert list(frame["val"]) == [5.0]
        assert pd.api.types.is_datetime64_any_dtype(frame["filed"])
        assert pd.api.types.is_datetime64_any_dtype(frame["end"])

    def test_missing_tag_returns_empty_frame_with_schema(self, script):
        frame = script.tag_rows(_bundle(), "NetIncomeLoss")
        assert frame.empty
        assert "val" in frame.columns and "filed" in frame.columns

    def test_instant_tag_without_start_column_is_preserved(self, script):
        frame = script.tag_rows(
            _bundle(assets=[_fact(None, "2022-12-31", 10.0, "2023-02-20")]),
            "Assets",
        )
        assert len(frame) == 1
        assert frame["start"].isna().all()


class TestAnnualObservations:
    def test_accruals_and_asset_growth_match_definition(self, script):
        observations = script.annual_observations(_two_year_bundle())
        assert list(observations["end"].dt.year) == [2022, 2023]
        # first year has no prior assets -> both derived columns unusable
        assert pd.isna(observations.loc[0, "accruals"])
        assert pd.isna(observations.loc[0, "asset_growth"])
        # accruals = (NI - CFO) / mean assets = (120-100) / ((1000+1200)/2)
        assert observations.loc[1, "accruals"] == pytest.approx(20.0 / 1100.0)
        assert observations.loc[1, "asset_growth"] == pytest.approx(1200.0 / 1000.0 - 1.0)

    def test_filed_is_latest_contributing_fact(self, script):
        bundle = _two_year_bundle()
        # restate the 2023 balance sheet later: the row is only usable then
        bundle["facts"]["us-gaap"]["Assets"]["units"]["USD"][-1]["filed"] = "2024-03-01"
        observations = script.annual_observations(bundle)
        assert observations.loc[1, "filed"] == pd.Timestamp("2024-03-01")

    def test_duplicate_period_keeps_earliest_filed(self, script):
        bundle = _two_year_bundle()
        bundle["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"].append(
            _fact("2023-01-01", "2023-12-31", 999.0, "2024-06-01")
        )
        observations = script.annual_observations(bundle)
        row = observations[observations["end"] == pd.Timestamp("2023-12-31")].iloc[0]
        assert row["ni"] == 120.0
        assert row["filed"] == pd.Timestamp("2024-02-15")

    def test_non_annual_periods_are_dropped(self, script):
        bundle = _bundle(
            ni=[_fact("2023-01-01", "2023-06-30", 50.0, "2023-08-01")],
            cfo=[_fact("2023-01-01", "2023-06-30", 40.0, "2023-08-01")],
            assets=[_fact(None, "2023-06-30", 1000.0, "2023-08-01")],
        )
        assert script.annual_observations(bundle).empty

    def test_non_10k_forms_are_dropped(self, script):
        bundle = _bundle(
            ni=[_fact("2022-01-01", "2022-12-31", 100.0, "2023-02-20", form="10-Q")],
            cfo=[_fact("2022-01-01", "2022-12-31", 90.0, "2023-02-20", form="10-Q")],
            assets=[_fact(None, "2022-12-31", 1000.0, "2023-02-20", form="10-Q")],
        )
        assert script.annual_observations(bundle).empty


class TestCoverage:
    def test_has_annual_data_false_for_empty_bundle(self, script):
        row = script.coverage(_bundle(), "XOM")
        assert row["has_annual_data"] is False
        assert row["annual_observations"] == 0
        assert row["median_filing_lag_days"] is None

    def test_reports_observations_and_lag(self, script):
        row = script.coverage(_two_year_bundle(), "AAPL")
        assert row["has_annual_data"] is True
        assert row["annual_observations"] == 2
        assert row["usable_accruals"] == 1
        assert row["median_filing_lag_days"] == 48.5


def _seed_cache(cache_dir: Path, bundles: dict[str, dict], tickers: dict[str, str]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    mapping = {
        str(index): {"cik_str": int(cik), "ticker": symbol, "title": symbol}
        for index, (symbol, cik) in enumerate(tickers.items())
    }
    (cache_dir / "company_tickers.json").write_text(json.dumps(mapping))
    for cik, bundle in bundles.items():
        (cache_dir / f"CIK{int(cik):010d}.json").write_text(json.dumps(bundle))


class TestProbeSummary:
    def test_zero_annual_symbol_is_not_counted_as_usable(self, script, tmp_path):
        cache_dir = tmp_path / "xbrl"
        _seed_cache(
            cache_dir,
            {"1": _three_year_bundle(), "2": _bundle()},
            {"AAPL": "1", "XOM": "2"},
        )
        report = script.probe(["AAPL", "XOM"], cache_dir, fetch=False)
        assert report["symbols_requested"] == 2
        assert report["symbols_with_bundle"] == 2
        assert report["symbols_with_annual_data"] == 1
        assert report["symbols_with_zero_annual_observations"] == ["XOM"]
        assert report["symbols_with_two_plus_accrual_observations"] == 1
        assert report["missing_bundles"] == []

    def test_unknown_ticker_is_reported_as_missing_bundle(self, script, tmp_path):
        cache_dir = tmp_path / "xbrl"
        _seed_cache(cache_dir, {"1": _two_year_bundle()}, {"AAPL": "1"})
        report = script.probe(["AAPL", "NOPE"], cache_dir, fetch=False)
        assert report["missing_bundles"] == ["NOPE"]
        assert report["symbols_with_bundle"] == 1
