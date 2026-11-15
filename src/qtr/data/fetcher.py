"""
Data fetching module for quantitative trading research.

Supports:
- Yahoo Finance (equities, ETFs) via yfinance
- Crypto exchanges via CCXT
- Futures continuous contracts via yfinance =F tickers
"""

import hashlib
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger

from qtr.utils.config import config_path, get_config

PRICE_COLUMNS = ("open", "high", "low", "close")


def non_positive_prices(panel: pd.DataFrame) -> pd.DataFrame:
    """Every non-positive price in a price panel.

    A price of zero or less cannot be the base of a percentage return, and a
    price that *changes sign* cannot be the base of one either: the return
    from a negative base inverts the sign of the price move.  Both are
    silently catastrophic downstream -- ``prices.pct_change()`` turns a
    ``-37.63`` close into a ``-305.97%`` single-bar return -- so the screen
    is applied at the point where the data enters the pipeline rather than
    where it is finally noticed.

    The WTI front-month contract of 2020-04-20 is the canonical case: the
    expiring contract printed ``-37.63`` and the continuous Yahoo series
    splices it in front of the next contract, which makes the one-bar return
    of the *next* bar ``-126.60%`` as well.

    Every price column is screened, not only the close.  The same splice
    printed ``-14.0`` as the *open* of the next session -- on a session
    whose close was positive -- and a non-positive open is just as
    unusable: it is a negative fill price, and a roll gap computed from it
    inverts the sign of the price move.

    Args:
        panel: A price frame.  A long frame (the ``open``/``high``/``low``/
            ``close`` columns of a fetched quote) is screened column by
            column over its price columns; a wide frame (one column per
            symbol) is screened column by column over every column.

    Returns:
        A DataFrame with columns ``symbol``, ``timestamp`` and ``price``,
        one row per offending observation.  Empty when the panel is clean.
    """
    if panel is None or len(panel) == 0 or len(panel.columns) == 0:
        return pd.DataFrame(columns=["symbol", "timestamp", "price"])

    price_columns = [column for column in PRICE_COLUMNS if column in panel.columns]

    rows = []
    if price_columns:
        # ``panel[column]`` returns a DataFrame (not a Series) when ``column``
        # is a duplicated label, and ``pd.to_numeric`` on a DataFrame raises
        # ``TypeError: arg must be a list, tuple, 1-d array, or Series``.  A
        # duplicated column label is reachable from the documented pipeline:
        # a wide panel built with ``pd.concat(..., axis=1)`` from two frames
        # that share a symbol name, or a cached/vendor frame written with a
        # repeated column.  Screen by position so every column is a Series
        # regardless of how many labels share its name; the ``PRICE_COLUMNS``
        # order is preserved so the offending-observation order is unchanged.
        for column in price_columns:
            for position, label in enumerate(panel.columns):
                if label != column:
                    continue
                values = pd.to_numeric(panel.iloc[:, position], errors="coerce")
                bad = values[(values <= 0) & values.notna()]
                for timestamp, price in bad.items():
                    rows.append((str(column), timestamp, float(price)))
    else:
        for position, label in enumerate(panel.columns):
            values = pd.to_numeric(panel.iloc[:, position], errors="coerce")
            bad = values[(values <= 0) & values.notna()]
            for timestamp, price in bad.items():
                rows.append((str(label), timestamp, float(price)))
    if not rows:
        return pd.DataFrame(columns=["symbol", "timestamp", "price"])
    return pd.DataFrame(rows, columns=["symbol", "timestamp", "price"])


