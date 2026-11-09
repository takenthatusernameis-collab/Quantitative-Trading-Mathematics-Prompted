# NEXT_TASK.md — Cycle 75 complete (discovery + H161 pre-registered)

## Status: Cycle 75 discovery complete — H161 PRE-REGISTERED, execution pending

**Lineage:** H85–H160 all rejected/recorded. H161 (NF-20261109-02) pre-registered as highest-expected-information feasible candidate from Cycle 75 discovery. Next unused H-ID after H161: **H162** (H24/H68–H73/H76–H79 unassigned, not recycled).

**Mechanism (repo-new observable, pre-registered):** G10 currency carry basket risk-appetite timing SPY — trailing equal-weight G10 carry basket (long AUD/NZD/CAD vs JPY, short EUR/CHF/USD vs JPY) momentum z-score; de-risk vol-targeted long SPY when carry-basket momentum abnormally negative (carry unwind / risk-off), full exposure when benign; hysteresis, 1-bar delay via engine `signals.shift(1)`, long-only, Equity CostModel defaults (1 bp commission + 1 bp spread), MAX_POS=0.5.

**Data (free, point-in-time feasible):** SPY + 7 G10 pairs vs JPY (AUDJPY=X, NZDJPY=X, CADJPY=X, EURJPY=X, GBPJPY=X, CHFJPY=X, USDJPY=X) daily auto-adjust Close (yfinance). Common start ~2010-01-04; verify alignment/coverage on REAL run. Splits: Train 2010-01-01→2019-12-31; Val 2020-01-01→2022-12-31; Test (protected) 2023-01-01→2026-10-31.

**Grid (bounded, pre-registered):** `lookback ∈ {63,126,252}` × `z_window ∈ {126,252}` × `entry_scale ∈ {1.0,1.5,2.0}` × `exit_scale ∈ {0.0,0.5}` × `vol_target ∈ {0.10,0.15}` = 48 combos. Selection = best train-only 4-fold walk-forward Sharpe; gates on OOS Val+Test.

**Gates (OOS Val+Test, PROMPT_V2 Phase 4):** Sharpe ≥ 1.0, ≥ 200 trades, PF ≥ 1.3, max DD ≤ 15%, WF stability ≥ 0.7×train (when train>0), worst-regime rolling-252 Sharpe ≥ 0.3, benchmark p ≤ 0.05 vs buy-hold SPY with IR ≥ 0 (direction-aware), perturbation min ratio ≥ 0.5 (OAT ±20% on all grid params). All gates fail-closed on pre-registered OOS Val+Test.

**Falsifiers (pre-registered):** Random-exposure-matched (same on-bars, shuffled); inverse-signal (de-risk on positive z); buy-hold SPY benchmark; OAT perturbation; worst-regime rolling-252 Sharpe; Val vs Test subperiod stability; benchmark p-value vs SPY with IR ≥ 0.

**Adjacency disclosed (honest):** FX-channel adjacency to H95 (UUP USD basket), H103 (FXA AUD risk-on), H106 (FXY JPY safe-haven), H129/H134 (FX carry proposed Cycles 64/65). G10 carry basket is a diversified, carry-weighted construction distinct from single-currency or USD-basket families; scored novelty 4 (not 5) for honest adjacency.

**Deferred candidates carried forward (no silent drops):**
- NF-20261108-29 cross-asset return dispersion (4.10, Cycle 73/74)
- NF-20261109-03 TIPS breakeven inflation level regime (3.95, this cycle)
- NF-20261109-04 HYG momentum regime (3.95, this cycle)
- Plus all previously documented deferred/blocked candidates (NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r, NF-06-11, etc. — full list in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 75).

## Files to add (Cycle 75 execution)
- `run_nf_20261109_02_g10_carry.py` — H161 runner (pre-registered statement, 48-combo grid, train-only WF selection, 8 OOS gates, ablations, falsifiers, isolated cache)
- `tests/test_nf_20261109_02_g10_carry.py` — 10 focused tests (data fetch, signal construction, grid search, WF selection, gate evaluation, perturbation, ablations, artifact writing, cache isolation, PIT)
- `HYPOTHESIS_SPEC.md` — §H161 result appended (selected config, OOS metrics, gates, ablations, verdict, lineage)
- `NEW_FAMILY_RESEARCH_REGISTER.md` — Cycle 75 execution section appended (runner, execution, REAL result, lineage update)
- `NEXT_TASK.md` / `HANDOFF_NEXT.md` — updated for Cycle 76

## Verification (pending execution)
- `python -m ruff check run_nf_20261109_02_g10_carry.py tests/test_nf_20261109_02_g10_carry.py` — All checks must pass.
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_02_g10_carry.py` — **10 passed**.
- `PYTHONPATH=src python run_nf_20261109_02_g10_carry.py` — completed; REAL verdict recorded, artifact written.
- Global `ruff check src tests run_*.py` clean (H161 files included).

## No outstanding Cycle-75 discovery work
`src/qtr` unchanged; pinned full gates not rerun (no `src/qtr` change). No commit/push (not authorized). If `src/qtr` is touched later, run: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.

## If Cycle 75 execution is requested (H161)
Implement runner + tests per above, run verification, execute, record REAL verdict. Do not recycle H24/H68–H73/H76–H79. Free/public data only; no gate weakening.