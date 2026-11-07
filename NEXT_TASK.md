# NEXT_TASK — Cycle 51: discovery, pre-register, implement, execute H137

## State (post Cycle 50)
- **H85–H136 all REJECTED/recorded.** H136 (NF-20261107-47, SPY timing from realized lag-1 return autocorrelation / AR(1) serial-dependence state) executed REAL (committed artifact `81d036f`): `.experiments/nf_runs/nf_20261107_47_spy_ar1/summary.json`, verdict **REJECT 2/8** (1.515s). Selected `rv_window=21, ar_window=63, z_window=126, entry_scale=1.5, vol_target=0.10`. OOS Val+Test (1675 trades, n=1260): Sharpe **0.536** (fail), PF **1.128** (fail), maxDD **-15.53%** (fail), trades **1675** (pass), WF stability **0.452** (fail), worst-regime rolling-252 Sharpe **-1.066** (fail), benchmark p **1.000**/IR **-0.223** (fail), perturbation **0.642** (pass). Ablations: random-exposure-matched 0.772 (comparable/better), inverse 0.686 (no opposite edge). **Artifact-integrity note:** committed summary `experiment` string was mislabeled as VoV (copy-paste); artifact is immutable evidence of the executed AR(1) run (params/code are AR(1)); runner header/EXPERIMENT_DESC corrected in this session, artifact numbers unchanged.
- **Next unused H-ID: H137** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H136, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 50, `HANDOFF_NEXT_SESSION.md`.
- **src/qtr unchanged.** No published/certified artifact, verdict, threshold, or frozen number modified.

## Verified (Cycle 50 / this session)
- `python3 -m ruff check run_nf_20261107_47_spy_ar1.py tests/test_nf_20261107_47_spy_ar1.py` → pass.
- `python3 -m ruff format --check run_nf_20261107_47_spy_ar1.py tests/test_nf_20261107_47_spy_ar1.py` → pass.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_47_spy_ar1.py` → **7 passed**.
- NF-47 artifact present/parsed: `.experiments/nf_runs/nf_20261107_47_spy_ar1/summary.json` = **REJECT 2/8**. Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Precise next task (one task)
**Execute Cycle 51 discovery, pre-register, implement, and run H137** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H136. Propose **>=3 repo-new mechanism candidates across >=3 broad categories** with honest 25/25/20/15/10/5 scoring. **Concrete deferred reassessment (no silent drops):** NF-04 commodity carry **blocked**; NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 weekly REJECT 3/8); NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 **same root as NF-11** (not new root); NF-06-11 **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90). **Held:** NF-20261107-11 IVOL spread (separation from H118/H130 REJECTs), NF-20261107-12 credit-vs-equity vol divergence (sep H94/H100/H125 — needs distinct realized-vol divergence design), NF-20261107-14/NF-20261107-48 OVX−VIX (same construction class as H125/H126 — **materially different pre-registered design required**, not reframing), NF-20261107-31 sector breadth (adj H115 REJECT 1/8), NF-20261107-49 TLT-SPY corr (adj H127/H96). NF-20261107-32 (=H118), NF-20261107-36/39 (=H133), NF-20261107-43 (=H134), NF-20261107-46 (=H135), NF-20261107-47 (=H136) executed — not repo-new; do not rerun.
2. Select highest-expected-information feasible repo-new candidate. **Pre-register H137** in `HYPOTHESIS_SPEC.md` (§H137, decision-ready before validation outcomes) and record Cycle 51 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
3. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading.
4. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
