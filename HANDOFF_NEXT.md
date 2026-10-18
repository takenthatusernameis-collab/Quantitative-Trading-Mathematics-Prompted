# Handoff Summary

## Current state
- All tests pass: 533 passed, 0 warnings (was 532) — re-confirmed this session (~199s).
- src/ coverage: 99% (918/918 stmts; single uncovered branch is the unreachable `walk_forward_splits` empty-window guard at statistics.py:114). Lint/format clean on changed files. Workflow scripts pass `bash -n` and the progress-helper regression test.
- Changes this session (uncommitted):
  - `run_h23_crypto_futures_tsmom.py`: **`EXPERIMENT_DESC` corrected from prose with no combo count to "6912-combo grid (smooth_span x vol_window_long x regime_scaling x min_trade_interval x trailing_mult x max_hold_bars x vol_limit_mult x vol_floor_fraction), Val-selected, Test-protected, gates per H23 pre-registration."** — the pre-registration text (HYPOTHESIS_SPEC.md:2626) and the test docstring both claimed a "2304-combo grid", but the listed parameters yield 6912 (4×3×1×4×4×4×3×3). The description is logged verbatim into `.experiments/experiments.jsonl` (9 H23 records verified).
  - `tests/test_h23_crypto_futures_tsmom.py`: new `test_experiment_description_matches_pre_registered_grid` asserts the combo count in the prose equals the computed grid size and that all 8 grid dimensions are enumerated.
  - `HYPOTHESIS_SPEC.md:2626`: "2304-combo grid" → "6912-combo grid".
- Prior tasks (walk-forward stability gate false-pass, global RNG mutation fix, min_param_stability gate, empty-input guard, coverage gaps, beta ddof fix, H22 stale-prose fix) remain complete and verified.

## Next agent actions
If assigned a new task, verify with:
`python -m pytest -q`, `python -m pytest -W error -q`,
`python -m pytest --cov=qtr --cov-report=term-missing`,
`python -m ruff check src tests run_*.py`, `python -m ruff format --check`,
plus `bash -n .github/scripts/*.sh` and `bash .github/scripts/test_kilo_progress.sh`.
Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.

## Documented next task (requires paid data — outside this session)

Per FINAL_REPORT.md §Next Task: widen the OOS window with **paid hourly futures data**
so the PF and Sharpe bootstrap CIs clear their gates with margin. H10/H22/H25 are PASS
but PF-margin is CI-fragile (H13 CI [1.190, 1.425]; H25 Robustness CI [1.2049, 1.4425],
P(PF≥1.3)≈0.5–0.62). Do not run further hypotheses on free data — the free-data
hypothesis space is exhausted (yfinance hourly `=F` capped ~730 days; Coinbase ~12 days).

## Proxy caveat
`validate_strategy`'s `param_stability` is a *proxy* (fold-profitability fraction), not the
literal "±1 std of optimal parameters" from PROMPT_V2.md, because the function only
receives returns + trades, not a parameter grid. The real ±1-std perturbation gate lives in
the H10/H11 runners (`run_h10_intraday_tsmom_pfopt_experiment.py`,
`run_h11_robustness_experiment.py`) as `e2_perturbation`. Do not conflate the two.

`validate_strategy`'s `walkforward_stability` is likewise a *simplified* proxy (first-half
vs second-half ratio), not the literal 5-fold walk-forward metric computed independently
in the H9–H25 runners (`run_h10_intraday_tsmom_pfopt_experiment.py:286`). The runner gate
is unaffected by this fix.

## Latent issue (already fixed in HEAD)
`walk_forward_splits` previously dropped trailing samples when `n_samples % n_splits != 0`
(n=252/5 covers 250/252; n=77/3 covers 75/77). HEAD already absorbs the tail into the last
window (`statistics.py:108-110`): `walk_forward_splits(77, 3)` covers all 77 samples,
`walk_forward_splits(252, 5)` covers all 252. Verified empirically. Nothing to fix; no
certified number changes today (H10's 5148 bars are divisible by 5).

## Stale-prose regression guards (added across two sessions)
`test_experiment_description_matches_pre_registered_grid` in
`tests/test_h22_futures_tsmom_voltarget.py`,
`tests/test_h25_futures_tsmom_pfmargin.py`, and now
`tests/test_h23_crypto_futures_tsmom.py` computes the grid size from the dimension
lists and asserts the `EXPERIMENT_DESC` string contains that combo count (H23 also asserts
all grid dimensions are enumerated). Each fails under its stale prose and passes after the
correction, so the drift class cannot recur silently.

(End of file - total 44 lines)