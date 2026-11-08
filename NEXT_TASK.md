# NEXT_TASK — Cycle 54: discovery, pre-register, implement, execute H140

## State (post Cycle 53)
- **H85–H139 all REJECTED/recorded.** H139 (NF-20261107-53, IWM-vs-SPY *realized-vol divergence* `RV(IWM)/RV(SPY)` z-score timing SPY; size/liquidity risk-transmission divergence, repo-new IWM/SPY second-moment divergence pair) executed REAL: `.experiments/nf_runs/nf_20261107_53_iwm_spy_rv_divergence/summary.json` (3.32s, 2026-11-07T23:06:29Z), verdict **REJECT 2/8**. Selected `rv_window=63, z_window=126, entry_scale=2, vol_target=0.15`. OOS Val+Test (1383 trades, n=1260): Sharpe **0.461** (fail), PF **1.110** (fail), maxDD **-17.97%** (fail), trades **1383** (pass), WF stability **0.524** (fail), worst-regime rolling-252 **-0.750** (fail), benchmark p **0.982**/IR **-0.937** (fail), perturbation **0.923** (pass). Ablations: random-exposure-matched 0.042 (weak); **inverse RV-divergence** 1.065/1.225/-4.71% (materially outperforms — pre-registered falsifier of directional de-risking mapping; **not** a validated edge under pre-registered H139). Honest adjacency to H118 (return dispersion), H130 (cross-sectional IVOL), H138 (credit-vs-equity RV divergence). *Artifact-integrity note:* H139 immutable artifact description strings in `summary.json`/`data_meta.json` retain a copy-paste HYG-LQD reference; numbers/verdict unchanged; runner description corrected.
- **Next unused H-ID: H140** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H139, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 53, handoffs updated.
- **src/qtr unchanged.** No published/certified artifact, verdict, threshold, or frozen number modified.

## Verified (Cycle 53)
- `python3 -m ruff check run_nf_20261107_53_iwm_spy_rv_divergence.py tests/test_nf_20261107_53_iwm_spy_rv_divergence.py` → pass.
- `python3 -m ruff format --check run_nf_20261107_53_iwm_spy_rv_divergence.py tests/test_nf_20261107_53_iwm_spy_rv_divergence.py` → pass (runner description text corrected; artifact text immutable).
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_53_iwm_spy_rv_divergence.py` → **7 passed**.
- NF-53 artifact verified: `.experiments/nf_runs/nf_20261107_53_iwm_spy_rv_divergence/summary.json` = **REJECT 2/8**. H139 files/artifacts were already present/tracked in repo state; no rerun fabricated. Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Precise next task (one task)
**Execute Cycle 54 discovery, pre-register, implement, and run H140** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H139. Propose **>=3 repo-new mechanism candidates across >=3 broad categories** with honest 25/25/20/15/10/5 scoring. **Concrete deferred reassessment (no silent drops):** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy); NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 weekly REJECT 3/8); NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 TNX-FVX **SAME root as NF-11** (not new root); NF-06-11 CBOE PC ratio **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90). **Held:** NF-20261107-11 IVOL spread (sep H118/H130 REJECTs), NF-20261107-14/48 OVX−VIX (same construction class as H125/H126 — **materially different pre-registered design required**), NF-20261107-31 sector breadth (adj H115 REJECT 1/8), NF-20261107-49 TLT-SPY realized corr (adj H127/H96/H134/H137 correlation-regime construction class — **needs clearly distinct mechanism/design, not a new pair alone**), NF-20261107-52 EEM-SPY RV divergence (adj global risk/RV-divergence; adjacent to H138/H139 RV-ratio construction). NF-20261107-51/53 (=H138/H139) executed — not rerun. H138/H139 **inverse RV-divergence falsifiers** were not pre-registered PASS hypotheses — do **not** promote without fresh pre-registration/gates.
2. Select highest-expected-information feasible repo-new candidate. **Pre-register H140** in `HYPOTHESIS_SPEC.md` (§H140, decision-ready before validation outcomes) and record Cycle 54 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
3. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading.
4. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
