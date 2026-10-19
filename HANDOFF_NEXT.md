# Handoff Summary

## Current state
- All tests pass: **586 passed, 0 warnings** (~3:28). Full suite re-confirmed this session.
- src/ coverage: 99% (single uncovered branch is the unreachable `walk_forward_splits` empty-window guard at statistics.py:114, pre-existing). Lint/format clean on `src tests run_*.py`. Workflow scripts pass `bash -n` and the progress-helper regression test.
- **H26 (this session): Sharpe annualization-scale audit — COMPLETE.** The published "OOS Sharpe" is a **√252-per-bar** metric, so for the intraday (1h) families it is *not* an annualized Sharpe: it understates the annualized value by 2.55× (repo's own `√(252·6.5)` vol-target convention) to 4.76× (empirical calendar). Certified family: H10 1.276→3.253, H22 1.372→3.499, H25 1.324→3.375. The daily families were already correctly annualized (control ratio 0.9995) and are unaffected. **No verdict/gate/threshold/certified number changed** — the mis-scaling is conservative. The "Sharpe CI-fragile" caveat was a **scale artifact** (H25 CI [0.8834, 1.7506] → [2.2521, 4.4633], P(Sharpe≥1.0) 0.9275 → 1.0000); the **PF margin fragility stands** (scale-invariant) and is now the binding constraint together with the 730-day sample. See `FINAL_REPORT.md` §H26 detail, `HYPOTHESIS_SPEC.md` §H26 (pre-registration + measure log), `NEXT_TASK.md`.
- `qtr` must be importable — run `pip install -e .` from the repo root if `ModuleNotFoundError: No module named 'qtr'` appears at collection time.

## Next agent actions
If assigned a new task, verify with:
`python -m pytest -q`, `python -m pytest -W error -q`,
`python -m pytest --cov=qtr --cov-report=term-missing`,
`python -m ruff check src tests run_*.py`, `python -m ruff format --check`,
plus `bash -n .github/scripts/*.sh` and `bash .github/scripts/test_kilo_progress.sh`.
Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.

## Highest-value next task (free data, bounded, verifiable)
**Audit the *level* of the certified intraday P&L.** The scale correction implies an
annualized Sharpe of 3.25–6.53 for the certified family versus ≈0.5–1.5 for published
real-world futures TSMOM strategies — either the sample is extraordinary or the
backtest has a level/scale bug that would invalidate the certified family. Recompute
the per-bar dollar P&L and the cost drag from the committed H10/H25
`prices`/`positions`/`trades` artifacts using the engine's contract maths, check the
vol-target coherence (15% target vs ≈10.5% realized calendar-annualized vol at ≈32%
calendar-annualized return), pre-register the `LEVEL_CONFIRMED` / `LEVEL_DEFECT` rule
before executing, and pin the outcome with a new test file. Full scope, constraints and
evidence: `NEXT_TASK.md`.

## Documented next task (requires paid data — outside a free-data session)
Per FINAL_REPORT.md §Next Task: widen the OOS window with **paid hourly futures data**
so the **PF** bootstrap CI clears its gate with margin. H10/H22/H25 are PASS but the
PF-margin is CI-fragile (H13 CI [1.190, 1.425]; H25 Robustness CI [1.2049, 1.4425],
P(PF≥1.3)=0.6215) — that fragility is scale-invariant and is the binding constraint
(the *Sharpe* CI fragility was withdrawn by H26 as a scale artifact). Do not run further
hypotheses on free data — the free-data hypothesis space is exhausted (yfinance hourly
`=F` capped ~730 days; Coinbase ~12 days).


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

## Stale-prose regression guards (added across four sessions)
`test_experiment_description_matches_pre_registered_grid` in
`tests/test_h17_vrp.py`, `tests/test_h19_volume_predictive.py`,
`tests/test_h20_signed_volume.py`, `tests/test_h22_futures_tsmom_voltarget.py`,
`tests/test_h23_crypto_futures_tsmom.py`, and
`tests/test_h25_futures_tsmom_pfmargin.py` computes the grid size from the dimension
lists and asserts the `EXPERIMENT_DESC` string contains that combo count (H23 also asserts
all grid dimensions are enumerated). Each fails under its stale prose and passes after the
correction, so the drift class cannot recur silently.

`test_pre_registration_spec_matches_runner_grid` in
`tests/test_h22_futures_tsmom_voltarget.py` closes the same drift class one layer deeper:
it pins the *frozen pre-registration text* in `HYPOTHESIS_SPEC.md` §H22 against the certified
runner grid, so a spec/runner divergence (like the H22 16-combo-vs-8 drift) is caught as a
hard failure rather than surviving indefinitely in the auditable record.

## Reproducibility-marker fix (this session)
`test_git_dirty_detects_untracked_artifacts` in `tests/test_experiment_tracker.py` closes
a blind spot in the `git_dirty` reproducibility flag. The previous probe
(`git diff --quiet`) only inspects *tracked* working-tree changes, so an experiment that
wrote a new artifact into an untracked directory (e.g.
`.experiments/artifacts/<exp_id>/`) would be stamped `git_dirty=False` even though the
artifact was never committed. The corrected probe (`git status --porcelain`, dirty iff
non-empty output) reports untracked files (`??` prefix) as well as modified/deleted ones.
The test builds a real clean git repo, asserts `dirty is False`, writes an untracked file,
asserts `dirty is True`, then writes a modified tracked file and asserts `dirty is True`
again. It fails under the reverted buggy probe and passes with the fix.

## H26 drift guards (added this session)
`tests/test_h26_sharpe_scale_audit.py` pins the *scale convention* of the published
Sharpe so the defect class cannot recur silently:

- `test_published_sharpe_is_the_sqrt252_per_bar_metric` — for every audited artifact
  the published number is exactly the per-bar Sharpe × `√252`, and is **not** equal to
  the empirical-calendar annualized value (the assertion fails if the metric is ever
  relabelled as "annualized" without a scale change).
- `test_ci_scales_linearly` — the bootstrap CI at scale `k` is exactly `k ×` the
  per-bar CI, while `test_gate_fraction_is_recomputed_not_rescaled` pins that
  `P(Sharpe ≥ 1.0)` is *recomputed* per scale (0.9275 → 1.0000), not rescaled.
- `test_sharpe_ci_fragility_is_a_scale_artifact` — the "Sharpe CI-fragile" caveat is
  pinned as a scale artifact (CI LB < 1.0 as published, > 1.0 on the repo's own
  annualization convention) for H10/H22/H25.
- `test_h25_as_published_ci_matches_published_robustness_audit` — the audit
  re-derives the *committed* `pf_robustness` CI bit-for-bit, so the audit and the
  record cannot drift apart.
- `test_pf_gate_window_defect` / `test_audited_families_pf_window_is_oos` — pin that
  H9's published profit factor is the **full-sample** PF while H10/H21/H22/H25 are
  OOS-window, i.e. the PF-gate window defect class is detected.
- `test_sharpe_convention_drift` — pins H9's *sample*-std (ddof=1) convention against
  the *population*-std (ddof=0) convention used by H10 and later.
- `TestNegativeGuards` — each guard fails if the scale correction, the
  frequency inference (`bars_per_year`) or the PF-window diagnosis is undone.

New library helpers `bars_per_year(index)` / `annualized_sharpe(returns, index)` infer
the annualization multiplier from the bar timestamps; use `annualized_sharpe` whenever a
genuinely *annualized* Sharpe is wanted. The legacy `sharpe_ratio(...)` default remains
the frozen certification metric and must not be relabelled as "annualized" in any report.

## Verified prose-grid consistency (prior sessions)
All eight prose combo counts match their grids: H16=54, H17=60, H19=9, H20=36, H21=16,
H22=8, H23=6912, H25=8. H16 (54), H17 (60), H19 (9), H20 (36), H21 (16) and H25 (8) were
confirmed as genuinely different grids, so the H17/H19/H20 corrections are scoped and are
not over-corrections.

(End of file)