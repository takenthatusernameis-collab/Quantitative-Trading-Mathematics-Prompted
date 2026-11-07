# NEXT_TASK — Cycle 50: discovery, pre-register, implement, execute H136

## State (post Cycle 49)
- **H85–H135 all REJECTED/recorded.** H135 (NF-20261107-46, SPY timing from realized volatility-of-volatility / std of trailing realized vol) executed REAL: `.experiments/nf_runs/nf_20261107_46_spy_realized_vov/summary.json`, verdict **REJECT 5/8** (1.46s). Selected `rv_window=21, vov_window=63, z_window=126, entry_scale=2, vol_target=0.10`. OOS Val+Test (1238 trades, n=1260): Sharpe **1.015** (pass), PF **1.212** (fail), maxDD **-8.89%** (pass), trades **1238** (pass), WF stability **1.270** (pass), worst-regime rolling-252 Sharpe **-0.647** (fail), benchmark p **1.000**/IR **+0.257** vs buy-hold (fail, p>0.05), perturbation **0.828** (pass). Ablations: random-exposure-matched 0.538 (weaker), inverse 0.112 (no opposite edge). Honest adjacency to H104 implied VVIX (REJECT 5/9); repo-new *realized* VoV observable, no benchmark-clearing edge.
- **Next unused H-ID: H136** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H135, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 49, `HANDOFF_NEXT_SESSION.md` (to update).
- **src/qtr unchanged.** No published/certified artifact, verdict, threshold, or frozen number modified.

## Verified (Cycle 49 close)
- `python3 -m ruff check run_nf_20261107_46_spy_realized_vov.py tests/test_nf_20261107_46_spy_realized_vov.py` → pass.
- `python3 -m ruff format --check run_nf_20261107_46_spy_realized_vov.py tests/test_nf_20261107_46_spy_realized_vov.py` → pass (after formatting).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_46_spy_realized_vov.py` → **7 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_46_spy_realized_vov.py` → completed; artifact written, verdict **REJECT 5/8**. Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Precise next task (one task)
**Execute Cycle 50 discovery, pre-register, implement, and run H136** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H135. Propose **>=3 repo-new mechanism candidates across >=3 broad categories** with honest 25/25/20/15/10/5 scoring. **Concrete deferred reassessment (no silent drops):** NF-04 commodity carry **blocked**; NF-05 short-term CS reversal **deferred**; NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 **same root as NF-11** (not new root); NF-06-11 **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90). **Held:** NF-20261107-11 IVOL spread (NF-20261107-45; separation from H118/H130 REJECTs), NF-20261107-12 credit-vs-equity vol divergence (sep H94/H100/H125), NF-20261107-14/NF-20261107-48 OVX−VIX (same construction class as H125/H126 — **materially different pre-registered design required**), NF-20261107-31 sector breadth (adj H115 REJECT 1/8), NF-20261107-40/47 AR(1) serial dependence (adj diagnostics/H26; weak plausibility — decisive separation required), NF-20261107-49 TLT-SPY corr (adj H127/H96). NF-20261107-32 (=H118), NF-20261107-36/39 (=H133), NF-20261107-43 (=H134), NF-20261107-46 (=H135) executed — not repo-new; do not rerun.
2. Select highest-expected-information feasible repo-new candidate. **Pre-register H136** in `HYPOTHESIS_SPEC.md` (§H136, decision-ready before validation outcomes) and record Cycle 50 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
3. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading.
4. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
