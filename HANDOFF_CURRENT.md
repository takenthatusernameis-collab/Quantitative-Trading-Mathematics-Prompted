# HANDOFF — H34: the benchmark-significance gate is direction-aware (2026-10-20)

## What changed

**H34 — the pre-registered benchmark-significance gate was direction-blind: `p < max_p_value` on a
two-sided t-test of the excess returns is satisfied by a significantly *negative* alpha, i.e. by
the strategy being significantly **worse** than the benchmark. The gate is re-specified, closed in
the code for all 17 runners, and the published record is re-disclosed in full. No published
artifact, gate threshold, verdict, certified number or published row was modified; no grid was
re-run.**

### New

- `src/qtr/validation/statistics.py:benchmark_significance_gate(p_value, information_ratio,
  max_p_value=0.05)` — the single implementation of the re-specified gate, exported from
  `qtr.validation`. `p_gate = (two-sided p < max_p_value) AND (information_ratio > 0)`: the
  pre-registered significance level is kept and the direction of the excess return is added. The
  gate can only ever *remove* a pass, never manufacture one.
- `tests/test_benchmark_gate_contract.py` — **9 new tests** (the module had 12 from H33):
  - the gate's truth table (a significantly negative excess return never passes; the threshold
    is strict; a zero information ratio is not a positive excess return);
  - the "never manufactures a pass" property over a 101 x 5 grid of (p, IR);
  - fail-closed behaviour on NaN / -inf inputs;
  - a **static contract** that *no* runner compares a p-value against `GATES["max_p_value"]`
    directly — every benchmark significance gate must go through the helper;
  - a **static contract** that *no* runner reads `alpha_p_value_one_sided` — the published
    `benchmark_p_value` must stay the two-sided p-value so the committed artifacts remain
    reproducible from the code;
  - a **static contract** that every runner with a benchmark gate calls the helper (the expected
    set of 17 runners is listed, so the contract cannot be satisfied by deleting the gates);
  - an **artifact sweep** that fails if any committed artifact carries an *undisclosed*
    wrong-reason benchmark pass, plus a pin of the disclosed set and of the certified families'
    survival.

### Changed

- **17 runners** — the benchmark-significance gate site now calls
  `benchmark_significance_gate(...)`: `run_ts_momentum_experiment.py` (H1),
  `run_cs_momentum_experiment.py` (H2), `run_regime_gated_momentum_experiment.py` (H3),
  `run_futures_tsmom_experiment.py` (H4), `run_ddcv_experiment.py` (H5),
  `run_h6_vix_ddcv_experiment.py` (H6), `run_h7_intraday_tsmom_experiment.py` (H7),
  `run_h8_rolladjusted_tsmom_experiment.py` (H8), `run_h9_intraday_tsmom_experiment.py` (H9),
  `run_h10_intraday_tsmom_pfopt_experiment.py` (H10, and H21/H22/H25 through its shared
  `_full_gate_eval`), `run_h12_selection_bias_audit.py` (H12),
  `run_h16_factor_timing_experiment.py` (H16), `run_h17_vrp_experiment.py` (H17),
  `run_h18_overnight_intraday_experiment.py` (H18), `run_h19_volume_predictive_experiment.py`
  (H19), `run_h20_signed_volume_experiment.py` (H20), `run_h23_crypto_futures_tsmom.py` (H23).
  The published `benchmark_p_value` remains the **two-sided** p-value in every one of them.
