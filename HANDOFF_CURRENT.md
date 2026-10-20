# HANDOFF_CURRENT — session complete (H35)

## State
- **H35 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md` and `HANDOFF_NEXT.md`.
- Every gate defect class that has surfaced in this repository is now closed by an
  executable invariant: H33 (vacuous benchmark gates), H34 (direction-blind benchmark
  gate), H35 (non-evaluating gates: a constant, or a comparison against a placeholder).
- The H35 audit found **three** non-evaluating gates — H7's `min_perturbed_sharpe_ratio`
  and `min_worst_regime_sharpe` (hard-coded `True`) and H18's `perturbation_ratio` (a
  placeholder constant) — and **one** latent permissive default (H4/H5/H6 read the IR
  threshold as `GATES.get("min_information_ratio", -1e18)`), now fixed.
- **No certified family owns a non-evaluating gate.** The certified families (H9, H10,
  H11, H12, H21, H22, H25) and every other family evaluate all of their gates.
- No published artifact, gate threshold, verdict, certified number or published row was
  modified; no grid was re-run.

## What changed (this session)
- `run_futures_tsmom_experiment.py`, `run_ddcv_experiment.py`,
  `run_h6_vix_ddcv_experiment.py` — the IR threshold is read by direct subscript
  (behaviour-preserving: same key, same value).
- `src/qtr/validation/statistics.py` — `compare_to_benchmark`'s docstring now states that
  `alpha_p_value_one_sided` is informational and **not** the gate's statistic.
- `tests/test_gate_vacuity_contract.py` (new, 11 tests) and one new test in
  `tests/test_benchmark_gate_contract.py`.
- `HYPOTHESIS_SPEC.md` §H35, `FINAL_REPORT.md` §H35 + re-baselined `Summary statistics` and
  `Next Task` sections, `NEXT_TASK.md`, the `HANDOFF*` files.

## What was actually verified
- `python -m pytest -q -W error` → **748 passed** (736 + 12 new).
- `python -m pytest --cov=qtr --cov-report=term-missing` → `src/qtr` coverage **100%**
  (1010 statements, 0 missed).
- Negative control: the new module against the pre-H35 runner sources fails **1** test and
  names the three permissive-default sites.
- Artifact cross-check: H7's published artifact is 4/9 with two free PASSes (2/7 on the
  evaluable gates); H18's published artifact (`exp_2026-10-13T22-14-50-729923Z`, named in
  its Measure Log) is 2/9 with one free PASS (1/8 on the evaluable gates). Both are REJECT
  before and after.

## What remains unresolved
- None of the gate classes. The pre-registered free-data hypothesis space (H1–H30) is
  exhausted and the certified families' numbers and verdicts are frozen.
- The `ruff` verification step quoted throughout the published record cannot be reproduced
  from the repository (ruff is not declared in `pyproject.toml`/`requirements.txt`, is not
  installed in the environment, and no ruff configuration is committed). Recorded in
  `NEXT_TASK.md`; deliberately not started here.

## Approaches already tried / failed (and why)
- Repairing the disclosed gates for real was rejected: it needs the H7/H18 grids re-run
  (forbidden) and would change published tallies. They are disclosed and pinned instead.
- Rewiring H18's hard-coded thresholds to a shared `GATES` dict was rejected as a structural
  change to a runner that produced a published artifact; the equality with the shared set
  is pinned by a test instead.

## Precise next task (one task), with evidence and constraints
- **None assigned.** The one bounded item left is the `ruff` reproducibility gap recorded in
  `NEXT_TASK.md`. Any follow-up must not modify published artifacts, gates, thresholds,
  verdicts or certified numbers; must not re-run grids; must follow the "change approach
  after repeated failure" rule; and must preserve the existing invariants.
