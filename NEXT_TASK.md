# NEXT_TASK — Cycle 57: discovery, pre-register, implement, execute next H-ID after H142

## State (post Cycle 56 / H142)
- **H142 / NF-20261108-03 — SPY timing from turn-of-quarter window-dressing/rebalancing flows (calendar/auction): REJECT (4/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_03_spy_toq_window/summary.json` (+ `grid.csv`, `data_meta.json`, 31.45s)
  - Runner: `run_nf_20261108_03_spy_toq_window.py` (repaired: numpy/pandas mask bugs, duplicate defs, wrong NF/H IDs/path, incorrect inverse; pandas-3-safe metrics; re-executed — artifact is REAL corrected run)
  - Tests: `tests/test_nf_20261108_03_spy_toq_window.py` (5 passed)
  - Data (free/public yfinance, PIT): SPY daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Selected (train-only 4-fold WF mean Sharpe 0.8543): `end_days=1, start_days=1, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3353 engine trades, n=1260): Sharpe **0.894** fail, PF **1.163** fail, max DD **-3.41%** pass, trades **3353** pass, WF stability **1.047** pass, worst-regime rolling-252 **-1.220** fail, benchmark p **0.953** / IR **-0.722** fail, perturbation **0.996** pass → **4/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.111**/1.053/-10.17%/972 (much weaker — not pure noise); **inverse TOQ regime** 0.914/1.166/-2.93%/3353 (comparable, no clear directional falsifier; not a validated edge under pre-registered de-risking mapping).
  - Honest adjacency: repo-new *turn-of-quarter calendar* observable; distinct institutional cycle from H91 turn-of-month (REJECT 3/9). No validated edge under pre-registered design.
  - `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. `ruff check/format` clean. No commit/push.
- **H85–H142 all rejected/recorded.** Next unused H-ID after H142 (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H142, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 56 outcome, `HANDOFF_NEXT_SESSION.md` updated.

## Held / deferred candidates (reassess with concrete evidence, no silent drops)
- **Held (materially different design required vs rejected construction classes):** NF-20261107-49 TLT-SPY realized correlation (3.60, adj correlation class H96/H127/H134/H137 all REJECT); NF-20261107-52 EEM-SPY RV divergence (3.50, adj rejected H138/H139 RV-divergence class); NF-20261108-04 triple witching OPX+futures flow/pin (3.94 scored in §4 but subclass of H140 monthly OPX REJECT 4/8 — needs materially different construction); NF-20261107-11 IVOL spread (separation from H118/H130 REJECTs); NF-20261107-14/48 OVX−VIX (same class as H125/H126 — materially different pre-registered design required); NF-20261107-31 sector breadth (adj H115 REJECT 1/8).
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy); NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8); NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 same root as NF-11; NF-06-11 CBOE PC ratio **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90); NF-20261108-05 overnight/intraday return-flow (lower score 3.68; OHLC split feasible but microstructure-noisy; reassess).
- Suggested new mechanism categories not yet executed as timing families (verify free-data feasibility): order-flow/auction mechanics beyond TOQ/OPX, index-rebalance flow constraints, earnings-season/dispersion timing with a repo-new observable, cross-sectional skewness/coskewness timing (distinct from H122/H130 constructions), commodity basis/curve proxies if a free PIT source exists.

## Precise next task (one task) — Cycle 57 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H142 (H85–H142 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held/deferred pool above with concrete evidence (no silent drops). Explicitly justify independence from rejected construction classes (correlation regime H96/H127/H134/H137, RV-divergence H138/H139, OPX proximity H140, TOQ calendar H142/H91, IV spread H125/H126).
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 57 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading. **Pandas 3.x safety:** do not use `if <DataFrame>:` / `if trade_dates:` truthiness on DataFrames.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
