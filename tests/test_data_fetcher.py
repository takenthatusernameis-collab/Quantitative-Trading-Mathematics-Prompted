"""Tests for DataCache and DataFetcher error/parsing paths (no network)."""

from pathlib import Path

import pandas as pd
import pytest

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


def test_cache_set_strips_a_tz_aware_index_before_writing(tmp_path):
    """A frame written with a tz-aware index is stored tz-naive (§H58).

    The cache layer canonicalizes the index on the way out, so every fetch
    method's cache-hit path can assume a tz-naive index and need not
    re-normalize it. Without this guard a tz-aware frame would be written
    through verbatim and the tz-aware branch of every cache-hit path would
    have to fire later to correct it -- the four now-removed normalization
    blocks in ``fetch_yahoo`` / ``fetch_futures`` / ``fetch_ccxt``.
    """
    aware = pd.DataFrame(
        {"close": [1.0, 2.0]},
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]).tz_localize("America/New_York"),
    )
    c = DataCache(cache_dir=tmp_path)
    c.set("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d", aware)
    on_disk = pd.read_parquet(
        tmp_path / f"{c._cache_key('yahoo', 'SPY', '2020-01-01', '2020-02-01', '1d')}.parquet"
    )
    assert on_disk.index.tz is None
    # The round-trip is the tz-naive frame, not the tz-aware one: the cache
    # canonicalizes on the way out, so what comes back is the stripped version.
    stripped = aware.copy()
    stripped.index = pd.to_datetime(stripped.index).tz_localize(None)
    pd.testing.assert_frame_equal(
        c.get("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d"), stripped, check_names=False
    )


def test_cache_get_strips_tz_on_read(tmp_path):
    """Reading a tz-aware parquet from disk strips the timezone (fetcher.py:92-94).

    ``DataCache.set`` canonicalizes to tz-naive before writing, so a frame
    written through the normal path is already tz-naive on disk. But an
    external process -- or a stale cache file from an older writer -- could
    leave a tz-aware parquet in the cache directory. The read path must strip
    it so every caller can assume a tz-naive index.
    """
    c = DataCache(cache_dir=tmp_path)
    aware = pd.DataFrame(
        {"close": [1.0, 2.0]},
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]).tz_localize("America/New_York"),
    )
    key = c._cache_key("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")
    (tmp_path / f"{key}.parquet").write_bytes(aware.to_parquet())

    got = c.get("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")
    assert got.index.tz is None
    stripped = aware.copy()
    stripped.index = pd.to_datetime(stripped.index).tz_localize(None)
    pd.testing.assert_frame_equal(got, stripped, check_names=False)


def _install_flaky_tz_localize(monkeypatch):
    """Patch ``DatetimeIndex.tz_localize`` to raise once, then delegate.

    The first call simulates a pandas version where ``tz_localize(None)``
    fails on a tz-aware index; the second call succeeds, exercising the
    defensive ``pd.to_datetime(df.index).tz_localize(None)`` fallback in
    ``DataCache.get`` (fetcher.py:97-98) and ``DataCache.set`` (fetcher.py:121-122).
    """
    calls = {"n": 0}
    original = pd.DatetimeIndex.tz_localize

    def flaky(self, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("simulated tz_localize failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pd.DatetimeIndex, "tz_localize", flaky)
    return calls


def test_cache_get_tz_localize_fallback(tmp_path, monkeypatch):
    """The read path falls back to ``pd.to_datetime`` when ``tz_localize`` raises."""
    c = DataCache(cache_dir=tmp_path)
    aware = pd.DataFrame(
        {"close": [1.0, 2.0]},
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]).tz_localize("America/New_York"),
    )
    key = c._cache_key("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")
    (tmp_path / f"{key}.parquet").write_bytes(aware.to_parquet())

    # Return the tz-aware frame directly from read_parquet so no tz_localize
    # call is consumed during the read itself; the first tz_localize(None)
    # must be the one inside the inner try (fetcher.py:95).
    monkeypatch.setattr(pd, "read_parquet", lambda *a, **k: aware)

    calls = _install_flaky_tz_localize(monkeypatch)
    got = c.get("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")

    assert got is not None
    assert got.index.tz is None
    # First call raised (entered the except branch), second call succeeded.
    assert calls["n"] == 2


