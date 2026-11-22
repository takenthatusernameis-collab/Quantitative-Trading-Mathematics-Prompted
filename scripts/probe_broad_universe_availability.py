#!/usr/bin/env python3
"""Free-data availability probe: broad, higher-dispersion equity universe (S&P 500/400/600).

Why this exists
---------------
``NEXT_TASK.md`` (Cycles 257-269) records the research program as blocked on a
"universe decision": the only free, offline, point-in-time universe with cached
fundamentals is the 98-name S&P 100 (minus XOM/BKNG), which is survivorship-biased
and low-dispersion, and every equity cross-section on it (H187-H198) was REJECTED.
The handoff turned that into a *maintainer authorization* ask -- "authorize a
higher-dispersion universe file or network (429)" -- and ~15 cycles re-verified a
blocked baseline instead of making progress.

This probe tests the premise behind that ask. The "429 / network blocked" claim came
from raw ``urllib`` requests sent with the default Python ``User-Agent`` (which Yahoo
and SEC rate-limit / refuse). Free *market* data is in fact reachable when a normal
``User-Agent`` is sent, and the project's own yfinance-based ``DataFetcher`` already
works. This tool therefore verifies, reproducibly:

1. **Source reachability** -- Yahoo chart, SEC company tickers, FRED CSV and the
   Wikipedia S&P 500/400/600 constituent lists, each probed with a real User-Agent.
2. **A genuinely broader universe** -- the current S&P 500 (large), S&P 400 (mid)
   and S&P 600 (small) constituents, which together span mega/mid/small cap and so
   carry far more cross-sectional dispersion than the 98-name S&P 100.
3. **Price coverage** -- a bounded, deterministic sample of those names for which a
   daily Yahoo series is actually returned, so a discovery cycle can *verify* that a
   higher-dispersion universe is tradable instead of assuming it is blocked.

Per the Strategy-Family Expansion Directive (section 2) this is **not** a new strategy
family and does **not** pre-register an H-ID: moving an existing signal to a broader
universe is a universe *variant*, not a new mechanism. The output is a data-availability
measurement that resolves the research bottleneck ("is a broader universe reachable for
free?") with evidence.

Design / safety
---------------
* Read-only: no cache writes, no experiment artifact under ``.experiments/nf_runs/``
  (so it cannot perturb the pinned artifact-schema guard). ``--write-artifact`` writes
  a JSON file to a caller-chosen path (default under ``.cache/``, which is gitignored).
* Offline-testable: every network call is injectable (``fetch_fn`` for HTTP,
  ``download_fn`` for prices) so ``tests/test_probe_broad_universe_availability.py``
  makes no request and does not import yfinance (avoiding google.protobuf's
  module-level ``datetime.utcfromtimestamp`` DeprecationWarning under ``-W error``).
* Transient-failure retry: free quote APIs return empty frames for *live* tickers in a
  tight loop -- a rate-limit, not a delisting (see
  ``probe_sp500_membership_priceleg.py``). Each request is retried with a linear
  backoff and the artifact records ``attempts`` so "no data" is distinguishable from
  "recovered after a transient empty".

Usage
-----
    python scripts/probe_broad_universe_availability.py                 # full probe
    python scripts/probe_broad_universe_availability.py --sample 20     # smaller price sample
    python scripts/probe_broad_universe_availability.py --write-artifact
    python scripts/probe_broad_universe_availability.py --write-artifact PATH

Exit code is 0 when every core source is reachable and the sampled price coverage is
at least ``--min-coverage``, non-zero otherwise -- so the probe cannot silently pass
while the data is actually unavailable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

USER_AGENT = "qtr-research/0.1 (research@example.com)"

# The three S&P constituent lists together give a mega/mid/small-cap universe
# (~1500 names), far broader and higher-dispersion than the 98-name S&P 100.
CONSTITUENT_SOURCES = {
    "sp500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "sp400": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "sp600": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}

# Free sources whose reachability gates the whole program. ``core`` sources must be
# reachable for a "reachable" verdict; the rest are informational.
SOURCE_PROBES = {
    "yahoo_chart": "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1d&interval=1d",
    "sec_tickers": "https://www.sec.gov/files/company_tickers.json",
    "fred_csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF",
}

MIN_COVERAGE_TO_PASS = 0.60  # fraction of sampled names that need a price series
DEFAULT_SAMPLE = 30  # bounded price-coverage sample (keeps the probe fast/gentle)


def _http_get(url: str, timeout: float = 15.0) -> tuple[int, bytes]:
    """GET ``url`` with a real User-Agent; return ``(status, body_bytes)``.

    The User-Agent is the whole point: a raw ``urllib`` request with the default
    Python agent is refused / rate-limited (the false "429 / blocked" premise), so
    every probe request carries one.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(resp.status), resp.read()


