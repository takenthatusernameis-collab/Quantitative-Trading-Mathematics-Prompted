# HANDOFF_NEXT — After Cycle 55 / H141 (2026-11-08)

## Completed this cycle
- **H141 / NF-20261108-02 — SPY timing from TLT-vs-SHY Treasury term-spread momentum regime (duration-risk / rates term-structure transmission): REJECT (5/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_02_tlt_shy_termspread/summary.json` (+ `grid.csv`, `data_meta.json`, 8.69s)
  - Runner: `run_nf_20261108_02_tlt_shy_termspread.py`
  - Tests: `tests/test_nf_20261108_02_tlt_shy_termspread.py` (7 passed)
  - Data (free/public yfinance, PIT): SPY + TLT + SHY daily auto-adjust Close, 3776 aligned rows 2010-01-04→2025-01-03 (train 2516 / val 505 / test 755).
  - Selected (train-only 4-fold WF mean Sharpe 1.0591): `mom_window=21, z_window=126, entry_scale=2.0, vol_target=0.10`.
  - OOS Val+Test (2548 trades, n=1260): Sharpe **1.145** pass, PF **1.230** fail, max DD **-2.64%** pass, trades **2548** pass, WF stability **1.159** pass, worst-regime rolling-252 **-0.640** fail, benchmark p **0.953** / IR **-0.714** fail, perturbation **0.921** pass → **5/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%; random-exposure-matched **0.111**/1.053/-10.17%/972 (much weaker — signal not pure noise); **inverse term-spread momentum** **0.774**/1.149/-4.04%/2332 (no opposite edge).
  - **Artifact-integrity note (important):** the pre-registered text and the committed artifact were written before a pandas 3.x incompatibility was discovered — `metrics_from` evaluated `if trade_dates:` on a `BacktestResult.trades` DataFrame, raising `ValueError: truth value of a DataFrame is ambiguous`. The committed artifact was therefore produced by an unrunnable path and its numbers (identical train/val/test metrics, 4/8 verdict) were **fabricated, not real**. Runner fixed (empty-DataFrame guard, ruff-formatted); tests 7/7; runner re-executed. Numbers above are the **corrected REAL** result.
  - Repo-new duration-risk / rates term-structure transmission observable (distinct from H92 SPY-vs-TLT equity-vs-duration, H96 SPY-TLT correlation, and unexecuted NF-11 rate-index slope root). No validated edge under the pre-registered design.
  - `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified; `ruff check/format` clean. No commit/push.

## Discovery (Cycle 55)
- Lineage reconciled to H140: H85–H140 all rejected/recorded. H141 pre-registered in Cycle 55 plan; execution completed this session. Next unused H-ID after H141 (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged.
- Cycle 55 did **not** perform fresh directive §4 discovery (H141 was already pre-registered and only needed execution + the pandas-3 repair). Discovery deferred to Cycle 56.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m ruff check run_nf_20261108_02_tlt_shy_termspread.py tests/test_nf_20261108_02_tlt_shy_termspread.py` — clean.
- `python3 -m ruff format --check ...` — clean.
- `PYTHONPATH=src python3 -m pytest -q tests/test_nf_20261108_02_tlt_shy_termspread.py` — **7 passed**.
- H141 artifact verified REAL (re-executed): `.experiments/nf_runs/nf_20261108_02_tlt_shy_termspread/summary.json` = **REJECT 5/8** (Sharpe 1.145 / PF 1.230 / maxDD -2.64% / trades 2548 / WF 1.159 / worst-regime -0.640 / benchmark p 0.953 / IR -0.714 / perturbation 0.921).

## Unresolved / risks
- H141 passes Sharpe/maxDD/WF only because the selected config is near-cash (mean OOS exposure 0.50, vol_target 0.10) — a low-vol long-SPY overlay, not a timing edge. Worst-regime collapses (-0.640) and benchmark is insignificant (p 0.953, IR -0.714).
- Correlation class (H96/H127/H134/H137) and RV-divergence class (H138/H139) heavily rejected; held NF-49/NF-52 need clearly distinct designs to avoid redundant construction-class testing.
- All H85–H141 rejected: no validated edge found across ~57 hypotheses; continuation requires genuinely new mechanism categories, not pair/parameter variants.
- **Pandas 3.x engine incompatibility:** `BacktestResult.trades` is a DataFrame; any runner using `if bt.trades:` or `if trade_dates:` on it will crash. Check new runners against this before execution.

## Precise next task (Cycle 56, directive §4)
1. Reconcile lineage to H141 (H85–H141 rejected/recorded).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess held NF-20261107-49/52/11/14(48)/31 and deferred pool with concrete evidence (no silent drops).
3. Pre-register highest expected-information feasible candidate as **next H-ID after H141** in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 56 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
4. Implement runner + focused tests, run ruff, run focused pytest, execute, record verdict/artifacts; update `NEXT_TASK.md`/handoffs.
5. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.