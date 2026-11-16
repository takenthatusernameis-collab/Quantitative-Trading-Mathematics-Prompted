# Handoff — Current Session: H184 target_vol guard; suite green except maintainer-gated workflow

## What changed

Closed a reproduced, runner-reachable defect in the baseline signal layer
(`src/qtr/strategies/baselines.py`):

- `_vol_scale(vol, target_vol)` now validates `target_vol` with the same
  finite/non-negative contract the module already applies to
  `max_position_size`. A negative `target_vol` used to make the multiplier
  negative and **invert the sign of every position**
  (`_vol_scale(0.15, -0.15) == -1.0`), turning a trend-following book into a
  mean-reversion book (measured: correlation -1.0 between the `+0.15` and
  `-0.15` books over a 300-bar panel); a non-finite one made the multiplier
  `inf` (the `min(inf, 2.0)` cap does not fire). Both fail closed to `1.0`
  (the no-scaling boundary); `target_vol == 0.0` is a real, measured boundary
  and returns `0.0` (no risk to take -> no exposure).
- `time_series_momentum_signals` and `vol_scaled_tsmom_signals` now gate on
  `_is_finite_non_negative(target_vol)` alongside `max_position_size`, so the
  two call sites agree on this input class instead of one inverting and the
  other returning zero.
- +10 tests in `tests/test_baselines_extra.py` (78 -> 88 total), covering the
  `_vol_scale` operand contract, the per-parametrize fail-closed paths for both
  TSMOM variants, the "negative target_vol does not invert" regression test,
  and bit-identical behaviour on valid input.

`src/qtr` coverage remains **100%** (1616 stmts / 600 branches / 0 miss).

## Actually verified (this session, own evidence)

- Reproduced the defect before fixing: `_vol_scale(0.15, -0.15) == -1.0`,
  `_vol_scale(0.15, inf) == 2.0`, and both TSMOM variants produced non-zero
  books on `target_vol=-0.15` / `inf`.
- `python -m pytest -q tests/test_baselines_extra.py` -> **88 passed** (was 78).
- Full pinned suite
  `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
  -> **4210 passed, 51 skipped**, `src/qtr` coverage **100.00%**
  (1616 stmts, 600 branches, 0 missing). No regression.
- `python -m ruff check src tests run_*.py scripts` -> All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` -> 336 files
  already formatted (applied the one reformat the new code triggered).
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED**
  (0.440s, limit 5s).
- `tests/test_gates_workflow.py` -> **7 failed** (unchanged, maintainer-gated;
  `patches/0001-gates-workflow-contract-fix.patch` still applies cleanly but
  cannot be pushed by the agent).

## Unresolved / pre-existing (unchanged)

- Maintainer-only workflow patch for `.github/workflows/gates.yml` — the only
  red test file, by design of the AGENTS.md block.
- H1–H182 exhausted under free/public PIT data; no honest H183 without new
  authorized data (per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 96/116/140).
- Reproducibility backlog baseline-frozen at `missing_files=197`,
  `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`.

## Failed approaches / do not blindly repeat

- Do not trust a handoff's failure list without re-running the gate.
- Do not weaken `tests/test_gates_workflow.py`, frozen contracts, coverage
  gates, or published/frozen artifacts/verdicts/thresholds/frozen numbers.
- Do not edit `.github/workflows/**` (restored from `origin/main` after every
  session; the repo-scoped token has no `workflows` permission).
- Do not invent a free-data H183 or treat parameter/timeframe/universe/close-
  substitute variations as new mechanism families.
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError`);
  use `--cov=qtr`.

## Next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent alternative (only with new evidence):** if a new concrete, reproduced,
runner-reachable defect appears in `src/qtr`, runners, or corpus metadata,
implement the smallest reversible fix, add/adjust tests preserving 100%
`src/qtr` coverage, and verify with the full pinned suite, ruff check/format,
and the perf gate (own evidence required).

**Constraints:** no gate weakening; no modification of published/frozen
artifacts, verdicts, thresholds, or frozen numbers except deliberate authorized
corpus/baseline updates; no workflow commit from agent.

**Working-tree note:** `src/qtr/strategies/baselines.py` and
`tests/test_baselines_extra.py` are modified but NOT committed (no explicit
commit request). Commit them if this session's work is to be persisted before
the next session.

(End of file)