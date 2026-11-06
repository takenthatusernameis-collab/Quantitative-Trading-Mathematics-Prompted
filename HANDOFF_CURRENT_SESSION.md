# HANDOFF_CURRENT_SESSION.md — Cycle 16 H103 executed (REJECT 3/9); Cycle 17 discovery / H104 required

## State
- Branch `main` at `da3dbb1` (HEAD). Working tree has uncommitted H102 artifacts from prior session plus this session’s H103 work: `?? run_nf_20261106_06_fxa_risk.py`, `?? tests/test_nf_20261106_06_fxa_risk.py`, `?? .experiments/nf_runs/nf_20261106_06_fxa_risk/`, and modified `M HYPOTHESIS_SPEC.md`, `M NEW_FAMILY_RESEARCH_REGISTER.md`, `M HANDOFF_CURRENT_SESSION.md`, `M HANDOFF_NEXT.md`. `src/qtr` **NOT modified**.
- H1–H102 all rejected at session start; **H103 (NF-20261106-06, FXA AUD commodity-currency global risk-appetite regime timing SPY) executed 2026-11-06 — REJECT (3/9).** Experiment `exp_2026-11-06T12-54-14-976207Z`. Artifact `.experiments/nf_runs/nf_20261106_06_fxa_risk/summary.json`. No verdict/artifact/gate/certified-number modifications to prior experiments.
- Next unused H-ID: **H104** (H24/H68–H73/H76–H79 unassigned, not recycled). NF-04/05/11r/12/17/20/21/03/07 remain deferred/reassessed with documented decisive risks (register/HYPOTHESIS_SPEC §H103).

