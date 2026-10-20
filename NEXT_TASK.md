# Next Task — H34 complete; the direction-aware benchmark gate is closed in code (2026-10-20)

## State

**H34 is COMPLETE.** The benchmark-significance gate is no longer direction-blind: it is
re-specified as `p < max_p_value` **and** a positive excess return, implemented once in the
library and applied at the benchmark-significance gate site of all 17 runners. The published
record is re-disclosed in full. **No published artifact, gate threshold, verdict, certified
number or published row was modified; no grid was re-run.** The published rows stand as the
historical record; the recomputed tallies below are a disclosure, not a rewrite.

### What changed

- `src/qtr/validation/statistics.py:benchmark_significance_gate` (new, exported from
  `qtr.validation`) — the single implementation of the re-specified gate:
  `p_gate = (two-sided p < max_p_value) AND (information_ratio > 0)`. It can only ever *remove*
  a pass, never manufacture one.
- 17 runners — the benchmark-significance gate site of `run_ts_momentum_experiment.py` (H1),
  `run_cs_momentum_experiment.py` (H2), `run_regime_gated_momentum_experiment.py` (H3),
  `run_futures_tsmom_experiment.py` (H4), `run_ddcv_experiment.py` (H5),
  `run_h6_vix_ddcv_experiment.py` (H6), `run_h7_intraday_tsmom_experiment.py` (H7),
  `run_h8_rolladjusted_tsmom_experiment.py` (H8), `run_h9_intraday_tsmom_experiment.py` (H9),
  `run_h10_intraday_tsmom_pfopt_experiment.py` (H10, and H21/H22/H25 through its shared
  `_full_gate_eval`), `run_h12_selection_bias_audit.py` (H12),
  `run_h16_factor_timing_experiment.py` (H16), `run_h17_vrp_experiment.py` (H17),
  `run_h18_overnight_intraday_experiment.py` (H18), `run_h19_volume_predictive_experiment.py`
  (H19), `run_h20_signed_volume_experiment.py` (H20), `run_h23_crypto_futures_tsmom.py` (H23).
  The published `benchmark_p_value` stays the **two-sided** p-value, so every committed artifact
  remains numerically reproducible from the code.
- `tests/test_benchmark_gate_contract.py` — 9 new tests: the gate's truth table, the
  "never manufactures a pass" property, the fail-closed behaviour, a static contract that **no**
  runner compares a p-value against `max_p_value` directly, a static contract that no runner
  publishes the one-sided p-value, a static contract that every runner with a benchmark gate
  calls the helper, and an artifact sweep that fails if any committed artifact carries an
  **undisclosed** wrong-reason benchmark pass (the disclosed set is pinned).
- `HYPOTHESIS_SPEC.md` §H34 (the frozen pre-registration **plus** its amendment: the corrected
  equivalence, the widened scope and the complete disclosure table), `FINAL_REPORT.md` (§H34
  detail, the table footnote, the Next Task section), `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md`,
  `HANDOFF.md`.
