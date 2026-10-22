# HANDOFF_CURRENT_SESSION — H54: the published `metrics` block re-derives from its own frozen artifact

## What changed (H54)

**H54:** the published blocks of the summaries that publish no `metrics` block now re-derive
from their own frozen artifacts, and every convention the record carries is recorded. Of the **43**
non-`metrics` summaries (**24** shapes, **164** distinct top-level keys, **7 785** published leaf
values), **52** of the keys re-derive in full, **4** re-derive with a *named* disclosed leaf, and
**108** are declarations or audit verdicts about other artifacts. **Ten** convention profiles are
recorded and pinned, and three behavioural negative controls prove the checks fire.

- `tests/test_h54_non_metrics_block_disclosure.py` — the H54 contract: **21 tests**. The
  re-derivation walks the published structure; every reached leaf must agree, every
  unreached leaf must be *named* in `NOT_REDERIVABLE` with the reason the artifact cannot
  carry it, and every reconstructed-but-unpublished leaf must be named in `NOT_PUBLISHED`.
- `FINAL_REPORT.md` — new **§H54** section (the measured record, the classification of the
  **164** top-level keys, the **ten** conventions and the disclosure list).
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified
  number was modified; no grid was re-run; no hypothesis was added.

## What changed

- `tests/test_h53_published_metrics_disclosure.py` — the module that previously only enumerated the
  `metrics` summaries is replaced by the full re-derivation contract: **19 tests** (3 → 19). It
  re-derives every published value from the artifact that published it, pins the convention each
  producer used for each key, and carries four behavioural negative controls.
- `FINAL_REPORT.md` — new **§H53** section (with the full 450-row measured table), and the
  "Next task" section updated.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## The gap, measured

Four passes have audited the committed record, and they are disjoint:

| pass | what it covered | how many |
|---|---|---:|
| §H49 | the `validation` blocks of the exploratory summaries | **5** summaries |
| §H51 | the `information_ratio` inside the metric blocks | **48** artifacts |
| §H52 | the `avg_trade_cost` (strategy and benchmark) | **5** summaries + **23** tracker entries |
| §H53 | the rest of the `metrics` block — the **13** scalar keys that carry the certified numbers | **37** summaries, **450** values |

What §H53 closed: **441 of 450** published values re-derive from their own frozen artifact, with
residuals of 0 … 5.2e-14. The **9** that do not are the H9 family's regime block (`regime_sharpes` ×4,
`worst_regime_sharpe` ×5) — the producer fetched its VIX series from Yahoo at run time and never
committed it, so the regime labels are a function of an input the record does not hold.

## The conventions, per producer family

| producer | summaries | Sharpe std | profit factor | trades | WF folds | regime Sharpes | benchmark | `val_sharpe` holds |
|---|---:|---|---|---|---|---|---|---|
| `h9_intraday_tsmom_ctexits_v1` | 1 | **sample** (`ddof=1`) | **full sample** | **full sample** | pre-fix | full | full | val window |
| `h9_intraday_tsmom_ctexits_v2` | 4 | **sample** (`ddof=1`) | **full sample** | **full sample** | pre-fix | full | full | val window |
| `h10_intraday_tsmom_pfopt` | 2 | population | OOS | OOS | pre-fix | full | full | **`null`** |
| `h16_factor_timing` | 4 | population | OOS | OOS | pre-fix | OOS | OOS | val window (**3 publish train+val**) |
| `h17_vrp` | 1 | population | OOS | OOS | pre-fix | OOS | OOS | val window |
| `h19_volume_predictive` | 1 | population | OOS | OOS | pre-fix | OOS | OOS | val window |
| `h20_signed_volume` | 1 | population | OOS | OOS | pre-fix | OOS | OOS | val window |
| `h21_futures_tsmom_multicontract` | 1 | population | OOS | OOS | pre-fix | full | full | **the OOS Sharpe** |
| `h22_futures_tsmom_voltarget` | 5 | population | OOS | OOS | pre-fix | full | full | val window |
| `h23_crypto_futures_tsmom` | 7 | population | OOS | OOS | pre-fix | full | full | val window |
| `h25_futures_tsmom_pfmargin` | 2 | population | OOS | OOS | pre-fix | full | full | val window |
| `h28_h{10,21,22,25}_{control,causal}` | 8 | *as the parent* | OOS | OOS | **post-fix** | full | full | *as the parent* |

**Nineteen** producer tags, **ten** distinct convention profiles.

## The six findings

1. **The walk-forward stability gate was published on the PRE-FIX fold convention.** The library's
   `walk_forward_splits` used to end its last window at `n_splits * window_size`, silently dropping
   the tail of the return series; it was later changed so the last window absorbs it. **29** of the
   **37** published `wf_stability` values are pre-fix and **8** are post-fix. The split follows the
   production date: every post-fix summary is an H28 causal re-certification run of
   **2026-10-19**. All **8** post-fix summaries and **21** of the pre-fix ones are *discriminated* by
   the data (**29** of the 37); the other **8** — the H23 summaries, whose series length is an exact
   multiple of the fold count — coincide, because the tail is empty.
2. **`benchmark_alpha_annual` was published on the PRE-H51 beta convention** —
   `np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench)`, a mixed ddof that inflates beta by
   `n / (n - 1)`. All **7** published alphas (H16 ×4, H17, H19, H20) are pre-fix; they differ from
   the library's current alpha by **2.7e-05 … 3.7e-05**.
3. **The H9 family publishes the SAMPLE standard deviation** (`ddof=1`) because it passed a
   `pandas.Series` to `sharpe_ratio`; every other family passes an `ndarray` and publishes the
   POPULATION standard deviation (`ddof=0`). The same container split decides the information
   ratio's excess volatility — §H51's disclosure, extended here to the **8** H28 runs it did not
   cover.
