"""Offline tests for ``scripts/probe_remaining_family_sources.py``.

The probe is a free-data availability harness; these tests pin its parsing and
aggregation logic with synthetic inputs and injected fetchers so they never touch
the network. They mirror the structure of ``tests/test_probe_finra_regsho_availability.py``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "probe_remaining_family_sources", ROOT / "scripts" / "probe_remaining_family_sources.py"
)
assert _SPEC is not None and _SPEC.loader is not None
probe = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(probe)


def _fake_get_bytes(mapping):
    def _get(url, timeout=None):
        for key, value in mapping.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        raise AssertionError(f"unexpected url: {url}")

    return _get


def _fake_status(mapping):
    def _status(url, timeout=None):
        for key, value in mapping.items():
            if key in url:
                return value
        return (404, 0, b"")

    return _status


def test_parse_ncen_primary_doc_extracts_metadata_without_flow():
    xml = (
        '<?xml version="1.0"?>'
        "<edgarSubmission>"
        "<seriesInfo><totalSeries>71</totalSeries>"
        "<mnthlyAvgNetAssets>188729647.99</mnthlyAvgNetAssets></seriesInfo>"
        "</edgarSubmission>"
    )
    parsed = probe.parse_ncen_primary_doc(xml)
    assert parsed["parseable"] is True
    assert parsed["total_series"] == "71"
    assert parsed["mnthly_avg_net_assets"] == "188729647.99"
    assert parsed["flow_present"] is False


def test_parse_ncen_primary_doc_detects_flow_tags():
    xml = "<edgarSubmission><netAssetFlow><monthlyNetAssetFlow>123</monthlyNetAssetFlow></netAssetFlow></edgarSubmission>"
    parsed = probe.parse_ncen_primary_doc(xml)
    assert parsed["parseable"] is True
    assert parsed["flow_present"] is True


def test_parse_ncen_primary_doc_handles_namespaces():
    xml = (
        '<edgarSubmission xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">'
        "<totalSeries>5</totalSeries></edgarSubmission>"
    )
    parsed = probe.parse_ncen_primary_doc(xml)
    assert parsed["parseable"] is True
    assert parsed["total_series"] == "5"


def test_parse_ncen_primary_doc_malformed():
    parsed = probe.parse_ncen_primary_doc("<not-xml")
    assert parsed == {"parseable": False}


def test_probe_cboe_options_reports_blocked_on_403():
    report = probe.probe_cboe_options(status_get=_fake_status({"cboe.com": (403, 0, b"")}))
    assert report["reachable"] is False
    assert report["probes"][0]["status"] == 403
    assert "403" in report["note"] or "non-200" in report["note"]


def test_probe_cboe_options_reports_reachable_on_200():
    report = probe.probe_cboe_options(status_get=_fake_status({"cboe.com": (200, 256, b"{}")}))
    assert report["reachable"] is True


def test_probe_fred_parses_csv_coverage():
    csv = b"observation_date,T10YIE\n2003-01-02,1.64\n2003-01-03,1.62\n"
    report = probe.probe_fred(series_list=["T10YIE"], get=_fake_get_bytes({"fredgraph": csv}))
    assert report["reachable"] is True
    series = report["series"][0]
    assert series["n_obs"] == 2
    assert series["first"] == "2003-01-02"
    assert series["last"] == "2003-01-03"


def test_probe_fred_reports_error_for_failed_series():
    report = probe.probe_fred(
        series_list=["T10YIE"], get=_fake_get_bytes({"fredgraph": TimeoutError()})
    )
    assert report["reachable"] is False
    assert report["series"][0]["error"] == "TimeoutError"


def _ncen_submissions(cik):
    return json.dumps(
        {
            "filings": {
                "recent": {
                    "form": ["N-CEN", "NPORT-P"],
                    "accessionNumber": ["0001410368-26-069245", "0001410368-26-000001"],
                    "filingDate": ["2026-07-08", "2026-07-30"],
                    "acceptanceDateTime": ["2026-07-08T18:09:06.000Z", "2026-07-30T12:00:00.000Z"],
                    "primaryDocument": ["primary_doc.xml", "primary_doc.xml"],
                }
            }
        }
    ).encode()


def test_probe_sec_ncen_reports_metadata_and_flow_absent():
    ncen_xml = b"<edgarSubmission><totalSeries>71</totalSeries></edgarSubmission>"
    index = json.dumps({"directory": {"item": [{"name": "primary_doc.xml"}]}}).encode()
    mapping = {
        "submissions/CIK": _ncen_submissions("0001137360"),
        "index.json": index,
        "primary_doc.xml": ncen_xml,
    }
    report = probe.probe_sec_ncen(
        ciks={"0001137360": "BlackRock Funds"}, get=_fake_get_bytes(mapping)
    )
    assert report["reachable"] is True
    assert report["flow_bounded"] is False
    assert report["per_cik"][0]["total_series"] == "71"
    assert report["per_cik"][0]["acceptance_datetime"] == "2026-07-08T18:09:06.000Z"
    assert report["per_cik"][0]["documents"] == ["primary_doc.xml"]
    assert report["per_cik"][0]["n_xml_documents"] == 1
    assert "structural census" in report["note"]


def test_list_filing_documents_parses_index():
    index = json.dumps(
        {"directory": {"item": [{"name": "primary_doc.xml"}, {"name": "a.htm"}, {"name": ""}]}}
    ).encode()
    docs = probe.list_filing_documents(
        "0001137360", "0001410368-26-069245", get=_fake_get_bytes({"index.json": index})
    )
    assert docs == ["primary_doc.xml", "a.htm"]


def test_list_filing_documents_empty_on_error():
    docs = probe.list_filing_documents(
        "0001137360", "0001410368-26-069245", get=_fake_get_bytes({"index.json": TimeoutError()})
    )
    assert docs == []


def test_probe_sec_ncen_detects_flow_in_secondary_exhibit():
    index = json.dumps(
        {"directory": {"item": [{"name": "primary_doc.xml"}, {"name": "exhibit_flow.xml"}]}}
    ).encode()
    mapping = {
        "submissions/CIK": _ncen_submissions("0001137360"),
        "index.json": index,
        "primary_doc.xml": b"<edgarSubmission><totalSeries>3</totalSeries></edgarSubmission>",
        "exhibit_flow.xml": b"<x><monthlySales>42</monthlySales></x>",
    }
    report = probe.probe_sec_ncen(ciks={"0001137360": "X"}, get=_fake_get_bytes(mapping))
    assert report["flow_bounded"] is True
    assert report["per_cik"][0]["flow_present"] is True
    assert report["per_cik"][0]["n_xml_documents"] == 2
    assert report["per_cik"][0]["documents"] == ["primary_doc.xml", "exhibit_flow.xml"]


def test_probe_sec_ncen_no_filing_is_not_reachable():
    empty = json.dumps({"filings": {"recent": {"form": ["13F-HR"]}}}).encode()
    report = probe.probe_sec_ncen(
        ciks={"0001137360": "x"}, get=_fake_get_bytes({"submissions": empty})
    )
    assert report["reachable"] is False
    assert "no N-CEN" in report["per_cik"][0]["error"]


def test_probe_sec_nport_reachable():
    mapping = {"submissions/CIK": _ncen_submissions("0000036405")}
    report = probe.probe_sec_nport(
        ciks={"0000036405": "Vanguard World Fund"}, get=_fake_get_bytes(mapping)
    )
    assert report["reachable"] is True
    assert report["per_cik"][0]["accession"] == "0001410368-26-000001"


def test_probe_aggregates_any_reachable():
    mapping = {
        "submissions/CIK": _ncen_submissions("0001137360"),
        "index.json": json.dumps({"directory": {"item": [{"name": "primary_doc.xml"}]}}).encode(),
        "primary_doc.xml": b"<edgarSubmission><totalSeries>1</totalSeries></edgarSubmission>",
        "fredgraph": b"observation_date,T10YIE\n2020-01-01,1.0\n",
    }
    report = probe.probe(
        get=_fake_get_bytes(mapping), status_get=_fake_status({"cboe.com": (403, 0, b"")})
    )
    assert report["any_reachable"] is True
    assert set(report["sections"]) == {"cboe_options", "fred_macro", "sec_ncen", "sec_nport"}


def test_probe_all_unreachable_is_false():
    report = probe.probe(
        get=_fake_get_bytes({"submissions": TimeoutError(), "fredgraph": TimeoutError()}),
        status_get=_fake_status({"cboe.com": (403, 0, b"")}),
    )
    assert report["any_reachable"] is False


def test_main_writes_report_and_exit_zero(tmp_path, monkeypatch):
    out = tmp_path / "report.json"
    monkeypatch.setattr(probe, "probe", lambda: {"any_reachable": True, "sections": {}})
    code = probe.main(["--out", str(out)])
    assert code == 0
    assert json.loads(out.read_text())["any_reachable"] is True


def test_main_exit_one_when_unreachable(tmp_path, monkeypatch):
    out = tmp_path / "report.json"
    monkeypatch.setattr(probe, "probe", lambda: {"any_reachable": False, "sections": {}})
    code = probe.main(["--out", str(out)])
    assert code == 1


def test_normalize_cik_pads():
    assert probe.normalize_cik(1137360) == "0001137360"


def test_user_agent_is_nonempty():
    assert probe.user_agent()


def test_http_status_returns_tuple_on_error(monkeypatch):
    def _raise(*args, **kwargs):
        raise probe.urllib.error.URLError("boom")

    monkeypatch.setattr(probe.urllib.request, "urlopen", _raise)
    status, nbytes, head = probe.http_status("https://example.com")
    assert status == 0 and nbytes == 0 and head == b""


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
