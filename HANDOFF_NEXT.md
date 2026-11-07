# HANDOFF_NEXT — After Cycle 52 / H138 (2026-11-07)

## Completed this cycle
- **H138 / NF-20261107-51 — Credit-vs-equity realized-vol divergence timing SPY (`RV(HYG-LQD)/RV(SPY)`): REJECT (2/8).**
  - Artifact: `.experiments/nf_runs/nf_20261107_51_credit_equity_rv_divergence/summary.json` (+ `grid.csv`, `data_meta.json`)
  - Runner: `run_nf_20261107_51_credit_equity_rv_divergence.py`
  - Tests: `tests/test_nf_20261107_51_credit_equity_rv_divergence.py` (8 passed)
  - Data (free/public yfinance, PIT): SPY + HYG + LQD daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Selected (train-only 4-fold WF): `rv_window=21, z_window=126, entry_scale=1, vol_target=0.10` (WF mean 0.891).
  - OOS Val+Test (1218 trades, n=1260): Sharpe **0.389** fail, PF **1.090** fail, max DD **-17.97%** fail, trades **1218** pass, WF stability **0.414** fail, worst-regime rolling-252 **-1.362** fail, benchmark p **0.986** / IR **-0.987** fail, perturbation **0.927** pass → **2/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.759/1.155/-33.72%; random-exposure-matched 0.107/1.034/-22.82% (weak); **inverse RV-divergence** 1.155/1.263/-4.59% (materially outperforms — pre-registered falsifier of the directional de-risking mapping; **not** a validated edge under the pre-registered H138 hypothesis).
  - Honest adjacency: repo-new *realized-vol divergence ratio* observable (second-moment cross-asset). Distinct from H94/H108 (credit *price/momentum*, not RV divergence), H100/H125 (*implied* vol), H118 (equity cross-sectional dispersion). Adjacency acknowledged.

## Discovery (Cycle 52, directive §4)
- Reconciled lineage to H137 (H85–H137 rejected/recorded). Proposed >=3 candidates across >=3 broad categories, scored 25/25/20/15/10/5:
  - NF-20261107-51 credit-vs-equity *realized-vol divergence* (`RV(HYG-LQD)/RV(SPY)`) — **3.95, selected/executed H138**.
  - NF-20261107-53 IWM/SPY *realized-vol ratio divergence* (size/liquidity vol transmission) — **3.75, held**.
  - NF-20261107-49 TLT-SPY realized correlation (rates-equity co-movement) — **3.60, held** (adj correlation-regime construction class H96/H127/H134/H137).
  - NF-20261107-52 EEM-vs-SPY realized-vol divergence (global risk transmission) — **3.50, held**.
- Deferred/held reassessed with concrete evidence (no silent drops): NF-04 **blocked**; NF-05 deferred (turnover; H119 REJECT); NF-07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 **SAME root as NF-11**; NF-06-11 **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 deferred; NF-20261107-05 CPI deferred (data blocker). Held: NF-20261107-11/14(48)/31/49/52/53. NF-20261107-51 (=H138) and prior NF-20261107-32/36/39/43/46/47/50 executed — not rerun.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261107_51_credit_equity_rv_divergence.py tests/test_nf_20261107_51_credit_equity_rv_divergence.py` — clean.
- `python3 -m ruff format --check ...` — clean.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_51_credit_equity_rv_divergence.py` — **8 passed**.
- `PYTHONPATH=src python3 run_nf_20261107_51_credit_equity_rv_divergence.py` — verdict **REJECT 2/8**.

## Unresolved / risks
- H138 inverse RV-divergence mapping outperformed (1.155/1.263/-4.59%) but was a *pre-registered falsifier*, not a pre-registered acceptance hypothesis — do not promote to PASS without fresh pre-registration/gates.
- Correlation-regime construction class heavily tested (H96/H127/H134/H137 all rejected); NF-49 needs clearly distinct mechanism/design, not a new pair alone.
- NF-14/48 OVX−VIX remains held but requires **materially different pre-registered design** (same IV-spread construction class as H125/H126).

## Precise next task (Cycle 53, directive §4)
1. Reconcile lineage to H138 (H85–H138 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred/held NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (same root as NF-11), NF-06-11, NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05, NF-20261107-11/14(48)/31/49/52/53 with concrete evidence (no silent drops).
3. Pre-register highest-expected-information feasible candidate as **H139** with smallest decisive test, PIT timing, costs, splits, gates, ablations, and falsifiers.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts in `HYPOTHESIS_SPEC.md` and `NEW_FAMILY_RESEARCH_REGISTER.md`, update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