4. **The H9 family publishes a whole-sample profit factor and trade count**, not the OOS-window
   ones every other family publishes.
5. **Three of the four H16 summaries publish the TRAIN+VAL window Sharpe under the key
   `val_sharpe`** (n = 2769 bars) while the fourth publishes the val-window Sharpe (n = 756 bars).
   Their own `param_grid_results.parquet` carries the val-window value in all four cases, so the
   summaries and their own grids disagree in three of them. **No gate reads the key.**
6. **`val_sharpe` holds three different things across the record**: `null` (H10), the OOS Sharpe
   (H21), and the val-window Sharpe (everybody else, except the three H16 summaries above).

## The four keys the block also publishes, and does not re-derive

`ablations` (**35** summaries — **28** re-derivable from their committed equity files, **7** not),
`perturbation` / `perturbation_min_ratio` (**14**, none re-derivable) and `cross_validation`
(**2**, none re-derivable). All are pinned in the contract's 17-key union; all are nested
gate-result blocks rather than certified scalars.

## The contract now pinned (19 tests)

1. **The record is named** — the 37 summaries that publish a `metrics` block, the 17-key union of
   what they publish, and the 450 published values are all pinned.
2. **Every published value re-derives** from its own frozen artifact under the recorded
   convention (residual ≤ 1e-09 relative; the measured residuals are 0 … 5.2e-14).
3. **The nine exceptions are exactly the H9 regime block**, and the reason is checked against the
   artifact directories' own file lists rather than asserted.
4. **The conventions are pinned** — the fold convention (29 pre-fix / 8 post-fix, split by
   production date), the beta convention (7 pre-H51), the H9 sample-vs-population split, the
   H9 whole-sample profit factor and trade count, and the three meanings of `val_sharpe`.
5. **The library's fold convention has since moved** — the contract compares the pre-fix and
   post-fix splits against `qtr.validation.statistics.walk_forward_splits` itself.
6. **Four behavioural negative controls** — reconstructing the *current* library fold convention
   breaks the re-derivation of all **21** discriminable pre-fix summaries; reconstructing the
   *current* library beta breaks all **7** published alphas; reconstructing the val-only window
   breaks the three H16 summaries; and a published value nudged by one part in a thousand fails
   the residual check. None of them is an API check.
7. **The blast radius is empty** — no published `passes` block reads `val_sharpe` or
   `train_sharpe`, and every gate key is computed from values that do re-derive.

## What was actually verified

- `python -m pytest -q -W error tests/test_h53_published_metrics_disclosure.py` → **19 passed** (3
  before this session).
- `python -m pytest -q -W error` → **1666 passed, 13 skipped** (full suite, up from 1650 + 13).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **95 files already formatted**.
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1055
  statements, 318 branches, 0 missed, 0 partial, 100.00%**; *"Required test coverage of 100.0%
  reached. Total coverage: 100.00%"* — unchanged, because nothing under `src/qtr` changed.
- **Every number is a read of the frozen artifacts** — no pipeline re-execution, no network, no grid
  re-run. The 450-row table in `FINAL_REPORT.md` §H53 was measured from the committed parquet files,
  and every published value was checked against the artifact that published it.
- **The conventions were measured, not assumed** — each was identified by reconstructing it and
  matching the published value to ≤ 1e-09 relative, and the reconstruction is now part of the
  contract.
- **Negative control** — behavioural, not an API check: the *current* library fold convention
  breaks the re-derivation of all **21** discriminable pre-fix summaries; the *current* library beta
  breaks all **7** published alphas; the val-only window breaks the three H16 summaries; and a
  published value nudged by one part in a thousand fails the residual check.
- **The blast radius is empty** — no published `passes` block reads `train_sharpe` or
  `val_sharpe`, and every gate key is computed from values that do re-derive.

## What remains unresolved

- **The 9 H9 regime values** cannot be re-derived: the producer's VIX series was never committed.
  Disclosed, not quantified.
- **The 29 pre-fix `wf_stability` values** no longer re-derive from the library's current
  `walk_forward_splits`; published on the convention in force when they were produced, disclosed,
  not rewritten. The certified families (H10, H22, H25) are among them.
- **The 7 published `benchmark_alpha_annual` values** are on the pre-H51 mixed-ddof beta;
  disclosed, not rewritten; no gate reads the key.
- **Three of the four H16 `val_sharpe` values** publish the train+val window under a key named for
  the val window and disagree with their own grid artifact; disclosed, not rewritten.
- **The four nested `metrics` keys** — `ablations` (35), `perturbation` (7),
  `perturbation_min_ratio` (7), `cross_validation` (2) — are pinned in the key union but not
  re-derived; the **28** ablation blocks whose equity files were committed are re-derivable, the
  rest are not.
- **The 22 published `information_ratio` values** on the sample (`ddof=1`) convention no longer
  re-derive from the library (§H51); disclosed, not rewritten. H53 extends that disclosure to the
  **8** H28 runs §H51 did not cover.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families'
  numbers and verdicts are frozen.

## The next task

**H54 — re-derive the published blocks of the summaries that publish no `metrics` block, and record
the convention each publisher used for every key in them.** The **43** such summaries publish **164**
distinct top-level keys over **7 785** leaf values in **24** distinct shapes (`gates`, `passes`,
`all_pass`, `verdict`, `oos_metrics`, `split_metrics`, `benchmark_comparison`,
`strategy_metrics`, `validation`, …) and **three** of them publish no parquet artifact at all.
Read-only against the frozen artifacts; no grid re-run; no published number may move. The full
statement is in `NEXT_TASK.md`.
