# HANDOFF_CURRENT.md — H117/NF-20261106-34 executed (REJECT 4/8); Cycle 32 required

## What changed
- **Cycle 31 task completed** (pre-registered H117 executed with data-feasibility verification):
  - Verified yfinance feasibility via `DataFetcher`/cache: 9 sector ETFs with full 2010+ history (`XLK,XLF,XLE,XLV,XLI,XLY,XLP,XLU,XLB`) + `SPY` = 4233 aligned rows each, 2010-01-04→2026-10-30, 0 non-positive. `XLC` (2018-06-19) and `XLRE` (2015-10-08) excluded to preserve pre-registered 2010+ sample/splits (spec draft listed `XLC` and typo `XLF?`); adjustment documented before execution.
  - Implemented `run_nf_20261106_34_sector_corr_regime.py` and `tests/test_nf_20261106_34_sector_corr_regime.py` (11 focused tests). Signal: trailing average pairwise sector return correlation z-score (lookback 21/63, z_window 126/252); abnormally high correlation (contagion) reduces vol-targeted long SPY continuously, 1-bar delay (`signals.shift(1)` in engine). Long-only, `max_position=0.5`, equity costs.
  - Executed experiment `exp_2026-11-07T00-23-49-421603Z` (completed, 6.19s). Artifact `.experiments/nf_runs/nf_20261106_34_sector_corr_regime/summary.json` (+ `grid.csv`).
  - Updated `HYPOTHESIS_SPEC.md` H117 section with executed outcome/metrics, lineage, and feasibility note.
  - Appended Cycle 31 discovery + outcome to `NEW_FAMILY_RESEARCH_REGISTER.md` (candidates NF-34/35/36 scored, deferred reassessments recorded, H117 REJECT lineage).
  - Updated `NEXT_TASK.md` for Cycle 32 → H118.
- `src/qtr` unchanged. No published/certified artifacts, verdicts, thresholds, or frozen metrics modified. No gate weakened. Protected holdout not used for selection.

## What was actually verified
- Data feasibility (real, via DataFetcher/cache): `XLK,XLF,XLE,XLV,XLI,XLY,XLP,XLU,XLB,SPY` 4233 rows, 0 non-positive, 2010-01-04→2026-10-30. `XLC` 2104 rows from 2018-06-19; `XLRE` 2782 from 2015-10-08 (excluded; documented).
- Focused tests: `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261106_34_sector_corr_regime.py` → **11 passed** (3.33s).
- Lint/format: `python3 -m ruff check run_nf_20261106_34_sector_corr_regime.py tests/test_nf_20261106_34_sector_corr_regime.py` → All checks passed; `python3 -m ruff format --check ...` → clean (2 files reformatted once, final clean).
- Experiment execution (free/public yfinance cache): `PYTHONPATH=src python3 run_nf_20261106_34_sector_corr_regime.py` → **REJECT 4/8**.
- Pinned `src/qtr` 100% coverage/`-W error` suite **not re-run** (evidence: no `src/qtr` changes). Run if `src/qtr` changes.
- Pre-existing known issue unchanged: NF runners compare `bench_p <= GATES["max_p_value"]` directly (tripwire `test_no_runner_compares_a_p_value_against_max_p_value_directly` flags NF runners); H117 follows existing pattern — not modified.

## H117 result (REAL, pre-registered gates)
- Selected (train-only 4-fold WF): `lookback=21, z_window=126, entry_scale=1.5, vol_target=0.15` (WF mean 1.613). Train Sharpe 0.943.
- OOS Val+Test (809 trades): Sharpe **0.918** fail, PF **1.169** fail, max DD **-8.93%** pass, trades **809** pass, WF stability **0.973** pass, worst-regime rolling-252 Sharpe min **-0.906** fail, benchmark-p **1.0** / IR **-0.324** fail, perturbation min ratio **0.939** pass.
- Ablations (OOS): buy-hold SPY 0.791/1.164/DD -17.97%/1; random-exposure-matched **1.158/1.223/DD -10.89%/808** (outperforms); inverse-stress-long 0.315/1.143/DD -11.41%/808.
- Verdict rationale: perturbation-stable, ample trades/WF stability, drawdown reduced vs buy-hold, but no validated risk-adjusted edge on pre-registered OOS gates (fails Sharpe/PF/worst-regime/benchmark-p/IR). Random-exposure ablation outperforms, indicating the specific correlation-z mapping does not add edge beyond exposure management in this construction. Specific pre-registered construction tested; not all correlation-regime constructions. No gate weakened.

