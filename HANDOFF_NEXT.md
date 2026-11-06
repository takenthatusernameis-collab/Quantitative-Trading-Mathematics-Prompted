# HANDOFF_NEXT — Cycle 17 discovery / pre-register & execute H104

**State:** H1–H103 all REJECTED. H103 (NF-20261106-06, FXA AUD commodity-currency global risk-appetite → SPY timing, `exp_2026-11-06T12-54-14-976207Z`) REJECT 3/9 — fails Sharpe 0.510, PF 1.154, worst-regime -1.553, benchmark-p null, IR -0.616, perturbation 0.435; passes trades 692/DD/WF (continuous scaling fixed H95 sparsity but no validated edge). `src/qtr` unchanged. See `.experiments/nf_runs/nf_20261106_06_fxa_risk/summary.json`, `HYPOTHESIS_SPEC.md` §H103, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 16.

**One precise next task (Cycle 17, directive §4):**
1. Reconcile lineage to H103; next unused H-ID **H104**.
2. Propose >=3 repo-new mechanism candidates across >=3 broad categories (NF-YYYYMMDD), with mechanism/causal chain, point-in-time observables, construction/timing, null+falsifier, free-data feasibility, costs/turnover/capacity, closest prior family + why not variant, confounders/leakage. Reassess NF-04/05/11r/12/17/20/21/03/07 with concrete evidence (no silent drops). Avoid FX/macro risk-appetite variants adjacent to H95/H103 unless materially distinct and addressing their decisive failures.
3. Score honestly (25/25/20/15/10/5). Select smallest decisive / highest-information feasible test.
4. Pre-register **H104** before validation/protected-test outcomes; implement runner+tests, `ruff check/format --check` + focused pytest, execute, record verdict/exp ID/ablations. Protected holdout never used for selection.
5. **Constraints:** `src/qtr` unchanged unless evidenced defect (then pinned `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing` + Ruff). Free/public data only. No gate weakening. No changes to published artifacts/verdicts/certified numbers. No commit/push without explicit user request. Do not re-run H103 without a materially different pre-registered mechanism.
