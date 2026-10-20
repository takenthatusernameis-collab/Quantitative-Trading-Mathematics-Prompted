# HANDOFF_CURRENT — session complete (H36)

## State
- **H36 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: the shared research infrastructure (`qtr.strategies` +
  `qtr.backtest`) is now pinned by an executable **point-in-time (no look-ahead) invariant**,
  and the test suite runs from a bare clone with no install step.
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

## What changed (this session — H36)
- `tests/test_causality_invariant.py` (new, 30 tests + 1 skip) — the executable
  **point-in-time invariant** for the shared infrastructure: every strategy in
  `qtr.strategies.STRATEGY_REGISTRY` and the whole of `qtr.backtest` must satisfy
  *"no output observed at or before bar t may depend on any price strictly after bar t"*.
  Checked by future perturbation at every bar of a reduced sample (dense sweep) and at nine
  cut points on the full sample with the runners' lookbacks (sparse sweep); end-to-end
  through `run_backtest` (returns, positions, equity curve, trade log). Backed by a negative
  control, a non-vacuity check, a registry coverage pin, two static look-ahead checks (no
  negative `shift`, no backward `pct_change`/`diff` period) and a rebalance cost-timing test.
- `pyproject.toml` — `pythonpath = ["src"]` under `[tool.pytest.ini_options]`, so
  `python -m pytest` runs from a bare clone with no install step. Before this the suite
  could not even be collected (`ModuleNotFoundError: No module named 'qtr'`) because the
  package is not pip-installed in this environment.
- `NEXT_TASK.md`, `HANDOFF_NEXT.md`, `HANDOFF_CURRENT_SESSION.md`.
- No `src/qtr` source file was changed; no published artifact, gate threshold, verdict,
  certified number or published row was modified; no grid was re-run.

## What was actually verified
- Baseline (before this session): `PYTHONPATH=src python -m pytest -q -W error` → **750
  passed** in 161 s.
- After: `python -m pytest -q -W error` (no `PYTHONPATH`, no install) → **780 passed, 1
  skipped** in 167 s.
- `python -m pytest --cov=qtr --cov-report=term-missing` → `src/qtr` coverage **100%** (1011
  statements, 0 missed).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
  `python -m ruff format --check src tests run_*.py` → *81 files already formatted*.
- Negative controls injected into `src/qtr/strategies/baselines.py` and then restored
  (`git diff` on the file is empty): a negative `shift` → **3 tests fail**; a backward
  `pct_change` → **4 tests fail**; a *non-leak* control (the `skip` removed) → **all 30
  tests still pass**.
- H35 cross-checks still hold: H7's published artifact is 4/9 with two free PASSes (2/7 on
  the evaluable gates); H18's published artifact (`exp_2026-10-13T22-14-50-729923Z`) is 2/9
  with one free PASS (1/8 on the evaluable gates). Both are REJECT before and after.

## What remains unresolved
- The **runners' inline signal code** is not covered by a generic causality probe (H23 and
  H28 only). This is the next task.
- The engine's `metrics["total_return"]` excludes the first bar and is therefore inconsistent
  with its own equity curve and with `annualized_return`'s period count. **Disclosure only**:
  `metrics` values are in published artifacts and the record is frozen.
- `DataFetcher.fetch_sp500_constituents(date=...)` silently ignores `date` and returns the
  *current* constituent list — a latent survivorship-bias footgun; no runner calls it.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted and the
  certified families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)
- **A single cut point per causality probe was insufficient**: a perturbation at cut `c` can
  only expose a leak that reads *past* bar `c`, so a one-bar-ahead leak at bar `t` is
  detected only at cut `t`; the single-cut version also failed its own negative control (a
  sign-based leak whose sign did not flip). Replaced by a dense per-bar sweep plus a sparse
  sweep with the runners' lookbacks, and by forcing the first perturbed bar's factor to 0.5.
- **Repairing the disclosed gates for real was rejected**: it needs the H7/H18 grids re-run
  (forbidden) and would change published tallies. They are disclosed and pinned instead.
- **Rewiring H18's hard-coded thresholds to a shared `GATES` dict was rejected** as a structural
  change to a runner that produced a published artifact; the equality with the shared set
  is pinned by a test instead.
- **Re-deriving the intraday Sharpe scale was not attempted**: H26 already audited it and
  concluded the mis-scaling understates the intraday family and invalidates no verdict.

## Precise next task (one task), with evidence and constraints
- **Extend the point-in-time invariant from the shared library to the runners' inline signal
  code** — see `NEXT_TASK.md` for the full statement, the inventory to build and the
  constraints. Any follow-up must not modify published artifacts, gates, thresholds,
  verdicts or certified numbers; must not re-run grids; must follow the "change approach
  after repeated failure" rule; and must preserve the existing invariants.
