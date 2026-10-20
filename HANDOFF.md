# HANDOFF — H35 complete (session handoff)

## What changed
**H35 is complete.** The last open *gate-defect* class is closed: an offline static audit of
every gate site in every `run_*.py` found the gates that are a **constant** or that compare a
**placeholder** (and can therefore never fail) — H7's `min_perturbed_sharpe_ratio` and
`min_worst_regime_sharpe` (hard-coded `True`) and H18's `perturbation_ratio` (a placeholder
constant) — plus one latent *permissive default* (H4/H5/H6 read their IR threshold as
`GATES.get("min_information_ratio", -1e18)`).

- `run_futures_tsmom_experiment.py:547`, `run_ddcv_experiment.py:457`,
  `run_h6_vix_ddcv_experiment.py:553` — the IR threshold is now read by direct subscript.
  Behaviour-preserving: the key exists in all three and its value is unchanged, so no
  published number, tally, threshold or verdict changes.
- `src/qtr/validation/statistics.py:compare_to_benchmark` — the docstring now states that
  `alpha_p_value_one_sided` is an informational view and **not** the gate's statistic (a
  one-sided 5% test is a two-sided 10% test, so it is strictly looser). This closes the item
  H34 carried forward.
- `tests/test_gate_vacuity_contract.py` (new, 11 tests) and one new test in
  `tests/test_benchmark_gate_contract.py`.
- `HYPOTHESIS_SPEC.md` §H35, `FINAL_REPORT.md` §H35 + the re-baselined `Summary statistics`
  and `Next Task` sections, `NEXT_TASK.md`, the `HANDOFF*` files.

## What was actually verified
- `python -m pytest -q -W error` → **748 passed** (736 + 12 new).
- `python -m pytest --cov=qtr --cov-report=term-missing` → `src/qtr` coverage **100%**
  (1010 statements, 0 missed).
- **Negative control:** the new module run against the pre-H35 runner sources
  (`git checkout` of the three changed runners) fails **1** test and names the three
  permissive-default sites — the contract really binds the change.
- The published H18 artifact was cross-checked against its Measure Log: the published row is
  `exp_2026-10-13T22-14-50-729923Z` (2/9); the two earlier siblings are 3/9 (their
  `max_drawdown` gate still read `True` against a 22.2% drawdown / 15% limit).

## What remains unresolved
- **None of the gate classes.** H33 (vacuous gates), H34 (direction-blind gate) and H35
  (non-evaluating gates) between them cover every gate defect that has surfaced in this
  repository, and each is now pinned by an executable invariant.
- The `ruff` verification step quoted throughout the record is **not reproducible from the
  repository**: ruff is not declared in `pyproject.toml`/`requirements.txt`, is not installed
  in the agent environment, and no ruff configuration is committed (the sources carry
  `# noqa: BLE001` / `# noqa: UP045` markers that assume a non-default rule selection).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families (H10, H11, H12, H22, H25) are frozen.

## Approaches already tried / failed (and why)
- **Making the disclosed gates evaluate for real (H7's perturbation / worst-regime, H18's
  perturbation) was rejected**: it requires re-running the H7/H18 grids (forbidden by the
  carried-forward constraints) and would change published tallies. The gates are therefore
  *disclosed and pinned* rather than silently repaired.
- **Rewiring H18's hard-coded thresholds to a shared `GATES` dict was rejected** as a
  structural change to a runner that produced a published artifact; instead the equality of
  H18's thresholds with the shared set is *pinned by a test*, so a drift becomes visible.

## Precise next task (one task), with evidence and constraints
**None assigned.** If a future session picks one up, the only bounded item left is the
`ruff` reproducibility gap described in `NEXT_TASK.md`: declare ruff in
`pyproject.toml` (`[project.optional-dependencies] lint`), commit the ruff configuration
that makes the quoted commands meaningful, and re-measure `ruff check src tests run_*.py`
and `ruff format --check src tests run_*.py` **before** quoting them again (ruff is
currently absent from the environment — `python -m ruff` → "No module named ruff"). Do not
re-run any grid; do not modify a published artifact, gate threshold, verdict or certified
number; do not add a hypothesis.
