# HANDOFF — current session (2026-11-15, Cycle 142)

## What changed (substantive, not annotation-only)

1. **`src/qtr/utils/config.py` — new `config_value()` + `config_path()`.**
   `_apply_env_overrides` writes **nested** mappings (`QTR_CACHE_DIR` ->
   `{"data": {"cache_dir": ...}}`, pinned by
   `tests/test_config.py::test_env_override_cache_dir_string`), but the two
   consumers read the *literal flat key*:
   `DataCache.__init__` used `get_config().get("data.cache_dir", ".cache/data")`
   and `ExperimentTracker.__init__` used `get_config().get("tracking.log_dir",
   ".experiments")`. A flat key can only match a hand-written `data.cache_dir:`
   line, so the nested document the loader itself produces was silently
   discarded: the configured directory (from `config.yaml` **or** from
   `QTR_CACHE_DIR`) never took effect and the cache/log always landed in
   `.cache/data` / `.experiments`.
   - `config_value(config, dotted_key, default)`: nested walk first, literal flat
     key as fallback, `default` otherwise. A non-mapping intermediate node is a
     walk failure; a present `None` is a value (the caller decides).
   - `config_path(config, dotted_key, default)`: coerces to `Path`; fails closed
     to the default for bool / null / sequence / mapping / empty-string values;
     numeric values go through `str` because `_set_nested` parses
     `QTR_CACHE_DIR=10` to the int `10` (the caller's literal text is the
     intended path component).
2. **`src/qtr/data/fetcher.py` / `src/qtr/tracking/experiment.py`** — `DataCache`
   and `ExperimentTracker` now resolve their directory through `config_path`.
   **The default path is unchanged**, so a config-less tree is bit-identical.
3. **`src/qtr/utils/__init__.py`** — both names exported (`qtr.utils.__all__`
   must equal the module's public API; `tests/test_public_api_contract.py`
   enforces it and passes).
4. **Tests:** `tests/test_config.py` `TestConfigValue` (10) + `TestConfigPath`
   (13); `tests/test_data_fetcher.py` `TestDataCacheConfiguredDirectory` (5,
   incl. a behavioural negative control); `tests/test_experiment_tracker.py`
   `TestTrackerConfiguredLogDirectory` (4, incl. a behavioural negative
   control). **+32 tests.**
5. **Docs:** `HANDOFF.md` banner, `NEXT_TASK.md` Cycle 142 section, this file.

**No gate, artifact, sidecar, hash, frozen-number, or workflow change.**

## What was actually verified (own evidence, this session)

- **Reproduced before fixing:** a temp cwd with `config.yaml` =
  `data: {cache_dir: /tmp/nested-cache}` + `tracking: {log_dir:
  /tmp/nested-exp}` loads as `{'data': {'cache_dir': '/tmp/nested-cache'}, ...}`,
  yet `DataCache().cache_dir == .cache/data` and
  `ExperimentTracker().log_dir == .experiments`.
- **Negative control:** `git stash push -- src/qtr/data/fetcher.py
  src/qtr/tracking/experiment.py` -> exactly the 3 nested/env cases fail with
  `AssertionError: assert PosixPath('.cache/data') == PosixPath('/tmp/nested-cache')`
  (and `.experiments` for the tracker); `git stash pop`, **150 passed** on the
  three touched suites.
- **Committed probe now passes:** `python repro_cache_dir.py` (added at
  `1ede756`, when the override was silently dropped) prints
  `cfg data.cache_dir = 10` then **`cache_dir = 10`**; before this fix it
  printed `cache_dir = .cache/data`.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (643.87s) ->
  **3907 passed, 51 skipped, 0 failed**, `src/qtr` coverage **100.00%**
  (1523 stmts / 544 branches / 0 miss; `config.py` 73/32, `fetcher.py` 223/84,
  `experiment.py` 217/46, all 100%). 3907 = 3869 (Cycle 139) + 6 (the prior
  uncommitted-handoff commit `287de3a`) + 32 (this session).
- `python -m pytest -q tests/test_gates_workflow.py` -> **7 failed** (unchanged,
  exclusively the maintainer-gated block; fix is
  `patches/0001-gates-workflow-contract-fix.patch`, still `git apply --check`-clean).
- `python scripts/backtest_perf_regression_gate.py` -> **PASSED** (0.851s < 5s,
  10.7MB peak, 13668 trades).
- `python -m ruff check src tests run_*.py scripts` -> **All checks passed.**
  `python -m ruff format --check src tests run_*.py scripts` -> **336 files
  already formatted.**
- **Prior commit certified:** `287de3a` (CostModel negative-operand fail-closed,
  6 new tests) had landed without any handoff entry; the full pinned suite above
  is the first run that covers it.

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow scope. Agent
   cannot land `.github/workflows/**`. **Verified apply-ready.**
2. **Research queue exhausted under free/public PIT data:** H1–H182
   executed/rejected; H183 unassigned. Cycle 140 (FRED) confirmed the corrected
   data does not yield a new family. No materially different free source has
   been searched since.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen.
4. **Deliberately not fixed:** `logging.level` and `compute.max_cpu_hours` are
   written by the env-override table but read by nobody in `src/qtr`; wiring
   them is a behaviour change, out of scope.

## Approaches already tried / must not be repeated

- **Do not "fix" this by making `_set_nested` write flat keys.** `tests/test_config.py`
  pins the nested env-override shape, and the nested document is the loader's
  canonical output; the two consumers were the outliers.
- **Do not use `--cov=<dotted.module>`** (e.g. `--cov=qtr.utils.config`): it
  aborts collection with `ImportError: cannot load module more than once per
  process` in this environment (python 3.14 / numpy 2.5.4 / coverage 7.17.3,
  independent of `-W error`). Use `--cov=qtr`, as `pyproject.toml` specifies.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or
  alter coverage/frozen-contract gates.
- Do not make speculative `src/qtr` changes absent a reproduced, reachable
  defect. The defect hunt is **not** exhausted: `287de3a` and this cycle both
  landed after a handoff claimed no agent-actionable defect remained.
- Do not repeat the yfinance-only "data-blocked" classification — run
  `scripts/probe_fred_availability.py` (and probe other free sources) first.
- Do not invent a free-data H183 or treat parameter/timeframe/universe
  variations as new mechanism families.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on
`origin/main`. Patch verified apply-ready this session.

**Agent path:** run one more reproduced-defect cycle. First verify (do not
assume) the cached-read schema inconsistency: `DataCache.get` returns any stored
parquet as-is and `_fetch_yahoo_panel` skips the "missing column" handling the
fresh path has; measured, a cache entry without `close` yields a zero-exposure
0.0 book from `run_backtest` (no crash) and is silently dropped by
`run_baseline.py:126`. That is a fail-soft inconsistency to decide on, not a
proven defect. Any `src/qtr` change must preserve 100% coverage and pass
`ruff`/the pinned suite.