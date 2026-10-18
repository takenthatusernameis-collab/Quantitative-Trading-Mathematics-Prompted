# Next Task

## Status: COMPLETE (this session)

No prior agent assignment remained (the three bounded tasks from prior sessions were already committed and verified). I inspected the repository independently and confirmed the baseline is fully verified, then selected and completed one additional bounded, high-value task:
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
- Full suite: 528 passed, 0 warnings, no regressions.  [done]
- src/ coverage: 100%.  [done]

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

## Latent issue (not fixed this session)
`walk_forward_splits` drops trailing samples when `n_samples % n_splits != 0` (n=252/5
covers 250/252; n=77/3 covers 75/77). Runners using it for fold Sharpes silently ignore the
tail. No certified number changes today (H10's 5148 bars are divisible by 5). Fixing it
requires choosing a split policy (drop-tail vs distribute-remainder) and re-running the
affected experiments — out of scope for a free-data session.

(End of file - total 117 lines)