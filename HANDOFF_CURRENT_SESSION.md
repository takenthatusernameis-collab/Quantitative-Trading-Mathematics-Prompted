# HANDOFF — current session (2026-11-16, Cycle 154)

## What changed (substantive, not annotation-only)

1. **`src/qtr/utils/config.py` — `load_config` now fails closed on a non-mapping
   YAML document.** The loader did `_CONFIG = yaml.safe_load(f) or {}`. That
   `or {}` only degrades the *falsy* documents (`null`, blank, `[]`, `0`, `""`)
   to `{}`; a **truthy non-mapping** document (a YAML list `[1, 2, 3]`, a scalar
   `5`, a string `hello`) was returned verbatim. `config.py` is the startup
   config layer every runner touches — `DataCache`, `ExperimentTracker`,
   `get_data_fetcher`, `get_tracker` all call `get_config()` -> `config_path` —
   and every consumer indexes the config by key (`config["validation"]`,
   `config.get(...)`), so the first construction raised
   `AttributeError: 'list' object has no attribute 'get'`. This is the same
   class as Cycle 150's `Experiment.load_metadata` non-dict-file defect, one
   layer over.
   - **Fix:** accept only a mapping document; otherwise fail closed to `{}` and
     log a `loguru` warning naming the file and the offending type. A `null`/
     blank document still yields `{}` silently (it is not a "wrong shape" the
     way a list is). Every valid mapping config is bit-identical.

2. **`src/qtr/utils/config.py` — `_set_nested` tolerates a non-mapping node on
   the path.** It did `d = d.setdefault(key, {})`, so a document like
   `data: 5` plus any `QTR_*` env override (`QTR_CACHE_DIR`, `QTR_LOG_LEVEL`,
   `QTR_MAX_CPU_HOURS`) returned the scalar and the next assignment raised
   `TypeError: 'int' object does not support item assignment`. `_set_nested` now
   replaces a non-mapping intermediate with a fresh dict (so the override still
   lands, matching `config_value`'s "a non-mapping node is a walk failure, not a
   value" contract) and ignores the override when the document itself is not a
   mapping (there is nowhere to attach it). A valid nested mapping is descended
   unchanged and the int/float/bool value parsing is untouched.

3. **Tests:** `tests/test_config.py` (+12) —
   `TestNonMappingConfigDocument`: parametrized list/int/str/bool/blank/null
   documents load as `{}`; a non-mapping document plus `QTR_CACHE_DIR` still
   applies the override; `DataCache()` constructs against a non-mapping
   `config.yaml`. `TestSetNestedNonMapping`: a non-mapping intermediate is
   replaced; a non-mapping document is ignored; an existing mapping is descended;
   an end-to-end env override over a `data: 5` document lands.

## What was actually verified (own evidence, this session)

- **Repro before fix** (`/tmp/probe6.py`, temp cwd + `config.yaml`): with
  `config.yaml` = `[1, 2, 3]`, `DataCache()` raised
  `AttributeError: 'list' object has no attribute 'get'`; with `data: 5` +
  `QTR_CACHE_DIR`, `load_config()` raised
  `TypeError: 'int' object does not support item assignment`. After the fix both
  return an empty/override-applied config and `DataCache()` constructs.
- **Negative control:** `git stash push -- src/qtr/utils/config.py` →
  `TestNonMappingConfigDocument` + `TestSetNestedNonMapping` **9 failed, 3
  passed** (the 3 are the two already-`{}` cases `""`/`null` and the
  existing-mapping descent); `git stash pop` → **55 passed** on
  `tests/test_config.py` (was 43 on `origin/main`; +12).
- **Focused:** `python -m pytest -q tests/test_config.py tests/test_data_fetcher.py tests/test_experiment_tracker.py tests/test_experiment_tracking.py tests/test_experiment_artifact_schema.py -W error` → **318 passed**.
- **`config.py` coverage from the config tests alone:** `--cov=qtr --cov-branch`
  → `config.py` **85 stmts / 40 branches / 0 miss (100%)**.
- **Full pinned suite** `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (448.24s) →
  **3974 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%**
  (1575 stmts / 572 branches / 0 miss; `config.py` 85/40).
  - Count reconciliation vs the Cycle 153 baseline (3962 passed / 51 skipped):
    +12 new tests = **3974 passed**, skipped unchanged. No other delta.
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged,
  exclusively the maintainer-gated block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED**
  (0.431s < 5s, 10.7MB peak, 13668 trades).
- `python -m ruff check src tests run_*.py scripts` → **All checks passed.**
  `python -m ruff format --check src tests run_*.py scripts` → **336 files
  already formatted.**

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow scope. Agent
   cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182
   executed/rejected; no honest H183 without new authorized data.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen.

## Approaches already tried / must not be repeated

- Do not re-audit the pinned families without new evidence: cache-hit and
  fresh-fetch index/column normalization+dedup (Cycles 144/153),
  `max_leverage`/`initial_capital`/`max_position_size` boundaries (Cycles
  147/148/152), duplicate index/column handling in engine/fetcher/tracker paths,
  `Experiment.record_artifact` DataFrame dedupe, `Experiment.load_metadata`
  non-dict-file handling (Cycle 150), artifact/log path traversal, and now the
  `load_config`/`_set_nested` non-mapping-document handling (Cycle 154).
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not make speculative `src/qtr` changes absent a reproduced, reachable
  defect.
- Do not use `--cov=<dotted.module>` (aborts collection with
  `ImportError: cannot load module more than once per process`); use
  `--cov=qtr`.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`.

**Agent path (new evidence only):** hunt a *reproduced, runner-reachable*
`src/qtr` defect on a public path **not yet closed** — fuzz/boundary probes at
smallest inputs (n=0/1/2, empty, duplicate labels, non-finite, corrupt/partial
state, untrusted names/paths, type-mismatched operands). If `src/qtr` changes,
re-run the full pinned suite (excluding the maintainer-gated workflow file),
`ruff check`/`ruff format --check`, and
`python scripts/backtest_perf_regression_gate.py`, with own evidence. Do **not**
re-audit the pinned families listed above, and do **not** invent a free-data
H183 or treat parameter/timeframe/universe variations as new families.