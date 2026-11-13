# NEXT_TASK.md — Perf regression gate wired; `scripts/` lint gap is next

## Current status (re-verified from scratch this session)
- `python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **3743 passed, 51 skipped, 0 failed** (620s), `src/qtr` coverage **100.00%**
  (1211 stmts / 422 branches / 0 miss).
- `python3 -m ruff check src tests run_*.py` → All checks passed.
- `python3 -m ruff format --check src tests run_*.py` → 323 files already formatted.
- `python3 scripts/backtest_perf_regression_gate.py` → `0.845s (limit 5s)` exit 0.

## What changed this session (CI/CD hardening fallback item)
- `tests/test_backtest_perf_regression_gate.py` (new): 5 contract guards for the
  perf gate; deterministic (fake `perf_counter`, stubbed engine), no wall-clock
  dependence.
- `scripts/backtest_perf_regression_gate.py`: fixed the timed region — it ran
  under `tracemalloc`, which inflated the measurement ~3x (0.80s clean vs 2.35s
  traced). Memory is now a separate untimed probe; reported time is clean.
- `.github/workflows/gates.yml`: added a `Backtest performance regression gate`
  step to `research_gates` and added `scripts/**` to push/PR path triggers.

## Unresolved / blocked
- **Artifact restoration apply (needs explicit human authorization):** `--apply`
  is a no-op on this checkout; `--dry-run` → Recoverable 0 / Excluded 172 /
  Unrecoverable 25. Baseline in `tests/test_reproducibility_audit.py`:
  `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`,
  `missing_meta_files=140`.
- **H182 discovery (needs data/authorization):** free-data PIT family discovery is
  exhausted at H181 (Cycle 96); carry/insider/earnings/options/breakeven candidates
  are data-blocked; remaining candidates are adjacency- or power-blocked.
- **All generated inventories are pinned.** Running experiments that change
  `.experiments/experiments.jsonl` will fail
  `test_report_reproduces_committed_content` and the summary pins until
  `EXPERIMENT_LINEAGE_REPORT.md` is regenerated deliberately and pins updated.
- **`scripts/` is not linted.** `ruff check src tests run_*.py` never covers
  `scripts/*.py`; all three scripts are clean today, but a broken script passes CI.

## One precise next task
**Widen the ruff targets to include `scripts/`.** In `.github/workflows/gates.yml`
change both ruff commands from `src tests run_*.py` to
`src tests run_*.py scripts`, and update the matching command lines in `AGENTS.md`
(`## Lint and format` section) to match. Then re-run:
- `python3 -m ruff check src tests run_*.py scripts`
- `python3 -m ruff format --check src tests run_*.py scripts`
- `python3 -m pytest -q -W error tests/test_backtest_perf_regression_gate.py`

All three scripts are already clean under both ruff commands, so no source change
is expected. Do not widen coverage or weaken any gate.

## Failed approaches / do not repeat
- Do not trust committed doc counts without re-running the producing check.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not time a performance gate with `tracemalloc` active.
- Do not commit/push unless requested.

## Constraints
- `src/qtr` unchanged unless evidenced defect (then rerun pinned full gates). No
  frozen/certified/published artifact, verdict, threshold, or gate weakening. No
  commit/push unless requested. Free/public data only.