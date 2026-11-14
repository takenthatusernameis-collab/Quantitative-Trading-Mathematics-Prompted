"""SEC EDGAR insider-transaction data (Form 4), free and point-in-time.

Why this module exists
----------------------
The insider-transaction family was deferred in
``NEW_FAMILY_RESEARCH_REGISTER.md`` (NF-20261110-08) for exactly one reason:
"no free PIT insider source". That blocker does not hold. EDGAR serves the
Form 4 filing index, the filing's acceptance timestamp, and the filing XML
without a key, subscription, or login. What EDGAR does *not* serve is a
vendor-cleaned, deduplicated table, so this module performs the three
point-in-time-critical steps and nothing else:

1. **Discover** a CIK's Form 4 filings, keeping ``acceptanceDateTime`` -- the
   moment the filing first became public, which is the earliest moment the
   transaction could inform a trading decision.
2. **Fetch** the Form 4 XML document for a filing.
3. **Parse** every reported transaction row (derivative and non-derivative)
   into one tidy frame, each row stamped with the *transaction* date, the
   filing's *acceptance* time, and the resulting ``available_at`` timestamp.

What this module deliberately does not do: model a signal, price anything,
deduplicate amended filings, or touch the protected holdout. Those are the
experiment's job and are out of scope here.

Point-in-time rule
------------------
Rule 16a-3(g) requires a Form 4 to be filed before the end of the second
business day following the transaction date. The transaction *date* alone is
therefore not a safe availability stamp: the filing can be up to two business
days later. ``acceptanceDateTime`` (EDGAR's authoritative first-public
timestamp, UTC) is the stamp used for ``available_at``. Any experiment that
shifts on ``transaction_date`` instead would look ahead by up to two business
days, and the disclosure test in this module's suite pins the distinction.

Source contracts (verified 2026-11-14)
-------------------------------------
* ``https://data.sec.gov/submissions/CIK##########.json`` -- columnar JSON;
  ``filings.recent`` holds parallel arrays, older filings live in
  ``filings.files[*]`` pagination documents.
* ``https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json`` --
  the filing directory listing; the Form 4 XML is one of its items (usually
  ``form4.xml``).
* ``https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}``.

SEC requires a descriptive ``User-Agent`` with contact information on every
request and rate-limits at 10 requests/second; set ``QTR_SEC_USER_AGENT`` to
your own contact string and pass ``delay`` when looping over many filings.
"""

import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
from loguru import logger

DEFAULT_USER_AGENT = "qtr-research/0.1 (research@example.com)"
SEC_HOST = "https://data.sec.gov"
ARCHIVE_HOST = "https://www.sec.gov"
FORM4_DOCUMENT_SUFFIX = ".xml"

TRANSACTION_COLUMNS = (
    "cik",
    "accession_number",
    "form",
    "issuer_name",
    "issuer_trading_symbol",
    "reporting_owner",
    "officer_title",
    "is_director",
    "is_officer",
    "is_ten_percent_owner",
    "is_other",
    "security_kind",
    "security_title",
    "transaction_date",
    "transaction_code",
    "transaction_form_type",
    "shares",
    "price_per_share",
    "acquired_disposed",
    "direct_or_indirect",
    "nature_of_ownership",
    "accepted_at",
    "available_at",
)

FILING_COLUMNS = (
    "cik",
    "accession_number",
    "form",
    "filing_date",
    "acceptance_datetime",
    "report_date",
    "primary_document",
)

RECENT_FILING_KEYS = {
    "accessionNumber": "accession_number",
    "form": "form",
    "filingDate": "filing_date",
    "acceptanceDateTime": "acceptance_datetime",
    "reportDate": "report_date",
    "primaryDocument": "primary_document",
}


def _resolve_user_agent(explicit: str | None) -> str:
    """The ``User-Agent`` used for every EDGAR request.

    ``QTR_SEC_USER_AGENT`` wins over the default so a research deployment
    identifies itself with its own contact string, as EDGAR requires.
    """
    return explicit or os.environ.get("QTR_SEC_USER_AGENT") or DEFAULT_USER_AGENT