def test_cache_set_tz_localize_fallback(tmp_path, monkeypatch):
    """The write path falls back to ``pd.to_datetime`` when ``tz_localize`` raises."""
    c = DataCache(cache_dir=tmp_path)
    aware = pd.DataFrame(
        {"close": [1.0, 2.0]},
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]).tz_localize("America/New_York"),
    )

    calls = _install_flaky_tz_localize(monkeypatch)
    c.set("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d", aware)

    key = c._cache_key("yahoo", "SPY", "2020-01-01", "2020-02-01", "1d")
    on_disk = pd.read_parquet(tmp_path / f"{key}.parquet")
    assert on_disk.index.tz is None
    # First call raised (entered the except branch), second call succeeded.
    assert calls["n"] == 2


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
        cache=DataCache(cache_dir=Path("/tmp/scratchpad") if False else None) or DataCache()
    )
    # use tmp cache dir
    import tempfile

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_sp500_constituents()
    assert res == ["SPY", "IVV", "VOO", "SPLG"]


def test_fetch_sp500_constituents_rejects_date(tmp_path):
    """A historical ``date`` must raise loudly instead of returning the
    current list (which would introduce survivorship bias)."""
    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    with pytest.raises(ValueError, match="point-in-time lookup"):
        fetcher.fetch_sp500_constituents(date="2020-01-01")


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
    # lines 214 (missing column warning) and 222 (futures cache write).
    # A vendor panel that omits every required column is NOT an empty
    # result: the pre-fix selection raised ``KeyError`` inside the fetch
    # loop, the broad ``except Exception`` swallowed it, and the symbol was
    # returned as an empty frame with an error log -- a silent void of the
    # class the H53-H61 audits exist to catch. The corrected selection
    # returns the panel over the columns the vendor actually carried.
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
    assert list(res["ES=F"].columns) == ["close"]
    assert len(res["ES=F"]) == 1
    # ... and the corrected panel is what gets cached and returned on the
    # cache-hit path (no second yfinance call).
    res2 = fetcher.fetch_futures(["ES=F"], "2020-01-01", "2020-02-01", use_cache=True)
    pd.testing.assert_frame_equal(res2["ES=F"], res["ES=F"], check_names=False)


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
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False)
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
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=True)
    assert len(res["BTC/USDT"]) == 2
    # cache should now be populated
    res2 = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=True)
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
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False)
    assert res["BTC/USDT"].empty


def test_fetch_sp500_success(monkeypatch):
    import tempfile

    import pandas as pd

    df = pd.DataFrame({"Symbol": ["AAPL", "MSFT"]})
    monkeypatch.setattr(pd, "read_html", lambda url: [df])
    fetcher = DataFetcher(cache=DataCache(cache_dir=Path(tempfile.mkdtemp())))
    res = fetcher.fetch_sp500_constituents()
    assert res == ["AAPL", "MSFT"]


