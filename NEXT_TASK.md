# Next Task

## State

H35–H52 complete (the coverage gate is measured, declared and complete at 100% statement + branch;
the package's public API and the runners' import surface are both declared and pinned; the engine's
trade log reconciles with the costs it charges; the package's stochastic surface is seedable; the
published validation blocks re-derive from the frozen artifacts; the package's metadata has exactly
one declared source of truth; `compare_to_benchmark` is container-independent and the published
convention split is disclosed; **the H47 cost-attribution disclosure now covers the whole committed
record**).
**H52 is complete**: the pre-fix aggregate attribution of the committed trade logs is disclosed and
pinned for **every one of them** — **82** logs, not the 41 the §H47-era scan saw — and the set of
logs where that attribution actually *changes* a number (**70**) is pinned separately from the logs
where it cannot (**7**) and the logs that hold no trade (**5**). The arrangement is pinned by
`tests/test_trade_log_cost_reconciliation.py` (37 tests).

## What changed (H52)

- `tests/test_trade_log_cost_reconciliation.py` — the frozen-record section is extended from one
  artifact to the whole record: **24 new tests** (13 → 37). Every committed trade log is named,
  classified and pinned with its measured structure; the two sub-sets are pinned separately; the
  published numbers that read the column are pinned; and the **negative control** is behavioural.
- `FINAL_REPORT.md` — new **§H52** section, §H47's two disclosure bullets **corrected**, and the
  "Next task" and "What remains unresolved" sections updated.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

### The gap, measured

§H47's disclosure was narrower than the record on **three** counts.

1. **The scan missed half the record.** The pathspec `".experiments/artifacts/*/trades.parquet"`
   matches only the logs literally named `trades.parquet` — **41** of the **82** committed trade
   logs. The other **41** are named `best_trades`, `benchmark_trades`, `selected_trades`,
   `ensemble_trades`, `frozen_trades`, `baseline_trades`, `vix_only_trades`, `best_ddcv_trades` and
   `best_trades_w0.5`. The pathspec that sees the whole record is
   `".experiments/artifacts/*trades*.parquet"` → **82**.
2. **The family list was narrow.** The record spans **eleven** families — H3, H10, H11, H16, H17,
   H19, H20, H21, H22, H23 and H25 — across 36 artifact directories, plus **44** trade logs in 35
   exploratory artifacts that carry no `hypothesis`. §H47 named six families.
3. **The published numbers were under-counted.** §H47 disclosed the `avg_trade_cost` of "the three
   exploratory 2026-10-10 MA-crossover summaries". **Five** committed summaries publish it, and the
   tracker metadata publishes the **benchmark's** `avg_trade_cost` in **23** further entries — a
   number §H47 did not mention at all.

### The measured record

| class | logs | meaning |
|---|---:|---|
| aggregate, **changes a number** | **70** | at least one bar holds more than one trade, so the bar's value was written on each of its trades |
| aggregate, **coincides** | **7** | every bar holds exactly one trade, so the bar's value *is* that trade's own cost |
| empty | **5** | the log holds no trade at all (the empty H23 crypto logs) |

