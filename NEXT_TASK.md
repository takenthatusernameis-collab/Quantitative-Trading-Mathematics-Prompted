# NEXT TASK — Session 4/3 (next agent)

## Status: H10 prose-grid drift — COMPLETE

`run_h10_intraday_tsmom_pfopt_experiment.py:64` `EXPERIMENT_DESC` already carries
"13824-combo grid" enumerating all 8 dimension names; `main()` computes
`grid_size` from the constants (lines 358-367); `tests/test_h10_pfopt.py`
has `test_experiment_description_matches_pre_registered_grid` pinning it.
Verified this session via negative test (strip combo count → test FAILS;
restore → test PASSES). Full suite: **542 passed, 0 warnings**. Lint/format
clean. Working tree clean. No source change required.

## Documented next task (requires paid data — outside this session)

Per FINAL_REPORT.md §Next Task: widen the OOS window with **paid hourly futures
data** so the PF and Sharpe bootstrap CIs clear their gates with margin. H10/H22/H25
are PASS but PF-margin is CI-fragile (H13 CI [1.190, 1.425]; H25 Robustness CI
[1.2049, 1.4425], P(PF≥1.3)=0.6215). Do not run further hypotheses on free data
— the free-data hypothesis space is exhausted (yfinance hourly `=F` capped ~730
days; Coinbase ~12 days).

## Verification commands (run before declaring any task done)

`pip install -e .` (ensure `qtr` importable), then:
- `python -m pytest -q` (full suite, ~3:31)
- `python -m pytest -W error -q`
- `python -m pytest --cov=qtr --cov-report=term-missing`
- `python -m ruff check src tests run_*.py`
- `python -m ruff format --check src tests run_*.py`
- `bash -n .github/scripts/*.sh` and `bash .github/scripts/test_kilo_progress.sh`

## Notes

- `validate_strategy`'s `param_stability`/`walkforward_stability` are proxies;
  the literal ±1-std perturbation gate and 5-fold walk-forward metric live in
  the H10/H11/H9–H25 runners. Do not conflate them.
- `walk_forward_splits` tail-absorption is already fixed in HEAD
  (`statistics.py:108-110`); nothing to change there.