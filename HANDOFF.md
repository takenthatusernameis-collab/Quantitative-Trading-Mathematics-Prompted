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
  `walk_forward_splits` empty-window guard, pre-existing). *(Corrected by H33: this was wrong —
  the guard is at `statistics.py:159-160`, it is reachable (`walk_forward_splits(3, n_splits=5)`
  → `[]`) and it is covered by `tests/test_statistics.py:185`. The real uncovered block is the
  dead `deflated_sharpe_ratio` body, and the measured `src/qtr` coverage is **94%**, not 99%.)*
- The documented **library drift** in `walk_forward_splits` (changed 2026-10-19 09:28) still
  moves `metrics.wf_stability` by ~1.3e-3 on a re-run of a published experiment. H29's/H30's
  rebuilds are unaffected (they do not use that helper's output).
- The **paid-data task is unjustified for every family in the repo**: it was closed for the
  intraday family by H28; H29/H30 show the daily families are *causal* but all REJECT, so more
  of the same free data does not rescue them either. It stays downstream.
- **H34's leftovers (the next task).** (i) The committed artifacts of H19, H20 and H23 still
  record the **pre-H34** gate boolean (`passes["p"] = true`) while the current code computes the
  direction-aware `false`; the artifacts are immutable, so the disagreement must be pinned in the
  artifact-adjacent tests — `tests/test_h20_signed_volume.py:453` and
  `tests/test_h23_crypto_futures_tsmom.py:542` still assert the pre-H34 identity
  `p["p"] == (benchmark_p_value < max_p_value)`. (ii) The `FINAL_REPORT.md` §Summary statistics
  test-count bullet still quotes the H33 number ("725/725 passing"; H34 measured **735/735**) and
  must be re-stated after the test changes. (iii) The library's `alpha_p_value_one_sided` field is
  now an informational output that no runner reads (the gate uses the two-sided p-value plus the
  direction requirement).

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

## H32 — the H31 commit introduced a build-breaking defect and is fixed (2026-10-20)

**What changed.** Commit `68ec93b` (H31) replaced the `def compare_to_benchmark(...)` signature
with a `def deflated_sharpe_ratio(...)` block but left the original function's *body* in place
immediately after the new function's `return`, without a `def` header. The module still parsed
(`ast.parse` OK) but was **unimportable**: the orphaned body is dead code at module level, and
`from qtr.validation.statistics import compare_to_benchmark` raised
`ImportError: cannot import name 'compare_to_benchmark'`. Because `qtr/validation/__init__.py`
imports that symbol, **every** test that imports `qtr.validation` failed at collection — 18 test
files, 713 tests — so the repo went from green (H31's 707 passed) to red on the same source.
The fix is an 8-line insertion restoring a proper `def compare_to_benchmark(...)` header
immediately before the orphaned body, preserving the signature and behaviour H31 established
(`np.ndarray | pd.Series` for both return series, DataFrame and 2-D-ndarray reduction preserved).
`deflated_sharpe_ratio` is unchanged in position, signature and behaviour.

**What was verified.** `python -m pytest -q` → **713 passed** (707 + 6 new), 0 warnings;
`python -m pytest -W error -q` → 713 passed; `python -m pytest --cov=qtr --cov-report=term-missing`
→ 713 passed, `src/qtr` coverage 99% (the single uncovered branch is the pre-existing
unreachable `walk_forward_splits` empty-window guard at `statistics.py:169`);
`python -m ruff check src tests run_*.py` → All checks passed;
`python -m ruff format --check src tests run_*.py` → 77 files already formatted;
`bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
`from qtr.validation.statistics import compare_to_benchmark, deflated_sharpe_ratio` succeeds.
The H31 `compare_to_benchmark` regression tests (`test_dataframe_benchmark_reduced_to_equal_weighted`,
`test_2d_ndarray_benchmark_reduced`, and the pre-existing `TestCompareToBenchmark` set) all pass,
confirming the restored function still reduces a DataFrame/2-D-ndarray benchmark to its row-mean
series and that the OLS-beta / zero-variance / unit-interval-p-value expectations are unchanged.

**What remains unresolved.** Nothing from the audit record. The single uncovered branch is the
pre-existing unreachable `walk_forward_splits` empty-window guard at `statistics.py:169`.
*(Corrected by H33: the coverage claim is wrong — see the H33 section; the guard is at
`statistics.py:159-160`, it is covered, and the real uncovered block is the dead
`deflated_sharpe_ratio` body. Measured `src/qtr` coverage is **94%**, not 99%.)* The
documented library drift in `walk_forward_splits` (changed 2026-10-19 09:28) still moves
`metrics.wf_stability` by ~1.3e-3 on a re-run of a published experiment; H29's/H30's rebuilds
are unaffected (they do not use that helper's output). The paid-data task remains unjustified for
every family in the repo.

**Which approaches have already failed and why.** None new this session. The fix was a minimal
restoration of an existing function's header; no runner, gate, threshold, verdict or certified
number was modified, no grid was re-run, and no published artifact was touched.

## H33 — three published benchmark gates were vacuous; they are repaired (2026-10-20)

**What changed.** H31 fixed the *raising* defect in `compare_to_benchmark` but not its
**consumption contract**. An audit of all **17** call sites in the repository against the
library's actual return-key set found three defects, each of which made a published benchmark
gate evaluate a **constant** instead of a statistic:

- **D1 (H4, `run_futures_tsmom_experiment.py:522`)** — read `alpha_res.get("p_value", 1.0)`;
  the library returns `alpha_p_value` and never `p_value`, so `p` was always 1.0 and the `p`
  gate always False. The published artifact `exp_2026-10-14T08-27-02-650342Z` carries the
  fingerprint: `"alpha_vs_benchmark": {"p_value": 1.0, ...}`.
- **D2 (H18, `run_h18_overnight_intraday_experiment.py:742`)** — (a) `oos_mask` was passed as
  the **third positional argument**, i.e. as `risk_free`, which silently turned
  `alpha_annualized` into a length-N array; (b) `.get("p_value", 1.0)` → `benchmark_p` always
  1.0 and the `benchmark_p` gate always False. The published artifact records
  `gate_metrics.benchmark_p.value = 1.0`.
- **D3 (H7, `run_h7_intraday_tsmom_experiment.py:403`)** — (a) `.get("alpha")`/`.get("p_value")`
  → `benchmark` = `{alpha: NaN, ir: -38.34, p_value: NaN}` and `max_p_value` compared
  `NaN < 0.05` → always False; (b) the benchmark was the **price level**
  `prices[FUTURES_UNIVERSE]` compared against a **return** series — a unit mismatch whose
  information ratio is −38.34 and whose alpha p-value is **0.0** (so had the key names been
  right, H7 would have published an *apparently significant* alpha from a meaningless
  comparison; the NaN default was the only thing that protected the record).

The other 14 call sites use the canonical keys and pass no third positional argument. The repair:
the library validates `risk_free` (a non-scalar raises `TypeError`), drops NaN rows **pair-wise**
(`np.cov`/`np.var` do not skip NaN, so one NaN used to leave alpha/beta/p NaN while
IR/win_rate stayed finite — an internally inconsistent dict that silently voided any gate reading
it) and fails closed on degenerate inputs; the three runners read the keys the library actually
returns; and H7's new module-level `benchmark_comparison()` helper builds the equal-weighted
**return** benchmark (`prices.pct_change().mean(axis=1)`, verified equal to the repo's committed
`benchmark_returns.parquet` with max abs diff **0.0**). `tests/test_benchmark_gate_contract.py`
(12 tests) pins the contract **statically** over every call site — at most two positional
arguments, and every key read off the result is a key the library returns.

**What was verified.** `python -m pytest -q` → **725 passed** (713 + 12 new), 0 warnings;
`python -m pytest -W error -q` → 725 passed; `python -m pytest --cov=qtr --cov-report=term-missing`
→ 725 passed, `src/qtr` coverage **94%** (the same 16 uncovered statements as the HEAD baseline —
the dead `deflated_sharpe_ratio` body — so no regression);
`python -m ruff check src tests run_*.py` → All checks passed;
`python -m ruff format --check src tests run_*.py` → 78 files already formatted;
`bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
**Negative control:** the same suite run against the pre-fix source (`git stash -u`) fails **8
tests** and names the three defect sites, so the new contract is not vacuous. **Impact** (recomputed
offline from the committed artifacts; nothing published was touched): H4 p = **0.4592** (gate
still False → tally 1/8 unchanged; the published IR 0.33150832181222434 is reproduced
**bit-exactly**), H7 alpha 0.09987 / IR **+0.30022** / p 0.34319 (`min_information_ratio` False →
True → recomputed 5/9 vs published 4/9), H18 p = **0.04098500443612743** (gate False → True →
recomputed 3/9 vs published 2/9; the published IR −0.5967666565674836 is reproduced
**bit-exactly**). All three verdicts stay REJECT.

**What remains unresolved.** (i) The pre-registered benchmark-significance gate is
**direction-blind**: it is `p < max_p_value` on a **two-sided** t-test of the excess returns, so
it is satisfied by a significantly **negative** alpha — by the strategy being significantly
*worse* than the benchmark. **H19** (p = 0.00260, IR −0.8798), **H20** (p = 0.01595, IR −0.7040)
and **H23** (p = 0.00090, IR −3.0739) already carry such a PASS in the published record, and
H18's repaired gate passes for the same reason. The gate *definition* is pre-registered, so it is
not changed here — it is disclosed and named as the next task. (ii) The dead
`deflated_sharpe_ratio` in `src/qtr/validation/statistics.py` (lines 394–435) is unreachable: not
exported by `qtr/validation/__init__.py`, no runner or test calls it, and it duplicates
`run_h12_selection_bias_audit.py:deflated_sharpe_ratio` with the same `max_z` formula (correct,
merely unreachable) — it is the whole of the uncovered block. (iii) The H32 handoff's coverage
claim ("99%, one uncovered branch") is **wrong**: the measured HEAD baseline is **94%**, and its
named "uncovered branch" (the `walk_forward_splits` empty-window guard at
`statistics.py:159-160`) is covered by `tests/test_statistics.py:185`.

**Which approaches have already failed and why.** Fixing the runners by adding alias keys to the
library's return dict was rejected — it would leave the callers wrong and mask the next typo.
Changing the *direction* of the benchmark gate was not attempted: the gate definition is
pre-registered and changing it would change published gates. Re-running the H4/H7/H18 grids was
not done (forbidden and unnecessary): the benchmark statistics were recomputed offline from the
committed artifacts, reproducing the published OOS Sharpe and IR bit-exactly.

## H34 — the benchmark-significance gate is direction-aware (2026-10-20)

**What changed.** The pre-registered benchmark-significance gate is `p < max_p_value` on a
**two-sided** t-test of the excess returns, so it is satisfied by a significantly *negative*
alpha — by the strategy being significantly **worse** than the benchmark. H34 re-specified it,
implemented it once in the library, applied it at the benchmark-significance gate site of all
**17** runners, and re-disclosed the published record. **No published artifact, gate threshold,
verdict, certified number or published row was modified; no grid was re-run.**

**The gate** (`src/qtr/validation/statistics.py:benchmark_significance_gate`, exported from
`qtr.validation`):

```
p_gate = (two-sided p < max_p_value) AND (information_ratio > 0)
```

The frozen pre-registration proposed "one-sided `P(alpha > 0) < max_p_value`, equivalently the
conjunction `p < max_p_value` and `alpha_annualized > 0`". **The two are not equivalent**: the
one-sided rule at 5% is a two-sided **10%** test and therefore *loosens* the published gate,
while the conjunction keeps the published 5% two-sided level (the one-sided test at 2.5%). The
conjunction is implemented, because it can only ever *remove* a pass, and because it keeps every
committed artifact numerically reproducible from the code (the published `benchmark_p_value`
stays the two-sided p-value; H10's certified `4.790305556723297e-10` is still what the runner
publishes). The direction criterion is the sign of the **excess return** (IR > 0 — the sign of
the t-statistic the p-value is computed from), not the CAPM intercept, which can carry the
opposite sign (committed H16: IR = −0.3531 but `alpha_annualized` = +0.0124) and is not recorded
in the certified artifacts at all. The frozen pre-registration is **amended explicitly** — the
corrected equivalence, the widened scope ("the runners continue to gate on `alpha_p_value` …
exactly as before" is no longer true, and leaving it true would have left the defect live in the
code) and the complete family list — in `HYPOTHESIS_SPEC.md` §H34.

**Scope.** The library helper plus the benchmark-significance gate site of
`run_ts_momentum_experiment.py` (H1), `run_cs_momentum_experiment.py` (H2),
`run_regime_gated_momentum_experiment.py` (H3), `run_futures_tsmom_experiment.py` (H4),
`run_ddcv_experiment.py` (H5), `run_h6_vix_ddcv_experiment.py` (H6),
`run_h7_intraday_tsmom_experiment.py` (H7), `run_h8_rolladjusted_tsmom_experiment.py` (H8),
`run_h9_intraday_tsmom_experiment.py` (H9), `run_h10_intraday_tsmom_pfopt_experiment.py` (H10,
and H21/H22/H25 through its shared `_full_gate_eval`), `run_h12_selection_bias_audit.py` (H12),
`run_h16_factor_timing_experiment.py` (H16), `run_h17_vrp_experiment.py` (H17),
`run_h18_overnight_intraday_experiment.py` (H18), `run_h19_volume_predictive_experiment.py`
(H19), `run_h20_signed_volume_experiment.py` (H20), `run_h23_crypto_futures_tsmom.py` (H23).
`src/qtr/validation/statistics.py:deflated_sharpe_ratio` was **deleted** (dead: not exported, no
caller, duplicative of `run_h12_selection_bias_audit.py`'s own copy).

**Disclosure — the complete table** (recomputed offline from the committed artifacts, for every
family that owns a benchmark-significance gate; the pre-registration's list omitted H1, H2, H3,
H5, H8 and H21):

| Family | p | IR | published `p`-gate | H34 gate |
|--------|---|----|---------------------|----------|
| H1 | 0.78174 | −0.1241 | False | False |
| H2 | 0.57342 | −0.2523 | False | False |
| H3 | 0.046364 | −0.8932 | False | False |
| H4 | 1.0 (vacuous) | +0.3315 | False | False |
| H5 | 0.37864 | +0.3943 | False | False |
| H6 | 0.42178 | +0.3598 | False | False |
| H7 | null | — | False | False |
| H8 | 0.24133 | +0.5249 | False | False |
| H9 | 6.3295e-12 | +1.0210 | True | True |
| H10 | 4.7903e-10 | +0.9248 | True | **True (certified)** |
| H12 | 4.7903e-10 (Bonferroni) | +0.9248 | True | **True (certified)** |
| H16 | 0.20836 | −0.4764 | False | False |
| H17 | 0.53389 | −0.2396 | False | False |
| H18 | 1.0 (vacuous) | −0.5968 | False | False |
| H19 | 0.0026022 | −0.8798 | **True** | **False** |
| H20 | 0.0159482 | −0.7040 | **True** | **False** |
| H21 | 1.9148e-10 | +0.9459 | True | True |
| H22 | 1.3341e-19 | +1.3467 | True | **True (certified)** |
| H23 | 0.00089959 | −3.0739 | **True** | **False** |
| H25 | 1.4029e-19 | +1.3459 | True | **True (certified)** |

**Four published artifacts carry a wrong-reason PASS**: H3's earlier artifact
`exp_2026-10-10T21-27-13-928282Z` (p = 0.046364, IR = −0.8932; H3's *published* row comes from
the later artifact `exp_2026-10-10T21-28-20-920399Z`, which already records the gate as False),
H19, H20 and H23. Their published tallies (3/9, 2/9, 2/9) would read 2/9, 1/9 and 1/9 on a
re-run; H18's H33-repaired gate (p = 0.041, IR = −0.597) stays False, so its repaired tally
returns to the published 2/9. **No verdict changes** and no published row is modified.
**Certified-family survival: yes** — H10, H22, H25 (and H9, H12, H21) pass.

**What was actually verified.** `python -m pytest -q` → **735 passed** (726 + 9 new), ~3m37s;
`python -m pytest -W error -q` → clean; `python -m pytest --cov=qtr --cov-report=term-missing` →
**735 passed**, `src/qtr` coverage **100%** (1010 statements, 0 missed — the dead-code deletion
removed the last uncovered block); `ruff check` / `ruff format --check` → clean; `bash -n
.github/scripts/*.sh` and `bash .github/scripts/test_kilo_progress.sh` → OK.
**Negative control**: the new test module replayed against the pre-H34 source (`git stash -u`,
test file restored) fails **7** tests and names the 17 runners without the helper and the 19
sites that read the one-sided p-value — the contract is not vacuous. The disclosure table was
recomputed from the committed `.experiments/artifacts/*/summary.json`, not from the runners.

**Which approaches have already failed and why.** The one-sided p-value as the gate statistic was
tried first (an intermediate commit read `alpha_p_value_one_sided` in twelve runners) and was
reverted: it loosens the published gate (one-sided 5% = two-sided 10%) and changes every
published `benchmark_p_value`, which would have broken the reproducibility of the certified
artifacts. The CAPM-intercept direction criterion was rejected: it is not the direction the
p-value tests, it disagrees with the information ratio in committed artifacts (H16, H17) and it
is not recorded in the certified artifacts, so it could not have been verified from the record.
Leaving the runners untouched (the frozen pre-registration's scope) was rejected: it would have
left the defect live in the code. Rewriting the published rows and re-running the grids were not
done (forbidden and unnecessary).

**What remains unresolved.** The committed artifacts of H19/H20/H23 still record the pre-H34 gate
boolean while the code computes the direction-aware value — the two artifact-adjacent tests that
assert the old identity must be rewritten to assert the disclosed state (see the next task). The
report's coverage and test-count bullets are stale (the dead code is gone). The library's
`alpha_p_value_one_sided` field is now an informational output that no runner reads.

## One precise next task

**Close the artifact/code disagreement for the three wrong-reason families and re-baseline the
report's coverage and test-count bullets** (H34's leftovers; full statement in `NEXT_TASK.md`).

H34 re-specified the benchmark-significance gate and closed it in the code, but the committed
artifacts of H19, H20 and H23 still record the **pre-H34** gate boolean (`passes["p"] = true`)
while the current code computes `false`. The artifacts are immutable, so the disagreement has to
be pinned in the artifact-adjacent tests: `tests/test_h20_signed_volume.py:453` and
`tests/test_h23_crypto_futures_tsmom.py:542` still assert the pre-H34 identity
`p["p"] == (benchmark_p_value < max_p_value)`; rewrite them to assert the **disclosed** state
(the artifact records the pre-H34 rule, the information ratio is negative, the published pass is
a wrong-reason pass, the direction-aware gate is `False`). Then extend
`tests/test_benchmark_gate_contract.py` with the tally-impact pin (H19 3/9 → 2/9, H20 2/9 → 1/9,
H23 2/9 → 1/9), re-run the suite and update the `FINAL_REPORT.md` §Summary statistics test-count
bullet (it reads "735/735 passing" — H34 measured **735/735**; the coverage bullet is already
correct: `src/qtr` is at **100%**, 1010 statements, 0 missed, after the dead-code deletion). Do
**not** re-run any grid and do **not** touch the published rows.

Constraints carried forward: no published artifact, gate threshold, verdict or certified number
may be modified; no grid may be re-run; every recomputed number is a disclosure; the pre-existing
H1–H30 hypothesis space remains exhausted — no new hypothesis is warranted.

The pre-registered free-data hypothesis space (H1–H30) remains exhausted: every family has a
committed artifact or a documented reason for the gap, every daily/monthly family is `CAUSAL` and
REJECTED, every intraday family is `CAUSAL_REJECTED` under H28, and the paid-data task (a wider
OOS window for the PF bootstrap margin) is unjustified for every family in the repo — H28 closed
it for the intraday family and H29/H30 show the daily families are causal but all REJECT. Buying
more free-data-equivalent data changes no verdict.

If the next agent is given a *new* assignment, verify with:
`python -m pytest -q`, `python -m pytest -W error -q`,
`python -m pytest --cov=qtr --cov-report=term-missing`,
`python -m ruff check src tests run_*.py`, `python -m ruff format --check src tests run_*.py`,
plus `bash -n .github/scripts/*.sh` and `bash .github/scripts/test_kilo_progress.sh`.
Note: `qtr` must be importable — run `pip install -e .` from the repo root if
`ModuleNotFoundError: No module named 'qtr'` appears at collection time.
