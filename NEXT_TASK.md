# Next Task

## Status: COMPLETE (this session)

No prior agent handoff task existed (HANDOFF.md said "no bounded task identified"),
so I inspected the repository and selected a bounded, high-value task.

## Task: implement the `min_param_stability` evidence gate

**Demonstrated problem:** `PROMPT_V2.md` lists "Parameter sensitivity: performance stable
within ±1 standard deviation of optimal parameters" as a mandatory success metric, and
`run_baseline.py:72` / `run_experiment.py:75` pass `"min_param_stability": 0.8` into
`validate_strategy`. But `src/qtr/validation/statistics.py:449` only stored it in
`thresholds` and never computed or gated on it — so `all_pass` could be `True` for a
strategy that violated the parameter-sensitivity criterion. Reproduced with a 3-line
script: `validate_strategy(returns, trades, {"min_param_stability": 0.8})` returns a dict
with no `param_stability` key at all.

**Fix:** `statistics.py` now computes `param_stability` as the fraction of 5 walk-forward
test folds whose Sharpe > 0 (1.0 = perfectly stable; 0.8 gate = >=80% of folds
profitable), includes `param_stability_pass` in the `all_pass` conjunction, and documents
the proxy-vs-literal caveat in the code comment. Also added an empty-input guard to
`sharpe_ratio` (was emitting `RuntimeWarning: Mean of empty slice` on the new no-folds
code path).

## Additional work done this session

- Closed the last two src coverage gaps: `statistics.py` 99% → 100% (line 495 `else`
  branch) and `backtest/engine.py` 99% → 100% (line 268 `else` fallback, via a new
  `test_unknown_asset_class_zero_costs`). **src/ coverage is now 100% (912/912 stmts).**
- Full suite: 524 passed (was 521), 0 warnings (was 1 scipy RuntimeWarning) — verified
  with `python -m pytest -W error -q`. Lint/format clean. Workflow scripts pass
  `bash -n` and the progress-helper regression test.

## Environment note

`qtr` was not installed in the environment, causing `ModuleNotFoundError` at test
collection. Fixed with `pip install -e .` from the repo root. If a future session hits
the same error, run that command first.

## Success criteria — all met
- `min_param_stability` is now computed and enforced in `validate_strategy`.  [done]
- A regression test fails without the fix (KeyError), proving the gate is pinned.  [done]
- `all_pass` now includes the parameter-sensitivity gate.  [done]
- Lint/format clean.  [done]
- Full suite: 524 passed, 0 warnings, no regressions.  [done]
- src/ coverage: 100%.  [done]

## Next task (beyond free-data scope)

No bounded task remains within the free-data constraint. Per FINAL_REPORT.md §Next
Task, the precise next task requires **paid hourly futures data** to widen the OOS
window enough for the PF and Sharpe bootstrap CIs to clear their gates with margin
(H10/H22/H25 are PASS but PF-margin is CI-fragile: H13 CI [1.190, 1.425], H25 Robustness
CI [1.2049, 1.4425], P(PF≥1.3)≈0.5–0.62). Do not run further hypotheses on free data —
that repeats the H1–H9/H19–H23 pattern (OOS Sharpe 0.2–0.8, PF-CI-fragile).

## Proxy caveat
`validate_strategy`'s `param_stability` is a *proxy* (fold-profitability fraction), not the
literal "±1 std of optimal parameters" from PROMPT_V2.md, because the function only
receives returns + trades, not a parameter grid. The real ±1-std perturbation gate lives in
the H10/H11 runners (`run_h10_intraday_tsmom_pfopt_experiment.py`,
`run_h11_robustness_experiment.py`) as `e2_perturbation`. Do not conflate the two.

(End of file - total 75 lines)