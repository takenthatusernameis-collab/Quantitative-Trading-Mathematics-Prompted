"""Fetch and cache the H182 insider-transaction corpus from SEC EDGAR.

This is a one-time (cached) data-acquisition step for the H182 runner
(``run_nf_20261110_08_insider_signal.py``). It pulls Form 4 transactions for
the pre-registered universe over the pre-registered window and writes one
parquet frame per symbol to ``.cache/insider/`` so the runner can re-run its
grid search without re-contacting EDGAR.

Point-in-time safety: every transaction row is stamped with the filing's
``acceptance_datetime`` (EDGAR's first-public timestamp) as ``available_at``,
so a backtest bar on day t only sees filings that were public by the close of
day t. The runner shifts signals by one bar on top of that.

Run:
    python scripts/fetch_h182_insider_data.py [--symbols AAPL,MSFT ...]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from qtr.data import insider

CACHE_DIR = Path(".cache/insider")
UNIVERSE = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "NVDA": "0001045810",
    "META": "0001326801",
    "JPM": "0000019617",
    "XOM": "0000034088",
    "JNJ": "0000200406",
    "WMT": "0000104169",
}
START = "2024-06-01"
END = "2026-11-14"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=",".join(UNIVERSE))
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=END)
    ap.add_argument("--delay", type=float, default=0.12)
    ap.add_argument("--cache-dir", default=str(CACHE_DIR))
    args = ap.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    cache = Path(args.cache_dir)
    cache.mkdir(parents=True, exist_ok=True)

    manifest = {"start": args.start, "end": args.end, "symbols": {}, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    t0 = time.time()
    for sym in symbols:
        cik = UNIVERSE[sym]
        out = cache / f"{sym}.parquet"
        if out.exists():
            print(f"{sym}: cached, skipping")
            manifest["symbols"][sym] = {"cik": cik, "rows": len(pd.read_parquet(out)), "cache": str(out), "source": "cache"}
            continue
        tx = insider.fetch_insider_transactions(cik, forms=("4",), start=args.start, end=args.end, delay=args.delay)
        tx.to_parquet(out)
        manifest["symbols"][sym] = {"cik": cik, "rows": len(tx), "cache": str(out), "source": "edgar"}
        print(f"{sym}: {len(tx)} rows in {round(time.time()-t0,1)}s -> {out}")

    (cache / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    total = sum(v["rows"] for v in manifest["symbols"].values())
    print(f"TOTAL: {total} rows for {len(symbols)} symbols in {round(time.time()-t0,1)}s")


if __name__ == "__main__":
    main()