# Next Task

## State

H35–H53 complete (the coverage gate is measured, declared and complete at 100% statement + branch;
the package's public API and the runners' import surface are both declared and pinned; the engine's
trade log reconciles with the costs it charges; the package's stochastic surface is seedable; the
published validation blocks re-derive from the frozen artifacts; the package's metadata has exactly
one declared source of truth; `compare_to_benchmark` is container-independent and the published
convention split is disclosed; the H47 cost-attribution disclosure covers the whole committed
record; **every published `metrics` block re-derives from its own frozen artifact**).
**H53 is complete**: the **37** committed summaries that publish a `metrics` block are re-derived
key by key from the artifact that published them — **522** published scalars and regime Sharpes, to
a worst relative residual of **6.494e-11** — and the convention each publisher used is pinned
(including the six that differ from the library's current behaviour). The arrangement is pinned by
`tests/test_h53_published_metrics_disclosure.py` (974 passed, 69 skipped).

## What changed (H53)

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
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

### The record, measured

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

### The convention, per family (measured, not assumed)

| family | summaries | Sharpe | fold Sharpe | regime Sharpe | profit factor | trades | walk-forward | regimes | IR | beta | `val_sharpe` |
|---|---:|---|---|---|---|---|---|---|---|---|---|
| **H9** | 5 | `ddof=1` (Series) | `ddof=0` | `ddof=0` | full sample | all | tail-dropping | `^VIX` daily, from the cache | `ddof=1` | — | Val window |
| **H10** (H10, H21, H22, H25, H28) | 18 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping (the 8 H28 runs: tail-absorbing) | `vix_hourly.parquet` | `ddof=1` | — | Val, except 3 OOS and 4 `null` |
| **H16** (H16, H17, H19, H20) | 7 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping | `vix_close.parquet`, OOS only | `ddof=0` | pre-H51 (mixed `ddof`) | Val, except 3 leaky |
| **H23** | 7 | `ddof=0` | `ddof=0` | `ddof=0` | OOS window | OOS window | tail-dropping | `vix_hourly.parquet` | `ddof=1` | — | Val window |

Each convention was *measured* by re-deriving the published value under every candidate and keeping
the one that reproduces it; the alternatives are then asserted **not** to reproduce it.

### The six findings

1. **The Sharpe's deviation convention was the caller's container.** `sharpe_ratio` only became
   container-independent on 2026-10-17 (commit `9fb26b8`); the H9 family passed a Series (sample
   deviation) and the H10+ families passed `.values` (population deviation).
2. **The walk-forward split dropped the tail** until 2026-10-18 (commit `26c6aa6`). Every
   `wf_stability` published before that commit uses the tail-dropping split; the eight H28 artifacts
   (2026-10-19) use the tail-absorbing one. This is the **only** key whose convention is decided by
   the publication date.
3. **The published alpha uses the pre-H51 beta** (`np.cov(S, B, ddof=1)[0, 1] / np.var(B, ddof=0)`),
   which inflates beta by `n / (n - 1)`; the seven published alphas re-derive exactly under it and
   not under the library's current consistent-`ddof` beta.
4. **The published information ratio follows the same container rule** — the families that passed a
   Series published the sample deviation, the families that passed an ndarray the population one.
5. **Three H16 artifacts published a `val_sharpe` that leaks the training period** — the Sharpe of
   `(data start, VAL_END]` instead of `(TRAIN_END, VAL_END]`; they were published before the
   runner's first committed version bounded the mask. H21 and two H28 runs publish the *OOS*
   Sharpe under that key and four summaries publish it as `null`. **No published gate reads it.**
6. **One summary published two Sharpe conventions at once** — the H9 runner computed its *main*
   block from a Series and its *ablation* block from an ndarray, so the convention is per *call
   site*, not per family.

### The negative control — the library's *own* historical source

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
  skipped** (the skips name their reason).
- `python -m pytest -q -W error` → **2616 passed, 87 skipped** (full suite, up from 1647 + 13).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **95 files already formatted**.
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1055
  statements, 318 branches, 0 missed, 0 partial, 100.00%**; *"Required test coverage of 100.0%
  reached. Total coverage: 100.00%"* — unchanged, because nothing under `src/qtr` changed.
- **Every number is a read of the frozen artifacts** — no pipeline re-execution, no network, no grid
  re-run. The per-summary, per-key table in `FINAL_REPORT.md` §H53 was measured from the committed
  parquet files, and every published value was checked against the artifact that published it.
- **The negative control is behavioural** — the library's own historical source is executed and shown
  to reproduce the numbers of its era and to fail on the numbers of the next one.
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
- **H9's published OOS Sharpe** is on the sample convention (the population convention misses it by
  **9.7e-05** relative); disclosed and pinned, verdict frozen.
