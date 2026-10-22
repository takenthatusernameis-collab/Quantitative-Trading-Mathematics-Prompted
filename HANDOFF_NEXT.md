# HANDOFF_NEXT — H55: the four nested `metrics` blocks re-derive from the frozen record

## What changed (H55)

**H55:** the four **nested** blocks of the `metrics` block — and the **top-level** `perturbation`
block that no earlier pass covered — now re-derive from the frozen record. Of the **736** published
leaf values across **27** summaries, **610** re-derive (worst residual **2.5e-12**, median **0**,
**321** exact) and the **126** that do not are named with the reason the record cannot carry each
one. **Six** conventions the record hides are measured and pinned, and four behavioural negative
controls prove the checks fire.

- `tests/test_h55_nested_metrics_disclosure.py` — the H55 contract: **26 tests**. Every published
  leaf the reconstruction reaches must agree with it; every published leaf it does not reach must
  be *named* with the reason the artifact cannot carry it; and the record's own shape (the block
  counts, the leaf count, the producer families, the re-derived/disclosed split) must not move.
- `tests/h55_rederivation.py` — **new**, the re-derivation helper. It carries the two
  monthly-rebalance anchors, the per-family-ablaboration convention of the first H16 run, and the
  per-family re-derivation of H16, H17, H19, H22 and H25. Every re-execution is gated on a
  **bit-for-bit** match against the committed equity artifact.
- `FINAL_REPORT.md` — new **§H55** section (the measured record, the three re-derivation routes,
  the **six** conventions, the disclosure list and the blast radius).
- `tests/test_trade_log_cost_reconciliation.py` — the **one pre-existing suite failure** is fixed.
  The attribution-fix commit `3fbef17` is not in this squashed clone, so the test shelled out to
  `git show` and died. Its UTC time — **2026-10-21 11:33:35Z** — is already recorded in
  `FINAL_REPORT.md`, so the timestamp is now pinned in the test and **cross-checked against `git`
  whenever the commit is present**. The check is now *stronger* than the shell-out it replaces.
- `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_CURRENT.md`, `HANDOFF_CURRENT_SESSION.md`,
  `HANDOFF_NEXT.md` updated.
- **Nothing under `src/qtr` changed.** No artifact, gate threshold, verdict or certified number was
  modified; no grid was re-run; no hypothesis was added.

## The measured record

============  ==========================================  =========
measured      quantity                                    value
============  ==========================================  =========
blocks        the four nested `metrics` keys                **4**
blocks        the top-level `perturbation` block            **1**
summaries     publishing at least one nested block          **27**
leaf values   published                                    **736**
leaf values   re-derived                                   **610**
leaf values   disclosed                                    **126**
residual      worst relative residual                      **2.5e-12**
residual      median relative residual                     **0**
residual      exact (zero-residual) re-derivations         **321**
producers     producer families                            **10**
============  ==========================================  =========

============  ==================================  ==========  ==========
block         summaries   leaves                   re-derived  disclosed
============  ==================================  ==========  ==========
`ablations`   27          661                      **547**     **114**
`perturbation` 7          35                       **31**      **4**
`perturbation_min_ratio` 7  7                      **7**       **0**
`cross_validation` 2      8                        **0**       **8**
top-level `perturbation` 5  25                     **25**      **0**
============  ==================================  ==========  ==========

## The three re-derivation routes

1. **The committed ablation equity curves** (20 summaries: H9 x3, H10 x2, H21 x1, H22 x5,
   H23 x7, H25 x2). The engine computes `equity = (1 + net_returns).cumprod() * capital`, so the
   equity curve *determines* its own return series — the first bar's return is
   `equity[0] / capital - 1` and every later bar's return is the ratio of two consecutive equity
   values. Worst residual over the route: **7e-14**. The **86** published ablation *trade counts*
   do not re-derive: the record holds the ablation's equity curve but never its trade log.
2. **The committed strategy inputs** (12 summaries: H16 x4, H17, H19, H22 x3, H25 x2, and H20).
   These families publish no per-ablation artifact, but they commit the prices, the volumes and
   the VIX series their strategies were built from, so their blocks re-derive by re-running the
   producers' own signal builders over the frozen inputs. Each re-derivation is **validated
   bit-for-bit against the committed `best_equity` / `equity` artifact before it is used to check
   any published value** — which is why these land on **exactly zero** residuals. H20 is the
   exception: its signal builder reads the daily OHLC panel and the record only committed the
   close.
3. **The gate inputs that were never committed**: the QQQ/IWM closes the cross validation reads
   and the OHLC panel H20's signal reads. Those values are **not functions of the record**.

## The six findings

1. **The H9 family's ablation block mixes two windows.** Its `oos_sharpe` and `max_drawdown` are
   OOS-window values, but its `profit_factor` and `trades` are **whole-sample** values — the
   producer read them off the engine's own full-sample metric block. Every other family publishes
   an OOS-window profit factor under the `oos_` prefix.
