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
    fetcher = DataFetcher(
        cache=DataCache(cache_dir=Path("/tmp/scratchpad") if False else None)
        or DataCache()
    )
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
    res = fetcher.fetch_ccxt(
        "binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False
    )
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


def test_fetch_yahoo_success_and_cache(monkeypatch):
    import sys
    import types

    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.to_datetime(["2020-01-02"]),
    )

    class FakeTicker:
        def history(self, **kw):
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_yahoo(["SPY"], "2020-01-01", "2020-02-01", use_cache=False)
    assert "close" in res["SPY"].columns
    assert "open" in res["SPY"].columns
    assert res["SPY"].index.tz is None
    # second call hits the cache
    res2 = fetcher.fetch_yahoo(["SPY"], "2020-01-01", "2020-02-01", use_cache=True)
    assert len(res2["SPY"]) == 1
    pd.testing.assert_frame_equal(res2["SPY"], res["SPY"], check_names=False)


def test_fetch_yahoo_fetch_exception_returns_empty(monkeypatch):
    import sys
    import types

    class BadTicker:
        def history(self, **kw):
            raise RuntimeError("boom")

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: BadTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_yahoo(["BAD"], "2020-01-01", "2020-02-01", use_cache=False)
    assert res["BAD"].empty


def test_fetch_futures_success(monkeypatch):
    import sys
    import types

    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.to_datetime(["2020-01-02"]),
    )

    class FakeTicker:
        def history(self, **kw):
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_futures(["ES=F"], "2020-01-01", "2020-02-01", use_cache=True)
    assert "close" in res["ES=F"].columns
    # cache write (line 222) populated; second call hits the cache
    res2 = fetcher.fetch_futures(["ES=F"], "2020-01-01", "2020-02-01", use_cache=True)
    pd.testing.assert_frame_equal(res2["ES=F"], res["ES=F"], check_names=False)


def test_fetch_futures_missing_column_and_cache(monkeypatch):
    # lines 214 (missing column warning) and 222 (futures cache write)
    import sys
    import types

    df = pd.DataFrame(
        {"close": [1.0]},  # missing open/high/low/volume
        index=pd.to_datetime(["2020-01-02"]),
    )

    class FakeTicker:
        def history(self, **kw):
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_futures(["ES=F"], "2020-01-01", "2020-02-01", use_cache=True)
    assert res["ES=F"].empty  # required columns all missing -> empty result


def test_fetch_ccxt_success(monkeypatch):
    import sys
    import types

    class FakeExchange:
        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            return [
                [1577836800000, 1.0, 2.0, 0.5, 1.5, 100.0],
                [1577923200000, 1.5, 2.5, 1.0, 2.0, 120.0],
            ]

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: FakeExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_ccxt(
        "binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False
    )
    assert "BTC/USDT" in res
    assert len(res["BTC/USDT"]) == 2
    assert "close" in res["BTC/USDT"].columns


def test_fetch_ccxt_success_with_cache(monkeypatch):
    # line 318: ccxt cache write path
    import sys
    import types

    class FakeExchange:
        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            return [
                [1577836800000, 1.0, 2.0, 0.5, 1.5, 100.0],
                [1577923200000, 1.5, 2.5, 1.0, 2.0, 120.0],
            ]

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: FakeExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_ccxt(
        "binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=True
    )
    assert len(res["BTC/USDT"]) == 2
    # cache should now be populated
    res2 = fetcher.fetch_ccxt(
        "binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=True
    )
    pd.testing.assert_frame_equal(res2["BTC/USDT"], res["BTC/USDT"], check_names=False)


def test_fetch_ccxt_fetch_exception_returns_empty(monkeypatch):
    import sys
    import types

    class BadExchange:
        def fetch_ohlcv(self, *a, **k):
            raise RuntimeError("network down")

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: BadExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_ccxt(
        "binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False
    )
    assert res["BTC/USDT"].empty


