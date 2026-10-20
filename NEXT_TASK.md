# Next Task — all runners covered (H37 → remaining-runner extension complete)

## State

**H35, H36, H37 and the remaining-runner extension are COMPLETE.** Every
`run_*.py` in the repository (32 files) is now in scope of
`tests/test_runner_causality_inventory.py`:

- H37's 13 runners: `run_h9/h10/h12/h16/h18/h19/h20/h21/h22/h23/h25/h27/h29`.
- `run_ts_momentum_experiment.py` and `run_cs_momentum_experiment.py` (the two
  vol-scaled momentum families certified CAUSAL by H29).
- The H38 families: `run_ddcv_experiment.py`, `run_futures_tsmom_experiment.py`,
  `run_h6_vix_ddcv_experiment.py`, `run_h7_intraday_tsmom_experiment.py`,
  `run_h8_rolladjusted_tsmom_experiment.py`, `run_regime_gated_momentum_experiment.py`,
  `run_h11_robustness_experiment.py`, `run_h17_vrp_experiment.py`.
- This session: `run_experiment.py`, `run_baseline.py`, `run_param_sweep.py`,
  `run_alternatives.py`, `run_h13_oos_deflation_pf_audit.py`,
  `run_h14_pf_margin_selection_audit.py`, `run_h25_pf_robustness.py`,
  `run_h26_sharpe_scale_audit.py`, `run_h28_causal_recertification.py`.

All 48 functions of the nine runners added this session are classified
`static` with a written argument: none of them builds a position series inline
-- each composes imported frozen pipelines (H9/H10/H11) or audits committed
artifacts -- so no probe case is needed for any of them (the static check plus
written argument is the sanctioned alternative). `run_h26`'s single
`resample("1D")` collapse site (in `audit_artifact`) is pinned in
`RESAMPLE_SITES`. `KNOWN_LOOKAHEAD_CASES` and `INHERITED_LOOKAHEAD` are
unchanged.

This session also fixed one clean deterministic blocker: the engine's
annualized return raised `RuntimeWarning: invalid value encountered in scalar
power` once equity crossed zero in the dense sweep, which `-W error` turned
into a hard failure. It is now guarded
(`src/qtr/backtest/engine.py:317`: non-positive equity base -> -1.0);
`src/qtr/backtest/engine.py` stays at **100%** coverage and the new branch is
exercised by the existing dense-sweep tests. Additionally,
`tests/test_data_fetcher.py` now covers the `fetch_sp500_constituents(date=...)`
`ValueError` branch, bringing all of `src/qtr` to **100%** coverage
(1014/1014 statements) -- the footgun from the earlier record (silently
returning the current constituent list) is already closed in code: a historical
`date` raises loudly instead.

## Predictor-timing audit (H29 CAUSAL families)

Every predictor of the families H29 certified CAUSAL is probed clean
(`regime_labels`, `vol_scaled_tsmom_signals`, `regime_factor_series`, ... across
the H3/H4/H5/H6/H7/H8 runners). The runners added this session call only pinned
constructors: `h14`'s grid rebuild inherits the pinned `build_hourly_target`
look-ahead (detection unchanged), `h27`'s causal collapse is probed day-aligned,
and `h28` reuses the probed-causal collapse via monkeypatch. **No same-bar-close
predictor was found in any remaining runner**, so the predictor-timing class
(H37's P3: `vix_regime`) has no new instance; every disclosure remains bounded
the way P3 is (checked against the committed artifacts).

## What was actually verified (this session)

- `python -m pytest -q -W error` → **1102 passed, 1 skipped** (the skip is the
  pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → deviations only on
  pre-existing lines untouched by this session (ruff 0.17.1 style drift on
  lines this session did not modify); `ruff check` passes and every line this
  session added is format-clean.
- `src/qtr` coverage **100%** (1014 statements, 0 missed), including
  `engine.py` and `data/fetcher.py`.
- No published artifact, gate threshold, verdict, certified number or
  published row was modified; no grid was re-run; no hypothesis was added.
- `git diff` on the runners is limited to `src/qtr/backtest/engine.py` (the
  guard) plus the two test files.

## Remaining items (disclosures, not rewrites)

- `qtr/backtest/engine.py`: `metrics["total_return"]` excludes the first bar's
  return while `annualized_return` counts it (~a few bps; the values live in
  published artifacts, so this is a disclosure, not a rewrite).
- Nothing else: the `fetch_sp500_constituents(date=...)` footgun is already
  fixed in code (raises `ValueError`) and now tested.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be
  modified; no grid may be re-run; no new hypothesis (the H1–H30 space is
  exhausted; the certified families H10/H11/H12/H22/H25 are frozen).
- `python -m pytest -q -W error` and `ruff check src tests run_*.py` must pass
  from a bare clone (no install step); keep `src/qtr` at 100% coverage; re-run
  `tests/test_runner_causality_inventory.py` after any change in a `run_*.py`
  and `tests/test_causality_invariant.py` after any change under `src/qtr`.

## Next task

**None for the point-in-time invariant:** every `run_*.py` is covered, every
module-level function is classified, every known look-ahead is pinned, and the
suite is green. If a future session wants one bounded item, it is the engine's
`metrics["total_return"]` inconsistency disclosed above (a few bps; values in
published artifacts -- touch only if the record is being rewritten, which the
carried-forward constraints currently forbid).
