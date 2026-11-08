# NEXT_TASK — Cycle 61: discovery, pre-register, implement, execute next H-ID after H146

## State (post Cycle 60 / H146)
- **H146 / NF-20261107-11 — SPY timing from cross-sectional IVOL dispersion regime (cross-sectional volatility decomposition / higher-moment dispersion): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261107_11_ivol_spread_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 7.88s)
  - Runner: `run_nf_20261107_11_ivol_spread_spy.py`; Tests: `tests/test_nf_20261107_11_ivol_spread_spy.py` (7 passed)
  - Data (free/public yfinance, PIT): SPY + QQQ,IWM,EFA,EEM,XLF,XLE,XLV,XLI,XLK daily auto-adjust Close, 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Signal: z-score of rolling cross-sectional std of per-asset IVOL (OLS residual vol vs SPY over `ivol_lookback`) over `z_window`; continuous de-risking of vol-targeted long SPY when dispersion z abnormally high (idiosyncratic disagreement/stress), 1-bar delay, long-only.
  - Selected (train-only 4-fold WF mean Sharpe 0.827): `ivol_lookback=126, z_window=252, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3205 engine trades, n=1259): Sharpe **0.962** fail, PF **1.198** fail, max DD **-2.60%** pass, trades **3205** pass, WF stability **1.164** pass, worst-regime rolling-252 **-1.423** fail, benchmark p **0.941** / IR **-0.695** fail, perturbation **0.952** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.518**/1.120/-6.07%/1258 (weaker, no benchmark edge); **inverse regime** (de-risk when dispersion LOW) **0.573**/1.119/-2.66%/3417 (weaker than base — **direction supported**, but no benchmark edge).
  - Honest adjacency: repo-new executed *cross-sectional IVOL-dispersion* SPY-timing observable. Adjacent to H93 (single-IVOL level, REJECT), H122 (downside semivar level, REJECT), H125/H126 (implied-IV spread level, REJECT), H144/H145 (z-score de-risking class). No validated edge.
- `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. No commit/push.
- **H85–H146 all rejected/recorded.** Next unused H-ID after H146 (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H146, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 60 outcome, this file.

## Deferred / held candidates (reassess with concrete evidence, no silent drops)
- **Held (materially different design required vs rejected construction classes):** NF-20261107-49 TLT-SPY realized correlation (correlation class H96/H127/H134/H137 REJECT); NF-20261107-52 EEM-SPY RV divergence (RV-div class H138/H139); NF-20261108-04 triple witching OPX+futures (subclass of H140 REJECT 4/8); NF-20261107-11 IVOL spread **now executed as H146 (REJECT)**; NF-20261107-14/48 OVX−VIX (IV-spread class H125/H126); NF-20261107-11 IVOL spread executed; NF-20261107-31 sector breadth (adj H115).
- **Deferred from Cycle 60 discovery:** RV trend/momentum equity timing (3.40, adjacency to vol-level timing H122/H29/H30); cross-sectional idiosyncratic-skew spread timing (3.00, execution complexity/weak skew evidence).
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy). NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8). NF-07/08/10/11/13/15/17/20/21 **deferred**. NF-11r/NF-06-18 same root as NF-11 (ETF TLT-SHY proxy executed H141). NF-06-11 CBOE PC ratio **infeasible**. NF-20261106-03/23/24/28/30/32/33/35 **deferred**. NF-20261107-05 CPI drift **deferred** (data blocker). NF-20261108-05 overnight/intraday return-flow **deferred**. NF-20261108-07 TIP-IEF breakeven-proxy **deferred**. NF-20261108-08 DBC-SPY commodity-complex **deferred**. NF-20261108-10 FXE EUR momentum **deferred** (FX-family adjacency H95/H103/H106).
- **Rejected construction classes (do not blindly repeat):** correlation H96/H127/H134/H137; RV-divergence H138/H139; OPX proximity H140; TOQ/H91 calendar; IV spread H125/H126; overnight/gap direction H18/H87; overnight-gap RV H143; Amihud H121; RV term structure H136; EEM-SPY relative-momentum H144; GLD-SPY relative-momentum H145; cross-sectional IVOL dispersion H146; FX-strength z-score adjacency H95/H103/H106.

## Precise next task (one task) — Cycle 61 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4:
1. Reconcile lineage to H146 (H85–H146 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held pool above with concrete evidence (no silent drops). Justify independence from rejected construction classes above.
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID (**H147**) in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 61 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading. **Pandas 3.x safety:** do not use `if <DataFrame>:` / `if trade_dates:` truthiness on DataFrames.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
