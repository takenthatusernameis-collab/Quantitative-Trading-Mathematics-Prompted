# Next Task

## Status: COMPLETE (this session)

No prior agent assignment remained (the H22 pre-registration fix from the prior session was already committed and verified; the working tree was clean). I inspected the repository independently, re-ran the full verification suite, and selected one bounded, high-value task:

## Task 8 (this session): fix stale/absent combo-count prose in H17/H19/H20 `EXPERIMENT_DESC`

**Demonstrated problem:** three certified runners carried human-readable descriptions with **no combo count at all**:
- `run_h17_vrp_experiment.py:52` — `"H17: Term-structure-gated, vol-targeted long SVXY (VRP harvesting)"` while the pre-registered grid is **60 combos** (`GATE_THRESHES × VOL_WINDOWS × TARGET_VOLS × MAX_POSS`).
- `run_h19_volume_predictive_experiment.py:47-50` — `"H19: Volume-predictive return decomposition (anticipated vs unanticipated volume surprise)"` while the pre-registered grid is **9 combos** (`VOLUME_DECOMP_METHODS × THRESHOLD_TYPES`).
- `run_h20_signed_volume_experiment.py:55-57` — `"H20: Volume-sign (buy/sell-initiated) decomposition + order-flow imbalance"` while the pre-registered grid is **36 combos** (`SIGN_RULES × TARGET_VOLS × MAX_POSITIONS × IMBALANCE_LAGS`).

This is the **same drift class** fixed four prior sessions (H22 prose, H23 prose+spec, H25 prose, H22 pre-registration). It survived here because those three runners had no `test_experiment_description_matches_pre_registered_grid` — only their grid dimensions were pinned, so the prose was invisible to the test suite. The string is logged verbatim into `.experiments/experiments.jsonl` (verified — 3 H17, 5 H19 and 5 H20 records carry the bare prose with no combo count) and is the first prose an auditor or next operator reads.

**Fix:** each `EXPERIMENT_DESC` corrected to carry its combo count and enumerate its grid dimensions — H17 "60-combo grid (gate_thresh x vol_window x target_vol x max_pos)", H19 "9-combo grid (volume_decomp_method x threshold_type)", H20 "36-combo grid (sign_rule x target_vol x max_pos x imbalance_lag)" — each Val-selected, Test-protected. Verified the H16 (54), H21 (16), H22 (8), H23 (6912) and H25 (8) descriptions were already correct, so the correction is scoped to H17/H19/H20 and is not an over-correction.

**Regression tests (all three fail without the fix, pass with it):**
- `tests/test_h17_vrp.py::TestPreRegistration::test_experiment_description_matches_pre_registered_grid`
- `tests/test_h19_volume_predictive.py::TestPreRegistration::test_experiment_description_matches_pre_registered_grid`
- `tests/test_h20_signed_volume.py::TestPreRegistration::test_experiment_description_matches_pre_registered_grid`

Each computes the grid size from the dimension lists, asserts the `EXPERIMENT_DESC` string contains that combo count, and asserts every grid dimension is enumerated in the prose.

## Verified
- `python -m pytest -q` → 537 passed (was 534), ~207s
- `python -m pytest -W error -q` → 537 passed, 0 warnings
- `python -m pytest --cov=qtr --cov-report=term-missing` → 99% on src (918 stmts; single miss is the unreachable `walk_forward_splits` empty-window guard at statistics.py:114)
- `python -m ruff check` + `python -m ruff format --check` on the six changed files → clean
- `bash -n .github/scripts/*.sh` → OK
- `bash .github/scripts/test_kilo_progress.sh` → OK
- All three new regression tests fail under the reverted stale prose (reproduced the assertion failures) and pass with the fix.
- H17/H19/H20 artifact regression tests still pass — the fix is prose-only and does not touch grid, selection, gates, or artifacts.

## Task 7 (prior session): fix stale H22 pre-registration text in `HYPOTHESIS_SPEC.md`

