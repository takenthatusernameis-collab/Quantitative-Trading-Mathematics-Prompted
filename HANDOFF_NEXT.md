# HANDOFF_NEXT — Cycle 16 discovery / pre-register & execute H103

**State:** H1–H102 all REJECTED. H102 (NF-20261106-05, BTC/TLT risk-appetite → SPY timing, `exp_2026-11-06T12-34-38-533699Z`) REJECT 6/9 — fails trades 19 (<<200), worst-regime -2.009, IR -0.420; regime extremely sparse (see `.experiments/nf_runs/nf_20261106_05_btc_bond/summary.json`, `HYPOTHESIS_SPEC.md` §H102). `src/qtr` unchanged. H101 (`84606f9`) already executed/REJECT; verified clean this session.

**One precise next task (Cycle 16, directive §4):**
1. Reconcile lineage to H102; next unused H-ID **H103**.
2. Propose >=3 repo-new mechanism candidates across >=3 broad categories (NF-YYYYMMDD), with mechanism/causal chain, point-in-time observables, construction/timing, null+falsifier, free-data feasibility, costs/turnover/capacity, closest prior family + why not variant, confounders/leakage. Reassess NF-04/05/11r/12/17/20/21/03 with concrete evidence (no silent drops).
3. Score honestly (25/25/20/15/10/5). Select smallest decisive / highest-information feasible test.
4. Pre-register **H103** before validation/protected-test outcomes; implement runner+tests, `ruff check/format --check` + focused pytest, execute, record verdict/exp ID/ablations. Protected holdout never used for selection.
5. **Constraints:** `src/qtr` unchanged unless evidenced defect (then pinned `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` + Ruff). Free/public data only. No gate weakening. No changes to published artifacts/verdicts/certified numbers. No commit/push without explicit user request. Do not re-run H102 without a materially different pre-registered mechanism.
