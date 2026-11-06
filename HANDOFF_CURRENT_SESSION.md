# HANDOFF_CURRENT_SESSION.md — Cycle 17 H104 executed (REJECT 4/9); Cycle 18 discovery / H105 required

## State
- Branch `main...origin/main` (HEAD unchanged). Working tree has uncommitted H103 artifacts from prior session plus this session’s H104 work and doc updates (see `git status --short`). `src/qtr` **NOT modified**.
- H1–H103 all rejected at session start; **H104 (NF-20261106-07, ^VVIX volatility-of-volatility stress timing SPY) executed 2026-11-06 — REJECT (4/9).** Experiment `exp_2026-11-06T13-35-05-405528Z`. Artifact `.experiments/nf_runs/nf_20261106_07_vvix_stress/summary.json`. No verdict/artifact/gate/certified-number modifications to prior experiments.
- Next unused H-ID: **H105** (H24/H68–H73/H76–H79 unassigned, not recycled).

## What changed (this session)
- **Cycle 17 discovery (directive §4):** reconciled lineage to H103 (H85–H103 rejected). Assessed >=3 repo-new candidates across categories: (1) NF-20261106-07 ^VVIX vol-of-vol / second-order implied-vol stress timing SPY (selected, H104); (2) NF-20261106-09 ^SKEW CBOE tail-risk pricing stress timing SPY (deferred, high expected information — exploratory unselected quick check ~0.94 OOS Sharpe/733 trades on fixed params, NOT validated; needs full pre-registration); (3) NF-20261106-10 SI=F/GC=F silver/gold risk-sentiment timing (deferred, lower novelty/plausibility, adjacency to H101). Scored honestly (NF-07/NF-09 tied 3.80; NF-07 executed given pre-existing task/pre-reg skeleton; NF-09 prioritized for Cycle 18). Reassessed NF-04/05/11r/12/17/20/21/03/07/08 with concrete evidence (no silent drops); NF-03 superseded by H104.
- **Implemented & executed H104/NF-20261106-07:** added `run_nf_20261106_07_vvix_stress.py` (trailing smoothed ^VVIX level z-score, continuous long-only exposure `clip(1 - clip(z,0)/entry_scale,0,1)`×vol-target×MAX_POS, 1-bar delay; 24-combo grid `lookback{63,126}×z_window{126,252}×entry_scale{1,1.5,2}×vol_target{0.10,0.15}`, train-only 4-fold WF selection, protected Test, OOS Val+Test gates, OAT ±20% perturbation, ablations buy-hold SPY / random-exposure-matched / inverse-stress-long) and `tests/test_nf_20261106_07_vvix_stress.py` (10 tests). Fixed runner tracker API to match `src/qtr.tracking.experiment` (positional start/finish, `current_experiment.experiment_id`).
- **Recorded verdict:** `HYPOTHESIS_SPEC.md` §H104 executed REJECT (Cycle 17 completed note); `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 17 added with candidates/scores/reassessment/outcome; `HANDOFF_NEXT.md`/`NEXT_TASK.md` updated for Cycle 18/H105 (prioritize NF-09).
- No `src/qtr` changes. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. No commit/push.

## What was actually verified (this session)
- Data feasibility: `^VVIX` 4224 rows (2010-01-04→2026-10-30), `SPY` 4233; aligned 4224. ^SKEW 4171 rows checked for NF-09 feasibility (exploratory only).
- `python3 -m ruff check/format --check` clean for `run_nf_20261106_07_vvix_stress.py` and `tests/test_nf_20261106_07_vvix_stress.py`. `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261106_07_vvix_stress.py` → **10 passed**.
- Executed `PYTHONPATH=src python3 run_nf_20261106_07_vvix_stress.py` → **REJECT 4/9**, `exp_2026-11-06T13-35-05-405528Z`, artifact written.
- Pinned full-gate `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (100% `src/qtr`) **not re-run** (no `src/qtr` change).

