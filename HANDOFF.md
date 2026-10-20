# HANDOFF — H29 systematic look-ahead sweep of the remaining families (2026-10-19)

## What changed

**H29 — the pre-registered sweep H28 asked for. Every remaining family was audited for the
`resample` look-ahead from the committed artifacts. No published artifact was rewritten, no
published runner was edited, no gate, threshold, verdict or certified number changed, and no
grid was re-run.**

### New
- `run_h29_lookahead_sweep.py` — the sweep runner. Three legs: **(L1)** an `ast` sweep of every
  `run_*.py` for `resample(<literal>)` calls, each classified by a **runtime probe** of the
  installed pandas (the bin-label position and the resulting hold lag); **(L2)** an artifact
  alignment that **rebuilds** each family's collapse from the committed prices with that
  family's *own* runner code and the published configuration and requires a **bit-exact**
  reproduction of the committed artifact, plus a change-point check; **(L3)** the same-period vs
  previous-period expansion fractions of H27's L5a, generalised. Four mandatory self-checks
  (fire on H10; do not fire on a monthly family; report a deliberately causal construction as
  `CAUSAL`; classify both source constructions differently). Runtime 0.8 s, offline.
- `.experiments/artifacts/h29_lookahead_sweep/` — `summary.json`, `sweep_table.parquet`,
  `source_inventory.parquet` (re-written by H30 with H7 decided).
- `tests/test_h29_lookahead_sweep.py` — 36 tests (the collapse probe, the frozen verdict rule,
  the negative control, the source inventory, the bit-exact rebuilds, the committed report and
  the pre-registration). H30 replaced the "H7 is a coverage gap" test with a
  committed-artifact/causal test and added H7 to the bit-exact rebuild check.
- `.experiments/artifacts/exp_2026-10-19T18-56-08-872500Z/` — **H7's committed artifact**
  (`prices.parquet`, `equity_curve.parquet`, `returns.parquet`, `trades.parquet`, `summary.json`),
  plus the determinism control run `exp_2026-10-19T18-56-58-553612Z` (bit-identical parquets;
  `summary.json` differs only in the experiment id).
