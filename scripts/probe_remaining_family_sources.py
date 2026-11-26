#!/usr/bin/env python3
"""Free-data availability probe: remaining repo-new strategy-family sources.

Why this exists
---------------
H1-H201 are exhausted/rejected (see ``HYPOTHESIS_SPEC.md`` / ``AGENTS.md``). The
handoff's remaining genuinely-distinct, repo-new mechanism candidates each need a
*new* free data source (options positioning, fund share flow, macro surprises) or
a different asset class; parameter/universe/timeframe variants of the exhausted
equity cross-sections (H187-H201) are not new families (directive §2). Before a
candidate can be pre-registered, directive §6 requires probing the *named* source
-- a mechanism may not be declared "data-blocked" without a reproducible probe.

This script records, reproducibly, the reachability and bounded-parseability of
each remaining candidate source so a later cycle does not re-run the same ad-hoc
exploration:

  * CBOE options (per-symbol delayed chains / put-call) -- options-flow family.
  * FRED macro series (breakeven inflation, real yield)    -- macro-surprise family.
  * SEC Form N-CEN (fund share flows, Item C)              -- fund-flow family.
  * SEC Form N-PORT (monthly fund holdings)                -- fund-holdings family.

For N-CEN the probe enumerates *every* document in the filing directory (via the
filing ``index.json``) and scans *all* XML exhibits -- not just ``primary_doc.xml``
-- for shareholder-flow fields.  This settles the "heavier multi-exhibit parser"
question with evidence: an N-CEN filing is a structural census (series/classes,
shares outstanding, custodians, transfer agents, securities lending); it carries no
shareholder sales/redemptions flow item and no additional data exhibit, so the
fund-flow family is not free-sourceable from N-CEN (see ``N_CEN_FLOW_FINDING``).

It is read-only: it downloads to memory and writes only a JSON report (stdout, or
``--out``). It touches no experiment artifact, no ``src/qtr``, no gate. The
default report path is under ``.cache/`` (git-ignored) so the probe is
reproducible without perturbing the committed artifact inventory.

Exit code is 0 if at least one candidate source is reachable (HTTP 200), else 1,
so the probe cannot silently pass while every source it is meant to verify is
unreachable.

Usage
-----
    python scripts/probe_remaining_family_sources.py
    python scripts/probe_remaining_family_sources.py --out .cache/remaining_sources.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    from qtr.data.insider import (
        filing_document_url,
        normalize_cik,
        submissions_url,
        user_agent,
    )
except ImportError:  # allow `python scripts/...` with no editable install
    sys.path.insert(0, str(ROOT / "src"))
    from qtr.data.insider import (
        filing_document_url,
        normalize_cik,
        submissions_url,
        user_agent,
    )

DEFAULT_TIMEOUT = 30.0
DEFAULT_OUT = Path(".cache") / "remaining_family_sources.json"

# CBOE public delayed-quotes CDN (per-symbol chains). Historically 403 to
# non-browser clients; probed here so the options-flow family is not re-declared
# blocked without evidence.
CBOE_PROBE_URLS = [
    "https://cdn.cboe.com/api/global/delayed_quotes/chains/SPX.json",
]

# FRED CSV series (free, no key). Breakeven inflation (T10YIE) and 10y real
# yield (DFII10) are the macro-surprise inputs a cross-section would need.
FRED_SERIES = ["T10YIE", "DFII10"]

# Large fund trusts that file both N-CEN (annual share-flow) and NPORT-P
# (monthly holdings). CIKs resolved from SEC company search; fixed for
# reproducibility.
FUND_TRUST_CIKS = {
    "0001137360": "BlackRock Funds",
    "0000036405": "Vanguard World Fund",
}

# N-CEN Item C "net asset flow" tag names (shareholder sales/redemptions). If
# none appear in *any* XML exhibit of the filing, the shareholder-flow signal is
# not sourceable from that filing.  These are the canonical N-CEN flow field
# names; the probe confirms empirically that no N-CEN exhibit carries them.
NCEN_FLOW_TAGS = (
    "netAssetFlow",
    "NetAssetFlow",
    "monthlyNetAssetFlow",
    "totalRedemptions",
    "totalSales",
    "monthlySales",
    "monthlyRedemptions",
    "shareholderFlow",
)

# Durable finding (Cycles 311/313/319): the "heavier multi-exhibit parser" path
# (handoff option (a)) rests on a false premise.  Empirically -- across BlackRock
# Funds (0001137360) and Vanguard World Fund (0000036405) N-CEN filings -- the
# filing directory holds only ``primary_doc.xml`` plus index/header/htm files
# (no additional data exhibit), and ``primary_doc.xml`` contains none of the
# shareholder-flow tags above.  The only purchase/sale-like tags are ETF
# creation/redemption *units* (in-kind baskets) and broker-dealer *principal*
# transactions (securities lending) -- neither is a shareholder flow.  N-CEN is a
# structural census, so the fund-flow family is not free-sourceable from it.
N_CEN_FLOW_FINDING = (
    "N-CEN is a structural census: the filing directory carries no additional "
    "data exhibit beyond primary_doc.xml, and no exhibit contains shareholder "
    "sales/redemptions flow fields. The 'heavier multi-exhibit parser' path is a "
    "false premise; the fund-flow family is not free-sourceable from N-CEN."
)


def http_get(url: str, timeout: float = DEFAULT_TIMEOUT) -> bytes:
    """Download ``url`` with a descriptive SEC User-Agent; raise on failure."""
    request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def http_status(url: str, timeout: float = DEFAULT_TIMEOUT) -> tuple[int, int, bytes]:
    """Return ``(status, nbytes, head)`` without raising on HTTP/network errors.

    A non-200 (e.g. CBOE 403) or a network failure is an *expected* probe outcome,
    not a crash, so the probe can report it and continue.
    """
    request = urllib.request.Request(url, headers={"User-Agent": user_agent()})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            head = response.read(256)
            return response.status, len(head), head
    except urllib.error.HTTPError as error:
        return error.code, 0, b""
    except (TimeoutError, urllib.error.URLError):
        return 0, 0, b""


def probe_cboe_options(status_get=http_status) -> dict:
    """Probe CBOE delayed-options CDN reachability (options-flow candidate)."""
    probes = []
    for url in CBOE_PROBE_URLS:
        status, nbytes, _ = status_get(url)
        probes.append({"url": url, "status": status, "reachable": status == 200})
    reachable = any(item["reachable"] for item in probes)
    return {
        "name": "CBOE options (per-symbol delayed chains / put-call)",
        "candidate_family": "options positioning / flow",
        "reachable": reachable,
        "note": (
            "reachable"
            if reachable
            else "CBOE CDN returns non-200 (typically 403) to non-browser clients; "
            "the options-flow family is not free-reachable from this host without a "
            "browser/authorized feed."
        ),
        "probes": probes,
    }


def probe_fred(series_list=None, get=http_get) -> dict:
    """Probe FRED CSV reachability and coverage for macro-surprise inputs."""
    series_list = list(series_list if series_list is not None else FRED_SERIES)
    results = []
    for series in series_list:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
        try:
            text = get(url).decode("utf-8", "replace")
        except Exception as error:  # noqa: BLE001 - probe: report, keep going
            results.append({"series": series, "reachable": False, "error": type(error).__name__})
            continue
        rows = [
            line for line in text.splitlines() if line and not line.startswith("observation_date")
        ]
        first = rows[0].split(",")[0] if rows else ""
        last = rows[-1].split(",")[0] if rows else ""
        results.append(
            {
                "series": series,
                "reachable": True,
                "n_obs": len(rows),
                "first": first,
                "last": last,
            }
        )
    reachable = any(item.get("reachable") for item in results)
    return {
        "name": "FRED macro series",
        "candidate_family": "macro surprise / real-rate",
        "reachable": reachable,
        "note": (
            "macro levels reachable; macro-regime timing is already H175 and a "
            "macro-surprise cross-section still needs consensus/forecast data that "
            "FRED does not distribute for free."
        ),
        "series": results,
    }


def parse_ncen_primary_doc(xml_text: str) -> dict:
    """Namespace-agnostic parse of an N-CEN ``primary_doc.xml``.

    Returns ``parseable`` plus the bounded metadata fields (series count, monthly
    average net assets) and ``flow_present`` -- whether any Item C net-asset-flow
    tag appears. ``flow_present=False`` means the shareholder-flow signal is not
    bounded-parseable from the primary document alone.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {"parseable": False}

    ns = "{*}"

    def first_text(tag: str) -> str | None:
        element = root.find(f".//{ns}{tag}")
        if element is not None and element.text:
            return element.text.strip()
        return None

    flow_present = any(tag in xml_text for tag in NCEN_FLOW_TAGS)
    return {
        "parseable": True,
        "total_series": first_text("totalSeries"),
        "mnthly_avg_net_assets": first_text("mnthlyAvgNetAssets"),
        "flow_present": flow_present,
    }


