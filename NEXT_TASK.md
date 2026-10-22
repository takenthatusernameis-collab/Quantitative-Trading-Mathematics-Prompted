# Next Task

## State

H35–H55 complete (the coverage gate is measured, declared and complete at 100% statement + branch;
the package's public API and the runners' import surface are both declared and pinned; the engine's
trade log reconciles with the costs it charges; the package's stochastic surface is seedable;
the published validation blocks re-derive from the frozen artifacts; the package's metadata has exactly
one declared source of truth; `compare_to_benchmark` is container-independent and the published
convention split is disclosed; **the H47 cost-attribution disclosure now covers the whole committed
record**; **the published `metrics` block now re-derives from its own frozen artifact, key by key**).
**H53 is complete**: every published value in the **37** `metrics` blocks has been re-derived from
the artifact that published it — **441** of **450** values re-derive exactly (residuals 0 … 5.2e-14)
and the remaining **9** are the H9 family's regime block, whose VIX input was never committed. The
**ten** convention profiles the **nineteen** producer tags used are now recorded and pinned, and
four behavioural negative controls prove the checks fire.

**H54 is complete**: the **43** summaries that publish no `metrics` block are re-derived from their
own frozen artifacts under the conventions their producers used. Of the **164** distinct top-level
keys they publish, **52** re-derive in full, **4** re-derive with a *named* disclosed leaf, and
**108** are declarations or audit verdicts about other artifacts. The **ten** convention profiles
are recorded and pinned, and three behavioural negative controls prove the checks fire.

**H55 is complete**: the four **nested** `metrics` keys and the top-level `perturbation` block now
re-derive from the frozen record. Of the **736** published leaf values across **27** summaries,
**610** re-derive — the worst residual is **2.5e-12**, the median is **0**, and **321** of them are
exact. The **126** that do not are named with the reason the record cannot carry each one: **86**
ablation trade counts whose trade log was never committed, **32** H20 values whose OHLC panel was
never committed, and the **8** cross-validation Sharpes whose QQQ/IWM closes were never committed.
Six conventions the record hides are measured and pinned, including a **monthly-rebalance anchor
that changed inside the H16 family** and a **perturbation ratio that is a fallback rather than a
measurement**. The one pre-existing suite failure (the attribution-fix commit is not in this
squashed clone) is fixed by pinning the commit's recorded timestamp and cross-checking it against
`git` whenever the commit is present.

## The next task (H56)

The two families §H55 did not touch, both of them text echoes rather than blocks:

- **The `stats.json` echoes**: **40** files publish the head of a trade log as text (H52 pinned the
  count). Their `returns` field is a pandas repr of a return series, so the published numbers are
  rounded to the display precision and the series is truncated. **§H55 already measured that the
  `returns` text re-derives from the `equity.parquet` committed beside it**, provided the right
  initial capital is used — the H18 family starts from **100 000**, not the **1 000 000** every
  other producer uses, so `equity[0] / capital - 1` recovers the first bar's return exactly as it
  does elsewhere. What is still unmeasured is the **display convention** (how many head and tail
  rows the repr shows and how the series is truncated) and whether the `trades` text (the head of a
  trade log that was never committed as parquet) is recoverable at all.
- **The 14 benchmark `avg_trade_cost` entries** whose benchmark trade log and signals were never
  committed: their over-count factor is not measurable from the record, and the H27-style
  independent recomputation could not be applied to them. §H55 has since shown that the
  H27-style recomputation *does* work when the strategy's own signals and equity are committed —
  the H16/H17/H19/H22/H25 reconstructions reproduce their committed `best_equity` **bit-for-bit** —
  so the question for H56 is whether any of the **14** benchmark books have a committed equity
  curve and a committed signal that would let the benchmark be rebuilt the same way.

Both are *disclosure* tasks, not verification tasks: neither can move a published number, and both
are bounded by the record.

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

## What changed (H53)

- `tests/test_h53_published_metrics_disclosure.py` — the module that previously only enumerated the
  `metrics` summaries is replaced by the full re-derivation contract: **19 tests** (3 → 19). It
  re-derives every published value from the artifact that published it, pins the convention each
  producer used for each key, and carries four behavioural negative controls.