**Demonstrated problem:** the frozen H22 pre-registration in `HYPOTHESIS_SPEC.md` declared a **16-combo** grid (`SCALE_RULES = ["equal","inverse_vol"]`, `N_ASSETS_CHOICES = [3,5]`) in three places — the Statement (lines ~2577), the "Pre-registration (frozen)" Grid bullet (line ~2600), and the Tests bullet (line ~2608) — but the certified runner `run_h22_futures_tsmom_voltarget.py:80-89` executes an **8-combo** grid (`SCALE_RULES = ["equal"]`, `N_ASSETS_CHOICES = [5]`; the inert dimensions were collapsed to singletons). The `EXPERIMENT_DESC` prose was already corrected to "8-combo grid (... scale_rule and n_assets are fixed inert dimensions)" in a prior session, but the frozen pre-registration text was never updated. This is the **same drift class** fixed three prior sessions (H22 prose, H23 prose+spec, H25 prose); here it survived in the frozen pre-registration because no test pins the *spec text* to the runner grid — only the runner's own constants were pinned, so the drift was invisible to the test suite. The pre-registration is the auditable record an auditor reads first.

**Fix:** corrected all three H22 declarations to the executed 8-combo grid, naming the inert dimensions as fixed (`SCALE_RULES = ["equal"]`, `N_ASSETS_CHOICES = [5]`). Verified the H21 grid is genuinely 16 combos and H25 is genuinely 8, so the correction is scoped to H22 and is not an over-correction.

**Regression test (fails without the fix, passes with it):**
- `tests/test_h22_futures_tsmom_voltarget.py::test_pre_registration_spec_matches_runner_grid`

It reads `HYPOTHESIS_SPEC.md`, asserts the H22 block carries the 8-combo declaration with the inert dimensions named as fixed, asserts no "16 combo"/"16-combo" survivor remains in the H22 block, and asserts the runner grid agrees dimension-for-dimension.

## Task 6 (this session): fix stale `EXPERIMENT_DESC` prose in H23

**Demonstrated problem:** `run_h23_crypto_futures_tsmom.py:37` declared
`EXPERIMENT_DESC = "H23: Intraday TSMOM on crypto perpetual futures (Coinbase) — generalization of the H10 edge. Tests whether the intraday futures TSMOM mechanism generalizes to crypto markets. Val-selected, Test-protected, gates per H23 pre-registration."` — **no combo count at all**, while the pre-registration text (`HYPOTHESIS_SPEC.md:2626`) and the test docstring both claimed a "2304-combo grid". The actual listed parameters yield **6912** combos (4×3×1×4×4×4×3×3). The pre-registration arithmetic (2304) was simply wrong; the listed dimensions were always 6912, and the code followed the listed dimensions. This is a **certification-integrity defect**, not cosmetic: the string is logged verbatim into `.experiments/experiments.jsonl` (verified — 9 H23 records carry the stale/absent combo-count prose) and is the first prose an auditor or next operator reads. The H23 test suite pinned the *grid dimensions* (`test_grid_is_the_pre_registered_2304_combos`, which correctly asserts `== 6912`) but never pinned the *prose describing them*, so the drift was invisible to the test suite.

**Fix:** `EXPERIMENT_DESC` corrected to "6912-combo grid (smooth_span x vol_window_long x regime_scaling x min_trade_interval x trailing_mult x max_hold_bars x vol_limit_mult x vol_floor_fraction), Val-selected, Test-protected, gates per H23 pre-registration." Also corrected the same drift class in the H23 test docstring (2304 → 6912) and in `HYPOTHESIS_SPEC.md:2626`.

**Regression test (fails without the fix, passes with it):**
- `tests/test_h23_crypto_futures_tsmom.py::test_experiment_description_matches_pre_registered_grid`

It computes the grid size from the 8 dimension lists, asserts the `EXPERIMENT_DESC` string contains that combo count, and asserts all 8 grid dimensions are enumerated in the prose.