def _latest_form(recent: dict, prefix: str) -> dict | None:
    """Return the most recent filing whose form starts with ``prefix``."""
    forms = recent.get("form", [])
    count = len(forms)
    for i in range(count):
        if str(forms[i]).upper().startswith(prefix):
            return {
                "accession": recent.get("accessionNumber", [""] * count)[i],
                "form": forms[i],
                "filing_date": recent.get("filingDate", [""] * count)[i],
                "acceptance_datetime": recent.get("acceptanceDateTime", [""] * count)[i],
                "primary_document": recent.get("primaryDocument", [""] * count)[i],
            }
    return None


def _recent_filings(submissions: dict) -> dict:
    return submissions.get("filings", {}).get("recent", {})


def list_filing_documents(cik, accession: str, get=http_get) -> list[str]:
    """Names of every document in a filing directory, from its ``index.json``.

    The index is fetched with the same document-URL builder used for the primary
    document (``index.json`` lives beside ``primary_doc.xml``).  Returns an empty
    list if the index is missing or malformed -- the caller treats that as "no
    additional exhibits enumerable", not a crash.
    """
    try:
        raw = get(filing_document_url(cik, accession, "index.json")).decode("utf-8", "replace")
        index = json.loads(raw)
    except Exception:  # noqa: BLE001 - probe: report, keep going
        return []
    items = index.get("directory", {}).get("item", []) if isinstance(index, dict) else []
    return [
        str(item.get("name", "")) for item in items if isinstance(item, dict) and item.get("name")
    ]


