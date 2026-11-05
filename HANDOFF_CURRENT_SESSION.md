# HANDOFF_CURRENT_SESSION.md — Cycle 8 H94 executed (REJECT 3/9); gates green

## State
- HEAD `a683fad` on `main` (local); `origin/main` not checked this session. Working tree has uncommitted changes from this session (H94 runner/tests/spec/register + formatting fixes).
- H94/NF-20261105-14 (credit risk-premium / flight-to-quality regime timing: HYG-IEF → SPY) **EXECUTED and REJECTED (3/9 gates)**. `exp_2026-11-05T18-20-38-363385Z`. Artifact: `.experiments/nf_runs/nf_20261105_14_credit_regime/summary.json`. `src/qtr` unchanged.
- H1–H94 lineage recorded. H85–H94 all rejected. NF-20261105-04/05/11/12 remain deferred with decisive risks documented (register Cycle 8). NF-20261105-16 (USD/UUP macro risk timing) deferred as cycle 8 runner-up.

## What changed (this session)
- New-family discovery Cycle 8 executed per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4/§6: reconciled lineage to H93, reassessed NF-04/05/11/12 with concrete evidence, proposed/scored 3 repo-new candidates across 3 categories (credit flight-to-quality, equity-bond correlation regime, USD macro risk), selected NF-20261105-14 (4.05 tie-break over NF-16 by distinct instruments/cleaner causal channel).
- Added `run_nf_20261105_14_credit_regime.py` (H94, 12-combo grid, train-only 4-fold WF selection, protected OOS Val+Test gates, perturbation, ablations: random-exposure-matched + buy-hold SPY, tracker/artifact logging). Data via `DataFetcher.fetch_yahoo` (adj_close/close extraction; `DataCache(cache_dir=Path(...))`).
- Added `tests/test_nf_20261105_14_credit_regime.py` (10 focused tests: pre-registration constants/config/grid, signal shape/bounds/warmup, benign/stress direction, missing symbol, unknown mode).
- Pre-registered H94 in `HYPOTHESIS_SPEC.md` and recorded Cycle 8 in `NEW_FAMILY_RESEARCH_REGISTER.md` (deferred reassessment, candidates/scores, execution, lineage row, Cycle 9 required).
- Applied `ruff format` to `run_nf_20261105_14_credit_regime.py`, `tests/test_nf_20261105_14_credit_regime.py`, and pre-existing `run_h29_lookahead_sweep.py` (format-check required it).
- Generated `.experiments/nf_runs/nf_20261105_14_credit_regime/summary.json` and tracker entries (`exp_2026-11-05T18-20-38-363385Z`). `src/qtr` not modified.

## What was actually verified (this session)
- H94 focused tests: `PYTHONPATH=src python -m pytest -q tests/test_nf_20261105_14_credit_regime.py` → **10 passed**.
- H94 execution: `PYTHONPATH=src python run_nf_20261105_14_credit_regime.py` → **REJECT 3/9**, artifact written. Selected `lookback=21, vol_target=0.10, signal_mode=sign` (train WF Sharpe 1.277). OOS Val+Test: Sharpe 0.925 (fail), PF 1.214 (fail), max DD -13.19% (pass), trades 318 (pass), WF stability 1.715 (pass), worst-regime 252d Sharpe -1.396 (fail), bench p=1.0 (fail), IR -0.478 (fail), perturbation min ratio 0.319 (fail; lookback 17→Sharpe 0.295). Ablations: random-exposure Sharpe 0.153, buy-hold SPY Sharpe 0.798.
- Lint: `python -m ruff check src tests run_*.py` → **All checks passed**.
- Format: `python -m ruff format --check src tests run_*.py` → **126 files already formatted** (after formatting `run_h29_lookahead_sweep.py`).
- **Not run this session:** full `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (directive/gates require 100% `src/qtr` coverage on change cycles; `src/qtr` was **not** changed this session — only runner/tests/docs/artifacts added). Run pinned gates before any commit/merge/push per AGENTS.md/NEXT_TASK constraints.

## What remains unresolved
- H85–H94 all rejected; H1–H30 exhausted; hypotheses up to H94 documented (H24/H68–H73/H76–H79 unassigned, not recycled).
- Deferred decisive risks unresolved: NF-04 (free point-in-time term-structure/roll proxy unavailable in pipeline), NF-05 (daily CS reversal turnover/net-of-cost under pre-registered assumptions), NF-11 (^IRX blocked / FRED not in pipeline / term-spread proxy ambiguous), NF-12 (dispersion construction/turnover complexity; lower expected information), NF-16 (USD/UUP macro — runner-up; FX-equity instability/UUP tracking falsifiers required if selected).
- Uncommitted working-tree changes (H94 + formatting + artifacts). No commit/push performed (never commit without explicit user request).

## Approaches already tried / failed
- H94 (NF-20261105-14, credit flight-to-quality HYG-IEF → SPY, exp `exp_2026-11-05T18-20-38-363385Z`): **REJECT 3/9**. Fails Sharpe 0.925/PF 1.214/worst-regime -1.396/bench p=1.0/IR -0.478/perturbation 0.319 (lookback fragility 21→17 collapses Sharpe to 0.295). Better than random exposure (0.153) but not cost-robust vs buy-hold SPY (0.798) on OOS.
- Runner integration bugs encountered and fixed (evidence-based, not verdict-affecting): `DataCache` takes `Path|None` (not str), `fetch_yahoo` returns dict-of-DataFrames with lowercase `adj_close/close` columns (not `Close`), `ExperimentTracker` uses `log_metrics`/`log_artifact`/`finish_experiment(status=...)` (not `log_results`/`log_metadata`/verdict arg signature used initially).

## Precise next task (one task), with evidence and constraints
**Cycle 9 new-family discovery (decision-ready pre-registration for H95), then smallest decisive test if feasible.** Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6 and register Cycle 8: reconcile lineage to H94, search >=3 repo-new mechanism candidates across >=3 broad mechanism categories, score honestly (do not inflate), and reassess NF-04/05/11/12/16 decisive risks with concrete evidence (do not silently drop; NF-16 is the cycle-8 runner-up — if selected, pre-register UUP tracking/FX-equity instability falsifiers and clean point-in-time construction). Select the highest-information feasible candidate, pre-register as **H95 (NF-YYYYMMDD-XX)** in `HYPOTHESIS_SPEC.md` + `NEW_FAMILY_RESEARCH_REGISTER.md` with smallest decisive test, explicit gates/costs/splits/rejection, then implement runner + focused tests. Run lint/format/focused tests; execute only if decision-ready and within compute budget; record exp/artifact/verdict.

**Evidence/constraints:** H85–H94 rejected (register lineage + artifacts). `src/qtr` unchanged this session; if `src/qtr` changes, run pinned gates and preserve **100% statement+branch coverage for `src/qtr`** (`python -m ruff check src tests run_*.py`, `python -m ruff format --check src tests run_*.py`, `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`). Do not relax `fail_under`, drop `-W error`, modify published artifacts/gate thresholds/verdicts/certified numbers, or re-run rejected families without a materially different pre-registered mechanism. Free/public data only; protected holdout never used for selection. Never commit without explicit user request.
