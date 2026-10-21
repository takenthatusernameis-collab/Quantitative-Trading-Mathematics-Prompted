# HANDOFF_CURRENT_SESSION — H52: the cost-attribution disclosure covers the whole committed record

## What changed

- `tests/test_trade_log_cost_reconciliation.py` — the frozen-record section is extended from one
  artifact to the whole record: **24 new tests** (13 → 37).
- `FINAL_REPORT.md` — new **§H52** section (with the full 82-row measured table), §H47's two
  disclosure bullets **corrected**, and the "Next task" and "What remains unresolved" sections
  updated.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## The gap, measured (three counts, not one)

§H47's disclosure was narrower than the record it describes.

1. **The scan missed half the record.** The pathspec `".experiments/artifacts/*/trades.parquet"`
   matches only the logs literally named `trades.parquet` — **41** of the **82** committed trade
   logs. The other **41** are named `best_trades`, `benchmark_trades`, `selected_trades`,
   `ensemble_trades`, `frozen_trades`, `baseline_trades`, `vix_only_trades`, `best_ddcv_trades` and
   `best_trades_w0.5`. The pathspec that sees the whole record is
   `".experiments/artifacts/*trades*.parquet"` → **82**.
2. **The family list was narrow.** The record spans **eleven** families — H3, H10, H11, H16, H17,
   H19, H20, H21, H22, H23 and H25 — across 36 artifact directories, plus **44** trade logs in 35
   exploratory artifacts that carry no `hypothesis`. §H47 named six families ("H10, H11, H16, H21,
   H22, H25").
3. **The published numbers were under-counted.** §H47 disclosed the `avg_trade_cost` of "the three
   exploratory 2026-10-10 MA-crossover summaries". **Five** committed summaries publish it, and the
   tracker metadata publishes the **benchmark's** `avg_trade_cost` in **23** further entries — a
   number §H47 did not mention at all.

## The measured record

Every one of the **82** committed trade logs shares one schema
(`timestamp, symbol, side, weight_change, price, cost`) and every one records the **aggregate**
attribution: all the trades of a bar carry the bar's whole value.

| class | logs | meaning |
|---|---:|---|
| aggregate, **changes a number** | **70** | at least one bar holds more than one trade, so the bar's value was written on each of its trades |
| aggregate, **coincides** | **7** | every bar holds exactly one trade, so the bar's value *is* that trade's own cost |
| empty | **5** | the log holds no trade at all (the empty H23 crypto logs) |

The **repetition factor** — the recorded column's total over the total of the per-bar values — is
the factor by which the column repeats each bar's value. It is **1** exactly when no bar repeats
its value, and it runs from **1.229953** to **20.677528** over the 70 logs where the attribution
changes a number. The full 82-row table is in `FINAL_REPORT.md` §H52.

## Why "uniform per bar" is the *pre-fix* attribution here — three legs

1. **Provenance (decisive).** The tracker stamps every artifact id with the UTC **start** of the
   run that produced it (`exp_<UTC timestamp>`, `src/qtr/tracking/experiment.py:79`). Every
   committed trade log's stamp precedes **2026-10-19T18:56:58Z**, while the engine's per-trade
   attribution fix is committed in `3fbef17` (2026-10-21 11:33:35Z). No committed log was written by
   the fixed engine — and the pre-fix `_extract_trades` wrote the per-bar total, `costs[idx]`, on
   every trade of the bar.
2. **The charge anchor.** The H27 `L3` check recomputes the per-bar cost from the trades'
   `weight_change` and `price` — **never** from the `cost` column — and matches the engine's
   per-bar charge to **~1e-19** for H9, H10, H21, H22 and H25. For those families the per-bar
   recorded value *is* the charge, so the recorded column repeats the charge.
3. **The engine's own definition.** The pre-fix `_extract_trades` wrote the per-bar total on every
   trade of that bar (§H47, "The gap").

**The honest caveat.** Uniformity alone does not separate an aggregate log from a per-trade log
whose trades happen to share the same cost — a two-symbol backtest with identical signals records
the same number either way. That is exactly why the single-symbol case is the *coincides* bucket
and why leg 1 is needed; the contract's negative control shows the classifier does recognise a
per-trade log when the trades' costs differ.

## The published numbers that read the column

Exactly one place in the package reads the trade log's `cost` column:
`src/qtr/backtest/engine.py:448` → `metrics["avg_trade_cost"] = trades["cost"].mean()`. **No runner
reads it** (checked statically over `src/qtr` and every `run_*.py`).

| published number | where | count | over-stated by the pre-fix attribution |
|---|---|---:|---|
| `strategy_metrics.avg_trade_cost` | 5 artifact `summary.json` | 5 | **3** — by 1.229953×, 1.247109× and 2.868948×. The other 2 hold a single trade, so their value is exact. |
| `benchmark_avg_trade_cost_step0` | tracker metadata (`.experiments/experiments.jsonl`) | 23 | **9 verified** — 6 × **20.0×** (measured against the committed benchmark trade log) and 3 × **5×** (measured against the committed `signals_buy_and_hold.parquet`: all five symbols enter on one bar). The other **14** use a 5-contract futures benchmark whose trade log and signals were never committed, so their factor is **not measurable from the record**. |

**40** `stats.json` files also echo the head of a trade log (its first row, cost column included) as
text. **No gate, threshold, verdict or certified number reads the column**, and the certified
families publish no `avg_trade_cost` at all.

## The contract now pinned (24 new tests)

1. **The whole record is named** — the committed trade logs (`git ls-files
   ".experiments/artifacts/*trades*.parquet"`) are exactly the **82** paths pinned in
   `TRADE_LOG_RECORD`. A committed trade log that is not named fails the contract.
2. **The split is complete and exact** — the three pinned sets (70 / 7 / 5) partition the record;
   each is asserted to be *exactly* the measured set, so a log that moves between classes fails.
3. **The structure is pinned** — every log's trade count, bar count and multi-trade-bar count, and
   the repetition factor's floor of 1.
4. **The provenance holds** — every committed log's run stamp precedes the attribution fix's commit.
5. **The published numbers are pinned** — the five `avg_trade_cost` values with their repetition
   factors, the 23 benchmark entries, the verified benchmark factors and entry bars, and the fact
   that the engine metric is the *only* reader of the column.
6. **Negative control** — the classifier recognises a per-trade log (the fixed engine over two
   symbols of *different* sizes) as `"per-trade"`, the reconstructed pre-fix log as `"aggregate"`,
   and the single-symbol log as `"aggregate"` with a repetition factor of exactly **1**.

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
- **Negative control** — behavioural, not an API check: the classifier is shown to answer
  `"per-trade"` for a log the fixed engine wrote and `"aggregate"` for the pre-fix reconstruction
  of the same data.
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

## The next task

**H53 — re-derive the published `metrics` block of every summary that publishes one from its own
frozen artifact, and record the convention each publisher used for every key in it.** The committed
record holds **80** `summary.json` files publishing about 190 distinct top-level keys; §H49 covered
the **5** `validation` blocks, §H51 the **48** `information_ratio` values and §H52 the
`avg_trade_cost` values, and the rest of the `metrics` block (**37** summaries) — which carries the
*certified* numbers — has never been re-derived. Read-only against the frozen artifacts; no grid
re-run; no published number may move. The full statement is in `NEXT_TASK.md`.
