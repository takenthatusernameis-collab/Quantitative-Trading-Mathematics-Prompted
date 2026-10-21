# HANDOFF_CURRENT_SESSION — H53: every published `metrics` block re-derives from its own frozen artifact

## What changed

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
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md` updated.
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
`benchmark_alpha_annual`** — the two keys whose values are anomalous.

## The convention, per family (measured, not assumed)

| family | summaries | Sharpe | fold Sharpe | regime Sharpe | profit factor | trades | walk-forward | regimes | IR | beta | `val_sharpe` |
|---|---:|---|---|---|---|---|---|---|---|---|---|
| **H9** | 5 | `ddof=1` (Series) | `ddof=0` | `ddof=0` | full sample | all | tail-dropping | `^VIX` daily, from the cache | `ddof=1` | — | Val window |
| **H10** (H10, H21, H22, H25, H28) | 18 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping (the 8 H28 runs: tail-absorbing) | `vix_hourly.parquet` | `ddof=1` | — | Val, except 3 OOS and 4 `null` |
| **H16** (H16, H17, H19, H20) | 7 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping | `vix_close.parquet`, OOS only | `ddof=0` | pre-H51 (mixed `ddof`) | Val, except 3 leaky |
| **H23** | 7 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping | `vix_hourly.parquet` | `ddof=1` | — | Val window |

Each convention was *measured* by re-deriving the published value under every candidate and keeping
the one that reproduces it; the alternatives are then asserted **not** to reproduce it, so the
convention is pinned by the data and not by this session's own reconstruction.

## The six findings

1. **The Sharpe's deviation convention was the caller's container.** `sharpe_ratio` only became
   container-independent on 2026-10-17 (commit `9fb26b8`); the H9 family passed a Series (sample
   deviation) and the H10+ families passed `.values` (population deviation).
2. **The walk-forward split dropped the tail** until 2026-10-18 (commit `26c6aa6`). Every
   `wf_stability` published before that commit uses the tail-dropping split; the eight H28 artifacts
   (2026-10-19) use the tail-absorbing one — the **only** key whose convention is decided by the
   publication date.
3. **The published alpha uses the pre-H51 beta** (`np.cov(S, B, ddof=1)[0, 1] / np.var(B, ddof=0)`),
   which inflates beta by `n / (n - 1)`; the seven published alphas re-derive exactly under it and
   not under the library's current consistent-`ddof` beta.
4. **The published information ratio follows the same container rule** — the families that passed a
   Series published the sample deviation, the families that passed an ndarray the population one.
5. **Three H16 artifacts published a `val_sharpe` that leaks the training period** — the Sharpe of
   `(data start, VAL_END]` instead of `(TRAIN_END, VAL_END]`; they were published before the
   runner's first committed version bounded the mask. H21 and two H28 runs publish the *OOS* Sharpe
   under that key and four summaries publish it as `null`. **No published gate reads it.**
6. **One summary published two Sharpe conventions at once** — the H9 runner computed its *main*
   block from a Series and its *ablation* block from an ndarray, so the convention is per *call
   site*, not per family.

## The negative control — the library's *own* historical source

The control is not a hand-written reconstruction of a superseded convention: it is the library's
own `src/qtr/validation/statistics.py` at the commit that changed the convention, **executed as it
was written** (`git show 9fb26b8^`, `git show 26c6aa6^`, `git show 85ad85b^`). It is run in both
directions — the historical implementation must **reproduce** the numbers published under the
convention it implemented, and must **fail** on the numbers published under the convention that
replaced it:

| control | reproduces | fails |
|---|---|---|
| the pre-`9fb26b8` `sharpe_ratio` | the H9 Sharpe through the **Series** path (residual **0.0**), the H10 Sharpe through the **ndarray** path (residual **0.0**) | the H9 value through the array path (**9.7e-05** off) and the H10 value through the Series path (**9.7e-05** off) |
| the pre-`26c6aa6` `walk_forward_splits` | every pre-fix `wf_stability` (residual **0.0**) | the eight H28 values (**1.5e-03** off); the library's current splitter likewise fails the pre-fix values (**1.8e-03** off) |
| the pre-`85ad85b` `compare_to_benchmark` | the seven published alphas (residual **< 1e-10**), their p-values and their information ratios | the library's current consistent-`ddof` beta |

The pre-H51 `compare_to_benchmark` reproduces the daily family's published information ratio,
p-value and alpha **verbatim**, so that family's benchmark leg is *one library call*; the intraday
families' information ratio does **not** come from that function (they computed their own, on the
sample deviation, and are off by `sqrt(n / (n - 1))`).

## The contract now pinned (974 passed, 69 skipped)

1. **The record is complete and pinned** — the set of summaries that publish a `metrics` block is
   exactly the 37 in `RECORD`, the key union is exactly the 17 keys above, and the family counts
   are pinned (H9 = 5, H10 = 18, H16 = 7, H23 = 7).
2. **Every published scalar re-derives** — from the summary's *own* frozen artifact, under the
   recorded convention, to a worst relative residual of **6.494e-11** (the alphas, where the
   near-cancellation of the CAPM terms amplifies a ~3e-13 absolute difference; every other key is
   at **5.1e-13** or better). The tolerance is pinned by its own test, so it cannot be loosened
   silently.
3. **The conventions are discriminating** — for every publisher, the *alternative* convention is
   asserted **not** to reproduce the published number, and the cases where the data cannot
   discriminate are **skipped with the reason recorded**.
4. **The walk-forward split's date-dependence is pinned** — the 8 post-fix artifacts and the 29
   pre-fix artifacts are named, and each is re-derived on its own split.
5. **The alpha and the two `val_sharpe` anomalies are pinned** — the pre-H51 beta reproduces all
   seven published alphas and the library's beta reproduces none of them; the three leaky
   `val_sharpe` values are shown to cover the training period; the OOS-valued and `null`-valued
   ones are named.
6. **The structural blocks are pinned** — the key counts (35 / 7 / 2 / 7 / 36), the two flat
   ablation shapes and the nested one, the perturbation ratio's two disjoint forms (no artifact
   publishes both), and the fact that the ratio's variants are not quantifiable.
7. **The committed ablation curves re-derive** — the 28 publishers that commit an ablation equity
   curve (25 under the double-underscore name, 3 under the H9 single-underscore name) have their
   blocks' OOS Sharpe, profit factor, drawdown and test Sharpe re-derived from that curve.
8. **The H9 VIX leg is recovered, not guessed** — the run's fetch is addressed by the fetcher's own
   content-addressed cache key, and the key is checked against `DataCache._cache_key` itself.
9. **The negative control is behavioural.**

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
  re-run. The per-summary, per-key table in `FINAL_REPORT.md` §H53 was measured from the committed
  parquet files, and every published value was checked against the artifact that published it.
- **No published verdict moved** — the 37 publishers' verdicts (11 `PASS`, 26 `REJECT`) and their
  `all_pass` flags are unchanged.

## What remains unresolved

- **The 7 daily-family ablation blocks** (the nested `oos_metrics` shape) are **not quantifiable**
  from the record: those runners logged no ablation equity curve. Disclosed, not quantified.
- **The ablation blocks' own trade counts** (`trades` / `oos_trades`) are **not quantifiable**
  anywhere: an ablation's trade log was never committed. Disclosed, not quantified.
- **The perturbation and cross-validation blocks** (7 + 7 + 2 summaries) are **not quantifiable**:
  the perturbed and cross-validated curves were never committed. Disclosed, not quantified.
- **The 22 published `information_ratio` values** on the sample (`ddof=1`) convention no longer
  re-derive from the library (§H51); disclosed, not rewritten. **Re-measured per family in §H53.**
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04 absolute, 9.7e-05
  relative — re-measured in §H53); disclosed and pinned, verdict cannot move.
- **The three leaky `val_sharpe` values** remain published as they are; the artifacts are frozen and
  no published gate reads the key.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families'
  numbers and verdicts are frozen.

## The next task

**H54 — record the conventions of the `stats.json` echoes, and close the 14 benchmark
`avg_trade_cost` entries whose factor is not measurable from the record.** The committed record
holds **80** `summary.json` files publishing about 190 distinct top-level keys; four passes have now
audited disjoint slices of it — §H49 the **5** `validation` blocks, §H51 the **48**
`information_ratio` values, §H52 the `avg_trade_cost` values, §H53 the **37** `metrics` blocks — and
the **`stats.json` echo** has never been covered: **40** files publish the head of a trade log as
text, and their `returns` field is a pandas `to_string()` of a return series, so the published
numbers are rounded to the display precision and truncated. Read-only against the frozen artifacts;
no grid re-run; no published number may move. The full statement is in `NEXT_TASK.md`.
