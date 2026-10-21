# HANDOFF — H50 complete (session handoff)

## What changed (H50)

**H50:** the setuptools-generated metadata directory is **untracked** and ignored, and
`pyproject.toml` is the only declared source of the package's metadata.

- `.gitignore` — `*.egg-info/` added.
- `src/qtr.egg-info/` — **untracked** (`git rm -r --cached`); the files stay on disk (the editable
  install resolves to them) but they are no longer part of the repository.
- `tests/test_generated_manifest_contract.py` — **new**, 11 tests.
- `FINAL_REPORT.md` — new **§H50** section and an updated "Next task" section.

### The corrected finding

The tracked manifest was stale (61 of 64 entries; the three test modules added between H33 and H49
were missing), and the two earlier sessions' reason for rejecting regeneration was **not quite
right**: building the same tree with the local setuptools 68.1.2 writes `Metadata-Version: 2.1`
with re-spaced, re-quoted requirement markers (`numpy >=1.24.0`,
`yfinance >=0.2.0 ; extra == 'data'`), where the committed file was built under pip's build
isolation as `2.4` (`numpy>=1.24.0`, `yfinance>=0.2.0; extra == "data"`). The `Requires-Dist`
entries are **not dropped** — every base requirement and every extra's requirement is present in
both builds. What is environment-dependent is the **serialisation**, which is enough to make
"regenerate and commit" irreproducible: the committed bytes would freeze whichever setuptools
happened to build them last.

Reproduction (no network): `from setuptools import build_meta;
build_meta.prepare_metadata_for_build_wheel("<tmp>")`.

### The contract now pinned

`tests/test_generated_manifest_contract.py` (11 tests) holds six invariants: the generated
manifest is **ignored** (and `git check-ignore` agrees); it is **not tracked**; `pyproject.toml` is
the **only** declared source of package metadata; **no module under `src/qtr` depends on it**; the
generated `PKG-INFO` and the installed distribution's metadata both **agree with the declaration**
(comparison is normalisation-based, so it does not depend on the setuptools version); and a
generated `SOURCES.txt` that exists is **not stale**.

Two facts worth recording: **`importlib.metadata` resolves the distribution to the source tree**
whenever `src` is on the import path (the test suite puts it there), so a developer's tooling
reads the *generated* manifest as the package's metadata — which is why the agreement invariant
checks it; and **a git command that ran and failed is a verdict, not an absence** — the first draft
masked a failing `check-ignore` as a skip.

## What changed (H49)

**H49:** the published `validation` blocks in all five exploratory summaries re-derive from their
own frozen `equity_curve.parquet`, and the `walkforward_stability` basis they were written on is
disclosed and pinned.

- `tests/test_h49_validation_block_disclosure.py` — **new**, 11 tests: re-derives each published
  `validation` block from its own frozen equity curve and asserts the published values — including
  the pre-guard `walkforward_stability` ratio, the `walkforward_folds`, the absence of the
  `param_stability` key, the fact that the two buy-and-hold blocks differ by cost model, and that
  `all_pass` stays `false`.
- `FINAL_REPORT.md` — new **§H49** section (rewritten from the H48-era draft) and an updated
  "Next task" section.
- `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`, `HANDOFF_NEXT.md`,
  `NEXT_TASK.md` updated.

### The corrected finding

The H48-era handoff claimed the last two artifacts "do not re-derive" and that the two buy-and-hold
blocks were written by *different* code versions on the *same* series. **Both claims were based on
the wrong return convention.** The engine charges costs per bar and compounds them into the equity
curve (`equity = (1 + net_returns).cumprod() * initial_capital`), so the equity curve carries the
full series including the opening bar; `equity.pct_change()` alone drops that bar. Including the
first bar's return — `equity[0] / initial_capital - 1`, the cost of the very first position change
charged on the opening bar — reproduces the published block for **all five** artifacts to float
noise (< 1e-9).

