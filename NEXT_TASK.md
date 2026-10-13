# Next Task — H15 (regime-aware exit redesign) is DATA-WALLED; pivot to new hypothesis family

## Status of completed work
- **H10–H12**: certified chain (Sharpe-robust, selection-bias-corrected). All gates PASS.
- **H13**: REJECT on PF-fragility axes — OOS Sharpe deflation-robust (worst-case DSR-adj 1.2745, p = 0.00102) but PF margin statistically fragile (bootstrap 95% CI [1.190, 1.425], P(PF ≥ 1.3) = 51.7%) and single-symbol-dependent (CL=F, GC=F indispensable: leave-one-out PF 1.249 / 1.282).
- **H14**: REJECT — PF-margin fragility is a family property (0/50 top-by-Val-PF-margin configs clear all gates; CI-LB max 1.199).
- **H15-prep (COMPLETED THIS SESSION)**: bar-level per-symbol OOS contribution decomposition on frozen H10 artifacts.
  - Artifacts produced: `.experiments/probes/h15_loss_offset_decomposition.parquet`, `.experiments/probes/h15_loss_offset_decomposition.md`, `.experiments/probes/h15_loss_offset_decomposition_report.json`
  - Tests added: `tests/test_h15_loss_offset_decomposition.py` (5 tests)
  - Key findings (from report):
    - Pooled OOS PF (bar-level Σup/Σdn): 1.3378
    - Leave-one-out PF: no_CL_F=1.273, no_GC_F=1.310, no_ES_F=1.349, no_NQ_F=1.334, no_ZB_F=1.344
    - CL/GC loss-bar overlap (both loss | either loss): 0.153
    - CL/GC contribution correlation OOS: 0.057
    - CL/GC indispensable flag: True (both LOO PF < 1.3)
  - All 154 tests pass (149 prior + 5 new).

## What remains unresolved (the H10–H14 line is data-walled)
- **Data horizon**: free `yfinance` hourly `=F` hard-capped at ~730 days (no bars past 2026-10-09). Hard stop for extending the *futures TSMOM* line; paid data (CQG/Rithmic/IQFeed/Databento/Polygon) required.
- **PF-margin fragility is structural**, not selection-mined: H14 showed 0/50 even when selecting on Val PF margin. The margin (+0.004 over 1.3) is thinner than bootstrap noise (CI half-width ±0.117) and carried by commodity loss-offsetting (CL=F net PF 1.358 is the only symbol above pooled PF, yet its removal collapses pooled PF to 1.249).
- **H15 regime-aware exit redesign** (the only un-tried signal-redesign lever) **requires paid/longer data** and is explicitly out of scope until then. The H15-prep diagnostic confirmed the loss-offset mechanism but cannot redesign exits without a longer OOS window to validate.

## Approaches already failed and why
- PF-margin-targeted selection over top-K by Val PF margin (H14): all 50 fail OOS PF bootstrap CI-LB gate (max 1.199); fragility is family-level.
- Extended-data feasibility probe: needs ~5× OOS bars (~25k) to plausibly move CI-LB ≥ 1.3 *if* point estimate holds; not available; CL/GC indispensability is structural, not N-limited.
- Regime-aware **vol** scaling (frozen H10 ablation): lowers PF (1.304→1.249), Sharpe (1.276→1.021).
- H1–H9 momentum family on free daily/intraday data: all rejected (Sharpe < 1.0, PF < 1.3, DD > 15%, or regime failure).

## One precise next task (bounded, verifiable, no network, no paid data)
**Pivot to a new hypothesis family outside the momentum line.** The free-data TSMOM family (H1–H14) is exhausted — certified but PF-fragile on a 730-day hourly window, with no path to resolution without paid data. The next agent should:

1. **Select a new market/strategy family** from `INEFFICIENCY_RANKING.md` that is feasible on free data (daily ETFs, equities, crypto, or futures with different edge).
2. **Pre-register a falsifiable hypothesis** (H16) with explicit mechanism, null, data splits, gates, and compute budget.
3. **Implement the minimal experiment** reusing existing infrastructure (`src/qtr/backtest/engine`, `src/qtr/data/fetcher`, `src/qtr/tracking/experiment`, `src/qtr/strategies/baselines`, `src/qtr/validation/statistics`).
4. **Run gates rigorously** — no weakening. Preserve all artifacts and add regression tests.

### Candidate families (from INEFFICIENCY_RANKING.md, ranked by net opportunity on free data)
| Rank | Family | Edge hypothesis | Data feasibility | Why now |
|------|--------|-----------------|------------------|---------|
| 1 | **Cross-sectional equity factor timing** (value/momentum/quality rotation) | Regime-dependent factor persistence | Daily ETFs, 20+ years free | Momentum exhausted; factor timing untested |
| 2 | **Crypto basis / funding-rate carry** | Perpetual funding rate ≠ spot carry | Hourly crypto free (Binance/CCXT) | New asset class, different microstructure |
| 3 | **Intraday equity mean-reversion** (overnight vs day session) | Overnight drift / day-session reversal | Hourly SPY/QQQ free (yfinance) | Different regime than trend-following |
| 4 | **Volatility risk premium (VRP) harvesting** | VIX term structure / VXX contango decay | Daily VIX + VXX free | Directly addresses momentum crash regime |

### Constraints
- No paid data, no network for new data acquisition (use `yfinance` / free sources only).
- Reuse existing backtest engine, cost model, experiment tracker — do not rebuild.
- Pre-register *before* running (append to `HYPOTHESIS_SPEC.md`).
- Compute budget ≤ 2 CPU-h per hypothesis.
- All gates from `PROMPT_V2.md` + `HYPOTHESIS_SPEC.md` apply (Sharpe ≥ 1.0, PF ≥ 1.3, DD ≤ 15%, trades ≥ 200, WF stability ≥ 0.7, ±20% perturbation, worst-regime Sharpe ≥ 0.3, benchmark p < 0.05 & IR > 0).
- Add `tests/test_h16_*.py` for artifact pinning and invariants.

## Evidence / constraints
- All H10–H14 frozen artifacts in `.experiments/artifacts/exp_2026-10-11T17-41-18-169363Z/` and `exp_2026-10-13T19-01-59-371405Z/`.
- H15-prep probe artifacts in `.experiments/probes/h15_loss_offset_decomposition.*`.
- `INEFFICIENCY_RANKING.md` has 6-factor rankings with measured net edge (post-cost-fix).
- `MATHEMATICAL_DISCOVERY_REPORT.md` has literature traceability chains.
- Repository is clean: `git status` shows only `.pyc` cache churn (ignored).

## Handoff
**Completed:** H15-prep diagnostic (bar-level CL/GC loss-offset decomposition). All tests pass. No further work possible on H10–H15 line without paid data.
**Next agent:** Pick a new hypothesis family from the candidates above (or another justified by `INEFFICIENCY_RANKING.md`), pre-register as H16, implement minimal experiment, run gates, report verdict. Do not attempt to extend H10–H15 without paid data — it is a hard wall.