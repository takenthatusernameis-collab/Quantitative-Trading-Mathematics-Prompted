# Handoff Summary

## Current state
- All tests pass: **705 passed, 0 warnings** (~3:40). Full suite re-confirmed this session.
- src/ coverage: 99% (single uncovered branch is the unreachable `walk_forward_splits` empty-window guard at statistics.py:169, pre-existing). Lint/format clean on `src tests run_*.py`. Workflow scripts pass `bash -n` and the progress-helper regression test.
- **H29 (this session): systematic look-ahead sweep of the remaining families — COMPLETE.
  Verdict `LOOKAHEAD_FOUND`.** Every remaining family was audited for the `resample`
  look-ahead from the committed artifacts, with a detector that **fires** on the already-audited
  intraday family (H9/H10/H21/H22/H25 → `LOOKAHEAD`, reproducing H27's same/prev statistic
  1.000/0.016 and 1.000/0.382), **does not fire** on any `"ME"` family, and reports H27's
  deliberately *causal* `causal_daily_target_from_hourly` as **`CAUSAL`** (hold lag +2 bars,
  previous-period expansion on 100% of the bars). The discriminator is the **bin label**, probed
  at run time on the installed pandas: `"1D"` labels each bin at its **start** with that day's
  **close** (a look-ahead: min hold lag **−22** bars, 94.7%–96.0% of the bars are positioned
  with the close of the day they belong to), `"ME"` labels each bin at its **end** with the
  month's close (hold lag **+1** bar, **0** look-ahead bars). Results: **H1–H8 are all `CAUSAL`**
  — each verdict rests on a **bit-exact** rebuild of the committed artifact from the committed
  prices (max abs diff **0.0**) and on **0 extra** change points; H7 included after H30 committed
  its artifact (`exp_2026-10-19T18-56-08-872500Z`, offline on the complete futures cache, the
  re-run reproduces the published H7 row to reporting precision — OOS Sharpe 0.789 vs 0.7893,
  1,005 vs 1,005 trades, PF 1.166 vs 1.1661, max DD −14.5% vs −14.54% OOS, verdict REJECT vs
  REJECT — with two disclosures logged explicitly and the published row left as the historical
  record) and the H29 detector re-run with H7 added to `FAMILIES` reports H7 **`CAUSAL`**
  (min hold lag +1 bar, 0 look-ahead bars, bit-exact equity rebuild, 0 extra change points,
  same/prev 0.130/0.970); **H11, H12 and H13 are `LOOKAHEAD`** because they *inherit* H10's
  construction (H11's `baseline_positions` are bit-identical to H10's `positions`, H12's
  `selected_oos_sharpe` equals `h10_artifact_oos_sharpe` to the digit, H13's
  `returns_max_abs_diff_vs_h10` is 0.0) — so **H11's and H12's PASS verdicts rest on the same
  look-ahead positions as H10's** and are not independent evidence; **H23 is `LOOKAHEAD`** — it
  *does* use the daily collapse (it imports `_daily_target_from_hourly` from H9), contradicting
  the inherited premise, and its published build rebuilds **bit-exactly** (OOS Sharpe
  −7.187089456116173) while the minimal causal fix gives −5.8929 (a look-ahead is a *favourable*
  bias, so the REJECT stands a fortiori and **no** causal re-certification of H23 is warranted).
  **The sweep's only coverage gap (H7) is now closed: every family in the repo has a committed
  artifact or a documented reason for the gap.** H29/H30 changed no gate, threshold, verdict or
  certified number and re-ran no grid (only the *selected* configuration of the families they
  measure). See `FINAL_REPORT.md` §H29/§H30, `HYPOTHESIS_SPEC.md` §H29/§H30 (pre-registration
  + the pre-execution amendment + the measure log), `NEXT_TASK.md`.
