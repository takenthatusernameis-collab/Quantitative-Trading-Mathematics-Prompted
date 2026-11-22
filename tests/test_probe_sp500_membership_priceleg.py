"""Tests for ``scripts/probe_sp500_membership_priceleg.py``.

The script probes whether a tradable price series exists for S&P 500
index-membership *additions* and *deletions* on free data (yfinance).  The
synthetic fixtures below exercise the parsing, classification, sampling and
summary logic independently of the network; one integration test runs the
probe with an injected offline download stub so the probe stays honest as the
real changes table evolves.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "probe_sp500_membership_priceleg.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("probe_sp500_membership_priceleg", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Column flattening / table parsing (offline)
# --------------------------------------------------------------------------- #


def test_flatten_col_handles_tuple_and_repr_forms():
    module = _load_script()
    assert module._flatten_col(("Added", "Ticker")) == "Added_Ticker"
    # pandas read_html may hand back a literal string repr of the tuple.
    assert module._flatten_col("('Effective Date', 'Effective Date')") == (
        "Effective_Date_Effective_Date"
    )
    # first-level header with an internal space is collapsed
    assert module._flatten_col(("Effective Date", "Effective Date")) == (
        "Effective_Date_Effective_Date"
    )
    assert module._flatten_col("Plain") == "Plain"


def _synthetic_changes_html() -> str:
    # Mirror the real Wikipedia structure: a two-row header where each pair of
    # columns shares the same top-level label (Effective Date, Added, ...).
    return """
    <table>
      <tr>
        <th>Effective Date</th><th>Effective Date</th>
        <th>Added</th><th>Added</th>
        <th>Removed</th><th>Removed</th>
        <th>Reason</th><th>Reason</th>
        <th>Refs</th><th>Refs</th>
      </tr>
      <tr>
        <th>Effective Date</th><th>Effective Date</th>
        <th>Ticker</th><th>Security</th>
        <th>Ticker</th><th>Security</th>
        <th>Reason</th><th>Reason</th>
        <th>Refs</th><th>Refs</th>
      </tr>
      <tr>
        <td>October 30, 2026</td><td>October 30, 2026</td>
        <td>OKTA</td><td>Okta, Inc.</td>
        <td>KVUE</td><td>Kenvue</td>
        <td>S&amp;P 500 constituent Kimberly-Clark acquired Kenvue.</td>
        <td>S&amp;P 500 constituent Kimberly-Clark acquired Kenvue.</td>
        <td>[2]</td><td>[2]</td>
      </tr>
      <tr>
        <td>October 6, 2026</td><td>October 6, 2026</td>
        <td>TWLO</td><td>Twilio</td>
        <td>CTVA</td><td>Corteva</td>
        <td>Market capitalization changes.</td>
        <td>Market capitalization changes.</td>
        <td>[3]</td><td>[3]</td>
      </tr>
      <tr>
        <td>not a date</td><td>not a date</td>
        <td></td><td></td>
        <td></td><td></td>
        <td></td><td></td>
        <td></td><td></td>
        <td></td><td></td>
      </tr>
    </table>
    """


def test_fetch_changes_table_parses_and_normalises():
    module = _load_script()
    frame = module.fetch_changes_table(fetch_fn=lambda url: _synthetic_changes_html())

    # The core renamed columns must all be present.
    for col in (
        "effective_date",
        "added_ticker",
        "added_security",
        "removed_ticker",
        "removed_security",
        "reason",
    ):
        assert col in frame.columns, f"missing {col} in {list(frame.columns)}"
    # Refs columns are dropped.
    assert not any(c.startswith("Refs") for c in frame.columns)
    # The malformed-date row is dropped; two valid events remain.
    assert len(frame) == 2
    assert frame["effective_date"].iloc[0] == pd.Timestamp("2026-10-30")
    assert frame["added_ticker"].iloc[0] == "OKTA"
    assert frame["removed_ticker"].iloc[1] == "CTVA"


# --------------------------------------------------------------------------- #
# Reason classification
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "reason,expected",
    [
        ("Acquired by Foo Corp", "acquisition"),
        ("Completed merger with Bar", "acquisition"),
        ("Bankruptcy filing", "bankruptcy"),
        ("Market capitalization changes.", "market_cap"),
        ("Corporate spin-off", "spin_off"),
        ("Reorganization", "reorganization"),
        ("Something else entirely", "other"),
        (None, "other"),
    ],
)
def test_classify_reason(reason, expected):
    module = _load_script()
    assert module.classify_reason(reason) == expected


# --------------------------------------------------------------------------- #
# Sampling
# --------------------------------------------------------------------------- #


def test_sample_events_is_deterministic_and_spread_out():
    module = _load_script()
    frame = pd.DataFrame(
        {
            "effective_date": pd.to_datetime(
                [f"20{y:02d}-01-01" for y in range(10, 20)]  # 2010..2019
            ),
            "added_ticker": [f"A{i}" for i in range(10)],
            "removed_ticker": [f"R{i}" for i in range(10)],
            "reason": ["Market capitalization changes."] * 10,
        }
    )
    samples = module._sample_events(frame, per_class=3, min_year=2005)
    assert [e["ticker"] for e in samples["added"]] == ["A0", "A3", "A6"]
    assert [e["ticker"] for e in samples["removed"]] == ["R0", "R3", "R6"]
    # deterministic: calling again yields the same picks
    assert module._sample_events(frame, per_class=3, min_year=2005) == samples


def test_sample_events_filters_by_min_year():
    module = _load_script()
    frame = pd.DataFrame(
        {
            "effective_date": pd.to_datetime(["2001-01-01", "2020-01-01"]),
            "added_ticker": ["OLD", "NEW"],
            "removed_ticker": ["GONE", "STAY"],
            "reason": ["x", "y"],
        }
    )
    samples = module._sample_events(frame, per_class=5, min_year=2005)
    assert [e["ticker"] for e in samples["added"]] == ["NEW"]
    assert [e["ticker"] for e in samples["removed"]] == ["STAY"]


# --------------------------------------------------------------------------- #
# Per-ticker probing with a stubbed download
# --------------------------------------------------------------------------- #


def _price_frame(n: int, start: str = "2010-01-01") -> pd.DataFrame:
    idx = pd.bdate_range(start=start, periods=n)
    return pd.DataFrame({"Close": range(n)}, index=idx)


def _window_price_frame(**kwargs) -> pd.DataFrame:
    """A series that spans the requested [start, end] window."""
    start = pd.Timestamp(kwargs["start"])
    end = pd.Timestamp(kwargs["end"])
    idx = pd.bdate_range(start=start, end=end)
    return pd.DataFrame({"Close": range(len(idx))}, index=idx)


def test_probe_ticker_covers_event():
    module = _load_script()
    event = dt.date(2010, 6, 1)

    def fake_download(ticker, **kwargs):
        return _window_price_frame(**kwargs)

    row = module._probe_ticker("TEST", event, window_days=252, download_fn=fake_download)
    assert row["has_data"] is True
    assert row["covers_event"] is True
    assert row["rows"] > 0


def test_probe_ticker_no_data_and_error_handling():
    module = _load_script()
    event = dt.date(2010, 6, 1)

    def empty_download(ticker, **kwargs):
        return pd.DataFrame()

    row = module._probe_ticker("DEAD", event, window_days=252, download_fn=empty_download)
    assert row["has_data"] is False
    assert row["covers_event"] is False

    def raising_download(ticker, **kwargs):
        raise RuntimeError("delisted")

    row = module._probe_ticker("DEAD", event, window_days=252, download_fn=raising_download)
    assert row["has_data"] is False
    assert "RuntimeError" in row["error"]


def test_probe_ticker_does_not_cover_event_when_series_misses_date():
    module = _load_script()
    event = dt.date(2020, 6, 1)

    def fake_download(ticker, **kwargs):
        # series ends well before the event -> has data but does not cover it
        return _price_frame(100, start="2010-01-01")

    row = module._probe_ticker("OLD", event, window_days=252, download_fn=fake_download)
    assert row["has_data"] is True
    assert row["covers_event"] is False


# --------------------------------------------------------------------------- #
# Integration (offline): full main() with stubbed fetch + download
# --------------------------------------------------------------------------- #


def test_main_offline_integration_blocks_on_removed_leg(capsys, monkeypatch):
    module = _load_script()
    monkeypatch.setattr(
        module,
        "fetch_changes_table",
        lambda: _frame_from_html(_synthetic_changes_html()),
    )

    # Every added ticker has data; every removed ticker is delisted (no data).
    added = {"OKTA", "TWLO"}

    def fake_download(ticker, **kwargs):
        if ticker in added:
            return _price_frame(300, start="2009-01-01")
        return pd.DataFrame()

    rc = module.main(["--sample", "10"], download_fn=fake_download)
    out = capsys.readouterr().out
    assert "PRICE LEG BLOCKED" in out
    assert rc == 1


def _frame_from_html(html: str) -> pd.DataFrame:
    module = _load_script()
    return module.fetch_changes_table(fetch_fn=lambda url: html)


def test_main_offline_integration_feasible(capsys, monkeypatch):
    module = _load_script()
    monkeypatch.setattr(
        module,
        "fetch_changes_table",
        lambda: _frame_from_html(_synthetic_changes_html()),
    )

    def fake_download(ticker, **kwargs):
        return _price_frame(300, start="2009-01-01")

    rc = module.main(["--sample", "10"], download_fn=fake_download)
    out = capsys.readouterr().out
    assert "PRICE LEG FEASIBLE" in out
    assert rc == 0
