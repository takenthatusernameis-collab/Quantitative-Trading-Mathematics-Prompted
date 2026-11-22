#!/usr/bin/env python3
"""Free-data availability probe: S&P 500 index-membership price leg (NF-18 / H198).

Why this exists
---------------
``NEW_FAMILY_RESEARCH_REGISTER.md`` (Cycles 90-255) has carried the S&P 500
index inclusion/deletion discrete-event mechanism (NF-20261109-18) as
*deferred*: low frequency (~25/yr) plus an "external index-change calendar
dependency" and "removed names are frequently delisted; yfinance does not
reliably serve delisted tickers".

Cycle 255 refuted the *calendar* half of that blocker (free PIT event data
exists on Wikipedia's "Historical components of the S&P 500" table). The
remaining, unprobed blocker was the **price leg**: can a tradable price series
be obtained for the added *and* removed names around their effective dates on
free data (yfinance)? This tool is that probe.

Design
------
1. Fetch the free PIT changes table from Wikipedia ("Historical components of
   the S&P 500"), which lists, per effective date, the added ticker(s) and the
   removed ticker(s) with a stated reason (acquisition / bankruptcy / market-cap
   / spin-off / etc.).
2. Classify each event (added vs removed) and its reason.
3. For a deterministic, dated sample of added and removed tickers, request a
   daily price series from yfinance over a window around the effective date
   (default +/- 252 trading days) and record whether a tradable series is
   returned and how much history it covers around the event.
4. Report coverage fractions per class so a discovery cycle can *verify* the
   price-leg feasibility claim instead of assuming it.

It is read-only: it downloads to memory, writes no cache, and touches no
experiment artifact. The only disk output is an optional JSON coverage
artifact under ``.experiments/`` when ``--write-artifact`` is passed, so the
coverage numbers are durable.

Usage
-----
    python scripts/probe_sp500_membership_priceleg.py                # full probe
    python scripts/probe_sp500_membership_priceleg.py --sample 12    # smaller sample
    python scripts/probe_sp500_membership_priceleg.py --write-artifact

Exit code is non-zero if neither the added nor the removed class yields a
tradable price series for a majority of the sampled events, so the probe cannot
silently pass while the price leg is actually unavailable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

CHANGES_URL = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"
USER_AGENT = "qtr-research/0.1 (research@example.com)"
DEFAULT_WINDOW_DAYS = 252  # ~1 trading year each side of the effective date
MIN_COVERAGE_TO_PASS = 0.60  # fraction of sampled events that need a price series


def _flatten_col(col: object) -> str:
    """Normalise a pandas column label (tuple or string-repr) to 'A_B'."""
    if isinstance(col, tuple):
        parts = [str(part).strip() for part in col]
    else:
        text = str(col).strip()
        if text.startswith("(") and text.endswith(")"):
            inner = text[1:-1]
            parts = [p.strip().strip("'\"") for p in inner.split(",")]
        else:
            parts = [text]
    # Collapse any internal whitespace so "Effective Date" -> "Effective_Date".
    return "_".join(p.replace(" ", "_") for p in parts).strip("_")


def fetch_changes_table(fetch_fn=None) -> pd.DataFrame:
    """Return the Wikipedia S&P 500 changes table as a flat-column DataFrame."""
    fetch = fetch_fn or _http_get
    html = fetch(CHANGES_URL)
    tables = pd.read_html(io.StringIO(html))
    raw = tables[0]
    # Flatten the two-level column header into single strings. pandas may return
    # either tuples or their string repr depending on the version, so normalise
    # both forms before joining the levels with an underscore.
    flat = raw.copy()
    flat.columns = [_flatten_col(col) for col in raw.columns]
    # pandas read_html may duplicate a spanning header cell (e.g. the merged
    # "Effective Date" over two columns) as "...", "... .1".  Strip the suffix
    # and drop duplicate columns so the rename below is unambiguous.
    flat.columns = [c.replace(".1", "") for c in flat.columns]
    flat = flat.loc[:, ~flat.columns.duplicated()]
    flat = flat.rename(
        columns={
            "Effective_Date_Effective_Date": "effective_date",
            "Added_Ticker": "added_ticker",
            "Added_Security": "added_security",
            "Removed_Ticker": "removed_ticker",
            "Removed_Security": "removed_security",
            "Reason_Reason": "reason",
        }
    )
    flat = flat.drop(columns=[c for c in flat.columns if c.startswith("Refs")], errors="ignore")
    flat["effective_date"] = pd.to_datetime(flat["effective_date"], errors="coerce")
    flat = flat.dropna(subset=["effective_date"]).reset_index(drop=True)
    return flat


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def classify_reason(reason: object) -> str:
    """Map a free-text reason to a coarse acquisition/bankruptcy/market-cap bucket."""
    text = ("" if reason is None else str(reason)).lower()
    if "acquir" in text or "merger" in text or "merg" in text or "buy" in text:
        return "acquisition"
    if "bankrupt" in text:
        return "bankruptcy"
    if "market capitalization" in text or "market cap" in text:
        return "market_cap"
    if "spin" in text or "spun" in text:
        return "spin_off"
    if "reorg" in text or "reorganiz" in text:
        return "reorganization"
    return "other"


def _probe_ticker(ticker: str, event_date: dt.date, window_days: int, download_fn) -> dict:
    """Request a price series for one ticker and measure coverage around the event."""
    start = event_date - dt.timedelta(days=int(window_days * 1.6))
    end = event_date + dt.timedelta(days=int(window_days * 1.6))
    row: dict = {
        "ticker": ticker,
        "event_date": event_date.isoformat(),
        "rows": 0,
        "has_data": False,
        "covers_event": False,
        "last_date": None,
        "first_date": None,
    }
    try:
        df = download_fn(
            ticker,
            start=start.isoformat(),
            end=end.isoformat(),
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception as exc:  # noqa: BLE001 - report, do not crash the whole probe
        row["error"] = f"{type(exc).__name__}: {exc}"[:120]
        return row
    if df is None or len(df) == 0:
        return row
    row["has_data"] = True
    row["rows"] = int(len(df))
    row["first_date"] = str(df.index[0].date())
    row["last_date"] = str(df.index[-1].date())
    # Does the series span the effective date (i.e. is it usable for an event study)?
    event_ts = pd.Timestamp(event_date)
    row["covers_event"] = bool(df.index.min() <= event_ts <= df.index.max())
    return row


def _sample_events(frame: pd.DataFrame, per_class: int, min_year: int) -> dict[str, list[dict]]:
    """Pick a deterministic, spread-out sample of added and removed tickers."""
    frame = frame[frame["effective_date"].dt.year >= min_year].copy()
    frame["reason_bucket"] = frame["reason"].map(classify_reason)

    samples: dict[str, list[dict]] = {"added": [], "removed": []}
    for label, col in (("added", "added_ticker"), ("removed", "removed_ticker")):
        sub = frame.dropna(subset=[col]).copy()
        sub = sub[sub[col].astype(str).str.strip() != ""]
        # Deterministic, spread-out pick: sort by date, take every k-th row.
        sub = sub.sort_values("effective_date").reset_index(drop=True)
        n = len(sub)
        if n == 0:
            continue
        k = max(1, n // per_class)
        picks = sub.iloc[::k].head(per_class)
        for _, r in picks.iterrows():
            samples[label].append(
                {
                    "ticker": str(r[col]).strip(),
                    "event_date": r["effective_date"].date(),
                    "reason_bucket": r["reason_bucket"],
                    "reason": str(r.get("reason", ""))[:120],
                }
            )
    return samples


def main(argv: list[str] | None = None, download_fn=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sample",
        type=int,
        default=20,
        help="max sampled tickers per class (added / removed) (default 20)",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=2005,
        help="ignore events before this effective year (default 2005)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help="half-window in calendar days around the event (default 252)",
    )
    parser.add_argument(
        "--write-artifact",
        action="store_true",
        help="write the coverage result as a JSON artifact under .experiments/",
    )
    args = parser.parse_args(argv)

    try:
        import yfinance as yf
    except ImportError:
        print("yfinance is not installed; cannot probe the price leg.", file=sys.stderr)
        return 2

    download = download_fn or yf.download

    try:
        frame = fetch_changes_table()
    except Exception as exc:  # noqa: BLE001
        print(f"could not fetch changes table: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    samples = _sample_events(frame, per_class=args.sample, min_year=args.min_year)
    if not samples["added"] and not samples["removed"]:
        print("no added/removed events parsed from the changes table.", file=sys.stderr)
        return 1

    results: dict[str, list[dict]] = {"added": [], "removed": []}
    for label in ("added", "removed"):
        for ev in samples[label]:
            results[label].append(
                _probe_ticker(ev["ticker"], ev["event_date"], args.window_days, download)
            )

    def _summarize(rows: list[dict]) -> dict:
        n = len(rows)
        with_data = [r for r in rows if r["has_data"]]
        covers = [r for r in rows if r["covers_event"]]
        return {
            "n_sampled": n,
            "n_with_data": len(with_data),
            "n_covers_event": len(covers),
            "frac_with_data": (len(with_data) / n) if n else 0.0,
            "frac_covers_event": (len(covers) / n) if n else 0.0,
        }

    summ = {label: _summarize(results[label]) for label in ("added", "removed")}
    all_rows = results["added"] + results["removed"]
    overall = _summarize(all_rows)

    print("S&P 500 index-membership price-leg availability probe (NF-18 / H198)")
    print(
        f"changes-table window: {args.min_year}+ ; window +-{args.window_days}d ; "
        f"sample<= {args.sample}/class"
    )
    print(f"{'class':<8}{'sampled':>8}{'with_data':>11}{'covers_evt':>12}{'frac_data':>11}")
    for label in ("added", "removed"):
        s = summ[label]
        print(
            f"{label:<8}{s['n_sampled']:>8}{s['n_with_data']:>11}"
            f"{s['n_covers_event']:>12}{s['frac_with_data']:>11.2%}"
        )
    print(
        f"{'ALL':<8}{overall['n_sampled']:>8}{overall['n_with_data']:>11}"
        f"{overall['n_covers_event']:>12}{overall['frac_with_data']:>11.2%}"
    )
    # Print per-class reason breakdown for removed names (the delisting risk lives here).
    removed_reasons: dict[str, int] = {}
    for ev in samples["removed"]:
        removed_reasons[ev["reason_bucket"]] = removed_reasons.get(ev["reason_bucket"], 0) + 1
    if removed_reasons:
        print("removed reason buckets:", removed_reasons)

    # A long/short event study needs BOTH legs. The binding constraint is the
    # weaker leg, so feasibility is governed by the minimum class coverage (not
    # the max), reported alongside the overall (all-events) coverage.
    binding = min(summ["added"]["frac_with_data"], summ["removed"]["frac_with_data"])
    status = (
        "PRICE LEG FEASIBLE"
        if (binding >= MIN_COVERAGE_TO_PASS and overall["frac_with_data"] >= MIN_COVERAGE_TO_PASS)
        else "PRICE LEG BLOCKED"
    )
    print(
        f"\nBinding (min-leg) coverage {binding:.2%}, overall coverage "
        f"{overall['frac_with_data']:.2%} (threshold {MIN_COVERAGE_TO_PASS:.0%}) -> {status}"
    )

    if args.write_artifact:
        summ["overall"] = overall
        summ["binding_min_leg"] = binding
        summ["status"] = status
        _write_artifact(frame, summ, results, args)

    return 0 if status == "PRICE LEG FEASIBLE" else 1


def _write_artifact(
    frame: pd.DataFrame, summ: dict, results: dict, args: argparse.Namespace
) -> None:
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(".experiments") / "nf_runs" / f"nf_20261122_03_sp500_membership_priceleg_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = {
        "probe": "sp500_membership_priceleg",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "changes_url": CHANGES_URL,
        "params": {
            "sample": args.sample,
            "min_year": args.min_year,
            "window_days": args.window_days,
        },
        "summary": summ,
        "results": results,
    }
    with (out_dir / "coverage.json").open("w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)
    print(f"\ncoverage artifact: {out_dir / 'coverage.json'}")


if __name__ == "__main__":
    raise SystemExit(main())
