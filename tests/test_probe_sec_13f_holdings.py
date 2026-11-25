"""Tests for ``scripts/probe_sec_13f_holdings.py``.

The script probes SEC EDGAR Form 13F-HR institutional holdings as a free
point-in-time flow source. The synthetic fixtures below exercise the parsing,
extraction, and summary logic independently of the network; one integration
test runs the probe with an injected offline download stub so the probe stays
honest as the real SEC EDGAR data evolves.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "probe_sec_13f_holdings.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("probe_sec_13f_holdings", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Submission index parsing
# --------------------------------------------------------------------------- #


def _synthetic_submissions_json() -> dict:
    return {
        "filings": {
            "recent": {
                "accessionNumber": [
                    "0001067983-26-000001",
                    "0001067983-25-000002",
                    "0001067983-24-000003",
                    "0001067983-23-000004",
                ],
                "form": ["13F-HR", "13F-HR/A", "10-K", "13F-HR"],
                "filingDate": ["2026-11-16", "2025-11-14", "2024-02-28", "2024-11-14"],
                "acceptanceDateTime": [
                    "2026-11-16T10:30:00.000Z",
                    "2025-11-14T14:45:00.000Z",
                    "2024-02-28T16:20:00.000Z",
                    "2024-11-14T11:15:00.000Z",
                ],
                "reportDate": ["2026-09-30", "2025-09-30", "2023-12-31", "2024-09-30"],
                "primaryDocument": [
                    "primary_doc1.html",
                    "primary_doc2.html",
                    "10k.html",
                    "primary_doc4.html",
                ],
            }
        }
    }


def test_extract_13f_filings_parses_only_13f_forms():
    module = _load_script()
    frame = module.extract_13f_filings(_synthetic_submissions_json())

    # Should only keep 13F-HR and 13F-HR/A, not 10-K
    assert len(frame) == 3
    assert list(frame["form"]) == ["13F-HR", "13F-HR/A", "13F-HR"]
    assert list(frame["report_date"]) == ["2026-09-30", "2025-09-30", "2024-09-30"]
    assert list(frame["acceptance_datetime"]) == [
        "2026-11-16T10:30:00.000Z",
        "2025-11-14T14:45:00.000Z",
        "2024-11-14T11:15:00.000Z",
    ]


def test_extract_13f_filings_empty_recent():
    module = _load_script()
    empty = {"filings": {"recent": {}}}
    frame = module.extract_13f_filings(empty)
    assert len(frame) == 0
    assert list(frame.columns) == [
        "accession_number",
        "form",
        "filing_date",
        "acceptance_datetime",
        "report_date",
        "primary_document",
    ]


# --------------------------------------------------------------------------- #
# Information table document discovery
# --------------------------------------------------------------------------- #


def test_find_information_table_document_prefers_numeric_xml():
    module = _load_script()
    documents = {
        "primary_doc.xml": "https://example.com/primary_doc.xml",
        "60471.xml": "https://example.com/60471.xml",
        "99999.xml": "https://example.com/99999.xml",
        "other.xml": "https://example.com/other.xml",
    }
    result = module.find_information_table_document(documents)
    # Should pick the first numeric-named XML (not primary_doc.xml)
    assert result == "https://example.com/60471.xml"


def test_find_information_table_document_none_when_no_numeric_xml():
    module = _load_script()
    documents = {
        "primary_doc.xml": "https://example.com/primary_doc.xml",
        "exhibit.xml": "https://example.com/exhibit.xml",
    }
    result = module.find_information_table_document(documents)
    assert result is None


# --------------------------------------------------------------------------- #
# Acceptance datetime parsing
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-11-16T10:30:00.000Z", pd.Timestamp("2026-11-16 10:30:00")),
        ("2026-11-16T10:30:00Z", pd.Timestamp("2026-11-16 10:30:00")),
        (None, pd.NaT),
        ("", pd.NaT),
        ("not-a-date", pd.NaT),
    ],
)
def test_parse_acceptance_datetime(value, expected):
    module = _load_script()
    result = module.parse_acceptance_datetime(value)
    if pd.isna(expected):
        assert pd.isna(result)
    else:
        assert result == expected


# --------------------------------------------------------------------------- #
# Per-CIK coverage computation with stubbed network
# --------------------------------------------------------------------------- #


def _stub_submissions_with_filings(n_filings: int = 2) -> dict:
    return {
        "filings": {
            "recent": {
                "accessionNumber": [f"0001067983-26-{i:06d}" for i in range(1, n_filings + 1)],
                "form": ["13F-HR"] * n_filings,
                "filingDate": [f"202{6 - i}-11-15" for i in range(n_filings)],
                "acceptanceDateTime": [f"202{6 - i}-11-15T10:00:00.000Z" for i in range(n_filings)],
                "reportDate": [f"202{6 - i}-09-30" for i in range(n_filings)],
                "primaryDocument": [f"primary_doc{i}.html" for i in range(1, n_filings + 1)],
            }
        }
    }


def _stub_13f_index(has_info_table: bool = True) -> dict:
    if has_info_table:
        return {
            "directory": {
                "item": [
                    {"name": "primary_doc.html"},
                    {"name": "12345.xml"},
                ]
            }
        }
    return {"directory": {"item": [{"name": "primary_doc.html"}]}}


def _stub_13f_xml(n_positions: int = 5) -> str:
    if n_positions == 0:
        return """<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
