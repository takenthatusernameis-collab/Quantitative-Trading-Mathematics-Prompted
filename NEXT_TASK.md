# NEXT_TASK — Cycle 55: discovery, pre-register, implement, execute next H-ID after H140

## State (post Cycle 54 / H140)
- **H140 / NF-20261108-01 — SPY timing from monthly options-expiration dealer-flow / pin-proximity regime: REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_01_spy_opx_flow/summary.json` (+ `grid.csv`, `data_meta.json`, timestamp 2026-11-08, 16.25s)
  - Runner: `run_nf_20261108_01_spy_opx_flow.py`
  - Tests: `tests/test_nf_20261108_01_spy_opx_flow.py` (8 passed)
  - Data (free/public yfinance, PIT): SPY daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755); OPX dates = third Friday of each month, computed deterministically (no external market data for signal).
  - Selected (train-only 4-fold WF mean Sharpe 1.003): `z_window=126, entry_scale=2.0, vol_target=0.10`.
  - OOS Val+Test (1029 trades, n=1260): Sharpe **0.888** (fail), PF **1.196** (fail), max DD **-13.45%** (pass), trades **1029** (pass), WF stability **0.887** (pass), worst-regime rolling-252 **-0.727** (fail), benchmark p **0.914** / IR **-0.611** (fail), perturbation **0.970** (pass) → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.759/1.155/-33.72%/1; random-exposure-matched 0.325/1.098/-27.23%/560 (weaker — signal not pure noise); **inverse OPX-flow** 0.158/1.035/-7.86%/1029 (no opposite edge — unlike H138/H139 inverse falsifiers).
  - Repo-new mechanism category (options flow / supply-constraints; no executed NF/H uses monthly OPX proximity). Honest adjacency to H138/H139 z-score de-risking construction class acknowledged. No validated edge under pre-registered design.
  - `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. `ruff check/format` clean. No commit/push.
- **H85–H140 all rejected/recorded.** Next unused H-ID after H140 (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H140, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 54.

## Held / deferred candidates (reassess with concrete evidence, no silent drops)
- **Held:** NF-20261107-49 TLT-SPY realized correlation (3.60, adj correlation class H96/H127/H134/H137 all REJECT — materially different design required); NF-20261107-52 EEM-SPY RV divergence (3.50, adj rejected H138/H139 RV-divergence class); NF-20261107-11 IVOL spread; NF-20261107-14/48 OVX−VIX (same class as H125/H126 — materially different design required); NF-20261107-31 sector breadth.
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy); NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8); NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 same root as NF-11; NF-06-11 CBOE PC ratio **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90).
- Suggested new mechanism categories not yet executed as timing families (verify free-data feasibility): order-flow/auction mechanics, calendar-quarter/holiday effects, index-rebalance flow constraints.

## Precise next task (one task) — Cycle 55 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H140 (H85–H140 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held/deferred pool above with concrete evidence (no silent drops).
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 55 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
