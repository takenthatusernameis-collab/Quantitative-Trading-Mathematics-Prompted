# Next task (2026-11-20, Cycle 235 — new-family discovery: crypto perpetual funding carry)

## State

H1–H189 exhausted/rejected or data-blocked (H187 REJECT 2/8, H188 REJECT 3/8, H189
data-blocked on SEC XBRL gross profitability: 28/29 of 100 names, below 40 minimum).
The SEC XBRL `companyfacts` fundamental source is tapped out across its three
accounting mechanisms. Price-based families (H1–H30, H184–H188) are exhausted per
register.

## Verified evidence (this session)

- `python scripts/probe_binance_funding_availability.py` → 7/7 curated USDT perps
  OK, funding + perp/spot daily kline archives reachable from 2020-01 (BTC/ETH)
  through 2026-10, no geo-block, no key. The earlier "data-blocked" classification
  for NF-20261114-02 (crypto funding carry) was based on the REST API / yfinance
  and is invalidated by the public archive probe.
- `python -m ruff check src tests run_*.py scripts` → clean (baseline unchanged).

## One precise next task

**Implement and run a crypto perpetual funding carry experiment (NF-20261120-04)** using
the Binance public archives:

1. Write `run_nf_20261120_04_crypto_funding_carry.py`. Reuse engine, metrics, gate,
   benchmark and cross-sectional/hysteresis helpers from
   `run_nf_20261119_02_commodity_hedging_pressure.py`. Import archive helpers from
   `scripts/probe_binance_funding_availability.py` — do not fork tag logic.
2. Signal: funding rate (8h) annualized / basis (perp-spot) as carry; long low-funding
   (negative carry paid to shorts), short high-funding. Availability stamp = funding
   settlement timestamp; monthly refresh, forward-filled to daily calendar; skip a
   rebalance with < 5 active names.
3. Universe: the 7 curated USDT perps. Sample 2020-01-01 → 2026-10-31; Train → 2023-12-31;
   Val 2024-01-01 → 2024-12-31; Test protected 2025-01-01 → 2026-10-31.
4. Emit `.experiments/nf_runs/nf_20261120_04_crypto_funding_carry_<timestamp>/summary.json`
   + `grid.csv` + `data_meta.json`; add `tests/test_nf_20261120_04_crypto_funding_carry.py`;
   bump `tests/test_experiment_artifact_schema.py` inventory pins only for the new
   artifact directory (Cycle 219 precedent). Record verdict in register as Cycle 235.
5. If archive download fails (network), record the failure and stop — do not substitute
   a different price source inside the same pre-registered test.

## Approaches already tried / do not repeat

- Do not re-run the binance probe for the same 7 symbols; measurement recorded.
- Do not re-declare crypto funding carry as data-blocked; archives are usable.
- Do not modify .github/workflows/** or weaken any gate/contract test.
- Do not treat parameter/universe variations as a new family; mechanism is funding/basis
  carry (distinct from commodity term-structure carry H184).
