# HANDOFF_CURRENT_SESSION — H36: point-in-time invariant for the shared infrastructure

## What changed

1. **`pyproject.toml`** — added `pythonpath = ["src"]` to `[tool.pytest.ini_options]`
   (pytest >= 7.0 feature; `requirements.txt` pins `pytest>=7.4.0`).
   **Why:** the package uses a `src/` layout and was *not installed* in this
   environment, so `python -m pytest` failed at collection with
   `ModuleNotFoundError: No module named 'qtr'` unless `PYTHONPATH=src` was
   set by hand. The published record quotes a passing test count, but the
   command was not reproducible from a bare clone. After the change
   `python -m pytest` resolves `qtr` with no install step and no network.
   No source file, gate, threshold, artifact, verdict or certified number was
   touched.

2. **`tests/test_causality_invariant.py`** (new: 30 tests + 1 skip) — an
   executable **point-in-time (no look-ahead) invariant** for the shared
   research infrastructure:
   - `qtr.strategies.STRATEGY_REGISTRY` (the signal library) and
     `qtr.backtest.engine` (the vectorized engine) are the code path behind
     almost every runner in this repository (`run_experiment.py`,
     `run_baseline.py`, `run_param_sweep.py`, `run_alternatives.py`,
     `run_cs_momentum_experiment.py`, `run_ts_momentum_experiment.py`,
     `run_ddcv_experiment.py`, `run_h6_vix_ddcv_experiment.py`,
     `run_futures_tsmom_experiment.py`, `run_h7/h9/h10/h18/h21`, ...).
   - Before this module the only causality coverage was one narrow engine
     test (`test_signal_earns_from_next_period`) and two runner-specific
     suites (H23, H28). **Nothing pinned the shared library**, so a
     look-ahead introduced in `baselines.py` or `engine.py` would have
     reached every runner with no test failing.
   - The contract: *no output observed at or before bar `t` may depend on
     any price strictly after bar `t`.* It is checked by future
     perturbation (the prices after a cut are replaced by a different seeded
     path; everything at or before the cut must come out bit-identical) at
     **every bar of a reduced sample** (dense sweep) and at nine cut points
     on the full sample with the lookbacks the runners actually use (sparse
     sweep), for the strategy library and end-to-end through `run_backtest`
     (returns, positions, equity curve, trade log).
   - Non-vacuity is enforced in both directions: a **negative control**
     (a `shift(-1)` signal) must be *detected* by the probe, and every
     *reactive* strategy must actually *change* after the cut.
   - A **coverage pin** ties the probes to `STRATEGY_REGISTRY`, so a newly
     registered strategy fails the suite until it is probed.
   - Two **static checks** close the explicit look-ahead operators that a
     per-bar perturbation alone would not catch: no negative `shift(...)`
     and no backward `pct_change(...)`/`diff(...)` period anywhere in
     `src/qtr`.
   - One **cost-timing** test: a rebalance's transaction cost is charged in
     the same bar in which the new weight is first held (the engine applies
     positions with a one-bar delay, `signals.shift(1) * price_returns`).

## What was actually verified

- Baseline before this session: `PYTHONPATH=src python -m pytest -q -W error`
  → **750 passed** in 161 s.
- After: `python -m pytest -q -W error` (no `PYTHONPATH`, no install) →
  **780 passed, 1 skipped** in 167 s (750 + the 30 new tests; the skip is
  `buy_and_hold`, a constant position that cannot react to a perturbation).
- `python -m pytest --cov=qtr --cov-report=term-missing` → `src/qtr`
  coverage **100%** (1011 statements, 0 missed).
- `python -m ruff check src tests run_*.py` → *All checks passed!*
- `python -m ruff format --check src tests run_*.py` → *81 files already
  formatted*.