class DataCache:
    """File-based cache for downloaded data with content hashing."""

    def __init__(self, cache_dir: Path | None = None):
        # ``data.cache_dir`` is nested in the loaded config (the loader's
        # canonical shape, written by ``_apply_env_overrides``); reading a
        # literal flat ``"data.cache_dir"`` key could never see it, so the
        # configured cache directory -- from config.yaml *or* from
        # ``QTR_CACHE_DIR`` -- was silently replaced by the default and the
        # cache landed in ``.cache/data`` regardless. ``config_path`` resolves
        # both shapes and fails closed to the default.
        self.cache_dir = cache_dir or config_path(get_config(), "data.cache_dir", ".cache/data")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, source: str, symbol: str, start: str, end: str, interval: str) -> str:
        key = f"{source}:{symbol}:{start}:{end}:{interval}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get(
        self, source: str, symbol: str, start: str, end: str, interval: str
    ) -> pd.DataFrame | None:
        key = self._cache_key(source, symbol, start, end, interval)
        path = self.cache_dir / f"{key}.parquet"
        if path.exists():
            try:
                df = pd.read_parquet(path)
                if getattr(df.index, "tz", None) is not None:
                    df = df.copy()
                    try:
                        df.index = df.index.tz_localize(None)
                    except Exception:  # noqa: BLE001 -- be defensive across pandas versions
                        df.index = pd.to_datetime(df.index).tz_localize(None)
                logger.debug(f"Cache hit: {source} {symbol} {interval}")
                return df
            except Exception as e:  # noqa: BLE001 -- cache corruption is non-fatal; skip and re-read
                logger.warning(f"Cache read failed: {e}")
        return None

    def set(
        self,
        source: str,
        symbol: str,
        start: str,
        end: str,
        interval: str,
        df: pd.DataFrame,
    ) -> None:
        key = self._cache_key(source, symbol, start, end, interval)
        path = self.cache_dir / f"{key}.parquet"
        try:
            df_to_write = df.copy()
            if getattr(df_to_write.index, "tz", None) is not None:
                try:
                    df_to_write.index = df_to_write.index.tz_localize(None)
                except Exception:  # noqa: BLE001
                    df_to_write.index = pd.to_datetime(df_to_write.index).tz_localize(None)
            df_to_write.to_parquet(path)
            logger.debug(f"Cache write: {source} {symbol} {interval}")
        except Exception as e:  # noqa: BLE001 -- cache write failure is non-fatal; continue in memory
            logger.warning(f"Cache write failed: {e}")


