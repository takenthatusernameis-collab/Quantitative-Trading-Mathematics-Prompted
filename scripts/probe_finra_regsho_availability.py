#!/usr/bin/env python3
"""Free-data availability probe: FINRA Reg SHO daily short volume.

Why this exists
---------------
The NEXT_TASK.md candidate (2) "short-interest / days-to-cover cross-section
(FINRA/SEC data)" requires a bounded availability probe before pre-registration.
FINRA publishes daily Reg SHO short volume files at
https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt — free, no key,
no geo-blocking. This is *daily short volume* (not the bi-weekly short interest
report), but it provides a high-frequency proxy for short-selling pressure that
can be aggregated to a monthly cross-sectional signal.

This tool reports, for a curated universe of liquid large-cap tickers, whether
daily short volume files are reachable and how much history they cover. It is
read-only: it downloads to memory and touches no experiment artifact.

Usage
-----
    python scripts/probe_finra_regsho_availability.py            # curated set
    python scripts/probe_finra_regsho_availability.py AAPL MSFT  # subset

Exit code is 1 if no requested symbol has usable history for the
latest available date, so the probe cannot silently pass while the data it is
meant to verify is missing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import sys
import urllib.error
import urllib.request

import pandas as pd

REGSHO_URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{date}.txt"
USER_AGENT = "qtr-research/0.1 (research@example.com)"

# Curated liquid large-cap universe (subset of S&P 100) for probe.
CURATED = [
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "NVDA",
    "TSLA",
    "BRK.B",
    "UNH",
    "JNJ",
    "V",
    "JPM",
    "WMT",
    "MA",
    "PG",
    "XOM",
    "HD",
    "CVX",
    "ABBV",
    "KO",
    "PEP",
    "COST",
    "AVGO",
    "MRK",
    "CSCO",
    "ADBE",
    "NFLX",
    "CRM",
    "TMO",
    "ACN",
    "LLY",
    "ABT",
    "DHR",
    "LIN",
    "TXN",
    "NEE",
    "AMD",
    "QCOM",
    "HON",
    "INTU",
    "AMGN",
    "LOW",
    "SBUX",
    "AMAT",
    "ISRG",
    "BKNG",
    "GILD",
    "MDT",
    "ADP",
    "VRTX",
]

# Earliest known Reg SHO daily file (FINRA started publishing ~2010).
EARLIEST_DATE = dt.date(2010, 1, 4)


def date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    """Inclusive list of business days between two dates (approx)."""
    return pd.bdate_range(start, end).tolist()


def regsho_url(date: dt.date) -> str:
    """Build Reg SHO daily file URL for a given date."""
    return REGSHO_URL.format(date=date.strftime("%Y%m%d"))


def fetch_regsho(date: dt.date, timeout: float = 15.0) -> bytes | None:
    """Download one Reg SHO daily file; None for expected 404/403 (weekend/holiday)."""
    url = regsho_url(date)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except (urllib.error.HTTPError, TimeoutError, urllib.error.URLError):
        return None


def parse_regsho(raw: bytes) -> pd.DataFrame:
    """Parse a Reg SHO daily file into Symbol/ShortVolume/TotalVolume rows."""
    text = raw.decode("utf-8")
    frame = pd.read_csv(io.StringIO(text), sep="|", dtype=str)
    for col in ["ShortVolume", "ShortExemptVolume", "TotalVolume"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame["ShortRatio"] = frame["ShortVolume"] / frame["TotalVolume"]
    return frame[["Symbol", "ShortVolume", "TotalVolume", "ShortRatio"]].dropna(
        subset=["ShortRatio"]
    )


def latest_available_date(max_check: int = 10) -> dt.date | None:
    """Find the latest business day with a Reg SHO file (within max_check days)."""
    today = dt.date.today()
    for i in range(max_check):
        check_date = today - dt.timedelta(days=i)
        if check_date.weekday() >= 5:
            continue
        if fetch_regsho(check_date) is not None:
            return check_date
    return None


def probe_symbol(
    symbol: str,
    start_date: dt.date,
    end_date: dt.date,
    sample_dates: list[dt.date] | None = None,
    fetch=None,
) -> dict[str, object]:
    """Probe one symbol: check coverage over a sample of dates."""
    if fetch is None:
        fetch = fetch_regsho
    if sample_dates is None:
        all_dates = date_range(start_date, end_date)
        sample_dates = all_dates[::21]  # ~monthly
        if not sample_dates and all_dates:
            sample_dates = [all_dates[-1]]

    observations = 0
    first_obs = None
    last_obs = None
    ratios = []

    for date in sample_dates:
        raw = fetch(date)
        if raw is None:
            continue
        frame = parse_regsho(raw)
        row = frame[frame["Symbol"] == symbol]
        if len(row) == 0:
            continue
        ratio = float(row.iloc[0]["ShortRatio"])
        observations += 1
        ratios.append(ratio)
        if first_obs is None:
            first_obs = date
        last_obs = date

    mean_ratio = float(pd.Series(ratios).mean()) if ratios else 0.0

    return {
        "symbol": symbol,
        "status": "OK" if observations > 0 else "NO_DATA",
        "observations": observations,
        "first_date": first_obs.isoformat() if first_obs else "",
        "last_date": last_obs.isoformat() if last_obs else "",
        "mean_short_ratio": mean_ratio,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("symbols", nargs="*", help="symbols to probe (default: curated set)")
    parser.add_argument("--start", default=None, help="start date YYYY-MM-DD (default: 2010-01-04)")
    parser.add_argument(
        "--end", default=None, help="end date YYYY-MM-DD (default: latest available)"
    )
    parser.add_argument("--sample-every", type=int, default=21, help="sample every N business days")
    args = parser.parse_args(argv)

    symbols = args.symbols or CURATED
    start_date = dt.date.fromisoformat(args.start) if args.start else EARLIEST_DATE
    end_date = (
        dt.date.fromisoformat(args.end)
        if args.end
        else (latest_available_date() or dt.date.today())
    )

    print(
        f"Free-data availability probe: FINRA Reg SHO daily short volume ({start_date} to {end_date})"
    )
    print(
        f"{'symbol':<8}  {'status':<8}  {'obs':>4}  {'first':<12}  {'last':<12}  {'mean_short_ratio':>8}"
    )

    rows = []
    all_dates = date_range(start_date, end_date)
    sample_dates = all_dates[:: args.sample_every] if all_dates else []
    if not sample_dates and all_dates:
        sample_dates = [all_dates[-1]]

    for symbol in symbols:
        row = probe_symbol(symbol, start_date, end_date, sample_dates, fetch=fetch_regsho)
        rows.append(row)
        print(
            f"{row['symbol']:<8}  {row['status']:<8}  {row['observations']:>4}  "
            f"{row['first_date']:<12}  {row['last_date']:<12}  {row['mean_short_ratio']:>8.4f}"
        )

    usable = [row["symbol"] for row in rows if row["status"] == "OK"]
    if not usable:
        print(
            "\nNO USABLE SYMBOL: Reg SHO files unreachable or symbols not found.", file=sys.stderr
        )
        return 1

    print(
        f"\nUsable symbols from free public archives: {', '.join(map(str, usable))} ({len(usable)}/{len(rows)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