def user_agent(explicit: str | None = None) -> str:
    """Public alias of :func:`_resolve_user_agent`."""
    return _resolve_user_agent(explicit)


def normalize_cik(cik: str | int) -> str:
    """Return the 10-digit zero-padded CIK EDGAR uses in its URLs."""
    digits = "".join(character for character in str(cik) if character.isdigit())
    if not digits:
        raise ValueError(f"CIK {cik!r} contains no digits")
    return digits.zfill(10)


def submissions_url(cik: str | int) -> str:
    """EDGAR submissions JSON for one CIK."""
    return f"{SEC_HOST}/submissions/CIK{normalize_cik(cik)}.json"


def filing_index_url(cik: str | int, accession_number: str) -> str:
    """Directory listing for one filing (accession numbers are dash-free here)."""
    accession = accession_number.replace("-", "")
    return f"{ARCHIVE_HOST}/Archives/edgar/data/{int(normalize_cik(cik))}/{accession}/index.json"


def filing_document_url(cik: str | int, accession_number: str, document: str) -> str:
    """Direct URL of one document inside a filing."""
    accession = accession_number.replace("-", "")
    return f"{ARCHIVE_HOST}/Archives/edgar/data/{int(normalize_cik(cik))}/{accession}/{document}"


def _http_get(url: str, *, user_agent: str | None = None, timeout: float) -> bytes:
    """One GET with the EDGAR-required header. Network errors propagate."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": _resolve_user_agent(user_agent), "Accept": "*/*"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, *, user_agent: str | None = None, timeout: float = 30.0) -> dict:
    """Fetch and decode one EDGAR JSON document."""
    return json.loads(_http_get(url, user_agent=user_agent, timeout=timeout))


def fetch_text(url: str, *, user_agent: str | None = None, timeout: float = 30.0) -> str:
    """Fetch one EDGAR text/XML document."""
    return _http_get(url, user_agent=user_agent, timeout=timeout).decode("utf-8")


def _recent_column(recent: dict, key: str, count: int) -> list:
    """One ``filings.recent`` array padded to ``count`` entries.

    EDGAR occasionally returns a shorter array than ``accessionNumber``; a
    positional read past the end would raise, so the missing tail is padded
    with blanks instead of dropping the whole CIK.
    """
    values = list(recent.get(key) or [])
    return values[:count] + [""] * (count - len(values))


def _recent_filings(submissions: dict) -> pd.DataFrame:
    """The columnar ``filings.recent`` block as a frame (empty when absent)."""
    recent = (submissions.get("filings") or {}).get("recent") or {}
    if not isinstance(recent, dict) or not recent.get("accessionNumber"):
        return pd.DataFrame(columns=list(FILING_COLUMNS))

    count = len(recent["accessionNumber"])
    frame = pd.DataFrame(
        {target: _recent_column(recent, key, count) for key, target in RECENT_FILING_KEYS.items()}
    )
    for column in FILING_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame["cik"] = ""
    return frame[list(FILING_COLUMNS)]


def fetch_filings(
    cik: str | int,
    *,
    forms: tuple[str, ...] = ("4",),
    start: str | None = None,
    end: str | None = None,
    user_agent: str | None = None,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Form 4 (or other) filings for one CIK, newest first.

    Args:
        cik: CIK as int or string; zero-padding is handled.
        forms: Form types to keep (``"4"``, ``"4/A"``, ``"3"``, ``"5"``).
        start: Inclusive lower bound on ``filing_date`` (``YYYY-MM-DD``).
        end: Inclusive upper bound on ``filing_date`` (``YYYY-MM-DD``).
        user_agent: Overrides ``QTR_SEC_USER_AGENT``.
        timeout: Per-request timeout in seconds.

    Returns:
        A frame with :data:`FILING_COLUMNS`, sorted by ``acceptance_datetime``
        descending. Empty (with the columns) when the CIK has no matching
        filing; pagination beyond ``filings.recent`` is not followed, so a
        CIK's older history requires the pagination documents under
        ``filings.files``.
    """
    submissions = fetch_json(submissions_url(cik), user_agent=user_agent, timeout=timeout)
    frame = _recent_filings(submissions)
    if len(frame) == 0:
        return frame

    frame["form"] = frame["form"].fillna("").astype(str)
    wanted = {form.upper() for form in forms}
    frame = frame[frame["form"].str.upper().isin(wanted)]

    filing_date = frame["filing_date"].fillna("").astype(str)
    mask = pd.Series(True, index=frame.index)
    if start:
        mask &= filing_date >= start
    if end:
        mask &= filing_date <= end

    frame = frame[mask].copy()
    frame["cik"] = normalize_cik(cik)
    frame = frame.assign(
        acceptance_datetime=pd.to_datetime(frame["acceptance_datetime"], errors="coerce", utc=True)
    )
    return frame.sort_values("acceptance_datetime", ascending=False).reset_index(drop=True)


