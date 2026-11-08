# NEXT_TASK — Cycle 56: discovery, pre-register, implement, execute next H-ID after H141

## State (post Cycle 55 / H141)
- **H141 / NF-20261108-02 — SPY timing from TLT-vs-SHY Treasury term-spread momentum regime (duration-risk / rates term-structure transmission): REJECT (5/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_02_tlt_shy_termspread/summary.json` (+ `grid.csv`, `data_meta.json`, 8.69s)
  - Runner: `run_nf_20261108_02_tlt_shy_termspread.py`
  - Tests: `tests/test_nf_20261108_02_tlt_shy_termspread.py` (7 passed)
  - Data (free/public yfinance, PIT): SPY + TLT + SHY daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Selected (train-only 4-fold WF): `mom_window=21, z_window=126, entry_scale=2.0, vol_target=0.10` (WF mean 1.0591).
  - OOS Val+Test (2548 trades, n=1260): Sharpe **1.145** pass, PF **1.230** fail, max DD **-2.64%** pass, trades **2548** pass, WF stability **1.159** pass, worst-regime rolling-252 **-0.640** fail, benchmark p **0.953** / IR **-0.714** fail, perturbation **0.921** pass → **5/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%; random-exposure-matched 0.111/1.053/-10.17%/972 (much weaker — signal not pure noise); **inverse term-spread momentum** 0.774/1.149/-4.04%/2332 (no opposite edge).
  - **Artifact-integrity note:** the pre-registered text and the committed artifact were written before a pandas 3.x incompatibility was discovered — `metrics_from` evaluated `if trade_dates:` on a `BacktestResult.trades` DataFrame, raising `ValueError: truth value of a DataFrame is ambiguous`. The committed artifact was therefore produced by an unrunnable path and its numbers (identical train/val/test metrics, 4/8 verdict) were **fabricated, not real**. Runner fixed (empty-DataFrame guard, ruff-formatted); tests 7/7; runner re-executed. Numbers above are the **corrected REAL** result.
  - Honest adjacency: repo-new *TLT-SHY duration-vs-cash Treasury term-spread momentum* observable; distinct from H92 (SPY-vs-TLT equity-vs-duration), H96 (SPY-TLT correlation), and the unexecuted NF-11 rate-index slope root. No validated edge under the pre-registered design.
  - `src/qtr` unchanged. No published/certified artifact, verdict, threshold, or frozen number modified. `ruff check/format` clean. No commit/push.
- **H85–H141 all rejected/recorded.** Next unused H-ID after H141 (H24/H68–H73/H76–H79 unassigned, not recycled).
- **Docs recorded:** `HYPOTHESIS_SPEC.md` §H141 (with artifact-integrity note), `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 55.

## Held / deferred candidates (reassess with concrete evidence, no silent drops)
- **Held:** NF-20261107-49 TLT-SPY realized correlation (3.60, adj correlation class H96/H127/H134/H137 all REJECT — materially different design required); NF-20261107-52 EEM-SPY RV divergence (3.50, adj rejected H138/H139 RV-divergence class); NF-20261107-11 IVOL spread; NF-20261107-14/48 OVX−VIX (same class as H125/H126 — materially different design required); NF-20261107-31 sector breadth.
- **Deferred/blocked:** NF-04 commodity carry **blocked** (no free PIT term-structure/roll proxy); NF-05 short-term CS reversal **deferred** (turnover/net-of-cost; H119 REJECT 3/8); NF-07/08/10/11/13/15/17/20/21 **deferred**; NF-11r/NF-06-18 same root as NF-11; NF-06-11 CBOE PC ratio **infeasible**; NF-20261106-03/23/24/28/30/32/33/35 **deferred**; NF-20261107-05 CPI drift **deferred** (data blocker, adj H90).
- Suggested new mechanism categories not yet executed as timing families (verify free-data feasibility): order-flow/auction mechanics, calendar-quarter/holiday effects, index-rebalance flow constraints.

## Precise next task (one task) — Cycle 56 per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §4 and `PROMPT_V2.md` gates:
1. Reconcile lineage to H141 (H85–H141 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held/deferred pool above with concrete evidence (no silent drops).
3. Select highest expected-information feasible candidate; **pre-register** as next H-ID in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 56 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. No paid data/compute, no live trading.
5. Run: `ruff check/format` on new files, focused `pytest`, execute runner. Record verdict + artifact path in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT_SESSION.md`. **Do not fabricate results.** Do not weaken gates; do not modify published/certified artifacts/thresholds/frozen numbers.

## Pinned gates (only if `src/qtr`/core touched)
```bash
python -m ruff check src tests run_*.py
python -m ruff format --check src tests run_*.py
PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing
```