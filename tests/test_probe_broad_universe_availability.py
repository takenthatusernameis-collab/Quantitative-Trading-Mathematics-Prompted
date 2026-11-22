"""Tests for ``scripts/probe_broad_universe_availability.py`` (offline, no network).

The probe verifies -- reproducibly -- that a broad, higher-dispersion equity
universe (S&P 500/400/600) is reachable on free data, so a discovery cycle can
*measure* the "universe blocked" claim instead of re-asserting it.  Every network
layer is stubbed here: ``fetch_fn`` stands in for ``urllib.request.urlopen`` (the
reachability + constituent-list HTTP GETs) and ``download_fn`` stands in for
``yf.download`` (the price-coverage leg).  No HTTP request is made and yfinance is
never imported (which would pull in google.protobuf's ``datetime.utcfromtimestamp``
DeprecationWarning under ``-W error``).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "probe_broad_universe_availability.py"

spec = importlib.util.spec_from_file_location("probe_broad_universe_availability", SCRIPT)
assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _series(rows: int) -> pd.DataFrame:
    idx = pd.bdate_range("2022-01-03", periods=rows)
    return pd.DataFrame({"close": range(rows)}, index=idx)


def _fake_fetch(mapping: dict[str, tuple[int, bytes]]):
    """Return a ``fetch_fn(url)`` that serves ``mapping`` by exact/first-substring URL."""

    def _fetch(url: str, timeout: float = 15.0):
        for key, value in mapping.items():
            if key in url:
                return value
        raise AssertionError(f"unexpected URL in test: {url}")

    return _fetch


def _constituents_html(symbols: list[str]) -> bytes:
    rows = "".join(f"<tr><td>{s}</td><td>Security {s}</td></tr>" for s in symbols)
    return f"<table><tr><th>Symbol</th><th>Security</th></tr>{rows}</table>".encode()


# --------------------------------------------------------------------------- #
# _http_get: real User-Agent is sent (the whole point of the probe)
# --------------------------------------------------------------------------- #


class _FakeResponse:
    def __init__(self, payload: bytes, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def test_http_get_sends_user_agent(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["ua"] = req.get_header("User-agent")
        captured["url"] = req.full_url
        return _FakeResponse(b"hello")

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    status, body = mod._http_get("https://example.test/x")
    assert status == 200
    assert body == b"hello"
    # A real, non-default User-Agent must be present, otherwise Yahoo/SEC 429/403.
    assert captured["ua"] and "qtr-research" in captured["ua"]


# --------------------------------------------------------------------------- #
# check_sources
# --------------------------------------------------------------------------- #


def test_check_sources_marks_reachable_and_unreachable():
    mapping = {
        "yahoo": (200, b"{}"),
        "sec": (200, b"{}"),
        "fred": (200, b"DATE,value\n"),
    }

    # A source that raises is recorded as not-ok with a detail, not a crash.
    def fetch(url, timeout=15.0):
        if "fred" in url:
            raise OSError("boom")
        for key, value in mapping.items():
            if key in url:
                return value
        raise AssertionError(url)

    res = mod.check_sources(fetch_fn=fetch)
    assert set(res) == set(mod.SOURCE_PROBES)
    assert all(res[name]["ok"] for name in ("yahoo_chart", "sec_tickers"))
    assert res["fred_csv"]["ok"] is False
    assert "boom" in res["fred_csv"]["detail"]


# --------------------------------------------------------------------------- #
# parse_constituents / _normalize_ticker
# --------------------------------------------------------------------------- #


def test_normalize_ticker_maps_class_shares_and_strips_caret():
    assert mod._normalize_ticker("brk.b") == "BRK-B"
    assert mod._normalize_ticker("bf.b") == "BF-B"
    assert mod._normalize_ticker("^gspc") == "GSPC"
    assert mod._normalize_ticker(" aapl ") == "AAPL"


def test_parse_constituents_extracts_symbol_column_and_dedups():
    html = _constituents_html(["AAPL", "MSFT", "BRK.B", "AAPL"])
    got = mod.parse_constituents(html.decode())
    assert got == ["AAPL", "BRK-B", "MSFT"]  # sorted, deduped, dot->dash


def test_parse_constituents_returns_empty_when_no_symbol_column():
    html = b"<table><tr><th>Name</th></tr><tr><td>x</td></tr></table>"
    assert mod.parse_constituents(html.decode()) == []


# --------------------------------------------------------------------------- #
# fetch_constituents
# --------------------------------------------------------------------------- #


def test_fetch_constituents_reads_all_three_indices():
    html = _constituents_html(["AAPL", "MSFT"])
    res = mod.fetch_constituents(fetch_fn=_fake_fetch({"List_of_S": (200, html)}))
    assert set(res) == {"sp500", "sp400", "sp600"}
    assert all(v == ["AAPL", "MSFT"] for v in res.values())


# --------------------------------------------------------------------------- #
# _sample_tickers: deterministic, spread-out
# --------------------------------------------------------------------------- #


def test_sample_tickers_is_deterministic_and_bounded():
    names = [f"S{i:03d}" for i in range(100)]
    a = mod._sample_tickers(names, 10)
    b = mod._sample_tickers(names, 10)
    assert a == b  # deterministic
    assert len(a) == 10
    assert a == sorted(a)
    # A sample >= universe returns the whole universe.
    assert mod._sample_tickers(names, 100) == sorted(names)


# --------------------------------------------------------------------------- #
# _probe_prices: coverage + transient-empty retry
# --------------------------------------------------------------------------- #


def test_probe_prices_records_coverage():
    def download(ticker, **kwargs):
        return _series(50)

    rows = mod._probe_prices(["A", "B"], download, max_attempts=1, throttle_s=0.0)
    assert rows["A"]["has_data"] is True
    assert rows["A"]["rows"] == 50
    assert rows["A"]["first_date"] == "2022-01-03"


def test_probe_prices_recovers_from_transient_empty():
    calls = {"n": 0}

    def download(ticker, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return pd.DataFrame()  # transient empty on the first attempt
        return _series(10)

    rows = mod._probe_prices(["A"], download, max_attempts=3, throttle_s=0.0)
    assert rows["A"]["has_data"] is True
    assert rows["A"]["attempts"] == 2
    assert rows["A"]["transient_failures"] == 1


def test_probe_prices_records_persistent_miss_after_retries():
    def download(ticker, **kwargs):
        return pd.DataFrame()

    rows = mod._probe_prices(["A"], download, max_attempts=2, throttle_s=0.0)
    assert rows["A"]["has_data"] is False
    assert rows["A"]["attempts"] == 2


# --------------------------------------------------------------------------- #
# _summarize_price_rows
# --------------------------------------------------------------------------- #


def test_summarize_price_rows():
    rows = {
        "A": {"has_data": True, "rows": 100, "transient_failures": 0},
        "B": {"has_data": True, "rows": 200, "transient_failures": 2},
        "C": {"has_data": False, "rows": 0, "transient_failures": 3},
    }
    s = mod._summarize_price_rows(rows)
    assert s["n_sampled"] == 3
    assert s["n_with_data"] == 2
    assert s["frac_with_data"] == pytest.approx(2 / 3)
    assert s["n_recovered_after_transient"] == 1
    assert s["median_rows_per_name"] == 200  # upper median of the two populated rows [100, 200]
    assert s["total_rows"] == 300


# --------------------------------------------------------------------------- #
# main: end-to-end, fully offline, exit codes + artifact
# --------------------------------------------------------------------------- #


def _all_ok_fetch():
    html = _constituents_html(["AAPL", "MSFT", "AMZN", "GOOGL", "META"])
    mapping = {
        "yahoo": (200, b"{}"),
        "sec": (200, b"{}"),
        "fred": (200, b"DATE,value\n"),
        "List_of_S": (200, html),
    }
    return _fake_fetch(mapping)


def test_main_reachable_returns_zero(tmp_path):
    def download(ticker, **kwargs):
        return _series(40)

    artifact = tmp_path / "a.json"
    rc = mod.main(
        ["--sample", "5", "--write-artifact", str(artifact)],
        fetch_fn=_all_ok_fetch(),
        download_fn=download,
    )
    assert rc == 0
    assert artifact.is_file()
    import json

    data = json.loads(artifact.read_text())
    assert data["status"] == "REACHABLE"
    assert data["price_coverage"]["frac_with_data"] == pytest.approx(1.0)
    assert data["universe_size"] == 5


def test_main_low_coverage_returns_nonzero(tmp_path):
    def download(ticker, **kwargs):
        return pd.DataFrame()  # nothing has data

    rc = mod.main(["--sample", "5"], fetch_fn=_all_ok_fetch(), download_fn=download)
    assert rc == 1


def test_main_unreachable_source_returns_nonzero():
    html = _constituents_html(["AAPL"])

    def fetch(url, timeout=15.0):
        if "yahoo" in url:
            raise OSError("blocked")
        if "List_of_S" in url:
            return (200, html)
        return (200, b"{}")

    def download(ticker, **kwargs):
        return _series(10)

    rc = mod.main(["--sample", "3"], fetch_fn=fetch, download_fn=download)
    assert rc == 1