## Verified
- `python -m pytest -q` → 533 passed (was 532), ~199s
- `python -m pytest -W error -q` → 533 passed, 0 warnings
- `python -m pytest --cov=qtr --cov-report=term-missing` → 99% on src (918 stmts; single miss is the unreachable `walk_forward_splits` empty-window guard at statistics.py:114)
- `python -m ruff check` + `ruff format --check` on the two changed files → clean
- `bash -n .github/scripts/*.sh` → OK
- `bash .github/scripts/test_kilo_progress.sh` → OK
- H23 artifact regression tests (25) still pass — the fix is prose-only and does not touch grid, selection, gates, or artifacts.

## Task 5 (this session): fix stale `EXPERIMENT_DESC` prose in H22

**Demonstrated problem:** `run_h22_futures_tsmom_voltarget.py:60` declared
`EXPERIMENT_DESC = "H22: Vol-targeting expansion test on H21 basket; 16-combo grid ..."`
while the actual pre-registered grid is **8 combos** — `TARGET_VOLS=[0.50,0.75,1.0,1.5]` ×
`MAX_POSITIONS=[0.5,1.0]` × `SCALE_RULES=["equal"]` (fixed) × `N_ASSETS_CHOICES=[5]` (fixed).
The grid shrank from H21's 16 (2×2×2×2) to H22's 8 (4×2×1×1) by collapsing the inert
dimensions to singletons, but the human-readable description was never updated. This is a
certification-integrity defect, not cosmetic: the string is logged verbatim into
`.experiments/experiments.jsonl` (verified — 5 H22 records carry the stale "16-combo"
string) and is the first prose an auditor or next operator reads. The H22 regression tests
pinned the *grid dimensions* (`test_grid_is_the_pre_registered_8_combos`) but never the
*prose describing them*, so the drift was invisible to the test suite.

**Fix:** `EXPERIMENT_DESC` corrected to "8-combo grid (target_vol x max_pos; scale_rule and
n_assets are fixed inert dimensions)". H25's prose was already correct (8-combo); no source
change there.

**Regression tests (both fail without the fix, pass with it):**
- `tests/test_h22_futures_tsmom_voltarget.py::test_experiment_description_matches_pre_registered_grid`
- `tests/test_h25_futures_tsmom_pfmargin.py::test_experiment_description_matches_pre_registered_grid`

Each computes the grid size from the dimension lists and asserts the `EXPERIMENT_DESC`
string contains that combo count, so the drift class cannot recur silently.

## Verified
- `python -m pytest -q` → 532 passed (was 530), ~199s
- `python -m pytest -W error -q` → 532 passed, 0 warnings
- `python -m pytest --cov=qtr --cov-report=term-missing` → 99% on src (918 stmts; single miss is the unreachable `walk_forward_splits` empty-window guard at statistics.py:114)
- `python -m ruff check` + `ruff format --check` on the four changed files → clean
- `bash -n .github/scripts/*.sh` → OK
- `bash .github/scripts/test_kilo_progress.sh` → OK
- H22/H25 artifact regression tests (46) still pass — the fix is prose-only and does not touch grid, selection, gates, or artifacts.

## Prior tasks (already committed and verified)
- `python -m pytest -q` → 528 passed, ~213s
- `python -m pytest -W error -q` → 528 passed, 0 warnings
- `python -m pytest --cov=qtr --cov-report=term-missing` → 100% on every src module (915/915 stmts)
- `python -m ruff check src tests run_*.py` → clean
- `python -m ruff format --check` → 83 files formatted
- `bash -n .github/scripts/*.sh` → OK
- `bash .github/scripts/test_kilo_progress.sh` → OK
- No TODOs/FIXMEs in `src/` or `tests/`

## Prior tasks (already committed and verified)

### Task 1: fix the walk-forward stability gate false-pass
**Demonstrated problem:** `validate_strategy`'s walk-forward stability gate could
**pass for a strategy that loses in both halves**. The metric is
`wf_stability = sharpe_second / sharpe_first` (statistics.py:481). A ratio of two
negatives is positive, so a strategy with Sharpe −18.4 in half 1 and −14.0 in half 2
scores 0.76 and **passes** the default 0.7 gate — the opposite of "stable".