- `FINAL_REPORT.md` — new **§H53** section (with the 450-row disclosure table), the "Next task"
  section updated.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

### The gap, measured

The committed record holds **80** `summary.json` files. Four passes have audited parts of it, and
they are disjoint:

| pass | what it covered | how many |
|---|---|---:|
| §H49 | the `validation` blocks of the exploratory summaries | **5** summaries |
| §H51 | the `information_ratio` inside the metric blocks | **48** artifacts |
| §H52 | the `avg_trade_cost` (strategy and benchmark) | **5** summaries + **23** tracker entries |
| §H53 | the rest of the `metrics` block — the **13** scalar keys that carry the certified numbers | **37** summaries, **450** values |

What §H53 closed: **441 of 450** published values re-derive from their own frozen artifact. The
**9** that do not are the H9 regime block (`regime_sharpes` ×4, `worst_regime_sharpe` ×5) — the
producer fetched its VIX series from Yahoo at run time and never committed it, so the regime
labels are a function of an input the record does not hold.

### The conventions, per producer family

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

### The six findings

1. **The walk-forward stability gate was published on the PRE-FIX fold convention.** The library's
   `walk_forward_splits` used to end its last window at `n_splits * window_size`, silently dropping
   the tail of the return series; it was later changed so the last window absorbs it. **29** of the
   **37** published `wf_stability` values are pre-fix and **8** are post-fix. The split follows the
   production date: every post-fix summary is an H28 causal re-certification run of **2026-10-19**.
   All **8** post-fix summaries and **21** of the pre-fix ones are *discriminated* by
   the data (**29** of the 37); the other **8** — the H23 summaries, whose series length is an
   exact multiple of the fold count — coincide, because the tail is empty.
2. **`benchmark_alpha_annual` was published on the PRE-H51 beta convention** —
   `np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench)`, a mixed ddof that inflates beta by
   `n / (n - 1)`. All **7** published alphas (H16 ×4, H17, H19, H20) are pre-fix; they differ from
   the library's current alpha by **2.7e-05 … 3.7e-05**.
3. **The H9 family publishes the SAMPLE standard deviation** (`ddof=1`) because it passed a
   `pandas.Series` to `sharpe_ratio`; every other family passes an `ndarray` and publishes the
   POPULATION standard deviation (`ddof=0`). The two differ by `sqrt(n / (n - 1))`. The same
   container split decides the information ratio's excess volatility — §H51's disclosure, extended
   here to the **8** H28 runs it did not cover.
4. **The H9 family publishes a whole-sample profit factor and trade count**, not the OOS-window ones
   every other family publishes.
5. **Three of the four H16 summaries publish the TRAIN+VAL window Sharpe under the key
   `val_sharpe`** (n = 2769 bars) while the fourth publishes the val-window Sharpe (n = 756 bars).
   The published `param_grid_results.parquet` carries the *val-window* value in all four cases, so
   the summaries and their own grids disagree in three of them. **No gate reads the key.**
6. **`val_sharpe` holds three different things across the record**: `null` (H10), the OOS Sharpe
   (H21), and the val-window Sharpe (everybody else, except the three H16 summaries above).

## What was actually verified

- `python -m pytest -q -W error tests/test_h53_published_metrics_disclosure.py` → **19 passed** (3
  before this session).
- `python -m pytest -q -W error` → **1666 passed, 13 skipped** (full suite, up from 1650 + 13).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **95 files already formatted**.
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1055
  statements, 318 branches, 0 missed, 0 partial, 100.00%**; *"Required test coverage of 100.0%
  reached. Total coverage: 100.00%"* — unchanged, because nothing under `src/qtr` changed.
- **Every number is a read of the frozen artifacts** — no pipeline re-execution, no network, no
  grid re-run. The 450-row table in `FINAL_REPORT.md` §H53 was measured from the committed parquet
  files, and every published value was checked against the artifact that published it.
- **The conventions were measured, not assumed** — each was identified by reconstructing it and
  matching the published value to ≤ 1e-09 relative, and the reconstruction is now part of the
  contract. The fold convention is additionally anchored to the library's own
  `walk_forward_splits`, and the beta convention to the exact expression the library replaced.
