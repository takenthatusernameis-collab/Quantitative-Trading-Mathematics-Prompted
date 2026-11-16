# HANDOFF — current session (2026-11-16, Cycle 155)

## What changed (substantive, not annotation-only)

1. **`src/qtr/data/insider.py` — added `_as_mapping()` and threaded it through the
   EDGAR JSON parsing layer.** `_recent_filings` did
   `(submissions.get("filings") or {}).get("recent")`, which only degrades a
   *falsy* `filings` (`null`/blank) to `{}`; a **truthy non-mapping** document
   (a list `[1, 2, 3]`, a scalar, a string) was indexed verbatim and the first
   `.get("recent")` raised `AttributeError: 'list' object has no attribute
   'get'`. `filing_documents` had the same shape one layer over
   (`(index.get("directory") or {}).get("item")`). EDGAR serves untrusted external
   JSON, so this is reachable from the public API with no caller-side filtering
   -- a reproduced, runner-reachable defect.
   - **Fix:** `_as_mapping(value)` returns the value when it is a dict, otherwise
     `{}`. `_recent_filings` now does
     `_as_mapping(_as_mapping(submissions).get("filings")).get("recent")` and
     `filing_documents` does
     `_as_mapping(_as_mapping(index).get("directory")).get("item")`. A mapping is
     returned unchanged; a non-mapping degrades to `{}`, the same tuple the
     absent-block path already returns, so a malformed document is
     indistinguishable from an empty one. The non-mapping-item handling inside a
     *mapping* `directory` (the existing
     `test_filing_documents_skips_nameless_or_non_mapping_items`) is untouched.
     This is the same class as Cycle 154's config fix, one layer over in the EDGAR
     path rather than the startup config path.

2. **Tests:** `tests/test_sec_insider.py::TestNonMappingEdgarJsonDocument` (+15) --
   parametrized non-mapping `filings`/top-level/`recent` for `_recent_filings`,
   parametrized non-mapping `filings`/`directory`/top-level for the public
   `fetch_filings`/`filing_documents`, a mapping-`directory`-with-non-mapping-items
   control, and two behavioural negative controls reconstructing the pre-fix
   `(x or {}).get(...)` expressions and requiring them to raise.

## What was actually verified (own evidence, this session)

- **Repro before fix** (`/tmp/probe_insider.py`, `/tmp/repro2.py`): `fetch_filings`
  on `{"filings": [1, 2, 3]}` raised `AttributeError`; `filing_documents` on
  `{"directory": [1, 2, 3]}` raised `AttributeError`. After the fix both return an
  empty frame / empty dict.
- **Negative control:** `git stash push -- src/qtr/data/insider.py` ->
  `TestNonMappingEdgarJsonDocument` **25 failed, 9 passed** (the 9 are the
  already-`{}` cases and the mapping-directory control); `git stash pop` -> **72
  passed** on `tests/test_sec_insider.py`.
- **Full pinned suite** `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (441.48s) ->
  **4008 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%**
  (1577 stmts / 572 branches / 0 miss; `insider.py` 236/84).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  exclusively the maintainer-gated block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`).
- `python scripts/backtest_perf_regression_gate.py` -> **PERF GATE PASSED**
  (0.418s < 5s, 10.7MB peak, 13668 trades).
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed.**
  `python -m ruff format --check src tests run_*.py scripts` -> **336 files
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
  non-dict-file handling (Cycle 150), artifact/log path traversal, the
  `load_config`/`_set_nested` non-mapping-document handling (Cycle 154), and now
  the EDGAR `_recent_filings`/`filing_documents` non-mapping-document handling
  (Cycle 155).
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
`src/qtr` defect on a public path **not yet closed** -- fuzz/boundary probes at
smallest inputs (n=0/1/2, empty, duplicate labels, non-finite, corrupt/partial
state, untrusted names/paths, type-mismatched operands). If `src/qtr` changes,
re-run the full pinned suite (excluding the maintainer-gated workflow file),
`ruff check`/`ruff format --check`, and
`python scripts/backtest_perf_regression_gate.py`, with own evidence. Do **not**
re-audit the pinned families listed above, and do **not** invent a free-data
H183 or treat parameter/timeframe/universe variations as new families.
