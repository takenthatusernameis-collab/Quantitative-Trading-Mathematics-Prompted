# Session complete (2026-11-20, Cycle 236 — audit/infrastructure: test hermeticity fix)

## State

H1–H190 exhausted/rejected or data-blocked (unchanged; see `AGENTS.md` and
`NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 215–235). Free-data point-in-time family
discovery remains exhausted; do not re-declare any H-ID data-blocked without
naming the probed source, and do not treat parameter/timeframe/universe/market
variants of H1–H190 as new families.

This cycle made a **durable, verified infrastructure fix** instead of new family
discovery (the prior handoff's suggested fallback).

## What changed (Cycle 236)

`tests/test_nf_20261120_01_equity_accruals.py` and
`tests/test_nf_20261120_02_net_share_issuance.py` were **non-hermetic**: six tests
read the untracked, git-ignored SEC cache (`.cache/xbrl/company_tickers.json` +
`CIK*.json`) with `fetch=False`. That cache exists only after a live H187/H188 run,
so **any fresh checkout (including CI) failed 6 tests with
`FileNotFoundError: ticker map not cached`**. The prior handoff's "only 7 failures"
claim was inaccurate for a clean checkout — the real count was **13**
(7 maintainer-gated + 6 cache-dependent).

Fix: the six tests now build a small **synthetic in-memory companyfacts bundle**
(`_fact` + `_accruals_bundle` / `_share_bundle` helpers) and call the pure runner
functions (`mod.xbrl.annual_observations`, `mod.annual_share_observations`,
`mod.build_monthly_signal_panel`) directly. No `.cache/`, no network. Two former
no-op tests (`test_filed_date_is_max_of_*`) were strengthened to assert the
latest-contributing-fact rule against distinct per-tag `filed` dates.

Scope: test files only. No `src/qtr`, runner, artifact, sidecar, hash, gate,
frozen number, or workflow was modified.

## Verified evidence (this session)

- `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **7 failed, 4540 passed, 51 skipped** (was 13 failed / 4534 passed). The 7
  failures are **all** `tests/test_gates_workflow.py` (maintainer-gated, by design);
  the 6 H187/H188 cache failures are gone (+6 passed).
- Coverage gate: `TOTAL 1692 0 642 0 100%`, "Required test coverage of 100.0%
  reached." (`src/qtr` untouched, so 100% branch coverage is unchanged).
- Hermeticity proven: `.cache/xbrl/` does not exist in this checkout, and both
  files pass under `-W error` (32 tests).
- `python -m ruff check src tests run_*.py scripts` → clean;
  `python -m ruff format --check src tests run_*.py scripts` → 360 files formatted.
- `python scripts/backtest_perf_regression_gate.py` → PERF GATE PASSED
  (0.432s, limit 5s).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → applies cleanly.
- Change set is exactly the two test files (no stray edits).

## One precise next task (for next session)

**None blocking.** The only remaining actionable item is still the
maintainer-applied workflow contract fix (`patches/0001-gates-workflow-contract-fix.patch`)
to make `tests/test_gates_workflow.py` green; it is agent-unreachable
(`.github/workflows/**` is maintainer-managed, restored from `origin/main` after
every session, and the repo-scoped GitHub App token has no `workflows` permission).
Optionally, as low-risk follow-ups:
1. `EXPERIMENT_ARTIFACT_AUDIT.md` still states Cycle-115 pins (108 dirs / 100
   summaries / 131 keys) while the live corpus and
   `tests/test_experiment_artifact_schema.py` pins are 116 / 108 / 150; refresh the
   prose (no test currently pins that doc, so it drifted silently).
2. Continue artifact/audit follow-ups from `REPRODUCIBILITY_AUDIT_REPORT.md` §2
   (drop 8 superseded duplicate `param_grid_results` keys + 3 stale `summary`
   keys from `experiments.jsonl`; authorization-gated, do not overwrite artifacts).

## Approaches already tried / do not repeat

- Do not re-declare any H-ID family as data-blocked without naming the probed source.
- Do not treat parameter/timeframe/universe/market variants of H1–H190 as new families.
- Do not modify `.github/workflows/**` (maintainer-managed; agent-unreachable).
- Do not re-run H190 as a variant; the full-window pre-registered run is the record.
- Do not reintroduce a hard dependency on `.cache/xbrl/**` in tests: that cache is
  git-ignored and absent on fresh checkouts/CI. Tests must be hermetic (synthetic
  fixtures), as H187/H188 now are.

(End of file - total 78 lines)