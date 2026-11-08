# NEXT_TASK — Cycle 58: discovery, pre-register, implement, execute next H-ID after H143

## State (post Cycle 57 / H143)
- **H143 / NF-20261108-06 — SPY timing from overnight gap realized-volatility regime (liquidity/microstructure): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_06_spy_overnight_gap_rv/summary.json` (+ `grid.csv`, `data_meta.json`, 18.21s)
  - Runner: `run_nf_20261108_06_spy_overnight_gap_rv.py`
  - Tests: `tests/test_nf_20261108_06_spy_overnight_gap_rv.py` (5 passed)
  - Data (free/public yfinance, PIT): SPY daily OHLC (`auto_adjust=False`), 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: `z` of trailing `RV(log(Open/prev Close), rv_window)` over `z_window`; continuous de-risking, 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.7645): `rv_window=63, z_window=126, entry_scale=2.0, vol_target=0.10`.
  - OOS Val+Test (3403 engine trades, n=1260): Sharpe **0.739** fail, PF **1.154** fail, max DD **-1.54%** pass, trades **3403** pass, WF stability **1.007** pass, worst-regime rolling-252 **-1.907** fail, benchmark p **0.930** / IR **-0.661** fail, perturbation **0.932** pass → **4/8 REJECT**. Mean OOS exposure **0.0565** (near-cash).
  - Ablations OOS: buy-hold SPY 0.676/1.137/-34.10%/1 (close-based within run); random-exposure-matched **0.137**/1.030/-2.31%/3776 (much weaker — not noise); **inverse regime** 0.680/1.133/-1.25%/3602 (comparable, no opposite edge; not a validated edge).
  - Honest adjacency: repo-new *overnight gap/jump realized-vol* component (liquidity/microstructure). Distinct from H18/H87 (overnight/gap direction), H121 (Amihud), H136 (close-to-close RV term structure), H122/H128/H132/H135 (total-return higher moments/VoV). No validated edge.
  - `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. `ruff check/format` clean. No commit/push.
- **H85–H143 all rejected/recorded.** Next unused H-ID after H143 (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H143, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 57 outcome, this file.

## Held / deferred candidates (reassess with concrete evidence, no silent drops)
- **Held (materially different design required vs rejected construction classes):** NF-20261107-49 TLT-SPY realized correlation (correlation class H96/H127/H134/H137 all REJECT); NF-20261107-52 EEM-SPY RV divergence (RV-div class H138/H139); NF-20261108-04 triple witching OPX+futures (subclass of H140 monthly OPX REJECT 4/8 — materially different construction required); NF-20261107-11 IVOL spread (separation from H118/H130); NF-20261107-14/48 OVX−VIX (**materially different pre-registered design required**; same IV-spread class as H125/H126); NF-20261107-31 sector breadth (adj H115).
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy; DBC/ETF proxies confound roll/flows/equity beta). NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8). NF-07/08/10/11/13/15/17/20/21 **deferred** (NF-08/NF-13 breakeven-proxy reassessed as NF-20261108-07 Cycle 57 — lower expected information/proxy history). NF-11r/NF-06-18 same root as NF-11 (ETF TLT-SHY proxy executed H141). NF-06-11 CBOE PC ratio **infeasible**. NF-20261106-03/23/24/28/30/32/33/35 **deferred** (NF-32 DBC/SPY reassessed NF-20261108-08, confounds). NF-20261107-05 CPI drift **deferred** (data blocker). NF-20261108-05 overnight/intraday return-flow **deferred** (microstructure-noisy; H143 tested overnight-gap RV component).

## Precise next task (one task) — Cycle 58 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H143 (H85–H143 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held/deferred pool above with concrete evidence (no silent drops). Explicitly justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ calendar H142/H91; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136).
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 58 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading. **Pandas 3.x safety:** do not use `if <DataFrame>:` / `if trade_dates:` truthiness on DataFrames.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
