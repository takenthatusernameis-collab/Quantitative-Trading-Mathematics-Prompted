# HANDOFF_CURRENT — session complete (H53)

## State

- **H53 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: every published `metrics` block re-derives from its own frozen
  artifact, and the convention each publisher used is pinned. The **37** summaries that publish one
  carry **12 scalars** and **5 structural keys**; all **522** published scalars and regime Sharpes
  re-derive under the convention their publisher used, to a worst relative residual of
  **6.494e-11**. The arrangement is pinned by `tests/test_h53_published_metrics_disclosure.py`
  (974 passed, 69 skipped) — including a **behavioural negative control** that executes the
  library's *own* historical source.
- **H52 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: §H47's cost-attribution disclosure now covers **the whole
  committed record** — **82** trade logs, not the 41 the §H47-era pathspec saw — and every one of
  them is named, classified and pinned by `tests/test_trade_log_cost_reconciliation.py`
  (37 tests). The set where the pre-fix attribution actually changes a number (**70**) is pinned
  separately from the set where it cannot (**7**) and the logs that hold no trade (**5**). The
  published numbers that read the column are disclosed too: 5 summaries publish the strategy's
  `avg_trade_cost` (3 over-stated) and 23 tracker-metadata entries publish the benchmark's
  (9 verified at 20x or 5x).
- **H51 is COMPLETE** as recorded in `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md` and
  `HANDOFF_CURRENT_SESSION.md`: `compare_to_benchmark` is **container-independent** — both sides are
  reduced to float numpy arrays before any statistic is computed, every standard deviation carries
  an explicit `ddof`, and the excess volatility (and the information ratio) is taken on the
  **population** standard deviation (`ddof=0`). The choice is pinned by
  `tests/test_h51_benchmark_container_invariance.py` (246 tests, 12 skipped for documented reasons).
  The published convention split is disclosed in full: of the **48** committed artifacts that publish
  an `information_ratio`, **26** are on `ddof=0` and **22** on `ddof=1`.
- **H50 is COMPLETE**: the setuptools-generated metadata directory `src/qtr.egg-info/` is
  **untracked** and ignored, `pyproject.toml` is the only declared source of the package's metadata,
  and the arrangement is pinned by `tests/test_generated_manifest_contract.py` (11 tests). The
  "regenerate and commit" route is closed by measurement: the generated metadata's serialisation
  depends on which setuptools built it.
- **H35–H50 are COMPLETE**: every gate defect class that has surfaced is closed by an executable
  invariant, the point-in-time invariant covers every `run_*.py`, the engine's `total_return` spans
  every bar, the package's two Sharpe implementations agree, the lint/format gate is reproducible,
  the coverage gate is measured, declared and complete, both the package's public API and the
  runners' import surface are declared and pinned, the engine's trade log reconciles with the
  costs it charges, the package's stochastic surface is seedable, and the published validation
  blocks re-derive from the frozen artifacts.
- No published artifact, gate threshold, verdict or certified number was modified; no grid was
  re-run; no hypothesis was added.

## What changed (this session — H53)

- `tests/test_h53_published_metrics_disclosure.py` — **new**, **974 passed, 69 skipped**.
- `FINAL_REPORT.md` — new **§H53** section (with the full per-summary, per-key table), the "Next
  task" section updated, and the §H50 / §H51 / §H52 "What remains unresolved" bullets corrected
  where they enumerated the covered scope.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## The measured finding (H53)

The `metrics` block is the block that carries the *certified* numbers, and it had never been
re-derived from the artifact that published it. It re-derives — but only under the convention each
publisher used, and those conventions are **not** the library's current ones. Six differences were
measured:

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
5. **Three H16 artifacts published a `val_sharpe` that leaks the training period** — the Sharpe of
   `(data start, VAL_END]` instead of `(TRAIN_END, VAL_END]`; they were published before the
   runner's first committed version bounded the mask. H21 and two H28 runs publish the *OOS* Sharpe
   under that key and four summaries publish it as `null`. **No published gate reads it.**
