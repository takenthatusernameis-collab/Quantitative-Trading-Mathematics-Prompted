# Next Task — H37 complete (runners' inline signal code); extend the invariant to the remaining runners (2026-10-20)

## State

**H35, H36 and H37 are COMPLETE.** H37 extended the point-in-time invariant from the shared
infrastructure to the **runners' own inline signal code**, and in doing so found one
look-ahead the record did not state (H18's `vix_regime` predictor). **No published artifact,
gate threshold, verdict, certified number or published row was modified; no grid was re-run;
no hypothesis was added.**

### What changed (H37)

- `tests/test_runner_causality_inventory.py` (new: 179 tests) — the point-in-time contract
  for the runners' inline signal code:
  - **The probe** is H36's *future perturbation*, applied to the runners' own constructors:
    the market data after a cut is replaced by a different seeded path and everything at or
    before the cut must come out bit-identical. Dense sweep (every bar of a reduced sample is
    a cut) + sparse sweep (nine cuts on the full sample at the lookbacks the runners
    actually use). Two scopes, because the runners do not execute their decision at the same
    moment: `after` (the engine's one-bar delay — the signal may read its own bar) and
    `close` (H18, whose decision is executed at the **open** of the bar — the signal may not
    read that bar's close).
  - **The inventory**: all **137** module-level functions of **13** runners (the eleven named
    by the H36 handoff plus their two dependencies, `run_h9` and `run_h23`) are classified as
    `probed` (36), `lookahead` (7) or `static` (94). A new function in an in-scope runner
    fails the suite until it is classified. 53 probe cases + 2 day-aligned collapse probes.
  - **The static sweep**: an exhaustive, by-construction AST sweep of the runners' source for
    the operators that *are* look-aheads (negative `shift`, backward `pct_change`/`diff`
    period, centred window, backward fill, same-period `resample` collapse). The site list is
    pinned, so a new look-ahead operator anywhere in the runners fails the suite even if it
    sits in a function the inventory does not probe.
  - **The known look-aheads are pinned as *detections***: the probe must find the violation, so
    the disclosure cannot be silently dropped and the defect cannot be silently repaired
    without updating the record.
- `FINAL_REPORT.md` §H37, the `## Next Task` section of `FINAL_REPORT.md`, and this file.

### The findings (disclosures — the published record is untouched)

| # | Site | Class | Effect on the published record |
|---|------|-------|------------------------------|
| P1 | `run_h10_…:build_hourly_target`, `run_h23_…:build_hourly_target` | known look-ahead | The H27/H28/H29 defect, now **reproduced from the runners' own code** by the probe (76/79 dense cuts, 9/9 sparse cuts). The published intraday verdicts stand as published. |
| P2 | `run_h12_…:_rebuild_grid_oos`, `run_h21/22/25_…:_apply_exits_and_aggregate` | inherited look-ahead | Pinned by an executable **call-graph** check (they call `build_hourly_target`). The OOS matrix / per-contract positions are the published (look-ahead) ones. |
| P3 | `run_h18_…:_overnight_intraday_signal` with `predictor="vix_regime"` | **new look-ahead** | The pre-registration requires a one-day lag ("Signal (causal, 1-day lag)", "at the prior day's close"); the predictor reads `vix_close[t]` and the runner applies the signal to **day `t`'s own legs** with no one-bar delay. The probe detects it (79/79 dense cuts, 9/9 sparse cuts) while the two lagged predictors are clean (0 cuts). |

**P3 is bounded**: the published selection (by Val Sharpe) was
`prior_5d_return_sign_next_intraday` (Val Sharpe 0.9797) — a *causal* predictor. The two
leaky cells' Val Sharpes (0.4710 and 0.5801) are below it, so the published row, the
published numbers and the published verdict (**REJECT**) are unaffected. A test pins the
selection against the committed artifact (`exp_2026-10-13T22-14-50-729923Z`), so if the
selection ever changed, the disclosure would have to be revisited.

**What the probe cannot see, and why**: `_apply_exits_and_aggregate` (H21/H22/H25) is *not*
probed, because its output is a sticky state machine (the exit holds the size it entered
with), so a positional probe of the position series cannot see the look-ahead its input
target carries; the pin for it is the call graph, as for H12.

### The executable invariant

`tests/test_runner_causality_inventory.py`:

1. every module-level function of every in-scope runner is classified
   (`probed` / `lookahead` / `static`) — a new function fails the suite;
2. every `probed` function has a probe case (or a day-aligned collapse probe);
3. every `lookahead` function has a **pinned detection** (a probe that must find it, or a
   pinned call-graph inheritance);
4. the set of detected look-aheads is pinned, so the disclosure cannot grow or shrink
   silently;
5. the probe is shown to bind: two injected leaks (`shift(-1)`, `pct_change(-1)`) must be
   detected, and every probed constructor must *react* to the perturbation (non-vacuity);
6. the runners' source contains no negative `shift`, no backward period, no centred window,
   and only the **pinned** backward-fill and collapse sites;
7. the pinned backward fills can only fill a *pre-inception* gap (executable argument: the
   fabricated segment is flat, so it contributes no return and alters no real bar);
8. the published H18 row does not use the leaky predictor.

### Verification

- `python -m pytest -q` → **959 passed, 1 skipped** in 182 s (780 + the 179 new tests; the
  skip is the pre-existing `buy_and_hold` skip in H36's module).
- `python -m ruff check src tests run_*.py` → *All checks passed!*;
  `python -m ruff format --check src tests run_*.py` → *82 files already formatted*.
- `src/qtr` was not touched → its coverage is unchanged at **100%**.
- **Injected negative controls** (into the runners, then reverted; `git diff` on both files is
  empty): a `shift(-1)` in `run_h19_…:build_targets` → **8 tests fail**; a *non-leak* control
  (`prices.shift(skip)` → `prices` in `run_h16_…:factor_momentum`, which still only reads
  `price[t]`) → **all 14 H16 tests still pass**, so the invariant is not over-strict.

## Status (this session — COMPLETE)

1. The runners' inline signal code is now covered by a point-in-time invariant: 137 functions
   across 13 runners classified and pinned, 55 probes, an exhaustive static operator sweep.
2. The published intraday look-ahead is **reproduced from the runners' own code** by the
   probe (not from a copy of it) and pinned as a detection.
3. **One new look-ahead found and disclosed**: H18's `vix_regime` predictor omits the
   pre-registered one-day lag. The published row and verdict are unaffected (the selection
   was a causal predictor) and the selection is pinned by a test.
4. No published artifact, gate threshold, verdict, certified number or published row was
   modified; no grid was re-run; no hypothesis was added.

## The next task (one, precise)

**Extend the point-in-time invariant to the *remaining* runners, and audit the predictor
timing (not just the collapse construction) in the families H29 certified as CAUSAL.**

*Evidence.* H37 covered `run_h9/h10/h12/h16/h18/h19/h20/h21/h22/h23/h25/h27/h29`. The
remaining runners still build position series inline with no generic coverage:
`run_experiment.py`, `run_baseline.py`, `run_param_sweep.py`, `run_alternatives.py`,
`run_cs_momentum_experiment.py`, `run_ts_momentum_experiment.py`,
`run_ddcv_experiment.py`, `run_futures_tsmom_experiment.py`,
`run_h6_vix_ddcv_experiment.py`, `run_h7_intraday_tsmom_experiment.py`,
`run_h8_rolladjusted_tsmom_experiment.py`, `run_regime_gated_momentum_experiment.py`,
`run_h1_*`, `run_h11_*`, `run_h13_*`, `run_h17_*` and the H25–H36 audit runners.

H29's sweep classified the **collapse** constructions of the remaining families as CAUSAL
(min hold lag +1), but it did **not** audit the *information timing of the predictors
themselves*. That is the class H37 found a new instance of in H18 (P3): a predictor that
reads its own bar's close while trading that bar's return. The same defect class is
plausible in the other families (e.g. a regime or momentum selector evaluated on the same
bar it is traded), and it is currently invisible to every test in the repository.

*Deliverable.* The same treatment as H37: an inventory of the remaining runners' signal
constructors, pinned by a test, in which every constructor is either probed by a
future-perturbation probe (dense + sparse cuts, negative control retained) or pinned by a
static check plus a written, tested argument; **plus** a report of every predictor that
reads its own bar's close while trading that bar's return, with the published selection
checked against the committed artifacts so that the disclosure is bounded exactly as P3 is.

*Also open (disclosure only, do not rewrite):* the engine's `metrics["total_return"]`
excludes the first bar and is therefore inconsistent with its own equity curve and with
`annualized_return`'s period count (a few bps; `metrics` values are in published artifacts);
and `DataFetcher.fetch_sp500_constituents(date=...)` silently ignores its `date` argument and
returns the *current* constituent list (a latent survivorship-bias footgun; no runner calls
it — this one **can** be fixed, because no published artifact depends on it).

Do **not** re-run any grid, do **not** modify a published artifact, gate threshold, verdict
or certified number, and do **not** add a hypothesis: the free-data hypothesis space is
exhausted and the H1–H30 records are frozen.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; every recomputed number is a **disclosure**, not a rewrite.
- The pre-existing H1–H30 hypothesis space remains exhausted — no new hypothesis is
  warranted.
- The certified families' numbers and verdicts are frozen (H10, H11, H12, H22, H25).
- The shared library, the engine **and the thirteen audited runners** are now pinned as
  point-in-time; keep them that way (re-run `tests/test_causality_invariant.py` after any
  change under `src/qtr`, and `tests/test_runner_causality_inventory.py` after any change in
  a `run_*.py`).
