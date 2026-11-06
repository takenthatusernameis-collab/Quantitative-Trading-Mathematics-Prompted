# HANDOFF_CURRENT_SESSION.md — Cycle 20 H106 executed (REJECT 4/8); Cycle 21 discovery / H107 required

## State
- Branch `main...origin/main` (HEAD unchanged). Working tree has uncommitted H103–H106 artifacts from prior/current sessions (see `git status --short`). `src/qtr` **NOT modified**.
- H1–H105 all rejected at session start; **H106 (NF-20261106-14, FXY JPY safe-haven/funding-unwind stress timing SPY) executed 2026-11-06 — REJECT (4/8).** Experiment `exp_2026-11-06T13-53-01-203238Z`. Artifact `.experiments/nf_runs/nf_20261106_14_fxy_safehaven/summary.json`. No verdict/artifact/gate/certified-number modifications to prior experiments.
- Next unused H-ID: **H107** (H24/H68–H73/H76–H79 unassigned, not recycled).

## What changed (this session)
- **Cycle 20 discovery (directive §4):** reconciled lineage to H105 (H85–H105 rejected). Assessed >=3 repo-new candidates across categories with free-data feasibility checks (yfinance): (1) NF-20261106-14 FXY JPY safe-haven/funding-unwind stress timing SPY — **FX safe-haven/funding-currency unwind transmission** (selected/executed H106; novelty honest 3 given FX adjacency to H95 UUP/H103 FXA, but different currency/mechanism/construction); (2) NF-20261106-12 TNX-FVX 10y-5y term-slope regime timing SPY — **rates term-structure/macro slope** (data feasible, 0 non-positive; deferred as NF-11/NF-11r **data-resolution path, same root mechanism, not a new root family**; exploratory unselected check suggested info but not holdout-selected); (3) NF-20261106-15 EEM/EFA global EM-vs-DM risk-appetite transmission — **global equity cross-market risk appetite** (deferred; weak exploratory ~0.42 OOS fixed-param). Cycle 19 deferred addressed: NF-06-11 CBOE ^CPC/^CPCE **infeasible** (yfinance 0 rows/"not found"); NF-12 maps to NF-11r evidence; NF-13 (GLD/TIP) deferred (adjacency/weak proxy history).
- **Implemented & executed H106/NF-20261106-14:** added `run_nf_20261106_14_fxy_safehaven.py` (trailing FXY momentum z-score, continuous long-only exposure `clip(1 - clip(z,0)/entry_scale,0,1)`×vol-target×MAX_POS, 1-bar delay; 24-combo grid `lookback{21,63}×z_window{126,252}×entry_scale{1,1.5,2}×vol_target{0.10,0.15}`, train-only 4-fold WF selection via `walk_forward_splits(len, n_splits)`, protected Test, OOS Val+Test gates, perturbation ±20%, ablations buy-hold/random-exposure-matched/inverse-stress) and `tests/test_nf_20261106_14_fxy_safehaven.py` (10 tests). Fixed WF selection bug from first pass (NaN selection from wrong `walk_forward_splits` API usage) — re-ran and recorded final artifact.
- **Recorded verdict:** `HYPOTHESIS_SPEC.md` §H106 pre-reg + executed REJECT (4/8); `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 20 added with candidates/scores/reassessment/outcome; `HANDOFF_NEXT.md`/`NEXT_TASK.md` updated for Cycle 21/H107.
- No `src/qtr` changes. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. No commit/push.

## What was actually verified (this session)
- Data feasibility: `FXY` 4237 rows (2010-01-04→2026-11-05), `SPY` 4237; aligned 4233. Also checked ^CPC/^CPCE infeasible, ^TNX/^FVX feasible (NF-11r data-resolved), EEM/EFA/TIP feasible.
- `python3 -m ruff check/format --check` clean for `run_nf_20261106_14_fxy_safehaven.py` and `tests/test_nf_20261106_14_fxy_safehaven.py`. `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261106_14_fxy_safehaven.py` → **10 passed**.
- Executed `PYTHONPATH=src python3 run_nf_20261106_14_fxy_safehaven.py` → **REJECT 4/8**, `exp_2026-11-06T13-53-01-203238Z`, artifact written.
- Pinned full-gate `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (100% `src/qtr`) **not re-run** (no `src/qtr` change).

