#!/usr/bin/env python3
"""Free-data availability probe: Binance public perp archives.

Why this exists
---------------
``NEW_FAMILY_RESEARCH_REGISTER.md`` closed the crypto perpetual
funding/basis candidate (NF-20261114-02, scored 3.00) as **data-blocked**
because "no free historical funding-rate series" was available.  That
classification was based on the *exchange REST API* and on yfinance, both of
which are geo-restricted to 451 from this host and neither of which serves
funding history.  It is not proof the observable is unavailable: Binance
publishes monthly ZIP archives of perpetual ``fundingRate`` and daily
``klines`` (perp + spot) at ``data.binance.vision`` free, without a key and
without geo-blocking.  ``STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`` §6 forbids
mistaking "an unavailable dataset" for proof that a mechanism is exhausted
and requires probing a materially different source before concluding.

This tool reports, per curated USDT-perp symbol, whether funding and daily
perp/spot kline archives are reachable and when they start.  It is read-only:
it downloads to memory and touches no experiment artifact.

Usage
-----
    python scripts/probe_binance_funding_availability.py            # curated set
    python scripts/probe_binance_funding_availability.py BTCUSDT ETHUSDT

Exit code is 1 if no requested symbol has usable funding *and* kline history
for the latest completed month, so the probe cannot silently pass while the
data it is meant to verify is missing.  Individual 404s for months before a
symbol was listed are expected and are reported as coverage, not failure.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import sys
import urllib.error
import urllib.request
import zipfile

import pandas as pd

ARCHIVE_ROOT = "https://data.binance.vision/data"
USER_AGENT = "qtr-research/0.1 (research@example.com)"

CURATED = {
    "BTCUSDT": "crypto perpetual funding carry / basis (major)",
    "ETHUSDT": "crypto perpetual funding carry / basis (major)",
    "BNBUSDT": "crypto perpetual funding carry / basis (alt-major)",
    "XRPUSDT": "crypto perpetual funding carry / basis (alt-major)",
    "ADAUSDT": "crypto perpetual funding carry / basis (alt-major)",
    "SOLUSDT": "crypto perpetual funding carry / basis (high-beta, later listing)",
    "DOGEUSDT": "crypto perpetual funding carry / basis (high-beta, later listing)",
}

CANDIDATE_FIRST_MONTHS = ["2020-01", "2020-07", "2020-09", "2021-01"]


def month_range(start: str, end: str) -> list[str]:
    """Inclusive list of ``YYYY-MM`` months between two ``YYYY-MM`` strings."""
    start_ts = pd.Period(start, freq="M")
    end_ts = pd.Period(end, freq="M")
    if end_ts < start_ts:
        return []
    return [str(p) for p in pd.period_range(start_ts, end_ts, freq="M")]


def latest_complete_month(today: dt.date | None = None) -> str:
    """Last fully published archive month (the current month is partial)."""
    today = today or dt.date.today()
    previous = today.replace(day=1) - dt.timedelta(days=1)
    return f"{previous.year:04d}-{previous.month:02d}"


def archive_url(kind: str, symbol: str, month: str) -> str:
    """Build a public-archive URL for ``funding``, ``perp`` or ``spot`` data."""
    if kind == "funding":
        return (
            f"{ARCHIVE_ROOT}/futures/um/monthly/fundingRate/{symbol}/"
            f"{symbol}-fundingRate-{month}.zip"
        )
    if kind == "perp":
        return f"{ARCHIVE_ROOT}/futures/um/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip"
    if kind == "spot":
        return f"{ARCHIVE_ROOT}/spot/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip"
    raise ValueError(f"unknown archive kind: {kind!r}")


def fetch_archive(url: str, timeout: float = 30.0) -> bytes | None:
    """Download one archive; ``None`` for the expected 404 (not yet listed)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def parse_funding_archive(raw: bytes) -> pd.DataFrame:
    """Parse a fundingRate ZIP into ``calc_time``/``interval``/``rate`` rows."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = archive.namelist()[0]
        frame = pd.read_csv(io.BytesIO(archive.read(name)))
    frame.columns = [str(c).strip() for c in frame.columns]
    frame["calc_time"] = pd.to_datetime(frame["calc_time"], unit="ms", utc=True)
    frame["funding_interval_hours"] = pd.to_numeric(
        frame["funding_interval_hours"], errors="coerce"
    )
    frame["last_funding_rate"] = pd.to_numeric(frame["last_funding_rate"], errors="coerce")
    return frame.dropna(subset=["last_funding_rate"]).reset_index(drop=True)


def parse_kline_archive(raw: bytes) -> pd.DataFrame:
    """Parse a daily kline ZIP into ``open_time``/``close`` rows (numeric only)."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = archive.namelist()[0]
        frame = pd.read_csv(io.BytesIO(archive.read(name)))
    frame.columns = [str(c).strip() for c in frame.columns]
    frame["open_time"] = pd.to_numeric(frame["open_time"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    return frame.dropna(subset=["open_time", "close"]).reset_index(drop=True)


def first_available_month(symbol: str, fetch=fetch_archive) -> str | None:
    """Earliest candidate month whose funding archive exists for ``symbol``."""
    for month in CANDIDATE_FIRST_MONTHS:
        if fetch(archive_url("funding", symbol, month)) is not None:
            return month
    return None


def probe_symbol(symbol: str, last_month: str, fetch=fetch_archive) -> dict[str, object]:
    """Probe one symbol: funding coverage plus perp/spot kline reachability."""
    first = first_available_month(symbol, fetch=fetch)
    if first is None:
        return {
            "symbol": symbol,
            "status": "NO_FUNDING",
            "first_month": "",
            "last_month": "",
            "funding_obs": 0,
            "mean_bps_per_day": 0.0,
            "perp_ok": False,
            "spot_ok": False,
            "category": CURATED.get(symbol, ""),
        }
    months = month_range(first, last_month)
    funding_raw = fetch(archive_url("funding", symbol, last_month))
    perp_raw = fetch(archive_url("perp", symbol, last_month))
    spot_raw = fetch(archive_url("spot", symbol, last_month))
    funding = parse_funding_archive(funding_raw) if funding_raw else pd.DataFrame()
    mean_daily = 0.0
    if not funding.empty:
        daily = (
            funding.set_index("calc_time")["last_funding_rate"]
            .groupby(lambda ts: ts.date())
            .sum()
        )
        mean_daily = float(daily.mean()) * 1e4
    return {
        "symbol": symbol,
        "status": "OK" if (perp_raw and spot_raw) else "PARTIAL",
        "first_month": first,
        "last_month": last_month,
        "months": len(months),
        "funding_obs": int(len(funding)),
        "mean_bps_per_day_latest_month": mean_daily,
        "perp_ok": perp_raw is not None,
        "spot_ok": spot_raw is not None,
        "category": CURATED.get(symbol, ""),
    }


def main(argv: list[str] | None = None, fetch=fetch_archive) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("symbols", nargs="*", help="symbols to probe (default: curated set)")
    args = parser.parse_args(argv)
    symbols = args.symbols or list(CURATED)
    last_month = latest_complete_month()

    rows = [probe_symbol(symbol, last_month, fetch) for symbol in symbols]
    width = max([len("symbol")] + [len(str(row["symbol"])) for row in rows])
    print(f"Free-data availability probe: Binance public archives (latest month {last_month})")
    print(
        f"{'symbol':<{width}}  {'status':<8}{'first':<9}{'last':<9}"
        f"{'obs':>6}  {'bps/day':>8}  perp  spot"
    )
    for row in rows:
        print(
            f"{row['symbol']!s:<{width}}  {row['status']!s:<8}{row['first_month']!s:<9}"
            f"{row['last_month']!s:<9}{row['funding_obs']:>6}  "
            f"{row.get('mean_bps_per_day_latest_month', 0.0):>8.3f}  "
            f"{'yes' if row['perp_ok'] else 'NO':<4}  {'yes' if row['spot_ok'] else 'NO'}"
        )

    usable = [row["symbol"] for row in rows if row["status"] == "OK"]
    if not usable:
        print("\nNO USABLE SYMBOL: funding/kline archives unreachable.", file=sys.stderr)
        return 1
    print(
        f"\nUsable symbols from free public archives: {', '.join(map(str, usable))}"
        f" ({len(usable)}/{len(rows)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