The **repetition factor** (the recorded column's total over the total of the per-bar values) is the
factor by which the column repeats each bar's value; it is **1** exactly when no bar repeats its
value, and it runs from **1.229953** to **20.677528** over the 70 logs where the attribution
changes a number.

### Why "uniform per bar" is the *pre-fix* attribution here — three legs

1. **Provenance (decisive).** The tracker stamps every artifact id with the UTC **start** of the
   run that produced it (`exp_<UTC timestamp>`, `src/qtr/tracking/experiment.py`). Every committed
   trade log's stamp precedes **2026-10-19T18:56:58Z**, while the engine's per-trade attribution
   fix is committed in `3fbef17` (2026-10-21 11:33:35Z). No committed log was written by the fixed
   engine — and the pre-fix `_extract_trades` wrote the per-bar total on every trade of the bar.
2. **The charge anchor.** The H27 `L3` check recomputes the per-bar cost from the trades'
   `weight_change` and `price` — **never** from the `cost` column — and matches the engine's
   per-bar charge to **~1e-19** for H9, H10, H21, H22 and H25. For those families the per-bar
   recorded value *is* the charge, so the recorded column repeats the charge.
3. **The engine's own definition.** The pre-fix `_extract_trades` wrote the per-bar total on every
   trade of that bar (§H47).

**The honest caveat.** Uniformity alone does not separate an aggregate log from a per-trade log
whose trades happen to share the same cost — a two-symbol backtest with identical signals records
the same number either way. That is exactly why the single-symbol case is the *coincides* bucket
and why leg 1 is needed; the contract's negative control shows the classifier does recognise a
per-trade log when the trades' costs differ.

### The published numbers that read the column

Exactly one place in the package reads the trade log's `cost` column:
`src/qtr/backtest/engine.py` → `metrics["avg_trade_cost"] = trades["cost"].mean()`. **No runner
reads it** (checked statically over `src/qtr` and every `run_*.py`).

| published number | where | count | over-stated by the pre-fix attribution |
|---|---|---:|---|
| `strategy_metrics.avg_trade_cost` | 5 artifact `summary.json` | 5 | **3** — by 1.229953×, 1.247109× and 2.868948×. The other 2 hold a single trade, so their value is exact. |
| `benchmark_avg_trade_cost_step0` | tracker metadata (`.experiments/experiments.jsonl`) | 23 | **9 verified** — 6 × **20.0×** (measured against the committed benchmark trade log) and 3 × **5×** (measured against the committed `signals_buy_and_hold.parquet`: all five symbols enter on one bar). The other **14** use a 5-contract futures benchmark whose trade log and signals were never committed, so their factor is **not measurable from the record**. |

**40** `stats.json` files also echo the head of a trade log (its first row, cost column included) as
text. **No gate, threshold, verdict or certified number reads the column**, and the certified
families publish no `avg_trade_cost` at all.

## What was actually verified

- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **37 passed** (13
  before this session).
- `python -m pytest -q -W error` → **1647 passed, 13 skipped** (full suite, up from 1623 + 13).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **94 files already formatted**.
- `python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing` → `src/qtr` = **1055
  statements, 318 branches, 0 missed, 0 partial, 100.00%**; *"Required test coverage of 100.0%
  reached. Total coverage: 100.00%"* — unchanged, because nothing under `src/qtr` changed.
- **Every number is a read of the frozen artifacts** — no pipeline re-execution, no network, no grid
  re-run. The 82-row table in `FINAL_REPORT.md` §H52 was measured from the committed parquet files,
  and every published value was checked against the artifact that published it.
- **Negative control** — the classifier is shown to answer `"per-trade"` for a log the fixed engine
  wrote (two symbols of *different* sizes) and `"aggregate"` for the reconstructed pre-fix log of
  the same data; the single-symbol log is `"aggregate"` with a repetition factor of exactly **1**.
- **The provenance leg was checked, not assumed** — every committed log's artifact-id stamp parses
  and precedes the fix commit's date.

## What remains unresolved

- **The 14 benchmark `avg_trade_cost` entries** whose benchmark trade log and signals were never
  committed are on the pre-fix basis (same engine commit) but their over-count factor is **not
  measurable from the record**. Disclosed, not quantified.
- **The three published `avg_trade_cost` values** over-stated by the pre-fix attribution remain
  published as they are; the artifacts are frozen and no gate reads them.
- **The 22 published `information_ratio` values** on the sample (`ddof=1`) convention no longer
  re-derive from the library (§H51); disclosed, not rewritten.
- **H9's published OOS Sharpe** is on the sample convention (gap 1.026e-04); disclosed and pinned,
  verdict cannot move.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families'
  numbers and verdicts are frozen.

## Approaches already tried / failed (and why)

- **Fixing the trade log by changing the charge** — rejected: the charge was never wrong (H27's
  `L3` check proves it to ~1e-19). Only the *attribution* inside the log was wrong, so the fix
  moves the log, not the charge.
- **A negative control that only asserted the new API exists** — rejected for the same reason in
  H47/H48/H50/H51: the control must be behavioural, not a missing-keyword error.
- **Using the per-bar *first* recorded value as the bar total for every log** — rejected after
  measurement: that is only the bar total for an *aggregate* log. For a per-trade log the first
  value is one trade's own share, so the "over-count" computed from it is meaningless. The contract
  therefore classifies the recorded form first and only computes the repetition factor on an
  aggregate log.
- **Deriving the attribution from the log alone** — rejected: a per-trade log whose trades happen to
  share the same cost is indistinguishable from an aggregate log by the `cost` column alone (a
  two-symbol backtest with identical signals records the same number either way). The disclosure
  therefore rests on the **provenance** leg (the artifact id's run stamp vs the fix's commit),
  which is measured, and the negative control shows the classifier can still recognise a per-trade
  log when the costs differ.
- **Re-deriving every artifact's cost model to decide each log independently** — rejected as
  disproportionate: it needs each runner's cost model, ADV and volume inputs, and the published
  record does not carry all of them (two buy-and-hold artifacts used a fixed `0.0002` per trade).
  The provenance leg plus the H27 charge anchor covers the same ground with facts the record
  actually holds.

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
- Re-run `tests/test_runner_causality_inventory.py`, `tests/test_runner_metric_agreement.py` and
  `tests/test_benchmark_gate_contract.py` after any change in a runner or under
  `src/qtr/validation`.
- The coverage gate (`python -m pytest -q --cov=qtr --cov-branch`) must stay at 100% for
  `src/qtr`; the lint gate (`python -m ruff check src tests run_*.py` and
  `python -m ruff format --check src tests run_*.py`) must stay clean.

## The next task (H53)

> **Re-derive the published `metrics` block of every summary that publishes one from its own
> frozen artifact, and record the convention each publisher used for every key in it.**

### The gap (measured)

The committed record holds **80** `summary.json` files. Three of them have been audited so far, and
they are disjoint:

| pass | what it covered | how many |
|---|---|---:|
| §H49 | the `validation` blocks of the exploratory summaries | **5** summaries |
| §H51 | the `information_ratio` inside the metric blocks | **48** summaries |
| §H52 | the `avg_trade_cost` (strategy and benchmark) | **5** summaries + **23** tracker entries |

What is **not** covered is the rest of the **`metrics` block** — the block that carries the
*certified* numbers. `metrics` appears in **37** summaries and carries `oos_sharpe`, `oos_pf`,
`oos_max_dd`, `oos_trades`, `profit_factor`, `max_drawdown`, `test_sharpe`, `val_sharpe`,
`train_sharpe`, `wf_stability`, `worst_regime_sharpe` and `regime_sharpes` beside the
`information_ratio` that §H51 re-derived. **None of those keys has ever been re-derived from the
artifact that published it.** The published `passes` / `all_pass` / `verdict` blocks (49 / 57 / 52
summaries) rest on them.

The measurement behind the task: the 80 summaries publish about 190 distinct top-level keys. The
`metrics` block is the one that reaches the certified families' published verdicts.

### The work

1. **Enumerate** the summaries that publish a `metrics` block (37) and, for each, the keys it
   publishes and the artifact files it published them from (`equity_curve.parquet`,
   `returns.parquet`, `best_equity.parquet`, `selected_equity.parquet`, `ensemble_equity.parquet`,
   `best_ddcv_equity.parquet`, `benchmark_equity.parquet`, …).
2. **Re-derive** each published metric from that summary's own frozen artifact, using the engine's
   own conventions (the full return series including the opening bar, as §H49 established).
3. **Record the convention each publisher used** for each key — the annualisation factor, the
   risk-free rate, the OOS window, the drawdown definition, the trade-count definition, the
   Sharpe's deviation convention — because a value that does not re-derive is usually a *convention*
   difference, not a defect (as §H51 showed for `ddof`).
4. **Publish** a table: per summary and per key, the published value, the re-derived value, the
   residual, and whether it re-derives.
5. **Pin** the result with a new contract module (e.g.
   `tests/test_h53_published_metrics_disclosure.py`), including a **behavioural negative control**
   that reconstructs a pre-fix convention and shows the contract failing against it.
6. **Correct** any published wording that enumerates the covered scope, exactly as §H52 corrected
   §H47's.

### Constraints

- **Read-only** against the frozen artifacts. No pipeline re-execution, no network, no grid re-run,
  no artifact rewritten.
- No published artifact, gate threshold, verdict or certified number may move. Where a value does
  not re-derive, **disclose** it with the convention that explains it; do not rewrite it.
- The certified families (H10, H22, H25) are out of scope for *changes* — their numbers and
  verdicts are frozen — but they are **in** scope for measurement.
- The coverage gate, the lint gate and every pinned contract listed above must stay green.

### The runner-up (H54, if H53 is closed)

- The **`stats.json`** echoes: 40 files publish the head of a trade log as text (H52 pinned the
  count). Their `returns` field is a pandas `to_string()` of a return series, so the published
  numbers are rounded to the display precision and the series is truncated — the conventions of that
  publisher are unrecorded.
- The **14 benchmark `avg_trade_cost` entries** whose benchmark trade log and signals were never
  committed: their over-count factor is not measurable from the record, and the H27-style
  independent recomputation could not be applied to them.