6. **One summary published two Sharpe conventions at once** — the H9 runner computed its *main*
   block from a Series and its *ablation* block from an ndarray, so the convention is per *call
   site*, not per family.

The **negative control** is the library's own historical source, executed: `git show 9fb26b8^`,
`26c6aa6^` and `85ad85b^`. Each reproduces the numbers of its own era (residual **0.0** for the
Sharpe and the walk-forward stability) and fails on the numbers of the next one (**9.7e-05** for the
Sharpe, **1.5e-03** for the H28 walk-forward stability).

Two facts worth recording for the next session: the H9 family's VIX series is **recoverable** — the
run's fetch is addressed by the fetcher's own content-addressed cache key
(`sha256(f"yahoo:^VIX:{start}:{end}:1d")[:16]`), so the exact series it read is in the committed
cache; and the ablation blocks log their curves under **two different names** (`ablations_<name>_
equity` for H9, `ablations__<name>__equity` for H10), so a scan that looks for one pattern sees
only half the record.

## What was actually verified

- `python -m pytest -q -W error tests/test_h53_published_metrics_disclosure.py` → **974 passed, 69
  skipped** (the skips name their reason).
- `python -m pytest -q -W error` → **2616 passed, 87 skipped** (full suite, up from 1647 + 13).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **95 files already formatted**.
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1055
  statements, 318 branches, 0 missed, 0 partial, 100.00%**; *"Required test coverage of 100.0%
  reached. Total coverage: 100.00%"* — unchanged, because nothing under `src/qtr` changed.
- **Every H53 number is a read of the frozen artifacts** — no pipeline re-execution, no network,
  no grid re-run — and the negative control is behavioural.

## What remains unresolved

- **The 7 daily-family ablation blocks** (the nested `oos_metrics` shape) are **not quantifiable**
  from the record: those runners logged no ablation equity curve. Disclosed, not quantified.
- **The ablation blocks' own trade counts** (`trades` / `oos_trades`) are **not quantifiable**
  anywhere: an ablation's trade log was never committed. Disclosed, not quantified.
- **The perturbation and cross-validation blocks** (7 + 7 + 2 summaries) are **not quantifiable**:
  the perturbed and cross-validated curves were never committed. Disclosed, not quantified.
- The **22 published `information_ratio` values on the sample (`ddof=1`) convention** no longer
  re-derive from the library, which now enforces the population convention. They are **disclosed**,
  not rewritten; the artifacts are frozen and no gate outcome moves. **Re-measured per family in
  §H53**, which pins the container rule that produced the split.
- **The H47 cost-attribution disclosure is RESOLVED (§H52).** The record is **82** trade logs,
  all of them carry the pre-fix attribution, and all of them are pinned; the set where the
  attribution changes a number (**70**) is pinned separately from the set where it cannot (**7**)
  and the logs that hold no trade (**5**). The **14** benchmark `avg_trade_cost` entries
  whose benchmark trade log and signals were never committed remain **not quantifiable** from
  the record; they are disclosed, not quantified.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04 absolute, 9.7e-05
  relative — re-measured in §H53); disclosed and pinned, verdict frozen.
- **The three leaky `val_sharpe` values** remain published as they are; the artifacts are frozen and
  no published gate reads the key.
- **H54 is assigned** — stated in full in `NEXT_TASK.md`: record the conventions of the
  **`stats.json` echoes** (**40** files publish the head of a trade log as text, and their
  `returns` field is a pandas `to_string()` of a return series, so the published numbers are
  rounded to the display precision and truncated), and close the **14** benchmark `avg_trade_cost`
  entries whose factor is not measurable from the record. Four passes have now audited disjoint
  slices of the **80** committed `summary.json` files: §H49 the **5** `validation` blocks, §H51 the
  **48** `information_ratio` values, §H52 the `avg_trade_cost` values and §H53 the **37**
  `metrics` blocks.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted.
