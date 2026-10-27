# Intraday Futures TSMOM — Strategy Summary and Evidence Status

**Prepared:** 2026-10-27  
**Repository:** [Quantitative-Trading-Mathematics-Prompted](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted)  
**Scope:** Documentation-only summary of H10 and its multi-contract H22 extension. No strategy code, historical result, gate, threshold, or certified artifact is changed by this document.

## Executive conclusion

Intraday futures time-series momentum (TSMOM) was a high-ranking *reported* result in this repository, but it is **not currently a validated trading edge**. The published H10 and H22 results were materially overstated by a signal-timing/look-ahead defect. The repository's later H29 audit marks both published constructions as `LOOKAHEAD`; H28's causal re-certification records `CAUSAL_REJECTED` and no causal-certified members in the H10/H22/H25 family.

Treat the original Sharpe ratios as historical, invalidated estimates—not forecasts, independently validated performance, or a basis for live deployment. Preserve the frozen artifacts for auditability. Any future research should begin from a causally correct implementation and a new, explicitly pre-registered evaluation, not from silently editing the original numbers.

## 1. Strategy idea

The hypothesis is that the direction of recent futures returns contains information about subsequent returns, and that volatility scaling plus path-dependent exits can turn that directional persistence into a diversified, risk-managed strategy.

### Signal construction

The H10 family implementation computes hourly returns and two momentum directions:

- **Slow direction:** sign of the return over a long lookback. The selected H10/H22 configuration uses 1,008 hourly bars.
- **Fast direction:** sign of the return over a shorter lookback, one quarter of the long lookback (252 hourly bars in the selected configuration).
- **Volatility scaling:** estimates long- and short-window realized volatility, inversely scales each directional component, blends the components, then scales exposure toward a 15% annualized target-volatility baseline (subject to caps and available history).
- **Target timing:** the implementation collapses the hourly signal to a daily target and expands that target back onto the hourly price grid. This step is the critical defect: the published resampling/label convention allowed a target computed using the end of a day to appear on earlier hourly bars of that same day.

These are research-code conventions, not a recommendation to trade this exact signal. The implementation and timing defect are documented in [H9 signal code](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/run_h9_intraday_tsmom_experiment.py), [H10 experiment](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/run_h10_intraday_tsmom_pfopt_experiment.py), and [H29 look-ahead audit](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/.experiments/artifacts/h29_lookahead_sweep/summary.json).

### Position management and exits

The selected H10 configuration used:

- Long volatility lookback: 1,008 hourly bars.
- Fast momentum lookback: 252 hourly bars.
- Target volatility baseline: 15% annualized.
- Trailing exit: 2.0 × the implementation's ATR-like measure.
- Maximum holding period: 60 hourly bars.
- Volatility-limit multiplier: 1.5.
- Volatility floor fraction: 0.25.
- No signal smoothing, no VIX regime scaling, and no minimum trade interval in the published H10 selection.

The exit state machine also contains a trailing stop, a time stop when a trade has not made positive progress, volatility-based exposure reduction, and exits when the target becomes zero. Exact semantics should be read from the runner and tests before any new implementation; do not assume that a prose description alone reproduces the code.

## 2. Markets, data and costs

### H10 single-family experiment

The H10 runner uses hourly futures data over **2024-10-12 through 2026-10-11**, with VIX as an optional regime input. The split is 55% train, 25% validation and 20% test. The selection rule says validation selects the configuration and test is protected from selection, with gates evaluated over validation plus test.

### H22 multi-contract extension

H22 extends the selected signal/exit configuration to five liquid futures proxies:

- ES=F — equity-index futures proxy
- NQ=F — Nasdaq-index futures proxy
- CL=F — crude-oil futures proxy
- GC=F — gold futures proxy
- ZB=F — Treasury-bond futures proxy

H22 evaluated an eight-combination grid: target-volatility multipliers `{0.50, 0.75, 1.0, 1.5}` crossed with maximum portfolio-position caps `{0.5, 1.0}`. The selected published configuration used target-volatility multiplier 1.0, maximum position 0.5, equal aggregation, and five assets. The signal/exit parameters were frozen from H10 rather than re-optimized.

The runner specifies futures costs of **$0.50 commission per contract, 0.25 tick spread and 0.5 tick slippage**. These are modeled assumptions, not proof that realized execution costs would match. Data and instrument construction, missing-bar treatment, continuous-contract roll behavior and point-in-time availability should be checked in any fresh study.

## 3. What the original results said

The original committed summaries reported:

| Metric | H10 published run | H22 published run |
|---|---:|---:|
| OOS Sharpe | 1.276 | 1.372 |
| Profit factor | 1.304 | 1.334 |
| Maximum drawdown | −5.8% | −11.9% |
| Trades | 2,416 | 3,045 |
| Worst regime Sharpe | 1.046 | 1.129 |
| Published verdict | PASS | PASS |

