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

from qtr.utils.config import get_config

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
    if price_columns:
        series = {str(column): panel[column] for column in price_columns}
    else:
        series = {str(col): panel[col] for col in panel.columns}

    rows = []
    for name, column in series.items():
        values = pd.to_numeric(column, errors="coerce")
        bad = values[(values <= 0) & values.notna()]
        for timestamp, price in bad.items():
            rows.append((name, timestamp, float(price)))
    if not rows:
        return pd.DataFrame(columns=["symbol", "timestamp", "price"])
    return pd.DataFrame(rows, columns=["symbol", "timestamp", "price"])


class DataCache:
    """File-based cache for downloaded data with content hashing."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path(get_config().get("data.cache_dir", ".cache/data"))
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
            if use_cache:
                # ``DataCache.get`` canonicalizes the index to tz-naive on the
                # way out (fetcher.py:92-96), so a cached frame is already in
                # the shape every caller expects and needs no per-fetch
                # normalization here. The normalization lives in the cache
                # layer, not in each fetch method's cache-hit path.
                cached = self.cache.get("yahoo", symbol, start, end, interval)
                if cached is not None:
                    self._reject_non_positive_prices(symbol, cached)
                    results[symbol] = cached
                    continue

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
                    results[symbol] = pd.DataFrame()
                    continue

                # Standardize column names
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]

                # Ensure required columns. The selection is built from the
                # columns that are actually present: a vendor that omits
                # ``volume`` (or any other required column) is warned about
                # and the frame is re-ordered over the columns it *does*
                # carry, rather than indexing a list that contains a missing
                # name and raising ``KeyError``. A missing column is a fact
                # about the source, not a crash -- the fetch degrades to a
                # panel without it and the caller decides whether that is
                # usable (the engine treats a missing volume column as zero
                # volume in the impact model).
                required = ["open", "high", "low", "close", "volume"]
                present = [col for col in required if col in df.columns]
                for col in required:
                    if col not in df.columns:
                        logger.warning(f"Missing column {col} for {symbol}")
                extras = [c for c in df.columns if c not in required]

                df = df[present + extras]
                df.index = pd.to_datetime(df.index).tz_localize(None)

                results[symbol] = df

                if use_cache:
                    self.cache.set("yahoo", symbol, start, end, interval, df)

            except Exception as e:  # noqa: BLE001 -- per-symbol fetch failure is non-fatal; log and continue
                logger.error(f"Failed to fetch {symbol}: {e}")
                results[symbol] = pd.DataFrame()

            self._reject_non_positive_prices(symbol, results[symbol])

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

            if use_cache:
                # ``DataCache.get`` canonicalizes the index to tz-naive on the
                # way out (fetcher.py:92-96), so a cached frame is already in
                # the shape every caller expects and needs no per-fetch
                # normalization here. The normalization lives in the cache
                # layer, not in each fetch method's cache-hit path.
                cached = self.cache.get("yahoo_futures", symbol, start, end, interval)
                if cached is not None:
                    self._reject_non_positive_prices(symbol, cached)
                    results[symbol] = cached
                    continue

            try:
                import yfinance as yf

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
                    results[symbol] = pd.DataFrame()
                    continue

                # Standardize column names
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]

                # Ensure required columns. The selection is built from the
                # columns that are actually present (see the identical fix in
                # ``fetch_yahoo``): a vendor that omits a required column is
                # warned about and the frame is re-ordered over the columns it
                # carries, instead of indexing a list containing a missing name
                # and raising ``KeyError``.
                required = ["open", "high", "low", "close", "volume"]
                present = [col for col in required if col in df.columns]
                for col in required:
                    if col not in df.columns:
                        logger.warning(f"Missing column {col} for {symbol}")
                extras = [c for c in df.columns if c not in required]

                df = df[present + extras]
                df.index = pd.to_datetime(df.index).tz_localize(None)

                results[symbol] = df

                if use_cache:
                    self.cache.set("yahoo_futures", symbol, start, end, interval, df)

            except Exception as e:  # noqa: BLE001 -- per-symbol fetch failure is non-fatal; log and continue
                logger.error(f"Failed to fetch {symbol}: {e}")
                results[symbol] = pd.DataFrame()

            self._reject_non_positive_prices(symbol, results[symbol])

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
            exchange_class = getattr(ccxt, exchange_id)
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
                # way out (fetcher.py:92-96), so a cached frame is already in
                # the shape every caller expects and needs no per-fetch
                # normalization here. The normalization lives in the cache
                # layer, not in each fetch method's cache-hit path.
                cached = self.cache.get(
                    "ccxt", f"{exchange_id}:{cache_symbol}", start, end, timeframe
                )
                if cached is not None:
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

                df = pd.DataFrame(
                    all_ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"],
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.set_index("timestamp")
                df = df[(df.index >= start) & (df.index <= end)]
                df = df[~df.index.duplicated(keep="first")].sort_index()
                # Standardize column names defensively (ccxt usually returns the above)
                df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
                required = ["open", "high", "low", "close", "volume"]
                present = [col for col in required if col in df.columns]
                for col in required:
                    if col not in df.columns:
                        logger.warning(f"Missing column {col} for {symbol}")
                extras = [c for c in df.columns if c not in required]
                df = df[present + extras]
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
