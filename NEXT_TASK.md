# Next task (2026-11-19, Cycle 217)

## What changed this session
- **Fixed a vacuous integrity guard.** `tests/test_experiments_jsonl_no_duplicate_artifact_names.py`
  (added in Cycle 216) built its duplicate-artifact-name check on `json.loads`. That parser keeps
  only the last value of a repeated key, so the test could never see the duplicate-key pattern its
  docstring claims to protect — it passed on every possible corpus. It now parses each raw line with
  an `object_pairs_hook` that records repeated keys at every nesting level, and a new unit test
  (`test_duplicate_key_detection_is_not_vacuous`) proves the detector fires on a crafted duplicate
  while plain `json.loads` collapses it.
- **Corrected the docstring's root-cause claim.** The current 11 `hash_mismatches` are *stale hash
  suffixes* on records whose artifact file was rewritten in place (8 momentum
  `param_grid_results.parquet` rows + 3 `summary.json` rows), **not** duplicate JSON keys: the raw
  corpus has 0 repeated keys (verified with `object_pairs_hook` over all 174 lines). The duplicate-key
  pattern is historical and already gone from the log; the guard now proves that and would catch a
  reintroduction.
- **Corrected a stale handoff number.** The previous `NEXT_TASK.md` said the artifact-schema pins had
  "distinct keys unchanged at 139"; the pinned value is **143**
  (`tests/test_experiment_artifact_schema.py:117`), and the test passes at 143.
- **Pinned the identity of the 11 `hash_mismatches`.** Added `PINNED_HASH_MISMATCHES` list to
  `tests/test_reproducibility_audit.py` with exact (experiment_id, experiment_name, artifact_name,
  expected_hash, actual_hash) tuples. The test now asserts the live mismatches match this list
  exactly (order-insensitive), preventing a fixed row from being silently replaced by a new mismatch.
- No change to `src/qtr`, gates, `.github/workflows/**`, artifacts, sidecars, hashes, verdicts, or
  frozen numbers.

## What was actually verified (own evidence, 2026-11-19)
- `python -m pytest -q tests/test_experiments_jsonl_no_duplicate_artifact_names.py` → **5 passed**.
- Adversarial end-to-end proof: copied the real `experiments.jsonl`, injected a duplicate key into
  record 1, pointed the module at the copy → guard **fired** (`found 1 experiment record(s) with
  duplicate JSON keys: line 1: ['dupe_key']`); the same copy is invisible to `json.loads`.
- `python -m ruff check src tests run_*.py scripts` → All checks passed; `ruff format --check` → already formatted.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.422s, limit 5s).
- `python scripts/verify_gates_workflow_patch.py` → **PATCH VERIFIED** (applies to live gates.yml, resolves all 7 violations).
- `python -m pytest -q tests/test_reproducibility_audit.py` → **7 passed** (identity pin verified).
- Full pinned suite `python -m pytest -q -W error --ignore=tests/test_gates_workflow.py` →
  **4453 passed, 51 skipped, 0 failed**. Pinned coverage run (`--cov=qtr --cov-branch`) → `src/qtr`
  **100.00%** (1692 stmts / 642 branches / 0 miss).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials, then
  `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed). Currently 7 failed, unchanged.
- **H1–H185 exhausted/rejected; H186 unassigned with no free-data source pending.** Per directive §6
  the free-data point-in-time strategy-family queue is exhausted. Do not pre-register an H-ID without
  a newly authorized data source.
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197, hash_mismatches=11,
  orphaned_files=528, missing_meta_files=0. The 11 stale-hash rows could be remediated only by a
  deliberate, reviewable corpus update, which is out of scope for an agent session.

## One precise next task
**Maintainer:** `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am
"fix(ci): satisfy gates workflow contract" && git push origin main`, then
`python scripts/verify_gates_workflow_patch.py` (expect `CONTRACT SATISFIED`) and
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).

**Agent:** no free-data research task remains. The frozen record has been strengthened by pinning
the identity of the 11 `hash_mismatches`. Future sessions should verify the baseline
(`ruff check/format`, focused tests, full suite, `python scripts/backtest_perf_regression_gate.py`)
and leave the handoff.

## Approaches already tried and why they should not be repeated
- Do not rebuild a corpus guard on `json.loads` — it collapses duplicate keys; use
  `object_pairs_hook` (this session's fix).
- Do not re-run H184/H185 or any parameter/universe/window variant; do not re-probe
  CHRIS/CME/Yahoo/stooq/LME/DCE; do not re-declare probed FRED/binance/exchange sources as blocked.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` or any gate.
- Do not trust handoff counts (including the ones in this file) — re-run the checks.

(End of file - total 65 lines)