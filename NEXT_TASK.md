# NEXT_TASK — Cycle 52: discovery, pre-register, implement, execute H138

## State (post Cycle 51)
- **H85–H137 all REJECTED/recorded.** H137 (NF-20261107-50, SPY timing from realized SPY--GLD return-correlation regime / safe-haven co-movement-diversification transmission) executed REAL: `.experiments/nf_runs/nf_20261107_50_spy_gld_corr/summary.json` (1.75s), verdict **REJECT 2/8**. Selected `corr_window=252, z_window=126, entry_scale=2, vol_target=0.10`. OOS Val+Test (1437 trades, n=1260): Sharpe **0.152** (fail), PF **1.035** (fail), maxDD **-14.41%** (pass), trades **1437** (pass), WF stability **0.161** (fail), worst-regime rolling-252 **-0.931** (fail), benchmark p **0.977**/IR **-0.895** (fail), perturbation **0.243** (fail). Ablations: random-exposure-matched 0.174 (comparable); **inverse** 0.943 (materially outperforms — pre-registered falsifier of directional de-risking mapping; not a validated edge under pre-registered hypothesis). Repo-new SPY--GLD pair/channel with honest adjacency to correlation-regime construction class (H96/H127/H134).
- **Next unused H-ID: H138** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H137, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 51, handoffs updated.
- **src/qtr unchanged.** No published/certified artifact, verdict, threshold, or frozen number modified.

## Verified (Cycle 51)
- `python3 -m ruff check run_nf_20261107_50_spy_gld_corr.py tests/test_nf_20261107_50_spy_gld_corr.py` → pass.
- `python3 -m ruff format --check run_nf_20261107_50_spy_gld_corr.py tests/test_nf_20261107_50_spy_gld_corr.py` → pass.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261107_50_spy_gld_corr.py` → **7 passed**.
- NF-50 executed: `.experiments/nf_runs/nf_20261107_50_spy_gld_corr/summary.json` = **REJECT 2/8**. Baseline full-suite pinned gates **not rerun** (`src/qtr` unchanged).

## Precise next task (one task)
**Execute Cycle 52 discovery, pre-register, implement, and run H138** per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H137. Propose **>=3 repo-new mechanism candidates across >=3 broad categories** with honest 25/25/20/15/10/5 scoring. **Concrete deferred reassessment (no silent drops):** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy); NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 weekly REJECT 3/8); NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 TNX-FVX **SAME root as NF-11** (not new root); NF-06-11 CBOE PC ratio **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90). **Held:** NF-20261107-11 IVOL spread (sep H118/H130 REJECTs), NF-20261107-12/51 credit-vs-equity *realized-vol divergence* (distinct PIT design required; sep H94/H100/H125), NF-20261107-14/48 OVX−VIX (same construction class as H125/H126 — **materially different pre-registered design required**), NF-20261107-31 sector breadth (adj H115 REJECT 1/8), NF-20261107-49 TLT-SPY realized corr (adj H127/H96; repo-new pair but correlation-regime construction class adjacency). NF-20261107-32/36/39/43/46/47/50 executed — not repo-new; do not rerun.
2. Select highest-expected-information feasible repo-new candidate. **Pre-register H138** in `HYPOTHESIS_SPEC.md` (§H138, decision-ready before validation outcomes) and record Cycle 52 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
3. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading.
4. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```
