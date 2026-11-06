# NEXT_TASK.md — post H99 (Cycle 13 → H100 pre-registration/decision-ready experiment)

## State
- H98 (NF-20261105-19, PEAD) REJECTED (5/9), `exp_2026-11-06T01-30-29-259047Z`.
- H99 (NF-20261106-01, gold-miner vs gold real-optionality spread MR, GDX/GLD → long GDX) **EXECUTED and REJECTED (4/9)**, `exp_2026-11-06T03-04-40-778747Z`.
  - OOS Val+Test (1716 periods, 1286 trades): Sharpe 0.329 (fail ≥1.0), PF 1.065 (fail <1.3), max DD -12.47% (pass), trades 1286 (pass), WF stability 1.000 (pass; train -0.090, test_wf_mean 0.486), worst-regime rolling-252 Sharpe -1.046 (fail <0.3), bench p=0.123 vs buy-hold GDX (fail), IR -0.592 (fail), perturbation min ratio 0.937 (pass). Train/Val/Test Sharpe -0.090 / -0.012 / 0.653.
  - Ablations: random-exposure-matched Sharpe 0.763/PF 1.173 **> strategy** (timing falsified); inverse-signal 0.243/1.047; GDX buy-hold OOS Sharpe 0.578/PF 1.107/DD -49.79%. Root cause: log(GDX/GLD) near-unit-root (shared gold factor), rare z-score triggers, incidental exposure.
  - Runner `run_nf_20261106_01_miner_gold_rv.py` + tests `tests/test_nf_20261106_01_miner_gold_rv.py` (10 tests pass). Lint/format clean. `src/qtr` unchanged. See HYPOTHESIS_SPEC.md §H99 and NEW_FAMILY_RESEARCH_REGISTER.md Cycle 12.
- H85–H99 all rejected. No pre-registered NF candidates remain executable without resolving a documented decisive risk. Next unused H-ID: **H100** (H24/H68–H73/H76–H79 unassigned, not recycled).
- Pre-existing: `test_no_runner_compares_a_p_value_against_max_p_value_directly` (11 NF runners compare `bench_p <= GATES["max_p_value"]` directly; re-routing via `benchmark_significance_gate` changes semantics/adds IR>0 and affects published gate behavior — do not “fix” without explicit authorization and impact analysis).

## Next task (Cycle 13 per STRATEGY_FAMILY_EXPANSION_DIRECTIVE §4/§6)
Perform a fresh new-family discovery cycle: reconcile lineage to H99, propose ≥3 repo-new mechanism candidates spanning ≥3 broad mechanism categories (checked against H1–H99 root families; no parameter/instrument/universe/timeframe variants or audits), score each 1–5 with directive weights (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%), and **reassess deferred candidates NF-20261105-04/05/11/12/17/20/21 with concrete evidence** (do not silently drop). Pre-register the highest-expected-information feasible candidate as **H100** with the smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, and ablations.

If decision-ready and feasible in-session (free/public yfinance, no `src/qtr` change): implement `run_nf_*_*.py` + focused tests, run lint/format/focused pytest, execute, and record the verdict on pre-registered OOS Val+Test gates only. Record all candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 13 and register H100 in `HYPOTHESIS_SPEC.md`.

## Constraints
`src/qtr` unchanged unless a genuine evidenced defect requires it (then run pinned 100% src/qtr coverage/`-W error`). Free/public data only. Protected holdout never used for selection. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. Preserve 100% src/qtr statement/branch coverage, Ruff, and warning-as-error gates. Assign next unused H-ID only on formal registration; keep NF-ID as family-level lineage key.
