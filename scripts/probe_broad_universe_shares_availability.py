#!/usr/bin/env python3
"""Free-data availability probe: point-in-time shares outstanding for the broad universe.

Why this exists
---------------
``NEXT_TASK.md`` (Cycle 271) recorded the equity cross-section program as blocked on
a single decisive data gap: the one genuinely-distinct, repo-new mechanism not yet
executed is the **market-cap size premium** (no executed H-ID sorts purely by
market cap), but a size signal needs *point-in-time* market cap = shares outstanding
(as filed <= month-end) x close(month-end). Cycle 271 claimed PIT shares for the
~1502-name S&P 500/400/600 universe were unobtainable: ``yfinance.Ticker.get_shares``
is unimplemented and ``Ticker.info['marketCap']`` is current-only (lookahead), so it
framed "fetch PIT shares for ~1502 names" as "a large, slow, rate-limited SEC XBRL
fetch -- not bounded for this session".

That premise is wrong. The SEC ``frames`` API returns **every** reporting entity's
value for one XBRL concept and period in a *single* request
(``data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json``). One request
per quarter returns thousands of entities (measured: 4960 for CY2024Q1I, ~2832 for
CY2024Q4I), so N quarters of PIT shares for the whole broad universe costs N requests
-- a bounded, seconds-scale fetch, not a per-CIK crawl. This probe measures that
coverage reproducibly so a discovery cycle can *verify* the size-premium data path is
feasible instead of re-asserting it is blocked.

Point-in-time semantics
-----------------------
The ``dei:EntityCommonStockSharesOutstanding`` fact is the cover-page shares count of
a 10-K/10-Q. A frames response carries the accession (``accn``) and the instant
(``end``) but *not* the filing acceptance date. For a PIT backtest the shares value
for an instant in quarter Q must be treated as knowable only from a later quarter
(the ~50-day median 10-K/10-Q lag measured in H187/H188 plus a safety margin). This
probe therefore reports coverage *depth* (distinct quarters with an observation per
name) and the request budget, so the downstream runner can apply its own conservative
lag; it does not itself pick a lag or compute any return.

Scope / safety
--------------
Per the Strategy-Family Expansion Directive this is **not** a strategy family and does
**not** pre-register an H-ID: it is a data-availability measurement. Read-only apart
from its own cache (``.cache/broad_shares/``, gitignored) and an optional JSON
artifact under ``.cache/``; it never writes under ``.experiments/nf_runs/`` so the
pinned artifact-schema guard is untouched. Every network call is injectable
(``fetch_fn``) so ``tests/test_probe_broad_universe_shares_availability.py`` makes no
request. Source probed by name: SEC ``frames`` (shares outstanding), SEC
``company_tickers.json`` (ticker -> CIK), and the Wikipedia S&P 500/400/600
constituent lists (universe).

Usage
-----
    python scripts/probe_broad_universe_shares_availability.py
    python scripts/probe_broad_universe_shares_availability.py --quarters 20
    python scripts/probe_broad_universe_shares_availability.py --write-artifact
    python scripts/probe_broad_universe_shares_availability.py --refresh

Exit code is 0 when the core sources are reachable and at least ``--min-coverage`` of
the universe has a shares series with ``--min-quarters`` depth, non-zero otherwise.
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

ROOT = Path(__file__).resolve().parents[1]

try:
    from qtr.data.insider import user_agent
except ImportError:  # allow `python scripts/...` with no editable install
    sys.path.insert(0, str(ROOT / "src"))
    from qtr.data.insider import user_agent

# SEC XBRL frames API: one request returns every entity's value for a concept/period.
FRAMES_URL = "https://data.sec.gov/api/xbrl/frames/dei/EntityCommonStockSharesOutstanding/shares/{period}.json"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"

# The three S&P constituent lists give the same mega/mid/small-cap universe
# (~1500 names) used by scripts/probe_broad_universe_availability.py.
CONSTITUENT_SOURCES = {
    "sp500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "sp400": "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    "sp600": "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
}

CACHE_DIR = Path(".cache") / "broad_shares"

# Defaults: 12 quarters (3y) is enough to prove depth; the whole fetch is ~12 requests.
DEFAULT_QUARTERS = 12
DEFAULT_MIN_QUARTERS = 4
# Feasibility bar: a size cross-section trades only the names that have data, so the
# question is whether the covered subset is large and high-dispersion enough -- not
# whether every name is covered.  80% of the ~1500-name mega/mid/small universe is
# >1000 tradeable names spanning the size spectrum; the residual names are foreign
# issuers, recent IPOs and class-share ticker-map misses that are legitimately
# excludable from a US-equity size book.  (Measured coverage is reported in full so
# this bar is auditable, not a knob hidden behind the verdict.)
DEFAULT_MIN_COVERAGE = 0.80
# SEC rate-limits at 10 req/s; a small per-request pause stays well under that.
REQUEST_PAUSE_S = 0.12


def _http_get(url: str, timeout: float = 30.0) -> bytes:
    """GET ``url`` with a real User-Agent and return the body bytes.

    The User-Agent is the whole point: a raw ``urllib`` request with the default
    Python agent is refused / rate-limited (the false "429 / blocked" premise that
    Cycles 257-269 re-verified). Every probe request carries one.
    """
    request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


# ---------------------------------------------------------------------------
# Universe: Wikipedia S&P 500/400/600 constituent lists
# ---------------------------------------------------------------------------


def _normalize_ticker(ticker: object) -> str:
    """Canonicalise a Wikipedia ticker to the yfinance/SEC dash convention."""
    text = str(ticker).strip().upper()
    return text.replace(".", "-").lstrip("^")


def parse_constituents(html: str) -> list[str]:
    """Extract the ``Symbol`` column from a Wikipedia S&P constituents page."""
    tables = pd.read_html(io.StringIO(html))
    for table in tables:
        cols = [str(c) for c in table.columns]
        if "Symbol" in cols:
            series = table["Symbol"].dropna().astype(str)
            return sorted({_normalize_ticker(t) for t in series if t.strip()})
    return []


def fetch_constituents(fetch_fn=None) -> dict[str, list[str]]:
    """Fetch and dedup the S&P 500/400/600 constituent lists (empty list on failure)."""
    fetch = fetch_fn or _http_get
    out: dict[str, list[str]] = {}
    for name, url in CONSTITUENT_SOURCES.items():
        try:
            _status_body = fetch(url)
            out[name] = parse_constituents(_status_body.decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001 - a source failure is a data point, not a crash
            out[name] = []
            print(
                f"warning: could not parse {name} constituents: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
    return out


# ---------------------------------------------------------------------------
# Ticker -> CIK map (SEC company_tickers.json, cached)
# ---------------------------------------------------------------------------


def load_ticker_cik_map(
    cache_dir: Path | str | None = None,
    *,
    fetch: bool = True,
    refresh: bool = False,
    fetch_fn=None,
) -> dict[str, int]:
    """Ticker -> integer CIK, cached on disk after the first fetch."""
    directory = Path(cache_dir) if cache_dir is not None else CACHE_DIR
    target = directory / "company_tickers.json"
    if refresh or not target.exists():
        if not fetch:
            raise FileNotFoundError(f"ticker map not cached at {target}")
        directory.mkdir(parents=True, exist_ok=True)
        target.write_bytes((fetch_fn or _http_get)(TICKER_MAP_URL))
    raw = json.loads(target.read_text())
    return {str(entry["ticker"]).upper(): int(entry["cik_str"]) for entry in raw.values()}


# ---------------------------------------------------------------------------
# Frames API: shares outstanding per quarter
# ---------------------------------------------------------------------------


def frame_periods(n_quarters: int, end: dt.date | None = None) -> list[str]:
    """The ``n_quarters`` most recently *completed* quarter frames, newest first.

    ``end`` defaults to today; the current (in-progress) quarter is skipped so the
    first period is the last completed quarter. Period strings use the frames
    instant convention ``CY{year}Q{quarter}I``.
    """
    end = end or dt.date.today()
    year, quarter = end.year, (end.month - 1) // 3 + 1
    quarter -= 1  # step back to the most recently completed quarter
    if quarter == 0:
        quarter, year = 4, year - 1
    periods: list[str] = []
    for _ in range(max(0, int(n_quarters))):
        periods.append(f"CY{year}Q{quarter}I")
        quarter -= 1
        if quarter == 0:
            quarter, year = 4, year - 1
    return periods


def fetch_frame(
    period: str, fetch_fn=None, retries: int = 3, throttle_s: float = 0.5
) -> list[dict]:
    """Return the ``data`` list for one frames period (empty list on failure)."""
    fetch = fetch_fn or _http_get
    url = FRAMES_URL.format(period=period)
    last_error: Exception | None = None
    for attempt in range(max(1, retries)):
        try:
            payload = json.loads(fetch(url))
        except Exception as exc:  # noqa: BLE001 - network/HTTP; bounded backoff
            last_error = exc
            if attempt < retries - 1:
                time.sleep(throttle_s * (attempt + 1))
                continue
            print(f"warning: frame {period} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return []
        return list(payload.get("data", []))
    if last_error is not None:  # pragma: no cover - loop always returns above
        print(f"warning: frame {period} failed: {last_error}", file=sys.stderr)
    return []


def fetch_frames(
    periods: list[str], fetch_fn=None, pause_s: float = REQUEST_PAUSE_S
) -> dict[str, list[dict]]:
    """Fetch every period's frame, pausing to respect the SEC rate limit."""
    frames: dict[str, list[dict]] = {}
    for index, period in enumerate(periods):
        frames[period] = fetch_frame(period, fetch_fn=fetch_fn)
        if pause_s and index < len(periods) - 1:
            time.sleep(pause_s)
    return frames


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