</informationTable>"""
    rows = "\n".join(
        f"""<infoTable>
    <nameOfIssuer>ISSUER{i}</nameOfIssuer>
    <titleOfClass>Common Stock</titleOfClass>
    <cusip>{123456000 + i:09d}</cusip>
    <value>{1000000 + i * 100000}</value>
    <shrsOrPrnAmt>
        <sshPrnamt>{1000 + i * 100}</sshPrnamt>
        <sshPrnamtType>SH</sshPrnamtType>
    </shrsOrPrnAmt>
    <investmentDiscretion>SOLE</investmentDiscretion>
    <votingAuthority>
        <Sole>{1000 + i * 100}</Sole>
        <Shared>0</Shared>
        <None>0</None>
    </votingAuthority>
</infoTable>"""
        for i in range(n_positions)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
{rows}
</informationTable>"""


def test_coverage_for_cik_computes_lags_and_positions(monkeypatch):
    module = _load_script()

    def fake_cached_submissions(cik, cache_dir, fetch=True, refresh=False, retries=3):
        return _stub_submissions_with_filings(2)

    def fake_fetch_13f_holdings_table(cik, accession_number, user_agent=None, timeout=30.0):
        # First filing has positions, second has zero
        if "000001" in accession_number:
            return pd.DataFrame({"cusip": ["123456001", "123456002"], "value": [1000000, 2000000]})
        return pd.DataFrame()

    monkeypatch.setattr(module, "cached_submissions", fake_cached_submissions)
    monkeypatch.setattr(module, "fetch_13f_holdings_table", fake_fetch_13f_holdings_table)

    result = module.coverage_for_cik("0001067983", "Berkshire Hathaway Inc.", fetch=False)

    assert result["cik"] == "0001067983"
    assert result["filings_downloaded"] == 2
    assert result["filings_with_positions"] == 1
    assert result["total_positions"] == 2
    assert result["quarters_covered"] == 2
    assert result["zero_position_filings"] == 1
    # Filing lag: 2026-11-15 - 2026-09-30 = 46 days; 2025-11-15 - 2025-09-30 = 46 days
    assert result["median_filing_lag_days"] == 46.0


def test_coverage_for_cik_handles_missing_submissions(monkeypatch):
    module = _load_script()

    def fake_cached_submissions(cik, cache_dir, fetch=True, refresh=False, retries=3):
        raise FileNotFoundError("not cached")

    monkeypatch.setattr(module, "cached_submissions", fake_cached_submissions)

    result = module.coverage_for_cik("9999999999", "Unknown", fetch=False)

    assert result["cik"] == "9999999999"
    assert result["filings_downloaded"] == 0
    assert result["filings_with_positions"] == 0


