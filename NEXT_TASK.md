# NEXT_TASK.md — Cycle 91 (after H176 REJECT 3/8)

## Status: Cycle 90 complete (H176 executed REAL; REJECT) — Cycle 91 discovery pending

## H176 result (REAL, not fabricated) — REJECT 3/8
- Runner `run_nf_20261109_15_tax_loss_harvesting.py` + tests `tests/test_nf_20261109_15_tax_loss_harvesting.py` (**13 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261109_15_tax_loss_harvesting_20261110_025220/summary.json` (+`grid.csv`, ~8s).
- Data (PIT, free yfinance): 11 liquid sector ETFs + SPY daily 2010-01-04→2026-10-30 (2104 aligned rows). Train 50% (~2010→2022-08-23), Val 25% (→2024-09-26), Test protected final 25% (~2024→2026). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Construction (daily, causal, 36-combo grid): `n_days {5,10} × k {1,3,5} × hold_days {3,5,10} × vol_target {0.10,0.15}`; at each November close, rank universe by YTD return (ascending = biggest losers); during last `n_days` of December, long bottom `k` losers equal-weight; hold `hold_days` into January; vol-target off trailing 21-day basket realized vol; long-only MAX_POS=0.5; Equity CostModel defaults (1bp commission+1bp spread); 1-bar delay via engine `signals.shift(1)`.
- Selected (train-only 4-fold WF Sharpe 1.212): `n_days=5, k=1, hold_days=3, vol_target=0.15`.
- OOS Val+Test (1052 periods, 8 trades): Sharpe **0.628** fail (≥1.0), PF **1.951** pass (≥1.3), max DD **−1.18%** pass (≤15%), trades **8** fail (≥50), WF stability **0.540** fail (≥0.7), worst-regime rolling-252 Sharpe **−1.443** fail (≥0.3), benchmark p **0.977** / IR **−0.975** vs buy-hold SPY 1.073 (fail), perturbation min ratio **0.858** pass (≥0.5). → **REJECT 3/8**.
- Ablations OOS: buy-hold SPY 1.073/1.214/+41.1%; equal-weight universe 1.054/1.209/+75.8%; random-year control 0.098/1.101/58 trades (weaker, signal not noise); inverse-signal (long YTD winners) **−0.365**/0.679/8 trades — directionally consistent (losers outperform winners) but magnitude insufficient.
- **Integrity (honest):** `ruff check/format` clean; focused pytest 13 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.
- Documented in `HYPOTHESIS_SPEC.md` §H176 and `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 90 execution).

## Lineage
**Lineage:** H85–H176 all rejected/recorded. Next unused H-ID: **H177** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public data only. No commit/push unless explicitly authorized.

## Cycle 91 Discovery Pending

Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions:** H85–H176 rejected/recorded, H177 next unused. No tracked draft collides with H177. NF-label reuse avoided.
2. **Directive §4 discovery scan:** Propose repo-new candidates across broad mechanism categories with honest scoring and concrete deferred reassessment.
3. **Reassess carried-forward/deferred pool with evidence:** NF-20261109-16 dividend capture (4.05), NF-20261109-18 S&P 500 inclusion (3.70), NF-20261109-19 options GEX (3.10), NF-20261109-02 earnings revision (3.10), NF-20261109-22 RSP-SPY relmom (3.75), NF-20261109-23 USMV-SPY low-vol relmom (3.55), NF-20261109-12 holiday drift (held), NF-04 blocked, NF-05 deferred, NF-08-16 held, NF-09-03 data-limited — reassess with updated evidence.
4. **Verify NF roots** against executed H-IDs/artifacts/runners.
5. **Pre-register highest-expected-information feasible candidate as H177.**
6. **Next steps (this cycle):**
    - Implement runner + focused tests for selected H177 candidate
    - Run `python -m ruff check/format --check` and `PYTHONPATH=src python -m pytest -q` focused tests (all pass)
    - Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H177, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 91, `NEXT_TASK.md`, `HANDOFF_NEXT.md`
    - **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H176: Tax-loss harvesting / year-end selling pressure (long YTD losers in Dec, hold into Jan) REJECT 3/8 (Sharpe 0.628, trades 8, WF stability 0.540, worst-regime −1.443, benchmark p 0.977/IR −0.975). Direction correct (inverse −0.365, random-year 0.098) but effect size too small; low frequency (8 trades/4yr OOS) limits power; train WF 1.212 → OOS 0.628 decay. Structural tax-flow edge does not clear gates on free daily data.
- H175: Cross-asset macro regime timing (z(HG=F/GC=F) − z(TIP/IEF) → SPY) failed 7/8 gates (Sharpe −0.005, PF 0.998, trades 123, WF −0.004, worst-regime −1.31, benchmark p 0.996/IR −0.931, perturbation −32.37); only maxDD passes; inverse-regime falsifier outperforms (1.009 vs −0.005); train WF 1.288 → OOS −0.005 decay. Composite macro regime has no OOS edge on free daily data after costs.
- H174: ETF premium/discount mean reversion (NAV approximated) failed 6/8 gates (Sharpe 0.074, PF 1.019, DD −18.95%, worst-regime −1.753, benchmark p 0.982/IR −0.721, perturbation 0.0); random-premium ablation outperforms signal; NAV approximation invalidates mechanism test — **without point-in-time NAV, creation/redemption arbitrage cannot be fairly tested**.
- H173: Fed model / ERP timing (div yield − 10Y yield) failed 7/8 gates (Sharpe 0.310, PF 1.170, DD −16.89%, trades 114, WF 0.264, worst-regime −1.326, benchmark p 0.991/IR −0.813); inverse-signal outperformed (0.739); train WF 1.363 → OOS 0.310 decay.
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; train WF negative; limited ~2y 1h history (yfinance 730-bar constraint). Do not rerun same hour-window construction without materially different mechanism/data.
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: Leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: Overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: Quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H176 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.