## H104 key evidence (OOS Val+Test)
- Selected (train-only 4-fold WF): `lookback=63, z_window=252, entry_scale=1.5, vol_target=0.15`. ^VVIX/SPY 4224 rows (train 2516 / val 753 / test 955).
- OOS (977 trades): Sharpe **0.783** (fail), PF **1.158** (fail), max DD **-6.36%** (pass), trades **977** (pass), WF stability **0.974** (pass), worst-regime rolling-252 **-0.921** (fail), benchmark p **null** (fail), IR **-0.425** (fail), perturbation min ratio **0.886** (pass). Train Sharpe 0.804.
- Ablations (OOS): buy-hold SPY 0.720/1.149/DD -17.97%/1; random-exposure-matched 0.486/1.008/DD -14.65%/818 (beats random); inverse-stress-long 0.281/1.054/DD -13.68%/621.
- Failure mode: reduces drawdown and beats random exposure, but no validated risk-adjusted edge vs buy-hold (fails Sharpe/PF/worst-regime/benchmark-p/IR).

## What remains unresolved
- **H85–H104 all rejected.** H105 not pre-registered/executed.
- Cycle 18 discovery required per directive §4; **prioritize NF-09 (^SKEW tail-risk pricing, options category)** as high-expected-information deferred candidate — must be fully pre-registered (train-only WF selection, protected holdout, all gates, cost-aware) before outcomes.

## Approaches already tried / failed (evidence)
- **H104/NF-20261106-07 REJECT 4/9** (`exp_2026-11-06T13-35-05-405528Z`, `.experiments/nf_runs/nf_20261106_07_vvix_stress/summary.json`): fails Sharpe 0.783, PF 1.158, worst-regime -0.921, benchmark-p null, IR -0.425. Do **not** re-run/re-optimize H104 without a materially different, pre-registered mechanism.
- NF-09 ^SKEW exploratory fixed-param check (not holdout-selected, NOT a result): ~0.94 OOS Sharpe/733 trades — **unvalidated**; do not treat as evidence of edge.
- NF-10 SI/GC exploratory check inconclusive/adjacent to H101 — deferred.

## Precise next task (one task), with evidence and constraints
**Cycle 18 discovery: pre-register H105 (repo-new family, prioritize NF-09 ^SKEW tail-risk pricing) with smallest decisive test.**
1. Reconcile lineage to H104 (`HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, runners/tests/artifacts). Confirm H85–H104 rejected; next unused H-ID **H105**.
2. Search >=3 materially distinct mechanism categories and propose >=3 **repo-new** candidates (NF-YYYYMMDD IDs). For each: mechanism/causal chain, observables + point-in-time availability, construction/timing/horizon, null + falsifier, free-data feasibility, turnover/cost/capacity/ops constraints, closest prior repo family + why not a variant, confounders/leakage/alt explanations. **Evaluate NF-09 ^SKEW (options tail-risk pricing → SPY) as primary candidate** with a decisive, cost-aware, train-only-selected construction addressing IR/benchmark gates. Reassess NF-04/05/11r/12/17/20/21/07/08/09/10 with concrete evidence (no silent drops).
3. Score honestly (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, exec 10%, support 5%). Select the **smallest decisive test** / highest-information feasible experiment.
4. Pre-register **H105** in `HYPOTHESIS_SPEC.md` (and register Cycle 18) **before** examining validation/protected-test outcomes. Implement runner + focused tests, run `ruff check/format --check` and focused pytest, then execute; record exp ID/verdict/ablations/artifact. Protected holdout never used for selection.
5. **Constraints:** `src/qtr` unchanged unless genuine evidenced defect (then run pinned `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` + Ruff). Free/public data only. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. No live/paper trading. Do not commit/push without explicit user request.

## Uncommitted state (intentional)
- This session: `?? run_nf_20261106_07_vvix_stress.py`, `?? tests/test_nf_20261106_07_vvix_stress.py`, `?? .experiments/nf_runs/nf_20261106_07_vvix_stress/`, `M HYPOTHESIS_SPEC.md`, `M NEW_FAMILY_RESEARCH_REGISTER.md`, `M HANDOFF_CURRENT_SESSION.md`, `M HANDOFF_NEXT.md`, `M NEXT_TASK.md`.
- Prior session (uncommitted, not modified here): `?? run_nf_20261106_06_fxa_risk.py`, `?? tests/test_nf_20261106_06_fxa_risk.py`, `?? .experiments/nf_runs/nf_20261106_06_fxa_risk/`.
