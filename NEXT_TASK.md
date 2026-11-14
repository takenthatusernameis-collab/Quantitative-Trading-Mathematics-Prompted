# NEXT_TASK.md

## Latest session (2026-11-14, Cycle 115) — fixed H182 corpus cache poisoning; corpus repaired; H182 experiment run and REJECTED

### What changed

- `src/qtr/data/insider.py` — added `load_cached_transactions(path)`: a missing,
  unreadable, or zero-row parquet is returned as an empty `TRANSACTION_COLUMNS`
  frame (a cache *miss*) instead of being trusted. Repairs the observed failure
  where a transient EDGAR outage wrote a zero-row cache that was then skipped forever.
- `src/qtr/data/__init__.py` — export `load_cached_transactions`.
- `scripts/fetch_h182_insider_data.py` — skip a cache only when it has ≥1 row;
  re-fetch empty caches; never write an empty parquet (leave existing file untouched);
  isolate per-issuer fetch errors into the manifest; added `--force` and a `src`
  `sys.path` bootstrap so it runs from a bare clone.
- `tests/test_sec_insider.py` — 2 tests for `load_cached_transactions` (all branches).
- `tests/test_fetch_h182_insider_data.py` — new: 5 tests pinning the corpus cache
  contract (empty re-fetch, non-empty skip, `--force`, error, empty-fetch).

### What was actually verified (own evidence)

- `python -m pytest tests/test_sec_insider.py tests/test_fetch_h182_insider_data.py -q` — 42 passed.
- `src/qtr/data/insider.py` coverage — **100%** (234 stmts / 84 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` — All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` — 334 files already formatted.
- Real EDGAR re-fetch (no mocks): `python scripts/fetch_h182_insider_data.py --symbols AAPL --force` → 325 rows; then `--symbols AAPL,MSFT,AMZN,NVDA` → AAPL skipped (325 cached), MSFT 402, AMZN 704, NVDA 1381 (all previously zero-row). Corpus now populated for AAPL/GOOGL/MSFT/AMZN/NVDA.
- **H182 corpus complete:** All 10 pre-registered symbols cached (8,420 total rows): AAPL(325), MSFT(402), GOOGL(401), AMZN(704), NVDA(1381), META(3653), JPM(222), XOM(114), JNJ(503), WMT(715).
- **H182 experiment run:** `python run_nf_20261110_08_insider_signal.py` (full grid, 36 combos) — **VERDICT: REJECT** (3/8 gates passed). OOS Val+Test Sharpe 0.46, PF 1.11, WF stability 0.47, worst-regime Sharpe -0.22, benchmark IR -1.39 (p=0.97). Gates passed: trades≥50, maxDD≤15%, perturbation≥0.5. Artifact at `.experiments/nf_runs/nf_20261110_08_insider_signal_20261114_115858/summary.json`.
- Full pinned gate `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` — **3,793 passed / 51 skipped / 9 failed** (443s). The 7 `test_gates_workflow.py` failures are *exclusively* the maintainer-gated workflow-contract block (unchanged). The 2 `test_experiment_artifact_schema.py` failures are expected: new H182 artifacts increased directory count (103→108) and summary count (95→100). `src/qtr` coverage **100%** (1448 stmts / 508 branches / 0 miss).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` — **APPLIES_CLEANLY**.
- `python scripts/backtest_perf_regression_gate.py` — **PASSED** (0.410s, limit 5s).

Git state: changes are **uncommitted** in the working tree (no commit was requested this
session): modified `scripts/fetch_h182_insider_data.py`, `src/qtr/data/__init__.py`,
`src/qtr/data/insider.py`, `tests/test_sec_insider.py`, `NEXT_TASK.md`,
`HANDOFF_CURRENT_SESSION.md`, `HANDOFF.md`; untracked `tests/test_fetch_h182_insider_data.py`.
The fetched corpus under `.cache/insider/` is gitignored (not staged). New experiment artifacts under `.experiments/nf_runs/nf_20261110_08_insider_signal_*/` are also uncommitted.

### What remains unresolved

1. **Maintainer-only:** `tests/test_gates_workflow.py` is red on `origin/main` by design; fix is `patches/0001-gates-workflow-contract-fix.patch`. `.github/workflows/**` is agent-unreachable.
2. **Artifact schema tests:** `test_experiment_artifact_schema.py` has 2 failures due to new H182 experiment artifacts (directory count 108 vs expected 103, summary count 100 vs expected 95). These are expected consequences of running the H182 experiment and will be resolved when the artifact inventory is updated.
3. **H182 concluded:** H182 is REJECTED per pre-registered gates. No further action on H182.
4. **H183 selection required:** H1–H182 exhausted/rejected per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96 and this session. Selecting H183 requires a new NEW-FAMILY DISCOVERY MODE cycle per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6.

### Approaches already tried and why they should not be repeated

- Do not repeat re-verification-only cycles (105–114): suite state is stable; re-running is not progress.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` / coverage / frozen contracts.
- Do not treat a zero-row parquet as a valid cache; the fix is the `load_cached_transactions` miss semantics.

### One precise next task

**Select H183 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4/§6 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96:** Complete a NEW-FAMILY DISCOVERY MODE cycle — search at least three materially distinct mechanism categories, propose ≥3 repository-new family candidates with scores, rank them, pre-register the highest-expected-information experiment, and implement only after decision-ready. Free-data preference, protected holdout, 100% `src/qtr` coverage, and all statistical gates are preserved.

**Constraints:** no gate weakening; no published/frozen artifact, verdict, threshold, or frozen number modified; no commit/push of `.github/workflows/**`; `src/qtr` changes require 100% coverage.