class TestSp500SymbolSanitization:
    """The Wikipedia Symbol column carries class-share dots that must be
    stripped as LITERAL characters, not as a regex pattern.

    In pandas 2.x ``Series.str.replace`` defaulted to ``regex=True``, so a
    bare ``"."`` was the "any character" pattern and turned every class-share
    ticker (BRK.B, BF.B, GOOGL.A, ...) into a string of dashes. The committed
    fixture had no dotted ticker, so the three existing tests could not see
    it: they asserted ``["AAPL", "MSFT"]`` -> ``["AAPL", "MSFT"]`` either way.
    The fix pins ``regex=False`` explicitly, which is correct under both the
    2.x default (where it changes behaviour) and the 3.x default (where it is
    a no-op but keeps the code honest against the documented contract).
    """

    @staticmethod
    def _panel(symbols: list[str]) -> pd.DataFrame:
        return pd.DataFrame({"Symbol": symbols})

    def test_dotted_class_share_tickers_are_preserved(self, monkeypatch):
        import tempfile

        df = self._panel(["BRK.B", "BF.B", "GOOGL", "AAPL", "MSFT", "A.B.C"])
        monkeypatch.setattr(pd, "read_html", lambda url: [df])
        fetcher = DataFetcher(cache=DataCache(cache_dir=Path(tempfile.mkdtemp())))
        res = fetcher.fetch_sp500_constituents()
        assert res == ["BRK-B", "BF-B", "GOOGL", "AAPL", "MSFT", "A-B-C"]

    def test_the_contract_rejects_the_regex_default(self, monkeypatch):
        """Behavioural negative control: the pre-fix construction relied on
        the pandas-2.x default of ``regex=True``, so a bare ``"."`` was the
        "any character" pattern and mangled every dotted ticker. The corrected
        sanitization must not reproduce that mangling.
        """
        import tempfile

        df = self._panel(["BRK.B", "BF.B", "GOOGL", "AAPL", "MSFT"])
        monkeypatch.setattr(pd, "read_html", lambda url: [df])
        fetcher = DataFetcher(cache=DataCache(cache_dir=Path(tempfile.mkdtemp())))
        res = fetcher.fetch_sp500_constituents()

        pre_fix = df["Symbol"].str.replace(".", "-", regex=True).tolist()
        assert pre_fix == ["-----", "----", "-----", "----", "----"], (
            "the negative control must reconstruct the regex mangling"
        )
        assert res != pre_fix, "the corrected sanitization must not reproduce the regex mangling"
        assert res == ["BRK-B", "BF-B", "GOOGL", "AAPL", "MSFT"]


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
    # line 131: a vendor panel that omits required columns must degrade, not
    # raise. The pre-fix selection raised ``KeyError`` inside the fetch loop,
    # the broad ``except Exception`` swallowed it, and the symbol came back
    # as an empty frame -- a silent void, the class the H53-H61 audits exist
    # to catch. The corrected selection returns the panel over the columns
    # the vendor actually carried.
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
    assert list(res["SPY"].columns) == ["close"]
    assert len(res["SPY"]) == 1


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
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=True)
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
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False)
    assert res["BTC/USDT"].empty


def test_fetch_ccxt_keeps_required_column_order(tmp_path, monkeypatch):
    """A complete CCXT panel returns its columns in the required order.

    Mirrors ``test_fetch_keeps_extras_and_orders_present_required_first`` for
    ``fetch_yahoo`` / ``fetch_futures``: the ``present + extras`` selection in
    ``fetch_ccxt`` (fetcher.py:453-460) must not scramble a complete panel into
    a different column order, and must not drop a required column. CCXT builds
    its own frame from ohlcv rows, so a missing-required-column scenario is not
    reachable through this path; this test pins that a complete panel survives
    the defensive selection bit-identically ordered.
    """
    import sys
    import tempfile
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

    d = Path(tempfile.mkdtemp())
    fetcher = DataFetcher(cache=DataCache(cache_dir=d))
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False)
    assert list(res["BTC/USDT"].columns) == ["open", "high", "low", "close", "volume"]
    assert len(res["BTC/USDT"]) == 2


def test_get_data_fetcher_singleton():
    from qtr.data.fetcher import get_data_fetcher

    a = get_data_fetcher()
    b = get_data_fetcher()
    assert a is b


# --------------------------------------------------------------------------- #
# The public ``fetcher()`` dispatch entry point (H65)
# --------------------------------------------------------------------------- #
def _install_fake_yahoo(monkeypatch, df: pd.DataFrame) -> None:
    """Install a yfinance stub whose Ticker always returns ``df``."""
    import sys
    import types

    class FakeTicker:
        def history(self, **kw):
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)


def _install_fake_ccxt(monkeypatch, rows: list[list]) -> None:
    import sys
    import types

    class FakeExchange:
        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            return rows

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: FakeExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)


def test_fetcher_dispatches_to_fetch_yahoo(monkeypatch, tmp_path):
    """``fetcher("yahoo", ...)`` must be the same call as ``fetch_yahoo``."""
    from qtr.data import fetcher

    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.to_datetime(["2020-01-02"]),
    )
    _install_fake_yahoo(monkeypatch, df)

    direct = DataFetcher(cache=DataCache(cache_dir=tmp_path)).fetch_yahoo(
        ["SPY"], "2020-01-01", "2020-02-01", use_cache=False
    )
    dispatched = fetcher("yahoo", ["SPY"], "2020-01-01", "2020-02-01", use_cache=False)
    assert "close" in dispatched["SPY"].columns
    pd.testing.assert_frame_equal(dispatched["SPY"], direct["SPY"], check_names=False)


