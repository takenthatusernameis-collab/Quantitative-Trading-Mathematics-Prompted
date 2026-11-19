# Next task (2026-11-19, Cycle 226)

## State at the start of this session (what the previous session left)
- HEAD `f48d30f` == origin/main, clean tree. Cycle 225 had reconciled the H28 path
  remediation docs and re-verified the baseline (4471 passed, 100% `src/qtr`
  coverage, perf gate pass).
- Backlog: **missing 25, hash_mismatches 11, orphaned 356, missing_meta 0**; the two
  count-only backlogs are identity-pinned (`a5024443…` / `c6611f77…`) and the 11
  mismatches are identity-pinned as tuples.
- Repeated defect pattern, Cycles 222–225: the authoritative prose
  (`REPRODUCIBILITY_AUDIT_REPORT.md`, handoffs) drifted from the executable pins, and a
  whole session was spent re-reconciling it. Cycle 226's top report block still called
  the superseded 197 / 528 values "current".

## What changed this session
- `tests/test_reproducibility_audit.py`: new
  `test_audit_report_findings_table_matches_pinned_baseline` parses the Findings status
  table of `REPRODUCIBILITY_AUDIT_REPORT.md` and asserts it equals
  `REPRODUCIBILITY_BASELINE`, plus that both live identity digests are quoted verbatim;
  `test_audit_report_count_parser_is_not_vacuous` proves a drifted count is detectable.
  Helpers `REPORT_ROW_LABELS` / `_report_status_row_counts`. Existing pins untouched.
- `REPRODUCIBILITY_AUDIT_REPORT.md`: live 25 / 11 / 356 / 0 now stated first; the
  Cycle-223 197 / 528 block relabelled as superseded pre-remediation history.
- No change to `src/qtr`, other tests, runners, gates, artifacts, sidecars, hashes,
  frozen numbers, or `.github/workflows/**`.

## What was actually verified (own evidence, 2026-11-19)
- Independent recount of the 174-record log → 25 / 11 / 356 / 0 with digests equal to
  the pins. Independent scan: none of the 11 mismatched artifacts' recorded hashes
  exists anywhere under `.experiments/`, so they are **not** path-remediation candidates.
- `pytest -q tests/test_reproducibility_audit.py` → **10 passed** (was 8);
  with the restoration-plan and H28 files → **65 passed**.
- Full pinned suite `pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
  --ignore=tests/test_gates_workflow.py` → **4473 passed, 51 skipped, 0 failed**
  (482.34 s); `src/qtr` coverage **100.00%** (1692/642/0).
- `ruff check` → All checks passed; `ruff format --check` → 352 files formatted.
- `scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.440 s, 10.7 MB,
  13668 trades). `scripts/verify_gates_workflow_patch.py` → **PATCH VERIFIED** (7 live
  violations, maintainer-gated). `pytest -q tests/test_gates_workflow.py` → 7 failed
  (unchanged, maintainer-gated).

## What remains unresolved
- **Maintainer-gated workflow patch:** apply/push `patches/0001-gates-workflow-contract-fix.patch`,
  then verify `CONTRACT SATISFIED` and 7 passing contract tests.
- **25 unrecoverable missing artifacts** (no hash-matching source) — need a re-run with
  the original configs; authorization-gated.
- **11 hash mismatches** — superseded duplicate log entries; remediation is dropping the
  stale keys from `experiments.jsonl`; authorization-gated and must not overwrite artifacts.
- **H1–H186 exhausted/rejected; H187 unassigned with no free-data source** (directive §6).

## One precise next task
**Maintainer:** apply/push `patches/0001-gates-workflow-contract-fix.patch`, then verify
`CONTRACT SATISFIED` + 7 passing contract tests.

**Agent:** stop the maintenance-only loop. The only remaining reproducible work needs
authorization: (a) re-run the 25 missing artifacts with their original configs, or (b) drop
the 11 superseded `experiments.jsonl` keys — either way updating
`REPRODUCIBILITY_BASELINE`, `PINNED_HASH_MISMATCHES`, the two identity digests, and
`REPRODUCIBILITY_AUDIT_REPORT.md` in one commit (the new report-consistency test forces the
doc and pins to move together). If authorization is unavailable, record the block and stop;
do not re-derive the same counts a tenth time.

## Approaches already tried and why they should not be repeated
- Do not restore H28 artifacts by copying them to depth-one paths (breaks the H28 depth-one
  invariant); do not invent a `patches/0002-*` rehearsal patch (provenance is commit `1a7c83a`).
- Do not rebuild the corpus guard on `json.loads`; use `object_pairs_hook` (Cycle 217).
- Do not reclassify the 11 hash mismatches as path corrections — verified 2026-11-19 that no
  file under `.experiments/` carries the recorded hashes.
- Do not re-run H184/H185/H186 or parameter/universe/window variants; do not re-probe
  CHRIS/CME/Yahoo/stooq/LME/DCE; do not re-declare probed FRED/binance/Chinese-exchange/
  CFTC-Socrata sources as blocked.
- Do not edit `.github/workflows/**` or weaken any gate, contract test, or the new
  report/baseline consistency assertion.
- Do not trust "working tree clean" or handoff counts as proof tests are green.
