# Handoff — Current Session (Cycle 70 complete, H156 REJECT)

## What changed
- **Cycle 70 discovery (directive §4):** Reconciled lineage to H155 (H85–H155 all rejected/recorded). Proposed/scored 3 repo-new/decisive candidates across 3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). **NF root integrity:** NF-20261108-28 (UUP realized-volatility stress) verified unused as an executed root — UUP appears only in H95 (NF-20261105-16, REJECT 3/9, 88 trades) as *trailing strength/direction* (first-moment/hysteresis), not as *realized volatility* (second-moment). Honest adjacency disclosed: same instrument (UUP) different moment/channel; RV-stress construction class adjacent to H151/H143/H149 (different asset/mechanism). NF-20261108-27 (EWJ-vs-SPY relmom) and NF-20261108-20 (IEF RV stress) verified unused/deferred. NF-20261108-16 held (3.90, calendar adj). No H99/H149-style collisions.
- **Candidates:** NF-20261108-28 UUP RV stress (3.70, **selected/executed as H156**); NF-20261108-27 EWJ-vs-SPY relmom (3.55, deferred); NF-20261108-20 IEF RV stress (3.50, deferred). Selection justified: highest feasible score, repo-new second-moment UUP observable addressing H95’s sparse first-moment construction; modest expected information given H95/RV-stress-class rejects but genuinely untested moment.
- **H156 pre-registered & executed (NF-20261108-28):** Added `run_nf_20261108_28_uup_rv_stress_spy.py` and `tests/test_nf_20261108_28_uup_rv_stress_spy.py` (7 tests). `src/qtr` unchanged. `ruff check/format` clean; focused pytest **7 passed**. Executed REAL → **REJECT 5/8**. Updated `HYPOTHESIS_SPEC.md` §H156, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 70, `NEXT_TASK.md` (Cycle 71 / H157), `HANDOFF_NEXT.md`, this handoff.

## H156 result (REAL, pre-registered gates)
- Mechanism: UUP realized-volatility z-score stress (USD/FX global financial-conditions uncertainty). Stress on **positive** z (abnormally high UUP RV) de-risks vol-targeted long SPY. Honest adjacency: H95 UUP *direction* (REJECT 3/9, 88 trades, first moment) — different moment/channel; RV-stress construction class adj H151/H143/H149 (different asset).
- Data: SPY+UUP 3776 rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755). Free/public yfinance auto-adjust.
- Selected (train-only 4-fold WF): `rv_window=63, z_window=252, entry_scale=1.0, vol_target=0.15` (WF mean 0.970).
- OOS Val+Test (2885 trades, n=1259): Sharpe **1.158** pass, PF **1.262** fail, maxDD **-2.21%** pass, trades **2885** pass, WF stability **1.380** pass, worst-regime rolling-252 Sharpe **-1.620** fail, benchmark p **0.948** / IR **-0.670** fail, perturbation **0.986** pass → **5/8 REJECT**.
- Ablations (OOS): buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.229**/1.095/-3.27%/1404 (much weaker — structure present — but no benchmark edge); **inverse regime** **0.485**/1.108/-2.92%/2470 — much weaker than base (direction supported, no benchmark edge).
- Verdict: **REJECT (5/8)**. Passes Sharpe/DD/trades/WF/perturbation but fails PF (1.262, narrow miss)/worst-regime/benchmark. Random/inverse support direction/structure but no benchmark-significant edge (p=0.948, IR=−0.670). No gate weakened.

## Actually verified
- `python -m ruff check run_nf_20261108_28_uup_rv_stress_spy.py tests/test_nf_20261108_28_uup_rv_stress_spy.py` — All checks passed.
- `python -m ruff format --check run_nf_20261108_28_uup_rv_stress_spy.py tests/test_nf_20261108_28_uup_rv_stress_spy.py` — 2 files already formatted.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_28_uup_rv_stress_spy.py` — **7 passed**.
- `PYTHONPATH=src python run_nf_20261108_28_uup_rv_stress_spy.py` — completed; artifact `.experiments/nf_runs/nf_20261108_28_uup_rv_stress_spy/summary.json` written (+ `grid.csv`, `data_meta.json`, 13.24s). Verdict **REJECT 5/8**.

## Unresolved / constraints
- H85–H156 all REJECTED/recorded. Lineage gaps H24/H68–H73/H76–H79 remain unassigned (not recycled).
- No commit/push performed. Published/certified artifacts and thresholds unchanged. `src/qtr` unchanged. H156 runner/tests/docs and experiment artifacts are uncommitted local changes.
- `src/qtr` pinned full gates were **not rerun** (no `src/qtr` change). If `src/qtr` is touched, run: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## Approaches that failed / evidence (do not blindly repeat)
- H156 (UUP RV stress, this cycle) failed PF/worst-regime/benchmark; Sharpe passed but no benchmark edge; random-exposure much weaker and inverse much weaker (direction supported). Do not rerun same construction.
- NF-08-13 ES-SPY futures basis stub only (not decision-ready). NF-06-28 legacy runner/test but no artifact (credit adjacency H94/H108).
- NF-08-20 IEF RV stress adjacent to H151 TLT RV (REJECT 5/8) — must justify maturity separation before execution.

## One precise next task
**Execute Cycle 71 discovery and implement+run H157** per `NEXT_TASK.md` and `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: reconcile lineage to H156, propose >=3 repo-new candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops) — **verify NF roots against executed H-IDs/artifacts before selection**. Pre-register H157 (smallest decisive feasible test) before validation outcomes, add runner+focused tests, `ruff check/format`, focused pytest, execute, record verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/`HANDOFF_NEXT.md`. Justify independence from rejected classes including UUP RV stress H156 and all prior listed classes. Free/public data only; no gate weakening; no published artifact changes; no commit/push; do not modify `src/qtr` unless evidenced defect requires it (then rerun pinned full gates).