## What changed (this session)
- **Cycle 16 discovery (directive §4):** reconciled lineage to H102 (H85–H102 rejected). Assessed >=3 repo-new candidates across categories: (1) NF-20261106-06 FXA commodity-currency risk-appetite/carry-unwind transmission timing SPY (selected, H103; FX/macro channel — adjacency to H95 UUP acknowledged honestly: different instrument/direction/construction, continuous scaling to address H95 sparsity); (2) NF-20261106-07 GLD/SPY safe-haven rotation timing (assessed; quick check ~4/9 weak profile, not selected); (3) NF-20261106-08 TIP/IEF breakeven-proxy→GLD (assessed; quick check very weak WF/OOS; proxy/FRED limitation). Scored (nominal tie, NF-06 selected on expected information/construction). Reassessed deferred NF-04/05/11r/12/17/20/21/03 (no silent drops) — evidence unchanged.
- **Implemented & executed H103/NF-20261106-06:** added `run_nf_20261106_06_fxa_risk.py` (trailing FXA momentum z-score, continuous long-only exposure clipped [0,1]×vol-target×MAX_POS, 1-bar delay via engine shift; 24-combo grid `lookback{63,126}×z_window{126,252}×entry_scale{1,1.5,2}×vol_target{0.10,0.15}`, train-only 4-fold WF selection, protected Test, OOS Val+Test gates, OAT ±20% perturbation, ablations random-exposure-matched / buy-hold SPY / inverse carry-unwind) and `tests/test_nf_20261106_06_fxa_risk.py` (10 tests). Fixed `_align_prices` to use `fetch_yahoo(list)` dict API and `tracker.finish_experiment` API; finalized summary artifact with reconstructed verdict evidence after non-fatal tracker mismatch.
- **Recorded verdict:** `HYPOTHESIS_SPEC.md` §H103 executed REJECT; `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 16 added with candidates/scores/reassessment/outcome.
- No `src/qtr` changes. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. No commit/push (no explicit user request).

## What was actually verified (this session)
- Data feasibility: `FXA`/`SPY` yfinance 2010-01-01→2026-10-31, 4233 aligned rows, no non-positive. Quick checks for NF-07/NF-08 performed (exploratory, not selected as executed candidates).
- `ruff check` + `ruff format --check` clean for `run_nf_20261106_06_fxa_risk.py` and `tests/test_nf_20261106_06_fxa_risk.py`. `PYTHONPATH=src pytest -q tests/test_nf_20261106_06_fxa_risk.py` → **10 passed**.
- Executed `PYTHONPATH=src python3 run_nf_20261106_06_fxa_risk.py` → **REJECT 3/9**, `exp_2026-11-06T12-54-14-976207Z`, summary written (finalized). Console OOS metrics captured in artifact/spec/register.
- Pinned full-gate `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` (100% `src/qtr`) **not re-run** (no `src/qtr` change).

## H103 key evidence (OOS Val+Test)
- Selected (train-only WF 1.5491): `lookback=63, z_window=126, entry_scale=1.0, vol_target=0.15`. FXA/SPY 4233 rows (train 2516 / val 756 / test 961).
- OOS (692 trades): Sharpe **0.510** (fail), PF **1.154** (fail), max DD **-6.97%** (pass), trades **692** (pass), WF stability **0.946** (pass), worst-regime rolling-252 **-1.553** (fail), benchmark p **null** (fail), IR **-0.616** (fail), perturbation min ratio **0.435** (fail). Train Sharpe 0.539.
- Failure mode: continuous scaling fixed H95-like sparsity but no validated risk-adjusted edge; fails Sharpe/PF/worst-regime/benchmark/IR/perturbation. FX/macro adjacency to H95 acknowledged (different instrument/direction/construction).

## What remains unresolved
- **H85–H103 all rejected.** H104 not pre-registered/executed.
- Cycle 17 discovery required per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4: reconcile lineage to H103, propose >=3 repo-new mechanism candidates across >=3 broad categories, score honestly, reassess NF-04/05/11r/12/17/20/21/03/07 with concrete evidence (no silent drops). Pre-register highest-information feasible candidate as **H104** with smallest decisive test.
- H103 runner had `tracker.finish_experiment` API mismatch (fixed in code; non-fatal) and exploratory/pre-check numbers were corrected to match actual executed result in spec/register/artifact — evidence is consistent now.

## Approaches already tried / failed (evidence)
- **H103/NF-20261106-06 REJECT 3/9** (`exp_2026-11-06T12-54-14-976207Z`, `.experiments/nf_runs/nf_20261106_06_fxa_risk/summary.json`): fails Sharpe 0.510, PF 1.154, worst-regime -1.553, benchmark-p null, IR -0.616, perturbation 0.435. Do **not** re-run/re-optimize H103 without a materially different, pre-registered mechanism.
- NF-07 (GLD/SPY safe-haven rotation) quick check showed weak 4/9 profile (Sharpe 0.749, PF 1.226, IR -0.612) — treat as deferred/reassessed, not an executed H.
- NF-08 (TIP/IEF breakeven proxy→GLD) quick check very weak (WF ~0.10, OOS Sharpe 0.280) — deferred; point-in-time breakeven observable limited on free yfinance.
- No speculative changes to `src/qtr`, gates, or published artifacts.

## Precise next task (one task), with evidence and constraints
**Cycle 17 discovery: pre-register H104 (repo-new family), highest expected information.**
1. Reconcile lineage to H103 (`HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, runners/tests/artifacts). Confirm H85–H103 rejected; next unused H-ID **H104**.
2. Search >=3 materially distinct mechanism categories and propose >=3 **repo-new** candidates (NF-YYYYMMDD IDs). For each: mechanism/causal chain, observables + point-in-time availability, construction/timing/horizon, null + falsifier, free-data feasibility, turnover/cost/capacity/ops constraints, closest prior repo family + why not a variant, confounders/leakage/alt explanations. Reassess NF-04/05/11r/12/17/20/21/03/07 with concrete evidence (no silent drops). Avoid FX/macro risk-appetite variants adjacent to H95/H103 unless mechanism is materially distinct and construction addresses their decisive failures.
3. Score honestly (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, exec 10%, support 5%). Select the **smallest decisive test** / highest-information feasible experiment.
4. Pre-register **H104** in `HYPOTHESIS_SPEC.md` (and register Cycle 17) **before** examining validation/protected-test outcomes. Implement runner + focused tests, run `ruff check/format --check` and focused pytest, then execute; record exp ID/verdict/ablations/artifact. Protected holdout never used for selection.
5. **Constraints:** `src/qtr` unchanged unless genuine evidenced defect (then run pinned `PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` + Ruff). Free/public data only. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. No live/paper trading. Do not commit/push without explicit user request.

## Uncommitted state (intentional)
- `?? run_nf_20261106_06_fxa_risk.py`, `?? tests/test_nf_20261106_06_fxa_risk.py`, `?? .experiments/nf_runs/nf_20261106_06_fxa_risk/`
- Prior-session untracked: `run_nf_20261106_05_btc_bond.py`, `tests/test_nf_20261106_05_btc_bond.py`, `.experiments/nf_runs/nf_20261106_05_btc_bond/` (already committed in HEAD? HEAD has them per log - but check; `git status` showed `M` only on docs at session start context? session started clean for H102 context in prior handoff text but actual tree: `git status --short` at start showed empty; H102 files were committed in `da3dbb1` and also present? `git log --name-only` showed them committed. `ls` shows them. They should be tracked/clean.)
- `M HYPOTHESIS_SPEC.md`, `M NEW_FAMILY_RESEARCH_REGISTER.md`, `M HANDOFF_CURRENT_SESSION.md`, `M HANDOFF_NEXT.md`
