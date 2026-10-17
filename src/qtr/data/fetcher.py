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


class DataCache:
    """File-based cache for downloaded data with content hashing."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path(get_config().get("data.cache_dir", ".cache/data"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, source: str, symbol: str, start: str, end: str, interval: str) -> str:
        key = f"{source}:{symbol}:{start}:{end}:{interval}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get(self, source: str, symbol: str, start: str, end: str, interval: str) -> pd.DataFrame | None:
        key = self._cache_key(source, symbol, start, end, interval)
        path = self.cache_dir / f"{key}.parquet"
        if path.exists():
            try:
                df = pd.read_parquet(path)
                logger.debug(f"Cache hit: {source} {symbol} {interval}")
                return df
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
        return None

    def set(self, source: str, symbol: str, start: str, end: str, interval: str, df: pd.DataFrame) -> None:
        key = self._cache_key(source, symbol, start, end, interval)
        path = self.cache_dir / f"{key}.parquet"
        try:
            df.to_parquet(path)
            logger.debug(f"Cache write: {source} {symbol} {interval}")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")


class DataFetcher:
    """Unified data fetcher with caching and standardization."""

    def __init__(self, cache: DataCache | None = None):
        self.cache = cache or DataCache()
        self._ccxt_exchanges: dict[str, ccxt.Exchange] = {}

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
                cached = self.cache.get("yahoo", symbol, start, end, interval)
                if cached is not None:
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
                df = df.rename(columns={"adj_close": "adj_close"})

                # Ensure required columns
                required = ["open", "high", "low", "close", "volume"]
                for col in required:
                    if col not in df.columns:
                        logger.warning(f"Missing column {col} for {symbol}")

                df = df[required + [c for c in df.columns if c not in required]]
                df.index = pd.to_datetime(df.index).tz_localize(None)

                results[symbol] = df

                if use_cache:
                    self.cache.set("yahoo", symbol, start, end, interval, df)

            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                results[symbol] = pd.DataFrame()

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
                cached = self.cache.get("yahoo_futures", symbol, start, end, interval)
                if cached is not None:
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
                df = df.rename(columns={"adj_close": "adj_close"})

                # Ensure required columns
                required = ["open", "high", "low", "close", "volume"]
                for col in required:
                    if col not in df.columns:
                        logger.warning(f"Missing column {col} for {symbol}")

                df = df[required + [c for c in df.columns if c not in required]]
                df.index = pd.to_datetime(df.index).tz_localize(None)

                results[symbol] = df

                if use_cache:
                    self.cache.set("yahoo_futures", symbol, start, end, interval, df)

            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                results[symbol] = pd.DataFrame()

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
            self._ccxt_exchanges[exchange_id] = exchange_class({
                "enableRateLimit": True,
                "rateLimit": 1000,  # ms between requests
            })

        exchange = self._ccxt_exchanges[exchange_id]
        since = int(pd.Timestamp(start).timestamp() * 1000)
        end_ms = int(pd.Timestamp(end).timestamp() * 1000)

        for symbol in symbols:
            cache_symbol = symbol.replace("/", "_")
            if use_cache:
                cached = self.cache.get("ccxt", f"{exchange_id}:{cache_symbol}", start, end, timeframe)
                if cached is not None:
                    results[symbol] = cached
                    continue

            try:
                all_ohlcv = []
                current_since = since

                while current_since < end_ms:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
                    if not ohlcv:
                        break
                    all_ohlcv.extend(ohlcv)
                    current_since = ohlcv[-1][0] + 1
                    if len(ohlcv) < 1000:
                        break

                if not all_ohlcv:
                    logger.warning(f"No data for {symbol} on {exchange_id}")
                    results[symbol] = pd.DataFrame()
                    continue

                df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.set_index("timestamp")
                df = df[(df.index >= start) & (df.index <= end)]
                df = df[~df.index.duplicated(keep="first")].sort_index()

                results[symbol] = df

                if use_cache:
                    self.cache.set("ccxt", f"{exchange_id}:{cache_symbol}", start, end, timeframe, df)

            except Exception as e:
                logger.error(f"Failed to fetch {symbol} from {exchange_id}: {e}")
                results[symbol] = pd.DataFrame()

        return results

    def fetch_sp500_constituents(self, date: str | None = None) -> list[str]:
        """Fetch S&P 500 constituents as of a given date (approximate via current list)."""
        # For MVP, return current S&P 500 from Wikipedia
        # In production, use point-in-time constituents from a vendor
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        try:
            tables = pd.read_html(url)
            df = tables[0]
            return df["Symbol"].str.replace(".", "-").tolist()
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 list: {e}")
            # Fallback to major ETFs as proxy
            return ["SPY", "IVV", "VOO", "SPLG"]


def get_data_fetcher() -> DataFetcher:
    """Singleton data fetcher."""
    if not hasattr(get_data_fetcher, "_instance"):
        get_data_fetcher._instance = DataFetcher()
    return get_data_fetcher._instance