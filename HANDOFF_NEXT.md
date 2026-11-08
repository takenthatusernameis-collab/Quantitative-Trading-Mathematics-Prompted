# HANDOFF_NEXT — After Cycle 69 / H155 (2026-11-08)

## Completed this cycle
- **H155 / NF-20261108-24 — SPY timing from 10-year Treasury yield-level regime (^TNX z-score, long-end discount-rate/financial-conditions transmission): REJECT (5/8).**
  - Artifact: `.experiments/nf_runs/nf_20261108_24_tnx_10y_level_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 8.53s, **REAL**).
  - Runner: `run_nf_20261108_24_tnx_10y_level_spy.py`. Tests: `tests/test_nf_20261108_24_tnx_10y_level_spy.py` (**6 passed**).
  - Data (free/public, PIT): SPY + ^TNX yfinance daily auto-adjust, 3774 rows 2010-01-04→2025-01-03 (train 2514 / val 505 / test 755), 0 non-positive (^TNX verified clean).
  - Signal (pre-registered): z-score of ^TNX yield *level* (not return); continuous de-risking of vol-targeted long SPY when ^TNX is abnormally **high** (positive z = restrictive long rate); 1-bar delay via engine `signals.shift(1)`, long-only, MAX_POS=0.5, 1bp+1bp equity costs.
  - Selected (train-only 4-fold WF mean Sharpe 1.006): `z_window=126, entry_scale=2.0, vol_target=0.15`.
  - OOS Val+Test (3413 engine trades, n=1259): Sharpe **1.091** pass, PF **1.250** fail, max DD **-2.66%** pass, trades **3413** pass, WF stability **1.084** pass, worst-regime rolling-252 Sharpe **-0.289** fail, benchmark p **0.952** / IR **-0.696** fail, perturbation min ratio **0.990** pass → **5/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.750/1.153/-33.72%/1; random-exposure-matched **0.247**/1.057/-4.98%/1258 (much weaker, not pure noise, no benchmark edge); **inverse regime** (de-risk when ^TNX abnormally low / negative z) **0.837**/1.162/-3.20%/3438 — **weaker than base** (direction supported, no benchmark edge).
  - Honest root separation: NF-24 deferred Cycles 67-68 due to same-root risk vs NF-17/H154 short-rate *level* (SHY ETF return, short end, REJECT 4/8). H155 is a **maturity-distinct decisive test**: 10Y vs 1-3Y, yield-index level vs ETF price return, long-end discount-rate/term-premium channel vs short-end policy-rate tightness. Broad rates-level domain adjacency disclosed. No validated edge under pre-registered H155. No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

## Discovery (Cycle 69, directive §4)
- Reconciled lineage to H154; **H85–H155 all rejected/recorded**. Next unused H-ID: **H156** (H24/H68–H73/H76–H79 unassigned, not recycled).
- **NF root integrity (honest):** NF-24 executed with explicit maturity/instrument/channel separation from H154 (deferred same-root blocker resolved by short-end execution). NF-20261108-26 (GLD realized-vol stress, 3.50; adj H151/H149, standalone GLD RV unexecuted) verified unused/deferred. NF-20261108-27 (EWJ-vs-SPY relmom, 3.55; relmom class adj, EWJ only in H2 universe spec) verified unused/deferred. NF-22 (3.55), NF-21 (3.30), NF-23 (3.25) remain deferred. No H99/H149-style collisions.
- Candidates scored (25/25/20/15/10/5): NF-20261108-24 **3.70** selected/executed as H155; NF-20261108-27 **3.55** deferred; NF-20261108-26 **3.50** deferred.
- Deferred/held reassessed (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/20/21 deferred (NF-17 executed H154; NF-20 executed H110); NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01 lineage executed H149 (NF-20261108-14); NF-06-03/23/24/28/30/32/33/35 deferred (verify roots; NF-06-28 legacy runner/test but no artifact, credit adjacency H94/H108); NF-07-05 deferred (data blocker); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation H96/H127/H134/H137); NF-07-52 executed H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween seasonal held (3.90); NF-08-20 IEF realized-vol stress deferred (adj H151/TLT RV); NF-08-21 UNG-USO relmom deferred (3.30); NF-08-22 EFA-EEM relmom deferred (3.55); NF-08-23 USO oil-price→SPY lead-lag deferred (3.25); NF-08-26 GLD realized-vol stress deferred (3.50); NF-08-27 EWJ-vs-SPY relmom deferred (3.55).

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public data only (yfinance). No gate weakening. No commit/push.

## Verified this session
- `python -m ruff check run_nf_20261108_24_tnx_10y_level_spy.py tests/test_nf_20261108_24_tnx_10y_level_spy.py` — clean.
- `python -m ruff format --check run_nf_20261108_24_tnx_10y_level_spy.py tests/test_nf_20261108_24_tnx_10y_level_spy.py` — clean (after format).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_24_tnx_10y_level_spy.py` — **6 passed**.
- `PYTHONPATH=src python run_nf_20261108_24_tnx_10y_level_spy.py` — **REAL** verdict **REJECT 5/8**; artifact written.

## Unresolved / risks
- H155 fails PF/worst-regime/benchmark; passes Sharpe but PF 1.250 narrowly misses 1.3; random exposure much weaker (not noise) and inverse weaker than base (direction supported) — no benchmark edge. Do not promote.
- NF-20261108-26 (GLD RV stress) adjacency to H151/H149 requires explicit observable separation (standalone GLD RV vs TLT RV / GDX-GLD RV difference) before selection.
- NF-20261108-27 (EWJ-vs-SPY relmom) is in relmom construction class (H144/H145/H152 rejects) — justify materially different regional channel.
- NF-06-28 has legacy runner/test but no artifact; root/credit adjacency must be verified before any use.
- NF-08-13 ES-SPY basis stub not decision-ready (basis construction/roll-adj).
- Search space heavily depleted (H85–H155 all rejected); Cycle 70 must complete the >=3-candidate, >=3-category discovery before selecting H156.

## Precise next task (Cycle 70, directive §4)
See `NEXT_TASK.md`. In summary: reconcile lineage to H155; propose >=3 repo-new candidates across >=3 broad categories with honest scoring; verify NF roots; pre-register highest-expected-information feasible candidate as **H156**; implement runner + focused tests; run ruff + focused pytest; execute; record verdict/artifacts; update docs. Free/public data only; no gate weakening; no commit/push. If `src/qtr` touched, rerun pinned 100% coverage suite.