def build_shares_panel(frames: dict[str, list[dict]]) -> dict[int, list[dict]]:
    """Collapse per-period frames into ``{cik: [{end, val, period}, ...]}``."""
    panel: dict[int, list[dict]] = {}
    for period, points in frames.items():
        for point in points:
            cik = point.get("cik")
            value = point.get("val")
            end = point.get("end")
            if cik is None or value is None or end is None:
                continue
            panel.setdefault(int(cik), []).append(
                {"end": str(end), "val": float(value), "period": period}
            )
    return panel


def compute_coverage(
    universe: list[str],
    ticker_to_cik: dict[str, int],
    panel: dict[int, list[dict]],
    *,
    min_quarters: int = DEFAULT_MIN_QUARTERS,
) -> dict:
    """Summarise shares-outstanding availability across the universe.

    Reports raw coverage (any observation), depth (distinct quarters per name) and
    the fraction of names meeting ``min_quarters`` -- the depth a PIT size signal
    needs to line up with a monthly rebalance.
    """
    n = len(universe)
    with_any = 0
    with_min_depth = 0
    no_cik = 0
    depths: list[int] = []
    per_name: dict[str, dict] = {}
    for ticker in universe:
        cik = ticker_to_cik.get(ticker)
        if cik is None:
            no_cik += 1
            per_name[ticker] = {"cik": None, "quarters": 0, "has_data": False}
            continue
        obs = panel.get(cik, [])
        quarters = len({row["period"] for row in obs})
        depths.append(quarters)
        has_any = quarters > 0
        with_any += int(has_any)
        with_min_depth += int(quarters >= min_quarters)
        per_name[ticker] = {"cik": cik, "quarters": quarters, "has_data": has_any}
    depths_sorted = sorted(depths)
    median_depth = depths_sorted[len(depths_sorted) // 2] if depths_sorted else 0
    return {
        "universe_size": n,
        "n_with_any_shares": with_any,
        "frac_with_any_shares": (with_any / n) if n else 0.0,
        "n_with_min_quarters": with_min_depth,
        "frac_with_min_quarters": (with_min_depth / n) if n else 0.0,
        "min_quarters": int(min_quarters),
        "n_without_cik": no_cik,
        "median_quarters_per_name": int(median_depth),
        "per_name": per_name,
    }


def _default_artifact_path() -> Path:
    return Path(".cache") / "broad_universe_shares_availability.json"


def main(argv: list[str] | None = None, fetch_fn=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--quarters",
        type=int,
        default=DEFAULT_QUARTERS,
        help=f"most-recent completed quarters to fetch (default {DEFAULT_QUARTERS})",
    )
    parser.add_argument(
        "--min-quarters",
        type=int,
        default=DEFAULT_MIN_QUARTERS,
        help=f"distinct quarters a name needs to count as covered (default {DEFAULT_MIN_QUARTERS})",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=DEFAULT_MIN_COVERAGE,
        help=f"minimum fraction of the universe with shares depth to pass (default {DEFAULT_MIN_COVERAGE})",
    )
    parser.add_argument(
        "--cache-dir", default=None, help="cache directory (default .cache/broad_shares)"
    )
    parser.add_argument(
        "--refresh", action="store_true", help="re-download the ticker map even if cached"
    )
    parser.add_argument(
        "--write-artifact",
        nargs="?",
        const="",
        default=None,
        help="write a JSON artifact (default .cache/broad_universe_shares_availability.json)",
    )
    args = parser.parse_args(argv)

    cache_dir = Path(args.cache_dir) if args.cache_dir else CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    print("Broad-universe PIT shares-outstanding availability probe (SEC frames API)")
    print(f"quarters <= {args.quarters} ; min depth {args.min_quarters} ; user-agent set\n")

    # 1. Universe.
    constituents = fetch_constituents(fetch_fn=fetch_fn)
    universe: set[str] = set()
    for name, tickers in constituents.items():
        print(f"  {name:<8} {len(tickers):>5} constituents")
        universe.update(tickers)
    universe = sorted(universe)
    print(f"  {'UNION':<8} {len(universe):>5} unique tickers")

    if not universe:
        print("\nERROR: no constituents parsed; cannot measure coverage", file=sys.stderr)
        return 2

    # 2. Ticker -> CIK.
    ticker_to_cik = load_ticker_cik_map(cache_dir, refresh=args.refresh, fetch_fn=fetch_fn)
    n_mapped = sum(1 for ticker in universe if ticker in ticker_to_cik)
    print(
        f"  ticker->CIK map: {len(ticker_to_cik)} names; {n_mapped}/{len(universe)} universe names mapped"
    )

    # 3. Frames: shares outstanding per quarter.
    periods = frame_periods(args.quarters)
    frames = fetch_frames(periods, fetch_fn=fetch_fn)
    n_points = sum(len(points) for points in frames.values())
    print(f"  SEC frames: {len(periods)} requests, {n_points} entity-observations")
    for period in periods:
        print(f"    {period}: {len(frames[period])} entities")

    # 4. Coverage.
    panel = build_shares_panel(frames)
    coverage = compute_coverage(universe, ticker_to_cik, panel, min_quarters=args.min_quarters)
    print(
        f"\nPIT shares coverage: {coverage['n_with_any_shares']}/{coverage['universe_size']} "
        f"({coverage['frac_with_any_shares']:.1%}) names have a shares series; "
        f"{coverage['n_with_min_quarters']} ({coverage['frac_with_min_quarters']:.1%}) reach "
        f">= {coverage['min_quarters']} quarters depth; "
        f"median {coverage['median_quarters_per_name']} quarters/name; "
        f"{coverage['n_without_cik']} names without a CIK"
    )

    coverage_ok = coverage["frac_with_min_quarters"] >= args.min_coverage
    status = "REACHABLE" if coverage_ok else "BLOCKED"
    print(
        f"\nMin-depth coverage {coverage['frac_with_min_quarters']:.1%} "
        f"({coverage['n_with_min_quarters']} names) >= {args.min_coverage:.0%} "
        f"feasibility bar: {coverage_ok} -> {status}"
    )
    print(
        f"Request budget: {len(periods)} requests for {len(periods)} quarters of PIT shares "
        f"across all {len(universe)} names (vs a per-CIK companyfacts crawl)."
    )
    if coverage_ok:
        print(
            "=> The Cycle 271 'PIT shares for the broad universe is not bounded' blocker does "
            "NOT hold: a market-cap size cross-section (H199 candidate) is data-feasible."
        )

    if args.write_artifact is not None:
        path = Path(args.write_artifact) if args.write_artifact else _default_artifact_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        artifact = {
            "probe": "broad_universe_shares_availability",
            "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "user_agent": user_agent(),
            "source": "SEC XBRL frames dei/EntityCommonStockSharesOutstanding/shares",
            "frames_url_template": FRAMES_URL,
            "params": {
                "quarters": args.quarters,
                "min_quarters": args.min_quarters,
                "min_coverage": args.min_coverage,
            },
            "constituents": {k: len(v) for k, v in constituents.items()},
            "periods": periods,
            "entity_observations": n_points,
            "coverage": {
                key: coverage[key]
                for key in (
                    "universe_size",
                    "n_with_any_shares",
                    "frac_with_any_shares",
                    "n_with_min_quarters",
                    "frac_with_min_quarters",
                    "min_quarters",
                    "n_without_cik",
                    "median_quarters_per_name",
                )
            },
            "status": status,
        }
        with path.open("w", encoding="utf-8") as fh:
            json.dump(artifact, fh, indent=2)
        print(f"artifact: {path}")

    return 0 if status == "REACHABLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
