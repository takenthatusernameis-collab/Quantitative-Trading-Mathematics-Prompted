# Handoff Summary

## Current state
- All tests pass: 525 passed, 0 warnings (~157s) — re-confirmed this session.
- Changes this session:
  - `src/qtr/backtest/engine.py`: wired the `volumes` argument through the
    `AssetClass.CRYPTO` cost branch. It previously hardcoded
    `daily_vol_pct = 0.0` ("Would need 24h volume data"), so the
    `crypto_slippage_bps_per_pct_daily_vol` term was structurally zero and
    every crypto backtest — including the H23 5-symbol Coinbase book — was
    charged a flat 7 bps regardless of volume traded. Now computes daily-volume
    participation (clipped to [0,1] like the equity ADV path) and degrades to
    the old flat-7-bps behaviour when no volumes are supplied.
  - `tests/test_backtest_engine.py`: added `test_crypto_uses_volumes_argument`,
    a regression test that fails without the fix (asserts -0.0107 vs the old
    -0.0007 for a 1-BTC-volume book).
- Lint clean (`ruff check src tests run_*.py`), format clean
  (`ruff format --check` → 69 files). Coverage on `src/` remains 100%
  (the new branch is covered by the new test).
- H23 artifacts are **unaffected**: H23 calls `make_futures_config()` from
  `run_h9_intraday_tsmom_experiment.py`, which sets
  `asset_class=AssetClass.FUTURE`, so the crypto branch is not exercised by
  the committed H23 artifacts. `test_certified_artifact_values.py` (68 tests)
  and `test_h23_crypto_futures_tsmom.py` both pass unchanged.

## Next agent actions
No pending task within the free-data constraint. If assigned a new task,
verify with: `python -m pytest -q`, `python -m ruff check src tests run_*.py`,
`python -m ruff format --check`, plus `bash -n .github/scripts/*.sh` and
`bash .github/scripts/test_kilo_progress.sh`. Note: `qtr` must be importable — run
`pip install -e .` from the repo root if `ModuleNotFoundError: No module named 'qtr'`
appears at collection time.

## Documented next task (requires paid data — outside this session)

Per FINAL_REPORT.md §Next Task: widen the OOS window with **paid hourly futures data**
so the PF and Sharpe bootstrap CIs clear their gates with margin. H10/H22/H25 are PASS
but PF-margin is CI-fragile (H13 CI [1.190, 1.425]; H25 Robustness CI [1.2049, 1.4425],
P(PF≥1.3)≈0.5–0.62). Do not run further hypotheses on free data — the free-data
hypothesis space is exhausted (yfinance hourly `=F` capped ~730 days; Coinbase ~12 days).

## Implementation note for future gate work
`validate_strategy`'s `param_stability` is a *proxy* (fold-profitability fraction), not the
literal "±1 std of optimal parameters" from PROMPT_V2.md, because the function only
receives returns + trades, not a parameter grid. The real ±1-std perturbation gate lives in
the H10/H11 runners (`run_h10_intraday_tsmom_pfopt_experiment.py`,
`run_h11_robustness_experiment.py`) as `e2_perturbation`. Do not conflate the two.

(End of file - total 41 lines)