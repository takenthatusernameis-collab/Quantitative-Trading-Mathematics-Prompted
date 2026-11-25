#!/usr/bin/env python3
"""Free-data availability probe for candidate discovery observables.

Why this exists
---------------
Several candidate strategy families were closed as ``data-blocked`` in
``NEW_FAMILY_RESEARCH_REGISTER.md`` because a series was "unavailable on the
free pipeline" -- but the pipeline that was checked was *yfinance only*.  A
ticker that is missing from yfinance (for example the breakeven-inflation
series ``^T5YIE``/``^T10YIE``) is not proof the *observable* is unavailable:
the Federal Reserve Bank of St. Louis (FRED) publishes it free, without a
key, as CSV.  ``STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`` §6 explicitly
forbids mistaking "an unavailable dataset" for proof that a mechanism is
exhausted, and requires searching a materially different set of sources
before concluding no candidate is testable.

This tool is that different source.  It reports, for a curated list of
free/public series, whether the data is actually reachable and how much
history it covers, so a future discovery cycle can *verify* a data-availability
claim instead of assuming it.  It is read-only: it downloads to memory, never
writes a cache, and touches no experiment artifact.

Usage
-----
    python scripts/probe_fred_availability.py            # probe every series
    python scripts/probe_fred_availability.py T10YIE NFCI  # probe a subset

Exit code is non-zero if any *FRED* series in the probe set is unreachable, so
the probe cannot silently pass while the data it is meant to verify is missing.
yfinance misses are reported but do not fail the run (yfinance delistings are
common and are a separate, already-documented issue).
"""

from __future__ import annotations

import argparse
import io
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
USER_AGENT = "qtr-research/0.1 (research@example.com)"

# Curated free/public candidates the register has variously called
# "data-blocked".  ``category`` is the broad mechanism category they feed.
FRED_SERIES: dict[str, tuple[str, str]] = {
    # series_id: (description, mechanism category)
    "T10YIE": ("10-year breakeven inflation rate", "inflation expectations / macro regime"),
    "T5YIE": ("5-year breakeven inflation rate", "inflation expectations / macro regime"),
    "DFII10": ("10-year TIPS real yield", "real rates / macro regime"),
    "NFCI": ("Chicago Fed National Financial Conditions Index", "financial conditions"),
    "STLFSI": ("St. Louis Fed Financial Stress Index", "financial stress"),
    "UMCSENT": ("University of Michigan consumer sentiment", "household sentiment"),
    "BAMLH0A0HYM2": ("ICE BofA US High Yield effective yield", "credit conditions"),
    "BAMLC0A0CM": ("ICE BofA US High Yield OAS", "credit conditions"),
    "VIXCLS": ("CBOE Volatility Index (VIX) close", "volatility"),
    "DGS10": ("10-year Treasury constant maturity yield", "rates level"),
    "T10Y2Y": ("10y minus 2y Treasury spread", "yield-curve slope"),
}


def fetch_fred(series_id: str, timeout: float = 20.0) -> pd.Series:
    """Download one FRED series as a date-indexed float Series (memory only).

    Transient network errors (timeout, connection) are retried with bounded
    exponential backoff; HTTP errors (e.g. 404 for an unknown series id) are
    re-raised so the caller can record them as UNREACHABLE findings.
    """
    request = urllib.request.Request(FRED_CSV.format(series_id), headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode()
            break
        except urllib.error.HTTPError:
            raise
        except (TimeoutError, urllib.error.URLError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(1.0 * (2**attempt))
    else:
        raise last_error or TimeoutError(f"FRED fetch exhausted for {series_id}")
    frame = pd.read_csv(io.StringIO(raw))
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return frame.dropna().set_index("date")["value"]


def probe(series_id: str) -> dict[str, object]:
    """Probe one series and return a row of evidence."""
    description, category = FRED_SERIES.get(series_id, (series_id, "unknown"))
    try:
        data = fetch_fred(series_id)
    except Exception as error:  # noqa: BLE001 -- a per-series miss is the finding
        return {
            "series": series_id,
            "status": "UNREACHABLE",
            "n_obs": 0,
            "start": "",
            "end": "",
            "category": category,
            "error": f"{type(error).__name__}: {error}",
        }
    return {
        "series": series_id,
        "status": "OK",
        "n_obs": int(len(data)),
        "start": data.index.min().date().isoformat() if len(data) else "",
        "end": data.index.max().date().isoformat() if len(data) else "",
        "category": category,
        "error": "",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "series",
        nargs="*",
        help="FRED series ids to probe (default: the curated set)",
    )
    args = parser.parse_args(argv)
    selected = args.series or list(FRED_SERIES)

    rows = []
    for series_id in selected:
        if series_id not in FRED_SERIES:
            print(f"warning: {series_id!r} is not in the curated set; probing anyway")
        rows.append(probe(series_id))

    width = max(len(str(row["series"])) for row in rows)
    print(f"Free-data availability probe ({len(rows)} series)")
    print(f"{'series':<{width}}  {'status':<12}{'n_obs':>7}  {'start':<12}{'end':<12}category")
    for row in rows:
        print(
            f"{row['series']!s:<{width}}  {row['status']!s:<12}{row['n_obs']:>7}  "
            f"{row['start']!s:<12}{row['end']!s:<12}{row['category']}"
        )
        if row["error"]:
            print(f"{'':<{width}}    error: {row['error']}")

    unreachable = [row["series"] for row in rows if row["status"] != "OK"]
    if unreachable:
        print(f"\nUNREACHABLE: {', '.join(map(str, unreachable))}", file=sys.stderr)
        return 1
    print("\nAll probed series are reachable from the free source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
