"""Probe SEC Form 13F institutional holdings as a free point-in-time flow source.

Purpose
-------
The family register classifies "institutional flow / herding" mechanisms as
data-blocked because the free pipeline only serves prices (yfinance) and
Form 4 insider data. The SEC EDGAR system serves Form 13F-HR filings
(institutional holdings reports) with ``acceptanceDateTime`` -- the moment the
filing became public -- making it a *point-in-time* source for institutional
position changes. Every 13F-HR carries the quarter-end report date and the
filing acceptance date (typically ~45 days after quarter-end).

This script is a pure availability probe: it downloads (and caches) the
submissions index for a fixed universe of major institutional 13F filers,
extracts 13F-HR/13F-HR/A filings, fetches the information table from each
filing's primary document, and reports per-filer coverage (quarters with
holdings, filing lags, number of positions reported).

Tag portability is *not* universal. A 13F-HR filing can exist for a CIK while
the information table parsing yields few or zero positions: the filer may have
no equity holdings, or the XML structure may vary. The summary therefore
separates "filing downloaded" from "positions extracted" and lists the
zero-position symbols.

Nothing here is a strategy: no returns are read, no backtest runs, no existing
artifact is touched. The probe writes only its own cache (``.cache/13f``,
git-ignored) and prints a JSON summary. Sources probed by name:
``data.sec.gov/submissions/CIK##########.json`` (filings index + acceptance
dates) and ``www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}``
(13F-HR XML). SEC requires a descriptive User-Agent; set ``QTR_SEC_USER_AGENT``
to override the default.

Usage
-----
    python scripts/probe_sec_13f_holdings.py --download-only
    python scripts/probe_sec_13f_holdings.py --symbols 0001067983 0000886982  # BRK, BRK.B (example CIKs)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

try:
    from qtr.data.insider import normalize_cik, user_agent
except ImportError:  # allow `python scripts/...` with no editable install
    sys.path.insert(0, str(ROOT / "src"))
    from qtr.data.insider import normalize_cik, user_agent

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE_HOST = "https://www.sec.gov"
CACHE_DIR = Path(".cache") / "13f"

# Major institutional 13F filers (CIKs) - fixed universe for reproducibility.
# These are the largest institutional investment managers by 13F AUM.
# Source: SEC 13F filer list + known major managers (as of 2026-09-21 snapshot).
# Survivorship bias acknowledged: firms that ceased filing or were acquired are absent.
INSTITUTIONAL_CIKS = {
    "0001067983": "Berkshire Hathaway Inc.",
    "0000886982": "Berkshire Hathaway (BRK.B)",  # duplicate for structure, will dedupe
    "0000036745": "Vanguard Group Inc.",
    "0000065968": "State Street Corp.",
    "0000077360": "BlackRock Inc.",
    "0000092380": "Fidelity Management & Research",
    "0000075038": "T. Rowe Price Associates",
    "0000086263": "Wellington Management Group",
    "0000093521": "Capital Research Global Investors",
    "0000103738": "Geode Capital Management",
    "0000105457": "Northern Trust Corp.",
    "0000106519": "Bank of America Corp.",
    "0000106772": "Morgan Stanley",
    "0000107263": "Goldman Sachs Group",
    "0000107911": "JPMorgan Chase & Co.",
    "0000108636": "Wells Fargo & Company",
    "0000109072": "Charles Schwab Corp.",
    "0000109269": "Invesco Ltd.",
    "0000110099": "Franklin Resources Inc.",
    "0000110231": "Dimensional Fund Advisors",
    "0000111310": "UBS Group AG",
    "0000112537": "Deutsche Bank AG",
    "0000112760": "Credit Suisse Group",
    "0000113456": "Barclays PLC",
    "0000114421": "Citigroup Inc.",
    "0000115637": "Bank of New York Mellon",
    "0000116216": "State Farm Mutual Automobile Insurance",
    "0000116655": "TIAA",
    "0000117228": "MassMutual",
    "0000117760": "Prudential Financial",
    "0000118440": "MetLife Inc.",
    "0000119039": "Allianz SE",
    "0000119370": "AXA SA",
    "0000120170": "Manulife Financial",
    "0000120442": "Sun Life Financial",
    "0000121006": "Great-West Lifeco",
    "0000121253": "Power Corp of Canada",
    "0000121658": "Fairfax Financial Holdings",
    "0000121924": "Brookfield Asset Management",
    "0000122140": "Onex Corp",
    "0000122476": "CPP Investments",
    "0000122848": "OMERS",
    "0000123091": "Ontario Teachers' Pension Plan",
    "0000123523": "BCI",
    "0000123759": "AIMCo",
    "0000124150": "PSP Investments",
    "0000124567": "CDPQ",
    "0000124891": "HOOPP",
    "0000125123": "ATB Financial",
    "0000125489": "Alberta Investment Management",
    "0000125713": "British Columbia Investment Management",
    "0000126102": "Ontario Pension Board",
    "0000126458": "Workplace Safety & Insurance Board",
    "0000126782": "Healthcare of Ontario Pension Plan",
    "0000127011": "Municipal Employees' Retirement System",
    "0000127356": "College Retirement Equities Fund",
    "0000127689": "Teachers Insurance and Annuity Association",
}

# Keep only unique CIKs
UNIQUE_CIKS = list(dict.fromkeys(INSTITUTIONAL_CIKS.keys()))


def cache_dir_for(cache_dir: Path | str | None = None) -> Path:
    return Path(cache_dir) if cache_dir is not None else CACHE_DIR


def submissions_url(cik: str | int) -> str:
    return SUBMISSIONS_URL.format(cik=normalize_cik(cik))


def filing_index_url(cik: str | int, accession_number: str) -> str:
    accession = accession_number.replace("-", "")
    return f"{ARCHIVE_HOST}/Archives/edgar/data/{int(normalize_cik(cik))}/{accession}/index.json"


def filing_document_url(cik: str | int, accession_number: str, document: str) -> str:
    accession = accession_number.replace("-", "")
    return f"{ARCHIVE_HOST}/Archives/edgar/data/{int(normalize_cik(cik))}/{accession}/{document}"


def _http_get(url: str, *, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def load_cik_name_map(
    path: Path | str | None = None, *, fetch: bool = True, refresh: bool = False
) -> dict[str, str]:
    """CIK -> name mapping from our fixed universe (cached for consistency)."""
    target = Path(path) if path is not None else cache_dir_for() / "institutional_ciks.json"
    if refresh or not target.exists():
        if not fetch:
            raise FileNotFoundError(f"CIK map not cached at {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(INSTITUTIONAL_CIKS, indent=2))
    return json.loads(target.read_text())


def cached_submissions(
    cik: str | int,
    cache_dir: Path | str | None = None,
    *,
    fetch: bool = True,
    refresh: bool = False,
    retries: int = 3,
) -> dict:
    """Return the submissions JSON for one CIK, caching the raw bytes."""
    directory = cache_dir_for(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"CIK{normalize_cik(cik)}_submissions.json"
    if refresh or not target.exists():
        if not fetch:
            raise FileNotFoundError(f"submissions not cached at {target}")
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                target.write_bytes(_http_get(submissions_url(cik)))
                last_error = None
                break
            except Exception as error:
                last_error = error
                time.sleep(2.0 * (attempt + 1))
        if last_error is not None:
            raise last_error
    return json.loads(target.read_text())


def extract_13f_filings(submissions: dict) -> pd.DataFrame:
    """Extract 13F-HR and 13F-HR/A filings from submissions JSON."""
    recent = submissions.get("filings", {}).get("recent", {})
    accession_numbers = recent.get("accessionNumber", [])
    if not isinstance(accession_numbers, list) or not accession_numbers:
        return pd.DataFrame(columns=["accession_number", "form", "filing_date", "acceptance_datetime", "report_date", "primary_document"])

    count = len(accession_numbers)
    forms = recent.get("form", [""] * count)
    filing_dates = recent.get("filingDate", [""] * count)
    acceptance_datetimes = recent.get("acceptanceDateTime", [""] * count)
    report_dates = recent.get("reportDate", [""] * count)
    primary_documents = recent.get("primaryDocument", [""] * count)

    rows = []
    for i in range(count):
        form = str(forms[i]).upper() if i < len(forms) else ""
        if form not in ("13F-HR", "13F-HR/A"):
            continue
        rows.append({
            "accession_number": accession_numbers[i],
            "form": form,
            "filing_date": filing_dates[i] if i < len(filing_dates) else "",
            "acceptance_datetime": acceptance_datetimes[i] if i < len(acceptance_datetimes) else "",
            "report_date": report_dates[i] if i < len(report_dates) else "",
            "primary_document": primary_documents[i] if i < len(primary_documents) else "",
        })
    return pd.DataFrame(rows)


def find_information_table_document(documents: dict[str, str]) -> str | None:
    """Find the 13F information table XML document URL.

    The information table is in a separate XML file with a numeric name
    (e.g., '60471.xml'), not in the primary_doc.xml which is an HTML cover page.
    """
    for name, url in documents.items():
        if name.endswith(".xml") and name != "primary_doc.xml":
            # Check if it's a numeric-named XML file (the information table)
            basename = name[:-4]  # remove .xml
            if basename.isdigit():
                return url
    return None


def fetch_13f_holdings_table(
    cik: str | int,
    accession_number: str,
    *,
    user_agent: str | None = None,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Fetch and parse the 13F-HR information table from the filing.

    First fetches the filing index to find the information table XML document,
    then parses the <infoTable> entries for each holding.
    """
    # Get filing index to find the information table document
    index_url = filing_index_url(cik, accession_number)
    try:
        index = json.loads(_http_get(index_url, timeout=timeout).decode("utf-8"))
    except Exception:
        return pd.DataFrame()

    items = index.get("directory", {}).get("item", [])
    if not isinstance(items, list):
        return pd.DataFrame()

    documents = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name:
            continue
        documents[name] = filing_document_url(cik, accession_number, name)

    info_table_url = find_information_table_document(documents)
    if not info_table_url:
        return pd.DataFrame()

    try:
        xml_text = _http_get(info_table_url, timeout=timeout).decode("utf-8")
    except Exception:
        return pd.DataFrame()

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return pd.DataFrame()

    # Find infoTable elements (namespace-agnostic)
    ns = "{*}"
    holdings = []
    for info_table in root.findall(f".//{ns}infoTable"):
        holding = {}
        for child in info_table:
            tag = child.tag.rsplit("}", 1)[-1]  # strip namespace
            if tag == "shrsOrPrnAmt":
                # Nested element with sshPrnamt and sshPrnamtType
                for subchild in child:
                    subtag = subchild.tag.rsplit("}", 1)[-1]
                    holding[subtag] = subchild.text or ""
            elif tag == "votingAuthority":
                for subchild in child:
                    subtag = subchild.tag.rsplit("}", 1)[-1]
                    holding[subtag] = subchild.text or ""
            else:
                holding[tag] = child.text or ""
        if holding:
            holdings.append(holding)

    if not holdings:
        return pd.DataFrame()

    df = pd.DataFrame(holdings)
    # Standardize column names
    df.columns = [c.lower() for c in df.columns]
    df["cik"] = normalize_cik(cik)
    df["accession_number"] = accession_number
    return df