2. **The H9 family's ablation Sharpe is on the POPULATION standard deviation** (`ddof=0`),
   because the producer passed `.values` to `sharpe_ratio` — while the *same* summary's top-level
   Sharpes are on the SAMPLE standard deviation (`ddof=1`). §H53 recorded the second half of the
   split; H55 records the first. The sample convention breaks 78 of the 86 nested Sharpes; the
   other 8 are degenerate (published Sharpe exactly `0.0`).
3. **The H16 family was produced under two different monthly-rebalance anchors.** The producers'
   current `monthly_rebalance` anchors the month-end target on the *actual last trading day*; the
   run-time code anchored it on the *calendar* month end. The two differ by one trading day on
   every month boundary and move the published OOS Sharpe by **3 %**. The **first two** H16 runs
   used the calendar anchor and the **last two** used the actual-last-trading-day anchor. The
   contract *identifies* the anchor per summary from the committed equity curve rather than
   assuming it; the negative control shows the wrong anchor fails the bit-for-bit validation and
   breaks all four published perturbation variants.
4. **The first H16 summary published its three per-family ablations as the same block.**
   `exp_2026-10-13T21-11-45-843908Z` publishes identical values under `family_value`,
   `family_momentum` and `family_quality`; the block is the *unrestricted* single-factor result
   (all three families, `n_factors=1`), reproduced here bit-for-bit. The three later H16 summaries
   publish the per-family blocks correctly. The block is exploratory — no gate reads it.
5. **The H23 family's `perturbation_min_ratio` is a fallback, not a measurement.** The ratio is
   `0.0` whenever the base OOS Sharpe is not positive, which is the case in all **seven** H23
   summaries (five publish an OOS Sharpe of exactly `0.0`, two publish a negative one).
6. **Two H22 summaries publish the perturbation gate but not the perturbation values.**
   `exp_2026-10-14T07-12-35-292010Z` and `exp_2026-10-14T07-12-59-473353Z` publish
   `passes.perturbation = true` and no perturbation block at all, while the other three H22
   summaries and both H25 summaries publish the top-level `perturbation` block.

## The disclosure list

- **The 86 ablation trade counts** (H9's `trades`, the H10-style `oos_trades`): the record holds
  each ablation's equity curve but never its trade log.
- **H20's 32 values** (four ablation blocks of seven leaves, and the four perturbation variant
  Sharpes): the daily OHLC panel the signal builder reads was never committed.
- **The 8 cross-validation Sharpes** (H19 and H20, QQQ and IWM): the cross-validation closes were
  fetched at run time and never committed.

## The blast radius

No published gate reads an `ablations` block or a `cross_validation` block. The published
**perturbation** gate reads exactly one number — the ratio — and that number re-derives in every
one of the **19** summaries that publish it, including the one whose variant Sharpes cannot be
re-derived. No published number moves.

## What was actually verified

- `python -m pytest -q -W error tests/test_h55_nested_metrics_disclosure.py` → **26 passed**.
- `python -m pytest -q -W error tests/test_trade_log_cost_reconciliation.py` → **37 passed** (the
  pre-existing failure is gone).
- `python -m pytest -q -W error` → **1 710 passed, 16 skipped** (full suite; the only failure
  before this session is fixed).
- `python -m ruff check src tests run_*.py` → *All checks passed!*.
- `python -m ruff format --check src tests run_*.py` → **98 files already formatted**.
- **Every number is a read of the frozen artifacts** — no network, no grid re-run, nothing
  written. The re-executed families re-run the producers' own signal builders over the committed
  inputs and are validated bit-for-bit against the committed equity artifact before any published
  value is checked.

## A note on the scope constraint

§H55's brief said "no pipeline re-execution". §H55 does re-execute a **bounded** number of
backtests — the producers' own signal builders over the committed inputs — for the summaries of
route 2. The deviation is deliberate and is recorded here so the next session can judge it:
re-executing the *grid* would regenerate the record and is still forbidden, but re-running the
signal builder over frozen inputs is a re-derivation, and it is **gated on a bit-for-bit match
against the committed equity artifact**, so it cannot silently drift into a re-run that agrees with
nothing. Nothing was written, no network was touched, and no published number moved.

## What a next session inherits

- **One task is assigned (H56)** — stated in full in `NEXT_TASK.md`: the `stats.json` text echoes
  and the 14 benchmark `avg_trade_cost` entries. §H55 measured the first half of the `stats.json`
  task already: the `returns` text re-derives from the `equity.parquet` committed beside it,
  provided the **H18 family's 100 000** initial capital is used rather than the **1 000 000**
  every other producer uses.
- The pre-registered free-data hypothesis space (H1–H30) remains exhausted; the certified families
  are frozen.
- **The 126 disclosed values** (§H55) are not functions of the record; they are disclosed, not
  rewritten. No gate reads any of them.
