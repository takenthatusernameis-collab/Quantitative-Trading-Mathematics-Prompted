# HANDOFF — H28 causal re-certification of the intraday family (2026-10-19)

## What changed

**H28 — the pre-registered re-certification H27 asked for. The published grids were re-run
with a causal daily collapse and the unchanged gates. No published artifact was rewritten, no
published runner was edited, no gate, threshold, verdict or certified number changed.**

### New
- `run_h28_causal_recertification.py` — for each of H10/H21/H22/H25 it runs the family's
  **published `main()` verbatim** (so the grid, the selection rule, the gates, the splits and
  the cost model are reused unchanged *by construction*, not by copy) twice: a **control** run
  with the published same-day expansion and a **causal** run with the daily collapse lagged by
  one calendar day. The collapse is installed by patching the module-global
  `_daily_target_from_hourly` in all five runner modules; the experiment identity is swapped
  for an H28 id; the originals are restored on exit. It then compares the control against the
  frozen published artifact (bit-exact, field-level) and gate-evaluates the causal run.
  Runtime 6786.5 s ≈ 1.89 CPU-h, offline.
- `.experiments/artifacts/h28_causal_recertification/summary.json` +
  `recertification_table.parquet`, plus the eight run directories (4 control + 4 causal).
- `tests/test_h28_causal_recertification.py` — 47 tests (collapse semantics and the weekend
  carry, the calendar guard, the module patch/restore incl. on failure, the experiment
  identity and tracker capture, the control's sensitivity, the verdict rule, the
  pre-registration).

### Changed
- `HYPOTHESIS_SPEC.md` — new §H28 with the **pre-registration frozen before the run** (the
  unchanged gates/splits/selection rule/cost model, the one-change rule, the mandatory negative
  control, the frozen verdict rule, the frozen artifact ids, the budget, the disclosures) and
  the **measure log**.
- `FINAL_REPORT.md` — executive-summary H28 block, a new §H28 detail section, a corrected
  Conclusion, corrected Summary statistics (H1–H28) and a rewritten §Next Task.
- `NEXT_TASK.md` — rewritten for **H29** (the systematic look-ahead sweep of the *remaining*
  certified families).
- `HANDOFF_NEXT.md` — updated.

## What was actually verified

