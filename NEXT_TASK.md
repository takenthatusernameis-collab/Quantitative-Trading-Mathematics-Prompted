# NEXT_TASK — Cycle 49: discovery, pre-register, implement, execute H135

## State (post Cycle 48)
- **H85–H134 all REJECTED/recorded.** H134 (NF-20261107-43, SPY timing from realized SPY--VIX correlation feedback) executed REAL: `.experiments/nf_runs/nf_20261107_43_spy_vix_corr/summary.json`, verdict **REJECT 5/8** (1.61s). Selected `corr_window=126, z_window=126, entry_scale=2, vol_target=0.10`. OOS Val+Test (1373 trades, n=1260): Sharpe **1.098** (pass), PF **1.235** (fail), maxDD **-10.53%** (pass), trades **1373** (pass), WF stability **1.367** (pass), worst-regime rolling-252 Sharpe **-1.226** (fail), benchmark p **0.879**/IR **-0.524** vs buy-hold (fail), perturbation **0.999** (pass). Ablations: random-exposure-matched 0.045 (signal not pure noise), inverse 0.298 (no opposite edge).
- **Next unused H-ID: H135** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H134, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 48, `HANDOFF_NEXT_SESSION.md`.
- **src/qtr unchanged.** No published/certified artifact, verdict, threshold, or frozen number modified.

## Verified (Cycle 48 close)
- `python3 -m ruff check run_nf_20261107_43_spy_vix_corr.py tests/test_nf_20261107_43_spy_vix_corr.py` → pass.
- `python3 -m ruff format --check run_nf_20261107_43_spy_vix_corr.py tests/test_nf_20261107_43_spy_vix_corr.py` → 2 files already formatted.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_43_spy_vix_corr.py` → **7 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_43_spy_vix_corr.py` → completed; artifact written, verdict **REJECT 5/8**. Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Precise next task (one task)
**Execute Cycle 49 discovery, pre-register, implement, and run H135** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H134. Propose **>=3 repo-new mechanism candidates across >=3 broad categories** with honest 25/25/20/15/10/5 scoring. **Concrete deferred reassessment (no silent drops):** NF-04 commodity carry **blocked**; NF-05 short-term CS reversal **deferred**; NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 **same root as NF-11** (not new root); NF-06-11 **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90). **Held:** NF-20261107-11 IVOL spread (NF-20261107-45 concept; separation from H118/H130 REJECTs), NF-20261107-12 credit-vs-equity vol divergence (sep H94/H100/H125), NF-20261107-14 OVX−VIX (same class as H125/H126 — materially different design required), NF-20261107-31 sector breadth (adj H115 REJECT 1/8), NF-20261107-40 AR(1) serial dependence (adj diagnostics/H26). NF-20261107-32 (=H118 executed REJECT) and NF-20261107-36 (=H133 executed REJECT) are not repo-new; do not rerun.
2. Select highest-expected-information feasible repo-new candidate. **Pre-register H135** in `HYPOTHESIS_SPEC.md` (§H135, decision-ready before validation outcomes) and record Cycle 49 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
3. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading.
4. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