The published `walkforward_stability` is exactly `sharpe(second half) / sharpe(first half)`, taken
**unconditionally** (the pre-guard formula). In three ma_crossover artifacts both halves are losing,
so the sign-unaware ratio **passed** the `0.7` gate on a strategy that lost money in both halves;
the current sign-aware code reports `0.0`. In the two buy-and-hold artifacts both halves are
profitable, so the published value and the current code agree. All five published blocks report
`walkforward_pass: True` and `all_pass: false`; the current code would report
`walkforward_pass: False` for the three ma_crossover artifacts. **No verdict moves.**

The two buy-and-hold blocks differ because they charged **different costs** baked into their own
frozen equity curves (real cost model, `avg_trade_cost = 0.041106`, vs a fixed `0.0002` per trade),
on the **same** SPY price series. Each block re-derives exactly from **its own** frozen equity
curve; they do not re-derive from each other's. Disclosed, not reconciled.

## What changed (H48)

**H48:** `qtr.validation.statistics.parameter_sensitivity` is now seedable, so its bootstrap
confidence intervals are reproducible instead of redrawn from OS entropy on every call.

- `src/qtr/validation/statistics.py`
  - `parameter_sensitivity` takes an **optional** `random_state` (default `None`, so **no existing
    caller changes behaviour** — the unseeded path is byte-for-byte what it always was).
  - `_bootstrap_seeds` (new) expands an integer seed into **one independent stream per parameter
    row** (`np.random.SeedSequence(seed).spawn(n)`), so the rows are not resampled with a shared
    pattern; a row's seed does not depend on how many rows the grid holds, so extending the grid
    does not perturb the rows already analysed. The unseeded path passes `None` straight through.
- `tests/test_parameter_sensitivity_reproducibility.py` — **new**, 14 tests: exact reproducibility
  under a fixed seed, seed isolation from the legacy global `np.random.seed`, different seeds →
  different bounds, seed-free point estimates, row independence, grid-extension stability,
  **cross-process** reproducibility, a **negative control** (the unseeded path really moves; the
  pre-fix call site is reconstructed and shown to fail the invariant), and the published-record
  disclosure.
- `FINAL_REPORT.md` — new **§H48** section and an updated "Next task" section.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.

### The defect

`parameter_sensitivity` is exported in `qtr.validation.__all__` but called
`bootstrap_confidence_interval` **without** a `random_state`, so `np.random.default_rng(None)` drew
from OS entropy and two calls on the same input returned **different** confidence intervals
(measured: `ci_lower` = `[-0.7393122, -2.54308907]` then `[-0.93933284, -3.07895489]` on the same
input). Its siblings `sharpe_ratio_ci` and `bootstrap_confidence_interval` both accept
`random_state`, and all three runners that call the bootstrap directly pass `random_state=SEED`;
`parameter_sensitivity` was the only bootstrap caller in the package that could not be seeded.

The point estimates (`metrics`, `optimal_param`, `optimal_metric`, `stability_ratio`,
`metric_std`) were always deterministic — only the bootstrap bounds move — which is why the defect
was invisible in every published number.

With this change the package's **entire** stochastic surface is seedable: `src/qtr` contains exactly
two randomness sites, both in `statistics.py`, and every stochastic computation reachable from the
public API now takes a `random_state`.

## What was actually verified

- `python -m pytest -q -W error tests/test_parameter_sensitivity_reproducibility.py` → **14 passed**.
- `python -m pytest -q -W error` → **1355 passed, 1 skipped**; `src/qtr` =
  **1054 statements, 320 branches, 0 missed, 0 partial, 100.00%**; the committed gate reports
  *"Required test coverage of 100.0% reached. Total coverage: 100.00%"*.
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **91 files already formatted**.
- **Negative control** — the new contract run against the **pre-fix** implementation: **4 of the 14
  tests fail**, and every failure is **behavioural** (the bounds move; e.g. `-0.5059` against
  `-0.7423`) rather than a `TypeError` for a missing keyword.
- **Preconditions verified before the change** — no `run_*.py` calls `parameter_sensitivity` (AST
  scan of all 32 runners), and `validate_strategy` derives its published `param_stability` from the
  walk-forward fold Sharpes (`src/qtr/validation/statistics.py:714`), **not** from
  `parameter_sensitivity`; both facts are now pinned by the new contract.

