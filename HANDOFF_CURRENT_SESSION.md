# HANDOFF — current session (2026-11-14, Cycle 121)

## What changed

**No source, test, gate, artifact, or frozen-number change.** The previous session's
handoff claimed H182 was a "lineage gap" (173 records, 0 insider records). That claim
was **false**, and this session's only durable output is correcting it in two
documentation files so the next agent does not re-derive a wrong finding.

- **`REPRODUCIBILITY_AUDIT_REPORT.md`** — corrected the stale §H182 lineage
  reconciliation block. It now states the corpus is **174** records and H182 is
  present (record 174, `exp_2026-11-14T11-39-15Z`, REJECT, 3 artifacts on disk under
  `.experiments/nf_runs/`). All "173 experiments" prose updated to 174. The four
  baseline counts (`missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`,
  `missing_meta_files=0`) are unchanged; a re-verification banner was appended.
- **`HANDOFF.md`** — appended a Cycle 121 banner recording the correction and the
  verification evidence.

## What was actually verified (own evidence)

- Corpus count: `wc -l .experiments/experiments.jsonl` → **174** records.
- H182 record (last line) parses; `metadata.config` and `metadata.data_sources` are
  populated (not `unknown`); `status.verdict` = `REJECT`, `gates_passed=3/8`.
- H182 artifacts exist on disk
  (`.experiments/nf_runs/nf_20261110_08_insider_signal_20261114_113912/`:
  `summary.json`, `corpus_info.json`, `grid.csv`) and their SHA-256 16-char prefixes
  **match** the artifact names exactly:
  `summary_json_6b4eed5db62decae`, `corpus_info_json_d19f66a79f5b1f33`,
  `grid_csv_9141c6d1a1d43e5e`.
- All 3 H182 `.meta.json` sidecars exist under `.experiments/` and re-derive from
  their artifacts (JSON → `keys`; CSV → `shape`/`columns`/`dtypes`).
- `python -m pytest -q tests/test_sidecar_schema_contract.py
  tests/test_experiment_artifact_schema.py tests/test_experiment_lineage_report.py
  tests/test_reproducibility_audit.py tests/test_fetch_h182_insider_data.py` →
  **124 passed, 0 failed**.
- `python -m pytest -q tests/test_reproducibility_audit.py` → **7 passed**;
  reproducibility baseline unchanged (197 / 11 / 528 / 0).
- `python -m ruff check src tests run_*.py scripts` and `ruff format --check` → clean.
- `git status` → clean before this session; the two annotation edits are the only
  working-tree changes. No commit/push.

## What remains unresolved

1. **Maintainer-only (CI contract):** `.github/workflows/gates.yml` not updated;
   7 `tests/test_gates_workflow.py` tests red until the maintainer applies
   `patches/0001-gates-workflow-contract-fix.patch` with workflow-scoped credentials.
   Agent cannot land `.github/workflows/**`.
2. **Research queue exhausted under free/public PIT data:** H1–H182 executed/rejected
   (register Cycles 96/116/118). No honest free-data H183 is pre-registrable.
3. **Reproducibility backlog:** `missing_files=197`, `hash_mismatches=11`,
   `orphaned_files=528`, `missing_meta_files=0` unchanged; baseline-frozen where
   contract/citation constraints apply.

## Approaches already failed / must not be repeated

- **Do not re-derive a "H182 is missing from the corpus" finding.** It is false:
  `experiments.jsonl` holds **174** records and H182 is present (record 174,
  `exp_2026-11-14T11-39-15Z`, REJECT, 3 artifacts on disk under `.experiments/nf_runs/`).
  The prior sweep erred by counting a stale 173-record file and by searching for a
  substring (`insider`) that does match the committed name
  `nf_20261110_08_insider_signal`. Always count the corpus directly and grep the
  committed runner name before drawing lineage conclusions.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or alter
  coverage/frozen-contract gates.
- Do not treat delisted/spliced/unavailable free series as PIT-valid.
- Do not mass-edit runners/tests/gates or frozen artifacts to force green.
- Do not append an H182 record to `experiments.jsonl` without sidecars + coordinated
  baseline/pinned-test updates (ratchet fails).
- Do not make speculative `src/qtr` changes absent an evidenced defect.

## One precise next task

**Maintainer (preferred, unblocks CI):** apply and push
`patches/0001-gates-workflow-contract-fix.patch` with workflow scope, then run
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed) on `origin/main`.
**Authorized research alternative:** secure one paid/PIT data gap (commodity
per-contract roll/contango, crypto perpetual funding, or historical options
chain/GEX) and run the smallest decisive pre-registered test for that single
mechanism (no invented free-data H183).

**Constraints:** preserve gates/contracts/100% `src/qtr` coverage; do not alter
published/frozen artifacts or thresholds except a deliberate authorized
corpus/baseline update; no workflow commit from agent.