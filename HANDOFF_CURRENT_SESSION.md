# HANDOFF_CURRENT_SESSION.md — Cycle 115 (2026-11-14): fixed H182 corpus cache poisoning; corpus repaired; H182 experiment run and REJECTED

## What changed

- `src/qtr/data/insider.py` — new `load_cached_transactions(path)`: missing, unreadable, or
  zero-row parquet is a cache *miss* (empty `TRANSACTION_COLUMNS` frame), not a valid cache.
- `src/qtr/data/__init__.py` — export `load_cached_transactions`.
- `scripts/fetch_h182_insider_data.py` — skip only non-empty caches; re-fetch empty ones;
  never write an empty parquet; isolate per-issuer errors; added `--force` and a `src`
  `sys.path` bootstrap.
- `tests/test_sec_insider.py` — 2 tests for the helper (all branches).
- `tests/test_fetch_h182_insider_data.py` — new: 5 tests for the corpus cache contract.

## Actually verified (this session, own evidence)

- **Focused:** `pytest tests/test_sec_insider.py tests/test_fetch_h182_insider_data.py -q` — 42 passed.
- **Coverage:** `src/qtr/data/insider.py` — **100%** (234 stmts / 84 branches / 0 miss).
- **Lint:** `python -m ruff check src tests run_*.py scripts` — All checks passed.
- **Format:** `python -m ruff format --check src tests run_*.py scripts` — 334 files already formatted.
- **Real EDGAR re-fetch:** `--symbols AAPL --force` → 325 rows; then
  `--symbols AAPL,MSFT,AMZN,NVDA` → AAPL skipped (325 cached), MSFT 402, AMZN 704, NVDA 1381
  (all previously zero-row). Corpus now populated for AAPL/GOOGL/MSFT/AMZN/NVDA.
- **H182 corpus complete:** All 10 pre-registered symbols cached (8,420 total rows):
  AAPL(325), MSFT(402), GOOGL(401), AMZN(704), NVDA(1381), META(3653), JPM(222), XOM(114), JNJ(503), WMT(715).
- **H182 experiment run:** `run_nf_20261110_08_insider_signal.py` (full grid, 36 combos) —
  **VERDICT: REJECT** (3/8 gates passed). OOS Val+Test Sharpe 0.46, PF 1.11, WF stability 0.47,
  worst-regime Sharpe -0.22, benchmark IR -1.39 (p=0.97). Gates passed: trades≥50, maxDD≤15%, perturbation≥0.5.
- **Full pinned gate:** `pytest -q --cov=qtr --cov-branch --cov-report=term-missing` (443s) —
  **3,793 passed / 51 skipped / 9 failed**. The 7 `test_gates_workflow.py` failures are the
  maintainer-gated workflow-contract block (unchanged). The 2 new `test_experiment_artifact_schema.py`
  failures are expected: new H182 artifacts increased directory count (103→108) and summary count (95→100).
  `src/qtr` coverage **100%** (1448 stmts / 508 branches / 0 miss).
- **Patch:** `git apply --check patches/0001-gates-workflow-contract-fix.patch` — **APPLIES_CLEANLY**.
- **Perf gate:** `python scripts/backtest_perf_regression_gate.py` — **PASSED** (0.410s, limit 5s).

## What remains unresolved

1. **Maintainer-only:** apply `patches/0001-gates-workflow-contract-fix.patch` (workflow scope)
   and push to `origin/main` to turn the 7 red `tests/test_gates_workflow.py` tests green.
2. **Artifact schema tests:** `test_experiment_artifact_schema.py` has 2 failures due to new
   H182 experiment artifacts. These are expected and will be resolved when the artifact
   inventory is updated to include the H182 run (or the test expectations are updated by maintainer).
3. **H182 concluded:** H182 is REJECTED per pre-registered gates. No further action on H182.

## Failed approaches / do not repeat

- Do not repeat re-verification-only cycles as "progress" when state is stable and no evidenced defect exists.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` / coverage / frozen contracts.
- Do not treat a zero-row parquet as a valid cache.

## One precise next task

**Select H183 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96.**
H1–H182 are now exhausted/rejected. The next NEW-FAMILY DISCOVERY MODE cycle must search at least three
materially distinct mechanism categories, rank candidates, pre-register the highest-information experiment,
and implement only after decision-ready. Free-data preference and all statistical gates are preserved.

**Constraints:** `src/qtr` changes require 100% coverage; no gate weakening; no published/frozen
artifact, verdict, threshold, or frozen number modified; no commit/push of `.github/workflows/**`.