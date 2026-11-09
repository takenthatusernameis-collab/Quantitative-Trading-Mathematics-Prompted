# HANDOFF_NEXT (Cycle 78)

## Completed this session (Cycle 77)
- **H163 / NF-20261109-05 — HYG high-yield credit-momentum regime SPY timing (credit risk-premium / momentum regime transmission): REJECT (3/8, REAL).**
  - Artifact: `.experiments/nf_runs/nf_20261109_05_hyg_momentum_spy/summary.json` (+ `grid.csv`, `data_meta.json`, 71.17s)
  - Runner: `run_nf_20261109_05_hyg_momentum_spy.py`; Tests: `tests/test_nf_20261109_05_hyg_momentum_spy.py` (**11 passed**)
  - Data (free/public yfinance, PIT): SPY (traded) + HYG (signal), daily auto-adjust Close, 4233 rows 2010-01-04→2026-10-30 (train 2515 / val 756 / test 962; OOS Val+Test n=1716).
  - Signal: trailing HYG return-momentum z-score with hysteresis (`z <= -entry_scale` de-risk / credit-momentum stress, `z >= exit_scale` full exposure, hold prior, initial long), vol-targeted SPY, 1-bar delay via engine `signals.shift(1)`, long-only, Equity CostModel defaults.
  - Selected (train-only 4-fold WF mean Sharpe 0.975): `lookback=252, z_window=252, entry_scale=1.5, exit_scale=0.0, vol_target=0.15`.
  - OOS Val+Test (2568 trades, n=1716): Sharpe **0.935** fail, PF **1.224** fail, max DD **-2.14%** pass, trades **2568** pass, WF stability **0.975** pass (train 0.958→OOS 0.935), worst-regime rolling-252 **-1.336** fail, benchmark p **0.903** / IR **-0.545** fail, perturbation **0.664** pass → **3/8 REJECT**.
  - Ablations OOS: buy-hold SPY 0.792/1.164/-33.72%/1; random-exposure-matched **0.209**/1.090/-2.21%/1323 (much weaker, structure present, no edge); **inverse regime** (de-risk on strong HYG momentum) **0.148**/1.035/-4.65%/3782 (much weaker, direction supported, no edge). Val 0.806 / Test 1.037 (test stronger but combined OOS fails gates/benchmark).
  - Honest adjacency: repo-new executed *HYG return-momentum z-score* SPY-timing observable. Distinct from H94 HYG-IEF excess *level* (REJECT 4/8), H108 LQD-HYG ratio *level* (REJECT 4/8), H146 JNK/LQD ratio *level* (REJECT 4/8). Construction-class adjacency (z-score hysteresis/de-risking/vol-target/1-bar delay) disclosed. No validated edge.
  - **NF-ID mapping (honest):** Cycle-75/76 carried-forward NF-20261109-04 (HYG momentum proposal, 3.95) had no executed artifact; executed as **NF-20261109-05 / H163** to avoid lineage ambiguity with proposal labels. NF-09-03 (breakeven inflation) downgraded/deferred this cycle: ^T5YIE/^T10YIE unavailable on yfinance probe 2026-11-09; TIP/IEF ETF proxy weak/confounded.
- **Cycle 77 discovery (directive §4):** Reconciled lineage to H162. Proposed/scored >=3 repo-new/decisive candidates across >=3 broad mechanism categories with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops): NF-20261109-05 HYG credit-momentum (3.95, **selected/executed as H163**), NF-20261106-33 EWH/SPY China-exposure/capital-flow (3.35, deferred/confounded), NF-20261108-16 Halloween seasonal (3.35, deferred/calendar adjacency), NF-20261109-03 TIP/IEF breakeven-inflation (downgraded 3.50, deferred/data-limited). NF roots verified (no H99/H149-style collisions).
- **Docs updated:** `HYPOTHESIS_SPEC.md` §H163, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 77, `NEXT_TASK.md`, `HANDOFF_NEXT.md`.

## Invariants preserved
- `src/qtr` unchanged — pinned 100% coverage suite **not rerun**.
- No published/certified/frozen artifacts, thresholds, or verdicts modified.
- Free/public yfinance data only. No gate weakening. No commit/push.

## Verified this session
- `python3 -m py_compile run_nf_20261109_05_hyg_momentum_spy.py tests/test_nf_20261109_05_hyg_momentum_spy.py` — clean (imports qtr.engine at runtime).
- `python -m ruff check run_nf_20261109_05_hyg_momentum_spy.py tests/test_nf_20261109_05_hyg_momentum_spy.py` — **All checks passed**.
- `python -m ruff format --check` (same files) — **clean**.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_05_hyg_momentum_spy.py` — **11 passed**.
- `python3 run_nf_20261109_05_hyg_momentum_spy.py` — completed; artifact written. Verdict **REJECT 3/8** (REAL, not fabricated).
- **Not rerun:** full pinned `src/qtr` suite (no `src/qtr` change); global ruff/format over `src tests run_*.py`.

## Approaches / evidence (do not blindly repeat)
- H163 direction supported (inverse 0.148, random 0.209 much weaker) but fails Sharpe/PF/worst-regime/benchmark gates (p=0.903, IR=-0.545). Reject stands.
- Credit-family executed rejects: H94 HYG-IEF excess level (4/8), H108 LQD-HYG ratio level (4/8), H146 JNK/LQD ratio level (4/8), **H163 HYG momentum z-score (3/8)**. Further HY/IG credit observables require clear separation.
- Dispersion de-risking rejects remain: H118/H160/H162. FX-channel rejects include H95/H103/H106/H161. Implied-vol/VRP rejects include H158/H159/H160 etc. — see lineage.
- NF-09-03 direct breakeven indices (^T5YIE/^T10YIE) unavailable on yfinance probe 2026-11-09; TIP/IEF proxy previously weak/confounded.

## Precise next task (Cycle 78, directive §4)
1. Reconcile lineage to H163 (H85–H163 rejected/recorded). Next unused H-ID: **H164** (H24/H68–H73/H76–H79 unassigned, not recycled).
2. Propose **>=3 repo-new candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring; reassess deferred pool with concrete evidence (no silent drops). Reassess: NF-20261109-03 (breakeven, data-limited), NF-20261106-33 (EWH/SPY, 3.35), NF-20261108-16 (Halloween, 3.35), NF-20261108-26 (GLD RV stress, 3.50). Justify independence from rejected classes (credit H94/H108/H146/H163, dispersion H118/H160/H162, FX H95/H103/H106/H161).
3. Verify NF roots against executed H-IDs/artifacts/runners before selection. NF-20261109-05/H163 executed; NF-09-04 mechanism consumed (document honestly).
4. Pre-register highest-expected-information feasible candidate as **H164** in `HYPOTHESIS_SPEC.md` before validation outcomes; record Cycle 78 discovery in `NEW_FAMILY_RESEARCH_REGISTER.md`.
5. Add `run_nf_*.py` + focused `tests/test_nf_*.py`. Free/public data only (yfinance ok). `src/qtr` unchanged. **Pandas 3.x safety:** do not use `if <DataFrame>:` truthiness.
6. Run `ruff check/format`, focused `pytest`, execute REAL runner; record verdict + artifact path. **Do not fabricate results.** No gate weakening; no published/certified artifact modification.
7. If `src/qtr` is touched, rerun: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python3 -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