def _scan_flow_in_xml(xml_text: str) -> bool:
    """True if any shareholder-flow tag appears in ``xml_text``."""
    return any(tag in xml_text for tag in NCEN_FLOW_TAGS)


def probe_sec_ncen(ciks=None, get=http_get) -> dict:
    """Probe SEC N-CEN reachability + multi-exhibit shareholder-flow scan.

    For each fund trust the probe resolves the latest N-CEN filing, enumerates
    every document in the filing directory, scans *all* ``.xml`` exhibits for
    shareholder-flow fields, and parses the primary document for bounded
    metadata.  ``flow_present`` is True only if a flow tag appears in *some*
    exhibit; ``documents`` records the full exhibit list so the negative result
    is auditable (it shows there is no additional data exhibit to parse).
    """
    ciks = dict(ciks if ciks is not None else FUND_TRUST_CIKS)
    per_cik = []
    for cik, name in ciks.items():
        record: dict = {"cik": normalize_cik(cik), "name": name, "reachable": False}
        try:
            submissions = json.loads(get(submissions_url(cik)).decode("utf-8"))
            filing = _latest_form(_recent_filings(submissions), "N-CEN")
            if filing is None:
                record["error"] = "no N-CEN filing in recent submissions"
                per_cik.append(record)
                continue
            record["accession"] = filing["accession"]
            record["acceptance_datetime"] = filing["acceptance_datetime"]
            documents = list_filing_documents(cik, filing["accession"], get=get)
            record["documents"] = documents
            xml_docs = [doc for doc in documents if doc.lower().endswith(".xml")]
            record["n_xml_documents"] = len(xml_docs)
            primary_parsed: dict = {}
            flow_present = False
            for doc in xml_docs:
                text = get(filing_document_url(cik, filing["accession"], doc)).decode(
                    "utf-8", "replace"
                )
                if doc == "primary_doc.xml":
                    primary_parsed = parse_ncen_primary_doc(text)
                if _scan_flow_in_xml(text):
                    flow_present = True
            record.update(primary_parsed or {"parseable": False})
            record["flow_present"] = flow_present
            record["reachable"] = bool(primary_parsed.get("parseable"))
        except Exception as error:  # noqa: BLE001 - probe: report, keep going
            record["error"] = type(error).__name__
        per_cik.append(record)

    reachable = any(item["reachable"] for item in per_cik)
    flow_bounded = any(item.get("flow_present") for item in per_cik)
    return {
        "name": "SEC Form N-CEN (fund share flows)",
        "candidate_family": "fund-flow demand pressure",
        "reachable": reachable,
        "flow_bounded": flow_bounded,
        "note": (
            N_CEN_FLOW_FINDING
            if reachable and not flow_bounded
            else "N-CEN reachable; flow presence varies by filer."
        ),
        "per_cik": per_cik,
    }


