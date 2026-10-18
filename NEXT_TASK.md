# Next Task

## Status: COMPLETE (this session)

No prior agent handoff task existed (HANDOFF.md said "no bounded task identified"),
so I inspected the repository and selected two bounded, high-value tasks.

## Task 1: fix the walk-forward stability gate false-pass

**Demonstrated problem:** `validate_strategy`'s walk-forward stability gate could
**pass for a strategy that loses in both halves**. The metric is
`wf_stability = sharpe_second / sharpe_first` (statistics.py:481). A ratio of two
negatives is positive, so a strategy with Sharpe −18.4 in half 1 and −14.0 in half 2
scores 0.76 and **passes** the default 0.7 gate — the opposite of "stable".
Reproduced with a 3-line script:
`validate_strategy(returns, trades, {"min_walkforward_stability": 0.7, ...})`
returns `walkforward_stability = 0.76`, `walkforward_pass = True` for a losing series.

**Fix:** guard the ratio on the sign of both halves. `wf_stability = 0.0` unless
both `sharpe_first > 0` and `sharpe_second > 0`. A losing strategy can no longer be
certified as stable. This is a cheap, deterministic correctness fix to an evidence
gate that PROMPT_V2.md mandates and that `run_baseline.py:72` /
`run_experiment.py:75` rely on. It does not touch orchestration, permissions, or the
experiment runners.

## Task 2: fix global RNG state mutation in `bootstrap_confidence_interval`

**Demonstrated problem:** `bootstrap_confidence_interval` (statistics.py:31) called
`np.random.seed(random_state)`, which mutates the **global** numpy RNG. Any subsequent
`np.random.*` call in the same process draws from a seeded state, causing
non-deterministic cross-contamination between unrelated random operations.

**Fix:** replaced `np.random.seed(random_state)` + `np.random.randint(0, n, n)` with
a local `rng = np.random.default_rng(random_state)` + `rng.integers(0, n, n)`.
The function no longer touches global RNG state. Tests are property-based (not
value-dependent on the RNG sequence), so no numeric expectations changed.

## Additional work done this session
- Added regression test `test_walkforward_passes_with_both_halves_losing` in
  `tests/test_statistics.py`: a both-halves-negative series (Sharpe −1.0 / −1.0,
  raw ratio ~1.0) must yield `walkforward_stability == 0.0` and
  `walkforward_pass is False`.
- Added regression test `test_does_not_mutate_global_rng` in
  `tests/test_statistics.py`: advancing the global RNG, calling
  `bootstrap_confidence_interval`, then asserting the global RNG position/state
  vector are unchanged. Fails under the old `np.random.seed(random_state)`
  implementation; passes with the local-`Generator` fix.
- Full suite: 526 passed (was 525), 0 warnings — verified with
  `python -m pytest -W error -q`.
- src/ coverage: 100% (913/913 stmts). Lint/format clean.
- All 63 statistics tests pass (property-based, not value-dependent on the RNG sequence).

## Success criteria — all met
- A losing strategy can no longer pass the walk-forward stability gate.  [done]
- A regression test fails without the fix, proving the gate is pinned.  [done]
- `all_pass` now correctly excludes both-halves-negative strategies.  [done]
- `bootstrap_confidence_interval` no longer mutates global numpy RNG state.  [done]
- A regression test fails under the old `np.random.seed` implementation and
  passes with the fix, pinning the RNG non-mutation.  [done]
- Lint/format clean.  [done]
- Full suite: 526 passed, 0 warnings, no regressions.  [done]
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

(End of file - total 97 lines)