def test_fetcher_dispatches_to_fetch_futures(monkeypatch, tmp_path):
    """``fetcher("yahoo_futures", ...)`` must be the same call as ``fetch_futures``."""
    from qtr.data import fetcher

    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [100]},
        index=pd.to_datetime(["2020-01-02"]),
    )
    _install_fake_yahoo(monkeypatch, df)

    direct = DataFetcher(cache=DataCache(cache_dir=tmp_path)).fetch_futures(
        ["ES=F"], "2020-01-01", "2020-02-01", use_cache=False
    )
    dispatched = fetcher("yahoo_futures", ["ES=F"], "2020-01-01", "2020-02-01", use_cache=False)
    assert "close" in dispatched["ES=F"].columns
    pd.testing.assert_frame_equal(dispatched["ES=F"], direct["ES=F"], check_names=False)


def test_fetcher_dispatches_to_fetch_ccxt(monkeypatch, tmp_path):
    """``fetcher("ccxt", ..., exchange_id="binance")`` must be the same call as ``fetch_ccxt``.

    Both sides are called with an explicit ``timeframe`` so the test pins the
    *forwarding* of the argument rather than the default: the dispatcher's
    default is ``"1h"`` (matching ``fetch_ccxt``'s own default), and a test
    that left it at the dispatcher's default would not notice the dispatcher
    forwarding its ``interval`` default into the CCXT branch instead -- see
    ``test_fetcher_ccxt_default_timeframe_matches_fetch_ccxt``.
    """
    from qtr.data import fetcher

    rows = [[1577836800000, 1.0, 2.0, 0.5, 1.5, 100.0]]
    _install_fake_ccxt(monkeypatch, rows)

    direct = DataFetcher(cache=DataCache(cache_dir=tmp_path)).fetch_ccxt(
        "binance", ["BTC/USDT"], "2020-01-01", "2020-02-01", "1d", use_cache=False
    )
    dispatched = fetcher(
        "ccxt",
        ["BTC/USDT"],
        "2020-01-01",
        "2020-02-01",
        use_cache=False,
        exchange_id="binance",
        timeframe="1d",
    )
    assert "BTC/USDT" in dispatched
    pd.testing.assert_frame_equal(dispatched["BTC/USDT"], direct["BTC/USDT"], check_names=False)


def _install_recording_ccxt(monkeypatch, rows: list[list], sink: dict) -> None:
    """Install a CCXT stub that records the ``timeframe`` it was called with."""
    import sys
    import types

    class RecordingExchange:
        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            sink["timeframe"] = timeframe
            return rows

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: RecordingExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)


def test_fetcher_ccxt_default_timeframe_matches_fetch_ccxt(monkeypatch, tmp_path):
    """A default-argument ``fetcher("ccxt", ...)`` call is the same call as
    ``fetch_ccxt(...)`` with its own defaults.

    The dispatcher's CCXT branch used to forward its ``interval`` parameter
    (default ``"1d"``) into ``fetch_ccxt``'s ``timeframe`` slot, whose own
    default is ``"1h"``. The dispatch-equality test above passed only because
    the fake exchange ignores the ``timeframe`` argument, so a caller using
    defaults would have requested hourly bars as daily ones and the
    "same call" claim would have been false. The dispatcher now carries its
    own ``timeframe`` default of ``"1h"`` and forwards that.
    """
    from qtr.data import fetcher

    rows = [[1577836800000, 1.0, 2.0, 0.5, 1.5, 100.0]]
    sink: dict = {}
    _install_recording_ccxt(monkeypatch, rows, sink)
    # The dispatcher uses the singleton fetcher, which caches CCXT exchange
    # instances across calls; a prior test may have cached a different stub
    # under "binance", so the cache must be cleared for the recording stub
    # to be picked up.
    from qtr.data.fetcher import get_data_fetcher

    get_data_fetcher()._ccxt_exchanges.clear()

    # The corrected dispatcher forwards its own ``timeframe`` default ("1h").
    fetcher(
        "ccxt",
        ["BTC/USDT"],
        "2020-01-01",
        "2020-02-01",
        use_cache=False,
        exchange_id="binance",
    )
    corrected_default = sink["timeframe"]

    # The pre-fix form forwarded the dispatcher's ``interval`` default ("1d")
    # into the CCXT branch. Re-run it by passing that value explicitly.
    sink.clear()
    get_data_fetcher()._ccxt_exchanges.clear()
    fetcher(
        "ccxt",
        ["BTC/USDT"],
        "2020-01-01",
        "2020-02-01",
        use_cache=False,
        exchange_id="binance",
        timeframe="1d",
    )
    pre_fix_default = sink["timeframe"]

    assert corrected_default == "1h"
    assert pre_fix_default == "1d"
    assert corrected_default != pre_fix_default


