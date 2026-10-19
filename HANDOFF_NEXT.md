# Handoff Summary

## Current state
- All tests pass: **622 passed, 0 warnings** (~3:35). Full suite re-confirmed this session.
- src/ coverage: 99% (single uncovered branch is the unreachable `walk_forward_splits` empty-window guard at statistics.py:114, pre-existing). Lint/format clean on `src tests run_*.py`. Workflow scripts pass `bash -n` and the progress-helper regression test.
- **H27 (this session): P&L level audit + look-ahead attribution — COMPLETE.** The *level* of the
  certified intraday P&L is **clean**: the dollar P&L recomputed from the committed
  prices/positions with the engine's contract maths reproduces the logged returns to
  **≤4.9e-16**, the contract specs are exactly consistent (`tick_value == tick_size x
  multiplier`), and the cost drag recomputed from `trades.parquet` matches the engine to
  **≤1.1e-19** (1.1%-4.9% of the gross edge) — so the extraordinary Sharpe is **not** a unit
  error. But the *positions were not knowable when traded*: the daily-target collapse
  (`_daily_target_from_hourly` -> `resample("1D").last()`, expanded back with
  `reindex(method="ffill")`) positions **every session with that session's own closing
  signal** — a one-day look-ahead present in **H9, H10, H21, H22 and H25 alike**. Proofs:
  (a) artifact-only — the logged daily collapse equals the signal at the day's *close* (0.0)
  while the day's *open* differs by up to 4.0, and the logged hourly target matches the
  same-day expansion on 100% of bars (prev-day only 38.6%); (b) bit-exact rebuild of every
  selected config (positions and returns, max abs diff **0.0**); (c) causal counterfactual
  — shifting only the daily series by one day gives OOS Sharpe H10 1.2758->**0.2923**,
  H22 1.3725->**0.3605**, H25 1.3236->**0.3231** and full-sample equity multiples
  6.92x/79.80x/100.73x -> **1.19x/1.89x/2.03x** (equal-weight buy-and-hold of the same
  basket: 1.36x, under a 5x gross leverage cap). 94.7%-97.8% of the published gross P&L is
  *intraday* P&L earned with same-day foresight (mean `sign(w_open) x r_intraday` tilt
  +0.00248 published vs +0.00040 causal, a 5.9x-6.2x excess). **Verdicts: `LEVEL_CONFIRMED` /
  `LOOKAHEAD_CONFIRMED`; `certified_family_valid = false`.** H27 changed **no gate,
  threshold, verdict or certified number** — the published PASS verdicts stand as published
  but are **not evidence of a tradable edge**. See `FINAL_REPORT.md` §H27 detail,
  `HYPOTHESIS_SPEC.md` §H27 (pre-registration + measure log), `NEXT_TASK.md`.
- **H26 (prior session): Sharpe annualization-scale audit — COMPLETE.** The published "OOS Sharpe" is a **√252-per-bar** metric, so for the intraday (1h) families it is *not* an annualized Sharpe: it understates the annualized value by 2.55× (repo's own `√(252·6.5)` vol-target convention) to 4.76× (empirical calendar). Certified family: H10 1.276→3.253, H22 1.372→3.499, H25 1.324→3.375. The daily families were already correctly annualized (control ratio 0.9995) and are unaffected. **No verdict/gate/threshold/certified number changed** — the mis-scaling is conservative. The "Sharpe CI-fragile" caveat was a **scale artifact** (H25 CI [0.8834, 1.7506] → [2.2521, 4.4633], P(Sharpe≥1.0) 0.9275 → 1.0000); the **PF margin fragility stands** (scale-invariant) and is now the binding constraint together with the 730-day sample. See `FINAL_REPORT.md` §H26 detail, `HYPOTHESIS_SPEC.md` §H26 (pre-registration + measure log), `NEXT_TASK.md`.
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
**H28 — re-certify the intraday futures TSMOM family under a causal daily collapse.**
H27 showed the certified family's edge is a one-day look-ahead in the daily-target collapse
(`run_h9_intraday_tsmom_experiment.py::_daily_target_from_hourly` +
`run_h10_intraday_tsmom_pfopt_experiment.py::build_hourly_target`). The fix is a one-day lag
of the collapsed daily series; the family must then be re-run under the **same** gates,
splits, Val-only selection and Test protection to record an honest verdict. Expect
**REJECT** (the causal counterfactual on the already-selected configs gives OOS Sharpe
0.29–0.36, PF 1.06–1.08, max DD −12% to −26%). Do **not** edit the published runners —
their artifacts are the historical record and H26/H27 reproduce them bit-exactly; add a
causal target builder + a new H28 runner instead. Full scope, constraints and the
pre-registration skeleton: `NEXT_TASK.md`.

## Documented next task (requires paid data — outside a free-data session, and now
## downstream of H28)
Per FINAL_REPORT.md §Next Task: widen the OOS window with **paid hourly futures data**
so the **PF** bootstrap CI clears its gate with margin. H10/H22/H25 are PASS *as published*
but the PF-margin is CI-fragile (H13 CI [1.190, 1.425]; H25 Robustness CI [1.2049, 1.4425],
P(PF≥1.3)=0.6215) — that fragility is scale-invariant and is the binding constraint
(the *Sharpe* CI fragility was withdrawn by H26 as a scale artifact). **H27 has moved this
task downstream: buying more data for a construction with a look-ahead would be wasted,
so H28 (causal re-certification) must come first.**


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
## H27 drift guards (added this session)
`tests/test_h27_pnl_level_audit.py` pins the two H27 findings so the defect class cannot
recur silently:

- `TestLevelChecks` — the dollar P&L recomputed from the contract maths must match the
  logged returns (≤1e-9) and the cost drag recomputed from `trades.parquet` must match the
  engine (≤1e-9) for every audited family; the contract specs must satisfy
  `tick_value == tick_size x multiplier` exactly.
- `TestLookaheadStructure` — the **artifact-only** chain: the logged daily collapse equals
  the signal at that day's *close* (0.0) and differs from the signal at that day's *open*;
  the logged hourly target matches the same-day expansion on 100% of bars.
- `TestCausalCounterfactual` — the rebuild of every selected config must reproduce the
  committed positions and returns **bit-exactly** (0.0), and the causal counterfactual must
  keep the certified family's OOS Sharpe below half the published value.
- `TestPnLAttribution` — the published build must keep its gross P&L >90% intraday, the
  causal build must book <30% of that intraday P&L, the same-day tilt (`sign(w_open) x
  r_intraday`) must stay >4x the causal build's, and the overnight component must stay
  within 50% of the causal build's (it is earned the same way by both).
- `TestCausalCollapseSemantics` — the counterfactual's construction is pinned on a
  synthetic series, and `causal_collapse()` must restore the runner modules on exit.
- `TestNegativeGuards` — each guard fails if the check is made vacuous: a wrong capital or
  a 1000x unit error breaks L1, a wrong contract multiplier or a wrong cost breaks L3, a
  hard-coded annualization breaks L4, and a *causal* construction is correctly **not**
  reported as a look-ahead.

The look-ahead lives in the *runners* (`run_h9_intraday_tsmom_experiment.py:195` and
`run_h10_intraday_tsmom_pfopt_experiment.py:114-133`), not in `src/qtr/`, so H28 must add a
causal path **without** editing those two functions (the published artifacts are the
historical record and H26/H27 reproduce them bit-exactly).