Sources: [H10 summary](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/.experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/summary.json) and [H22 summary](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/.experiments/artifacts/exp_2026-10-14T18-52-08-943792Z/summary.json).

Those were the originally reported outcomes under gates including OOS Sharpe ≥ 1.0, at least 200 trades, profit factor ≥ 1.3, maximum drawdown no worse than 15%, walk-forward stability ≥ 0.7, worst-regime Sharpe ≥ 0.3, benchmark p-value ≤ 0.05, non-negative information ratio, and a perturbation robustness gate where applicable. **Passing those gates did not detect the timing flaw.**

## 4. Why the result was rejected

### H29: direct look-ahead evidence

The committed [H29 look-ahead sweep](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/.experiments/artifacts/h29_lookahead_sweep/summary.json) reports for H10 and H22:

- Published verdict: `LOOKAHEAD`.
- Minimum hold lag: **−22 hourly bars**.
- Look-ahead bar fraction: approximately **94.7%**.
- The daily signal matched the same-period collapsed signal rather than the prior day's signal.
- A causal negative control shifted the daily target by one calendar day and was classified as causal.

In plain language, the backtest could use information from later in a trading day to set a position on earlier bars of that same day. That violates the requirement that every decision use only information actually available at the decision time. Strong metrics from this construction cannot establish a tradable edge.

### H28: causal re-certification

The committed [H28 re-certification summary](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/.experiments/artifacts/h28_causal_recertification/summary.json) states:

- Family verdict: `CAUSAL_REJECTED`.
- Causal-certified members: none.
- Published artifacts and runners were not rewritten.
- The causal H10 run reported OOS Sharpe **0.391**, profit factor **1.087**, maximum drawdown **−10.1%**, and worst-regime Sharpe **−0.369**. It failed the Sharpe, profit-factor, worst-regime, benchmark-significance and information-ratio gates.
- The causal H22 run reported OOS Sharpe **0.360**, profit factor **1.077**, maximum drawdown **−22.8%**, and worst-regime Sharpe **−0.498**. It failed the Sharpe, profit-factor, drawdown, worst-regime and benchmark-significance gates.

Sources: [H10 causal run](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/.experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T16-41-44-683912Z/summary.json) and [H22 causal run](https://github.com/takenthatusernameis-collab/Quantitative-Trading-Mathematics-Prompted/blob/main/.experiments/artifacts/h28_causal_recertification/runs/exp_2026-10-19T17-38-50-887609Z/summary.json).

The causal results are materially weaker and do not pass the repository's stated promotion criteria. Do not interpret the positive residual Sharpe as evidence of a validated strategy.

## 5. Main limitations and open questions

1. **Signal availability must be repaired first.** Every feature, resample, label and target must be tested against its actual timestamp. A signal for a completed daily bar cannot be used on earlier hourly bars in that day.
2. **The history is short for robust futures claims.** The cited hourly window spans roughly two years, which limits evidence across full market cycles and structural changes.
3. **Instrument/data construction matters.** Validate futures roll adjustments, session calendars, missing observations, timestamps/time zones, and whether the chosen Yahoo Finance futures series is suitable for return calculations.
4. **Execution realism is uncertain.** Stress spreads, slippage, commissions and turnover; costs can vary by contract, session and market regime.
5. **Portfolio aggregation needs scrutiny.** H22's equal aggregation and gross exposure cap should be checked for overlapping risk, contract multipliers and unintended concentration.
6. **The historical parameter search raises selection risk.** H10 evaluated 13,824 configurations. The original validation/test protocol is documented, but the look-ahead defect invalidates the original performance interpretation; a corrected study needs a fresh protected evaluation and explicit accounting for all research attempts.
7. **Implementation semantics should be reconciled.** Before any new experiment, inspect the signal's signed weights against the backtest configuration's short-selling policy, as well as contract sizing and return accounting. Do not infer behavior from a strategy name alone.

## 6. Recommended research disposition

**Current status: rejected for performance claims; preserve as an audited negative result.**

No live deployment or promotion is justified by the existing evidence. If the research is reopened, use a separate, clearly named causal experiment that:

1. Pre-registers the hypothesis, features, universe, cost model, split and gates before running.
2. Uses only lagged, timestamp-valid inputs; includes automated future-perturbation and timestamp/label-position tests.
3. Recomputes targets and positions from scratch rather than editing historical result files.
4. Uses a sufficiently long, reproducible free-data history, documents contract rolls and data gaps, and stress-tests costs.
5. Selects only on training/validation data, evaluates once on a protected test, and records every attempted variant.
6. Compares against simple causal baselines and reports net returns, Sharpe uncertainty, profit factor, drawdown, turnover, trade count, regime results and portfolio exposure.
7. Promotes the strategy only if it passes all frozen gates on the causal implementation and survives independent review.

This is a documentation summary, not authorization to start another backtest or alter the frozen hypothesis family. The repository's current handoff says no hypothesis work is assigned and that published gates, verdicts and certified numbers must remain unchanged.
