# HANDOFF_NEXT_SESSION.md — Cycle 50 complete (H136 REJECT); prepare Cycle 51 discovery/H137

## State
- **H85–H136 all REJECTED/recorded.** H136 (NF-20261107-47, SPY timing from realized lag-1 return autocorrelation / AR(1) serial-dependence state) executed REAL via committed artifact `81d036f`: `.experiments/nf_runs/nf_20261107_47_spy_ar1/summary.json` (1.515s), verdict **REJECT 2/8**. **Next unused H-ID: H137** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Files (H136):** `run_nf_20261107_47_spy_ar1.py`, `tests/test_nf_20261107_47_spy_ar1.py` (7 passed). Runner/artifact/test existed in committed state `81d036f`; this session corrected runner header/EXPERIMENT_DESC (AR(1) mechanism) without changing the immutable artifact numbers, and recorded outcomes. Docs updated: `HYPOTHESIS_SPEC.md` §H136, `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 50 discovery/scoring/deferred reassessment + H136 outcome), `NEXT_TASK.md` (Cycle 51), this file. `src/qtr` unchanged. No published/certified artifact/verdict/threshold/frozen number modified except adding H136 records and correcting non-artifact runner text. No secrets/credentials added. No commit/push performed by this session.

## What changed (Cycle 50 / this session)
- **Directive §4 discovery:** lineage reconciled to H135. >=3 repo-new mechanism candidates across >=3 broad categories scored honestly (25/25/20/15/10/5): NF-20261107-47 SPY AR(1) serial-dependence state timing (serial dependence/microstructure-state) **3.60, selected/executed H136** (decisive falsification of Cycle 49-held NF-40 concept; weak plausibility 2, strong feasibility/falsifiability); NF-20261107-49 TLT-SPY realized correlation regime (rates-equity co-movement/flight-to-quality) **3.60, held** (adj H127/H96 separation required); NF-20261107-12 credit-vs-equity volatility-divergence regime (credit stress/volatility transmission) **3.50, held** (distinct realized-vol divergence design required; sep H94/H100/H125); NF-20261107-48 OVX−VIX (cross-asset commodity-options) **3.35, held/not selected** — same construction class as H125/H126, **materially different pre-registered design required**.
- **H136 result (REAL, NF-20261107-47, committed artifact):** SPY 3776 rows 2010-01-04→2025-01-03 (train 2516/val 505/test 755). Selected `rv_window=21, ar_window=63, z_window=126, entry_scale=1.5, vol_target=0.10` (train WF mean 1.049). OOS Val+Test (1675 trades): Sharpe **0.536** (fail), PF **1.128** (fail), maxDD **-15.53%** (fail), trades **1675** (pass), WF stability **0.452** (fail), worst-regime rolling-252 **-1.066** (fail), benchmark p **1.000**/IR **-0.223** (fail), perturbation **0.642** (pass) → **REJECT 2/8**. Ablations: random-exposure-matched 0.772 (comparable/better), inverse 0.686 (no opposite edge). **Artifact-integrity note:** committed summary `experiment` string mislabeled as VoV; params/code/observable are AR(1); immutable artifact unchanged.
- **Honest separation:** AR(1) is a pre-registered timing-family execution; repo has AR(1)/autocorrelation diagnostics (`run_h26_sharpe_scale_audit.py`, `run_nf_20261105_06_gold_oil_rv.py`) and H26 is an audit, not a timing family — decisive separation documented. Distinct from VIX/vol-term/corr (H86/H113/H123/H125/H126/H127/H131/H134), higher moments (H89/H122/H124/H128/H132/H135), IVOL (H93/H130), drawdown state (H133), return dispersion (H118). No validated edge.

## What was actually verified
- `python3 -m ruff check run_nf_20261107_47_spy_ar1.py tests/test_nf_20261107_47_spy_ar1.py` → **All checks passed**.
- `python3 -m ruff format --check run_nf_20261107_47_spy_ar1.py tests/test_nf_20261107_47_spy_ar1.py` → **2 files already formatted**.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_47_spy_ar1.py` → **7 passed**.
- Artifact parsed: `.experiments/nf_runs/nf_20261107_47_spy_ar1/summary.json` → `NF-20261107-47`, `H136`, verdict `REJECT`, gates_passed `2`.
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## What remains unresolved
- **Cycle 51 discovery/H137 (NEXT_TASK):** Fresh directive §4 cycle: >=3 repo-new candidates across >=3 broad categories, honest 25/25/20/15/10/5 scoring, concrete deferred reassessment (no silent drops). Deferred highlights (see `NEXT_TASK.md`): NF-04 **blocked**; NF-06-11 **infeasible**; NF-11r/NF-06-18 **SAME root as NF-11**; NF-05/07/08/10/11/13/15/17/20/21/NF-20261106-03/23/24/28/30/32/33/35/NF-20261107-05 deferred. Held: NF-20261107-11/12/14(48)/31/49 with separation/design requirements.
- H85–H136 all rejected; serial-dependence timing (H136 AR1), vol-of-vol (H104 implied, H135 realized), higher-moment (H89/H122/H124/H128/H132), VIX-term/cross-asset vol/corr (H86/H113/H123/H125/H126/H127/H131/H134), IVOL (H93/H130), drawdown state (H133), return dispersion (H118) heavily tested — require clearly distinct mechanism/design if revisited.
- Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Approaches already tried / failed (do not blindly repeat)
- H85–H136 all REJECTED. H136: fails 6/8 gates (Sharpe 0.536, PF 1.128, maxDD -15.53%, WF 0.452, worst-regime -1.066, benchmark p 1.000/IR -0.223); random-exposure comparable/better (0.772). Do not rerun same AR(1) construction.
- NF-20261107-32/36(39)/43/46/47 are duplicates of executed H118/H133/H134/H135/H136 — do not re-execute as "new" without a materially distinct observable/design.
- NF-20261107-14/48 OVX−VIX: same cross-asset IV-spread construction class as H125/H126 — **materially different pre-registered design required** (not reframing).

## Precise next task (one task)
**Execute Cycle 51 discovery and implement+run H137** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H136, propose >=3 repo-new candidates across >=3 broad categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops), pre-register H137 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, run `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/handoff. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless an evidenced defect requires it (then rerun pinned full gates).

**Pinned gates (if `src/qtr`/core touched):**
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