- **The three leaky `val_sharpe` values** remain published as they are; the artifacts are frozen and
  no published gate reads the key.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families'
  numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Assuming one convention for the whole `metrics` block** — rejected after measurement: the
  convention is per *call site*. The H9 summary publishes its main block on the sample deviation
  and its ablation block on the population one, and the daily family's benchmark leg is one
  pre-H51 library call while the intraday families computed their own information ratio.
- **Re-deriving the ablation blocks' trade counts** — rejected: an ablation's trade log was never
  committed, so the count is not quantifiable from the record. Disclosed, not quantified.
- **Treating the H9 VIX series as unrecoverable** — rejected: the run's fetch is addressed by the
  fetcher's own content-addressed cache key (`sha256(f"yahoo:^VIX:{start}:{end}:1d")[:16]`), so the
  series it read is recoverable from the committed cache.
- **A negative control that only asserted the conventions are pinned** — rejected: the control must
  be behavioural. Here the library's *own* historical source is executed and shown to reproduce the
  numbers of its era and to fail on the numbers of the next one.
- **Rewriting the values that do not re-derive under the library's current behaviour** — rejected:
  the artifacts are frozen and no published gate reads the affected keys. Disclosed, not rewritten.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; the H1–H30 hypothesis space remains exhausted.
- The package's public API (§H45) is pinned by `tests/test_public_api_contract.py`; re-run it
  after any change under `src/qtr`.
- The runners' import surface (§H46) is pinned by `tests/test_runner_import_contract.py`; re-run
  it after any change in a runner or under `src/qtr`.
- The engine's trade-log reconciliation (§H47) and the **whole frozen record** (§H52) are pinned by
  `tests/test_trade_log_cost_reconciliation.py`; re-run it after any change under
  `src/qtr/backtest` **or after a new artifact is committed**.
- The seeded reproducibility of `parameter_sensitivity` (§H48) is pinned by
  `tests/test_parameter_sensitivity_reproducibility.py`; re-run it after any change under
  `src/qtr/validation`.
- The published validation blocks (§H49) are pinned by
  `tests/test_h49_validation_block_disclosure.py`; re-run it after any change under
  `src/qtr/validation`.
- The metadata source of truth (§H50) is pinned by
  `tests/test_generated_manifest_contract.py`; re-run it after any change to `pyproject.toml`,
  `.gitignore` or the packaging layout.
- The container-independence of `compare_to_benchmark` and the published convention split (§H51)
  are pinned by `tests/test_h51_benchmark_container_invariance.py`; re-run it after any change under
  `src/qtr/validation`.
- The published `metrics` blocks (§H53) are pinned by
  `tests/test_h53_published_metrics_disclosure.py`; re-run it after any change under
  `src/qtr/validation` **or after a new artifact is committed**.
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under
  `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.

## The next task (H54)

> **Record the conventions of the `stats.json` echoes, and close the 14 benchmark `avg_trade_cost`
> entries whose factor is not measurable from the record.**

### The gap (measured)

- **The `stats.json` echoes.** **40** files publish the head of a trade log as text (H52 pinned
  the count). Their `returns` field is a pandas `to_string()` of a return series, so the published
  numbers are rounded to the display precision and the series is truncated — the conventions of
  that publisher are unrecorded, and no pass has covered them.
- **The 14 benchmark `avg_trade_cost` entries** whose benchmark trade log and signals were never
  committed are on the pre-fix basis (same engine commit), but their over-count factor is **not
  measurable from the record**: they use a 5-contract futures benchmark whose trade log and signals
  are absent. Disclosed, not quantified — and now the only remaining item of that kind.

### The work

1. Enumerate the `stats.json` files that publish a return series or a trade-log head, and record
   the display conventions (the rounding, the truncation, the row count) each publisher used.
2. Re-derive what *can* be re-derived from the echoed text — the head of the trade log, the first
   rows of the return series — and pin the rounding convention.
3. Publish the per-file table of published text vs re-derived text vs residual.
4. Pin it with a contract module carrying a behavioural negative control.
5. Correct any published wording that enumerates the covered scope.

### Constraints

- **Read-only** against the frozen artifacts. No pipeline re-execution, no network, no grid re-run,
  no artifact rewritten.
- No published artifact, gate threshold, verdict or certified number may move.
- The coverage gate, the lint gate and every pinned contract listed above must stay green.

### The runner-up (H55, if H54 is closed)

- The **3** H16 artifacts whose `val_sharpe` leaks the training period, and the **2** H10 plus
  **2** H28 summaries that publish it as `null`: a *published-key semantics* disclosure — which key
  is published under which name by which publisher — could be pinned as its own contract.
- The **`regime_sharpes` block** of the 36 publishers: the regime labels are re-derived, but the
  *source* of each family's VIX series is a call-site fact (a live fetch for H9, a committed
  parquet for the rest) and could be pinned per publisher.
