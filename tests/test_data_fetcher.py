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


def test_fetcher_ccxt_rejects_the_pre_fix_interval_forwarding(monkeypatch, tmp_path):
    """Negative control: the pre-fix dispatch forwarded ``interval`` into the
    CCXT branch's ``timeframe`` slot, so a default call requested ``"1d"``
    bars where ``fetch_ccxt``'s own default is ``"1h"``. Reconstructing that
    forwarding must produce a *different* call than the corrected dispatcher,
    otherwise the contract would not have caught the defect.
    """
    from qtr.data import fetcher

    rows = [[1577836800000, 1.0, 2.0, 0.5, 1.5, 100.0]]
    sink: dict = {}
    # The dispatcher uses the singleton fetcher, which caches CCXT exchange
    # instances across calls; a prior test may have cached a different stub
    # under "binance", so the cache must be cleared for the recording stub
    # to be picked up.
    from qtr.data.fetcher import get_data_fetcher

    get_data_fetcher()._ccxt_exchanges.clear()

    # The corrected dispatcher forwards its own ``timeframe`` default ("1h").
    _install_recording_ccxt(monkeypatch, rows, sink)
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
    import qtr.data.fetcher as fetcher_mod

    def raise_html(*a, **k):
        raise RuntimeError("no network")

    monkeypatch.setattr(pd, "read_html", raise_html)
    # ensure we use a fresh fetcher instance
    if hasattr(fetcher_mod, "get_data_fetcher") and hasattr(fetcher_mod.get_data_fetcher, "_instance"):
        del fetcher_mod.get_data_fetcher._instance
    res = fetcher_mod.fetch_sp500_constituents()
    assert res == ["SPY", "IVV", "VOO", "SPLG"]
