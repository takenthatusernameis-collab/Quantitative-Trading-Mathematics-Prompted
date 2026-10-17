"""Tests for DataCache and DataFetcher error/parsing paths (no network)."""

from pathlib import Path

import pandas as pd

from qtr.data.fetcher import DataCache, DataFetcher


def test_cache_key_deterministic(tmp_path):
    c = DataCache(cache_dir=tmp_path)
    k1 = c._cache_key("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")
    k2 = c._cache_key("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")
    assert k1 == k2
    assert len(k1) == 16


def test_cache_roundtrip(tmp_path):
    c = DataCache(cache_dir=tmp_path)
    df = pd.DataFrame({"close": [1.0, 2.0]})
    c.set("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d", df)
    got = c.get("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")
    pd.testing.assert_frame_equal(got, df)


def test_cache_miss(tmp_path):
    c = DataCache(cache_dir=tmp_path)
    assert c.get("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d") is None


def test_cache_corrupt_returns_none(tmp_path, monkeypatch):
    c = DataCache(cache_dir=tmp_path)
    key = c._cache_key("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")
    (tmp_path / f"{key}.parquet").write_text("not parquet")
    assert c.get("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d") is None


def test_cache_write_failure_nonfatal(tmp_path, monkeypatch):
    c = DataCache(cache_dir=tmp_path)
    # make cache_dir unwritable by pointing to a file
    bad = tmp_path / "file"
    bad.write_text("x")
    c.cache_dir = bad  # type: ignore[assignment]
    df = pd.DataFrame({"close": [1.0]})
    c.set("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d", df)  # should not raise


def test_fetch_sp500_fallback(monkeypatch):

    def raise_html(*a, **k):
        raise RuntimeError("no network")

    monkeypatch.setattr(pd, "read_html", raise_html)
    fetcher = DataFetcher(cache=DataCache(cache_dir=Path("/tmp/scratchpad") if False else None) or DataCache())
    # use tmp cache dir
    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_sp500_constituents()
    assert res == ["SPY", "IVV", "VOO", "SPLG"]


def test_fetch_yahoo_empty_result(monkeypatch):
    # mock yfinance Ticker to return empty history
    import sys
    import types

    class FakeTicker:
        def history(self, **kw):
            return pd.DataFrame()

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_yahoo(["SPY"], "2020-01-01", "2020-02-01", use_cache=False)
    assert res["SPY"].empty


def test_fetch_ccxt_missing_module(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "ccxt", None)
    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False)
    assert res == {}


def test_futures_symbol_warning_does_not_fail(monkeypatch):
    import sys
    import types

    class FakeTicker:
        def history(self, **kw):
            return pd.DataFrame()

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_futures(["ES"], "2020-01-01", "2020-02-01", use_cache=False)
    assert res["ES"].empty
