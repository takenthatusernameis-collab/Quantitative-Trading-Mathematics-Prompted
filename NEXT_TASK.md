# Session complete (2026-11-21, Cycle 239 — code hardening: compare_to_benchmark 2-D strategy)

## State

H1–H190 exhausted/rejected or data-blocked (unchanged; see `AGENTS.md` and
`NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 215–235). Free-data point-in-time family
discovery remains exhausted; do not re-declare any H-ID data-blocked without
naming the probed source, and do not treat parameter/timeframe/universe/market
variants of H1–H190 as new families.

This cycle made a **real code fix + tests** (not a doc-sync): it closed a
degenerate-shape crash in `qtr.validation.statistics.compare_to_benchmark` that
was reachable from the public API. No strategy family was added; H1–H190
exhaustion is unchanged.

## What changed (Cycle 239)

`src/qtr/validation/statistics.py::compare_to_benchmark` reduced a multi-symbol
**benchmark** (DataFrame or 2-D ndarray) to its equal-weighted row-mean series
but did NOT reduce the **strategy** side. A 2-D `strategy_returns` therefore
broadcast against the 1-D benchmark in `excess = strat - bench`;
`stats.ttest_1samp(excess, 0)` then returned an ARRAY `t_stat`, and
`if t_stat > 0` raised an opaque
`ValueError: The truth value of an array with more than one element is ambiguous`
out of a function every caller treats as returning a dict.

Fix: apply the same equal-weighted (mean across symbols, axis 1) reduction to
`strategy_returns` that the benchmark side already carried, symmetric with it.
A 1-D ndarray or `pd.Series` strategy is returned unchanged (the `ndim > 1` test
is False), so every valid 1-D input is **bit-identical** to before. This is the
same degenerate-shape class `regime_analysis` (non-1-D `returns`) and
`parameter_sensitivity` (non-2-D `returns`) already fail closed on.

Tests (`tests/test_statistics.py::TestCompareToBenchmark`): 3 new tests —
`test_dataframe_strategy_reduced_to_equal_weighted`,
`test_2d_ndarray_strategy_reduced`, `test_1d_strategy_is_unchanged_by_the_reduction`
— each asserting the result equals the row-mean comparison (and the 1-D path is
unchanged). No existing test passed a 2-D strategy (it previously crashed), so no
frozen number/contract moved.

Scope: `src/qtr/validation/statistics.py` + `tests/test_statistics.py` only. No
runner, artifact, sidecar, hash, gate, frozen number, or workflow was modified.
No `NEW_FAMILY_RESEARCH_REGISTER.md` / `HYPOTHESIS_SPEC.md` / `AGENTS.md` H-range
claim was touched (this is a hardening fix, not a new family).

## Verified evidence (this session)

- `python -m pytest -q` → **4543 passed / 51 skipped / 7 failed** (baseline was
  4540/51/7; +3 = the new tests). All 7 failures are `tests/test_gates_workflow.py`,
  unchanged and maintainer-gated by design (patch
  `patches/0001-gates-workflow-contract-fix.patch`).
- `PYTHONPATH=src python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing`
  → **100.00% coverage** (`src/qtr/validation/statistics.py` 378 stmts / 158
  branches / 0 miss; TOTAL 1697 stmts / 646 branches / 0 miss). The new branch is
  fully covered by the 3 new tests.
- `python -m ruff check src tests run_*.py scripts` → clean.
- `python -m ruff format --check src tests run_*.py scripts` → 360 files formatted.
- Adversarial probe of the public API under `-W error` (statistics, baselines,
  engine, cost model): no remaining crash / non-finite / inconsistency found.
  Supplementary probe confirms 2-D-strategy + 1-D-bench, DataFrame strategy,
  2-D + 2-D, 1-D list, and 2-D-with-NaN all return cleanly, and that a 1-D
  `pd.Series` and a 1-D `ndarray` give bit-identical results.
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → applies
  cleanly (unchanged).
- Change set is exactly the two files above (no stray edits).

## One precise next task (for next session)

**None blocking.** The only remaining actionable items are unchanged from prior
cycles:

1. Maintainer-applied workflow contract fix
   (`patches/0001-gates-workflow-contract-fix.patch`) to make
   `tests/test_gates_workflow.py` green — **agent-unreachable** (`.github/workflows/**`
   is maintainer-managed, excluded from staging by
   `.github/scripts/kilo-controller.sh`, restored from `origin/main` after every
   session, and the repo-scoped GitHub App token has no `workflows` permission).
   Patch verified to `git apply --check` cleanly; capture as apply-ready and record
   the maintainer action here.

2. Optional, authorization-gated artifact cleanup from
   `REPRODUCIBILITY_AUDIT_REPORT.md` §2: drop 8 superseded duplicate
   `param_grid_results` keys + 3 stale `summary` keys from `experiments.jsonl`.
   **Do not overwrite artifacts** without authorization.

Optional further hardening (same pattern as this cycle, evidence-first): probe a
public-API function for a degenerate-input class not yet guarded, reproduce the
smallest failure under `-W error`, then fix with a minimal fail-closed/reduction
guard + a test that keeps `src/qtr` at 100% branch coverage. Do not invent a
guard with no reproduced failure.

## Approaches already tried / do not repeat

- Do not re-declare any H-ID family as data-blocked without naming the probed source.
- Do not treat parameter/timeframe/universe/market variants of H1–H190 as new families.
- Do not modify `.github/workflows/**` (maintainer-managed; agent-unreachable).
- Do not re-run H190 or any exhausted family as a variant; the full-window
  pre-registered runs are the record.
- Do not reintroduce a hard dependency on `.cache/xbrl/**` in tests: that cache is
  git-ignored and absent on fresh checkouts/CI. Tests must be hermetic (synthetic
  fixtures), as H187/H188 now are.
- Do not mass-edit runners/tests/gates to force the suite green; frozen-contract
  drifts need per-contract evidence and authorization.
- Do not manufacture a hardening guard without first reproducing a concrete failure
  under `-W error`; this cycle's fix was driven by a reproduced
  `ValueError` from a 2-D strategy input, not by speculation.

(End of file - total 110 lines)