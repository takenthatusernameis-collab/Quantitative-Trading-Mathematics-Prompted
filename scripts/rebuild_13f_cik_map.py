"""Rebuild the 13F filer CIK map from the authoritative SEC company_tickers.json.

Usage
-----
    python scripts/rebuild_13f_cik_map.py

Downloads ``https://www.sec.gov/files/company_tickers.json`` (the SEC's official
ticker -> CIK mapping), resolves each target institutional manager name to a CIK
by matching the filing entity title, then verifies each CIK's submissions index
returns HTTP 200 and contains at least one 13F-HR/13F-HR/A filing.

Writes a machine-readable report to ``.cache/13f/cik_map_rebuild.json`` and
prints a summary. Does NOT modify ``scripts/probe_sec_13f_holdings.py`` -- the
author copies verified CIKs into ``INSTITUTIONAL_CIKS`` by hand after review.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
CACHE_DIR = Path(".cache") / "13f"
UA = "qtr research contact@example.com"
REQUEST_DELAY_S = 1.0  # stay well under SEC's ~10 req/s guidance; be conservative

TARGET_MANAGERS = [
    "Berkshire Hathaway Inc",
    "Vanguard Group Inc",
    "State Street Corp",
    "BlackRock Inc",
    "Fidelity Management & Research",
    "T. Rowe Price Associates",
    "Wellington Management Group",
    "Capital Research Global Investors",
    "Geode Capital Management",
    "Northern Trust Corp",
    "Bank of America Corp",
    "Morgan Stanley",
    "Goldman Sachs Group",
    "JPMorgan Chase & Co",
    "Wells Fargo & Company",
    "Charles Schwab Corp",
    "Invesco Ltd",
    "Franklin Resources Inc",
    "Dimensional Fund Advisors",
    "UBS Group AG",
    "Deutsche Bank AG",
    "Credit Suisse Group",
    "Barclays PLC",
    "Citigroup Inc",
    "Bank of New York Mellon",
    "State Farm Mutual Automobile Insurance",
    "TIAA",
    "MassMutual",
    "Prudential Financial",
    "MetLife Inc",
    "Allianz SE",
    "AXA SA",
    "Manulife Financial",
    "Sun Life Financial",
    "Great-West Lifeco",
    "Power Corp of Canada",
    "Fairfax Financial Holdings",
    "Brookfield Asset Management",
    "Onex Corp",
    "CPP Investments",
    "OMERS",
    "Ontario Teachers Pension Plan",
    "BCI",
    "AIMCo",
    "PSP Investments",
    "CDPQ",
    "HOOPP",
    "ATB Financial",
    "Alberta Investment Management",
    "British Columbia Investment Management",
    "Ontario Pension Board",
    "Workplace Safety Insurance Board",
    "Healthcare of Ontario Pension Plan",
    "Municipal Employees Retirement System",
    "College Retirement Equities Fund",
    "Teachers Insurance and Annuity Association",
]


def _http_get(url: str, *, timeout: float = 30.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def load_tickers() -> list[dict]:
    raw = _http_get(TICKERS_URL)
    data = json.loads(raw.decode("utf-8"))
    # company_tickers.json is a dict keyed by integer index -> {cik_str, ticker, title}
    return list(data.values())


def build_title_index(tickers: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for entry in tickers:
        index.setdefault(entry["title"].lower(), []).append(entry)
    return index


def resolve_cik(name: str, title_index: dict[str, list[dict]]) -> int | None:
    """Resolve a manager name to a CIK using title matching.

    Preference order:
      1. exact title match (case-insensitive)
      2. title that starts with the manager name (e.g. "BlackRock, Inc.")
      3. title containing the manager name, preferring the shortest title
         (the operating company rather than a fund/trust)
    """
    key = name.lower().replace("&", "and")
    exact = title_index.get(key)
    if exact:
        return int(exact[0]["cik_str"])

    starts: list[dict] = []
    contains: list[dict] = []
    for title, entries in title_index.items():
        if title.startswith(key):
            starts.extend(entries)
        elif key in title:
            contains.extend(entries)

    for pool in (starts, contains):
        if pool:
            pool.sort(key=lambda e: len(e["title"]))
            return int(pool[0]["cik_str"])
    return None


def cik_has_13f(cik: int) -> tuple[bool, int]:
    """Return (ok, n_13f_filings): submissions 200 and count of 13F-HR/A forms."""
    cik10 = f"{cik:010d}"
    try:
        raw = _http_get(SUBMISSIONS_URL.format(cik=cik10))
    except Exception:
        return False, 0
    data = json.loads(raw.decode("utf-8"))
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    n_13f = sum(1 for f in forms if str(f).upper() in ("13F-HR", "13F-HR/A"))
    return len(forms) > 0, n_13f


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tickers = load_tickers()
    title_index = build_title_index(tickers)

    resolved: dict[str, int] = {}
    unresolved: list[str] = []
    for name in TARGET_MANAGERS:
        cik = resolve_cik(name, title_index)
        if cik is not None:
            resolved[name] = cik
        else:
            unresolved.append(name)

    verified: dict[str, int] = {}
    failed: list[dict[str, object]] = []
    for name, cik in resolved.items():
        ok, n_13f = cik_has_13f(cik)
        time.sleep(REQUEST_DELAY_S)
        if ok and n_13f > 0:
            verified[name] = cik
            print(f"VERIFIED {name:45s} CIK {cik:010d} 13F-HR filings={n_13f}")
        else:
            failed.append({"name": name, "cik": cik, "has_submissions": ok, "n_13f": n_13f})
            print(f"FAILED   {name:45s} CIK {cik:010d} submissions={ok} n_13f={n_13f}")

    report = {
        "source": TICKERS_URL,
        "target_managers": len(TARGET_MANAGERS),
        "resolved_from_tickers": len(resolved),
        "unresolved": unresolved,
        "verified_13f_filers": len(verified),
        "failed_verification": failed,
        "cik_map": {name: f"{cik:010d}" for name, cik in sorted(verified.items())},
    }
    out = CACHE_DIR / "cik_map_rebuild.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nWrote {out}")
    print(f"Verified 13F filers: {len(verified)}/{len(TARGET_MANAGERS)}")
    print(f"Unresolved (not in company_tickers.json): {len(unresolved)}")


if __name__ == "__main__":
    main()
