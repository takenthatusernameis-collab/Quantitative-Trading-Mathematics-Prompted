# HANDOFF_NEXT

## 1) What changed (Cycle 75 complete, H161 pre-registered)

- **Lineage reconciled to H160.** H85–H160 all rejected/recorded prior to this cycle. Cycle 75 completed the mandatory new-family discovery per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`: proposed and scored ≥3 repo-new mechanism candidates across ≥3 broad mechanism categories (honest 25/25/20/15/10/5) with concrete deferred reassessment (no silent drops) and NF-root integrity checks against executed H-IDs/artifacts before selection.
- **Cycle 75 discovery (directive §4).** Three candidates scored 3.95 weighted (tied):
  - NF-20261109-02 G10 currency carry basket risk-appetite timing SPY (4.15→3.95 after honest adjacency) — **Currency carry / FX risk-premium transmission** — **H161 selected/pre-registered**
  - NF-20261109-03 TIPS breakeven inflation level regime timing SPY (3.95) — Inflation expectations / real-yield regime transmission — deferred as Cycle 76 high-expected-information alternative
  - NF-20261109-04 High-yield credit momentum regime timing SPY (3.95) — Credit risk-premium / momentum regime transmission — deferred as Cycle 77 high-expected-information alternative
- **H161 pre-registered (decision-ready).** `NF-20261109-02` pre-registered in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 75 and `HYPOTHESIS_SPEC.md` §H161 with bounded 48-combo grid, train-only 4-fold WF selection, Test protected, OOS Val+Test 8 gates + ablations. Smallest decisive test: 7 G10 pairs vs JPY (yfinance, free), SPY traded, continuous scaling avoids H95/H103 sparsity, decisive falsifiers pre-registered (random-exposure, inverse-signal, buy-hold SPY, perturbation, worst-regime, subperiod stability). Adjacency to H95/H103/H106/H129/H134 (FX families) disclosed and scored honestly (novelty 4, not 5).
- **Implementation pending.** Runner `run_nf_20261109_02_g10_carry.py` + tests `tests/test_nf_20261109_02_g10_carry.py` to be created next session following H160 template. No `src/qtr` changes expected.

## 2) Actually verified (this session, 2026-11-09)
- `NEW_FAMILY_RESEARCH_REGISTER.md` updated with Cycle 75 entry (discovery, scoring, deferred reassessment, H161 pre-registration, lineage map).
- `HYPOTHESIS_SPEC.md` §H161 appended (statement, null, gates, data/splits, costs, falsifiers, pre-registration, lineage).
- No runner executed yet; Cycle 75 discovery + pre-registration complete per directive §4.
- `src/qtr` unchanged; pinned 100% coverage suite not rerun (no `src/qtr` change).
- Dependencies present (numpy/pandas/scipy/pytest/ruff/yfinance).

## 3) Remains unresolved
- H85–H160 all REJECTED/recorded. H161 pre-registered, not yet executed. Lineage gaps H24/H68–H73/H76–H79 unassigned (not recycled). No commit/push performed in this session.
- Deferred/held (no silent drops): NF-04 blocked (no free PIT term-structure/roll proxy); NF-05/07/08/10/11/13/15/20/21 deferred (NF-17 H154, NF-20 H110); NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-01→H149; NF-06-03/23/24/28/30/32/33/35 deferred (NF-06-28 legacy runner/test no artifact, credit adj H94/H108); NF-07-05 data blocker; NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (corr H96/H127/H134/H137); NF-07-52→H148; NF-08-04/05/07/08/10 deferred/held; NF-08-13 ES-SPY basis stub/deferred; NF-08-16 Halloween held (3.90, calendar adj H91/H140/H142); NF-08-20 IEF RV stress deferred (3.50, adj H151/TLT RV maturity); NF-08-21 UNG-USO relmom deferred (3.30); NF-08-22 EFA-EEM relmom deferred (3.55, relmom-class/H144 adj); NF-08-23 USO oil-price→SPY lead-lag deferred (3.25); NF-20261108-26 GLD RV stress deferred (3.50, adj H151/H149); **NF-20261108-29 cross-asset return dispersion deferred (4.10, carried forward)**; **NF-20261109-03 breakeven inflation deferred (3.95)**; **NF-20261109-04 HYG momentum deferred (3.95)**.
- Search space heavily depleted (H85–H160 all rejected); Cycle 76 must complete ≥3-candidate, ≥3-category discovery before selecting H162. NF-08-29/NF-09-03/NF-09-04 are carried-forward candidates but must be honestly re-assessed alongside ≥2 other repo-new mechanisms.

## 4) Approaches that failed (do not blindly repeat)
- H160 (cross-sectional IVOL dispersion, Cycle 74) failed Sharpe/PF/worst-regime/benchmark; random-exposure much weaker (structure) but inverse ≈ base (direction falsified) and return-dispersion control ≈ base (IVOL adds no info beyond return dispersion). Do not rerun same construction.
- H159 (VVIX-VIX spread, Cycle 73) failed Sharpe/PF/trades/worst-regime/benchmark/IR; perturbation-stable but no edge. Do not rerun same construction.
- Do not reuse NF roots without integrity check (see H99/H149 collision precedent). Verify runner/artifact/H-ID mapping before selection.
- NF-08-13 ES-SPY basis stub only (not decision-ready). NF-06-28 legacy runner/test but no artifact (credit adjacency H94/H108). NF-08-20 IEF RV adjacent to H151 — must justify maturity separation if selected. NF-08-22 EFA-EEM relmom adjacent to relmom class/H144. NF-08-29 adjacent to H118 — must justify cross-asset vs within-equity separation if selected.
- NF-09-02 (H161) FX-channel adjacency to H95/H103/H106/H129/H134 — must justify G10 carry basket separation if executed; do not claim wholly unrelated mechanism.

## 5) One precise next task (Cycle 75 execution / H161)
Implement and execute **H161** (NF-20261109-02, G10 currency carry basket risk-appetite timing):
1. Create runner `run_nf_20261109_02_g10_carry.py` following H160 template (pre-registered statement, 48-combo grid, train-only 4-fold WF selection, 8 OOS gates, ablations, falsifiers, isolated per-experiment cache).
2. Create focused tests `tests/test_nf_20261109_02_g10_carry.py` (10 tests covering data fetch, signal construction, grid search, walk-forward selection, gate evaluation, perturbation, ablations, artifact writing).
3. Run `python -m ruff check run_nf_20261109_02_g10_carry.py tests/test_nf_20261109_02_g10_carry.py` and `python -m ruff format --check` on new files.
4. Run `PYTHONPATH=src python -m pytest -q tests/test_nf_20261109_02_g10_carry.py` — all 10 must pass.
5. Execute `PYTHONPATH=src python run_nf_20261109_02_g10_carry.py` — record REAL verdict/artifacts in `.experiments/nf_runs/nf_20261109_02_g10_carry/`.
6. Update `HYPOTHESIS_SPEC.md` §H161, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 75 execution section, `NEXT_TASK.md`, `HANDOFF_NEXT.md` with REAL result.
7. Justify independence from rejected classes including all FX families (H95/H103/H106/H129/H134), credit families (H94/H108/H146), vol families (H100/H104/H105/H158/H159/H160), and all prior listed classes.
8. Free/public data only; no gate weakening; no published/certified artifact modification; no commit/push unless explicitly authorized. If `src/qtr` is touched, rerun pinned 100% coverage suite (`python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`).