- `python -m pytest -q` → **669 passed** (622 before + 47 new), 0 warnings.
- `python -m pytest -W error -q` → clean.
- `python -m pytest --cov=qtr --cov-report=term-missing` → coverage unchanged (no library
  code was added; the helpers live in the runner).
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → clean.
- `bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
- **The negative control, for all four families:** the control run reproduced the published
  artifact **bit-exactly** — H10 9/9 artifacts and H21/H22/H25 12/12 each, max abs diff
  **0.0** everywhere, including `grid_results` (which pins the Val metrics of all 13,824 H10
  combos) — with the selected configuration, every gate boolean and the verdict identical. The
  single documented exception is `metrics.wf_stability`, which moves only because the library's
  `walk_forward_splits` was changed on 2026-10-19 09:28 (after the published runs); the
  published value is reproduced bit-exactly by the pre-change implementation, and the gate that
  consumes it is unchanged. **The published record is fully reproducible, and the only thing
  that changes the result is the causal collapse.**
- **H27 remains reproducible:** re-running `run_h27_pnl_level_audit.py` reproduces its
  `summary.json` bit-for-bit (ignoring `elapsed_sec`).

## The finding (headline)

**H28's verdict: `CAUSAL_REJECTED` for every family — the certified family does not survive
its own re-certification.** H27 established the defect; H28 measured the consequence under the
unchanged gates with the full grids re-run.

| Family | Published | Control (bit-exact?) | Causal verdict | OOS Sharpe | OOS PF | Max DD | OOS trades | Gates |
|---|---|---|---|---|---|---|---|---|
| H10 | PASS | **yes** | **CAUSAL_REJECTED** | 0.3909 | 1.087 | −10.1% | 2524 | 3/8 |
| H21 | REJECT | **yes** | **CAUSAL_REJECTED** | 0.1317 | 1.030 | −26.1% | 5927 | 3/8 |
| H22 | PASS | **yes** | **CAUSAL_REJECTED** | 0.3605 | 1.077 | −22.8% | 3288 | 4/9 |
| H25 | PASS | **yes** | **CAUSAL_REJECTED** | 0.3231 | 1.069 | −26.2% | 1786 | 4/9 |

The failing gates are the same four in every family — `sharpe` (≥ 1.0), `pf` (≥ 1.3), `worst`
(worst-regime Sharpe ≥ 0.3) and `p` (benchmark p < 0.05) — plus `ir` for H10. `trades`, `stab`
and (H22/H25) `perturbation` pass; `dd` passes only for H10.

**The re-selection headroom is now measured.** H27's counterfactual re-ran only the
already-selected configuration and was therefore a lower bound. H28 re-ran the full grids:
H10 re-selects a *different* configuration (`smooth_span` None → **4**, `regime_scaling` False →
**True**), lifting the causal OOS Sharpe from 0.2923 to **0.3909** — real but small, still 2.6×
below the gate, with PF 0.21 short and a negative information ratio. H21/H22/H25 re-select the
published configuration itself, so their causal numbers coincide with H27's to the digit. **The
REJECT is not an artefact of a frozen configuration.**

**H27's findings still stand** (they are the evidence H28 acted on).

**Level (no unit error).** `contracts = weight × 1e6 / (price × multiplier)` and
`P&L = contracts × Δprice × multiplier` reproduce the logged return series to **≤4.9e-16**
(L1); `tick_value == tick_size × multiplier` holds exactly for all five symbols and the
per-contract cost matches `commission + (spread+slippage) × tick_value` exactly (L2); the
cost drag recomputed from `trades.parquet` matches the engine to **≤1.1e-19** and is
**1.1%–4.9%** of the gross edge (L3). The vol target is applied to the same hourly-return
quantity the P&L is built from (L4); the *annualization* is the same mismatch H26 found
from the Sharpe side — the code uses `√(252 × 6.5) = 1638` bars/yr while the artifacts'
bar index implies **5,701** bars/yr (**1.8657×**).

**Look-ahead (the real defect).** `run_h9_intraday_tsmom_experiment.py::_daily_target_from_hourly`
collapses the hourly signal to `resample("1D").last()` — a day-labelled series holding *that
day's closing* signal — and `run_h10_intraday_tsmom_pfopt_experiment.py::build_hourly_target`
expands it back with `reindex(index, method="ffill")`, which assigns **every bar of day D the
value of day D's label**. Every session is therefore positioned at its own open with the
signal computed at its own close. This affects **H9, H10, H21, H22 and H25 alike**.

Three independent proofs (all in the audit artifact):

1. *Artifact-only*: the logged daily collapse equals the logged signal at that day's close
   to 0.0 while the signal at the day's open differs by up to 3.87–4.0; the expansion puts
   the close value on the open bar. For H21/H22/H25 the logged expanded hourly target
   matches the **same-day** expansion on **100%** of bars and the previous-day expansion on
   only **38.6%**.
2. *Bit-exact rebuild*: each family's selected config rebuilt from the committed prices
   reproduces the committed positions and returns with max abs diff **0.0**; the rebuilt
   target matches the same-day expansion on 100% of bars.
3. *Causal counterfactual*: shifting only the daily series by one day (nothing else in the
   pipeline changes) and re-running the same engine:

| Family | Published OOS Sharpe | Causal | Drop | Published equity (full sample) | Causal | Buy-and-hold |
|---|---|---|---|---|---|---|
| H9 (REJECT) | 1.0565 | 0.1860 | 82.4% | 8.02× | 1.26× | 1.33× |
| H10 (PASS) | 1.2758 | 0.2923 | 77.1% | 6.92× | 1.19× | 1.36× |
| H21 (REJECT) | 0.8394 | 0.1317 | 84.3% | 14.96× | 1.27× | 1.36× |
| H22 (PASS) | 1.3725 | 0.3605 | 73.7% | 79.80× | 1.89× | 1.36× |
| H25 (PASS) | 1.3236 | 0.3231 | 75.6% | 100.73× | 2.03× | 1.36× |

**Where the money came from:** 94.7%–97.8% of the published gross P&L is *intraday* P&L
(engine per-bar chain; overnight gap → session open vs. open → close); under the causal build
the intraday P&L falls 4.574 → 0.653 for H25 (**7.0×**), while the *overnight* component is
earned almost identically by both (0.257 vs 0.279) — the entire difference is the same-day
part of the session. The model-free fingerprint: the mean `sign(w_open) × r_intraday` is
**+0.00248** published vs **+0.00040** causal — a **5.9×–6.2×** excess same-day tilt, in
every family. The equal-weight buy-and-hold of the same basket grows 1.36× over the same
window, while the published H25 grows **100.7×** under a 5× gross leverage cap.

## What remains unresolved

- **The certified family is `CAUSAL_REJECTED`.** H28 re-ran the full published grids under a
  causal daily collapse and every family failed the unchanged gates. The published PASS
  verdicts (H10/H11/H12/H22/H25) stand as published — H28 changed no gate, threshold, verdict
  or certified number — but they are now *demonstrated* not to be evidence of a tradable edge.
  There is no intraday edge in this record.
- **The daily families have never been swept for the same defect.** H27/H28 covered the
  intraday family only. The daily/monthly families (H1–H8) and the intraday diagnostics
  (H11–H13) have not been audited for the `resample` look-ahead. The *mechanism* suggests they
  are clean (`resample("ME")` labels each month at the bin **end**, so the forward-fill carries
  the *previous* month's value, unlike `resample("1D")` which labels at the bin **start**),
  but that is a hypothesis, not a result. That is H29.
- **The paid-data task is now unjustified for the intraday family.** Widening the OOS window
  cannot rescue a construction that fails the gates on the free window; it may still be
  justified for the *daily* families, which H29 would certify as clean.
- **H23 (crypto) was not audited** — it is a different construction (its own runner, no
  daily-collapse family) and is REJECTED anyway; H27's scope was the intraday futures family.
- `src/qtr/validation/statistics.py:114` remains the single uncovered branch (unreachable
  `walk_forward_splits` empty-window guard, pre-existing).
- **A latent artifact-discovery fragility in the repo was exposed and closed.** The helpers that
  resolve a family's artifact directory (`run_h25_pf_robustness.py::_find_latest_h25_dir` and
  the `_latest_hXX_dir` helpers in the family test files) pick the *lexicographically last*
  depth-1 directory whose `summary.json` carries the family's `hypothesis` label. The H28 runs
  initially sat at depth 1 and were picked up as the published family runs, which broke four
  H25-Robustness regression tests (they compared the *causal* run against the *published*
  artifact). H28 now groups its runs under
  `.experiments/artifacts/h28_causal_recertification/runs/<exp_id>/` — the same layout H26/H27
  use — and `TestPublishedArtifactDiscovery` fails if an H28 run is ever left at depth 1 or if
  the published run is not the maximum candidate for its family. **No published artifact, gate,
  verdict or certified number was touched.**
- **One documented reproducibility drift remains in the library**: `walk_forward_splits` was
  changed on 2026-10-19 09:28 (the last window now absorbs the trailing samples), so a re-run
  of a *published* experiment moves `metrics.wf_stability` by ~1.3e-3. The published value is
  reproduced bit-exactly by the pre-change implementation; every other field, every gate
  boolean and every artifact is unaffected. H28 freezes this as the single tolerated
  difference in its negative control.

## Which approaches have already failed and why

- **The "fix the runner and re-run" approach was rejected.** The published runners are the
  historical record that H26/H27/H28 reproduce bit-exactly; editing `_daily_target_from_hourly`
  in place would silently invalidate that reproducibility. H28 instead patched the module
  attribute at run time and restored it, which keeps the published artifacts and runners
  untouched.
- **Re-running the grids with the *published* construction was not considered a valid
  substitute for the negative control** — but it *was* run, and it is what makes the causal
  comparison credible: it shows the pipeline reproduces to 0.0 and that only the collapse
  changes the result.
- One honest disclosure carried forward from H27: the look-ahead hypothesis was first
  *observed* during exploratory reproduction, before the section was frozen, even though the
  **level verdict rule** was pre-registered in `NEXT_TASK.md` before any execution. The
  look-ahead sub-rule, the frozen artifact ids and the tolerances were fixed before the formal
  audit run; the rule is symmetric (a clean timing would have forced a `LOOKAHEAD_ABSENT`
  report), and the measurement plan (L1–L5) was fixed before the audit was run. H28's
  pre-registration was written *before* the formal run, including the prior expectation of
  REJECT and the single frozen library-drift exemption.

## One precise next task

**H29 — a systematic look-ahead sweep of the *remaining* certified families** (free data,
bounded, verifiable). Full scope, constraints and the pre-registration skeleton are in
`NEXT_TASK.md`; the short version:

1. **Enumerate and audit every certified family not covered by H27/H28**: the daily / monthly
   families (H1–H8 — the only other PASS family in the repo), the intraday diagnostics that
   inherit H10's construction (H11 robustness, H12 selection bias, H13 OOS deflation / PF
   audit) and H23 (crypto, for completeness).
2. **Decide from the committed artifacts alone** whether each family's position at the start
   of a period is aligned with *that* period's own close (look-ahead) or with the previous
   period's close (causal) — the same artifact-only evidence chain H27 used.
3. **Sweep the source, not just the artifacts**: every `resample(...)` followed by a forward-fill
   expansion, classified by where the bin label sits. A collapse is a look-ahead **iff** the
   bin label is at the bin's **start** (`resample("1D")`) and not if it is at the bin's **end**
   (`resample("ME")`).
4. **Self-check the detector**: it must *fire* on H10 and *not* fire on a monthly family, and
   must report clean on the H27 causal construction (the negative control). Report per family;
   do **not** re-run grids and do **not** change any published verdict.

**Expect:** `SWEEP_CLEAN` for the monthly families (the labelling rule says so) and `SWEEP_CLEAN`
for the intraday diagnostics beyond the already-audited H10/H21/H22/H25 — but that is a
prediction, and the sweep is worth running because a *second* defective family would be a
serious finding.