- Two `h7_intraday_tsmom_v1` records appended to `.experiments/experiments.jsonl` (status
  `completed`, through the tracker's normal record format).

### Changed
- `HYPOTHESIS_SPEC.md` — new §H30 with the **pre-registration frozen before the run** (scope,
  reconciliation rule, detector leg, verdict rule, frozen expectation `REPRODUCED` + `CAUSAL`,
  determinism negative control) and the **measure log**; §H29's scope table is unchanged
  (H29's report stands as the H29 session's record).
- `FINAL_REPORT.md` — the H7 row of the §H29 table is now `CAUSAL` (+1 bar hold lag, 0.0%
  look-ahead, same/prev 0.130/0.970, bit-exact rebuild); the H7 coverage-gap paragraph is
  replaced by the H30 outcome; a new §H30 section; summary statistics and the Next Task section
  updated (no further next task).
- `NEXT_TASK.md` — rewritten to record **H30 complete** and that there is no further next task
  (the paid-data task is unjustified for every family in the repo).
- `HANDOFF.md`, `HANDOFF_NEXT.md` — updated (this session).

## What was actually verified

- `python -m pytest -q` → **705 passed** (669 before + 36 new), 0 warnings.
- `python -m pytest -W error -q` → **705 passed**, clean.
- `python -m pytest --cov=qtr --cov-report=term-missing` → 705 passed, `src/qtr` coverage 99%
  (the single uncovered branch is the pre-existing unreachable `walk_forward_splits`
  empty-window guard at `statistics.py:169`).
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 77 files already formatted.
- `bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
- **The daily/monthly verdicts rest on bit-exact rebuilds**: H1 `selected_signals`, H2
  `selected_signals`, H3 `selected_signals`, H4 `ensemble_equity`, H5 `best_ddcv_equity`, H6
  `best_equity`, H8 `signals_w0.5` — every one reproduces the committed artifact with **max abs
  diff 0.0**, and the committed target's change points are a subset of the predicted ones
  (**0 extra** in every family).
- **The H23 counterfactual's control is bit-exact**: the rebuilt published pipeline reproduces
  the committed `positions` (max abs diff **0.0**) and the published summary to the digit
  (OOS Sharpe **−7.187089456116173**, 107 trades, max DD −97.5618%).
- **The detector self-checks**: H9/H10/H21/H22/H25 → `LOOKAHEAD` (same/prev 1.000/0.016 and
  1.000/0.382 — H27's statistic); no `"ME"` family fires; H27's `causal_daily_target_from_hourly`
  → `CAUSAL` (hold lag **+2**, previous-period expansion on 100% of the bars) while the published
  collapse → `LOOKAHEAD` by the same rule.
- **H30 (this session, after H29)**: H7's artifact committed as
  `exp_2026-10-19T18-56-08-872500Z` (offline, all five futures symbols served from the cache,
  no network) and recorded in `.experiments/experiments.jsonl`; determinism confirmed by a
  second bit-identical run (`exp_2026-10-19T18-56-58-553612Z` — identical sha256 on
  `prices`/`equity_curve`/`returns`/`trades`); the re-run reconciles with the published H7 row
  (OOS Sharpe 0.789 vs 0.7893, 1,005 vs 1,005 trades, PF 1.166 vs 1.1661, max DD −14.5% vs
  −14.54% OOS / −21.4% full-sample, verdict REJECT vs REJECT), with two disclosures logged
  (`compare_to_benchmark` raised advisory — benchmark null — and the gate tally 3/8 published
  vs 4/9 recomputed; the published row is left as the historical record); the H29 detector
  re-run with H7 added to `FAMILIES` reports H7 **`CAUSAL`** (min hold lag **+1 bar**, **0**
  look-ahead bars, committed equity curve rebuilt **bit-exactly** max abs diff `0.0`, **0 extra**
  change points, same/prev 0.130 / 0.970); all four detector self-checks pass and the sweep
  verdict stays `LOOKAHEAD_FOUND`.
- `python -m pytest -q` → **705 passed** (after the H30 test change), 0 warnings; coverage and
  lint/format checks unchanged and clean; workflow scripts OK.

## The finding (headline)

**H29's verdict: `LOOKAHEAD_FOUND`.** The look-ahead is confined to the **intraday** collapse,
but the sweep found that it reaches **four families that had never been audited for it**, and it
**certified the daily/monthly families as clean** on the committed artifacts.

| Family | Collapse | Min hold lag | Look-ahead bars | same / prev | Rebuild | **Verdict** | Published |
|---|---|---|---|---|---|---|---|
| H1 | `ME` | **+1** | 0.0% | 0.401 / 0.980 | 0.0 | **CAUSAL** | REJECT |
| H2 | `ME` | **+1** | 0.0% | 0.416 / 0.980 | 0.0 | **CAUSAL** | REJECT |
| H3 | `ME` | **+1** | 0.0% | 0.079 / 0.968 | 0.0 | **CAUSAL** | REJECT |
| H4 | `ME` | **+1** | 0.0% | 0.420 / 0.972 | 0.0 | **CAUSAL** | REJECT |
| H5 | `ME` | **+1** | 0.0% | 0.424 / 0.980 | 0.0 | **CAUSAL** | REJECT |
| H6 | `ME` | **+1** | 0.0% | 0.454 / 0.980 | 0.0 | **CAUSAL** | REJECT |
| H7 | `ME` | **+1** | 0.0% | 0.130 / 0.970 | 0.0 | **CAUSAL** | REJECT |
| H8 | `ME` | **+1** | 0.0% | 0.391 / 0.980 | 0.0 | **CAUSAL** | REJECT |
| H11 | `1D` (inherited) | **−22** | 94.7% | 1.000 / 0.016 | identity 0.0 | **LOOKAHEAD** | PASS |
| H12 | `1D` (inherited) | **−22** | 94.7% | 1.000 / 0.016 | identity 0.0 | **LOOKAHEAD** | PASS |
| H13 | `1D` (inherited) | **−22** | 94.7% | 1.000 / 0.016 | identity 0.0 | **LOOKAHEAD** | REJECT |
| H23 | `1D` | **−22** | 96.0% | 1.000 / 0.385 | control 0.0 | **LOOKAHEAD** | REJECT |

**The discriminator is the bin label, and it was probed, not assumed.** On the installed pandas
(3.0.6) `resample("1D")` labels each bin at its **start** (day D 00:00) with the value of day
D's **close**, while `resample("ME")` labels each bin at its **end** (the calendar month end)
with the value of the month's **close**. The engine trades `signals.shift(1)`, so a value that
first appears on bar `d` is first traded on bar `d+1`; the **hold lag** is `d+1 − s` (`s` = the
bar whose raw signal the value carries). The monthly families have a hold lag of **+1 bar
everywhere** and **0** look-ahead bars; the intraday collapse has **−22 bars** and 94.7%–96.0%
look-ahead bars. The source sweep found **no other collapse construction in the repo**: 8 ×
`"ME"` (H1–H8) and 4 × `"1D"` (H9, plus the H26/H27 audit helpers).

**H11 / H12 / H13 — the defect travels with the PASS.** The three diagnostics inherit H10's
construction and the inheritance is proved from the committed artifacts, not from the source:
H11's `baseline_positions` are **bit-identical** to H10's `positions` (max abs diff **0.0**, and
so are the returns), H12's `selected_oos_sharpe` equals `h10_artifact_oos_sharpe` to the digit
(1.2757590680990518), H13's `returns_max_abs_diff_vs_h10` is **0.0**. **H11's and H12's PASS
verdicts therefore rest on the same look-ahead positions as H10's** and are *not* independent
evidence of an edge; they travel with H28's `CAUSAL_REJECTED`. No published verdict was changed.

**H23 (crypto) — the inherited premise was wrong and the family inherits the defect.**
`run_h23_crypto_futures_tsmom.py` imports `_daily_target_from_hourly` from H9 (line 30) and
calls it in `build_hourly_target` (line 133): the crypto family **does** use the daily collapse
(the next-task brief said it did not). Magnitude in H27's terms: the published build (bit-exact
control) has OOS Sharpe **−7.187089456116173**; under the minimal causal fix it is **−5.8929**
(76 trades, max DD −90.5%); the look-ahead bar fraction is **96.0%**; the intraday/overnight
split is **not applicable** (a continuous 24/7 market with no session boundary). A look-ahead is
a *favourable* bias, so removing it cannot rescue the family: **H23 stays REJECTED** and no
causal re-certification of H23 is warranted.

**Two premises of the inherited brief were corrected.** (i) The brief called the daily families
"the only other PASS family in the repo" — **no daily family passes** (H1 0.093, H2 0.116,
H3 −0.868, H4 0.376, H5 0.509, H6 0.708, H7 0.789, H8 0.814 — all REJECTED). The only PASS
families (H10, H11, H12, H22, H25) are all intraday and all `CAUSAL_REJECTED` under H28.
**The repo contains no PASS family that survives a causal construction.** (ii) H23 was
described as free of a daily collapse — it is not.

## What remains unresolved

- None from the audit record: H30 closed the H29 sweep's only coverage gap (H7). Every family
  in the repo now has a committed artifact or a documented reason for the gap, every
  daily/monthly family is `CAUSAL` and REJECTED (H1 0.093, H2 0.116, H3 −0.868, H4 0.376,
  H5 0.509, H6 0.708, H7 0.789, H8 0.814), and every intraday family is `CAUSAL_REJECTED`
  under H28 — the repo contains **no PASS family that survives a causal construction**.
- `src/qtr/validation/statistics.py:169` remains the single uncovered branch (unreachable
  `walk_forward_splits` empty-window guard, pre-existing).
- The documented **library drift** in `walk_forward_splits` (changed 2026-10-19 09:28) still
  moves `metrics.wf_stability` by ~1.3e-3 on a re-run of a published experiment. H29's/H30's
  rebuilds are unaffected (they do not use that helper's output).
- The **paid-data task is unjustified for every family in the repo**: it was closed for the
  intraday family by H28; H29/H30 show the daily families are *causal* but all REJECT, so more
  of the same free data does not rescue them either. It stays downstream.

## Which approaches have already failed and why

- **A thresholded same/prev match fraction does not discriminate.** The first implementation of
  the verdict rule required the dominant candidate to match on ≥99% of the bars. That is
  impossible for the `"ME"` construction: the bin label sits on the period's **last** bar, so the
  committed target equals the period's own value on that one bar (≈1/120 of a monthly grid) and
  the previous-period value everywhere else — the previous-period fraction is ≈0.95, not ≥0.99.
  This was diagnosed *before* the sweep was run and fixed by a **pre-execution amendment**
  (recorded in the spec): the **hold lag** became the thresholded statistic (it is exact for
  every bar of every construction) and the two fractions became a corroborating *ordering*.
  The sweep was **not** re-tuned after any measurement.
- **The hold lag cannot be read off a canonical probe for a *lagged* construction.** The probe
  assumes the label's value comes from its own bin's last bar; a causal construction takes it
  from the *previous* bin. The first negative-control implementation therefore reported the
  published construction's hold lag for the causal one and came out `INCONCLUSIVE`. The fix is
  the explicit `source_bin_offset` parameter of the probe (the negative control now reports
  **+2 bars** and `CAUSAL`).
- **The column labels of the daily collapse and the base signal do not match** (a 5-contract
  collapse against a 1-column slice of the signal), which made the first expansion comparison
  return `NaN` for every intraday family. The comparison now falls back to a positional pairing.
- **The H4 ensemble must be accumulated in the published order.** `sum(sigs) / len(sigs)` differs
  from the published running sum (`sig/len + sig/len + ...`) in the last bits and moved the
  rebuilt equity by 6e-9 — enough to fail a bit-exactness requirement. Reproducing the
  published accumulation order made the rebuild exact (0.0).
- **A "fixed" source that is silently stale is worse than none.** The `summary.json` lookup
  inside the rebuilds was keyed on the *parent* directory name (`artifacts`) instead of the
  experiment id, which made every rebuild fail with a `NoneType` error; the fix was to key on
  the artifact id. The failing rebuild is reported as `INCONCLUSIVE` with the traceback rather
  than being skipped.

## H31 — the H30 advisory was a real defect and is fixed (2026-10-20)

**What changed.** H30 logged `compare_to_benchmark` raising `"The truth value of a Series is
ambiguous"` during H7's re-run and recorded it as an advisory. It was in fact a bug in
`src/qtr/validation/statistics.py:compare_to_benchmark`: the function assumed a 1-D benchmark
and raised whenever the caller passed a multi-column DataFrame, which is exactly what H7 does
(`prices[FUTURES_UNIVERSE]`, a 5-column slice). The function now reduces a DataFrame
benchmark to its row-mean series (and likewise a 2-D ndarray) before aligning, so the
comparison is computed rather than skipped. Two regression tests pin the behaviour
(`test_dataframe_benchmark_reduced_to_equal_weighted`,
`test_2d_ndarray_benchmark_reduced` in `tests/test_statistics.py`); the pre-existing
`compare_to_benchmark` tests are unchanged in expectation and still pass.

**What was verified.** `python -m pytest -q` → **707 passed** (705 + 2 new), 0 warnings;
`python -m pytest -W error -q` → 707 passed; `python -m ruff check src tests run_*.py` → All
checks passed; `python -m ruff format --check src tests run_*.py` → 77 files already
formatted; `bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh`
OK. The H29 sweep re-run (`run_h29_lookahead_sweep.py`) is unchanged in verdict
(`LOOKAHEAD_FOUND`, all four self-checks pass, H1–H8 `CAUSAL`, H11/H12/H13/H23 `LOOKAHEAD`).
A verification re-run of H7 (`exp_2026-10-20T01-51-28-367059Z`, since deleted from the tree —
it was a reproduction, not a committed artifact) produced `prices`/`equity_curve`/`returns`/
`trades` **bit-identical** to the committed artifact `exp_2026-10-19T18-56-08-872500Z`
(identical sha256 on all four parquets) and `summary.json` differing only in the experiment id
and the two benchmark-fed gate booleans; OOS Sharpe (0.7893261992589912), trades (1,005),
profit factor (1.16605221165269), max DD (−14.54%) and verdict (REJECT) are unchanged.

**What remains unresolved.** Nothing from the audit record. The single uncovered branch is the
pre-existing unreachable `walk_forward_splits` empty-window guard at
`src/qtr/validation/statistics.py:169`. The documented library drift in `walk_forward_splits`
(changed 2026-10-19 09:28) still moves `metrics.wf_stability` by ~1.3e-3 on a re-run of a
published experiment; H29's/H30's rebuilds are unaffected (they do not use that helper's
output). The paid-data task remains unjustified for every family in the repo.

**Which approaches have already failed and why.** None new this session. The fix was a
minimal, additive change to a library function; no runner, gate, threshold, verdict or
certified number was modified, no grid was re-run, and no published artifact was touched.

## One precise next task

**None.** H31 is complete and the pre-registered free-data hypothesis space (H1–H30) is
exhausted: every family has a committed artifact or a documented reason for the gap, every
daily/monthly family is `CAUSAL` and REJECTED, every intraday family is `CAUSAL_REJECTED`
under H28, and the paid-data task (a wider OOS window for the PF bootstrap margin) is
unjustified for every family in the repo — H28 closed it for the intraday family and
H29/H30 show the daily families are causal but all REJECT. Buying more free-data-equivalent
data changes no verdict.

If the next agent is given a *new* assignment, verify with:
`python -m pytest -q`, `python -m pytest -W error -q`,
`python -m pytest --cov=qtr --cov-report=term-missing`,
`python -m ruff check src tests run_*.py`, `python -m ruff format --check src tests run_*.py`,
plus `bash -n .github/scripts/*.sh` and `bash .github/scripts/test_kilo_progress.sh`.
Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.