def test_fetcher_ccxt_requires_exchange_id(tmp_path):
    """CCXT has no default exchange: calling without ``exchange_id`` must raise
    rather than silently return an empty dict (every fetch method logs and
    continues on a per-symbol failure, so a misspelled or omitted argument
    would otherwise be invisible)."""
    from qtr.data import fetcher

    with pytest.raises(ValueError, match="exchange_id"):
        fetcher("ccxt", ["BTC/USDT"], "2020-01-01", "2020-02-01", use_cache=False)


@pytest.mark.parametrize("bad", ["yahoo_future", "YAHOO", "yfinance", "", "ccx", "binance"])
def test_fetcher_rejects_unknown_source(bad, tmp_path):
    """A typo in ``source`` must raise a named ``ValueError``.

    The dispatch is explicit rather than a ``getattr`` on the fetcher exactly
    so this cannot silently return an empty dict: every fetch method treats a
    per-symbol failure as non-fatal and logs it, so a misspelled method name
    would be indistinguishable from a symbol that genuinely had no data.
    """
    from qtr.data import fetcher

    with pytest.raises(ValueError, match="unknown data source"):
        fetcher(bad, ["SPY"], "2020-01-01", "2020-02-01", use_cache=False)


def test_fetcher_is_exported_from_the_data_package():
    """The dispatch entry point is part of the public data surface."""
    import qtr.data as data

    assert "fetcher" in data.__all__
    assert data.fetcher is not None
    # ... and reachable through the top-level star export too.
    namespace: dict = {}
    exec("from qtr import *", namespace)  # noqa: S102
    assert "fetcher" in namespace


def test_fetch_sp500_constituents_module_level(tmp_path, monkeypatch):
    import sys

    fetcher_mod = sys.modules["qtr.data.fetcher"]

    def raise_html(*a, **k):
        raise RuntimeError("no network")

    monkeypatch.setattr(pd, "read_html", raise_html)
    # ensure we use a fresh fetcher instance
    if hasattr(fetcher_mod, "get_data_fetcher") and hasattr(
        fetcher_mod.get_data_fetcher, "_instance"
    ):
        del fetcher_mod.get_data_fetcher._instance
    res = fetcher_mod.fetch_sp500_constituents()
    assert res == ["SPY", "IVV", "VOO", "SPLG"]


# --------------------------------------------------------------------------- #
# H75 -- a vendor that omits a required column must not crash the fetch
# --------------------------------------------------------------------------- #
def _fake_yf_returning(df):
    import sys
    import types

    class FakeTicker:
        def history(self, **kw):
            return df

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = lambda s: FakeTicker()
    sys.modules["yfinance"] = fake_yf
    return fake_yf


@pytest.mark.parametrize("method", ["fetch_yahoo", "fetch_futures"])
def test_fetch_does_not_crash_when_volume_is_missing(method, tmp_path, monkeypatch):
    """A vendor panel that omits ``volume`` must degrade, not raise.

    The column selection used to be ``df[required + extras]`` with
    ``required = ["open", "high", "low", "close", "volume"]`` built as a
    *literal* list, so a frame missing any one of the five raised
    ``KeyError`` inside the fetch loop. A real yfinance response that omits
    ``volume`` (or any other required column) is a fact about the source,
    not an exception: the fetch logs the warning the code already carries and
    returns the panel over the columns it actually has. The engine treats a
    missing volume column as zero volume in the impact model, so the
    downstream behaviour is unchanged for panels that carry it.
    """
    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5]},
        index=pd.to_datetime(["2020-01-02"]),
    )
    _fake_yf_returning(df)

    res = getattr(fetcher, method)(["SPY"], "2020-01-01", "2020-02-01", use_cache=False)
    assert "close" in res["SPY"].columns
    assert "volume" not in res["SPY"].columns
    assert len(res["SPY"]) == 1


