# NEXT_TASK — Cycle 59: discovery, pre-register, implement, execute next H-ID after H144

## State (post Cycle 58 / H144)
- **H144 / NF-20261108-09 — SPY timing from EEM-vs-SPY relative-momentum regime (global cross-market leadership transmission): REJECT (3/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_09_eem_spy_relmom/summary.json` (+ `grid.csv`, `data_meta.json`, 14.24s)
  - Runner: `run_nf_20261108_09_eem_spy_relmom.py`
  - Tests: `tests/test_nf_20261108_09_eem_spy_relmom.py` (5 passed)
  - Data (free/public yfinance, PIT): SPY+EEM daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: z-score of trailing `(ret(EEM,mom_window)-ret(SPY,mom_window))` over `z_window`; continuous de-risking on negative z (EM leadership weak), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.961): `mom_window=21, z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3579 engine trades, n=1259): Sharpe **0.537** fail, PF **1.102** fail, max DD **-3.81%** pass, trades **3579** pass, WF stability **0.559** fail, worst-regime rolling-252 **-1.627** fail, benchmark p **0.957** / IR **-0.756** fail, perturbation **0.919** pass → **3/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.518**/1.120/-5.71%/1258 (comparable — no clear edge); **inverse regime** (pre-registered falsifier, de-risk when EM leadership strong) **0.878**/1.175/-2.29%/3584 (outperforms pre-registered mapping — **direction falsified**).
  - Honest adjacency: repo-new executed *EEM-vs-SPY relative-momentum* leadership pair. Adjacent to H85 (lead-lag, different causal form), NF-15 (EEM/EFA deferred, different pair), H139 (IWM/SPY RV-div, different observable). No validated edge.
- `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. `ruff check/format` clean. No commit/push.
- **H85–H144 all rejected/recorded.** Next unused H-ID after H144 (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H144, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 58 outcome, this file.

## Held / deferred candidates (reassess with concrete evidence, no silent drops)
- **Held (materially different design required vs rejected construction classes):** NF-20261107-49 TLT-SPY realized correlation (correlation class H96/H127/H134/H137 REJECT); NF-20261107-52 EEM-SPY RV divergence (RV-div class H138/H139); NF-20261108-04 triple witching OPX+futures (subclass of H140 monthly OPX REJECT 4/8); NF-20261107-11 IVOL spread (separation from H118/H130); NF-20261107-14/48 OVX−VIX (**materially different pre-registered design required**; IV-spread class H125/H126); NF-20261107-31 sector breadth (adj H115).
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy; DBC/ETF proxies confound roll/flows/equity beta). NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8). NF-07/08/10/11/13/15/17/20/21 **deferred** (NF-08/NF-13 breakeven-proxy weak proxy history; NF-15 EEM/EFA adjacent to H144 but different pair — reassess only with materially different construction). NF-11r/NF-06-18 same root as NF-11 (ETF TLT-SHY proxy executed H141). NF-06-11 CBOE PC ratio **infeasible**. NF-20261106-03/23/24/28/30/32/33/35 **deferred** (NF-32 ETF confounds). NF-20261107-05 CPI drift **deferred** (data blocker). NF-20261108-05 overnight/intraday return-flow **deferred** (microstructure-noisy; H143 tested overnight-gap RV component). NF-20261108-07 TIP-IEF breakeven-proxy **deferred** (weak proxy/sanity). NF-20261108-08 DBC-SPY commodity-complex **deferred** (ETF roll/flow confounds). NF-20261108-10 FXE EUR momentum **deferred** (tied score; FX-family adjacency H95/H103/H106; rough sanity mixed).

## Precise next task (one task) — Cycle 59 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H144 (H85–H144 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held/deferred pool above with concrete evidence (no silent drops). Explicitly justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relative-momentum H144; FX-strength z-score family adjacency H95/H103/H106).
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 59 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading. **Pandas 3.x safety:** do not use `if <DataFrame>:` / `if trade_dates:` truthiness on DataFrames.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
