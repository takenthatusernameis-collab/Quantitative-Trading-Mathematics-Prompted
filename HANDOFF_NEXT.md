# HANDOFF_NEXT — H53: every published `metrics` block re-derives from its own frozen artifact

## What changed (this session)

- `tests/test_h53_published_metrics_disclosure.py` — **new**, **974 passed, 69 skipped**: the record
  of the 37 publishers, the per-family convention and the per-artifact overrides, the re-derivation
  of every published scalar, the *discriminating* control (the alternative convention does **not**
  reproduce the published number), the walk-forward split's date-dependence, the pre-H51 alpha, the
  three `val_sharpe` anomalies, the structural blocks, the committed ablation curves, the H9 VIX leg
  recovered from the content-addressed cache, and the **behavioural negative control** that executes
  the library's *own* historical source.
- `FINAL_REPORT.md` — new **§H53** section (with the full per-summary, per-key table), the "Next
  task" section updated, and the §H50 / §H51 / §H52 "What remains unresolved" bullets corrected
  where they enumerated the covered scope.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## The gap, measured

§H49 re-derived the `validation` blocks of five exploratory summaries, §H51 the
`information_ratio` of 48 artifacts and §H52 the `avg_trade_cost` values. The rest of the
**`metrics` block** — the block that carries the *certified* numbers and that the published
`passes` / `all_pass` / `verdict` blocks rest on — had never been re-derived from the artifact
that published it.

## The record

**37** of the committed summaries publish a non-empty `metrics` block. Their key union is **12
scalars** and **5 structural keys**:

| key | publishers | re-derived from the artifact? |
|---|---:|---|
| the 12 scalars | 37 each | **yes** |
| `regime_sharpes` | 36 | **yes** (three regimes each) |
| `benchmark_alpha_annual` | 7 | **yes** (on the pre-H51 beta) |
| `ablations` | 35 (157 entries, 19 distinct blocks) | **28** publishers yes, **7** no |
| `perturbation` / `perturbation_min_ratio` / `cross_validation` | 7 / 7 / 2 | **no** — the curves were never committed |

That is **522** published scalars and regime Sharpes, and they are the numbers the published gates
read: the `passes` block of all 37 publishers keys on `sharpe`, `trades`, `pf`, `dd`, `stab`,
`worst`, `p` and `ir` (plus `perturbation` in 25). **No published gate reads `val_sharpe` or
`benchmark_alpha_annual`.**

## The convention, per family (measured, not assumed)

| family | summaries | Sharpe | fold Sharpe | regime Sharpe | profit factor | trades | walk-forward | regimes | IR | beta | `val_sharpe` |
|---|---:|---|---|---|---|---|---|---|---|---|---|
| **H9** | 5 | `ddof=1` (Series) | `ddof=0` | `ddof=0` | full sample | all | tail-dropping | `^VIX` daily, from the cache | `ddof=1` | — | Val window |
| **H10** (H10, H21, H22, H25, H28) | 18 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping (the 8 H28 runs: tail-absorbing) | `vix_hourly.parquet` | `ddof=1` | — | Val, except 3 OOS and 4 `null` |
| **H16** (H16, H17, H19, H20) | 7 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping | `vix_close.parquet`, OOS only | `ddof=0` | pre-H51 (mixed `ddof`) | Val, except 3 leaky |
| **H23** | 7 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping | `vix_hourly.parquet` | `ddof=1` | — | Val window |

## The six findings

1. **The Sharpe's deviation convention was the caller's container.** `sharpe_ratio` only became
   container-independent on 2026-10-17 (commit `9fb26b8`); the H9 family passed a Series (sample
   deviation) and the H10+ families passed `.values` (population deviation).
2. **The walk-forward split dropped the tail** until 2026-10-18 (commit `26c6aa6`). Every
   `wf_stability` published before that commit uses the tail-dropping split; the eight H28 artifacts
   (2026-10-19) use the tail-absorbing one — the **only** key whose convention is decided by the
   publication date.
3. **The published alpha uses the pre-H51 beta** (`np.cov(S, B, ddof=1)[0, 1] / np.var(B, ddof=0)`),
   which inflates beta by `n / (n - 1)`.