@pytest.mark.parametrize("method", ["fetch_yahoo", "fetch_futures"])
def test_fetch_keeps_extras_and_orders_present_required_first(method, tmp_path, monkeypatch):
    """The selection re-orders the vendor's columns over the ones present.

    The order is ``[present required columns] + [extras]`` -- the same order
    the literal-list form produced for a complete panel, so a complete panel
    is bit-identical to before and an incomplete one keeps whatever extra
    columns the vendor returned (``adj_close`` etc.).
    """
    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    df = pd.DataFrame(
        {
            "Adj Close": [1.5],
            "Open": [1.0],
            "High": [2.0],
            "Low": [0.5],
            "Close": [1.5],
            "Volume": [100],
        },
        index=pd.to_datetime(["2020-01-02"]),
    )
    _fake_yf_returning(df)

    res = getattr(fetcher, method)(["SPY"], "2020-01-01", "2020-02-01", use_cache=False)
    cols = list(res["SPY"].columns)
    assert cols[:5] == ["open", "high", "low", "close", "volume"]
    assert "adj_close" in cols


@pytest.mark.parametrize("method", ["fetch_yahoo", "fetch_futures"])
def test_fetch_missing_required_column_warns_but_does_not_raise(method, tmp_path, monkeypatch):
    """The existing ``Missing column`` warning must still fire for each gap.

    ``loguru`` does not propagate to the stdlib logging module, so the
    warning is captured through loguru's own sink rather than ``caplog``.
    """
    from loguru import logger

    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5]},
        index=pd.to_datetime(["2020-01-02"]),
    )
    _fake_yf_returning(df)

    messages: list[str] = []
    handler_id = logger.add(messages.append, level="WARNING")
    try:
        getattr(fetcher, method)(["SPY"], "2020-01-01", "2020-02-01", use_cache=False)
        assert any("Missing column volume" in m for m in messages)
    finally:
        logger.remove(handler_id)


def test_fetch_missing_required_column_pre_fix_form_raises(tmp_path, monkeypatch):
    """Behavioural negative control: the literal-list selection still crashes.

    Reconstructs the pre-fix selection over a volume-less frame and requires
    it to raise ``KeyError``, proving the corrected selection is what makes
    the fetch safe rather than merely lucky.
    """
    df = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5]},
        index=pd.to_datetime(["2020-01-02"]),
    )
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    required = ["open", "high", "low", "close", "volume"]
    with pytest.raises(KeyError):
        df[required + [c for c in df.columns if c not in required]]


def test_fetch_ccxt_does_not_crash_when_volume_is_missing(tmp_path, monkeypatch):
    """A CCXT panel that omits a required column must degrade, not raise."""
    import sys
    import types

    class FakeExchange:
        def __init__(self):
            self.calls = 0

        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            self.calls += 1
            if self.calls == 1:
                return [
                    [1577836800000 + 86400000, 1.0, 2.0, 0.5, 1.5],  # missing volume, advanced
                ]
            return []

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: FakeExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-01-03", use_cache=False)
    assert "close" in res["BTC/USDT"].columns
    assert "volume" not in res["BTC/USDT"].columns
    assert len(res["BTC/USDT"]) == 1


def test_fetch_ccxt_missing_required_column_warns_but_does_not_raise(tmp_path, monkeypatch):
    from loguru import logger

    import sys
    import types

    class FakeExchange:
        def __init__(self):
            self.calls = 0

        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
            self.calls += 1
            if self.calls == 1:
                return [
                    [1577836800000 + 86400000, 1.0, 2.0, 0.5, 1.5],
                ]
            return []

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = lambda cfg: FakeExchange()
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
    messages: list[str] = []
    handler_id = logger.add(messages.append, level="WARNING")
    try:
        res = fetcher.fetch_ccxt("binance", ["BTC/USDT"], "2020-01-01", "2020-01-03", use_cache=False)
        assert any("Missing column volume" in m for m in messages)
        assert "close" in res["BTC/USDT"].columns
    finally:
        logger.remove(handler_id)