def test_fetch_sp500_success(monkeypatch):
    import tempfile

    import pandas as pd

    df = pd.DataFrame({"Symbol": ["AAPL", "MSFT"]})
    monkeypatch.setattr(pd, "read_html", lambda url: [df])
    fetcher = DataFetcher(cache=DataCache(cache_dir=Path(tempfile.mkdtemp())))
    res = fetcher.fetch_sp500_constituents()
    assert res == ["AAPL", "MSFT"]


def test_fetch_yahoo_cache_hit(monkeypatch):
    # lines 103-104: cache hit short-circuits the yfinance call
    import sys
    import types

    df = pd.DataFrame(
        {"close": [9.0]},
        index=pd.to_datetime(["2020-01-02"]),
    )

    class NeverCalled:
        def history(self, **kw):
            raise AssertionError("should not be called on cache hit")

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: NeverCalled()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    cache = DataCache(cache_dir=d)
    cache.set("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d", df)
    fetcher = DataFetcher(cache=cache)
    res = fetcher.fetch_yahoo(["SPY"], "2020-01-01", "2020-02-01", use_cache=True)
    pd.testing.assert_frame_equal(res["SPY"], df, check_names=False)


def test_fetch_yahoo_missing_column(monkeypatch):
    # line 131: missing required column triggers a warning but does not raise
    import sys
    import types

    df = pd.DataFrame(
        {"close": [1.0]},  # only close, missing open/high/low/volume
        index=pd.to_datetime(["2020-01-02"]),
    )

    class FakeTicker:
        def history(self, **kw):
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_yahoo(["SPY"], "2020-01-01", "2020-02-01", use_cache=False)
    assert res["SPY"].empty  # required columns all missing -> empty result


def test_fetch_futures_cache_hit(monkeypatch):
    # lines 184-187: futures cache hit short-circuits the yfinance call
    import sys
    import types

    df = pd.DataFrame({"close": [7.0]}, index=pd.to_datetime(["2020-01-02"]))

    class NeverCalled:
        def history(self, **kw):
            raise AssertionError("should not be called on cache hit")

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: NeverCalled()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    cache = DataCache(cache_dir=d)
    cache.set("yahoo_futures", "ES=F", "2020-01-01", "2020-02-01", "1d", df)
    fetcher = DataFetcher(cache=cache)
    res = fetcher.fetch_futures(["ES=F"], "2020-01-01", "2020-02-01", use_cache=True)
    pd.testing.assert_frame_equal(res["ES=F"], df, check_names=False)


def test_fetch_futures_fetch_exception_returns_empty(monkeypatch):
    # lines 224-226: futures per-symbol fetch failure is non-fatal
    import sys
    import types

    class BadTicker:
        def history(self, **kw):
            raise RuntimeError("futures down")

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: BadTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_futures(["ES=F"], "2020-01-01", "2020-02-01", use_cache=False)
    assert res["ES=F"].empty


def test_fetch_ccxt_cache_hit(monkeypatch):
    # lines 279-284: ccxt cache hit short-circuits the exchange call
    import sys
    import types

    df = pd.DataFrame({"close": [1.0]}, index=pd.to_datetime(["2020-01-02"]))

    class NeverCalled:
        def fetch_ohlcv(self, *a, **k):
            raise AssertionError("should not be called on cache hit")

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: NeverCalled()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    import tempfile

    d = Path(tempfile.mkdtemp())
    cache = DataCache(cache_dir=d)
    cache.set("ccxt", "binance:BTC_USDT", "2020-01-01", "2020-02-01", "1h", df)
    fetcher = DataFetcher(cache=cache)
    res = fetcher.fetch_ccxt(
        "binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=True
    )
    pd.testing.assert_frame_equal(res["BTC/USDT"], df, check_names=False)


def test_fetch_ccxt_no_ohlcv(monkeypatch):
    # lines 301-304: empty ohlcv list yields an empty DataFrame
    import sys
    import types

    class EmptyExchange:
        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            return []

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: EmptyExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_ccxt(
        "binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False
    )
    assert res["BTC/USDT"].empty


def test_get_data_fetcher_singleton():
    from qtr.data.fetcher import get_data_fetcher

    a = get_data_fetcher()
    b = get_data_fetcher()
    assert a is b
