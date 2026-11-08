# NEXT_TASK — Cycle 60: discovery, pre-register, implement, execute next H-ID after H145

## State (post Cycle 59 / H145)
- **H145 / NF-20261108-11 — SPY timing from GLD-vs-SPY relative-momentum regime (safe-haven / real-asset vs equity risk-premium transmission): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_11_gld_spy_relmom/summary.json` (+ `grid.csv`, `data_meta.json`, 14.69s)
  - Runner: `run_nf_20261108_11_gld_spy_relmom.py`
  - Tests: `tests/test_nf_20261108_11_gld_spy_relmom.py` (5 tests)
  - Data (free/public yfinance, PIT): SPY+GLD daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: z-score of trailing `(ret(GLD,mom_window)-ret(SPY,mom_window))` over `z_window`; continuous de-risking on positive z (gold flight-to-safety leadership), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.800): `mom_window=63, z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3455 engine trades, n=1259): Sharpe **0.761** fail, PF **1.153** fail, max DD **-3.59%** pass, trades **3455** pass, WF stability **0.951** pass, worst-regime rolling-252 **-1.307** fail, benchmark p **0.948** / IR **-0.720** fail, perturbation **0.914** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.518**/1.120/-5.89%/1258 (weaker than strategy, no benchmark edge); **inverse regime** (pre-registered falsifier, de-risk when GLD underperforms/negative z) **0.909**/1.177/-2.66%/3515 (stronger than pre-registered mapping — **direction not supported**).
  - Honest adjacency: repo-new executed *GLD-vs-SPY relative-momentum* SPY-timing pair. Adjacent to H88 (GLD/USO spread RV, REJECT 1/9), H99 (GDX/GDX-GLD, REJECT 4/9), H101 (GLD/XLE RV, REJECT 3/9), H144 (EEM-SPY relmom, REJECT 3/8), and z-score relmom de-risking construction class. No validated edge.
  - Integrity: untracked runner/test repaired to pre-registered safe-haven positive-z mapping before execution; stale wrong-output artifact removed; artifact is corrected REAL run.
- `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. No commit/push.
- **H85–H145 all rejected/recorded.** Next unused H-ID after H145 (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H145, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 59 outcome, this file.

## Held / deferred candidates (reassess with concrete evidence, no silent drops)
- **Held (materially different design required vs rejected construction classes):** NF-20261107-49 TLT-SPY realized correlation (correlation class H96/H127/H134/H137 REJECT); NF-20261107-52 EEM-SPY RV divergence (RV-div class H138/H139); NF-20261108-04 triple witching OPX+futures (subclass of H140 monthly OPX REJECT 4/8); NF-20261107-11 IVOL spread (separation from H118/H130); NF-20261107-14/48 OVX−VIX (**materially different pre-registered design required**; IV-spread class H125/H126); NF-20261107-31 sector breadth (adj H115).
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy; DBC/ETF proxies confound roll/flows/equity beta). NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8). NF-07/08/10/11/13/15/17/20/21 **deferred** (NF-08/NF-13 breakeven-proxy weak proxy history; NF-15 EEM/EFA adjacent to H144 but different pair — reassess only with materially different construction). NF-11r/NF-06-18 same root as NF-11 (ETF TLT-SHY proxy executed H141). NF-06-11 CBOE PC ratio **infeasible**. NF-20261106-03/23/24/28/30/32/33/35 **deferred** (NF-32 ETF confounds). NF-20261107-05 CPI drift **deferred** (data blocker). NF-20261108-05 overnight/intraday return-flow **deferred** (microstructure-noisy; H143 tested overnight-gap RV component). NF-20261108-07 TIP-IEF breakeven-proxy **deferred** (weak proxy). NF-20261108-08 DBC-SPY commodity-complex **deferred** (ETF roll/flow confounds). NF-20261108-10 FXE EUR momentum **deferred** (tied score; FX-family adjacency H95/H103/H106).

## Precise next task (one task) — Cycle 60 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H145 (H85–H145 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held/deferred pool above with concrete evidence (no silent drops). Explicitly justify independence from rejected construction classes (correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relative-momentum H144; **GLD-SPY relative-momentum H145**; FX-strength z-score family adjacency H95/H103/H106).
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 60 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading. **Pandas 3.x safety:** do not use `if <DataFrame>:` / `if trade_dates:` truthiness on DataFrames.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
