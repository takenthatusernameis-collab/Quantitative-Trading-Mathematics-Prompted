"""Probe SEC XBRL companyfacts as a free point-in-time fundamentals source.

Purpose
-------
The family register classifies "fundamental / accounting" mechanisms as
data-blocked because the free pipeline only serves prices (yfinance).  The SEC
XBRL ``companyfacts`` API is a free, public, *point-in-time* alternative: every
reported fact carries the accession's ``filed`` acceptance date, so a signal
built from a 10-K cannot use information before that filing was public.

This script is a pure availability probe: it downloads (and caches) the
companyfacts bundle for a fixed large-cap universe, extracts annual 10-K
observations for the three tags needed by an accruals / asset-growth signal
(``NetIncomeLoss``, ``NetCashProvidedByUsedInOperatingActivities``, ``Assets``)
and reports, per symbol, the fiscal-year coverage and filing lags.

Tag portability is *not* universal.  A companyfacts bundle can exist for a
ticker while the fixed three-tag recipe yields few or zero annual rows: the
ticker map may resolve to a recently formed successor entity with no 10-K
history, or a firm may report net income under a different us-gaap tag after a
fiscal-year change.  The summary therefore separates "bundle downloaded" from
"annual rows extracted" and lists the zero-annual symbols, so coverage is an
observed quantity rather than an assumption.

Nothing here is a strategy: no returns are read, no backtest runs, no existing
artifact is touched.  The probe writes only its own cache (``.cache/xbrl``,
git-ignored) and prints a JSON summary.  Sources probed by name:
``data.sec.gov/api/xbrl/companyfacts`` (facts + ``filed`` dates) and
``www.sec.gov/files/company_tickers.json`` (ticker -> CIK).  SEC requires a
descriptive User-Agent; set ``QTR_SEC_USER_AGENT`` to override the default.

Usage
-----
    python scripts/probe_sec_xbrl_fundamentals.py --download-only
    python scripts/probe_sec_xbrl_fundamentals.py --symbols AAPL MSFT KO
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

try:
    from qtr.data.insider import normalize_cik, user_agent
except ImportError:  # allow `python scripts/...` with no editable install
    sys.path.insert(0, str(ROOT / "src"))
    from qtr.data.insider import normalize_cik, user_agent

COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_DIR = Path(".cache") / "xbrl"

# Annual duration window (days) accepted as a 10-K reporting period.
MIN_ANNUAL_DAYS = 340
MAX_ANNUAL_DAYS = 380

DURATION_TAGS = ("NetIncomeLoss", "NetCashProvidedByUsedInOperatingActivities")
INSTANT_TAGS = ("Assets",)
REQUIRED_TAGS = DURATION_TAGS + INSTANT_TAGS

# Fixed large-cap universe: current S&P 100 membership (as of 2026-09-21).  The
# list is an objective, reproducible snapshot at a fixed date, but it is
# *survivorship biased*: firms that failed or were removed are absent.  The
# bias must be disclosed and is documented in the H187 pre-registration.
UNIVERSE = (
    "AAPL ABBV ABT ACN ADBE AMAT AMD AMGN AMT AMZN ANET AVGO AXP BA BAC BKNG "
    "BLK BMY BNY C CAT CMCSA COF COP COST CRM CSCO CVS CVX DE DELL DHR DIS "
    "DUK EMR FDX GD GE GEV GILD GM GOOG GOOGL GS HD IBM INTC INTU ISRG JNJ "
    "JPM KO LIN LLY LMT LOW LRCX MA MCD MDLZ MDT META MMM MO MRK MS MSFT MU "
    "NEE NFLX NOW NVDA ORCL PANW PEP PFE PG PLTR PM QCOM RTX SBUX SCHW SNDK "
    "SO T TMO TMUS TSLA TXN UBER UNH UNP UPS USB V VZ WFC WMT XOM"
).split()


def cache_dir_for(cache_dir: Path | str | None = None) -> Path:
    return Path(cache_dir) if cache_dir is not None else CACHE_DIR


def companyfacts_url(cik: str | int) -> str:
    return COMPANYFACTS_URL.format(cik=normalize_cik(cik))


def _http_get(url: str, *, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def load_ticker_cik_map(
    path: Path | str | None = None, *, fetch: bool = True, refresh: bool = False
) -> dict[str, str]:
    """Ticker -> zero-padded CIK, cached on disk after the first fetch."""
    target = Path(path) if path is not None else cache_dir_for() / "company_tickers.json"
    if refresh or not target.exists():
        if not fetch:
            raise FileNotFoundError(f"ticker map not cached at {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_http_get(TICKER_MAP_URL))
    raw = json.loads(target.read_text())
    mapping: dict[str, str] = {}
    for entry in raw.values():
        mapping[str(entry["ticker"]).upper()] = normalize_cik(int(entry["cik_str"]))
    return mapping


def cached_companyfacts(
    cik: str | int,
    cache_dir: Path | str | None = None,
    *,
    fetch: bool = True,
    refresh: bool = False,
    retries: int = 3,
) -> dict:
    """Return the companyfacts bundle for one CIK, caching the raw bytes."""
    directory = cache_dir_for(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"CIK{normalize_cik(cik)}.json"
    if refresh or not target.exists():
        if not fetch:
            raise FileNotFoundError(f"companyfacts not cached at {target}")
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                target.write_bytes(_http_get(companyfacts_url(cik)))
                last_error = None
                break
            except Exception as error:  # network/HTTP; bounded backoff
                last_error = error
                time.sleep(2.0 * (attempt + 1))
        if last_error is not None:
            raise last_error
    return json.loads(target.read_text())


def tag_rows(facts: dict, tag: str) -> pd.DataFrame:
    """Flatten one us-gaap tag into a typed frame (empty when absent)."""
    units = facts.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {})
    if "USD" not in units:
        return pd.DataFrame(columns=["start", "end", "val", "form", "filed", "fy", "fp"])
    frame = pd.DataFrame(units["USD"])
    for column in ("start", "end", "filed"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    if "start" not in frame.columns:
        frame["start"] = pd.NaT
    keep = ["start", "end", "val", "form", "filed"]
    for column in ("fy", "fp"):
        if column in frame.columns:
            keep.append(column)
    return frame[keep].copy()


def annual_observations(facts: dict) -> pd.DataFrame:
    """Point-in-time annual 10-K observations for the accruals signal.

    One row per fiscal-year end that has all three required tags filed on the
    same 10-K accession window; ``filed`` is the acceptance date of the
    earliest accession that supplied the final value, and the row is only
    usable from that date onward.
    """
    columns = ["end", "filed", "ni", "cfo", "assets", "accruals", "asset_growth"]
    series: dict[str, pd.DataFrame] = {}
    for tag in DURATION_TAGS:
        frame = tag_rows(facts, tag)
        if frame.empty:
            return pd.DataFrame(columns=columns)
        frame = frame[frame["form"] == "10-K"].dropna(subset=["end", "filed", "val"])
        if frame.empty:
            return pd.DataFrame(columns=columns)
        days = (frame["end"] - frame["start"]).dt.days
        frame = frame[(days >= MIN_ANNUAL_DAYS) & (days <= MAX_ANNUAL_DAYS)]
        if frame.empty:
            return pd.DataFrame(columns=columns)
        series[tag] = frame.sort_values("filed").drop_duplicates("end", keep="first")
    for tag in INSTANT_TAGS:
        frame = tag_rows(facts, tag)
        if frame.empty:
            return pd.DataFrame(columns=columns)
        frame = frame[frame["form"] == "10-K"].dropna(subset=["end", "filed", "val"])
        if frame.empty:
            return pd.DataFrame(columns=columns)
        series[tag] = frame.sort_values("filed").drop_duplicates("end", keep="first")

    base = series["NetIncomeLoss"][["end", "val", "filed"]].rename(
        columns={"val": "ni", "filed": "ni_filed"}
    )
    base = base.merge(
        series["NetCashProvidedByUsedInOperatingActivities"][["end", "val", "filed"]].rename(
            columns={"val": "cfo", "filed": "cfo_filed"}
        ),
        on="end",
        how="inner",
    )
    base = base.merge(
        series["Assets"][["end", "val", "filed"]].rename(
            columns={"val": "assets", "filed": "assets_filed"}
        ),
        on="end",
        how="inner",
    )
    if base.empty:
        return pd.DataFrame(columns=columns)
    base["filed"] = base[["ni_filed", "cfo_filed", "assets_filed"]].max(axis=1)
    base = base.sort_values("end").reset_index(drop=True)
    previous = base["assets"].shift(1)
    average_assets = (base["assets"] + previous) / 2.0
    usable = average_assets > 0
    base["accruals"] = ((base["ni"] - base["cfo"]) / average_assets).where(usable)
    base["asset_growth"] = (base["assets"] / previous - 1.0).where(previous > 0)
    return base[columns]


def coverage(facts: dict, symbol: str = "") -> dict:
    """Summarise annual-fact availability and filing lag for one company."""
    observations = annual_observations(facts)
    lags = (observations["filed"] - observations["end"]).dt.days if len(observations) else None
    return {
        "symbol": symbol,
        "has_annual_data": bool(len(observations)),
        "annual_observations": int(len(observations)),
        "first_end": str(observations["end"].min().date()) if len(observations) else "",
        "last_end": str(observations["end"].max().date()) if len(observations) else "",
        "first_filed": str(observations["filed"].min().date()) if len(observations) else "",
        "last_filed": str(observations["filed"].max().date()) if len(observations) else "",
        "usable_accruals": int(observations["accruals"].notna().sum()) if len(observations) else 0,
        "usable_asset_growth": int(observations["asset_growth"].notna().sum())
        if len(observations)
        else 0,
        "median_filing_lag_days": float(lags.median()) if lags is not None and len(lags) else None,
    }


def probe(
    symbols: list[str] | tuple[str, ...] | None = None,
    cache_dir: Path | str | None = None,
    *,
    fetch: bool = True,
    refresh: bool = False,
) -> dict:
    """Download (or reuse) companyfacts for ``symbols`` and report coverage."""
    symbols = list(symbols if symbols is not None else UNIVERSE)
    mapping = load_ticker_cik_map(cache_dir_for(cache_dir) / "company_tickers.json", fetch=fetch)
    rows = []
    missing: list[str] = []
    for symbol in symbols:
        cik = mapping.get(symbol.upper())
        if cik is None:
            missing.append(symbol)
            continue
        try:
            facts = cached_companyfacts(cik, cache_dir, fetch=fetch, refresh=refresh)
        except FileNotFoundError:
            missing.append(symbol)
            continue
        row = coverage(facts, symbol)
        row["cik"] = cik
        rows.append(row)
    frame = pd.DataFrame(rows)
    usable = frame[frame["usable_accruals"] >= 2] if len(frame) else frame
    zero_annual = [row["symbol"] for row in rows if not row["has_annual_data"]]
    return {
        "source": "SEC XBRL companyfacts",
        "companyfacts_url_template": COMPANYFACTS_URL,
        "ticker_map_url": TICKER_MAP_URL,
        "pit_field": "filed (acceptance date per reported fact)",
        "symbols_requested": len(symbols),
        "symbols_with_bundle": int(len(frame)),
        "symbols_with_annual_data": int(frame["has_annual_data"].sum()) if len(frame) else 0,
        "symbols_with_two_plus_accrual_observations": int(len(usable)),
        "symbols_with_zero_annual_observations": zero_annual,
        "missing_bundles": missing,
        "median_filing_lag_days": float(usable["median_filing_lag_days"].median())
        if len(usable)
        else None,
        "first_filed": str(usable["first_filed"].min()) if len(usable) else "",
        "last_filed": str(usable["last_filed"].max()) if len(usable) else "",
        "per_symbol": rows,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--symbols", nargs="*", default=None, help="subset of tickers to probe")
    parser.add_argument("--limit", type=int, default=None, help="probe only the first N")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--refresh", action="store_true", help="re-download cached bundles")
    parser.add_argument("--download-only", action="store_true", help="populate the cache and exit")
    parser.add_argument("--out", default=None, help="write the JSON report here")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    args = _parse_args(argv)
    symbols = list(args.symbols) if args.symbols else list(UNIVERSE)
    if args.limit is not None:
        symbols = symbols[: args.limit]
    report = probe(symbols, args.cache_dir, refresh=args.refresh)
    if args.download_only:
        report = {
            key: report[key]
            for key in ("symbols_requested", "symbols_with_bundle", "missing_bundles")
        }
    text = json.dumps(report, indent=2)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n")
    print(text)
    return report


if __name__ == "__main__":
    main()
