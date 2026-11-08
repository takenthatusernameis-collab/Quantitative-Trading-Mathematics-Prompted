# HANDOFF_NEXT — After Cycle 53 / H139 (2026-11-07)

## Completed this cycle
- **H139 / NF-20261107-53 — IWM-vs-SPY realized-vol divergence timing SPY (`RV(IWM)/RV(SPY)`): REJECT (2/8).**
  - Artifact: `.experiments/nf_runs/nf_20261107_53_iwm_spy_rv_divergence/summary.json` (+ `grid.csv`, `data_meta.json`, timestamp `2026-11-07T23:06:29Z`, 3.32s)
  - Runner: `run_nf_20261107_53_iwm_spy_rv_divergence.py`
  - Tests: `tests/test_nf_20261107_53_iwm_spy_rv_divergence.py` (7 passed)
  - Data (free/public yfinance, PIT): SPY + IWM daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Selected (train-only 4-fold WF): `rv_window=63, z_window=126, entry_scale=2, vol_target=0.15` (WF mean 0.775).
  - OOS Val+Test (1383 trades, n=1260): Sharpe **0.461** fail, PF **1.110** fail, max DD **-17.97%** fail, trades **1383** pass, WF stability **0.524** fail, worst-regime rolling-252 **-0.750** fail, benchmark p **0.982** / IR **-0.937** fail, perturbation **0.923** pass → **2/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.759/1.155/-33.72%; random-exposure-matched 0.042/1.014/-22.45% (weak); **inverse RV-divergence** 1.065/1.225/-4.71% (materially outperforms — pre-registered falsifier of the directional de-risking mapping; **not** a validated edge under the pre-registered H139 hypothesis).
  - Honest adjacency: repo-new *IWM/SPY realized-vol divergence ratio* pair/channel (size/liquidity risk transmission). Distinct from H118 (cross-sectional sector return dispersion, first-moment), H130 (cross-sectional average sector IVOL), H138 (credit-spread HYG−LQD vs SPY RV divergence). RV-divergence construction class adjacency acknowledged.
  - **Artifact-integrity note:** immutable artifact description strings in `summary.json`/`data_meta.json` retain a copy-paste HYG-LQD credit-spread reference from the H138 template; artifact numbers/verdict are unchanged evidence of the executed IWM/SPY run. Runner `EXPERIMENT_DESC` corrected in Cycle 53.

## Discovery (Cycle 53, directive §4)
- Reconciled lineage to H138 (H85–H138 rejected/recorded). Proposed >=3 candidates across >=3 broad categories, scored 25/25/20/15/10/5:
  - NF-20261107-53 IWM/SPY *realized-vol ratio divergence* (size/liquidity risk-transmission) — **3.75, selected/executed H139** (honest adjacency to H118/H130/H138/RV-ratio construction).
  - NF-20261107-49 TLT-SPY realized correlation (rates-equity co-movement) — **3.60, held** (adj correlation-regime construction class H96/H127/H134/H137 — needs clearly distinct mechanism/design, not a new pair alone).
  - NF-20261107-52 EEM-vs-SPY realized-vol divergence (global risk transmission) — **3.50, held** (adj RV-divergence/construction).
  - NF-20261107-14/48 OVX−VIX IV spread — **3.35, not selected** (same IV-spread construction class as H125/H126; **materially different pre-registered design required**).
- Deferred/held reassessed with concrete evidence (no silent drops): NF-04 **blocked**; NF-05 deferred (turnover; H119 REJECT); NF-07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 **SAME root as NF-11**; NF-06-11 **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05 CPI deferred (data blocker). Held: NF-20261107-11/14(48)/31/49/52. NF-20261107-51 (=H138), NF-20261107-53 (=H139), prior NF-20261107-32/36/39/43/46/47/50 executed — not rerun.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261107_53_iwm_spy_rv_divergence.py tests/test_nf_20261107_53_iwm_spy_rv_divergence.py` — clean.
- `python3 -m ruff format --check ...` — clean (after runner description correction).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_53_iwm_spy_rv_divergence.py` — **7 passed**.
- H139 artifact verified: `.experiments/nf_runs/nf_20261107_53_iwm_spy_rv_divergence/summary.json` = **REJECT 2/8** (REAL). H139 files/artifacts were present/tracked; not fabricated/re-executed.

## Unresolved / risks
- H139 inverse RV-divergence mapping outperformed (1.065/1.225/-4.71%) but was a *pre-registered falsifier*, not a pre-registered acceptance hypothesis — do not promote to PASS without fresh pre-registration/gates. Same caution applies to H138 inverse.
- Correlation-regime construction class heavily tested (H96/H127/H134/H137 all rejected); NF-49 needs a clearly distinct mechanism/design, not a new pair alone.
- RV-divergence construction class now tested with credit (H138) and size/liquidity (H139), both rejected with inverse falsifiers; NF-52 (EEM-SPY) is adjacent — must justify distinct global-risk transmission channel/design to avoid redundant construction testing.
- NF-14/48 OVX−VIX remains held but requires **materially different pre-registered design** (same IV-spread construction class as H125/H126).
- H139 immutable artifact description strings contain H138 copy-paste text (HYG-LQD) — artifact numbers unchanged; runner text corrected.

## Precise next task (Cycle 54, directive §4)
1. Reconcile lineage to H139 (H85–H139 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (same root as NF-11), NF-06-11, NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05, NF-20261107-11/14(48)/31/49/52 with concrete evidence (no silent drops).
3. Pre-register highest-expected-information feasible candidate as **H140** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