def test_probe_records_bad_cik_without_crashing(monkeypatch):
    """One stale/incorrect CIK (HTTP 404) must not abort a multi-filer run.

    Regression guard: the bundled ``INSTITUTIONAL_CIKS`` map is partly stale, so
    a single non-existent submissions URL used to raise ``HTTPError`` and kill
    the whole probe. ``probe`` must record the bad CIK in ``missing_submissions``
    (with its error type in ``missing_errors``) and still report the good ones.
    """
    module = _load_script()

    def fake_coverage_for_cik(cik, name, cache_dir=None, fetch=True, refresh=False):
        if cik == "0001067983":
            # A stale/incorrect submissions URL surfaces as an HTTPError (a
            # subclass of OSError); a plain OSError represents that fetch
            # failure without HTTPError's temp-file destructor (which trips
            # ``-W error``).
            raise OSError("HTTP 404 Not Found")
        return {
            "cik": cik,
            "name": name,
            "filings_downloaded": 1,
            "filings_with_positions": 1,
            "total_positions": 3,
            "quarters_covered": 1,
            "first_report_date": "2025-09-30",
            "last_report_date": "2025-09-30",
            "first_acceptance_date": "2025-11-14",
            "last_acceptance_date": "2025-11-14",
            "median_filing_lag_days": 45.0,
            "zero_position_filings": 0,
        }

    monkeypatch.setattr(module, "coverage_for_cik", fake_coverage_for_cik)

    # Use a CIK from the current INSTITUTIONAL_CIKS as the "good" CIK
    report = module.probe(["0001067983", "0000093751"], fetch=False)

    assert report["ciks_requested"] == 2
    assert report["ciks_with_positions"] == 1
    assert "0001067983" in report["missing_submissions"]
    assert any(
        e["cik"] == "0001067983" and e["error"] == "OSError" for e in report["missing_errors"]
    )
    # The good CIK is still reported.
    assert any(row["cik"] == "0000093751" for row in report["per_cik"])


# --------------------------------------------------------------------------- #
# Integration (offline): full main() with stubbed fetch
# --------------------------------------------------------------------------- #


def test_main_offline_integration_feasible(monkeypatch, capsys):
    module = _load_script()

    def fake_cached_submissions(cik, cache_dir, fetch=True, refresh=False, retries=3):
        return _stub_submissions_with_filings(3)

    def fake_fetch_13f_holdings_table(cik, accession_number, user_agent=None, timeout=30.0):
        return pd.DataFrame({"cusip": ["123456001"], "value": [1000000]})

    monkeypatch.setattr(module, "cached_submissions", fake_cached_submissions)
    monkeypatch.setattr(module, "fetch_13f_holdings_table", fake_fetch_13f_holdings_table)

    rc = module.main(["--limit", "1", "--download-only"])
    out = capsys.readouterr().out

    assert rc["ciks_requested"] == 1
    assert rc["ciks_with_filings"] == 3
    assert "missing_submissions" not in rc or rc["missing_submissions"] == []


def test_main_offline_integration_partial_coverage(monkeypatch, capsys):
    module = _load_script()

    def fake_cached_submissions(cik, cache_dir, fetch=True, refresh=False, retries=3):
        return _stub_submissions_with_filings(2)

    def fake_fetch_13f_holdings_table(cik, accession_number, user_agent=None, timeout=30.0):
        # Alternate: one with positions, one without
        if "000001" in accession_number:
            return pd.DataFrame({"cusip": ["123456001"]})
        return pd.DataFrame()

    monkeypatch.setattr(module, "cached_submissions", fake_cached_submissions)
    monkeypatch.setattr(module, "fetch_13f_holdings_table", fake_fetch_13f_holdings_table)

    rc = module.main(["--limit", "1"])
    out = capsys.readouterr().out

    assert rc["ciks_requested"] == 1
    assert rc["ciks_with_positions"] == 1
    # ciks_with_zero_position_filings only includes CIKs where ALL filings have zero positions.
    # This CIK has one filing with positions, so it's not in the zero-position list.
    assert rc["ciks_with_zero_position_filings"] == []
    assert rc["total_positions_extracted"] > 0


# --------------------------------------------------------------------------- #
# CIK normalization and User-Agent
# --------------------------------------------------------------------------- #


def test_normalize_cik_handles_various_formats():
    module = _load_script()
    # The normalize_cik is imported from qtr.data.insider
    from qtr.data.insider import normalize_cik

    assert normalize_cik("0001067983") == "0001067983"
    assert normalize_cik("1067983") == "0001067983"
    assert normalize_cik(1067983) == "0001067983"


def test_user_agent_returns_string():
    module = _load_script()
    from qtr.data.insider import user_agent

    ua = user_agent()
    assert isinstance(ua, str)
    assert len(ua) > 0
    # The default user agent includes the project name
    assert "qtr" in ua.lower()
