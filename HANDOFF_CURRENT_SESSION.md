# HANDOFF_CURRENT_SESSION.md — Cycle 15 H102 executed (REJECT 6/9); Cycle 16 discovery / H103 required

## State
- Branch `main` at `84606f9` (clean at start of this session’s edits context). Working tree now has **untracked** `run_nf_20261106_05_btc_bond.py`, `tests/test_nf_20261106_05_btc_bond.py`, `.experiments/nf_runs/nf_20261106_05_btc_bond/` (cache + `summary.json`), plus modified lineage docs from this session: `M HYPOTHESIS_SPEC.md`, `M NEW_FAMILY_RESEARCH_REGISTER.md`, `M HANDOFF_CURRENT_SESSION.md`, `M HANDOFF_NEXT.md`. `src/qtr` **NOT modified**.
- H1–H101 all rejected; **H102 (NF-20261106-05, Bitcoin/bond risk-appetite regime equity timing) executed 2026-11-06 — REJECT (6/9).** Experiment `exp_2026-11-06T12-34-38-533699Z`. Artifact `.experiments/nf_runs/nf_20261106_05_btc_bond/summary.json`. No verdict/artifact/gate/certified-number modifications to prior experiments.
- Next unused H-ID: **H103** (H24/H68–H73/H76–H79 unassigned, not recycled). NF-04/05/11r/12/17/20/21/03 remain deferred with documented decisive risks (register/HYPOTHESIS_SPEC §H102).

