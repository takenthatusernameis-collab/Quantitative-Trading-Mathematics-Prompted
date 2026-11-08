# Handoff — Current Session (Cycle 71 complete, H157 REJECT)

## What changed
- **Cycle 71 discovery (directive §4):** Reconciled lineage to H156 (H85–H156 all rejected/recorded). Proposed/scored 3 repo-new/decisive candidates across 3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). **NF root integrity:** NF-20261108-27 (EWJ-vs-SPY relative-momentum, regional/Japan developed-market leadership) verified unused as an executed root — EWJ appears in H2 universe spec and committed `.experiments` price artifacts but **never executed as a SPY-timing signal** (no NF/H/runner/artifact). NF-20261108-22 (EFA-EEM DM/EM relmom) and NF-20261108-20 (IEF RV stress) verified unused/deferred. NF-20261108-16 held (3.90, calendar adj). NF-20261108-26/21/23 deferred. NF-06-28 legacy runner/test no artifact (credit adj H94/H108). NF-08-13 ES-SPY basis stub (not decision-ready). No H99/H149-style collisions.
- **Candidates:** NF-20261108-27 EWJ-vs-SPY relmom (3.55, **selected/executed as H157**); NF-20261108-22 EFA-EEM DM/EM relmom (3.55, deferred, relmom-class/H144 adj); NF-20261108-20 IEF RV stress (3.50, deferred, bond-RV/maturity adj H151). Selection justified (tie-break): NF-27 highest expected-information decisive test — repo-new executed timing pair (EWJ previously unexecuted as SPY-timing signal), clean regional/Japan leadership channel, bounded 16-combo grid, pre-registered inverse falsifier. Honest relmom-construction adjacency to H144/H145/H152 disclosed.
- **H157 pre-registered & executed (NF-20261108-27):** Added `run_nf_20261108_27_ewj_spy_relmom.py` and `tests/test_nf_20261108_27_ewj_spy_relmom.py` (7 tests). `src/qtr` unchanged. `ruff check/format` clean; focused pytest **7 passed**. Executed REAL → **REJECT 5/8**. Updated `HYPOTHESIS_SPEC.md` §H157, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 71, `NEXT_TASK.md` (Cycle 72 / H158), `HANDOFF_NEXT.md`, this handoff.

## H157 result (REAL, pre-registered gates)
- Mechanism: EWJ-vs-SPY relative-momentum regime (regional/Japan developed-market leadership / funding-spillover transmission). Stress on **negative** z of `ret(EWJ,w)-ret(SPY,w)` (EWJ leadership weak) de-risks vol-targeted long SPY. Honest adjacency: relmom/z-score construction class adjacent to H144 EEM-SPY (REJECT 3/8, inverse outperformed), H145 GLD-SPY (REJECT 4/8), H152 SLV-GLD relmom→SPY (REJECT 4/8) — different pair/mechanism (regional leadership vs EM/safe-haven/precious metals); distinct from H85 lead-lag form.
- Data: SPY+EWJ 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755). Free/public yfinance auto-adjust.
- Selected (train-only 4-fold WF): `mom_window=63, z_window=126, entry_scale=1.0, vol_target=0.15` (WF mean 0.930).
- OOS Val+Test (2846 trades, n=1259): Sharpe **1.202** pass, PF **1.273** fail, maxDD **-2.47%** pass, trades **2846** pass, WF stability **1.346** pass, worst-regime rolling-252 Sharpe **-0.543** fail, benchmark p **0.932** / IR **-0.688** fail, perturbation **0.988** pass → **5/8 REJECT**.
- Ablations (OOS): buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **-0.323**/0.874/-2.59%/1120 (much weaker — structure present — no benchmark edge); **inverse regime** (de-risk when EWJ outperforms/positive z) **0.222**/1.045/-3.85%/2950 — much weaker than base (direction supported, no benchmark edge).
- Verdict: **REJECT (5/8)**. Passes Sharpe/DD/trades/WF/perturbation but fails PF (1.273, narrow miss)/worst-regime/benchmark. Random/inverse support direction/structure but no benchmark-significant edge (p=0.932, IR=−0.688). No gate weakened.

## Actually verified
- `python -m ruff check run_nf_20261108_27_ewj_spy_relmom.py tests/test_nf_20261108_27_ewj_spy_relmom.py` — All checks passed.
- `python -m ruff format --check run_nf_20261108_27_ewj_spy_relmom.py tests/test_nf_20261108_27_ewj_spy_relmom.py` — 2 files already formatted (after format).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_27_ewj_spy_relmom.py` — **7 passed**.
- `PYTHONPATH=src python run_nf_20261108_27_ewj_spy_relmom.py` — completed; artifact `.experiments/nf_runs/nf_20261108_27_ewj_spy_relmom/summary.json` written (+ `grid.csv`, `data_meta.json`, 13.54s). Verdict **REJECT 5/8**.

## Unresolved / constraints
- H85–H157 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed. Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. H157 runner/tests/docs and experiment artifacts are uncommitted local changes.
- `src/qtr` pinned full gates were **not rerun** (no `src/qtr` change). If `src/qtr` is touched, run: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## Approaches that failed / evidence (do not blindly repeat)
- H157 (EWJ-SPY relmom, this cycle) failed PF/worst-regime/benchmark; Sharpe passed but no benchmark edge; random-exposure much weaker and inverse much weaker (direction supported). Do not rerun same construction.
- NF-08-13 ES-SPY basis stub only (not decision-ready). NF-06-28 legacy runner/test but no artifact (credit adjacency H94/H108).
- NF-08-20 IEF RV adjacent to H151 TLT RV (REJECT 5/8) — must justify maturity separation before execution. NF-08-22 EFA-EEM relmom adjacent to relmom class/H144 — modest expected information.

## One precise next task
**Execute Cycle 72 discovery and implement+run H158** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H157, propose >=3 repo-new candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops) — **verify NF roots against executed H-IDs/artifacts before selection**. Pre-register H158 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/`HANDOFF_NEXT.md`. Justify independence from rejected classes including EWJ-SPY relmom H157 and all prior listed classes. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless evidenced defect requires it (then rerun pinned full gates).