def filing_documents(
    cik: str | int,
    accession_number: str,
    *,
    user_agent: str | None = None,
    timeout: float = 30.0,
) -> dict[str, str]:
    """Map every document name in a filing to its archive URL."""
    index = fetch_json(
        filing_index_url(cik, accession_number), user_agent=user_agent, timeout=timeout
    )
    items = ((index.get("directory") or {}).get("item")) or []
    documents = {}
    for item in items:
        name = item.get("name") if isinstance(item, dict) else None
        if not name:
            continue
        documents[name] = filing_document_url(cik, accession_number, name)
    return documents


def _form4_document(documents: dict[str, str]) -> str | None:
    """The Form 4 XML document URL, or ``None`` when the filing carries none.

    ``form4.xml`` is the conventional name; a filing may instead carry a
    single generated name (``wk-form4_....xml``). Any lone XML document that
    is not an index/header file is accepted in that case, because refusing it
    would silently drop real Form 4s.
    """
    if "form4.xml" in documents:
        return documents["form4.xml"]
    xml_documents = [
        url
        for name, url in documents.items()
        if name.endswith(FORM4_DOCUMENT_SUFFIX) and "index" not in name.lower()
    ]
    if len(xml_documents) == 1:
        return xml_documents[0]
    return None


def _local_name(tag: str) -> str:
    """Strip any XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1]


def _value_text(element: ET.Element | None) -> str:
    """The text of a Form 4 field element (``""`` when absent).

    Two shapes occur: a wrapper whose value lives in a nested ``<value>``
    (``<transactionDate><value>2026-11-10</value></transactionDate>``) and a
    leaf that carries its text directly
    (``<issuerName>Apple Inc.</issuerName>``). Both are read; a wrapper with
    an empty ``<value>`` returns ``""`` rather than the wrapper's whitespace.
    """
    if element is None:
        return ""
    value = element.find("value")
    if value is not None:
        return (value.text or "").strip()
    return (element.text or "").strip()


def _child_text(element: ET.Element, *path: str) -> str:
    """Text of a nested child path, ``""`` when any level is missing."""
    node: ET.Element | None = element
    for name in path:
        if node is None:
            return ""
        node = next(
            (child for child in node if _local_name(child.tag) == name),
            None,
        )
    return _value_text(node)


def _number(text: str) -> float:
    """Parse a Form 4 numeric field; blank text becomes NaN rather than 0.0."""
    if not text:
        return float("nan")
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return float("nan")


def _owner_rows(document: ET.Element) -> list[dict]:
    """Reporting-owner identity and relationship flags, one row per owner."""
    rows = []
    for owner in (child for child in document if _local_name(child.tag) == "reportingOwner"):
        relationship = next(
            (child for child in owner if _local_name(child.tag) == "reportingOwnerRelationship"),
            None,
        )
        flags = {}
        for flag in ("isDirector", "isOfficer", "isTenPercentOwner", "isOther"):
            node = None
            if relationship is not None:
                node = next(
                    (child for child in relationship if _local_name(child.tag) == flag),
                    None,
                )
            flags[flag] = (_value_text(node) or "").lower() == "true"
        officer_title = ""
        if relationship is not None:
            title_node = next(
                (child for child in relationship if _local_name(child.tag) == "officerTitle"),
                None,
            )
            officer_title = _value_text(title_node)
        name = _child_text(owner, "reportingOwnerId", "rptOwnerName")
        rows.append({"reporting_owner": name, "officer_title": officer_title, **flags})
    if not rows:
        rows.append(
            {
                "reporting_owner": "",
                "officer_title": "",
                "isDirector": False,
                "isOfficer": False,
                "isTenPercentOwner": False,
                "isOther": False,
            }
        )
    return rows


def _transaction_rows(table: ET.Element, transaction_tag: str, security_kind: str) -> list[dict]:
    """Transaction rows from one table (non-derivative or derivative).

    The row element differs per table (``nonDerivativeTransaction`` vs
    ``derivativeTransaction``), so the caller names it explicitly instead of
    this function guessing from a shared suffix.
    """
    rows = []
    for transaction in (child for child in table if _local_name(child.tag) == transaction_tag):
        if security_kind == "non_derivative":
            shares = _child_text(transaction, "transactionAmounts", "transactionShares")
            price = _child_text(transaction, "transactionAmounts", "transactionPricePerShare")
        else:
            shares = _child_text(transaction, "underlyingSecurity", "underlyingSecurityShares")
            price = _child_text(transaction, "transactionAmounts", "conversionOrExercisePrice")
        rows.append(
            {
                "security_title": _child_text(transaction, "securityTitle"),
                "transaction_date": _child_text(transaction, "transactionDate"),
                "transaction_code": _child_text(
                    transaction, "transactionCoding", "transactionCode"
                ),
                "transaction_form_type": _child_text(
                    transaction, "transactionCoding", "transactionFormType"
                ),
                "shares": _number(shares),
                "price_per_share": _number(price),
                "acquired_disposed": _child_text(
                    transaction, "transactionAmounts", "transactionAcquiredDisposedCode"
                ),
                "direct_or_indirect": _child_text(
                    transaction, "ownershipNature", "directOrIndirectOwnership"
                ),
                "nature_of_ownership": _child_text(
                    transaction, "ownershipNature", "natureOfOwnership"
                ),
            }
        )
    return rows


def parse_form4(xml_text: str) -> pd.DataFrame:
    """Parse one Form 4 XML document into one row per reported transaction.

    Both the non-derivative and the derivative table are flattened into the
    same schema; ``security_kind`` distinguishes them. Derivative rows carry
    ``underlyingSecurityShares`` and ``conversionOrExercisePrice`` in place of
    transaction shares and price, because a Form 4's derivative table reports
    the underlying rather than the derivative contract.

    Args:
        xml_text: The filing's Form 4 XML text.

    Returns:
        A frame with the parseable columns of :data:`TRANSACTION_COLUMNS`
        (the filing-level identity columns are added by
        :func:`fetch_insider_transactions`). Empty when the document reports
        no transaction.

    Raises:
        ValueError: The text is not well-formed XML or is not an
            ``ownershipDocument``.
    """
    try:
        document = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise ValueError(f"Form 4 XML is not well-formed: {error}") from error
    if _local_name(document.tag) != "ownershipDocument":
        raise ValueError(f"not an ownershipDocument (root is {document.tag!r})")

    issuer = next((child for child in document if _local_name(child.tag) == "issuer"), None)
    issuer_name = _child_text(issuer, "issuerName") if issuer is not None else ""
    issuer_symbol = _child_text(issuer, "issuerTradingSymbol") if issuer is not None else ""

    owners = _owner_rows(document)
    transactions: list[dict] = []
    for kind in ("non_derivative", "derivative"):
        table_name = "nonDerivativeTable" if kind == "non_derivative" else "derivativeTable"
        table = next((child for child in document if _local_name(child.tag) == table_name), None)
        if table is None:
            continue
        for row in _transaction_rows(
            table,
            "nonDerivativeTransaction" if kind == "non_derivative" else "derivativeTransaction",
            kind,
        ):
            row["security_kind"] = kind
            transactions.append(row)

    rows = []
    for transaction in transactions:
        for owner in owners:
            rows.append(
                {
                    "issuer_name": issuer_name,
                    "issuer_trading_symbol": issuer_symbol,
                    "security_kind": transaction["security_kind"],
                    "security_title": transaction["security_title"],
                    "transaction_date": transaction["transaction_date"],
                    "transaction_code": transaction["transaction_code"],
                    "transaction_form_type": transaction["transaction_form_type"],
                    "shares": transaction["shares"],
                    "price_per_share": transaction["price_per_share"],
                    "acquired_disposed": transaction["acquired_disposed"],
                    "direct_or_indirect": transaction["direct_or_indirect"],
                    "nature_of_ownership": transaction["nature_of_ownership"],
                    "reporting_owner": owner["reporting_owner"],
                    "officer_title": owner["officer_title"],
                    "is_director": owner["isDirector"],
                    "is_officer": owner["isOfficer"],
                    "is_ten_percent_owner": owner["isTenPercentOwner"],
                    "is_other": owner["isOther"],
                }
            )

    columns = [
        "issuer_name",
        "issuer_trading_symbol",
        "reporting_owner",
        "officer_title",
        "is_director",
        "is_officer",
        "is_ten_percent_owner",
        "is_other",
        "security_kind",
        "security_title",
        "transaction_date",
        "transaction_code",
        "transaction_form_type",
        "shares",
        "price_per_share",
        "acquired_disposed",
        "direct_or_indirect",
        "nature_of_ownership",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    if len(frame):
        frame["transaction_date"] = pd.to_datetime(frame["transaction_date"], errors="coerce")
        frame["transaction_date"] = frame["transaction_date"].dt.tz_localize(None)
    return frame


def _acceptance_datetime(value: object) -> pd.Timestamp:
    """A tz-naive UTC timestamp from EDGAR's ISO string (or NaT)."""
    if value is None or value == "" or pd.isna(value):
        return pd.NaT
    stamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(stamp):
        return pd.NaT
    return stamp.tz_localize(None)