- **Four behavioural negative controls** — the *current* library fold convention breaks the
  re-derivation of all **21** discriminable pre-fix summaries; the *current* library beta breaks all
  **7** published alphas; the val-only window breaks the three H16 summaries; and a published value
  nudged by one part in a thousand fails the residual check. None of them is an API check.
- **The blast radius is empty** — no published `passes` block reads `train_sharpe` or
  `val_sharpe`, and every gate key is computed from values that do re-derive.

## What remains unresolved

- **The nine H9 regime values** cannot be re-derived: the producer's VIX series was never
  committed. Disclosed, not quantified.
- **The 29 pre-fix `wf_stability` values** no longer re-derive from the library's current
  `walk_forward_splits`. Published on the convention in force when they were produced; disclosed,
  not rewritten. The certified families (H10, H22, H25) are among them.
- **The 7 published `benchmark_alpha_annual` values** are on the pre-H51 mixed-ddof beta;
  disclosed, not rewritten; no gate reads the key.
- **Three of the four H16 `val_sharpe` values** publish the train+val window under a key named for
  the val window, and disagree with their own grid artifact. Disclosed, not rewritten.
- **The four nested `metrics` keys** — `ablations` (35 summaries), `perturbation` (7),
  `perturbation_min_ratio` (7), `cross_validation` (2) — are pinned in the key union but not
  re-derived. The **28** ablation blocks whose equity files were committed are re-derivable; the
  **7** H16/H17/H19/H20 ablation blocks, all **14** perturbation blocks and both
  `cross_validation` blocks have no committed input and are not.
- **The 22 published `information_ratio` values** on the `ddof=1` convention no longer re-derive
  from the library (§H51); disclosed, not rewritten. H53 extends that disclosure to the **8** H28
  runs §H51 did not cover.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families'
  numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Treating a value that does not re-derive as a defect** — rejected: §H53 measured that every
  non-re-deriving value is a *convention* difference (a ddof, a window, a fold rule) or a missing
  input (the VIX series), never an arithmetic error. The contract therefore records the convention
  rather than "fixing" the published number.
- **Assuming one convention for the whole record** — rejected after measurement: ten distinct
  profiles across nineteen producer tags, including two that publish the *same key* with three
  different meanings (`val_sharpe`).
- **A negative control that only asserted the new API exists** — rejected for the same reason in
  H47/H48/H50/H51: the control must be behavioural, not a missing-keyword error.
- **Re-deriving the H9 regime block from the published Sharpe alone** — rejected: the regime labels
  are a function of a VIX series that was never committed, so the block is not a function of the
  record at all. Disclosed as indeterminable rather than approximated.

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
- The metadata source of truth (§H50) is pinned by `tests/test_generated_manifest_contract.py`;
  re-run it after any change to `pyproject.toml`, `.gitignore` or the packaging layout.
- The container-independence of `compare_to_benchmark` and the published convention split (§H51)
  are pinned by `tests/test_h51_benchmark_container_invariance.py`; re-run it after any change under
  `src/qtr/validation`.