- `src/qtr/validation/statistics.py:deflated_sharpe_ratio` — **deleted** (it was dead: not
  exported, no caller, duplicative of `run_h12_selection_bias_audit.py`'s own copy).

### Why the conjunction and not the one-sided p-value

The frozen pre-registration proposed "one-sided `P(alpha > 0) < max_p_value`, equivalently the
conjunction `p < max_p_value` and `alpha_annualized > 0`". **The two are not equivalent**: the
one-sided rule at 5% is a two-sided 10% test and *loosens* the published gate, while the
conjunction keeps the published 5% two-sided level. The conjunction is implemented because it
can only remove a pass, and because it keeps the published artifact number (the two-sided p)
unchanged. The direction criterion is the sign of the **excess return** (IR > 0), not the CAPM
intercept: the IR carries the sign of the t-statistic the p-value is computed from, whereas the
CAPM intercept can carry the opposite sign (committed H16: IR = −0.3531, `alpha_annualized` =
+0.0124) and is not recorded in the certified artifacts at all. See `HYPOTHESIS_SPEC.md` §H34
"Amendment 1" for the full reasoning.

### The quantified impact (recomputed offline from the committed artifacts)

| Family | p | IR | published `p`-gate | H34 gate | note |
|--------|---|----|---------------------|----------|------|
| H1 | 0.78174 | −0.1241 | False | False | — |
| H2 | 0.57342 | −0.2523 | False | False | — |
| H3 | 0.046364 | −0.8932 | False | False | the *earlier* artifact `exp_2026-10-10T21-27-13-928282Z` records a wrong-reason PASS (4/10 gates); the published row comes from `exp_2026-10-10T21-28-20-920399Z` (3/10) |
| H4 | 1.0 (vacuous) | +0.3315 | False | False | H33 repair: p = 0.4592 → still False |
| H5 | 0.37864 | +0.3943 | False | False | — |
| H6 | 0.42178 | +0.3598 | False | False | — |
| H7 | null | — | False | False | H30: benchmark unavailable |
| H8 | 0.24133 | +0.5249 | False | False | — |
| H9 | 6.3295e-12 | +1.0210 | True | True | genuine |
| H10 | 4.7903e-10 | +0.9248 | True | **True** | **certified** |
| H12 | 4.7903e-10 (Bonferroni) | +0.9248 | True | **True** | **certified** |
| H16 | 0.20836 | −0.4764 | False | False | — |
| H17 | 0.53389 | −0.2396 | False | False | — |
| H18 | 1.0 (vacuous) | −0.5968 | False | False | H33 repair: p = 0.041 → wrong reason → still False (tally returns to the published 2/9) |
| H19 | 0.0026022 | −0.8798 | **True** | **False** | **wrong-reason pass**; 3/9 → 2/9 |
| H20 | 0.0159482 | −0.7040 | **True** | **False** | **wrong-reason pass**; 2/9 → 1/9 |
| H21 | 1.9148e-10 | +0.9459 | True | True | genuine |
| H22 | 1.3341e-19 | +1.3467 | True | **True** | **certified** |
| H23 | 0.00089959 | −3.0739 | **True** | **False** | **wrong-reason pass**; 2/9 → 1/9 |
| H25 | 1.4029e-19 | +1.3459 | True | **True** | **certified** |

**Certified-family survival: yes.** H10, H22 and H25 (and H9, H12, H21) pass the direction-aware
gate. No certified family and no certified number is affected.

The contract is not vacuous: the same test module run against the pre-H34 source (`git stash -u`)
fails **7** tests (three behavioural gate tests, the certified-family survival test, and the
three static contracts) and names the 17 runners that lacked the direction-aware gate.

## The next task (one, precise)

**Close the artifact/code disagreement for the three wrong-reason families, and re-baseline the
report's coverage and test-count bullets.**

The committed artifacts of H19, H20 and H23 record the **pre-H34** gate boolean
(`passes["p"] = true`), while the current code computes `false`. The artifacts are immutable, so
the disagreement has to be pinned in the *artifact-adjacent tests* rather than in the artifacts:

1. `tests/test_h20_signed_volume.py:453` and `tests/test_h23_crypto_futures_tsmom.py:542` still
   assert the pre-H34 identity `p["p"] == (benchmark_p_value < max_p_value)`. Rewrite them to
   assert the **disclosed** state explicitly: the artifact records the pre-H34 rule, the family's
   information ratio is negative, the published pass is a wrong-reason pass, and the
   direction-aware gate is `False`. (Both families' `information_ratio` is already in the
   artifact's `metrics`.) The same shape is checked for H19 in `tests/test_h19_volume_predictive.py`
   if a gate-value assertion is added there.
2. Extend `tests/test_benchmark_gate_contract.py` to pin the **tally** impact as a disclosure
   (H19 3/9 → 2/9, H20 2/9 → 1/9, H23 2/9 → 1/9) so the recomputed numbers cannot drift.
3. Re-run the suite and update the `Summary statistics` bullets of `FINAL_REPORT.md`:
   the test-count bullet (it currently reads "735/735 passing" — the count changes with the
   new/rewritten tests). The **coverage** bullet was re-measured by H34 and is already correct
   (`src/qtr` is at **100%**, 1010 statements, 0 missed — the dead `deflated_sharpe_ratio` is
   gone), so only the test count needs re-stating after the test changes.

Evidence and constraints:

- Constraints carried forward: no published artifact, gate threshold, verdict or certified
  number may be modified; no grid may be re-run; every recomputed number is a disclosure; the
  pre-existing H1–H30 hypothesis space remains exhausted — no new hypothesis is warranted.
- Do **not** re-run any grid: the benchmark statistics are recomputed offline from the committed
  artifacts, which is sufficient and is what the repo's H30/H33 pattern prescribes.
- Do **not** "fix" the committed artifacts' `passes["p"]` values: they are the historical record.

## Also carried forward (small, independent)

- `src/qtr/validation/statistics.py:benchmark_significance_gate` is exported but the library's
  `alpha_p_value_one_sided` field (added for H34) is **not** read by any runner — it is the
  informational one-sided view of the same comparison. Either keep it as a documented library
  output or remove it in the same cleanup as (3) above; it must not be mistaken for the gate's
  statistic (the gate is the two-sided p-value plus the direction requirement).
