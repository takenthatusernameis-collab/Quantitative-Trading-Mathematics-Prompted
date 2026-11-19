# Current session handoff (2026-11-19, Cycle 226)

## What changed (2 files, both doc/test; no `src/qtr`, artifact, gate, or workflow change)
- **New executable doc-consistency guard** in `tests/test_reproducibility_audit.py`:
  `test_audit_report_findings_table_matches_pinned_baseline` parses the Findings
  status table in `REPRODUCIBILITY_AUDIT_REPORT.md` and asserts it equals
  `REPRODUCIBILITY_BASELINE`, and that both live identity digests are quoted
  verbatim. `test_audit_report_count_parser_is_not_vacuous` proves the parser
  detects a drifted count. Helper: `_report_status_row_counts` /
  `REPORT_ROW_LABELS`.
- **Report corrected:** the top block presented the *superseded* 197 / 528 values
  as "current". It now states the live 25 / 11 / 356 / 0 first and labels the
  Cycle-223 values as pre-remediation history.
- Rationale: Cycles 222–225 each left stale counts/provenance in the report or
  handoff and spent the session re-reconciling it. The gate now fails on that drift
  instead of relying on the next agent noticing. This is a durable invariant, not a
  control-marker.

## What was actually verified (own evidence, 2026-11-19)
- Independent recount of `.experiments/experiments.jsonl` (174 records) → **missing 25,
  hash_mismatches 11, orphaned 356, missing_meta 0**; recomputed digests equal the pins
  (`a5024443…`, `c6611f77…`).
- Independent check that none of the 11 pinned hash-mismatch rows has a hash-matching
  source anywhere under `.experiments/` (expected-hash lookup over every file) → all 11
  "not found"; they are not path-remediation candidates.
- `python -m pytest -q tests/test_reproducibility_audit.py` → **10 passed** (was 8);
  with `tests/test_artifact_restoration_plan.py tests/test_h28_causal_recertification.py`
  → **65 passed**.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` →
  **4473 passed, 51 skipped, 0 failed** (482.34 s); `src/qtr` coverage **100.00%**
  (1692 stmts / 642 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**;
  `python -m ruff format --check …` → **352 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED**
  (0.440 s < 5 s, 10.7 MB peak, 13668 trades).
  `python scripts/verify_gates_workflow_patch.py` → **PATCH VERIFIED**
  (7 live violations; maintainer-gated).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch`; then
  `python scripts/verify_gates_workflow_patch.py` (expect `CONTRACT SATISFIED`) and
  `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **25 unrecoverable missing artifacts** — no hash-matching source in the store; only a
  re-run with the original configs restores them (authorization-gated).
- **11 hash mismatches** — superseded duplicate log entries; remediation is dropping the
  stale keys from `experiments.jsonl` (authorization-gated, must not overwrite artifacts).
- **H1–H186 exhausted/rejected; H187 unassigned with no free-data source** (directive §6).
- Cosmetic: commit `1a7c83a` has an empty message; history is pushed, not rewritten.

## One precise next task
**Maintainer:** apply/push `patches/0001-gates-workflow-contract-fix.patch`, then verify
`CONTRACT SATISFIED` + 7 passing contract tests.

**Agent:** the free-data research queue is concluded and the reproducibility backlog is
frozen behind authorization, so do not start a tenth maintenance-only cycle. Either
(a) obtain authorization for one of the two concrete remediations and execute it with
evidence — re-run the 25 missing artifacts, or drop the 11 superseded `experiments.jsonl`
keys — updating `REPRODUCIBILITY_BASELINE`, the pins, and the report in one commit; or
(b) if no authorization is available, verify the baseline, confirm the new doc-consistency
guard is green, and record that the queue is blocked rather than re-describing it.

## Approaches already tried and why they should not be repeated
- Do not restore H28 artifacts to depth-one paths (breaks the H28 invariant); do not add a
  `patches/0002-*` rehearsal patch (provenance is commit `1a7c83a`).
- Do not rebuild the corpus guard on `json.loads` (use `object_pairs_hook`).
- Do not treat the 11 hash mismatches as path-remediation candidates — verified 2026-11-19
  that no file in the store carries the recorded hash.
- Do not re-run H184/H185/H186 or parameter/universe/window variants; do not re-probe
  CHRIS/CME/Yahoo/stooq/LME/DCE; do not re-declare probed FRED/binance/Chinese-exchange/
  CFTC-Socrata sources as blocked.
- Do not edit `.github/workflows/**`, weaken `tests/test_gates_workflow.py`, or loosen the
  new report/baseline consistency assertion to make a doc edit pass.
- Do not trust handoff counts or "working tree clean" as proof the pins are green.

## HEAD
- Session started at `f48d30f` (== origin/main, clean tree).