**Fix:** guard the ratio on the sign of both halves. `wf_stability = 0.0` unless
both `sharpe_first > 0` and `sharpe_second > 0`.

### Task 2: fix global RNG state mutation in `bootstrap_confidence_interval`
**Demonstrated problem:** `bootstrap_confidence_interval` (statistics.py:31) called
`np.random.seed(random_state)`, which mutates the **global** numpy RNG.

**Fix:** replaced with a local `rng = np.random.default_rng(random_state)`.

### Task 3: guard `validate_strategy` against empty returns input
**Demonstrated problem:** `validate_strategy` raised `ZeroDivisionError` when
called with an empty returns series, at `ann_return = (1 + total_return) ** (252 / len(returns)) - 1`.

**Fix:** added an early guard returning a safe all-fail result.

## Task 4 (this session): fix `compare_to_benchmark` beta estimator ddof inconsistency

**Demonstrated problem:** `compare_to_benchmark` (statistics.py:371) computed
`beta = np.cov(strat, bench)[0, 1] / np.var(bench)`. `np.cov` defaults to `ddof=1`
(sample) while `np.var` defaults to `ddof=0` (population), so the ratio is inflated
by exactly `n/(n-1)` relative to the true OLS regression slope. For n=400 that is
+0.25% on every beta. `compare_to_benchmark` feeds the certified H10 pipeline
(`run_h10_intraday_tsmom_pfopt_experiment.py:315`), whose `information_ratio` and
`benchmark_p_value` gates depend on `beta` (via `alpha`). The existing test
`test_beta_is_covariance_ratio` actually encoded the buggy formula, pinning the
defect rather than catching it.

**Fix:** `beta = np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench, ddof=1)`. With
consistent ddof=1, beta is the OLS slope and alpha reduces to the OLS intercept net
of the risk-free term (standard CAPM alpha).

**Regression tests:**
- `test_beta_is_ols_slope` (renamed from `test_beta_is_covariance_ratio`): asserts
  beta against `np.polyfit(bench, strat, 1)[0]` and `scipy.stats.linregress(bench, strat).slope`.
- `test_beta_matches_ols_not_mixed_ddof`: asserts beta equals the OLS slope, differs
  from the mixed-ddof value, and is smaller in magnitude when beta != 0.

Both fail without the fix (reproduced the inflated beta) and pass with it.

## Success criteria — all met
- `compare_to_benchmark` beta now equals the OLS regression slope.  [done]
- A regression test fails without the fix, proving the estimator is pinned.  [done]
- Lint/format clean.  [done]
- Full suite: 537 passed, 0 warnings, no regressions.  [done]
- src/ coverage: 99%.  [done]
- H22 `EXPERIMENT_DESC` matches the pre-registered 8-combo grid.  [done]
- A regression test fails under the stale "16-combo" prose.  [done]
- H23 `EXPERIMENT_DESC` matches the pre-registered 6912-combo grid.  [done]
- A regression test fails under the stale/absent combo-count prose.  [done]
- H17 `EXPERIMENT_DESC` matches the pre-registered 60-combo grid.  [done]
- H19 `EXPERIMENT_DESC` matches the pre-registered 9-combo grid.  [done]
- H20 `EXPERIMENT_DESC` matches the pre-registered 36-combo grid.  [done]
- Three regression tests fail under the stale/absent combo-count prose.  [done]
- All eight prose combo counts verified against their grids: H16=54, H17=60, H19=9,
  H20=36, H21=16, H22=8, H23=6912, H25=8 — all match.  [done]

## Next task (beyond free-data scope)

No bounded task remains within the free-data constraint. Per FINAL_REPORT.md §Next
Task, the precise next task requires **paid hourly futures data** to widen the OOS
window enough for the PF and Sharpe bootstrap CIs to clear their gates with margin
(H10/H22/H25 are PASS but PF-margin is CI-fragile: H13 CI [1.190, 1.425],
H25 Robustness CI [1.2049, 1.4425], P(PF≥1.3)≈0.5–0.62).

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

(End of file - total 117 lines)