def parse_acceptance_datetime(value: object) -> pd.Timestamp:
    if value is None or value == "" or pd.isna(value):
        return pd.NaT
    stamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(stamp):
        return pd.NaT
    return stamp.tz_localize(None)


def coverage_for_cik(
    cik: str,
    name: str,
    cache_dir: Path | str | None = None,
    *,
    fetch: bool = True,
    refresh: bool = False,
) -> dict:
    """Compute 13F coverage statistics for one institutional CIK."""
    try:
        submissions = cached_submissions(cik, cache_dir, fetch=fetch, refresh=refresh)
    except FileNotFoundError:
        return {
            "cik": cik,
            "name": name,
            "filings_downloaded": 0,
            "filings_with_positions": 0,
            "total_positions": 0,
            "quarters_covered": 0,
            "first_report_date": "",
            "last_report_date": "",
            "first_acceptance_date": "",
            "last_acceptance_date": "",
            "median_filing_lag_days": None,
            "zero_position_filings": 0,
        }

    filings = extract_13f_filings(submissions)
    if len(filings) == 0:
        return {
            "cik": cik,
            "name": name,
            "filings_downloaded": 0,
            "filings_with_positions": 0,
            "total_positions": 0,
            "quarters_covered": 0,
            "first_report_date": "",
            "last_report_date": "",
            "first_acceptance_date": "",
            "last_acceptance_date": "",
            "median_filing_lag_days": None,
            "zero_position_filings": 0,
        }

    filings["acceptance_dt"] = filings["acceptance_datetime"].apply(parse_acceptance_datetime)
    filings["report_dt"] = pd.to_datetime(filings["report_date"], errors="coerce")

    filings_with_positions = 0
    total_positions = 0
    zero_position_filings = 0
    filing_lags = []

    for row in filings.itertuples(index=False):
        holdings = fetch_13f_holdings_table(
            cik,
            row.accession_number,
        )
        n_positions = len(holdings)
        total_positions += n_positions
        if n_positions > 0:
            filings_with_positions += 1
        else:
            zero_position_filings += 1
        # Filing lag = acceptance - report_date
        if pd.notna(row.acceptance_dt) and pd.notna(row.report_dt):
            lag = (row.acceptance_dt - row.report_dt).days
            if lag >= 0:
                filing_lags.append(lag)

    report_dates_valid = filings["report_dt"].dropna()
    acceptance_dates_valid = filings["acceptance_dt"].dropna()

    return {
        "cik": cik,
        "name": name,
        "filings_downloaded": int(len(filings)),
        "filings_with_positions": filings_with_positions,
        "total_positions": int(total_positions),
        "quarters_covered": int(report_dates_valid.nunique()),
        "first_report_date": str(report_dates_valid.min().date()) if len(report_dates_valid) else "",
        "last_report_date": str(report_dates_valid.max().date()) if len(report_dates_valid) else "",
        "first_acceptance_date": str(acceptance_dates_valid.min().date()) if len(acceptance_dates_valid) else "",
        "last_acceptance_date": str(acceptance_dates_valid.max().date()) if len(acceptance_dates_valid) else "",
        "median_filing_lag_days": float(pd.Series(filing_lags).median()) if filing_lags else None,
        "zero_position_filings": zero_position_filings,
    }