def fetch_insider_transactions(
    cik: str | int,
    *,
    forms: tuple[str, ...] = ("4", "4/A"),
    start: str | None = None,
    end: str | None = None,
    delay: float = 0.0,
    user_agent: str | None = None,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Every Form 4 transaction a CIK filed in the window, point-in-time safe.

    Each filing contributes its transaction rows stamped with the filing's
    ``acceptance_datetime`` (UTC, tz-naive) as ``available_at`` -- the earliest
    instant the transaction was public. ``accepted_at`` carries the same value
    so a caller can distinguish "when filed" from "when tradable".

    Args:
        cik: CIK as int or string.
        forms: Form types to keep; amendments (``4/A``) are included by
            default, and deduplication against the original is left to the
            experiment because an amendment is itself an information event.
        start: Inclusive lower bound on ``filing_date`` (``YYYY-MM-DD``).
        end: Inclusive upper bound on ``filing_date`` (``YYYY-MM-DD``).
        delay: Seconds to sleep between filing requests; EDGAR allows 10/s.
        user_agent: Overrides ``QTR_SEC_USER_AGENT``.
        timeout: Per-request timeout in seconds.

    Returns:
        One row per transaction, with :data:`TRANSACTION_COLUMNS`; empty (with
        the columns) when nothing was filed in the window. Filings whose
        document list carries no Form 4 XML are skipped with a warning, and a
        filing whose XML does not parse is skipped the same way, so one bad
        filing cannot abort a whole issuer.
    """
    filings = fetch_filings(
        cik,
        forms=forms,
        start=start,
        end=end,
        user_agent=user_agent,
        timeout=timeout,
    )
    if len(filings) == 0:
        return pd.DataFrame(columns=list(TRANSACTION_COLUMNS))

    frames = []
    for row in filings.itertuples(index=False):
        if delay:
            time.sleep(delay)
        try:
            documents = filing_documents(
                row.cik,
                row.accession_number,
                user_agent=user_agent,
                timeout=timeout,
            )
        except Exception as error:  # noqa: BLE001 -- one filing's index is not fatal
            logger.warning(f"{row.accession_number}: index fetch failed: {error}")
            continue

        document_url = _form4_document(documents)
        if document_url is None:
            logger.warning(f"{row.accession_number}: no Form 4 XML document; skipped")
            continue

        try:
            parsed = parse_form4(fetch_text(document_url, user_agent=user_agent, timeout=timeout))
        except Exception as error:  # noqa: BLE001 -- one malformed filing is not fatal
            logger.warning(f"{row.accession_number}: parse failed: {error}")
            continue

        if len(parsed) == 0:
            continue

        accepted_at = _acceptance_datetime(row.acceptance_datetime)
        parsed = parsed.assign(
            cik=row.cik,
            accession_number=row.accession_number,
            form=row.form,
            accepted_at=accepted_at,
            available_at=accepted_at,
        )
        frames.append(parsed[list(TRANSACTION_COLUMNS)])

    if not frames:
        return pd.DataFrame(columns=list(TRANSACTION_COLUMNS))
    return (
        pd.concat(frames, ignore_index=True)
        .sort_values(["available_at", "transaction_date"], na_position="last")
        .reset_index(drop=True)
    )


def insider_net_buy_ratio(transactions: pd.DataFrame) -> pd.DataFrame:
    """Daily insider net-buy ratio aggregated from Form 4 transaction rows.

    The ratio is ``(open-market purchases) / (open-market purchases + open-market
    sales)`` on the *available* date, so a sale-heavy filing day scores below
    0.5. Only open-market ``P``/``S`` codes count: ``A`` (grant), ``M``
    (exercise), ``G`` (gift), ``F`` (tax withholding), and ``C`` (conversion)
    are not discretionary trades and would dominate the ratio if included.

    Rows are grouped on ``available_at`` (the filing acceptance date), never on
    ``transaction_date``: the latter is up to two business days earlier and
    using it would look ahead.
    """
    if len(transactions) == 0:
        return pd.DataFrame(columns=["available_at", "buys", "sells", "net_buy_ratio"])

    open_market = transactions[transactions["transaction_code"].isin(["P", "S"])].copy()
    if len(open_market) == 0:
        return pd.DataFrame(columns=["available_at", "buys", "sells", "net_buy_ratio"])

    open_market["available_at"] = pd.to_datetime(open_market["available_at"]).dt.date
    open_market["is_buy"] = open_market["transaction_code"].eq("P")
    grouped = open_market.groupby("available_at", as_index=False).agg(
        buys=("is_buy", "sum"),
        rows=("is_buy", "size"),
    )
    grouped["sells"] = grouped["rows"] - grouped["buys"]
    grouped["net_buy_ratio"] = grouped["buys"] / grouped["rows"]
    grouped["available_at"] = pd.to_datetime(grouped["available_at"])
    return grouped[["available_at", "buys", "sells", "net_buy_ratio"]].sort_values("available_at")


def load_cached_transactions(path: str | Path) -> pd.DataFrame:
    """Load a cached transaction frame, treating an unusable cache as a miss.

    A cache file that is absent, unreadable, or has no rows is returned as an
    empty frame with :data:`TRANSACTION_COLUMNS`, so a caller re-fetches
    instead of skipping a failed acquisition forever. This repairs the observed
    failure in which a transient EDGAR outage wrote a zero-row parquet that the
    corpus builder then treated as a valid cache and never refreshed, silently
    dropping that issuer's history.

    Args:
        path: Parquet file written by the corpus builder.

    Returns:
        The cached frame, or an empty frame with :data:`TRANSACTION_COLUMNS`.
    """
    empty = pd.DataFrame(columns=list(TRANSACTION_COLUMNS))
    cache_path = Path(path)
    if not cache_path.exists():
        return empty
    try:
        frame = pd.read_parquet(cache_path)
    except Exception as error:  # noqa: BLE001 -- a corrupt cache is a miss, not fatal
        logger.warning(f"{cache_path}: unreadable cache, treating as a miss: {error}")
        return empty
    if len(frame) == 0:
        return empty
    return frame