## What remains unresolved
- **Cycle 32 required** (directive §4/§6): H85–H117 all rejected. Next unused H-ID **H118** (H24/H68–H73/H76–H79 unassigned, not recycled).
- Deferred candidates still need concrete reassessment in Cycle 32 (no silent drops): NF-04 blocked (no free point-in-time term-structure/roll proxy); NF-05 turnover/net-of-cost; NF-07 weak safe-haven check; NF-08 weak proxy; NF-10 adjacency/inconclusive; NF-11 adjacency; NF-11r/NF-06-18 TNX-FVX **NF-11 data-resolution path, SAME root mechanism — honest novelty, not a new root family**; NF-13 adjacency/weak proxy; NF-15 weak; NF-17 turnover/cost; NF-20 event calendar/timestamp; NF-21 weak/adj; NF-06-11 CBOE PC ratio infeasible; NF-20261106-03 VVIX VIX-complex adjacency; NF-20261106-21 RSP/SPY breadth (H115 executed REJECT); NF-20261106-23 XHB/XLU rates-channel adjacency; NF-20261106-24 XBI/XLV weak separation; NF-20261106-28 JNK/LQD credit adj (H94/H108); NF-20261106-30 VNQ/SPY rates/beta adj; NF-20261106-32 DBC/SPY ETF roll/flow confounds; NF-20261106-33 EWH/SPY capital-flow/risk-appetite confounds; NF-20261106-35 FXA/H103 adj; NF-20261106-36 dispersion adj to H117.
- Cycle 31 discovery candidates (NF-35 FXA, NF-36 dispersion) were scored/deferred but the full directive §4 Cycle 32 search (>=3 repo-new across >=3 categories + comprehensive reassessment) must be completed explicitly in the next session.

## Failed/blocked approaches (evidence)
- **H117 (executed, REJECT 4/8, `exp_2026-11-07T00-23-49-421603Z`):** fails Sharpe 0.918/PF 1.169/worst-regime -0.906/benchmark-p 1.0/IR -0.324; random-exposure-matched ablation outperforms (1.158/1.223). Artifact `.experiments/nf_runs/nf_20261106_34_sector_corr_regime/summary.json`. Do not re-run NF-34/H117 without a materially different, pre-registered mechanism/construction.
- **H116 (prior, REJECT 4/8):** ITA/SPY defense leadership; fails Sharpe/PF/worst-regime/benchmark-p/IR.
- **NF-11r remains NF-11 data-resolution path** (same root mechanism) — not a new root family if pursued.
- Session setup note: runtime deps (numpy/pandas/yfinance/pyarrow/loguru/scipy/scikit-learn/pytest/ruff) were not pre-installed in system Python 3.12; installed with `pip install --user` to execute/verify. Data came from existing `.cache/data` (92 parquet files) where available.
- No new `src/qtr` defects evidenced; no repeated identical approach retried.

## One precise next task
Perform **Cycle 32 discovery → pre-register H118** (and implement/execute only if decision-ready and feasible in-session without weakening gates):
1. Reconcile lineage to H117 (H85–H117 all rejected). Propose >=3 **repo-new** mechanism candidates spanning >=3 broad mechanism categories, checked against all root families H1–H117. Explicitly reassess NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, **NF-11 data-resolution path, SAME root mechanism — not a new root family**), NF-06-11 (infeasible), NF-20261106-03/21/23/24/28/30/32/33/35/36 with concrete evidence — no silent drops.
2. Score each 1–5 using directive weights (novelty 25%, plausibility 25%, data 20%, falsifiability 15%, execution 10%, independent empirical support 5%) with honest adjacency notes.
3. Pre-register the highest-expected-information **feasible** candidate as **H118** in `HYPOTHESIS_SPEC.md` and record candidates/decisions in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 32. Keep NF-ID as family-level lineage key. Specify smallest decisive test, data/splits/protected holdout, costs, gates, rejection/falsifiers, ablations.
4. If decision-ready with free/public data and no `src/qtr` change: implement `run_nf_*_*.py` + focused tests, run `ruff check/format --check` and focused pytest, execute, record verdict (OOS Val+Test only for selection/gates as pre-registered). **Do not** weaken gates, modify published/certified artifacts, use holdout for selection, or change `src/qtr` unless a genuine defect is evidenced (then run pinned 100% coverage suite).
5. If no feasible candidate: document blockers/evidence and leave a precise handoff; do not invent candidates or default to maintenance-only parameter work.