- **H28 (prior session): causal re-certification of the intraday family — COMPLETE.
  `CAUSAL_REJECTED` for every family.** The published H10/H21/H22/H25 pipelines were re-run
  with **one** change — the daily collapse lagged by one calendar day — and the **unchanged**
  gates, splits, Val-only selection, Test protection and cost model. Every family's
  **negative control** (the published same-day expansion through the identical harness)
  reproduced the published artifact **bit-exactly**: H10 9/9 artifacts, H21/H22/H25 12/12 each,
  max abs diff **0.0** everywhere, including `grid_results` (all 13,824 H10 combos' Val
  metrics), with the selected config, every gate boolean and the verdict identical. The only
  difference is the frozen, documented `metrics.wf_stability` library drift (the 2026-10-19
  09:28 `walk_forward_splits` change; the published value is reproduced bit-exactly by the
  pre-change implementation and the gate consuming it is unchanged). Results: H10 OOS Sharpe
  **0.3909** / PF 1.087 / DD −10.1% (3/8 gates), H21 **0.1317** / 1.030 / −26.1% (3/8), H22
  **0.3605** / 1.077 / −22.8% (4/9), H25 **0.3231** / 1.069 / −26.2% (4/9). The same four gates
  fail everywhere (`sharpe` ≥1.0, `pf` ≥1.3, `worst` ≥0.3, `p` <0.05; plus `ir` for H10). The
  full causal **re-selection** buys at most +0.10 Sharpe (H10 re-selects `smooth_span=4,
  regime_scaling=True`, 0.2923 → 0.3909) and changes no gate outcome, so the REJECT is not an
  artefact of a frozen configuration. **H28 changed no gate, threshold, verdict or certified
  number** — the published PASS verdicts stand as published, but the family is now
  *demonstrated* not to be a tradable edge. See `FINAL_REPORT.md` §H28 detail,
  `HYPOTHESIS_SPEC.md` §H28 (pre-registration + measure log), `NEXT_TASK.md`.
- **H27 (prior session): P&L level audit + look-ahead attribution — COMPLETE.** The *level* of the
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

There is **no assigned next task**: H30 (close the H7 coverage gap) is complete and the
pre-registered free-data hypothesis space (H1–H30) is exhausted — every family has a committed
artifact or a documented reason for the gap, every daily/monthly family is `CAUSAL` and
REJECTED, every intraday family is `CAUSAL_REJECTED` under H28, and the paid-data task (a
wider OOS window for the PF bootstrap margin) is unjustified for every family in the repo
(H28 closed it for the intraday family; H29/H30 show the daily families are causal but all
REJECT).

If the next agent is given a *new* assignment, verify with:
`python -m pytest -q`, `python -m pytest -W error -q`,
`python -m pytest --cov=qtr --cov-report=term-missing`,
`python -m ruff check src tests run_*.py`, `python -m ruff format --check`,
plus `bash -n .github/scripts/*.sh` and `bash .github/scripts/test_kilo_progress.sh`.
Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.

## Documented next task (requires paid data — outside a free-data session, and no longer
## justified for any family in the repo)
Per FINAL_REPORT.md §Next Task: widen the OOS window with **paid hourly futures data**
so the **PF** bootstrap CI clears its gate with margin. H10/H22/H25 are PASS *as published*
but the PF-margin is CI-fragile (H13 CI [1.190, 1.425]; H25 Robustness CI [1.2049, 1.4425],
P(PF≥1.3)=0.6215) — that fragility is scale-invariant and is the binding constraint
(the *Sharpe* CI fragility was withdrawn by H26 as a scale artifact). **H27 moved this task
downstream (buying more data for a construction with a look-ahead would be wasted) and H28
has now closed it for the intraday family: a causal construction that fails the gates on the
free window will not be rescued by more of the same data. H29 closes it for the rest: the
daily families are *causal* but all REJECT (H1 0.093, H2 0.116, H3 −0.868, H4 0.376,
H5 0.509, H6 0.708, H7 0.789, H8 0.814), so more of the same free data does not rescue them
either.**


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
`run_h10_intraday_tsmom_pfopt_experiment.py:114-133`), not in `src/qtr/`, so H28 added a
causal path **without** editing those two functions (the published artifacts are the
historical record and H26/H27/H28 reproduce them bit-exactly).

## H28 drift guards (added this session)
`tests/test_h28_causal_recertification.py` (47 tests) pins the H28 construction and its
verdict rule so the re-certification cannot be quietly weakened:

- `TestCausalCollapseSemantics` — the collapse lags the daily series by exactly one day, the
  first day is unknown (not the same day's close), a non-trading day is carried forward (the
  position is held over the weekend), the daily index spans the calendar, a malformed index is
  a hard error, and `causal_collapse()` patches **all five** runner modules and restores them
  — including on failure.
