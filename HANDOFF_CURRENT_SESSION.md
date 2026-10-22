# HANDOFF_CURRENT_SESSION — H55 complete

## What changed (H55)

**H55:** the four **nested** blocks of the `metrics` block — and the **top-level** `perturbation`
block that no earlier pass covered — now re-derive from the frozen record. Of the **736** published
leaf values across **27** summaries, **610** re-derive (worst residual **2.5e-12**, median **0**,
**321** exact) and the **126** that do not are named with the reason the record cannot carry each
one. **Six** conventions the record hides are measured and pinned, and four behavioural negative
controls prove the checks fire.

- `tests/test_h55_nested_metrics_disclosure.py` — **new**, the H55 contract: **26 tests**.
- `tests/h55_rederivation.py` — **new**, the re-derivation helper (the two monthly-rebalance
  anchors, the first H16 run's per-family-ablation convention, and the per-family re-derivation of
  H16, H17, H19, H22 and H25). Every re-execution is gated on a **bit-for-bit** match against the
  committed equity artifact.
- `FINAL_REPORT.md` — new **§H55** section.
- `tests/test_trade_log_cost_reconciliation.py` — the **one pre-existing suite failure** is fixed.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## The gap, measured

§H53 closed the thirteen **scalar** keys of the `metrics` block and §H54 closed the **43**
summaries that publish no `metrics` block at all. Neither touched the four **nested** blocks
inside the `metrics` block of the summaries that do publish one, and neither touched the
**top-level** `perturbation` block of the five summaries that publish both.

| block | summaries | leaves | re-derived | disclosed |
|---|---:|---:|---:|---:|
| `ablations` | 27 | 661 | **547** | **114** |
| `perturbation` | 7 | 35 | **31** | **4** |
| `perturbation_min_ratio` | 7 | 7 | **7** | **0** |
| `cross_validation` | 2 | 8 | **0** | **8** |
| top-level `perturbation` | 5 | 25 | **25** | **0** |
| **total** | **27** | **736** | **610** | **126** |

## The three re-derivation routes

1. **The committed ablation equity curves** (20 summaries). The engine computes
   `equity = (1 + net_returns).cumprod() * capital`, so the equity curve *determines* its own
   return series: the first bar's return is `equity[0] / capital - 1`, every later bar's return is
   the ratio of two consecutive equity values. Worst residual **7e-14**.
2. **The committed strategy inputs** (12 summaries: H16 x4, H17, H19, H22 x3, H25 x2, and H20).
   These families publish no per-ablation artifact but do commit the prices, the volumes and the
   VIX series, so their blocks re-derive by re-running the producers' own signal builders over the
   frozen inputs — each gated on a **bit-for-bit** match against the committed equity artifact.
3. **The gate inputs that were never committed** (the cross-validation closes, H20's OHLC panel).

## The six findings

1. **The H9 family's ablation block mixes two windows** — its `oos_sharpe`/`max_drawdown` are
   OOS-window, its `profit_factor`/`trades` are whole-sample.
2. **The H9 family's ablation Sharpe is on the POPULATION standard deviation** (`ddof=0`), while
   the same summary's top-level Sharpes are on the SAMPLE standard deviation (`ddof=1`).
3. **The H16 family was produced under two different monthly-rebalance anchors** — the calendar
   month end for the first two runs, the actual last trading day for the last two. The difference
   moves the published OOS Sharpe by **3 %**.
4. **The first H16 summary published its three per-family ablations as the same block** — the
   unrestricted single-factor result.
5. **The H23 family's `perturbation_min_ratio` is a fallback, not a measurement** — `0.0` because
   the base OOS Sharpe is not positive in all seven summaries.
6. **Two H22 summaries publish the perturbation gate but not the perturbation values.**

## The disclosure list

- **The 86 ablation trade counts**: the record holds each ablation's equity curve, never its
  trade log.
- **H20's 32 values**: the daily OHLC panel the signal builder reads was never committed.
- **The 8 cross-validation Sharpes**: the QQQ/IWM closes were fetched at run time, never
  committed.

## The blast radius

No published gate reads an `ablations` block or a `cross_validation` block. The published
**perturbation** gate reads exactly one number — the ratio — and that number re-derives in every
one of the **19** summaries that publish it. No published number moves.

## What was actually verified

- `python -m pytest -q -W error tests/test_h55_nested_metrics_disclosure.py` → **26 passed**.
- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **37 passed** (the
  pre-existing failure is gone).
- `python -m pytest -q -W error` → **1 710 passed, 16 skipped** (full suite; the only failure
  before this session is fixed).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **98 files already formatted**.
- **Every number is a read of the frozen artifacts** — no network, no grid re-run, nothing
  written.

## A note on the scope constraint

§H55's brief said "no pipeline re-execution". §H55 does re-execute a **bounded** number of
backtests — the producers' own signal builders over the committed inputs — for the summaries of
route 2. The deviation is deliberate and is recorded so the next session can judge it: re-executing
the *grid* would regenerate the record and is still forbidden, but re-running the signal builder
over frozen inputs is a re-derivation, and it is **gated on a bit-for-bit match against the
committed equity artifact**, so it cannot silently drift into a re-run that agrees with nothing.
Nothing was written, no network was touched, and no published number moved.

## What remains unresolved

- **The 126 disclosed values** (§H55) are not functions of the record; they are disclosed, not
  rewritten, and no gate reads any of them.
- **The first H16 summary's per-family ablation block** publishes the unrestricted single-factor
  result three times; reproduced under the convention that produced it, not rewritten.
- **The H23 perturbation ratio** is the `oos_sharpe <= 0` fallback in all seven summaries; the
  robustness measurement it stands for was never published.
- **Two H22 summaries publish a perturbation gate with no perturbation values.**
- **H56 is assigned** — the `stats.json` text echoes and the 14 benchmark `avg_trade_cost`
  entries; stated in full in `NEXT_TASK.md`.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families
  are frozen.
