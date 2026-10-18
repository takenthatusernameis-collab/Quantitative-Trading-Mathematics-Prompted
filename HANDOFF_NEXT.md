# Handoff Summary

## Current state
- All tests pass: 525 passed, 0 warnings (was 524) — re-confirmed this session (265s).
- src/ coverage: 100% (914/914 stmts). Lint/format clean. Workflow scripts pass `bash -n` and the progress-helper regression test.
- Changes this session:
  - `src/qtr/validation/statistics.py`:
    - **Fixed a false-pass in the walk-forward stability gate.** The ratio
      `sharpe_second / sharpe_first` is sign-sensitive: when BOTH halves are
      losing (e.g. Sharpe −18.4 / −14.0) the raw ratio is 0.76 and **passed**
      the 0.7 gate — the opposite of "stable". Now `wf_stability = 0.0`
      unless both halves are profitable (`sharpe_first > 0 and
      sharpe_second > 0`).
  - `tests/test_statistics.py`: added `test_walkforward_passes_with_both_halves_losing` —
    a both-halves-negative series (Sharpe −1.0 / −1.0, raw ratio ~1.0) must
    yield `walkforward_stability == 0.0` and `walkforward_pass is False`.
- Prior tasks (min_param_stability gate, empty-input guard, coverage gaps) remain
  complete and verified.

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

(End of file - total 43 lines)