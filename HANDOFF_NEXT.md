# HANDOFF_NEXT — extend the point-in-time invariant to the remaining runners (H37 complete; ts_momentum + cs_momentum covered this session)

**The next task is assigned** (see `NEXT_TASK.md` for the full statement):

> Continue extending the point-in-time invariant to the *remaining* runners, and audit the
> **predictor timing** (not just the collapse construction) in the families H29 certified as
> CAUSAL.

Progress this session: `run_ts_momentum_experiment.py` and `run_cs_momentum_experiment.py`
were added to `tests/test_runner_causality_inventory.py` (+96 lines): their momentum and
regime_labels constructors are probed clean (dense + sparse future-perturbation sweeps),
`resample_monthly_signals` is static with its `resample` collapse site pinned, and every
module-level function is classified. `KNOWN_LOOKAHEAD_CASES` is unchanged. No published
artifact, gate threshold, verdict or certified number was modified; no grid was re-run; no
hypothesis was added.

Verified: `python -m pytest -q -W error` → **975 passed, 1 skipped** in 183 s;
`python -m ruff check src tests run_*.py` → *All checks passed!*;
`python -m ruff format --check src tests run_*.py` → *82 files already formatted*; `src/qtr`
untouched → coverage still **100%**.

The remaining runners without coverage:
`run_experiment.py`, `run_baseline.py`, `run_param_sweep.py`, `run_alternatives.py`,
`run_ddcv_experiment.py`, `run_futures_tsmom_experiment.py`,
`run_h6_vix_ddcv_experiment.py`, `run_h7_intraday_tsmom_experiment.py`,
`run_h8_rolladjusted_tsmom_experiment.py`, `run_regime_gated_momentum_experiment.py`,
`run_h1_*`, `run_h11_*`, `run_h13_*`, `run_h17_*` and the H25–H36 audit runners.

Constraints: do **not** re-run any grid; do **not** modify a published artifact, gate
threshold, verdict or certified number; do **not** add a hypothesis; keep `python -m pytest
-q -W error` and `ruff check` / `ruff format --check` passing from a bare clone (no install
step), and keep `src/qtr` at 100% coverage.