4. **The published information ratio follows the same container rule.**
5. **Three H16 artifacts published a `val_sharpe` that leaks the training period**; H21 and two H28
   runs publish the *OOS* Sharpe under that key and four summaries publish it as `null`. **No
   published gate reads it.**
6. **One summary published two Sharpe conventions at once** — the H9 runner computed its *main*
   block from a Series and its *ablation* block from an ndarray, so the convention is per *call
   site*, not per family.

## The negative control — the library's *own* historical source

The control is the library's own `src/qtr/validation/statistics.py` at the commit that changed the
convention, **executed as it was written** (`git show 9fb26b8^`, `26c6aa6^`, `85ad85b^`). It must
**reproduce** the numbers published under the convention it implemented and **fail** on the numbers
published under the convention that replaced it:

| control | reproduces | fails |
|---|---|---|
| the pre-`9fb26b8` `sharpe_ratio` | the H9 Sharpe through the **Series** path (residual **0.0**), the H10 Sharpe through the **ndarray** path (residual **0.0**) | the H9 value through the array path (**9.7e-05** off) and the H10 value through the Series path (**9.7e-05** off) |
| the pre-`26c6aa6` `walk_forward_splits` | every pre-fix `wf_stability` (residual **0.0**) | the eight H28 values (**1.5e-03** off); the library's current splitter likewise fails the pre-fix values (**1.8e-03** off) |
| the pre-`85ad85b` `compare_to_benchmark` | the seven published alphas (residual **< 1e-10**), their p-values and their information ratios | the library's current consistent-`ddof` beta |

## What was actually verified

- `python -m pytest -q -W error tests/test_h53_published_metrics_disclosure.py` → **974 passed, 69
  skipped**.
- `python -m pytest -q -W error` → **2616 passed, 87 skipped** (full suite, up from 1647 + 13).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **95 files already formatted**.
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1055
  statements, 318 branches, 0 missed, 0 partial, 100.00%**; *"Required test coverage of 100.0%
  reached. Total coverage: 100.00%"* — unchanged, because nothing under `src/qtr` changed.
- **Every number is a read of the frozen artifacts** — no pipeline re-execution, no network, no grid
  re-run — and the negative control is behavioural.
- **No published verdict moved** — the 37 publishers' verdicts (11 `PASS`, 26 `REJECT`) and their
  `all_pass` flags are unchanged.

## The published record is unaffected

No published artifact, gate threshold, verdict or certified number was modified; no grid was
re-run; no hypothesis was added. Nothing under `src/qtr` changed, and the engine's per-bar charge
(H27's `L3` check must keep passing) and its per-trade attribution (§H47) stand exactly as they are.
This session only measured the frozen record and pinned it.

## What a next session inherits

- **One task is assigned (H54)** — stated in full in `NEXT_TASK.md`: record the conventions of the
  **`stats.json` echoes** (**40** files publish the head of a trade log as text, and their
  `returns` field is a pandas `to_string()` of a return series, so the published numbers are
  rounded to the display precision and truncated) and close the **14** benchmark `avg_trade_cost`
  entries whose benchmark trade log and signals were never committed and whose over-count factor is
  therefore not measurable from the record. Four passes have now audited disjoint slices of the
  **80** committed `summary.json` files: §H49 the **5** `validation` blocks, §H51 the **48**
  `information_ratio` values, §H52 the `avg_trade_cost` values and §H53 the **37** `metrics`
  blocks.
- The runner-up (H55) is to pin the *published-key semantics* — which key is published under which
  name by which publisher (the three leaky `val_sharpe` values, the three OOS-valued ones, the four
  `null` ones) — and the *source* of each family's regime series (a live fetch for H9, a committed
  parquet for the rest).
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families
  are frozen.
- **The 22 published `information_ratio` values on the sample convention no longer re-derive** —
  disclosed in §H51, not rewritten, and re-measured per family in §H53.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04 absolute, 9.7e-05
  relative — re-measured in §H53); disclosed and pinned, verdict frozen.
- **The 7 daily-family ablation blocks, the ablation trade counts and the perturbation /
  cross-validation blocks** are not quantifiable from the record; disclosed, not quantified.
