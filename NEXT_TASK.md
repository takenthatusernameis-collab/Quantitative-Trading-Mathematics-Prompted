# NEXT_TASK.md — post H100 (Cycle 14 discovery → H101 pre-registration/decision-ready experiment)

## State
- H100 (NF-20261106-02, rates-vol / Treasury implied-vol stress transmission timing, ^MOVE → SPY) **EXECUTED and REJECTED (5/9)**, `exp_2026-11-06T04-36-03-876862Z`.
  - OOS Val+Test (1717 periods, 199 trades): Sharpe 1.003 (pass ≥1.0), PF 1.227 (fail <1.3), max DD -9.14% (pass), trades 199 (fail <200), WF stability 2.015 (pass; train 0.497, val 1.011, test 1.001), worst-regime rolling-252 Sharpe -1.002 (fail <0.3), bench p=0.0299 (pass, runner direct check), IR -0.530 (fail <0), perturbation min ratio 0.925 (pass). Train/Val/Test Sharpe 0.497 / 1.011 / 1.001.
  - Ablations: random-exposure-matched -0.080/0.976 (603 trades, strategy beats random); buy-hold SPY 0.798/1.165/DD -17.97%; inverse MOVE-elevated long 0.042/1.015 (250 trades).
  - Runner `run_nf_20261106_02_move_rates_vol.py` + tests `tests/test_nf_20261106_02_move_rates_vol.py` (10 tests pass). Lint/format clean. `src/qtr` unchanged. See HYPOTHESIS_SPEC.md §H100 and NEW_FAMILY_RESEARCH_REGISTER.md Cycle 13.
- H85–H100 all rejected. No pre-registered NF candidates remain executable without resolving a documented decisive risk. Next unused H-ID: **H101** (H24/H68–H73/H76–H79 unassigned, not recycled).
- Pre-existing: `test_no_runner_compares_a_p_value_against_max_p_value_directly` / 11 NF runners compare `bench_p <= GATES["max_p_value"]` directly; re-routing via `benchmark_significance_gate` changes semantics/adds IR>0 and affects published gate behavior — do not “fix” without explicit authorization and impact analysis.

## Next task (Cycle 14 per STRATEGY_FAMILY_EXPANSION_DIRECTIVE §4/§6)
Perform a fresh new-family discovery cycle: reconcile lineage to H100, propose ≥3 repo-new mechanism candidates spanning ≥3 broad mechanism categories (checked against H1–H100 root families; no parameter/instrument/universe/timeframe variants or audits), score each 1–5 with directive weights (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%), and **reassess deferred candidates NF-20261105-04/05/11r (NF-11 data-resolved TNX/FVX variant, novelty honest)/12/17/20/21 and NF-20261106-03 (VVIX, VIX-complex adjacency) with concrete evidence** (do not silently drop). Pre-register the highest-expected-information feasible candidate as **H101** with the smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, and ablations.

If decision-ready and feasible in-session (free/public yfinance, no `src/qtr` change): implement `run_nf_*_*.py` + focused tests, run lint/format/focused pytest, execute, and record the verdict on pre-registered OOS Val+Test gates only. Record all candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 14 and register H101 in `HYPOTHESIS_SPEC.md`.

## Constraints
`src/qtr` unchanged unless a genuine evidenced defect requires it (then run pinned 100% src/qtr coverage/`-W error`). Free/public data only. Protected holdout never used for selection. No gate weakening. No changes to published results/artifacts/verdicts/certified numbers. Preserve 100% src/qtr statement/branch coverage, Ruff, and warning-as-error gates. Assign next unused H-ID only on formal registration; keep NF-ID as family-level lineage key.
