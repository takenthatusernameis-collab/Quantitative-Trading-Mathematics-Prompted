# HANDOFF_CURRENT.md — H111/NF-20261106-22 executed (REJECT 4/8); Cycle 26 required

## What changed
- **Cycle 25 discovery completed** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6 and prior `NEXT_TASK.md`:
  - Reconciled lineage to H110 (H85–H110 all rejected). Proposed 3 repo-new mechanism candidates across 3 broad categories, checked against H1–H110 root families (no parameter/instrument/universe/timeframe variants/audits). Reassessed deferred candidates NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, **NF-11 data-resolution path, SAME root mechanism — honest novelty, not a new root family**), NF-20261106-03 (VVIX, VIX-complex adjacency), NF-20261106-21 (RSP/SPY breadth) with concrete evidence (no silent drops). NF-06-11 CBOE PC ratio infeasible.
  - Scored (1–5, 25/25/20/15/10/5): NF-20261106-22 SMH/QQQ semiconductor capex-cycle **3.80** (selected/executed H111; tech capex-cycle/supply-chain leadership; some trend/beta adjacency risk noted), NF-20261106-23 XHB/XLU housing-rate-sensitivity **3.55** (deferred; overlaps rates/financial-conditions channels), NF-20261106-24 XBI/XLV biotech funding-risk-appetite **3.35** (deferred; weaker separation from risk-on/rates-duration beta).
  - Pre-registered **H111 / NF-20261106-22** (SMH/QQQ semiconductor capex-cycle leadership → vol-targeted long SPY reduced when SMH abnormally weak vs QQQ, hysteresis-like continuous scaling, 1-bar delay) in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 25.
  - Implemented `run_nf_20261106_22_smh_qqq_semicapex.py` and `tests/test_nf_20261106_22_smh_qqq_semicapex.py` (10 focused tests). Executed experiment `exp_2026-11-06T15-52-07-899045Z` (completed, 1.3s) and recorded verdict. Artifact `.experiments/nf_runs/nf_20261106_22_smh_qqq_semicapex/summary.json`.
- Updated `NEXT_TASK.md` for Cycle 26 → H112. Updated this handoff.
- `src/qtr` unchanged. No published/certified artifacts, verdicts, thresholds, or frozen metrics modified.

## What was actually verified
- Focused tests: `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261106_22_smh_qqq_semicapex.py` → **10 passed** (1.42s).
- Lint/format on touched files: `python3 -m ruff check run_nf_20261106_22_smh_qqq_semicapex.py tests/test_nf_20261106_22_smh_qqq_semicapex.py` → All checks passed; `python3 -m ruff format --check ...` → clean.
- Data feasibility (yfinance): SMH/QQQ/SPY 4233 rows, 0 non-positive, 2010-01-04→2026-10-30 (runner fetch). Pre-execution sanity check confirmed 4233 rows/0 non-positive to 2026-10-30.
- Experiment execution (free/public yfinance): `python3 run_nf_20261106_22_smh_qqq_semicapex.py` → `exp_2026-11-06T15-52-07-899045Z`, **REJECT 4/8**.
- Pinned `src/qtr` 100% coverage/`-W error` suite **not re-run** (evidence: no `src/qtr` changes). Run if `src/qtr` changes.
- Pre-existing known issue unchanged: `test_no_runner_compares_a_p_value_against_max_p_value_directly` / 11 NF runners compare `bench_p <= GATES["max_p_value"]` directly; H111 runner follows existing pattern (not modified; semantics/published gate behavior impact unchanged).

