# HANDOFF_NEXT.md — Cycle 86 (after H171 REJECT 4/8)

## Session summary
- **Cycle 85 complete.** Executed H171 (NF-20261109-21: Yield curve slope regime SPY timing, ^TYX-^FVX 30Y-5Y) as a real, honest test.
- **Result:** REJECT 4/8 gates. OOS Sharpe 0.903 (fail), PF 1.224 (fail), max DD -5.75% (pass), trades 740 (pass), WF stability 1.153 (pass), worst-regime rolling-252 Sharpe -1.006 (fail), benchmark p=0.971/IR=-0.725 (fail), perturbation min ratio 1.286 (pass).
- **Mechanism falsified (this construction):** Trailing yield-curve slope (30Y-5Y yield-index shape) does not provide a benchmark-significant SPY timing edge after costs under the pre-registered de-risk-on-flattening construction. Random exposure weaker (some structure) and inverse much weaker (direction supported), but no validated edge.
- **Artifacts:** `.experiments/nf_runs/nf_20261109_21_yield_curve_slope_spy_20261109_155438/summary.json`, `grid.csv`, `data_meta.json` (5.23s). Data: ^TYX/^FVX/SPY yfinance daily auto-adjust, 4231 aligned rows 2010-01-04→2026-10-30.
- **Files added (uncommitted):** `run_nf_20261109_21_yield_curve_slope_spy.py`, `tests/test_nf_20261109_21_yield_curve_slope_spy.py`. Focused tests **9 passed**. `ruff check/format` clean on new files.
- **Documentation updated:** `HYPOTHESIS_SPEC.md` §H171 (pre-registration + execution + lineage), `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 85, `NEXT_TASK.md`, this handoff.

## Lineage state
- H85–H171 all rejected/recorded. Next unused H-ID: **H172** (H24/H68–H73/H76–H79 unassigned, not recycled).
- `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified.
- Selection/validation uses no protected-test feedback. Free/public yfinance data only.
- **No commit/push performed** (not authorized).

## Deferred pool (no silent drops; reassess with concrete evidence)
| Candidate | Score | Category | Status | Evidence / blocker |
|---|---:|---|---|---|
| NF-20261109-15 Tax-loss harvesting / year-end selling | 4.20 (reassessed) | Institutional/behavioral constraint | Deferred | Decisive test needs survivorship-managed constituent/YTD-loser universe; sector-ETF proxy weakens mechanism |
| NF-20261109-16 Dividend capture / ex-dividend microstructure | 3.95 | Corporate action / microstructure | Deferred | Event alignment, overnight/open costs, tax-clientele/microstructure fragility |
| NF-20261109-12 Holiday / pre-holiday drift SPY timing | 4.00 | Calendar microstructure | Deferred | Adjacency to H91/H140/H142/H168 calendar families |
| NF-20261109-22 RSP-vs-SPY breadth-participation relmom SPY timing | 3.75 | Cross-asset participation / factor momentum | Deferred | Adjacency to H97 (same pair, different mechanism: relmom de-risking vs concentration mean reversion) — must justify if selected |
| NF-20261109-23 USMV-vs-SPY low-vol factor relmom SPY timing | 3.55 | Factor anomaly / style momentum | Deferred | USMV inception 2011 (shorter OOS power), style adjacency |
| NF-20261109-18 S&P 500 inclusion/deletion discrete event | 3.90 | Structural flow / discrete event | Deferred | Low frequency, external index-change data dependency |
| NF-20261109-19 Options dealer gamma exposure SPY timing | 3.50 | Market structure / dealer positioning | Deferred | Options chain/GEX construction complexity; free data history limits |
| NF-20261109-20 Stock split announcement effects | 3.10 | Corporate action / behavioral | Deferred | Low frequency |
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 weekly REJECT 3/8 |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142 |
| NF-09-03 Breakeven-inflation | 3.40 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable on yfinance (probe 2026-11-09) |

## Required next work (Cycle 86 / H172)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4` and `NEXT_TASK.md`:
1. Reconcile lineage to H171 (done) and confirm H172 next unused.
2. **Directive §4 discovery scan:** Propose **≥3 repo-new candidates across ≥3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring. **Search materially different mechanism categories before recycling.** Treat heavily executed categories (calendar, rates/credit regime/shape, correlation, RV-stress/realized-moment, dispersion, FX, VIX-complex/VRP, carry, overnight lead-lag, leveraged ETF flows, relmom, cross-sectional breadth/beta/IVOL) with high adjacency scrutiny and explicit novelty justification.
3. Verify NF roots against executed H-IDs/artifacts in `.experiments/nf_runs/`, `HYPOTHESIS_SPEC.md`, and `NEW_FAMILY_RESEARCH_REGISTER.md` — no collisions.
4. Pre-register H172 before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. Implement runner + focused tests; `ruff check/format` clean; focused `pytest` pass.
6. Execute REAL; record verdict in `HYPOTHESIS_SPEC.md` §H172, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 86, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Integrity constraints (do not violate)
- **No gate weakening.** All gates fail-closed on pre-registered OOS Val+Test.
- **No published/certified artifact modification.** Historical rows in `HYPOTHESIS_SPEC.md`, `INEFFICIENCY_RANKING.md`, `FINAL_REPORT.md` are frozen.
- **No silent drops.** Every deferred candidate reassessed with concrete evidence each cycle.
- **No fabrication.** Real execution only; report failures honestly.
- **Free data only.** yfinance/public sources only.
- **`src/qtr` unchanged** unless evidenced defect (then rerun pinned 100% coverage suite).
- **No commit/push** unless explicitly authorized.

## Approaches that failed / evidence (do not blindly repeat)
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark; inverse weaker (direction supported) but no edge. Do not rerun same construction.
- H170: leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation; random flow comparable.
- H169: overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: quarterly index-rebalance window de-risking failed; random-window control matched base.
- H141/H154/H155/H171: rates level/spread/slope constructions repeatedly fail benchmark/worst-regime under current gates — any new rates candidate must be *materially* different with explicit falsifier/gate plan.
- All H85–H171 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes.