- `TestExperimentIdentity` — the H28 runner swaps the experiment name/description and restores
  it, and the tracker capture is unwound.
- `TestNegativeControl` — the control is bit-exact when it should be, and **not** bit-exact
  when a single artifact value is perturbed, a control artifact is missing, a **gate boolean**
  changes, the **verdict** changes, or an **unexpected metric** changes. The single frozen
  library-drift field (`metrics.wf_stability`) is tolerated *only* as such — the gate that
  consumes it is not exempt.
- `TestVerdictRule` — a family is `CAUSAL_CERTIFIED` only if the control reproduced **and**
  every unchanged gate passed; a broken control **voids** the run; a missing summary is a
  reject; the family verdict requires **all three** certified members.
- `TestFrozenElements` — the gates are the published `GATES` object, the splits are the
  published `_splits`, the selection rules are the published ones and the H28 runner does not
  redefine them, the frozen artifact ids are the published ones, the grid sizes match the
  published runs, and H9 is out of scope.
- `TestPreRegistration` — `HYPOTHESIS_SPEC.md` §H28 must exist and must freeze the verdict
  rule, the artifact ids, the unchanged gates, the negative control (including the word
  "void") and the prior expectation of REJECT.

The published runners were **not** edited: H28 patches the module-global
`_daily_target_from_hourly` at run time and restores it, and it calls each published runner's
own `main()` so the grid, the selection rule and the gates are reused unchanged **by
construction**.

## H29 drift guards (added this session)
`tests/test_h29_lookahead_sweep.py` (36 tests) pins the look-ahead *sweep* so the detector
cannot be quietly weakened or re-pointed:

- `TestCollapseProbe` — the pandas bin-label semantics are **probed, not hard-coded**: `"1D"`
  labels at the bin **start** (and is a look-ahead on an hourly grid: min hold lag ≤ 0,
  >90% look-ahead bars), `"ME"` labels at the bin **end** (and is causal on a daily grid: min
  hold lag ≥ 1, **0** look-ahead bars), a *lagged* collapse (the causal one) is causal on the
  same grid, and the probe is grid-dependent (a `"1D"` collapse on a daily grid is a no-op).
- `TestVerdictRule` — the frozen rule's boundaries: a negative hold lag **with** the
  same-period match is `LOOKAHEAD`, a positive hold lag **with** the previous-period match is
  `CAUSAL`, the two legs must agree (otherwise `INCONCLUSIVE`), and a missing statistic is
  `INCONCLUSIVE`.
- `TestNegativeControl` — H27's `causal_daily_target_from_hourly` must be reported `CAUSAL`
  (hold lag ≥ 1, previous-period expansion dominant) while the published collapse is reported
  `LOOKAHEAD` by the same rule, and the H29 runner must use the H27 collapse *object* so the
  two cannot drift apart.
- `TestSourceSweep` — the source inventory contains both constructions, the `"1D"` collapse
  appears **only** in the intraday/audit runners, the `"ME"` collapse appears in exactly the
  eight daily runners, and the two are classified differently on the grid they run on.
- `TestRebuilds` — the H1 and H8 rebuilds reproduce their committed artifacts **bit-exactly**,
  the committed target only changes on predicted bars, and the H23 counterfactual restores the
  runner module it patches.
- `TestCommittedReport` — the committed H29 report's verdict, the four self-checks, the daily
  families' `CAUSAL` verdicts, the intraday families' `LOOKAHEAD` verdicts, H7's coverage-gap
  status, the bit-exactness of every causal family's rebuild, the already-audited families'
  verdicts, and the H23 control (bit-exact positions **and** the published OOS Sharpe to the
  digit, with the causal fix failing to rescue the family).
- `TestPreRegistration` — `HYPOTHESIS_SPEC.md` must contain §H29, the frozen artifact ids and
  the **pre-execution amendment**, and the published runners must not have been edited.

The look-ahead lives in the *runners* (`run_h9_intraday_tsmom_experiment.py:195` and
`run_h10_intraday_tsmom_pfopt_experiment.py:114-133`), not in `src/qtr/`, so H29 added a
detector **without** editing those functions (the published artifacts are the historical
record and H26/H27/H28/H29 reproduce them bit-exactly).
