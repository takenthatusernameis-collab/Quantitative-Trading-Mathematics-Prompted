# NEXT_TASK — Cycle 62: discovery, pre-register, implement, execute next H-ID after H147

## State (post Cycle 61 / H147)
- **H147 / NF-20261108-12 — SPY timing from sector participation breadth regime (market structure / participation breadth transmission; resolves held NF-20261107-31 with materially different construction from H115): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_12_sector_breadth_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 9.87s, REAL)
  - Runner: `run_nf_20261108_12_sector_breadth_spy.py`; Tests: `tests/test_nf_20261108_12_sector_breadth_spy.py` (6 passed)
  - Data (free/public yfinance, PIT): SPY + XLF,XLE,XLV,XLI,XLK,XLY,XLP,XLU,XLB daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: z-score of fraction of 9 SPDR sector ETFs above trailing MA (`ma_window`); continuous de-risking of vol-targeted long SPY when breadth z abnormally negative (narrow participation), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.755): `ma_window=200, z_window=252, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3320 engine trades, n=1259): Sharpe **0.972** fail, PF **1.199** fail, max DD **-2.75%** pass, trades **3320** pass, WF stability **1.287** pass, worst-regime rolling-252 **-1.852** fail, benchmark p **0.939** / IR **-0.692** fail, perturbation **0.988** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.518**/1.120/-6.40%/1258 (weaker, no benchmark edge); **inverse regime** (de-risk when breadth strong / positive z) **0.862**/1.168/-2.96%/3587 (weaker Sharpe; direction weakly supported, no benchmark edge).
  - Honest adjacency: repo-new executed *cross-sector MA-participation breadth* SPY-timing observable. Explicitly separated from H115 (RSP/SPY ratio-momentum breadth, REJECT 3/8; different observable/construction), H97 (cap-concentration mean reversion, REJECT), H129 (sector beta dispersion, REJECT). Resolves held NF-20261107-31 as this materially different construction. No validated edge.
- `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. No commit/push.
- **H85–H147 all rejected/recorded.** Next unused H-ID after H147: **H148** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H147, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 61 discovery/outcome, `HANDOFF_NEXT.md` (Cycle 61).

## Cycle 61 discovery (directive §4, >=3 repo-new mechanism candidates across >=3 broad categories)
Lineage reconciled to H146 (H85–H146 rejected/recorded). Candidates scored honestly (25 novelty / 25 plausibility / 20 data+PIT / 15 falsifiability / 10 execution / 5 support). Independence justified from rejected construction classes: correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relmom H144; GLD-SPY relmom H145; cross-sectional IVOL dispersion H146; FX-strength z-score adjacency H95/H103/H106; RSP/SPY ratio-momentum breadth H115 (H147 uses materially different MA-participation observable).

| Candidate (NF-ID) | Broad category | N | E | D | F | X | S | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NF-20261108-12 Cross-sector MA-participation breadth SPY timing (de-risk when z-score of fraction of sector ETFs above trailing MA is abnormally negative) — **H147 (selected/executed)** | Market structure / participation breadth transmission | 3 | 3 | 5 | 4 | 5 | 2 | **3.60** |
| NF-20261107-52 EEM-vs-SPY realized-vol divergence timing (de-risk when EM-vs-US RV divergence z abnormally high; reassess held RV-div class with concrete separation) | Cross-asset volatility transmission / global risk transmission | 3 | 3 | 5 | 4 | 4 | 2 | **3.50** |
| NF-20261108-07 TIP-vs-IEF inflation-compensation (breakeven-proxy) momentum SPY timing (reassessed NF-08/NF-13 root) | Macro term-premium / inflation-compensation transmission | 3 | 3 | 4 | 4 | 4 | 2 | **3.35** |

Scoring notes (honest): NF-20261108-12 novelty 3 (not 4/5) — repo-new executed cross-sector MA-participation observable/pair construction, but **material adjacency** to H115 breadth/participation theme (explicitly separated by observable: sector-count trend participation vs RSP/SPY ratio momentum) and to z-score de-risking class. NF-20261107-52 held but requires concrete separation from RV-divergence construction class H138/H139 (H139 IWM/SPY RV-div REJECT 2/8; H138 credit-vs-equity RV-div REJECT 2/8) — not selected this cycle. NF-20261108-07 remains weaker (ETF breakeven proxy; prior proxy weakness).

## Deferred / held candidates (reassess with concrete evidence, no silent drops)
- **Held (materially different design required vs rejected construction classes):** NF-20261107-49 TLT-SPY realized correlation (correlation class H96/H127/H134/H137 REJECT); NF-20261107-52 EEM-SPY RV divergence (RV-div class H138/H139; reassessed Cycle 61, not selected); NF-20261108-04 triple witching OPX+futures (subclass of H140 REJECT 4/8); NF-20261107-14/48 OVX−VIX (IV-spread class H125/H126). **NF-20261107-31 sector breadth now executed as H147 (REJECT).**
- **Deferred from Cycle 60 discovery:** RV trend/momentum equity timing (3.40, adjacency to vol-level timing H122/H29/H30 — requires clearly separated pre-registered design); cross-sectional idiosyncratic-skew spread timing (3.00, execution complexity/weak skew evidence).
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy). NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8). NF-07/08/10/11/13/15/17/20/21 **deferred**. NF-11r/NF-06-18 same root as NF-11 (ETF TLT-SHY proxy executed H141). NF-06-11 CBOE PC ratio **infeasible**. NF-20261106-03/23/24/28/30/32/33/35 **deferred**. NF-20261107-05 CPI drift **deferred** (data blocker). NF-20261108-05 overnight/intraday return-flow **deferred**. NF-20261108-07 TIP-IEF breakeven-proxy **deferred** (reassessed Cycle 61). NF-20261108-08 DBC-SPY commodity-complex **deferred**. NF-20261108-10 FXE EUR momentum **deferred** (FX-family adjacency H95/H103/H106).
- **Rejected construction classes (do not blindly repeat):** correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relative-momentum H144; GLD-SPY relative-momentum H145; cross-sectional IVOL dispersion H146; RSP/SPY ratio-momentum breadth H115 / MA-participation breadth H147 (breadth class); FX-strength z-score adjacency H95/H103/H106.

## Precise next task (one task) — Cycle 62 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4:
1. Reconcile lineage to H147 (H85–H147 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held pool above with concrete evidence (no silent drops). Justify independence from rejected construction classes above.
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID (**H148**) in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 62 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading. **Pandas 3.x safety:** do not use `if <DataFrame>:` / `if trade_dates:` truthiness on DataFrames.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
