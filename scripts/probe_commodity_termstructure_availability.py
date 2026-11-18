#!/usr/bin/env python3
"""Free-data availability probe: per-contract commodity term structure.

Why this exists
---------------
``NEW_FAMILY_RESEARCH_REGISTER.md`` (Cycles 96/116/213) keeps the commodity
futures **term-structure carry / roll-yield** candidate (NF-20261114-01)
classified as *data-blocked* because no free point-in-time **per-contract**
price series was found: yfinance ``=F`` tickers are spliced continuous
front-month series, so the roll yield (and hence the term structure) cannot be
recovered from them.

That classification was based on US/EU retail feeds only.  Before accepting it
again, directive §6 requires probing a *materially different* set of sources.
The Chinese futures exchanges publish free, key-less, daily **per-contract**
settlement data as static files:

* SHFE  (Shanghai Futures Exchange)  metals / rubber / bitumen JSON
* INE   (Shanghai Intl. Energy Exchange) crude oil, low-sulphur fuel oil
* CZCE  (Zhengzhou Commodity Exchange) agricultural / chemical text tables
* CFFEX (China Financial Futures Exchange) index & treasury futures CSV

Each file is a full cross-section of *every listed contract month* for that
trading day, so a term structure (and therefore a roll-yield signal) is
directly recoverable and point-in-time (the file is the official settlement
record for that date).

This tool probes reachability and coverage per source/date, then proves a
term structure is derivable by computing the front/second contract spread for
the most liquid product in the cross-section.  It is read-only: downloads go
to memory and no experiment artifact is touched.

Known-blocked sources (probed 2026-11-18, recorded so they are not
re-litigated as "maybe available"):

* ``data.nasdaq.com`` / ``quandl.com`` CHRIS deferred contracts -> HTTP 403
  (Incapsula bot wall; also requires an API key for the current free tier).
* ``www.cmegroup.com`` settlement APIs -> HTTP 403 "IP address is blocked".
* Yahoo ``query1/query2.finance.yahoo.com`` single-contract tickers
  (``CLZ25.NYM``) -> HTTP 429 from this host (and ``=F`` is continuous).
* ``stooq.com`` CSV -> JavaScript bot challenge, no key-less CSV.
* ``www.lme.com`` daily data API -> Cloudflare 403.
* DCE (Dalian) daily quotes POST -> HTTP 412 WAF block.

Usage
-----
    python scripts/probe_commodity_termstructure_availability.py

Exit code is 1 when no source/date yields a parsable cross-section, so the
probe cannot silently pass while the data it is meant to verify is missing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

import pandas as pd

USER_AGENT = "qtr-research/0.1 (research@example.com)"
TIMEOUT_SECONDS = 30.0

PROBE_DATES = [
    dt.date(2010, 1, 4),
    dt.date(2016, 1, 4),
    dt.date(2020, 1, 2),
    dt.date(2024, 1, 2),
    dt.date(2026, 11, 17),
]


@dataclass(frozen=True)
class Source:
    """One exchange cross-section source."""

    key: str
    label: str
    category: str
    parser: str


SOURCES: dict[str, Source] = {
    "SHFE": Source(
        "SHFE",
        "Shanghai Futures Exchange (metals, rubber, bitumen)",
        "industrial metals term structure",
        "json",
    ),
    "INE": Source(
        "INE",
        "Shanghai Intl. Energy Exchange (crude, fuel oil)",
        "energy term structure",
        "json",
    ),
    "CZCE": Source(
        "CZCE",
        "Zhengzhou Commodity Exchange (ags, chemicals)",
        "agricultural/chemical term structure",
        "pipe_text",
    ),
    "CFFEX": Source(
        "CFFEX",
        "China Financial Futures Exchange (index, bonds)",
        "financial futures term structure",
        "cffex_csv",
    ),
}


def source_url(source: str, day: dt.date) -> str:
    """Build the static per-contract cross-section URL for ``source``/``day``."""
    stamp = day.strftime("%Y%m%d")
    if source == "SHFE":
        return f"https://www.shfe.com.cn/data/tradedata/future/dailydata/kx{stamp}.dat"
    if source == "INE":
        return f"https://www.ine.cn/data/tradedata/future/dailydata/kx{stamp}.dat"
    if source == "CZCE":
        return (
            f"http://www.czce.com.cn/cn/DFSStaticFiles/Future/{day.year}/"
            f"{stamp}/FutureDataDaily.txt"
        )
    if source == "CFFEX":
        return (
            f"http://www.cffex.com.cn/sj/hqsj/rtj/{day.year}{day.month:02d}/"
            f"{day.day:02d}/{stamp}_1.csv"
        )
    raise ValueError(f"unknown source: {source!r}")


def fetch(
    source: str,
    day: dt.date,
    timeout: float = TIMEOUT_SECONDS,
    retries: int = 1,
    retry_delay: float = 1.0,
) -> bytes | None:
    """Download one cross-section; ``None`` for 404 (holiday / pre-listing).

    Transient transport failures raise :class:`FetchError` so a connection reset
    is reported as ``UNREACHABLE`` rather than silently read as "no data".  One
    bounded retry absorbs the exchange sites' occasional reset under repeated
    requests; the probe never loops indefinitely.
    """
    attempt = 0
    while True:
        request = urllib.request.Request(
            source_url(source, day), headers={"User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise FetchError(f"{source} {day}: HTTP {error.code}") from error
        except urllib.error.URLError as error:
            if attempt >= retries:
                raise FetchError(f"{source} {day}: {error.reason}") from error
            attempt += 1
            time.sleep(retry_delay)


class FetchError(RuntimeError):
    """Raised when a cross-section exists but could not be retrieved."""


def _clean_number(value: object) -> float | None:
    """Parse ``'1,234.5'`` / ``'1234'`` / floats into a positive float or ``None``."""
    if value is None:
        return None
    text = str(value).replace(",", "").strip()
    if not text or text in {"-", "--"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not pd.notna(number):
        return None
    return number


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=["product", "delivery", "settlement", "open_interest"])
    frame["product"] = frame["product"].astype(str).str.strip().str.upper()
    frame["delivery"] = frame["delivery"].astype(str).str.strip()
    frame["settlement"] = pd.to_numeric(frame["settlement"], errors="coerce")
    frame["open_interest"] = pd.to_numeric(frame["open_interest"], errors="coerce")
    frame = frame[frame["product"].str.fullmatch(r"[A-Z]{1,2}")]
    frame = frame[frame["delivery"].str.fullmatch(r"\d{4,6}")]
    frame = frame[(frame["settlement"] > 0) & (frame["open_interest"] >= 0)]
    return frame.reset_index(drop=True)


def parse_exchange_json(raw: bytes) -> pd.DataFrame:
    """Parse SHFE/INE ``o_curinstrument`` JSON into per-contract rows."""
    payload = json.loads(raw.decode("utf-8", errors="replace"))
    rows = []
    for item in payload.get("o_curinstrument", []):
        group = str(item.get("PRODUCTGROUPID") or "").strip()
        if not group:
            group = str(item.get("PRODUCTID") or "").split("_")[0].strip()
        rows.append(
            {
                "product": group,
                "delivery": str(item.get("DELIVERYMONTH", "")).strip(),
                "settlement": _clean_number(item.get("SETTLEMENTPRICE")),
                "open_interest": _clean_number(item.get("OPENINTEREST")),
            }
        )
    return _frame(rows)


def _decode_text(raw: bytes, encodings: tuple[str, ...] = ("utf-8", "gbk")) -> str:
    """Decode exchange payloads that mix UTF-8 (new) and GBK (legacy) files."""
    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode(encodings[-1], errors="replace")


def _normalize_ymm(digits: str, reference: dt.date | None) -> str:
    """Expand CZCE's 3-digit ``YMM`` contract code to ``YYYYMM``.

    The exchange omits the decade, so ``401`` in a 2024 file is 2024-01 while
    ``001`` in a December 2019 file is 2020-01.  The reference date (the
    cross-section's trade date) resolves the decade unambiguously.
    """
    if len(digits) != 3 or not digits.isdigit():
        return ""
    reference = reference or dt.date.today()
    decade = (reference.year // 10) * 10
    year = decade + int(digits[0])
    if year < reference.year - 1:
        year += 10
    return f"{year:04d}{digits[1:]}"


def parse_pipe_text(raw: bytes, reference: dt.date | None = None) -> pd.DataFrame:
    """Parse CZCE ``FutureDataDaily.txt`` pipe table into per-contract rows."""
    text = _decode_text(raw)
    rows = []
    for line in text.splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 12:
            continue
        code = parts[0]
        if not code or not code[:1].isalpha():
            continue
        digits = "".join(ch for ch in code if ch.isdigit())
        letters = "".join(ch for ch in code if ch.isalpha())
        rows.append(
            {
                "product": letters,
                "delivery": _normalize_ymm(digits, reference),
                "settlement": _clean_number(parts[6]),
                "open_interest": _clean_number(parts[10]),
            }
        )
    return _frame(rows)


def parse_cffex_csv(raw: bytes) -> pd.DataFrame:
    """Parse CFFEX daily CSV (GBK) keeping futures rows only (options dropped)."""
    text = raw.decode("gbk", errors="replace")
    if "<html" in text[:200].lower() or "DOCTYPE" in text[:200].upper():
        return _frame([])
    frame = pd.read_csv(io.StringIO(text))
    frame.columns = [str(column).strip() for column in frame.columns]
    code_column = frame.columns[0]
    rows = []
    for _, record in frame.iterrows():
        code = str(record[code_column]).strip()
        letters = "".join(ch for ch in code if ch.isalpha())
        digits = "".join(ch for ch in code if ch.isdigit())
        if letters not in {"IF", "IH", "IC", "IM", "T", "TF", "TS", "TL"} or len(digits) != 4:
            continue
        rows.append(
            {
                "product": letters,
                "delivery": digits,
                "settlement": _clean_number(record.get("今结算")),
                "open_interest": _clean_number(record.get("持仓量")),
            }
        )
    return _frame(rows)


PARSERS = {
    "json": parse_exchange_json,
    "pipe_text": parse_pipe_text,
    "cffex_csv": parse_cffex_csv,
}


def term_structure(frame: pd.DataFrame) -> dict[str, object]:
    """Summarise a cross-section and compute the front/second contract spread.

    ``spread_bps = (front - second) / second * 1e4`` for the most liquid
    product (highest front-contract open interest).  Positive means the near
    contract trades above the next one (backwardation -> positive roll yield
    for a long position).
    """
    if frame.empty:
        return {
            "contracts": 0,
            "products": 0,
            "curves": 0,
            "sample_product": "",
            "front_delivery": "",
            "second_delivery": "",
            "spread_bps": None,
        }
    stats = (
        frame.groupby("product")
        .agg(contracts=("delivery", "nunique"), open_interest=("open_interest", "sum"))
        .reset_index()
    )
    curves = stats[stats["contracts"] >= 2]
    sample = ""
    spread_bps = None
    front = ""
    second = ""
    if not curves.empty:
        sample = str(curves.sort_values("open_interest", ascending=False).iloc[0]["product"])
        ordered = frame[frame["product"] == sample].sort_values("delivery").head(2)
        if len(ordered) == 2:
            front, second = str(ordered.iloc[0]["delivery"]), str(ordered.iloc[1]["delivery"])
            near = float(ordered.iloc[0]["settlement"])
            far = float(ordered.iloc[1]["settlement"])
            if far > 0:
                spread_bps = (near - far) / far * 1e4
    return {
        "contracts": int(len(frame)),
        "products": int(frame["product"].nunique()),
        "curves": int(len(curves)),
        "sample_product": sample,
        "front_delivery": front,
        "second_delivery": second,
        "spread_bps": spread_bps,
    }


def probe(source: str, day: dt.date, fetch_fn=fetch) -> dict[str, object]:
    """Probe one source/date and report parsable per-contract coverage."""
    meta = SOURCES[source]
    row: dict[str, object] = {
        "source": source,
        "date": day.isoformat(),
        "status": "MISSING",
        "contracts": 0,
        "products": 0,
        "curves": 0,
        "sample_product": "",
        "front_delivery": "",
        "second_delivery": "",
        "spread_bps": None,
        "category": meta.category,
    }
    try:
        raw = fetch_fn(source, day)
    except FetchError:
        row["status"] = "UNREACHABLE"
        return row
    if raw is None:
        return row
    try:
        if meta.parser == "pipe_text":
            frame = parse_pipe_text(raw, reference=day)
        else:
            frame = PARSERS[meta.parser](raw)
    except Exception:
        row["status"] = "UNPARSABLE"
        return row
    summary = term_structure(frame)
    row.update(summary)
    row["status"] = "OK" if summary["contracts"] > 0 else "EMPTY"
    return row


def main(argv: list[str] | None = None, fetch_fn=fetch) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)

    rows = [probe(source, day, fetch_fn) for source in SOURCES for day in PROBE_DATES]
    print("Free-data availability probe: per-contract commodity term structure")
    header = (
        f"{'source':<7}{'date':<12}{'status':<11}{'contracts':>10}"
        f"{'products':>9}{'curves':>7}  {'sample':<7}{'front':<8}{'next':<8}{'spread_bps':>11}"
    )
    print(header)
    for row in rows:
        spread = row["spread_bps"]
        spread_text = f"{spread:>11.1f}" if isinstance(spread, float) else f"{'-':>11}"
        print(
            f"{row['source']!s:<7}{row['date']!s:<12}{row['status']!s:<11}"
            f"{row['contracts']:>10}{row['products']:>9}{row['curves']:>7}  "
            f"{row['sample_product']!s:<7}{row['front_delivery']!s:<8}"
            f"{row['second_delivery']!s:<8}{spread_text}"
        )

    usable = sorted({str(row["source"]) for row in rows if row["status"] == "OK"})
    if not usable:
        print("\nNO USABLE SOURCE: no per-contract cross-section parsed.", file=sys.stderr)
        return 1
    for source in usable:
        dates = [
            str(row["date"]) for row in rows if row["source"] == source and row["status"] == "OK"
        ]
        print(f"\n{source}: {SOURCES[source].label}\n  usable dates: {', '.join(dates)}")
    print(f"\nUsable sources: {', '.join(usable)} ({len(usable)}/{len(SOURCES)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