- **Negative controls (injected into `src/qtr/strategies/baselines.py`, then
  reverted; `git diff` on the file is empty):**
  - A) `momentum_signals`: `.shift(skip)` → `.shift(-skip)` → **3 tests
    fail** (the static negative-shift check + the causality probes).
  - B) `carry_signals`: `pct_change(lookback)` → `pct_change(-lookback)` →
    **4 tests fail** (the static backward-period check + the probes).
  - C) *control, not a leak*: `vol_scaled_tsmom_signals` with the `skip`
    removed (this still only reads price[t], which is consistent with the
    engine's one-bar delay) → **all 30 tests still pass**, so the invariant
    is not over-strict.
- No published artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## What remains unresolved

- **The runners' own inline signal code is still not covered by a generic
  causality probe.** H10, H12, H16, H18, H19, H20, H21, H22, H25, H27, H29
  each build their own position series inside `run_*.py`; only H23 and H28
  have causality tests. The shared library is now proven point-in-time, but
  the larger remaining look-ahead surface is in the runners.
- **The engine's `metrics["total_return"]` is inconsistent with its own
  equity curve.** `total_return = equity.iloc[-1] / equity.iloc[0] - 1`
  excludes the first bar's return, while `annualized_return` annualizes it
  with `n_periods = len(returns)` (which *includes* the first bar). The
  error is ~the size of one bar's return (a few bps in practice) but it is
  a genuine metric inconsistency. **Not fixed here**: `metrics` values are
  in published artifacts (`run_h8_rolladjusted_tsmom_experiment.py:733`
  publishes `benchmark_return` from it) and the published record is frozen.
  It is a *disclosure*, not a rewrite.
- **`DataFetcher.fetch_sp500_constituents(date=...)` silently ignores its
  `date` argument** and always returns the *current* constituent list — a
  latent survivorship-bias footgun in the shared library. No runner calls
  it, so nothing published is affected.

## Approaches already tried / failed (and why)

- **A single cut point per probe was rejected as insufficient.** A
  perturbation at cut `c` can only expose a leak that reads *past* bar `c`,
  so a leak at bar `t` reading `t+1` is detected only at cut `t`. The
  single-cut version also failed its own negative control (a sign-based
  leak whose sign happened not to flip). Replaced by a dense sweep (every
  bar is a cut) plus a sparse sweep with the runners' lookbacks, and by
  forcing the first perturbed bar's factor to 0.5 so a one-bar-ahead
  return always changes sign.
- **Fixing the runners' published Sharpe scale was not attempted.** H26
  already audited it: the published intraday Sharpe is a `sqrt(252)`-per-bar
  metric, the mis-scaling *understates* the intraday family, and it
  "creates no pass and invalidates no verdict" (H7 stays REJECT at 2/7 on
  the evaluable gates even if its Sharpe gate flipped). Re-deriving it
  would repeat completed work.
- **Re-running any grid, or repairing the disclosed H7/H18 non-evaluating
  gates, remains forbidden** by the carried-forward constraints.

## Precise next task (one task), with evidence and constraints

**Extend the point-in-time invariant from the shared library to the runners'
inline signal code.**

*Evidence.* The shared library is now proven point-in-time by an executable
probe (this session), and the only *documented* causality suites are
`tests/test_h23_crypto_futures_tsmom.py::TestCausality` and
`tests/test_h28_causal_recertification.py`. The runners
`run_h10_intraday_tsmom_pfopt_experiment.py`, `run_h12_selection_bias_audit.py`,
`run_h16_factor_timing_experiment.py`, `run_h18_overnight_intraday_experiment.py`,
`run_h19_volume_predictive_experiment.py`, `run_h20_signed_volume_experiment.py`,
`run_h21_futures_tsmom_multicontract.py`, `run_h22_futures_tsmom_voltarget.py`,
`run_h25_futures_tsmom_pfmargin.py`, `run_h27_pnl_level_audit.py` and
`run_h29_lookahead_sweep.py` each construct position series inline, and a
look-ahead there is invisible to the invariant added this session.

*Deliverable.* An inventory of the runners' signal constructors, pinned by a
test, in which every constructor is either (a) covered by a future-
perturbation probe of the kind added this session (dense + sparse cuts, with
the negative control retained), or (b) covered by a static check plus a
written, tested argument for why a dynamic probe is not applicable. A new
runner signal constructor must be classified, or the suite fails.

*Constraints.* Do not re-run any grid; do not modify a published artifact,
gate threshold, verdict or certified number; do not add a hypothesis; keep
`src/qtr` at 100% coverage; `python -m pytest -q -W error` and
`ruff check` / `ruff format --check` must pass from a bare clone (no
install step).
