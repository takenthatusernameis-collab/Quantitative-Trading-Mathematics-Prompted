# NEXT_TASK.md — Cycle 87 (after H172 REJECT 3/8)

## Status: Cycle 86 complete (H172 executed REAL; REJECT) — Cycle 87 discovery required

## H172 result (REAL, not fabricated) — REJECT 3/8
- Runner `run_nf_20261109_01_intraday_seasonality.py` + tests `tests/test_nf_20261109_01_intraday_seasonality.py` (**10 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261109_01_intraday_seasonality_20261109_213639/summary.json` (+`grid.csv`, 4.31s). No `data_meta.json` written by runner.
- NF-label collision disclosed: `NF-20261109-01` was H160’s execution key (IVOL dispersion); Cycle 86 reused label for intraday seasonality (H172). H-IDs/artifact paths distinct; no historical verdict altered.
- Data (PIT, free yfinance): SPY 1h auto-adjust, ET tz-naive; trading hours ET 9–15. 3313 bars 2024-12-02→2026-10-30 (yfinance ~730-day 1h limit). Train 2024-12-01→2025-11-12 (50%), Val →2026-05-08 (25%), Test protected →2026-10-31 (25%). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Construction (ET-native, 36-combo grid): hour windows `{9,10},{10,11},{9,10,11},{11,12},{12,13},{14}` × vol_target `{0.10,0.15,0.20}` × vol_window `{21,63}`; `Close/Open-1`; vol-target `vol_target/sqrt(252*6.5)`; clipped [0,0.5]; 1-bar delay; Equity CostModel defaults (1bp commission+1bp spread), long-only.
- Selected (train-only WF mean Sharpe -0.299; train ref -0.155): `hour_window=[10,11] ET, vol_target=0.15, vol_window=63`.
- OOS Val+Test (476 trades): Sharpe **-0.936** fail (≥1.0), PF **0.737** fail (≥1.3), max DD **-6.01%** pass (≤15%), trades **476** pass (≥200), WF stability **NaN** fail (≥0.7; train ref non-positive), worst-regime rolling-252 Sharpe **-2.650** fail (≥0.3), benchmark p **0.975** / IR **-1.938** vs buy-hold SPY 0.330 (fail), perturbation min ratio **0.886** pass (≥0.5). → **REJECT 3/8**.
- Ablations OOS: buy-hold SPY 0.330/1.068/-4.89%/1; random-hour (shuffled ET 9–15) -1.122/0.712/-8.04%/952; inverse-hour (unfavorable ET hours) 0.133/1.032/-4.39%/477 (weak, no edge).
- **Integrity (honest):** Tests/runner ablation hour universe aligned to ET-native encoding (9–15 ET) during verification (pre-execution test expected UTC 13–19). No gate/threshold/grid/construction weakened; spec clarified to ET. No published/certified artifact modified. `src/qtr` unchanged.
- Documented in `HYPOTHESIS_SPEC.md` §H172 and `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 86 execution).

## Lineage
**Lineage:** H85–H172 all rejected/recorded. Next unused H-ID: **H173** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public data only. No commit/push unless explicitly authorized.

## One precise next task (Cycle 87 / H173)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions first (evidence-based):** confirm H85–H172 rejected/recorded, H173 next unused. Confirm no tracked draft collides with H173. **Avoid NF-label reuse** (NF-20261109-01 collision noted).
2. **Directive §4 discovery scan:** propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). **Search materially different mechanism categories before recycling.** Treat heavily executed categories with high adjacency scrutiny: calendar/seasonal, credit/macro rates regime/shape, correlation/regime, RV-stress/realized-moment, dispersion, FX, VIX-complex/VRP/vol-shape, carry, overnight futures lead-lag, leveraged ETF flows, relmom, breadth/beta/IVOL cross-sectional, microstructure/intraday seasonality (H172).
3. **Reassess carried-forward/deferred pool with evidence (no silent drops):** NF-20261109-15 tax-loss harvesting (4.20; constituent/YTD-loser universe construction decisive risk on free yfinance), NF-20261109-16 dividend capture (3.95; microstructure/event alignment/overnight-open costs), NF-20261109-12 holiday drift (4.00; calendar adjacency H91/H140/H142/H168), NF-20261109-22 RSP-SPY breadth relmom (3.75; **adjacency to H97 same pair** — different mechanism must be explicit), NF-20261109-23 USMV-SPY low-vol relmom (3.55; 2011 inception/style adjacency), NF-20261109-18 S&P inclusion/deletion discrete (3.90; low frequency/external data), NF-20261109-19 options dealer GEX (3.50; options construction complexity), NF-20261109-20 stock split (3.10), NF-04 blocked (PIT term-structure/roll), NF-05 deferred (turnover/net-of-cost), NF-08-16 held (Halloween), NF-09-03 deferred/data-limited (breakeven). NF-20261109-02 earnings estimate revision (3.65; revision-history PIT construction risk) and NF-20261109-03 cross-asset macro growth/inflation proxies (3.85) remain unexecuted runner-ups from Cycle 86 — reassess with concrete evidence. Do not blindly select a runner-up.
4. **Verify NF roots** against executed H-IDs/artifacts/runners before selection (no collisions; H99/H149/H164-draft/NF-09-01 label reuse precedents).
5. **Pre-register** highest-expected-information **feasible** candidate as **H173** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
6. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
7. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H173, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 87, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; train WF negative; limited ~2y 1h history (yfinance 730-bar constraint). Do not rerun same hour-window construction without materially different mechanism/data.
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H172 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