def probe_sec_nport(ciks=None, get=http_get) -> dict:
    """Probe SEC N-PORT reachability (monthly fund *holdings*, not flows)."""
    ciks = dict(ciks if ciks is not None else FUND_TRUST_CIKS)
    per_cik = []
    for cik, name in ciks.items():
        record: dict = {"cik": normalize_cik(cik), "name": name, "reachable": False}
        try:
            submissions = json.loads(get(submissions_url(cik)).decode("utf-8"))
            filing = _latest_form(_recent_filings(submissions), "NPORT-P")
            if filing is None:
                record["error"] = "no NPORT-P filing in recent submissions"
                per_cik.append(record)
                continue
            record["accession"] = filing["accession"]
            record["acceptance_datetime"] = filing["acceptance_datetime"]
            record["reachable"] = True
        except Exception as error:  # noqa: BLE001 - probe: report, keep going
            record["error"] = type(error).__name__
        per_cik.append(record)
    reachable = any(item["reachable"] for item in per_cik)
    return {
        "name": "SEC Form N-PORT (monthly fund holdings)",
        "candidate_family": "fund-holdings demand pressure",
        "reachable": reachable,
        "note": (
            "N-PORT reachable; it reports monthly holdings, not shareholder flows, "
            "so a flow signal still needs a shares-outstanding / N-CEN cross-reference."
        ),
        "per_cik": per_cik,
    }


def probe(get=http_get, status_get=http_status) -> dict:
    """Run every candidate-source probe and aggregate the reachability verdict."""
    sections = {
        "cboe_options": probe_cboe_options(status_get=status_get),
        "fred_macro": probe_fred(get=get),
        "sec_ncen": probe_sec_ncen(get=get),
        "sec_nport": probe_sec_nport(get=get),
    }
    any_reachable = any(section["reachable"] for section in sections.values())
    return {
        "source": "remaining repo-new strategy-family candidate sources",
        "user_agent": user_agent(),
        "any_reachable": any_reachable,
        "sections": sections,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="write the JSON report here")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = probe()
    text = json.dumps(report, indent=2)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n")
    print(text)
    return 0 if report["any_reachable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
