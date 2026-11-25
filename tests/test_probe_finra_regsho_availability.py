"""Tests for ``scripts/probe_finra_regsho_availability.py``."""

from __future__ import annotations

import datetime as dt
import io

import pandas as pd
import pytest

import scripts.probe_finra_regsho_availability as probe


class TestParseRegSHO:
    """Tests for the Reg SHO file parser."""

    def test_parse_regsho_basic(self):
        """Parse a minimal valid Reg SHO file."""
        raw = b"Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\r\n20261120|AAPL|1000000|100|2000000|Q\r\n"
        df = probe.parse_regsho(raw)
        assert len(df) == 1
        assert df.iloc[0]["Symbol"] == "AAPL"
        assert df.iloc[0]["ShortVolume"] == 1_000_000
        assert df.iloc[0]["TotalVolume"] == 2_000_000
        assert df.iloc[0]["ShortRatio"] == pytest.approx(0.5)

    def test_parse_regsho_multiple_symbols(self):
        """Parse file with multiple symbols."""
        raw = (
            b"Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\r\n"
            b"20261120|AAPL|1000000|100|2000000|Q\r\n"
            b"20261120|MSFT|500000|50|1500000|Q\r\n"
            b"20261120|NVDA|200000|20|1000000|Q\r\n"
        )
        df = probe.parse_regsho(raw)
        assert len(df) == 3
        symbols = set(df["Symbol"])
        assert symbols == {"AAPL", "MSFT", "NVDA"}

    def test_parse_regsho_handles_missing_values(self):
        """Parser should drop rows with non-numeric volumes."""
        raw = (
            b"Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\r\n"
            b"20261120|AAPL|1000000|100|2000000|Q\r\n"
            b"20261120|BAD|abc|0|xyz|Q\r\n"
        )
        df = probe.parse_regsho(raw)
        assert len(df) == 1
        assert df.iloc[0]["Symbol"] == "AAPL"

    def test_parse_regsho_empty(self):
        """Empty file (header only) returns empty DataFrame with correct columns."""
        raw = b"Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\r\n"
        df = probe.parse_regsho(raw)
        assert len(df) == 0
        assert list(df.columns) == ["Symbol", "ShortVolume", "TotalVolume", "ShortRatio"]


class TestDateRange:
    """Tests for the business day range generator."""

    def test_date_range_basic(self):
        """Range includes start and end business days."""
        start = dt.date(2026, 11, 18)  # Wednesday
        end = dt.date(2026, 11, 20)  # Friday
        dates = probe.date_range(start, end)
        assert len(dates) == 3
        assert dates[0] == pd.Timestamp("2026-11-18")
        assert dates[-1] == pd.Timestamp("2026-11-20")

    def test_date_range_skips_weekend(self):
        """Range skips Saturday and Sunday."""
        start = dt.date(2026, 11, 20)  # Friday
        end = dt.date(2026, 11, 23)  # Monday
        dates = probe.date_range(start, end)
        # Should be Fri, Mon (Sat/Sun skipped)
        assert len(dates) == 2
        assert dates[0] == pd.Timestamp("2026-11-20")
        assert dates[1] == pd.Timestamp("2026-11-23")


class TestProbeSymbol:
    """Tests for the per-symbol probe function (with mocked fetch)."""

    def make_mock_raw(self, symbol: str, ratio: float) -> bytes:
        """Create a mock Reg SHO file with one symbol at a given ratio."""
        # Use exact values to avoid floating point issues
        short_vol = int(ratio * 10_000_000)
        total_vol = 10_000_000
        return (
            b"Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\r\n"
            + f"20261120|{symbol}|{short_vol}|0|{total_vol}|Q\r\n".encode()
        )

    def test_probe_symbol_found(self):
        """Symbol found in all sampled files."""

        def mock_fetch(date):
            return self.make_mock_raw("AAPL", 0.5)

        dates = [dt.date(2026, 11, 18), dt.date(2026, 11, 19), dt.date(2026, 11, 20)]
        row = probe.probe_symbol(
            "AAPL", dt.date(2026, 11, 1), dt.date(2026, 11, 30), dates, fetch=mock_fetch
        )
        assert row["status"] == "OK"
        assert row["observations"] == 3
        assert row["mean_short_ratio"] == pytest.approx(0.5)

    def test_probe_symbol_partial(self):
        """Symbol found in some sampled files."""
        call_count = {"n": 0}

        def mock_fetch(date):
            call_count["n"] += 1
            if call_count["n"] % 2 == 0:
                return self.make_mock_raw("AAPL", 0.5)
            return None  # Simulate weekend/holiday

        dates = [dt.date(2026, 11, 18), dt.date(2026, 11, 19), dt.date(2026, 11, 20)]
        row = probe.probe_symbol(
            "AAPL", dt.date(2026, 11, 1), dt.date(2026, 11, 30), dates, fetch=mock_fetch
        )
        assert row["status"] == "OK"
        assert row["observations"] == 1  # Only even calls return data
        assert row["mean_short_ratio"] == pytest.approx(0.5)

    def test_probe_symbol_not_found(self):
        """Symbol never found in sampled files."""

        def mock_fetch(date):
            return self.make_mock_raw("MSFT", 0.3)  # Different symbol

        dates = [dt.date(2026, 11, 18), dt.date(2026, 11, 19)]
        row = probe.probe_symbol(
            "AAPL", dt.date(2026, 11, 1), dt.date(2026, 11, 30), dates, fetch=mock_fetch
        )
        assert row["status"] == "NO_DATA"
        assert row["observations"] == 0
        assert row["mean_short_ratio"] == 0.0


class TestRegSHOURL:
    """Tests for URL construction."""

    def test_regsho_url_format(self):
        """URL follows the expected pattern."""
        url = probe.regsho_url(dt.date(2026, 11, 20))
        assert url == "https://cdn.finra.org/equity/regsho/daily/CNMSshvol20261120.txt"

    def test_regsho_url_zero_padding(self):
        """Month and day are zero-padded."""
        url = probe.regsho_url(dt.date(2026, 1, 5))
        assert url == "https://cdn.finra.org/equity/regsho/daily/CNMSshvol20260105.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
