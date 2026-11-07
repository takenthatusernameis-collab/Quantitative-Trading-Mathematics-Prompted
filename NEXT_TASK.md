# NEXT_TASK — Cycle 53: discovery, pre-register, implement, execute H139

## State (post Cycle 52)
- **H85–H138 all REJECTED/recorded.** H138 (NF-20261107-51, credit-vs-equity *realized-vol divergence* `RV(HYG-LQD)/RV(SPY)` z-score timing SPY; credit stress / vol-transmission divergence, repo-new second-moment divergence observable) executed REAL: `.experiments/nf_runs/nf_20261107_51_credit_equity_rv_divergence/summary.json` (1.43s), verdict **REJECT 2/8**. Selected `rv_window=21, z_window=126, entry_scale=1, vol_target=0.10`. OOS Val+Test (1218 trades, n=1260): Sharpe **0.389** (fail), PF **1.090** (fail), maxDD **-17.97%** (fail), trades **1218** (pass), WF stability **0.414** (fail), worst-regime rolling-252 **-1.362** (fail), benchmark p **0.986**/IR **-0.987** (fail), perturbation **0.927** (pass). Ablations: random-exposure-matched 0.107 (weak); **inverse RV-divergence** 1.155/1.263/-4.59% (materially outperforms — pre-registered falsifier of directional de-risking mapping; **not** a validated edge under pre-registered H138). Honest adjacency to H94/H108 (credit price/momentum, not RV divergence), H100/H125 (implied vol), H118 (equity cross-sectional dispersion).
- **Next unused H-ID: H139** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H138, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 52, handoffs updated.
- **src/qtr unchanged.** No published/certified artifact, verdict, threshold, or frozen number modified.

## Verified (Cycle 52)
- `python3 -m ruff check run_nf_20261107_51_credit_equity_rv_divergence.py tests/test_nf_20261107_51_credit_equity_rv_divergence.py` → pass.
- `python3 -m ruff format --check run_nf_20261107_51_credit_equity_rv_divergence.py tests/test_nf_20261107_51_credit_equity_rv_divergence.py` → pass.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_51_credit_equity_rv_divergence.py` → **8 passed**.
- NF-51 executed: `.experiments/nf_runs/nf_20261107_51_credit_equity_rv_divergence/summary.json` = **REJECT 2/8**. Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Precise next task (one task)
**Execute Cycle 53 discovery, pre-register, implement, and run H139** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H138. Propose **>=3 repo-new mechanism candidates across >=3 broad categories** with honest 25/25/20/15/10/5 scoring. **Concrete deferred reassessment (no silent drops):** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy); NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 weekly REJECT 3/8); NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 TNX-FVX **SAME root as NF-11** (not new root); NF-06-11 CBOE PC ratio **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90). **Held:** NF-20261107-11 IVOL spread (sep H118/H130 REJECTs), NF-20261107-14/48 OVX−VIX (same construction class as H125/H126 — **materially different pre-registered design required**), NF-20261107-31 sector breadth (adj H115 REJECT 1/8), NF-20261107-49 TLT-SPY realized corr (adj H127/H96/H134/H137 construction class), NF-20261107-52 EEM-SPY RV divergence (adj global risk/RV-divergence), NF-20261107-53 IWM/SPY RV divergence (feasible, repo-new RV-ratio pair candidate). NF-20261107-51 (=H138) executed — not rerun.
2. Select highest-expected-information feasible repo-new candidate. **Pre-register H139** in `HYPOTHESIS_SPEC.md` (§H139, decision-ready before validation outcomes) and record Cycle 53 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
3. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading.
4. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
