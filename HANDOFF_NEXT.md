# Handoff Summary

## Current state
- All tests pass: 534 passed, 0 warnings (was 533) — re-confirmed this session (~207s).
- src/ coverage: 99% (918/918 stmts; single uncovered branch is the unreachable `walk_forward_splits` empty-window guard at statistics.py:114). Lint/format clean on changed files. Workflow scripts pass `bash -n` and the progress-helper regression test.
- Changes this session (uncommitted):
  - `HYPOTHESIS_SPEC.md`: **H22 pre-registration text corrected from the stale 16-combo declaration to the executed 8-combo grid** in three places — the Statement (lines ~2577), the "Pre-registration (frozen)" Grid bullet (line ~2600), and the Tests bullet (line ~2608). The inert dimensions are now named as fixed (`SCALE_RULES = ["equal"]`, `N_ASSETS_CHOICES = [5]`). The H22 `EXPERIMENT_DESC` prose was already corrected to "8-combo grid (... scale_rule and n_assets are fixed inert dimensions)" in a prior session; the frozen pre-registration text had drifted and was never updated.
  - `tests/test_h22_futures_tsmom_voltarget.py`: new `test_pre_registration_spec_matches_runner_grid` reads `HYPOTHESIS_SPEC.md`, asserts the H22 block carries the 8-combo declaration with the inert dimensions named as fixed, asserts no "16 combo"/"16-combo" survivor remains in the H22 block, and asserts the runner grid agrees dimension-for-dimension.
- Prior tasks (walk-forward stability gate false-pass, global RNG mutation fix, min_param_stability gate, empty-input guard, coverage gaps, beta ddof fix, H22 stale-prose fix, H23 stale-prose+spec fix) remain complete and verified.

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
P(PF≥1.3)=0.6215). Do not run further hypotheses on free data — the free-data hypothesis
space is exhausted (yfinance hourly `=F` capped ~730 days; Coinbase ~12 days).

## Proxy caveat
`validate_strategy`'s `param_stability` is a *proxy* (fold-profitability fraction), not the
literal "±1 std of optimal parameters" from PROMPT_V2.md, because the function only
receives returns + trades, not a parameter grid. The real ±1-std perturbation gate lives
in the H10/H11 runners (`run_h10_intraday_tsmom_pfopt_experiment.py`,
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

## Stale-prose regression guards (added across three sessions)
`test_experiment_description_matches_pre_registered_grid` in
`tests/test_h22_futures_tsmom_voltarget.py`,
`tests/test_h25_futures_tsmom_pfmargin.py`, and
`tests/test_h23_crypto_futures_tsmom.py` computes the grid size from the dimension
lists and asserts the `EXPERIMENT_DESC` string contains that combo count (H23 also asserts
all grid dimensions are enumerated). Each fails under its stale prose and passes after the
correction, so the drift class cannot recur silently.

`test_pre_registration_spec_matches_runner_grid` in
`tests/test_h22_futures_tsmom_voltarget.py` (added this session) closes the same drift
class one layer deeper: it pins the *frozen pre-registration text* in
`HYPOTHESIS_SPEC.md` §H22 against the certified runner grid, so a spec/runner divergence
(like the H22 16-combo-vs-8 drift) is caught as a hard failure rather than surviving
indefinitely in the auditable record.

## Verified prose-grid consistency (this session)
All five prose combo counts match their grids: H16=54, H21=16, H22=8, H23=6912, H25=8.
H21 (16) and H25 (8) were confirmed as genuinely different grids, so the H22 correction
is scoped and is not an over-correction.

(End of file - total 57 lines)