## H111 result (REAL, pre-registered gates)
- Selected (train-only 4-fold WF): `lookback=21, z_window=252, entry_scale=1.0, vol_target=0.10` (selection WF mean 1.482, train Sharpe 0.821).
- OOS Val+Test (477 trades): Sharpe **0.805** fail, PF **1.149** fail, max DD **-11.89%** pass, trades **477** pass, WF stability **0.980** pass, worst-regime rolling-252 Sharpe min **-1.062** fail (worst quartile -0.214), benchmark-p **1.0** / IR **-0.242** fail, perturbation min ratio **0.996** pass.
- Ablations (OOS): buy-hold SPY 0.720/1.148/DD -18.21%/1; random-exposure-matched 0.549/1.129/DD -7.24%/1717; inverse-stress-long 0.226/1.130/DD -9.26%/476.
- Verdict rationale: drawdown reduced, perturbation-stable, WF stable and beats random exposure, but no validated risk-adjusted edge vs buy-hold. Specific pre-registered semiconductor-weakness mapping tested; does not test all technology-capex constructions. No gate weakened.

## What remains unresolved
- **Cycle 26 required** (directive §4/§6): H85–H111 all rejected. Next unused H-ID **H112** (H24/H68–H73/H76–H79 unassigned, not recycled).
- Deferred candidates still need concrete reassessment in Cycle 26 (do not silently drop): NF-04 blocked (no free point-in-time term-structure/roll proxy); NF-05 turnover/net-of-cost; NF-07 weak safe-haven check; NF-08 weak proxy; NF-10 adjacency/inconclusive; NF-11 adjacency; NF-11r/NF-06-18 TNX-FVX **NF-11 data-resolution path, same root mechanism, honest novelty, not new root family**; NF-13 adjacency/weak proxy; NF-15 weak exploratory; NF-17 turnover/cost; NF-20 event calendar/timestamp; NF-21 weak/adjacency; NF-06-11 CBOE PC ratio infeasible; NF-20261106-03 VVIX VIX-complex adjacency; NF-20261106-21 RSP/SPY breadth adjacency/exploratory weakness; NF-20261106-23 XHB/XLU housing-rate-sensitivity overlaps rates channels; NF-20261106-24 XBI/XLV biotech weaker separation from risk-on/rates-duration beta.

## Failed/blocked approaches (evidence)
- **H111 (executed, REJECT 4/8, `exp_2026-11-06T15-52-07-899045Z`):** fails Sharpe/PF/worst-regime/benchmark-p/IR; DD/WF/perturbation/random-exposure comparison acceptable but no risk-adjusted edge vs buy-hold. Artifact `.experiments/nf_runs/nf_20261106_22_smh_qqq_semicapex/summary.json`. Do not re-run NF-22/H111 without a materially different, pre-registered mechanism.
- **H110 (prior, REJECT 4/8):** XLY/XLP consumer leadership, fails Sharpe/PF/worst-regime/benchmark-p/IR.
- **NF-11r still NF-11 resolution path** (not repo-new root family); do not count as new family if pursued.
- No new `src/qtr` defects evidenced; no repeated identical approach retried.

## One precise next task
Perform **Cycle 26 discovery → pre-register H112** (and implement/execute only if decision-ready and feasible in-session without weakening gates):
1. Reconcile lineage to H111 (H85–H111 all rejected). Propose ≥3 **repo-new** mechanism candidates spanning ≥3 broad mechanism categories, checked against all root families H1–H111. Explicitly reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (NF-11 resolution path, honest novelty), NF-20261106-03, NF-20261106-21, NF-20261106-23, NF-20261106-24 with concrete evidence — no silent drops.
2. Score each 1–5 using directive weights (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%) with honest adjacency notes.
3. Pre-register the highest-expected-information **feasible** candidate as **H112** in `HYPOTHESIS_SPEC.md` and record candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 26. Keep NF-ID as family-level lineage key. Specify smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, ablations.
4. If decision-ready with free/public yfinance data and no `src/qtr` change: implement `run_nf_*_*.py` + focused tests, run `ruff check/format --check` and focused pytest, execute, record verdict (OOS Val+Test only for selection/gates as pre-registered). **Do not** weaken gates, modify published/certified artifacts, use holdout for selection, or change `src/qtr` unless a genuine defect is evidenced (then run pinned 100% coverage suite).
5. If no feasible candidate: document blockers/evidence and leave a precise handoff; do not invent candidates or default to maintenance-only parameter work.