## What changed (this session)
- **Implemented & executed H102/NF-20261106-05:** added `run_nf_20261106_05_btc_bond.py` (log(BTC-USD/TLT) trailing z-score, hysteresis, vol-targeted long SPY, 1-bar delay via engine shift; 36-combo grid `lookback{63,126,252}×entry_z{1,1.5,2}×exit_z{0,0.5}×vol_target{0.10,0.15}`, train-only 4-fold WF selection, protected Test, OOS Val+Test gates, perturbation OAT ±20%, ablations random-exposure-matched / buy-hold SPY / inverse risk-off long) and `tests/test_nf_20261106_05_btc_bond.py` (10 tests: pre-reg gates/config/universe/splits/grid, signal shape/bounds/warmup, rising risk-appetite can go long, risk-off can go flat, missing-symbol flat, hysteresis bounds).
- **Recorded verdict:** `HYPOTHESIS_SPEC.md` §H102 updated from pre-registered to executed with metrics/ablations/verdict/rationale/lineage row; `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 15 updated with execution outcome and Cycle 16 next. `summary.json` annotated with `experiment_id`.
- **H101 (prior session/HEAD):** `run_nf_20261106_04_copper_gold.py` `main()` completion, its tests, and H101 REJECT artifacts were already committed in `84606f9`; this session verified H101 lint/format/pytest clean in a deps-available env (`ruff 0.17.4`, `pytest 9.2.0`, deps present). No H101 re-execution/re-verdict.
- No `src/qtr` changes. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. No commit/push (no explicit user request).

## What was actually verified (this session)
- Deps/tools available: `numpy/pandas/yfinance` present; `ruff 0.17.4`; `pytest 9.2.0`. (Prior handoff reported deps unavailable — that blocker did not apply in this session.)
- H101 verification (committed files): `python3 -m ruff check/format --check run_nf_20261106_04_copper_gold.py tests/test_nf_20261106_04_copper_gold.py` OK; `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261106_04_copper_gold.py` → **10 passed**.
- H102: `ruff check/format --check` OK for runner+tests; `py_compile` OK; `PYTHONPATH=src pytest -q tests/test_nf_20261106_05_btc_bond.py` → **10 passed**. Executed `PYTHONPATH=src python3 run_nf_20261106_05_btc_bond.py` → **REJECT 6/9**, `exp_2026-11-06T12-34-38-533699Z`, 1.72s, summary written.
- Repo-wide lint/format: `python3 -m ruff check src tests run_*.py` and `ruff format --check src tests run_*.py` → clean (141 files formatted). Pinned `pytest -q -W error --cov=qtr --cov-branch` (100% `src/qtr`) **not re-run** (no `src/qtr` change).

## H102 key evidence (OOS Val+Test)
- Selected (train-only WF 1.055): `lookback=252, entry_z=1.0, exit_z=0.5, vol_target=0.15`. Panel 5611 rows (train 3116 / val 1096 / test 1399).
- Metrics (2495 periods, **19 trades**): Sharpe **1.173** (pass), PF **1.428** (pass), max DD **-4.63%** (pass), trades 19 (**fail, <<200**), WF stability **2.317** (pass), worst-regime rolling-252 **-2.009** (fail), benchmark p **0.0473** (pass), IR **-0.420** (fail), perturbation min ratio **0.905** (pass). Train/Val/Test Sharpe 0.520/1.136/1.205.
- Ablations: random-exposure-matched 1.001/1.526/DD -2.76%/558 trades; buy-hold SPY 0.662/1.165/DD -17.97%; inverse risk-off 0.236/1.076/113 trades.
- Failure mode: hysteresis regime extremely sparse (19 OOS trades) — not trade-rich/robust; worst-regime/IR fail; random exposure comparable on Sharpe/PF with far more trades.

## What remains unresolved
- **H85–H102 all rejected.** H103 not pre-registered/executed.
- Cycle 16 discovery required per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4: reconcile lineage to H102, propose >=3 repo-new mechanism candidates across >=3 broad categories, score honestly, reassess NF-04/05/11r/12/17/20/21/03 with concrete evidence (no silent drops). Pre-register highest-information feasible candidate as **H103** with smallest decisive test.
- NF-05 runner used `tracker.log_config` (tracker lacks it) → `tracker_error` recorded in summary (non-fatal; artifact written). Same pattern as prior NF runners; harmless but could be cleaned if a runner is next touched (not a `src/qtr` defect).

## Approaches already tried / failed (evidence)
- **H102/NF-20261106-05 REJECT 6/9** (`exp_2026-11-06T12-34-38-533699Z`, `.experiments/nf_runs/nf_20261106_05_btc_bond/summary.json`): fails trades 19 (<<200), worst-regime -2.009, IR -0.420. Do **not** re-run/re-optimize H102 without a materially different, pre-registered mechanism that honestly addresses sparsity/turnover.
- No speculative changes to `src/qtr`, gates, or published artifacts.

## Precise next task (one task), with evidence and constraints
**Cycle 16 discovery: pre-register H103 (repo-new family), highest expected information.**
1. Reconcile lineage to H102 (`HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, runners/tests/artifacts). Confirm H85–H102 rejected; next unused H-ID **H103**.
2. Search >=3 materially distinct mechanism categories and propose >=3 **repo-new** candidates (NF-YYYYMMDD IDs). For each: mechanism/causal chain, observables + point-in-time availability, construction/timing/horizon, null + falsifier, free-data feasibility, turnover/cost/capacity/ops constraints, closest prior repo family + why not a variant, confounders/leakage/alt explanations. Reassess NF-04/05/11r/12/17/20/21/03 with concrete evidence (no silent drops).
3. Score honestly (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, exec 10%, support 5%). Select the **smallest decisive test** / highest-information feasible experiment.
4. Pre-register **H103** in `HYPOTHESIS_SPEC.md` (and register Cycle 16) **before** examining validation/protected-test outcomes. Implement runner + focused tests, run `ruff check/format --check` and focused pytest, then execute; record exp ID/verdict/ablations/artifact. Protected holdout never used for selection.
5. **Constraints:** `src/qtr` unchanged unless genuine evidenced defect (then run pinned `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` + Ruff). Free/public data only. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. No live/paper trading. Do not commit/push without explicit user request.

## Uncommitted state (intentional)
- `?? run_nf_20261106_05_btc_bond.py`
- `?? tests/test_nf_20261106_05_btc_bond.py`
- `?? .experiments/nf_runs/nf_20261106_05_btc_bond/` (cache + summary)
- `M HYPOTHESIS_SPEC.md`, `M NEW_FAMILY_RESEARCH_REGISTER.md`, `M HANDOFF_CURRENT_SESSION.md`, `M HANDOFF_NEXT.md`