def check_sources(fetch_fn=None) -> dict[str, dict]:
    """Probe each free source and return ``{name: {ok, status, detail}}``."""
    fetch = fetch_fn or _http_get
    results: dict[str, dict] = {}
    for name, url in SOURCE_PROBES.items():
        try:
            status, body = fetch(url)
            results[name] = {
                "ok": 200 <= status < 300 and len(body) > 0,
                "status": status,
                "bytes": len(body),
            }
        except Exception as exc:  # noqa: BLE001 - a source failure is a data point, not a crash
            results[name] = {
                "ok": False,
                "status": None,
                "detail": f"{type(exc).__name__}: {exc}"[:160],
            }
    return results


def _flatten_col(col: object) -> str:
    """Normalise a pandas column label (tuple or string-repr) to a flat string."""
    if isinstance(col, tuple):
        parts = [str(part).strip() for part in col]
    else:
        text = str(col).strip()
        parts = [text]
    return "_".join(parts).strip()


def _normalize_ticker(ticker: object) -> str:
    """Canonicalise a Wikipedia ticker to the yfinance convention.

    Wikipedia uses ``BRK.B`` / ``BF.B`` class-share dots; yfinance uses ``BRK-B``.
    Strip a leading ``^`` and swap ``.`` -> ``-`` so the same name is fetched the
    same way the rest of the repo does (``DataFetcher.fetch_sp500_constituents``).
    """
    text = str(ticker).strip().upper()
    return text.replace(".", "-").lstrip("^")


def parse_constituents(html: str) -> list[str]:
    """Extract the ``Symbol`` column from a Wikipedia S&P constituents page."""
    tables = pd.read_html(io.StringIO(html))
    # The constituents table is the first table that carries a ``Symbol`` column.
    for table in tables:
        cols = [str(c) for c in table.columns]
        if "Symbol" in cols:
            series = table["Symbol"].dropna().astype(str)
            return sorted({_normalize_ticker(t) for t in series if t.strip()})
    return []


