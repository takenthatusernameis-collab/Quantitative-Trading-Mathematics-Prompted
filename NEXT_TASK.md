# NEXT TASK — next agent (post-H26)

## Status: H26 Sharpe annualization-scale audit — COMPLETE

**What was found (the headline):** every published "OOS Sharpe" in this project is
`sharpe_ratio(returns)` with the default `periods_per_year=252`, i.e. the **per-bar**
mean/vol ratio × `√252`. For the **daily** families the bar is a trading day, so
`√252` *is* the calendar annualization. For the **intraday (1h)** families the bar is
one hour, so the published number is **not** an annualized Sharpe: it understates the
annualized value by **2.55×** (the repo's own `√(252·6.5)` vol-target convention) to
**4.76×** (the empirical calendar convention).

- Certified family, published → annualized (repo vol convention): H10 1.276 → **3.253**,
  H22 1.372 → **3.499**, H25 1.324 → **3.375**. Independent daily-aggregation estimate:
  5.04 / 5.20 / 5.09 (confirms the magnitude).
- **No verdict, gate, threshold or certified number changed.** The mis-scaling is
  *conservative* (it understates the intraday edge), and the profit-factor gate is
  scale-invariant.
- The **"Sharpe CI-fragile" caveat was a scale artifact**: H25's Sharpe CI
  [0.8834, 1.7506] → **[2.2521, 4.4633]**, P(Sharpe≥1.0) 0.9275 → **1.0000** on the
  repo's own convention. The **PF margin fragility stands** (scale-invariant).
- Two cross-artifact defects found by the reproduction anchor (H9 excluded):
  (a) H9 was published with the *sample*-std (ddof=1) Sharpe estimator, H10+ use
  *population*-std (ddof=0) — relative difference ≈1e-4, H9 is no longer bit-reproducible
  with the current library; (b) H9's published "OOS profit factor" is the **full-sample**
  (train+val+test) PF; the correct OOS-window PF is 1.2529 (still < 1.3, so H9 stays
  REJECTED — the defect was conservative).

**Delivered:** `run_h26_sharpe_scale_audit.py` (deterministic, offline, ~1.8 s),
`.experiments/artifacts/h26_sharpe_scale/{summary.json,scale_table.parquet}`,
`tests/test_h26_sharpe_scale_audit.py` (44 tests), `bars_per_year` +
`annualized_sharpe` in `src/qtr/validation/statistics.py`,
`HYPOTHESIS_SPEC.md` §H26 (pre-registration **and** measure log),
`FINAL_REPORT.md` (table scale note, §H26 detail, corrected conclusion + exec summary).

**Verified this session:** full suite **586 passed, 0 warnings** (542 before + 44 new);
`pytest -W error`; `--cov=qtr`; `ruff check`; `ruff format --check`;
`bash -n .github/scripts/*.sh`; `bash .github/scripts/test_kilo_progress.sh`.

## Precise next task (free data, bounded, verifiable) — highest value

**Audit the *level* of the certified intraday P&L.** The scale correction implies an
annualized Sharpe of **3.25–6.53** for the certified family, versus ≈0.5–1.5 for
published real-world futures time-series-momentum strategies. Either the backtest
contains a scale/level bug (which would invalidate the certified family) or the sample
is extraordinary (which would need to be stated as such). H26 deliberately did **not**
attempt this audit.

Scope (all from committed artifacts + the cached data; no paid data, no new hypothesis):

1. **Position-sizing consistency.** Recompute, from `prices.parquet` + `positions.parquet`
   of `exp_2026-10-11T17-41-18-169363Z` (H10) and `exp_2026-10-14T20-08-34-613690Z` (H25),
   the dollar P&L implied by the engine's contract maths: contracts = weight × 1e6 /
   (price × multiplier), P&L = contracts × price change × multiplier, and compare with the
   logged `returns.parquet` bar by bar. Check the futures multipliers/tick values used by
   `CostModel` against the contract specs in `run_h9_intraday_tsmom_experiment.py`.
2. **Vol-target coherence.** The strategy targets 15% annualized vol using
   `√(252·6.5)` on hourly returns; the realized hourly vol of the certified config is
   0.259% ⇒ ≈10.5% calendar-annualized vol at ≈32% calendar-annualized return
   (1.725e-4 mean per hour). Verify the vol target is applied to the same quantity the
   returns are built from, and that the realized vol/return are consistent with the
   position caps (`max_pos` 0.5 in H22/H25) and the trailing-stop logic.
3. **Cost-scale sanity.** The mean cost drag is ≈1.17e-5 of capital per hour (~29% of
   the gross edge). Recompute it from `trades.parquet` (position changes × contracts ×
   per-contract cost) and confirm the cost model is charged on the same notional the
   return side uses.
4. **Verdict rule (pre-register before executing):** `LEVEL_CONFIRMED` iff the
   recomputed per-bar P&L matches the logged returns to ≤1e-9 *and* the implied
   annualized Sharpe is reproduced from the position/price/contract inputs alone
   (i.e. the high Sharpe comes from the strategy on this sample, not from a unit error);
   `LEVEL_DEFECT` if any of the three checks fails by more than 1%. Either verdict must
   be written to `HYPOTHESIS_SPEC.md` and pinned by a new test file.

Constraints: do **not** change any gate, threshold, verdict or certified number; do not
re-run the 13,824-combo H10 grid (0.48 CPU-h) unless a defect is found and the
re-registration is explicit; keep the audit offline and deterministic.

## Documented next task (requires paid data — still outstanding)

Per `FINAL_REPORT.md` §Next Task: widen the OOS window with **paid hourly futures
data** so the **PF** bootstrap CI clears its gate with margin (H13 CI [1.190, 1.425];
H25 Robustness CI [1.2049, 1.4425], P(PF≥1.3)=0.6215). The Sharpe side of that
requirement was withdrawn by H26 (scale artifact). Do not run further hypotheses on
free data — the free-data hypothesis space is exhausted (yfinance hourly `=F` capped
~730 days; Coinbase ~12 days).

## Verification commands (run before declaring any task done)

`pip install -e .` (ensure `qtr` importable), then:
- `python -m pytest -q` (full suite, ~3:30)
- `python -m pytest -W error -q`
- `python -m pytest --cov=qtr --cov-report=term-missing`
- `python -m ruff check src tests run_*.py`
- `python -m ruff format --check src tests run_*.py`
- `bash -n .github/scripts/*.sh` and `bash .github/scripts/test_kilo_progress.sh`

## Notes

- `validate_strategy`'s `param_stability`/`walkforward_stability` are proxies;
  the literal ±1-std perturbation gate and 5-fold walk-forward metric live in
  the H10/H11/H9–H25 runners. Do not conflate them.
- `walk_forward_splits` tail-absorption is already fixed in HEAD
  (`statistics.py:108-110`); nothing to change there.
- `sharpe_ratio` uses the **population** std (ddof=0) because it converts to a numpy
  array first. H9's artifact predates that and used pandas' sample std (ddof=1); the
  H26 test suite pins both conventions so the drift cannot recur silently.
- The Sharpe scale convention is now explicit in the code: use
  `qtr.validation.statistics.annualized_sharpe(returns, index)` (factor inferred from
  the bar timestamps) when an *annualized* Sharpe is wanted; the legacy
  `sharpe_ratio(...)` default is the frozen certification metric and must not be
  relabelled as "annualized" in any report.