- The published `metrics` block and its per-producer conventions (§H53) are pinned by
  `tests/test_h53_published_metrics_disclosure.py`; re-run it after any change under
  `src/qtr/validation`, `src/qtr/backtest` **or after a new artifact is committed**.
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under
  `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.

## The next task (H54)

> **Re-derive the published blocks of the summaries that publish no `metrics` block, and record the
> convention each publisher used for every key in them.**

### The gap (measured)

§H53 closed the `metrics` block. The record's other **43** summaries publish **no** `metrics`
block at all — they carry a different shape:

| measured | value |
|---|---:|
| summaries with no `metrics` block | **43** |
| distinct top-level keys they publish | **164** |
| distinct block shapes | **24** |
| leaf values they publish | **7 785** |
| summaries that publish no parquet artifact at all | **3** |

The shapes, by how many summaries publish them:

| shape | n | keys |
|---|---:|---|
| H23-style "all_pass" | 4 | `ablations`, `all_pass`, `alpha_vs_benchmark`, `best_combo`, `data_available`, `ddcv_only_grid`, `grid`, `oos_max_dd`, `oos_pf`, `oos_sharpe`, `oos_trades`, `passes`, `train_sharpe`, `wf_stability`, `worst_regime_sharpe` |
| H21-style "gates/verdict" | 4 | `all_pass`, `benchmark`, `experiment_id`, `gates`, `overall`, `splits`, `verdict` |
| H25-style "strategy/validation" | 3 | `benchmark_metrics`, `config`, `experiment_id`, `strategy_metrics`, `validation` |
| H16-style "gates/perturbations" | 4 | `all_gates_pass`, `benchmark_comparison`, `experiment_id`, `gates`, `gates_spec`, `oos_metrics`, `param_grid_summary`, `perturbations`, `regime_metrics`, `selected_params`, `split_metrics` |
| H22/H23-style "ablation" | 3 | `ablation`, `all_pass`, `alpha_vs_benchmark`, `data_available`, `ensemble_k`, `experiment_id`, `oos_max_dd`, `oos_pf`, `oos_sharpe`, `oos_trades`, `passes`, `top_k`, `train_sharpe`, `wf_stability`, `worst_regime_sharpe` |
| H25-style "grid" | 3 | `all_combo_results`, `gate_metrics`, `hypothesis`, `oos_metrics`, `selected_config` |
| plus 15 more shapes, 1–2 summaries each | 24 | — |

None of these **164** keys has ever been re-derived from the artifact that published it, and the
published `all_pass` / `verdict` / `gates` blocks (20, 15 and 15 summaries) rest on them.

### The work

1. **Enumerate** the 43 summaries, their 24 shapes, their 164 top-level keys and the artifact files
   each published them from (`equity_curve.parquet`, `benchmark_equity.parquet`,
   `param_grid_results.parquet`, `selected_equity.parquet`, `ablations.parquet`,
   `perturbation_results.parquet`, …).
2. **Re-derive** each published value from that summary's own frozen artifact, using the engine's
   own conventions, under the §H53 method: reconstruct the convention, match the published value
   to ≤ 1e-09 relative, and record the convention per producer.
3. **Separate the three classes** that the shapes fall into:
   - **certified-family blocks** (`gates`, `verdict`, `all_pass`, `splits`, `overall`) — the
     published verdicts of H10/H21/H22/H25; these are the ones that must not move;
   - **exploratory blocks** (`ablation`, `ablations`, `grid`, `all_results`, `all_combo_results`,
     `param_grid_summary`) — grid and ablation results published as nested tables;
   - **audit blocks** (`h26_sharpe_scale`, `h27_pnl_level`, `h28_causal_recertification`,
     `h29_lookahead_sweep`, `pf_robustness`) — summaries that publish a *verdict about the record*
     rather than metrics, and therefore read other artifacts instead of their own.
4. **Publish** a table: per summary and per key, the published value, the re-derived value, the
   residual, and whether it re-derives.
5. **Pin** the result with a new contract module (e.g.
   `tests/test_h54_non_metrics_block_disclosure.py`), including a **behavioural negative control**
   that reconstructs a pre-fix convention and shows the contract failing against it.
6. **Correct** any published wording that enumerates the covered scope, exactly as §H52 corrected
   §H47's and §H53 corrected §H49/§H51's.

### Constraints

- **Read-only** against the frozen artifacts. No pipeline re-execution, no network, no grid re-run,
  no artifact rewritten.
- No published artifact, gate threshold, verdict or certified number may move. Where a value does
  not re-derive, **disclose** it with the convention that explains it; do not rewrite it.
- The certified families (H10, H22, H25) are out of scope for *changes* — their numbers and
  verdicts are frozen — but they are **in** scope for measurement.
- The coverage gate, the lint gate and every pinned contract listed above must stay green.

### The runner-up (H55, if H54 is closed)

- **The four nested `metrics` keys** H53 left open: `ablations` (**28** re-derivable from their
  committed equity files, **7** not), `perturbation` / `perturbation_min_ratio` (**14**, none
  re-derivable) and `cross_validation` (**2**, none re-derivable).
- **The `stats.json` echoes**: 40 files publish the head of a trade log as text (H52 pinned the
  count). Their `returns` field is a pandas `to_string()` of a return series, so the published
  numbers are rounded to the display precision and the series is truncated — the conventions of that
  publisher are unrecorded.
- **The 14 benchmark `avg_trade_cost` entries** whose benchmark trade log and signals were never
  committed: their over-count factor is not measurable from the record, and the H27-style
  independent recomputation could not be applied to them.