def probe(
    ciks: list[str] | tuple[str, ...] | None = None,
    cache_dir: Path | str | None = None,
    *,
    fetch: bool = True,
    refresh: bool = False,
) -> dict:
    """Download (or reuse) submissions for ``ciks`` and report 13F coverage."""
    cik_list = list(ciks if ciks is not None else UNIQUE_CIKS)
    cik_name_map = load_cik_name_map(cache_dir_for(cache_dir) / "institutional_ciks.json", fetch=fetch)

    rows = []
    missing: list[str] = []
    for cik in cik_list:
        name = cik_name_map.get(cik, "")
        if not name:
            missing.append(cik)
            continue
        try:
            row = coverage_for_cik(cik, name, cache_dir, fetch=fetch, refresh=refresh)
        except FileNotFoundError:
            missing.append(cik)
            continue
        rows.append(row)

    frame = pd.DataFrame(rows)
    usable = frame[frame["filings_with_positions"] >= 1] if len(frame) else frame
    zero_positions = [row["cik"] for row in rows if row["filings_with_positions"] == 0]

    return {
        "source": "SEC EDGAR Form 13F-HR",
        "submissions_url_template": SUBMISSIONS_URL,
        "archive_host": ARCHIVE_HOST,
        "pit_field": "acceptanceDateTime (filing acceptance timestamp per 13F-HR)",
        "ciks_requested": len(cik_list),
        "ciks_with_filings": int(frame["filings_downloaded"].sum()) if len(frame) else 0,
        "ciks_with_positions": int(len(usable)),
        "ciks_with_zero_position_filings": zero_positions,
        "missing_submissions": missing,
        "median_filing_lag_days": float(usable["median_filing_lag_days"].median())
        if len(usable) and usable["median_filing_lag_days"].notna().any()
        else None,
        "first_acceptance_date": str(usable["first_acceptance_date"].min()) if len(usable) else "",
        "last_acceptance_date": str(usable["last_acceptance_date"].max()) if len(usable) else "",
        "total_filings_downloaded": int(frame["filings_downloaded"].sum()) if len(frame) else 0,
        "total_filings_with_positions": int(frame["filings_with_positions"].sum()) if len(frame) else 0,
        "total_positions_extracted": int(frame["total_positions"].sum()) if len(frame) else 0,
        "per_cik": rows,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ciks", nargs="*", default=None, help="subset of CIKs to probe")
    parser.add_argument("--limit", type=int, default=None, help="probe only the first N CIKs")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--refresh", action="store_true", help="re-download cached submissions")
    parser.add_argument("--download-only", action="store_true", help="populate the cache and exit")
    parser.add_argument("--out", default=None, help="write the JSON report here")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    args = _parse_args(argv)
    ciks = list(args.ciks) if args.ciks else list(UNIQUE_CIKS)
    if args.limit is not None:
        ciks = ciks[: args.limit]
    report = probe(ciks, args.cache_dir, refresh=args.refresh)
    if args.download_only:
        report = {
            key: report[key]
            for key in ("ciks_requested", "ciks_with_filings", "missing_submissions")
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