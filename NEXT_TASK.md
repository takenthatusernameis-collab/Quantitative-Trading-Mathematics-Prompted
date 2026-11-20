# Next task (2026-11-20, Cycle 227)

## State at the start of this session (what the previous session left)
- HEAD `a080c14` == origin/main, clean tree. Cycle 226 reconciled the report/pin drift with an executable doc-consistency guard and re-verified the baseline (4473 passed, 100% `src/qtr` coverage, perf gate pass).
- Backlog unchanged: **missing 25, hash_mismatches 11, orphaned 356, missing_meta 0**; both count-only backlogs identity-pinned (`a5024443…` / `c6611f77…`) and the 11 mismatches identity-pinned as tuples.

## What changed this session
- Nothing in `src/qtr`, `tests`, `run_*.py`, `scripts`, gates, artifacts, sidecars, hashes, frozen numbers, or `.github/workflows/**`. Only `HANDOFF.md` and this file updated. **Handoff update, not project progress.**

## What was actually verified (own evidence, 2026-11-20)
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → patch applies cleanly to the live `gates.yml` (maintainer task remains ready-to-apply).
- `pytest -q tests/test_gates_workflow.py` → **7 failed**, unchanged (lint lacks `scripts/**` in ruff targets; push/pull_request lack `scripts/**` path filters; `research_gates` lacks the backtest perf gate and the editable install).
- Full suite **not** re-run: Cycle 226 already re-verified with own evidence (4473 passed, 51 skipped, 0 failed; `src/qtr` coverage **100.00%** 1692/642/0); per Cycle 226 guidance, the 25/11/356/0 counts are not re-derived a tenth time.

## What remains unresolved
- **Maintainer-gated workflow patch:** apply/push `patches/0001-gates-workflow-contract-fix.patch`, then verify `CONTRACT SATISFIED` and 7 passing contract tests. Agent-unreachable: `.github/workflows/**` is restored from origin/main after every session, excluded from staging, and the repo token has no `workflows` permission.
- **25 unrecoverable missing artifacts** (no hash-matching source) — need a re-run with the original configs; authorization-gated.
- **11 hash mismatches** — superseded duplicate log entries; remediation is dropping the stale keys from `experiments.jsonl`; authorization-gated and must not overwrite artifacts.
- **H1–H186 exhausted/rejected; H187 unassigned with no free-data source** (directive §6).

## One precise next task
**Maintainer:** apply/push `patches/0001-gates-workflow-contract-fix.patch`, then verify `CONTRACT SATISFIED` + 7 passing contract tests.

**Agent:** stop the maintenance-only loop. The only remaining reproducible work needs authorization: (a) re-run the 25 missing artifacts with their original configs, or (b) drop the 11 superseded `experiments.jsonl` keys — either way updating `REPRODUCIBILITY_BASELINE`, `PINNED_HASH_MISMATCHES`, the two identity digests, and `REPRODUCIBILITY_AUDIT_REPORT.md` in one commit (the new report-consistency test forces the doc and pins to move together). If authorization is unavailable, record the block and stop; do not re-derive the same counts a tenth time.

## Approaches already tried and why they should not be repeated
- Do not restore H28 artifacts by copying them to depth-one paths (breaks the H28 depth-one invariant); do not invent a `patches/0002-*` rehearsal patch (provenance is commit `1a7c83a`).
- Do not rebuild the corpus guard on `json.loads`; use `object_pairs_hook` (Cycle 217).
- Do not reclassify the 11 hash mismatches as path corrections — verified 2026-11-19 that no file under `.experiments/` carries the recorded hashes.
- Do not re-run H184/H185/H186 or parameter/universe/window variants; do not re-probe CHRIS/CME/Yahoo/stooq/LME/DCE; do not re-declare probed FRED/binance/Chinese-exchange/CFTC-Socrata sources as blocked.
- Do not edit `.github/workflows/**` or weaken any gate, contract test, or the new report/baseline consistency assertion.
- Do not trust "working tree clean" or handoff counts as proof tests are green; do not re-derive the same counts a tenth time — Cycle 226 evidence stands.
