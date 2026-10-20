# HANDOFF_NEXT — one task: extend the point-in-time invariant to the runners (H36 complete)

**The next task is assigned** (see `NEXT_TASK.md` for the full statement):

> Extend the point-in-time invariant from the shared library to the runners' inline signal
> code. The shared library (`qtr.strategies`) and the engine (`qtr.backtest`) are now
> covered by `tests/test_causality_invariant.py`; the runners
> (`run_h10/h12/h16/h18/h19/h20/h21/h22/h25/h27/h29`) still build their position series
> inline and are covered only for H23 and H28. Deliver an inventory of the runners' signal
> constructors, pinned by a test, in which every constructor is either probed by a
> future-perturbation probe of the kind added this session or pinned by a static check plus
> a written, tested argument.

H36 (this session) closed the point-in-time gap in the shared infrastructure and made the
suite runnable from a bare clone:

- `tests/test_causality_invariant.py` (new, 30 tests + 1 skip) — the contract *"no output
  observed at or before bar t may depend on any price strictly after bar t"* for the whole
  `STRATEGY_REGISTRY` and end-to-end through `run_backtest`, with a negative control, a
  non-vacuity check, a registry coverage pin, two static look-ahead checks and a
  rebalance cost-timing test. Backed by three injected negative controls into
  `src/qtr/strategies/baselines.py` (detected / correctly not detected; the file was
  restored).
- `pyproject.toml` — `pythonpath = ["src"]` under `[tool.pytest.ini_options]`, so
  `python -m pytest` runs with no install step (before: `ModuleNotFoundError: No module
  named 'qtr'`).

Verified: `python -m pytest -q -W error` → **780 passed, 1 skipped**; `src/qtr` coverage
**100%** (1011 statements, 0 missed); `ruff check src tests run_*.py` → *All checks
passed!*; `ruff format --check src tests run_*.py` → *81 files already formatted*.

Do not re-run any grid; do not modify a published artifact, gate threshold, verdict or
certified number; do not add a hypothesis.
