# Next task (Cycle 179, 2026-11-17)

## What changed this session
Cycle 178 fixed a reproduced malformed-EDGAR filing-index defect in the public
insider API:
- `src/qtr/data/insider.py::filing_documents` now degrades a non-list
  `directory.item` to `[]` and skips any document `name` that is not a
  non-empty `str`. Previously a scalar/bool item raised `TypeError:
  'int' object is not iterable`, a single-mapping item silently yielded its
  keys, an `int` name became a non-string dict key that later crashed
  `_form4_document`, and a list/dict name raised `TypeError: unhashable type`.
- `tests/test_sec_insider.py::TestNonMappingEdgarJsonDocument` gained 9 tests
  (6 parametrized non-list-item payloads, 1 non-string-name test, 2 behavioural
  negative controls). `tests/test_sec_insider.py` is now 104 passed.
- Changes are **uncommitted in the working tree** at `4750ffd`; no commit was
  made this session.

## What was actually verified (own evidence, live tree)
- `python -m pytest -q tests/test_sec_insider.py -W error` -> **104 passed**;
  `insider.py` **100%** statements/branches from that file alone.
- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (342.78s) -> **4262 passed, 51 skipped, 0 failed**; `src/qtr` coverage **100.00%** (1652 stmts / 624 branches / 0 miss; `insider.py` 243/88).
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed**.
- `python -m ruff format --check src tests run_*.py scripts` -> **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED** (0.287s < 5s, 10.7MB, 13668 trades).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged, maintainer-gated; all assertions on `.github/workflows/gates.yml` content).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` -> **applies cleanly**.

## What remains unresolved
- The 7 `tests/test_gates_workflow.py` failures: fix is `patches/0001-gates-workflow-contract-fix.patch`. The agent **cannot** land it — the repo-scoped token has no `workflows` permission, and `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` after every session. This is a maintainer action.
- Reproduced next lead (not fixed this session): `Experiment.__init__` builds `self.base_dir / name / "artifacts"` from a caller-supplied experiment name without containment. Own evidence: `Experiment("../escaped", base_dir=<tmp>/base)` creates `<tmp>/escaped/artifacts` outside `base` (`is_relative_to(base)` is `False`). This is the sibling of the already-fixed `record_artifact` filename traversal and of `ExperimentTracker.log_artifact`/`log_dataframe`; `create_experiment(name)` is public. A fix should constrain the resolved experiment directory to `base_dir` (or reject escaping names) and add focused tests plus a behavioural negative control.
- No other evidenced defect remains in `src/qtr`; do not make speculative changes.

## One precise next task
**Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch` on `origin/main`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed). With it applied the whole pinned suite is **4262 passed, 51 skipped, 0 failed** at 100% coverage.
**Agent:** fix the reproduced `Experiment.__init__` experiment-name path containment above (smallest fail-closed guard, tests preserving 100% coverage, then pinned suite + ruff + perf gate). If you find a red gate on arrival, re-measure before trusting any handoff's pass/fail/coverage counts.

## Approaches already tried and why they should not be repeated
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — the failures are the maintainer-gated contract block; the fix is the workflow patch.
- Do not re-audit already-pinned defect classes without new evidence (cache normalization/dedup, config boundaries, EDGAR non-mapping/non-list/non-string-name handling, annualization/`bars_per_year`/`periods_per_year` guards, split/CV operand guards, engine cost/metric/position/impact guards, `CostModel` degenerate-input guards, `statistics.multiple_testing_correction(alpha=...)` guard, `_adv_for_symbol` degenerate-input guards).
- Do not use `--cov=<dotted.module>` (aborts collection with `ImportError`); use `--cov=qtr`.
- Do not trust a handoff's pass/fail/coverage counts — re-run the gates.