class DataFetcher:
    """Unified data fetcher with caching and standardization."""

    def __init__(self, cache: DataCache | None = None):
        self.cache = cache or DataCache()
        self._ccxt_exchanges: dict[str, object] = {}

    @staticmethod
    def _reject_non_positive_prices(symbol: str, df: pd.DataFrame) -> None:
        """Fail loud when a fetched panel carries a non-positive price.

        The panel is refused rather than repaired: a negative or zero price
        is a fact about the *source*, and every repair (dropping the bar,
        clipping the price, flooring it at zero) is a research decision the
        caller has to make and to record.  Silently returning the panel
        would let a single negative print become a six-hundred-percent
        one-bar return inside the engine.
        """
        bad = non_positive_prices(df)
        if len(bad) == 0:
            return
        first = bad.iloc[0]
        raise ValueError(
            f"{symbol}: {len(bad)} non-positive price(s) in the fetched panel; "
            f"first is {first['price']!r} on {first['timestamp']}. "
            "A percentage return from a non-positive price base is undefined "
            "(and inverts the sign of the price move when the base is "
            "negative), so this panel is refused rather than passed to the "
            "engine. Trim the window, select a contract series that does "
            "not cross zero, or handle the bar explicitly before retrying."
        )

    @staticmethod
    def _standardize_columns(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Canonicalize a vendor panel's column names and column set.

        Shared by the fresh-fetch path and the cache-hit path of every fetch
        method.  The cache is a persistent, cross-version file store (it is
        committed under ``.cache/data`` and survives code changes), so a cache
        hit must be *indistinguishable* from a fresh fetch.  A frame written by
        an older or foreign writer can carry capitalized vendor columns
        (``Close``, ``Volume``), a different column order, or -- across
        writers/case conventions -- several names that normalize to the same
        label (e.g. ``Close`` and ``CLOSE`` -> ``close``); the fresh path
        lowercases and reorders them, but a cache hit that returned the frame
        verbatim would hand downstream runners ``df["close"]`` -> ``KeyError``
        or, for a duplicated normalized label, a DataFrame instead of a Series
        so ``pct_change``/arithmetic breaks.  A frame that already carries
        canonical, unique lowercase columns is returned bit-identically.

        Column selection degrades over the columns that are present rather than
        indexing a missing name and raising ``KeyError``: a missing column is a
        fact about the source, not a crash.  A duplicated normalized column
        label keeps the first occurrence, mirroring ``_standardize_cached_index``
        (which keeps ``keep="first"`` for a duplicated timestamp).
        """
        df = df.copy()
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        if df.columns.has_duplicates:
            df = df.loc[:, ~df.columns.duplicated(keep="first")]
        required = ["open", "high", "low", "close", "volume"]
        present = [col for col in required if col in df.columns]
        for col in required:
            if col not in df.columns:
                logger.warning(f"Missing column {col} for {symbol}")
        extras = [c for c in df.columns if c not in required]
        return df[present + extras]

    @staticmethod
    def _standardize_cached_index(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Return a cache hit with the timestamp contract of a fresh quote panel.

        The cache is a persistent, cross-version file store (committed under
        ``.cache/data``), so a cache file written by an older or foreign writer
        can carry a non-datetime index or a duplicated timestamp. The fresh
        yahoo/ccxt paths both produce a tz-naive ``DatetimeIndex`` and the ccxt
        path drops duplicates and sorts; a cache hit that skipped that step
        would hand a runner an integer index (``prices.reindex`` / ``pd.concat``
        then align on a mixed index) or a duplicated bar.

        A non-datetime index is refused -- returned empty with its columns
        intact -- rather than coerced: ``pd.to_datetime`` on a stale integer
        index manufactures 1970 timestamps, which is a worse corruption than a
        dropped symbol. A duplicated index keeps the first occurrence and is
        sorted, matching the fresh ccxt path.
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning(
                f"Cached panel for {symbol} has a non-datetime index "
                f"({df.index.dtype}); refusing it rather than manufacturing timestamps"
            )
            return df.iloc[:0]
        return df[~df.index.duplicated(keep="first")].sort_index()

    def _fetch_yahoo_panel(
        self,
        source: str,
        symbol: str,
        start: str,
        end: str,
        interval: str,
        use_cache: bool,
    ) -> pd.DataFrame:
        """Fetch and standardize a single Yahoo Finance panel.

        Shared by :meth:`fetch_yahoo` and :meth:`fetch_futures`, which differ
        only in the cache source name and in the symbol-level pre-check
        (futures warn when the symbol lacks the ``=F`` suffix). Returns a
        possibly-empty DataFrame; the caller applies ``_reject_non_positive_prices``.
        """
        if use_cache:
            # ``DataCache.get`` canonicalizes the index to tz-naive on the way
            # out (fetcher.py:92-96), but the *columns* and the index dtype come
            # back exactly as the writer stored them.  A cache file written by
            # an older/foreign writer can therefore carry capitalized vendor
            # columns, a non-datetime index, or a duplicated timestamp; normalize
            # all three on read so a cache hit matches a fresh fetch.
            cached = self.cache.get(source, symbol, start, end, interval)
            if cached is not None:
                cached = self._standardize_cached_index(cached, symbol)
                return self._standardize_columns(cached, symbol)

        try:
            import yfinance as yf  # lazy import; data extras not required for core

            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start,
                end=end,
                interval=interval,
                auto_adjust=False,
                actions=False,
            )

            if df.empty:
                logger.warning(f"No data for {symbol} from {start} to {end}")
                return pd.DataFrame()

            # Standardize column names and degrade over the columns that are
            # present rather than indexing a missing name and raising
            # ``KeyError``. A missing column is a fact about the source, not
            # a crash.
            df = self._standardize_columns(df, symbol)
            df.index = pd.to_datetime(df.index).tz_localize(None)

            if use_cache:
                self.cache.set(source, symbol, start, end, interval, df)

            return df

        except Exception as e:  # noqa: BLE001 -- per-symbol fetch failure is non-fatal; log and continue
            logger.error(f"Failed to fetch {symbol}: {e}")
            return pd.DataFrame()

    def fetch_yahoo(
        self,
        symbols: list[str],
        start: str,
        end: str | None = None,
        interval: str = "1d",
        use_cache: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch data from Yahoo Finance.

        Args:
            symbols: List of ticker symbols (e.g., ["SPY", "AAPL"])
            start: Start date "YYYY-MM-DD"
            end: End date "YYYY-MM-DD" (default: today)
            interval: "1d", "1h", "5m", etc. (yfinance supported intervals)
            use_cache: Whether to use cached data

        Returns:
            Dict mapping symbol to DataFrame with columns:
            open, high, low, close, volume, (adj_close if available)
        """
        end = end or datetime.now().strftime("%Y-%m-%d")
        results = {}

        for symbol in symbols:
            df = self._fetch_yahoo_panel("yahoo", symbol, start, end, interval, use_cache)
            self._reject_non_positive_prices(symbol, df)
            results[symbol] = df

        return results

    def fetch_futures(
        self,
        symbols: list[str],
        start: str,
        end: str | None = None,
        interval: str = "1d",
        use_cache: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch continuous futures data from Yahoo Finance using =F tickers.

        Args:
            symbols: List of futures symbols with =F suffix (e.g., ["ES=F", "NQ=F", "CL=F", "GC=F", "ZB=F"])
            start: Start date "YYYY-MM-DD"
            end: End date "YYYY-MM-DD" (default: today)
            interval: "1d", "1h", etc. (yfinance supported intervals)
            use_cache: Whether to use cached data

        Returns:
            Dict mapping symbol to DataFrame with columns:
            open, high, low, close, volume

        Note:
            Yahoo Finance continuous futures are back-adjusted (spliced) contracts.
            Roll dates and adjustment methodology are opaque. Long-horizon returns
            may contain roll-date drift bias. Quantify if possible, else state as limitation.
        """
        end = end or datetime.now().strftime("%Y-%m-%d")
        results = {}

        for symbol in symbols:
            if not symbol.endswith("=F"):
                logger.warning(f"Futures symbol {symbol} should end with =F; proceeding anyway")

            df = self._fetch_yahoo_panel("yahoo_futures", symbol, start, end, interval, use_cache)
            self._reject_non_positive_prices(symbol, df)
            results[symbol] = df

        return results

    def fetch_ccxt(
        self,
        exchange_id: str,
        symbols: list[str],
        start: str,
        end: str | None = None,
        timeframe: str = "1h",
        use_cache: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data from a CCXT-supported exchange.

        Args:
            exchange_id: CCXT exchange ID (e.g., "binance", "coinbase", "kraken")
            symbols: List of unified symbols (e.g., ["BTC/USDT", "ETH/USDT"])
            start: Start date "YYYY-MM-DD"
            end: End date "YYYY-MM-DD" (default: today)
            timeframe: CCXT timeframe (e.g., "1m", "5m", "1h", "1d")
            use_cache: Whether to use cached data

        Returns:
            Dict mapping symbol to DataFrame with columns:
            open, high, low, close, volume
        """
        end = end or datetime.now().strftime("%Y-%m-%d")
        results = {}

        # Initialize exchange
        if exchange_id not in self._ccxt_exchanges:
            try:
                import ccxt  # lazy import
            except ImportError as e:
                logger.error(f"ccxt not installed: {e}")
                return results
            # ``getattr(ccxt, exchange_id)`` raises a bare ``AttributeError`` for
            # an exchange id that is not a real CCXT exchange, and that error
            # escapes the per-symbol ``try`` below (it runs BEFORE the symbol
            # loop), so the whole fetch aborts on the first unknown exchange
            # rather than failing closed per-symbol like every other fetch
            # failure here. Catch it and raise a named ``ValueError`` instead,
            # mirroring the ``fetcher()`` dispatcher's explicit error for an
            # unknown ``source``. ``ccxt.exchanges`` is the authoritative list
            # when present; a stub without it falls back to ``getattr``'s
            # behaviour, so the guard is honest against both.
            exchange_class = getattr(ccxt, exchange_id, None)
            if exchange_class is None:
                known = getattr(ccxt, "exchanges", None)
                listing = f" (ccxt supports {len(known)} exchanges)" if known else ""
                raise ValueError(
                    f"unknown CCXT exchange {exchange_id!r}{listing}. "
                    "Pass an id that exists on the ccxt module."
                )
            self._ccxt_exchanges[exchange_id] = exchange_class(
                {
                    "enableRateLimit": True,
                    "rateLimit": 1000,  # ms between requests
                }
            )

        exchange = self._ccxt_exchanges[exchange_id]
        since = int(pd.Timestamp(start).timestamp() * 1000)
        end_ms = int(pd.Timestamp(end).timestamp() * 1000)

        for symbol in symbols:
            cache_symbol = symbol.replace("/", "_")
            if use_cache:
                # ``DataCache.get`` canonicalizes the index to tz-naive on the
                # way out (fetcher.py:92-96), but the *columns* and the index
                # dtype come back exactly as the writer stored them; normalize
                # both on read so a cache hit matches a fresh fetch.
                cached = self.cache.get(
                    "ccxt", f"{exchange_id}:{cache_symbol}", start, end, timeframe
                )
                if cached is not None:
                    # The cache returns columns and index exactly as the writer
                    # stored them; normalize both on read so a cache hit matches
                    # a fresh fetch (a stale capitalized frame would reach
                    # ``df["close"]`` as ``KeyError``; a stale integer/duplicated
                    # index would reach ``prices.reindex`` on a mixed index).
                    cached = self._standardize_cached_index(cached, symbol)
                    cached = self._standardize_columns(cached, symbol)
                    self._reject_non_positive_prices(symbol, cached)
                    results[symbol] = cached
                    continue

            try:
                all_ohlcv = []
                current_since = since
                # Pagination advances ``current_since`` to one millisecond past
                # the last bar returned. A vendor that returns a batch whose
                # newest bar is not later than the ``since`` it was asked for
                # therefore never advances: the loop re-requests the same
                # window forever (measured: 27,992 calls in 15s against a stub
                # that repeats one fixed bar). The fetch is bounded by the
                # window itself -- ``current_since < end_ms`` -- and by the
                # page cap, so a non-advancing vendor must be refused here
                # rather than allowed to consume the whole compute budget.
                while current_since < end_ms:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
                    if not ohlcv:
                        break
                    last_ts = ohlcv[-1][0]
                    if last_ts <= current_since:
                        logger.warning(
                            f"CCXT pagination for {symbol} on {exchange_id} did not advance "
                            f"(last bar {last_ts} <= requested since {current_since}); "
                            "stopping to avoid an infinite loop."
                        )
                        break
                    all_ohlcv.extend(ohlcv)
                    current_since = last_ts + 1
                    if len(ohlcv) < 1000:
                        break

                if not all_ohlcv:
                    logger.warning(f"No data for {symbol} on {exchange_id}")
                    results[symbol] = pd.DataFrame()
                    continue

                # ccxt usually returns [timestamp, open, high, low, close, volume];
                # a vendor that omits a required column must not crash the fetch.
                base_cols = ["timestamp", "open", "high", "low", "close", "volume"]
                df = pd.DataFrame(all_ohlcv)
                if df.shape[1] >= len(base_cols):
                    df = df.iloc[:, : len(base_cols)]
                    df.columns = base_cols
                else:
                    df.columns = base_cols[: df.shape[1]]
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.set_index("timestamp")
                df = df[(df.index >= start) & (df.index <= end)]
                df = df[~df.index.duplicated(keep="first")].sort_index()
                # Standardize column names defensively and degrade over the
                # columns that are present.
                df = self._standardize_columns(df, symbol)
                df.index = pd.to_datetime(df.index).tz_localize(None)

                results[symbol] = df

                if use_cache:
                    self.cache.set(
                        "ccxt",
                        f"{exchange_id}:{cache_symbol}",
                        start,
                        end,
                        timeframe,
                        df,
                    )

            except Exception as e:  # noqa: BLE001 -- per-symbol fetch failure is non-fatal; log and continue
                logger.error(f"Failed to fetch {symbol} from {exchange_id}: {e}")
                results[symbol] = pd.DataFrame()

            self._reject_non_positive_prices(symbol, results[symbol])

        return results

    def fetch_sp500_constituents(self, date: str | None = None) -> list[str]:
        """Fetch S&P 500 constituents (current list only).

        Point-in-time constituents are not available from this source; the returned list
        is the *current* Wikipedia list. Passing ``date`` is not supported and raises
        ``ValueError`` rather than silently returning the current list for a historical
        date (which would introduce survivorship bias).
        """
        if date is not None:
            raise ValueError(
                "fetch_sp500_constituents does not support point-in-time lookup; "
                "the 'date' argument is not honored. Use a point-in-time vendor source."
            )
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        try:
            tables = pd.read_html(url)
            df = tables[0]
            # ``regex=False`` is required: in pandas >= 2.0 the default of
            # ``Series.str.replace`` is regex=True, so a bare ``"."`` is the
            # "any character" pattern and turns every class-share ticker
            # (BRK.B, BF.B, GOOGL.A, ...) into a string of dashes. The dot is
            # a literal character to strip, not a pattern to match.
            return df["Symbol"].str.replace(".", "-", regex=False).tolist()
        except Exception as e:  # noqa: BLE001 -- constituent list fetch failure is non-fatal; fallback proxy list
            logger.error(f"Failed to fetch S&P 500 list: {e}")
            # Fallback to major ETFs as proxy
            return ["SPY", "IVV", "VOO", "SPLG"]


def get_data_fetcher() -> DataFetcher:
    """Singleton data fetcher."""
    if not hasattr(get_data_fetcher, "_instance"):
        get_data_fetcher._instance = DataFetcher()
    return get_data_fetcher._instance


def fetch_sp500_constituents(date: str | None = None) -> list[str]:
    """Fetch S&P 500 constituents (current list only).

    Convenience wrapper around :meth:`DataFetcher.fetch_sp500_constituents`.
    """
    return get_data_fetcher().fetch_sp500_constituents(date=date)


def fetcher(
    source: str,
    symbols: list[str],
    start: str,
    end: str | None = None,
    interval: str = "1d",
    use_cache: bool = True,
    exchange_id: str | None = None,
    timeframe: str = "1h",
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV panels through the named source.

    The three fetch methods on :class:`DataFetcher` each carry their own
    contract (the futures ``=F`` suffix check, the CCXT pagination loop, the
    yahoo column standardisation), and a caller who knows which source they
    want has to remember which method to call and which keyword arguments it
    takes. This is the single entry point: it dispatches on ``source`` and
    forwards the rest unchanged, so ``fetcher("yahoo", ...)`` is the same
    call as ``DataFetcher().fetch_yahoo(...)`` and ``fetcher("ccxt", ...,
    exchange_id="binance")`` is the same call as ``fetch_ccxt``.

    The dispatch is explicit rather than a ``getattr`` on the fetcher, so a
    typo in ``source`` raises a named ``ValueError`` instead of silently
    returning an empty dict (every fetch method logs and continues on a
    per-symbol failure, so a misspelled method name would be invisible).

    Args:
        source: ``"yahoo"``, ``"yahoo_futures"`` or ``"ccxt"``.
        symbols: Tickers to download.
        start: Start date ``"YYYY-MM-DD"``.
        end: End date, or ``None`` for today.
        interval: Vendor interval string for the yahoo branches.
        use_cache: Whether the file cache is consulted.
        exchange_id: CCXT exchange id; required for ``source="ccxt"``.
        timeframe: CCXT timeframe string (e.g. ``"1h"``, ``"1d"``). Only
            consulted for ``source="ccxt"``; the CCXT branch has its own
            default of ``"1h"`` and would otherwise receive the dispatcher's
            ``"1d"`` here, so a caller using defaults would get hourly bars
            requested as daily.

    Returns:
        ``{symbol: DataFrame}``, exactly what the dispatched method returns.

    Raises:
        ValueError: if ``source`` is not one of the three supported names.
    """
    fetch = get_data_fetcher()
    if source == "yahoo":
        return fetch.fetch_yahoo(symbols, start, end, interval, use_cache)
    if source == "yahoo_futures":
        return fetch.fetch_futures(symbols, start, end, interval, use_cache)
    if source == "ccxt":
        if exchange_id is None:
            raise ValueError(
                "source='ccxt' requires exchange_id= (e.g. 'binance'); "
                "got None. CCXT needs an exchange to query."
            )
        return fetch.fetch_ccxt(exchange_id, symbols, start, end, timeframe, use_cache)
    raise ValueError(
        f"unknown data source {source!r}; supported: 'yahoo', 'yahoo_futures', 'ccxt'. "
        "Pass one of those as source=."
    )