- `src/qtr/validation/__init__.py` — exports `benchmark_significance_gate`.
- `src/qtr/validation/statistics.py:deflated_sharpe_ratio` — **deleted** (dead: not exported, no
  caller, duplicative of `run_h12_selection_bias_audit.py`'s own copy with the same formula).
- `HYPOTHESIS_SPEC.md` §H34 — the frozen pre-registration **plus** an explicit amendment that
  corrects three of its statements (the false "equivalently", the "no runner gate is changed"
  scope, and the incomplete family list) with the reason for each correction.
- `FINAL_REPORT.md` — the table footnote, the `Summary statistics` bullet, the `Next Task`
  section and a new `## H34` detail section with the complete disclosure table.
- `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF.md`.

### Why the conjunction and not the one-sided p-value (the one substantive judgement)

The frozen pre-registration proposed "one-sided `P(alpha > 0) < max_p_value`, equivalently the
conjunction `p < max_p_value` and `alpha_annualized > 0`". **The two are not equivalent**: the
one-sided rule at 5% is a two-sided **10%** test and therefore *loosens* the published gate,
while the conjunction keeps the published 5% two-sided level (it is the one-sided test at 2.5%).
The conjunction is what is implemented, because (i) it can only remove a pass, (ii) it keeps every
committed artifact numerically reproducible from the code (the published p-value stays two-sided;
H10's certified `4.790305556723297e-10` is still what the runner publishes), and (iii) the
direction criterion is the sign of the **excess return** (IR > 0) — the sign of the t-statistic
the p-value is computed from — rather than the CAPM intercept, which can carry the opposite sign
(committed H16: IR = −0.3531 but `alpha_annualized` = +0.0124) and is not recorded in the
certified artifacts at all.

## What was actually verified

- `python -m pytest -q` → **735 passed** (726 before + 9 new), ~3m37s.
- `python -m pytest -W error -q` → clean (**735 passed**), no warnings.
- `python -m pytest --cov=qtr --cov-report=term-missing` → **735 passed**; `src/qtr` coverage is
  **100%** (1010 statements, 0 missed) — deleting the dead `deflated_sharpe_ratio` removed the
  last uncovered block and H34's helper is fully covered.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 78 files already formatted.
- `bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
- **Negative control**: the new test module run against the pre-H34 source (`git stash -u`, with
  the test file restored) fails **7 tests** — the three behavioural gate tests, the
  certified-family survival test, and the three static contracts — and names the 17 runners that
  lacked the direction-aware gate and the 19 sites that read the one-sided p-value. The
  contract is therefore not vacuous.
- **The disclosure table was recomputed offline from the committed artifacts**
  (`.experiments/artifacts/*/summary.json`), not from the runners: every family with a
  benchmark-significance gate is covered (20 rows), the four wrong-reason passes are pinned by
  the artifact sweep, and the certified families' p-value/IR pairs are pinned to the digit.
- The full `run_*.py` sweep found **no** remaining bare p-value comparison against
  `max_p_value` outside the helper and **no** remaining read of `alpha_p_value_one_sided`.

## What remains resolved (this session)

- The artifact/code disagreement for the three wrong-reason families is now pinned in the
  artifact-adjacent tests rather than the immutable artifacts:
  `tests/test_h20_signed_volume.py` and `tests/test_h23_crypto_futures_tsmom.py` assert the
  disclosed state (artifact records the pre-H34 rule, information ratio negative, published pass
  is a wrong-reason pass, direction-aware gate `False`), replacing the pre-H34 identity
  assertions at the former lines 453 and 542. The same shape applies to H19 (its artifact
  already carries only metric-key assertions; no gate-value assertion existed to rewrite).
- `tests/test_benchmark_gate_contract.py` now pins the tally impact as a disclosure
  (`test_h34_tally_impact_is_pinned_as_a_disclosure`: H19 3/9 → 2/9, H20 2/9 → 1/9,
  H23 2/9 → 1/9).
- `FINAL_REPORT.md` §Summary statistics test-count bullet re-baselined to **736/736 passing**
  (10 H34 tests); the coverage bullet was already correct (**100%**, 1010 statements, 0 missed).

Nothing remains unresolved from H34.

## Approaches that failed / were not taken

- **The one-sided p-value as the gate statistic** (`alpha_p_value_one_sided < max_p_value`) was
  tried first — it is what an intermediate commit did for twelve runners. It was reverted because
  it *loosens* the published gate (a one-sided 5% test is a two-sided 10% test) and because it
  changes the published `benchmark_p_value` of every family, which would have broken the
  reproducibility of the certified artifacts (H10's certified value is pinned in
  `tests/test_certified_artifact_values.py`).
- **The CAPM-intercept direction criterion** (`alpha_annualized > 0`, as the frozen text and the
  H33 assignment named it) was rejected: it is not the direction the p-value tests, it disagrees
  with the information ratio in committed artifacts (H16: IR −0.3531 vs alpha +0.0124; H17: IR
  −0.2396 vs alpha +0.0541), and the certified families' artifacts do not record it at all, so it
  could not have been verified from the committed record.
- **Leaving the runners untouched** (the frozen pre-registration's scope) was rejected: it would
  have left the defect live in the code, so the next run would publish the same direction-blind
  gate. The scope change is recorded as an explicit amendment with its impact.
- **Rewriting the published rows / re-running the grids** was not done (forbidden by the repo's
  rules and unnecessary): the benchmark statistics are recomputed offline from the committed
  artifacts.

## One precise next task

**Close the artifact/code disagreement for the three wrong-reason families and re-baseline the
report's test-count bullet.** Concretely: rewrite
`tests/test_h20_signed_volume.py:453` and `tests/test_h23_crypto_futures_tsmom.py:542` so they
assert the *disclosed* state (the artifact records the pre-H34 rule; the information ratio is
negative; the published pass is a wrong-reason pass; the direction-aware gate is `False`), extend
`tests/test_benchmark_gate_contract.py` with the tally-impact pin (H19 3/9 → 2/9, H20 2/9 → 1/9,
H23 2/9 → 1/9), re-run the suite and update the `Summary statistics` test-count bullet of
`FINAL_REPORT.md` (the coverage bullet is already correct: 100%). Constraints: no published
artifact, gate threshold, verdict or certified number may be modified; no grid may be re-run;
every recomputed number is a disclosure; the H1–H30 hypothesis space remains exhausted. The
full statement is in `NEXT_TASK.md`.