def fetch_constituents(fetch_fn=None) -> dict[str, list[str]]:
    """Fetch and dedup the S&P 500/400/600 constituent lists."""
    fetch = fetch_fn or _http_get
    out: dict[str, list[str]] = {}
    for name, url in CONSTITUENT_SOURCES.items():
        try:
            _status, body = fetch(url)
            out[name] = parse_constituents(body.decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001 - report, keep going
            out[name] = []
            print(
                f"warning: could not parse {name} constituents: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
    return out


def _probe_prices(
    tickers: list[str],
    download_fn,
    max_attempts: int = 3,
    throttle_s: float = 0.5,
) -> dict[str, dict]:
    """Fetch one daily series per ticker and record coverage.

    ``download_fn(ticker, start=..., end=..., progress=False, auto_adjust=False,
    threads=False)`` mirrors the ``yf.download`` signature the price-leg probe
    already uses. Each ticker is retried up to ``max_attempts`` times with a linear
    ``throttle_s`` backoff so a transient rate-limit empty is not recorded as a miss.
    """
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * 3)
    out: dict[str, dict] = {}
    for ticker in tickers:
        row: dict = {
            "ticker": ticker,
            "rows": 0,
            "has_data": False,
            "first_date": None,
            "last_date": None,
            "attempts": 0,
            "transient_failures": 0,
        }
        for attempt in range(1, max(1, max_attempts) + 1):
            row["attempts"] = attempt
            try:
                df = download_fn(
                    ticker,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
            except Exception:  # noqa: BLE001 - retry, then record a miss
                if attempt < max_attempts:
                    row["transient_failures"] += 1
                    time.sleep(throttle_s * attempt)
                    continue
                row["error"] = "download failed"
                break
            if df is None or len(df) == 0:
                if attempt < max_attempts:
                    row["transient_failures"] += 1
                    time.sleep(throttle_s * attempt)
                    continue
                break
            row["has_data"] = True
            row["rows"] = int(len(df))
            try:
                row["first_date"] = str(df.index[0].date())
                row["last_date"] = str(df.index[-1].date())
            except Exception:  # noqa: BLE001 - index may not be datetime-like
                row["first_date"] = row["last_date"] = None
            break
        out[ticker] = row
    return out


def _sample_tickers(tickers: list[str], sample: int) -> list[str]:
    """Deterministic, spread-out sample of ``sample`` tickers."""
    ordered = sorted(tickers)
    n = len(ordered)
    if sample >= n or sample <= 0:
        return ordered
    k = max(1, n // sample)
    return ordered[::k][:sample]


def _summarize_price_rows(rows: dict[str, dict]) -> dict:
    n = len(rows)
    with_data = [r for r in rows.values() if r["has_data"]]
    recovered = [r for r in rows.values() if r.get("transient_failures", 0) and r["has_data"]]
    total_rows = sum(r["rows"] for r in with_data)
    median_rows = sorted(r["rows"] for r in with_data)[len(with_data) // 2] if with_data else 0
    return {
        "n_sampled": n,
        "n_with_data": len(with_data),
        "frac_with_data": (len(with_data) / n) if n else 0.0,
        "n_recovered_after_transient": len(recovered),
        "median_rows_per_name": median_rows,
        "total_rows": total_rows,
    }


def _default_artifact_path() -> Path:
    return Path(".cache") / "broad_universe_availability.json"


def main(argv: list[str] | None = None, fetch_fn=None, download_fn=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sample",
        type=int,
        default=DEFAULT_SAMPLE,
        help=f"price-coverage sample size (default {DEFAULT_SAMPLE})",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=MIN_COVERAGE_TO_PASS,
        help="minimum sampled price coverage to pass (default 0.60)",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="per-ticker request attempts with backoff (default 3)",
    )
    parser.add_argument(
        "--throttle",
        type=float,
        default=0.5,
        help="base backoff seconds between attempts (default 0.5)",
    )
    parser.add_argument(
        "--write-artifact",
        nargs="?",
        const="",
        default=None,
        help="write a JSON artifact to this path (default .cache/broad_universe_availability.json)",
    )
    args = parser.parse_args(argv)

    if download_fn is None:
        # Import lazily only on the live path, so the offline tests never pull in
        # yfinance (and its google.protobuf DeprecationWarning under -W error).
        try:
            import yfinance as yf
        except ImportError:
            print("yfinance is not installed; cannot probe price coverage.", file=sys.stderr)
            return 2
        download = yf.download
    else:
        download = download_fn

    print("Broad higher-dispersion equity universe availability probe (S&P 500/400/600)")
    print(
        f"price-coverage sample <= {args.sample} names ; attempts <= {args.max_attempts} ; user-agent set\n"
    )

    # 1. Source reachability.
    sources = check_sources(fetch_fn=fetch_fn)
    print("Free-source reachability (proper User-Agent):")
    for name, res in sources.items():
        status = res.get("status")
        detail = res.get("detail", "")
        line = f"  {name:<14} {'OK' if res['ok'] else 'FAIL':<4} HTTP {status}"
        if res.get("bytes"):
            line += f"  {res['bytes']} bytes"
        if detail:
            line += f"  {detail}"
        print(line)

    # 2. Constituent universe.
    constituents = fetch_constituents(fetch_fn=fetch_fn)
    universe: set[str] = set()
    for name, tickers in constituents.items():
        print(f"  {name:<14} {len(tickers):>5} constituents")
        universe.update(tickers)
    universe = sorted(universe)
    print(f"  {'UNION':<14} {len(universe):>5} unique tickers\n")

    core_ok = all(res["ok"] for res in sources.values())

    # 3. Price coverage on a bounded sample.
    sample = _sample_tickers(universe, args.sample)
    price_rows = _probe_prices(
        sample, download, max_attempts=args.max_attempts, throttle_s=args.throttle
    )
    price_summary = _summarize_price_rows(price_rows)
    print(
        f"Price coverage: {price_summary['n_with_data']}/{price_summary['n_sampled']} "
        f"({price_summary['frac_with_data']:.1%}) sampled names have a daily series; "
        f"median {price_summary['median_rows_per_name']} rows/name; "
        f"{price_summary['n_recovered_after_transient']} recovered after a transient empty"
    )

    coverage_ok = price_summary["frac_with_data"] >= args.min_coverage
    status = "REACHABLE" if (core_ok and coverage_ok) else "BLOCKED"
    print(
        f"\nCore sources reachable: {core_ok} ; price coverage {price_summary['frac_with_data']:.1%} "
        f">= {args.min_coverage:.0%}: {coverage_ok} -> {status}"
    )

    if args.write_artifact is not None:
        path = Path(args.write_artifact) if args.write_artifact else _default_artifact_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "probe": "broad_universe_availability",
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "user_agent": USER_AGENT,
            "params": {"sample": args.sample, "min_coverage": args.min_coverage},
            "sources": sources,
            "constituents": {k: len(v) for k, v in constituents.items()},
            "universe_size": len(universe),
            "price_coverage": price_summary,
            "price_rows": price_rows,
            "status": status,
        }
        with path.open("w", encoding="utf-8") as fh:
            json.dump(artifact, fh, indent=2)
        print(f"artifact: {path}")

    return 0 if status == "REACHABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
