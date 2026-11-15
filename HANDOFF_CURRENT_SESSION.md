# HANDOFF — current session (2026-11-15, Cycle 127)

## What changed

**Bounded defect fix in experiment tracking: tolerate malformed/incomplete JSONL log lines.**

The prior handoff suggested auditing `qtr.tracking.experiment` for malformed `experiments.jsonl` (partial/interleaved append) only if reachability was real. `experiments.jsonl` is append-only in this codebase; a mid-write crash, concurrent append, or manual truncation is a realistic failure mode. I reproduced that the tracker treated such corruption as fatal for the entire log:

- **`load_experiment` / `list_experiments` crashed on a bad line.** A non-JSON line raised `json.decoder.JSONDecodeError`; a JSON record missing required `ExperimentMetadata` keys raised `TypeError` (`ExperimentMetadata.__init__` missing fields); a JSON record with `metadata` but missing `name`/`timestamp` caused `KeyError` in `list_experiments`. After the bad line, later valid records were unreadable (e.g. `e2` appended after corruption could not be loaded/listed).
- **Fix:** `src/qtr/tracking/experiment.py` — both methods now skip empty, malformed, or incomplete lines (`try/except Exception: continue`) while still returning valid records before/after the corruption. Uses `record.get(...)` for optional/result fields; `status` defaults to `"unknown"` on list if absent. Valid-path behavior is unchanged.
- **Tests:** `tests/test_experiment_tracker.py` — added `_good_record` helper and `test_load_and_list_skip_malformed_and_incomplete_lines` (pins: bad JSON + incomplete record do not prevent loading/listing valid records around them). +1 test.

No gate, artifact, sidecar, hash, frozen number, or workflow change.

## What was actually verified (own evidence)

- Repro (before fix, isolated script with `PYTHONPATH=src`): malformed JSONL and incomplete-record cases raised `JSONDecodeError` / `TypeError` / `KeyError` as described.
- Repro (after fix, same shape): `load_experiment('e2')` returned `e2` and `list_experiments()` returned `['e2','e1']` despite a bad JSON line and an incomplete record in between.
- `PYTHONPATH=src python -m pytest -q tests/test_experiment_tracker.py tests/test_experiment_artifact_schema.py tests/test_public_api_contract.py` → **168 passed**.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (358.28s) → **3825 passed, 48 skipped, coverage 100.00%**. The +1 vs. prior 3824 non-workflow count is the new regression test; the 48 skips are pre-existing. `src/qtr/tracking/experiment.py` remained 100% covered.
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged; exclusively maintainer-gated workflow-contract block).
- `python -m ruff check src/qtr/tracking/experiment.py tests/test_experiment_tracker.py` → All checks passed.
- `python -m ruff format --check src/qtr/tracking/experiment.py tests/test_experiment_tracker.py` → 2 files already formatted.

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated; 7 `tests/test_gates_workflow.py` tests red until maintainer applies `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials. Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182 executed/rejected; no honest free-data H183 is pre-registrable without new authorized data.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where contract/citation constraints apply.

## Approaches already failed / must not be repeated

- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter coverage/frozen-contract gates.
- Do not mass-edit runners/tests/gates or frozen artifacts to force green.
- Do not make speculative `src/qtr` changes absent an evidenced defect/reachability.
- Do not re-open closed defect classes without new evidence (duplicate index/column guards, statistics shape guards, H182 fetch KeyError, etc.).
- **`qtr.utils.config.load_config` malformed YAML** raises `yaml.parser.ParserError` (fail-fast). This is arguably correct for config parsing and was not changed; do not "fix" it into silent fallback without explicit product decision/evidence.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push `patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.

**Agent alternative (if another evidenced defect is wanted):** audit the remaining `qtr.tracking` public surface for crash-on-corrupt-persistence reachable from realistic use — e.g. `Experiment.load_metadata()` already returns `{}` on corrupt JSON, but `Experiment.log_metadata/log_params/log_results` do `load_metadata()` then overwrite the file without guarding a mid-write; confirm a concrete failure mode (partial write leaving corrupt JSON is self-healing on next read, but concurrent interleaving is not exercised here) before changing behavior. Do not manufacture a fix without reproduced evidence and keep 100% `src/qtr` coverage.

**Constraints:** preserve gates/contracts/100% coverage; do not alter published/frozen artifacts or thresholds except a deliberate authorized corpus/baseline update; no workflow commit from agent.