# HANDOFF_NEXT — one task: extend the point-in-time invariant to the remaining runners (H37 complete)

**The next task is assigned** (see `NEXT_TASK.md` for the full statement):

> Extend the point-in-time invariant to the *remaining* runners, and audit the **predictor
> timing** (not just the collapse construction) in the families H29 certified as CAUSAL. H37
> covered `run_h9/h10/h12/h16/h18/h19/h20/h21/h22/h23/h25/h27/h29`; the rest
> (`run_experiment.py`, `run_baseline.py`, `run_param_sweep.py`, `run_alternatives.py`,
> `run_cs/ts_momentum_experiment.py`, `run_ddcv_experiment.py`,
> `run_futures_tsmom_experiment.py`, `run_h6/h7/h8_*`, `run_h1/h11/h13/h17_*` and the
> H25–H36 audit runners) still build position series inline with no generic coverage.
> Deliver the same inventory-and-probe treatment, and report every predictor that reads its
> own bar's close while trading that bar's return.

H37 (this session) closed the point-in-time gap in the **runners' inline signal code**:

- `tests/test_runner_causality_inventory.py` (new, 179 tests) — all **137** module-level
  functions of 13 runners classified (`probed` 36 / `lookahead` 7 / `static` 94) and pinned;
  53 future-perturbation probe cases (dense + sparse cuts, two negative controls,
  non-vacuity) + 2 day-aligned collapse probes; an exhaustive, pinned AST sweep for
  negative shifts, backward periods, centred windows, backward fills and same-period
  collapses.
- **Disclosed**: the published intraday look-ahead is now reproduced *from the runners' own
  code* by the probe and pinned as a detection; and **one new look-ahead was found** —
  H18's `vix_regime` predictor omits the pre-registered one-day lag (it reads `vix_close[t]`
  while trading day `t`'s own legs). The published H18 row and its REJECT verdict are
  unaffected (the selection was the causal `prior_5d_return_sign_next_intraday`) and the
  selection is pinned by a test.

Verified: `python -m pytest -q` → **959 passed, 1 skipped** (182 s);
`python -m ruff check src tests run_*.py` → *All checks passed!*;
`python -m ruff format --check src tests run_*.py` → *82 files already formatted*; `src/qtr`
untouched → coverage still **100%**. Two injected negative controls into the runners (a
`shift(-1)` → 8 tests fail; a non-leak control → all tests still pass) were detected /
correctly not detected, and both runner files were restored (`git diff` empty).

Do not re-run any grid; do not modify a published artifact, gate threshold, verdict or
certified number; do not add a hypothesis.
