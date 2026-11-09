# NEXT_TASK.md — Cycle 89 (after H174 REJECT 2/8)

## Status: Cycle 88 complete (H174 executed REAL; REJECT) — Cycle 89 discovery pending

## H174 result (REAL, not fabricated) — REJECT 2/8
- Runner `run_nf_20261109_26_etf_nav_arbitrage.py` + tests `tests/test_nf_20261109_26_etf_nav_arbitrage.py` (**13 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261109_26_etf_nav_arbitrage_20261109_234241/summary.json` (+`grid.csv`, 68.0s).
- Data (PIT, free yfinance): SPY daily 2010-01-04→2026-10-30 (4233 rows). NAV: approximated via mean-reverting premium/discount process (free public NAV endpoints unavailable; documented limitation). Train 2010-01-04→2018-05-31 (2116), Val →2022-08-12 (1058), Test protected →2026-10-30 (1059). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Construction (daily, causal, 108-combo grid): `z_window ∈ {21,63,126}` × `entry_z ∈ {1.0,1.5,2.0}` × `exit_z ∈ {0.0,0.5}` × `vol_target ∈ {0.10,0.15}` × `universe ∈ {{SPY},{SPY,QQQ,IWM},{SPY,QQQ,IWM,EFA,EEM}}`; vol targeting `vol_target/sqrt(252)`; clipped [0,0.5]; 1-bar delay; Equity CostModel defaults (1bp commission+1bp spread), long/short.
- Selected (train-only WF mean Sharpe 0.027; train ref 0.100): `z_window=21, entry_z=1.5, exit_z=0.5, vol_target=0.10, universe={SPY}`.
- OOS Val+Test (2117 periods, 484 trades): Sharpe **0.074** fail (≥1.0), PF **1.019** fail (≥1.3), max DD **−18.95%** fail (≤15%), trades **484** pass (≥200), WF stability **0.740** pass (≥0.7), worst-regime rolling-252 Sharpe **−1.753** fail (≥0.3), benchmark p **0.982** / IR **−0.721** vs buy-hold SPY 0.819 (fail), perturbation min ratio **0.000** fail (≥0.5). → **REJECT 2/8**.
- Ablations OOS: buy-hold SPY 0.819/1.170/-17.97%/1; random-premium 0.282/1.073/-7.75%/1213 (outperforms strategy); inverse-signal −0.182/0.954/-15.69%/484 (directionally consistent but no edge).
- **Integrity (honest):** `ruff check/format` clean; focused pytest 13 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.
- Documented in `HYPOTHESIS_SPEC.md` §H174 and `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 88 execution).

## Lineage
**Lineage:** H85–H174 all rejected/recorded. Next unused H-ID: **H175** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public data only. No commit/push unless explicitly authorized.

## Cycle 89 Discovery Pending

Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions:** H85–H174 rejected/recorded, H175 next unused. No tracked draft collides with H175. NF-label reuse avoided.
2. **Directive §4 discovery scan:** Propose repo-new candidates across broad mechanism categories with honest scoring and concrete deferred reassessment.
3. **Reassess carried-forward/deferred pool with evidence:** NF-20261109-15 tax-loss harvesting (4.20), NF-20261109-16 dividend capture (3.95), NF-20261109-12 holiday drift (4.00), NF-20261109-22 RSP-SPY breadth relmom (3.75), NF-20261109-23 USMV-SPY low-vol relmom (3.55), NF-20261109-03 cross-asset macro regime (3.85), NF-20261109-02 earnings revision (3.65), NF-20261109-18/19/20 deferred, NF-04 blocked, NF-05 deferred, NF-08-16 held, NF-09-03 data-limited — reassess with updated evidence.
4. **Verify NF roots** against executed H-IDs/artifacts/runners.
5. **Pre-register highest-expected-information feasible candidate as H175.**
6. **Next steps (this cycle):**
    - Implement runner + focused tests for selected H175 candidate
    - Run `python -m ruff check/format --check` and `PYTHONPATH=src python -m pytest -q` focused tests (all pass)
    - Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H175, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 89, `NEXT_TASK.md`, `HANDOFF_NEXT.md`
    - **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H174: ETF premium/discount mean reversion (NAV approximated) failed 6/8 gates (Sharpe 0.074, PF 1.019, DD −18.95%, worst-regime −1.753, benchmark p 0.982/IR −0.721, perturbation 0.0); random-premium ablation outperforms signal; NAV approximation invalidates mechanism test — **without point-in-time NAV, creation/redemption arbitrage cannot be fairly tested**.
- H173: Fed model / ERP timing (div yield − 10Y yield) failed 7/8 gates (Sharpe 0.310, PF 1.170, DD −16.89%, trades 114, WF 0.264, worst-regime −1.326, benchmark p 0.991/IR −0.813); inverse-signal outperformed (0.739); train WF 1.363 → OOS 0.310 decay.
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; limited ~2y 1h history (yfinance 730-bar constraint).
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: Leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: Overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: Quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H174 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.