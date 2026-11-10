# NEXT_TASK.md — Cycle 90 (after H175 REJECT 1/8)

## Status: Cycle 89 complete (H175 executed REAL; REJECT) — Cycle 90 discovery pending

## H175 result (REAL, not fabricated) — REJECT 1/8
- Runner `run_nf_20261109_03_macro_regime.py` + tests `tests/test_nf_20261109_03_macro_regime.py` (**10 passed**). `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261109_03_macro_regime_20261110_004316/summary.json` (+`grid.csv`, ~11s).
- Data (PIT, free yfinance): SPY daily 2010-01-04→2026-10-30 (4233 aligned rows with HG=F, GC=F, TIP, IEF). Train 50% (~2010→2018-06-04), Val 25% (→2022-08-15), Test protected final 25% (~2022→2026). Train-only 4-fold WF selection; gates on OOS Val+Test only.
- Construction (daily, causal, 36-combo grid): `lookback {63,126,252} × entry_z {0.5,1.0,1.5} × exit_z {0.0,0.5} × vol_target {0.10,0.15}`; regime = z(log(HG=F/GC=F), L) − z(log(TIP/IEF), L); hysteresis entry_z→long/exit_z→flat; vol-target off trailing 21-day SPY realized vol; long-only MAX_POS=0.5; Equity CostModel defaults (1bp commission+1bp spread); 1-bar delay via engine `signals.shift(1)`.
- Selected (train-only 4-fold WF Sharpe 1.288; train-ref Sharpe 1.189): `lookback=126, entry_z=1.0, exit_z=0.0, vol_target=0.10`.
- OOS Val+Test (1717 periods, 123 trades): Sharpe **−0.005** fail (≥1.0), PF **0.998** fail (≥1.3), max DD **−9.7%** pass (≤15%), trades **123** fail (≥200), WF stability **−0.004** fail (≥0.7), worst-regime rolling-252 Sharpe **−1.31** fail (≥0.3), benchmark p **0.996** / IR **−0.931** vs buy-hold SPY 0.810 (fail), perturbation min ratio **−32.37** fail (≥0.5). → **REJECT 1/8**.
- Ablations OOS: buy-hold SPY 0.810/1.168/+83.7%; random-regime 0.121/1.048/688 trades; inverse-regime (direction falsifier) **1.009/1.217/382 trades — outperforms the signal**, direction falsified.
- Bug fixed during implementation: regime composite `(g_z - i_z).fillna(0)` poisoned entire signal to zero when either component had zero rolling std; fixed to `g_z.fillna(0) - i_z.fillna(0)` in runner + inverse-regime falsifier.
- **Integrity (honest):** `ruff check/format` clean; focused pytest 10 passed. No gate/threshold/grid/construction weakened; `src/qtr` unchanged. No published/certified artifact modified.
- Documented in `HYPOTHESIS_SPEC.md` §H175 and `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 89 execution).

## Lineage
**Lineage:** H85–H175 all rejected/recorded. Next unused H-ID: **H176** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public data only. No commit/push unless explicitly authorized.

## Cycle 90 Discovery Pending

Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions:** H85–H175 rejected/recorded, H176 next unused. No tracked draft collides with H176. NF-label reuse avoided.
2. **Directive §4 discovery scan:** Propose repo-new candidates across broad mechanism categories with honest scoring and concrete deferred reassessment.
3. **Reassess carried-forward/deferred pool with evidence:** NF-20261109-15 tax-loss harvesting (4.20), NF-20261109-16 dividend capture (3.95), NF-20261109-12 holiday drift (4.00), NF-20261109-22 RSP-SPY breadth relmom (3.75), NF-20261109-23 USMV-SPY low-vol relmom (3.55), NF-20261109-02 earnings revision (3.65), NF-20261109-18/19/20 deferred, NF-04 blocked, NF-05 deferred, NF-08-16 held, NF-09-03 data-limited — reassess with updated evidence.
4. **Verify NF roots** against executed H-IDs/artifacts/runners.
5. **Pre-register highest-expected-information feasible candidate as H176.**
6. **Next steps (this cycle):**
    - Implement runner + focused tests for selected H176 candidate
    - Run `python -m ruff check/format --check` and `PYTHONPATH=src python -m pytest -q` focused tests (all pass)
    - Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H176, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 90, `NEXT_TASK.md`, `HANDOFF_NEXT.md`
    - **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H175: Cross-asset macro regime timing (z(HG=F/GC=F) − z(TIP/IEF) → SPY) failed 7/8 gates (Sharpe −0.005, PF 0.998, trades 123, WF −0.004, worst-regime −1.31, benchmark p 0.996/IR −0.931, perturbation −32.37); only maxDD passes; inverse-regime direction falsifier outperforms (1.009 vs −0.005); train WF 1.288 → OOS −0.005 decay. Composite macro regime has no OOS edge on free daily data after costs.
- H174: ETF premium/discount mean reversion (NAV approximated) failed 6/8 gates (Sharpe 0.074, PF 1.019, DD −18.95%, worst-regime −1.753, benchmark p 0.982/IR −0.721, perturbation 0.0); random-premium ablation outperforms signal; NAV approximation invalidates mechanism test — **without point-in-time NAV, creation/redemption arbitrage cannot be fairly tested**.
- H173: Fed model / ERP timing (div yield − 10Y yield) failed 7/8 gates (Sharpe 0.310, PF 1.170, DD −16.89%, trades 114, WF 0.264, worst-regime −1.326, benchmark p 0.991/IR −0.813); inverse-signal outperformed (0.739); train WF 1.363 → OOS 0.310 decay.
- H172: SPY 1h intraday seasonality (ET windows) failed Sharpe/PF/WF/worst-regime/benchmark; limited ~2y 1h history (yfinance 730-bar constraint).
- H171: ^TYX-^FVX slope de-risking failed Sharpe/PF/worst-regime/benchmark.
- H170: Leveraged ETF rebalancing flow failed Sharpe/PF/worst-regime/benchmark/perturbation.
- H169: Overnight futures lead-lag failed Sharpe/PF/worst-regime/benchmark.
- H168: Quarterly index-rebalance window de-risking failed; random-window control matched base.
- All H85–H175 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.
