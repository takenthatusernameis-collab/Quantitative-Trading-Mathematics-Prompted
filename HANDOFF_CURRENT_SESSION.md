# HANDOFF_CURRENT_SESSION.md — Perf regression gate finished and wired (Cycle 105)

## What changed (this session)

Three changes, all confined to the CI/CD-hardening fallback item. No `src/qtr`,
runner, gate, threshold, verdict, or frozen artifact changed.

1. **`tests/test_backtest_perf_regression_gate.py` (new).** Pins the contract of
   `scripts/backtest_perf_regression_gate.py` (added last session but left
   untested and unwired). Five guards: script exists, constants pinned
   (`N_SYMBOLS=100`, `N_BARS=252`, `MAX_ELAPSED_SECONDS=5.0`), `generate_data`
   shape/finiteness, and the pass/fail branch logic. The branch tests inject a
   fake `perf_counter` and stub `run_backtest`, so they are deterministic on any
   host and never depend on wall-clock speed.
2. **`scripts/backtest_perf_regression_gate.py` (fix).** The timed region ran
   with `tracemalloc` active, which inflates the measured backtest ~3x on this
   host (measured 0.80s clean vs 2.35s traced). The gate was therefore comparing
   tracing-inflated time to its 5.0s limit. `tracemalloc` now runs as a separate,
   untimed memory probe; the reported time is clean (0.845s on this host).
3. **`.github/workflows/gates.yml` (wiring).** Added a `Backtest performance
   regression gate` step to the `research_gates` job and added `scripts/**` to
   the push/PR path triggers, so the gate actually runs in CI instead of being
   dead code.

## What was actually verified (this session, own evidence)

- `PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **3743 passed, 51 skipped, 0 failed** (620s), `src/qtr` coverage **100.00%**
  (1211 stmts / 422 branches / 0 miss). Baseline before this session was 3738
  passed; +5 are the new gate tests.
- `python3 -m ruff check src tests run_*.py` → All checks passed.
- `python3 -m ruff format --check src tests run_*.py` → 323 files already formatted.
- `python3 scripts/backtest_perf_regression_gate.py` → `0.845s (limit 5s), 10.7MB
  peak, 13668 trades`, exit 0.
- `python3 -m pytest -q -W error tests/test_backtest_perf_regression_gate.py` → 5 passed.
- `.github/workflows/gates.yml` parses (`yaml.safe_load`) and the `research_gates`
  steps are `[<checkout>, <setup-python>, Install deps, Run gates, Backtest
  performance regression gate]`.

## What remains unresolved

- **Artifact restoration apply:** needs explicit human authorization and is a
  **no-op** on this checkout (`scripts/plan_artifact_restoration.py --dry-run` →
  Recoverable 0 / Excluded 172 / Unrecoverable 25).
- **H182 strategy-family discovery:** blocked on authorized free/PIT data for a
  materially new mechanism. Free-data point-in-time discovery is exhausted at
  H181 (`NEW_FAMILY_RESEARCH_REGISTER.md`, `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`
  §6).
- **All generated inventories are pinned** (lineage report, artifact audit,
  reproducibility audit baseline). Running experiments that mutate
  `.experiments/experiments.jsonl` will deliberately fail those pins until the
  report/pins are regenerated.
- **`scripts/` is excluded from the ruff targets.** `ruff check src tests
  run_*.py` never lints `scripts/*.py`; all three scripts happen to be clean
  today, but a broken script could pass CI. This is the next bounded task.

## Failed approaches / do not blindly repeat

- Do not trust a committed doc's counts without re-running the producing check.
- Do not run `scripts/plan_artifact_restoration.py --apply` without authorization.
- Do not invent H182 from exhausted/adjacent families or blocked data.
- Do not commit/push unless explicitly requested.
- A perf gate must not time the region while `tracemalloc` is active; tracing
  inflates the measurement and understates headroom (this session: 3x).

## One precise next task

**Add `scripts` to the ruff check/format targets.** `.github/workflows/gates.yml`
runs `python -m ruff check src tests run_*.py` and `python -m ruff format --check
src tests run_*.py`, and `AGENTS.md` documents the same commands; none lint
`scripts/`. All three scripts (`backtest_perf_regression_gate.py`,
`generate_experiment_lineage_report.py`, `plan_artifact_restoration.py`) are
already clean under `ruff check`/`ruff format --check`, so widening the target is
safe. Change the two CI commands and the matching `AGENTS.md` lines to include
`scripts`, then re-run both ruff commands and
`tests/test_backtest_perf_regression_gate.py`. No `src/qtr` change expected.

The alternative — artifact-restoration authorization or an authorized free/PIT
source for H182 — is blocked on human authorization and is not actionable here.

## Constraints

- `src/qtr` unchanged. No frozen/certified/published value, verdict, threshold, or
  gate weakened.
- No commit/push performed (not requested). Working tree has the new test file,
  the gate fix, and the workflow edit.
- Free/public data only.