## What remains unresolved

- **H49 is COMPLETE** (2026-10-21): the published `validation` blocks in all five exploratory
  summaries re-derive from their own frozen `equity_curve.parquet` under the engine's full return
  convention (including the opening bar), and the `walkforward_stability` basis — the
  sign-unaware `sharpe(2nd half) / sharpe(1st half)` — is disclosed and pinned by
  `tests/test_h49_validation_block_disclosure.py` (11 tests). The two buy-and-hold blocks differ
  from each other because they charged different costs baked into their own frozen equity curves.
  Full statement with the measured table in `FINAL_REPORT.md` §H49.
- **H50 is COMPLETE** (2026-10-21): the setuptools-generated metadata directory is untracked and
  ignored, `pyproject.toml` is the only declared source of the package's metadata, and the
  arrangement is pinned by `tests/test_generated_manifest_contract.py` (11 tests; 3 of them fail
  behaviourally against the pre-fix state). The "regenerate and commit" route is closed by
  measurement — the generated metadata's serialisation depends on which setuptools built it.
  Full statement in `FINAL_REPORT.md` §H50.
- **Disclosure (H47)** — the `cost` column of the **committed** trade logs (H10, H11, H16, H21,
  H22, H25) and the `avg_trade_cost` of the three exploratory 2026-10-10 MA-crossover summaries
  carry the pre-fix aggregate attribution. The artifact files are frozen and were left untouched.
  No gate, threshold, verdict or certified number reads them.
- H9's published OOS Sharpe is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move (REJECT on the profit factor, 55× margin over its 1.0 gate).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified
  families' numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **A negative control that only asserted the new keyword exists** — rejected: it failed against
  the pre-fix implementation with `TypeError` (the parameter was *missing*), not because the
  behaviour was wrong. The contract now goes through the `_seeded()` adapter, so the pre-fix
  implementation is driven down its unseeded path and the control is **behavioural**.
- **Regenerating `src/qtr.egg-info/` with the local setuptools** — rejected, and the stated reason
  was corrected in H50: setuptools 68.1.2 writes `Metadata-Version: 2.1` with re-spaced, re-quoted
  requirement markers, but it does **not** drop the `Requires-Dist` entries. The real problem is
  that the *serialisation* is a function of the build environment, so "regenerate and commit"
  cannot be reproduced. The manifest was **untracked** instead (§H50).
- **Regenerating the manifest with pip's build isolation** — rejected: the resulting bytes depend
  on whichever setuptools pip happens to resolve, which is the same irreproducibility by another
  route.
- **Fixing the trade log by changing the charge** — rejected: the charge was never wrong (H27's
  `L3` check proves it to ~1e-19). Only the attribution inside the log was wrong, so the fix moves
  the log, not the charge.
- **A negative control that only asserted the new API exists** (H47) — rejected for the same reason
  as above; the H47 spy now hooks both `_total_costs` and `_calculate_costs`, so that control is
  behavioural too.

## Precise next task

**H51 — publish the H47 cost-attribution disclosure and pin it.** The `cost` column of the
**committed** trade logs (H10, H11, H16, H21, H22, H25) and the `avg_trade_cost` of the three
exploratory 2026-10-10 MA-crossover summaries carry the **pre-fix** aggregate attribution: the
per-trade cost was attributed as a whole-order figure rather than split across the fills the engine
actually charges. The artifacts are frozen and no gate, threshold, verdict or certified number
reads the column, so the drift is currently invisible. The task is to (a) state it in
`FINAL_REPORT.md` §H51 with the measured difference, (b) show that re-deriving the attribution from
each committed trade log under the post-fix rule reproduces the engine's per-bar cost (the H27 `L3`
check already proves the *charge* was never wrong) while the published column does not, and (c) pin
the disclosure with a test so it cannot lapse silently. The full statement is in `NEXT_TASK.md`.

**H50 is complete** (2026-10-21). The record of what was done is in `FINAL_REPORT.md` §H50 and
`HANDOFF_CURRENT.md`.