## H106 key evidence (OOS Val+Test)
- Selected (train-only 4-fold WF, best 1.280): `lookback=63, z_window=126, entry_scale=2.0, vol_target=0.15`. FXY/SPY 4233 rows (train 2516 / val 756 / test 961).
- OOS (1049 trades): Sharpe **0.832** (fail), PF **1.165** (fail), max DD **-7.27%** (pass), trades **1049** (pass), WF stability **1.049** (pass), worst-regime rolling-252 **-0.754** (fail), benchmark p **null** (fail), IR **-0.377** (fail), perturbation min ratio **0.936** (pass). Train Sharpe 0.794.
- Ablations (OOS): buy-hold SPY 0.720/1.148/DD -18.21%/1; random-exposure-matched 0.549/1.129/DD -7.24%/1717 (beats random); inverse-stress-long 0.534/1.143/DD -14.83%/1363.
- Failure mode: reduces drawdown and beats random exposure, but no validated risk-adjusted edge vs buy-hold (fails Sharpe/PF/worst-regime/benchmark-p/IR). FX adjacency to H95/H103 scored honestly.

## What remains unresolved
- **H85–H106 all rejected.** H107 not pre-registered/executed.
- Cycle 21 discovery required per directive §4. **NF-11r (TNX-FVX slope) is data-resolved but is the SAME root mechanism as NF-11** — if pursued, must be pre-registered as NF-11 resolution with honest novelty (not a new root family) and decisive construction; do not present as repo-new. NF-04 still blocked (no free point-in-time term structure).

## Approaches already tried / failed (evidence)
- **H106/NF-20261106-14 REJECT 4/8** (`exp_2026-11-06T13-53-01-203238Z`, `.experiments/nf_runs/nf_20261106_14_fxy_safehaven/summary.json`): fails Sharpe 0.832, PF 1.165, worst-regime -0.754, benchmark-p null, IR -0.377. Do **not** re-run/re-optimize H106 without a materially different, pre-registered mechanism.
- NF-11r TNX-FVX exploratory unselected check (NOT evidence): showed some info on fixed params but not holdout-selected; mechanism-adjacency to NF-11.
- NF-15 EEM/EFA exploratory weak (~0.42 OOS fixed-param). NF-06-11 ^CPC/^CPCE infeasible on yfinance.

## Precise next task (one task), with evidence and constraints
**Cycle 21 discovery: pre-register H107 (repo-new family where possible) with smallest decisive test.**
1. Reconcile lineage to H106 (`HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, runners/tests/artifacts). Confirm H85–H106 rejected; next unused H-ID **H107**.
2. Search >=3 materially distinct mechanism categories and propose >=3 candidates (NF-YYYYMMDD IDs). For each: mechanism/causal chain, observables + point-in-time availability, construction/timing/horizon, null + falsifier, free-data feasibility, turnover/cost/capacity/ops constraints, closest prior repo family + why not a variant, confounders/leakage/alt explanations. **Reassess NF-04/05/07/08/10/11/13/15/17/20/21 and NF-11r** with concrete evidence (no silent drops). NF-11r TNX-FVX may be pursued only as an **NF-11 resolution path with honest novelty scoring (same root mechanism, data-resolved)** — not a repo-new root family. NF-06-11 CBOE PC ratio infeasible. Prioritize genuinely repo-new mechanisms.
3. Score honestly (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, exec 10%, support 5%). Select the **smallest decisive test** / highest-information feasible experiment.
4. Pre-register **H107** in `HYPOTHESIS_SPEC.md` (and register Cycle 21) **before** examining validation/protected-test outcomes. Implement runner + focused tests, run `ruff check/format --check` and focused pytest, then execute; record exp ID/verdict/ablations/artifact. Protected holdout never used for selection.
5. **Constraints:** `src/qtr` unchanged unless genuine evidenced defect (then run pinned `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` + Ruff). Free/public data only. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. No live/paper trading. Do not commit/push without explicit user request.

## Uncommitted state (intentional)
- This session: `?? run_nf_20261106_14_fxy_safehaven.py`, `?? tests/test_nf_20261106_14_fxy_safehaven.py`, `?? .experiments/nf_runs/nf_20261106_14_fxy_safehaven/`, `M HYPOTHESIS_SPEC.md`, `M NEW_FAMILY_RESEARCH_REGISTER.md`, `M .experiments/experiments.jsonl`, `M HANDOFF_CURRENT_SESSION.md`, `M HANDOFF_NEXT.md`, `M NEXT_TASK.md`.
- Prior sessions (uncommitted, not modified here): `?? run_nf_20261106_06_fxa_risk.py`/tests/artifact, `?? run_nf_20261106_07_vvix_stress.py`/tests/artifact, `?? run_nf_20261106_09_skew_tail_timing.py`/tests/artifact.
