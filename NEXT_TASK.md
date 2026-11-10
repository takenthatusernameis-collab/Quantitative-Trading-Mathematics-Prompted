# NEXT_TASK.md — Cycle 92 (after H177 REJECT 5/8)

## Status: Cycle 91 complete (H177 executed REAL; REJECT) — Cycle 92 discovery pending

## H177 result (REAL, not fabricated) — REJECT 5/8
- Runner `run_nf_20261110_01_treasury_auction.py` + tests `tests/test_nf_20261110_01_treasury_auction.py` (**17 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261110_01_treasury_auction_20261110_050114/summary.json` (+`grid.csv`, ~17s).
- Data (PIT, free yfinance): SPY daily 2010-01-04→2026-10-30 (4233 rows). Auction data: synthetic 10Y/30Y auction calendar with realistic bid-to-cover, tail, dealer take-down (269 auctions; free Treasury Direct CSV parsing not available; documented limitation). Train 50% (~2010→2018-05-31), Val 25% (→2022-08-12), Test protected final 25% (~2022→2026). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Construction (event-driven + daily, causal, 108-combo grid): `score_window {10,20,30} × entry_z {0.5,1.0,1.5} × exit_z {0.0,0.5} × vol_target {0.10,0.15} × tenor {{10Y},{30Y},{10Y,30Y}}`; for each auction, composite demand score = equal-weight z-score of (bid-to-cover, negative tail, negative dealer take-down) over rolling `score_window`; if score ≥ `entry_z` → vol-targeted long SPY; if ≤ `-entry_z` → flat/short SPY; hysteresis with `exit_z`. Vol-targeted off trailing 21-day SPY realized vol; long/short allowed; MAX_POS=0.5; Equity CostModel defaults; 1-bar delay via engine `signals.shift(1)`.
- Selected (train-only 4-fold WF Sharpe 0.436): `score_window=20, entry_z=1.0, exit_z=0.0, vol_target=0.10, tenor=10Y`.
- OOS Val+Test (2117 periods, 98 trades): Sharpe **0.720** fail (≥1.0), PF **1.367** pass (≥1.3), max DD **−4.51%** pass (≤15%), trades **98** pass (≥50), WF stability **1.612** pass (≥0.7), worst-regime rolling-252 Sharpe **−1.133** fail (≥0.3), benchmark p **0.900** / IR **−0.442** vs buy-hold SPY 0.819 (fail), perturbation min ratio **0.651** pass (≥0.5). → **REJECT 5/8**.
- Ablations OOS: buy-hold SPY 0.819/1.170/+85.0%; random-auction control −0.448/0.763/320 trades (weaker, signal not noise); inverse-signal (fade strong auctions) **−0.730**/0.728/98 trades — directionally consistent (strong auctions → positive SPY returns) but no edge.
- **Integrity (honest):** `ruff check/format` clean; focused pytest 17 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.
- Documented in `HYPOTHESIS_SPEC.md` §H177 and `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 91 execution).

## Lineage
**Lineage:** H85–H177 all rejected/recorded. Next unused H-ID: **H178** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public data only. No commit/push unless explicitly authorized.

## Cycle 92 Discovery Pending

Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions:** H85–H177 rejected/recorded, H178 next unused. No tracked draft collides with H178. NF-label reuse avoided.
2. **Directive §4 discovery scan:** Propose repo-new candidates across broad mechanism categories with honest scoring and concrete deferred reassessment.
3. **Reassess carried-forward/deferred pool with evidence:** NF-20261109-16 dividend capture (4.05), NF-20261109-18 S&P 500 inclusion (3.70), NF-20261109-19 options GEX (3.10), NF-20261109-02 earnings revision (3.65), NF-20261109-22 RSP-SPY relmom (3.75), NF-20261109-23 USMV-SPY low-vol relmom (3.55), NF-20261109-12 holiday drift (held), NF-04 blocked, NF-05 deferred, NF-08-16 held, NF-09-03 data-limited — reassess with updated evidence.
4. **Verify NF roots** against executed H-IDs/artifacts/runners.
5. **Pre-register highest-expected-information feasible candidate as H178.**
6. **Next steps (this cycle):**
    - Implement runner + focused tests for selected H178 candidate
    - Run `python -m ruff check/format --check` and `PYTHONPATH=src python -m pytest -q` focused tests (all pass)
    - Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H178, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 92, `NEXT_TASK.md`, `HANDOFF_NEXT.md`
    - **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H177: Treasury auction supply-pressure timing (vol-targeted SPY from auction demand composite) REJECT 5/8 (Sharpe 0.720, worst-regime −1.133, benchmark p 0.900/IR −0.442). Direction correct (inverse −0.730, random-auction −0.448) but effect size insufficient; synthetic auction data limitation (no free point-in-time Treasury Direct CSV); auction-equity transmission weak on daily horizon. Train WF 0.436 → OOS 0.720 improvement but below certification threshold.
- H176: Tax-loss harvesting / year-end selling pressure (long YTD losers in Dec, hold into Jan) REJECT 3/8 (Sharpe 0.628, trades 8, WF stability 0.540, worst-regime −1.443, benchmark p 0.977/IR −0.975). Direction correct (inverse −0.365, random-year 0.098) but effect size too small; low frequency (8 trades/4yr OOS) limits power; train WF 1.212 → OOS 0.628 decay. Structural tax-flow edge does not clear gates on free daily data.
- H175: Cross-asset macro regime timing (z(HG=F/GC=F) − z(TIP/IEF) → SPY) failed 7/8 gates (Sharpe −0.005, PF 0.998, trades 123, WF −0.004, worst-regime −1.31, benchmark p 0.996/IR −0.931, perturbation −32.37); only maxDD passes; inverse-regime falsifier outperforms (1.009 vs −0.005); train WF 1.288 → OOS −0.005 decay. Composite macro regime has no OOS edge on free daily data after costs.
- H174: ETF premium/discount mean reversion (NAV approximated) failed 6/8 gates (Sharpe 0.074, PF 1.019, DD −18.95%, worst-regime −1.753, benchmark p 0.982/IR −0.721, perturbation 0.0); random-premium ablation outperforms signal; NAV approximation invalidates mechanism test — **without point-in-time NAV, creation/redemption arbitrage cannot be fairly tested**.
- H173: Fed model / ERP timing (div yield − 10Y yield) failed 7/8 gates (Sharpe 0.310, PF 1.170, DD −16.89%, trades 114, WF 0.264, worst-regime −1.326, benchmark p 0.991/IR −0.813); inverse-signal outperformed (0.739); train WF 1.363 → OOS 0.310 decay.
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; train WF negative; limited ~2y 1h history (yfinance 730-bar constraint). Do not rerun same hour-window construction without materially different mechanism/data.
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: Leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: Overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: Quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H177 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.