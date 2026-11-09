# HANDOFF_NEXT.md — Cycle 85 (after H170 REJECT 3/8)

## Session summary
- **Cycle 84 complete.** Executed H170 (NF-20261109-17: Leveraged ETF Daily Rebalancing Flows) as a real, honest test.
- **Result:** REJECT 3/8 gates. OOS Sharpe 0.201 (fail), PF 1.034 (fail), max DD −1.07% (pass), trades 1717 (pass), WF stability 2.167 (pass), worst-regime rolling-252 Sharpe −1.354 (fail), benchmark p=0.972/IR=−0.713 (fail), perturbation min ratio −0.102 (fail).
- **Mechanism falsified:** Net leveraged ETF rebalancing flow (pro-cyclical daily derivative hedging by issuers) does not predict next-day SPY returns after costs. Inverse signal weaker (direction consistent) but no edge; random flow control comparable; equal-weight basket similar to AUM-weighted — the flow signal adds no information.
- **Artifacts:** `.experiments/nf_runs/nf_20261109_17_leveraged_etf_rebalancing/summary.json`, `grid.csv`, `data_meta.json`.
- **Tests:** `tests/test_nf_20261109_17_leveraged_etf_rebalancing.py` (19 passed). Lint/format clean.
- **Documentation updated:** `HYPOTHESIS_SPEC.md` §H170 (pre-registration + execution), `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 84, `NEXT_TASK.md` (Cycle 85).

## Lineage state
- H85–H170 all rejected/recorded. Next unused H-ID: **H171** (H24/H68–H73/H76–H79 unassigned, not recycled).
- `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified.
- Selection/validation uses no protected-test feedback. Free/public yfinance data only.
- No commit/push unless explicitly authorized.

## Deferred pool (no silent drops; reassess with concrete evidence)
| Candidate | Score | Category | Status | Blocker |
|---|---:|---|---|---|
| NF-20261109-15 Tax-loss harvesting / year-end selling | 4.35 | Institutional/behavioral constraint | Deferred | — |
| NF-20261109-16 Dividend capture / ex-dividend microstructure | 4.20 | Corporate action | Deferred | Execution score 3 (overnight hold tax, bid-ask at open) |
| NF-20261109-12 Holiday / pre-holiday drift SPY timing | 4.15 | Calendar microstructure | Deferred | Adjacency to H91/H140/H142/H168 calendar families |
| NF-20261109-13 Low-volatility factor timing USMV/SPLV vs SPY | 3.45 | Factor anomaly | Deferred | USMV/SPLV start 2011 (shorter history), style adjacency |
| NF-20261109-18 S&P 500 index inclusion/deletion discrete event | 3.95 | Structural flow / discrete event | Deferred | Low frequency (~20-40 events/year); external index-change data |
| NF-20261109-19 Options dealer gamma exposure SPY timing | 3.60 | Market structure / dealer positioning | Deferred | Options data complexity; limited deep-OTM history |
| NF-20261109-20 Stock split announcement effects SPY timing | 3.15 | Corporate action / behavioral | Deferred | Low frequency; adjacency to NF-16 |
| NF-04 Commodity carry | — | Carry / term structure | **BLOCKED** | No free PIT term-structure/roll proxy |
| NF-05 Short-term CS reversal | — | Liquidity provision | **DEFERRED** | Turnover/net-of-cost; H119 weekly REJECT 3/8 |
| NF-08-16 Halloween seasonal | 3.90 | Calendar seasonal | **HELD** | Calendar adjacency H91/H140/H142; declined 7x |
| NF-09-03 Breakeven-inflation | 3.50 | Macro regime | **DEFERRED/DATA-LIMITED** | ^T5YIE/^T10YIE unavailable on yfinance |

## Required next work (Cycle 85 / H171)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4` and `NEXT_TASK.md`:

1. **Reconcile lineage** to H170 (done above).
2. **Directive §4 discovery scan:** Propose **≥3 repo-new candidates across ≥3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring. Must search **materially different mechanism categories** before recycling deferred pool. Categories already heavily executed: calendar/seasonal (H91, H140, H142, H168, NF-12), credit/macro regime (H94, H95, H146, H155, H163), correlation/regime (H96, H127, H134, H137, H165), RV-stress (H151, H156, H164), dispersion (H118, H160, H162), FX (H95, H103, H106, H161), VIX-complex (H158, H159, H167), VRP (H17, H100, H167), carry (H161), overnight futures lead-lag (H169), leveraged ETF flows (H170). **Look elsewhere.**
3. **Verify NF roots** against executed H-IDs/artifacts in `.experiments/nf_runs/`, `HYPOTHESIS_SPEC.md`, and `NEW_FAMILY_RESEARCH_REGISTER.md` — no collisions.
4. **Pre-register H171** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. **Implement runner** `run_nf_...py` + focused tests `tests/test_nf_...py`; `ruff check/format` clean; focused `pytest` pass.
6. **Execute REAL**; record verdict in `HYPOTHESIS_SPEC.md` §H171, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 85, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Integrity constraints (do not violate)
- **No gate weakening.** All gates fail-closed on pre-registered OOS Val+Test.
- **No published/certified artifact modification.** Historical rows in `HYPOTHESIS_SPEC.md`, `INEFFICIENCY_RANKING.md`, `FINAL_REPORT.md` are frozen.
- **No silent drops.** Every deferred candidate must be reassessed with concrete evidence each cycle.
- **No fabrication.** Results must come from real execution; if experiment fails to run, report the failure honestly.
- **Free data only.** yfinance/public sources only; no paid data/subscriptions.
- **src/qtr unchanged** unless evidenced defect (then rerun pinned 100% coverage suite).
- **No commit/push** unless explicitly authorized.

## Suggested fresh mechanism categories to explore (not exhaustive)
- **Insider trading / Form 4 signals** (information transmission) — if free SEC data accessible via yfinance or SEC API.
- **Short interest / days-to-cover dynamics** (supply/flow constraints) — if free short interest data available.
- **Securities lending market signals** (supply/flow) — proxy via borrow rates or utilization (may need paid data).
- **Earnings announcement drift (PEAD)** — already tested as H98 (REJECT 5/9) but with limited free earnings history; could revisit with improved data.
- **Analyst revision momentum** (information transmission) — if free estimate data available.
- **Index reconstitution / Russell rebalancing** (structural flow) — distinct from S&P 500 quarterly rebalance (H168) and inclusion/deletion (NF-18).
- **Merger arbitrage / deal spreads** (event/auction) — if free deal announcement data available.
- **Convertible bond arbitrage signals** (relative value) — if free convertible data available.
- **ETF creation/redemption flow signals** (supply/flow) — using shares outstanding changes as proxy for AP activity.
- **Options put/call ratio or skew term structure** (volatility/convexity) — distinct from VIX level/slope (H86) and SKEW (H89).
- **Market breadth / advance-decline / new highs-new lows** (participation) — distinct from sector breadth (H129).
- **Corporate buyback execution patterns** (supply/flow) — if free buyback announcement + execution data available.
- **Fed policy / monetary regime timing** (macro regime) — using ^TNX/^TYX/^IRX yield levels/curve (distinct from VIX regime H3/H5/H6).
- **Commodity currency / FX carry** (carry) — AUD/USD, CAD/USD, NOK/USD via yfinance FX pairs.
- **Volatility risk premium term structure across tenors** (vol/convexity) — distinct from VIX/VIX3M slope (H86).

## Experiment runner checklist (for H171)
- [ ] `run_nf_YYYYMMDD_XX_descriptive.py` with full pre-registration docstring
- [ ] `tests/test_nf_YYYYMMDD_XX_descriptive.py` with ≥10 focused tests
- [ ] `ruff check/format` clean on both files
- [ ] `PYTHONPATH=src python -m pytest tests/test_nf_...py -q` all pass
- [ ] `PYTHONPATH=src python run_nf_...py` executes and produces `.experiments/nf_runs/nf_YYYYMMDD_XX_*/summary.json`
- [ ] Verdict recorded in `HYPOTHESIS_SPEC.md` §H171, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 85, `NEXT_TASK.md`, `HANDOFF_NEXT.md`

## Contacts / references
- Directive: `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md`
- Lineage: `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 84 ends at H170)
- Hypotheses: `HYPOTHESIS_SPEC.md` (ends at H170 execution)
- Next task: `NEXT_TASK.md` (Cycle 85)
- All experiment artifacts in `.experiments/nf_runs/`