# HANDOFF — current session (2026-11-16, Cycle 150)

## What changed

1. **`src/qtr/tracking/experiment.py` — `Experiment.load_metadata` now fails closed on a non-dict metadata file.**
   The previous handler only caught a `json.load` *parse* failure, so a metadata file
   that parsed as valid JSON but was not a mapping (a list, a string, a number, a
   boolean, or `null` — written by an older writer, a hand-edited file, or a
   concurrent process) was returned verbatim. Every writer then mutated it in place
   (`meta.update(...)`, `meta["params"] = ...`, `meta["results"] = ...`) and crashed
   out of a constructor every caller treats as infallible:
   - `log_metadata` after a `[1, 2, 3]` file → `AttributeError: 'list' object has no
     attribute 'update'`
   - `log_params` / `log_results` after a `"just a string"` / `5` file →
     `TypeError: 'str'/'int' object does not support item assignment`
   The fix adds an `isinstance(record, dict)` guard and returns the empty dict — the
   same tuple the parse-failure path returns — so a corrupted metadata directory is
   recoverable without deleting it. A file that is already a mapping is returned
   bit-identically.

2. **Tests:** `tests/test_experiment_tracking.py` (+6):
   - `test_load_metadata_non_dict_json_fails_closed` (parametrized over array, string,
     integer, float, boolean, null)
   - `test_log_metadata_recovers_from_a_non_dict_metadata_file`
   - `test_log_params_and_log_results_also_recover_from_non_dict_files`
   - `test_load_metadata_pre_fix_non_dict_load_propagates` (behavioural negative
     control)

No gate, artifact, sidecar, hash, frozen-number, or workflow change.

## What was actually verified (own evidence)

- **Before-fix repro:** a metadata file holding `json.dumps([1, 2, 3])` returned the
  list from `load_metadata()` and the next `log_metadata` call raised
  `AttributeError: 'list' object has no attribute 'update'`; a file holding
  `json.dumps("just a string")` crashed `log_params` with `TypeError: 'str' object
  does not support item assignment`; a file holding `json.dumps(5)` crashed
  `log_results` with `TypeError: 'int' object does not support item assignment`.
  After the fix all three writers succeed and the file reads back as a valid
  mapping.
- Focused `python -m pytest -q tests/test_experiment_tracking.py -W error` →
  **28 passed**.
- Full pinned suite
  `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`
  (350.87s) → **3950 passed, 48 skipped, 0 failed**, `src/qtr` coverage
  **100.00%** (1547 stmts / 556 branches / 0 miss; `tracking/experiment.py` 222/49).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged,
  maintainer-gated; fix is `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` → **PASSED** (0.304s < 5s, 13668
  trades).
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**;
  `python -m ruff format --check src tests run_*.py scripts` → **336 files already
  formatted**.

## What remains unresolved

1. **Maintainer-only CI contract:** apply
   `patches/0001-gates-workflow-contract-fix.patch` with workflow scope; the agent
   cannot persist `.github/workflows/**` changes.
2. **Frozen research/reproducibility baselines:** H1–H182 exhausted/rejected under
   free/public PIT data, H183 unassigned; reproducibility counts remain
   `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`,
   `missing_meta_files=0`.
3. **No new free-data H183** without genuinely new authorized data; do not treat
   parameter/timeframe/universe/close-substitute variations as new mechanism
   families.

## Approaches already tried / must not be repeat

- Do not re-probe the `Experiment` metadata writers for a non-dict file; it is now
  closed and pinned.
- Do not re-run the same suite as "work": this session ran focused tests and the
  full pinned suite with own evidence.
- Do not make speculative `src/qtr` changes absent a reproduced, runner-reachable
  defect.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter
  coverage/frozen-contract gates or published/frozen artifacts/verdicts/thresholds/
  frozen numbers.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative (only with new evidence):** continue hunting a *reproduced*,
runner-reachable defect in `src/qtr` — use executable fuzzing/property probes across
module boundaries and smallest input boundaries (n=0/1/2, empty, duplicate labels,
non-finite, corrupt/partial state) on public paths not yet closed. Do not re-run the
same suite as "work". If `src/qtr` changes, verify with
`python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py`,
`python -m ruff check src tests run_*.py scripts`,
`python -m ruff format --check src tests run_*.py scripts`, and
`python scripts/backtest_perf_regression_gate.py`.

**Constraints:** no gate weakening; no modification of published/frozen artifacts,
verdicts, thresholds, or frozen numbers except deliberate authorized corpus/baseline
updates; no workflow commit from agent.