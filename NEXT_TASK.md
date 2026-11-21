# Session complete (2026-11-21, Cycle 245 — H191 recorded + companion tests added)

## What changed (this session)

- **H191 (NF-20261121-01, equity value / book-to-price & cash-flow-yield) is now fully recorded.**
  The runner and artifact were committed at 14:42 (`3a8fba9`) but never documented. This session:
  - Added `tests/test_nf_20261121_01_equity_value.py` (22 tests: constants match pre-registration,
    universe = S&P 100 minus XOM/BKNG = 98, bounded 16-cell grid, `value_observations` column/filed
    rules + tag fallbacks + non-10-K exclusion, `build_value_panel` shape/values **and a regression
    guard against the transpose bug** fixed in `3a8fba9`, `cross_sectional_z` winsorization,
    value-direction signal weights (long-high / short-low), hysteresis + exit, insufficient-active
    zeroing, walk-forward sentinel/finite, perturbation 4-point, collinearity bounds, and
    summary/grid artifact assertions).
  - Updated `tests/test_experiment_artifact_schema.py` inventory pins for the new artifact
    directory: `EXPECTED_TOTAL_DIRS 116→117`, `EXPECTED_SUMMARY_COUNT 108→109`,
    `EXPECTED_DISTINCT_KEYS 150→151` (new key `train_input_collinearity_bp_vs_cfy`); added the
    Cycle 245 documentation comment. `EXPECTED_KEYS_GE_50_PCT` / `EXPECTED_KEYS_GE_80_PCT` /
    `EXPECTED_CACHE_ONLY_DIRS` unchanged (recomputed).
  - Recorded H191 (REAL REJECT 4/8) in `NEW_FAMILY_RESEARCH_REGISTER.md` (new Cycle 245 section
    with lineage map, mechanism separation from H187/H188/H189, data availability, execution
    outcome, and durable family-status consequence).

## H191 result (from `.experiments/nf_runs/nf_20261121_01_equity_value_20261121_144056/summary.json`)

- Selected `feature=book_to_price, entry_z=0.5, exit_z=0.0, k=10, vol_target=0.15` (train WF 0.354;
  in-train 0.326).
- OOS Val+Test (1272 periods, 1430 trades): Sharpe **0.853**, PF **1.159**, maxDD **−13.11%**,
  worst rolling-252 Sharpe **−0.683**, total return 0.761.
- Gates PASS (4): trades, maxDD, WF stability (2.612), OAT perturbation min ratio (1.129).
  Gates FAIL (4): Sharpe ≥ 1.0 (0.853), PF ≥ 1.3 (1.159), worst-regime ≥ 0.3 (−0.683),
  benchmark p ≤ 0.05 with IR ≥ 0 (p 0.756 two-sided, IR −0.138).
- Passive equal-weight long book OOS Sharpe 1.075 (total return 0.982) dominates; excess return
  −2.21%/yr; random ranking −1.018 and inverse signal −0.862 confirm the value *sign* is right but
  the spread is below the gate after 5 bps costs. **Verdict: REJECT (4/8).**

## What was actually verified (this session)

- `python -m pytest tests/test_nf_20261121_01_equity_value.py` → **22 passed**.
- `python -m pytest tests/test_experiment_artifact_schema.py` → **114 passed** (inventory pins updated).
- Sibling NF runners unchanged: `test_nf_20261120_01/02/04` → pass.
- Focused regression set (`test_tsmom_runner_long_only`, `test_runner_causality_inventory`,
  `test_runner_metric_agreement`, `test_h29_lookahead_sweep`, `test_h54_non_metrics_block_disclosure`,
  `test_reproducibility_audit`, `test_experiments_jsonl_no_duplicate_artifact_names`,
  `test_momentum_runner_single_grid_write`, `test_experiment_artifact_schema`,
  `test_nf_20261121_01_equity_value`) → **588 passed**.
- **Full suite (measured this session, `python -m pytest -q`): 4600 passed / 48 skipped / 7 failed**
  — the 7 failures are exactly the pre-existing maintainer-gated `tests/test_gates_workflow.py`;
  zero new failures from this session's changes. (Previous baseline 4572/51/7 at `4b1df88`; the
  +28/−3 shift is the new 22 H191 tests plus artifact-present tests that previously skipped.)
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **363 files already formatted**
  (was 362; +1 new test file).
- `src/qtr` unchanged → coverage unaffected (no source edit).

## Remaining unresolved

- **`tests/test_gates_workflow.py` — 7 failures** because `.github/workflows/gates.yml` is unpatched
  (unchanged from Cycle 245 handoff). The test pins: `scripts/**` in both `push`/`pull_request` path
  filters, `scripts` in both ruff targets, `python -m pip install -e . --no-deps` in both jobs, and
  `python scripts/backtest_perf_regression_gate.py` in `research_gates`.
- Fix = maintainer applies `patches/0001-gates-workflow-contract-fix.patch` (`.github/workflows/gates.yml`),
  commits, pushes. **Agent-unreachable**: `.github/workflows/**` is restored from `origin/main` after
  every session (`.github/scripts/kilo-controller.sh`) and the repo-scoped GitHub App token has no
  `workflows` permission, so an in-tree edit does not persist.
- Evidence the fix works: patch was applied in a clean `/tmp` checkout and
  `pytest tests/test_gates_workflow.py` → 7 passed (re-verified Cycles 106, 121, 235, 245).

## Approaches already failed / do not repeat

- In-tree edit of `.github/workflows/gates.yml`: does not persist (restored from origin/main; token
  lacks workflows permission). Do not retry.
- Mass-editing runners/tests/gates to force the suite green; frozen-contract drifts need
  per-contract evidence + authorization (per AGENTS.md / HANDOFF_CURRENT.md).
- Do not re-run H190 or H191 (or any exhausted family) as a parameter/universe/window variant; the
  full-window pre-registered runs are the record.
- Do not reintroduce a hard dependency on `.cache/xbrl/**` in tests: that cache is git-ignored and
  absent on fresh checkouts/CI. Tests must be hermetic (synthetic fixtures), as the new H191 test is.

## One precise next task (next session)

**Maintainer action only**: apply the gates workflow contract fix so `test_gates_workflow.py`
goes 7/7 green:
```
git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main
```
Then record the action here. No agent-executable code task remains; H191 is fully executed, tested
and recorded.

(End of file - total 72 lines)