# NEXT_TASK.md — Cycle 86 (after H171 REJECT 4/8)

## Status: Cycle 85 complete (H171 executed REAL; REJECT) — Cycle 86 discovery required

## H171 result (REAL, not fabricated) — REJECT 4/8
- Runner `run_nf_20261109_21_yield_curve_slope_spy.py` + tests `tests/test_nf_20261109_21_yield_curve_slope_spy.py` (9 passed). `ruff check/format` clean. Artifact `.experiments/nf_runs/nf_20261109_21_yield_curve_slope_spy_20261109_155438/summary.json` (+`grid.csv`, `data_meta.json`, 5.23s).
- Data (PIT, free yfinance): ^TYX/^FVX/SPY daily auto-adjust Close, 4231 aligned rows 2010-01-04→2026-10-30 (train 2010-01-01→2019-12-31, val 2020-01-01→2022-12-31, test protected 2023-01-01→2026-10-31).
- OOS Val+Test (740 trades): Sharpe **0.903** fail (≥1.0), PF **1.224** fail (≥1.3), max DD **-5.75%** pass (≤15%), trades **740** pass (≥200), WF stability **1.153** pass (≥0.7), worst-regime rolling-252 **-1.006** fail (≥0.3), benchmark p **0.971** / IR **-0.725** fail (p≤0.05 & IR≥0), perturbation min ratio **1.286** pass (≥0.5).
- Selected (train-only 4-fold WF mean Sharpe 0.874): `z_window=126, entry_scale=2.0, vol_target=0.15`.
- Ablations OOS: buy-hold SPY 0.791/1.164/-17.97%/1; random-exposure-matched **0.620**/1.183/-2.73%/861 (weaker, some structure); inverse regime (de-risk when slope steep/positive z) **0.336**/1.071/-3.93%/844 — much weaker (direction supported, no benchmark edge).
- Honest adjacency: repo-new executed *yield curve slope* (^TYX-^FVX 30Y-5Y) observable; adjacent rates-domain families H141/H154/H155/H100 — different observable/instrument type/mechanism. No validated edge.
- Documented in `HYPOTHESIS_SPEC.md` §H171 and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 85.

## Lineage
**Lineage:** H85–H171 all rejected/recorded. Next unused H-ID: **H172** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public yfinance data only. No commit/push unless explicitly authorized.

## One precise next task (Cycle 86 / H172)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions first (evidence-based):** confirm H85–H171 rejected/recorded, H172 next unused. Confirm no tracked draft collides with H172.
2. **Directive §4 discovery scan:** propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). **Search materially different mechanism categories before recycling.** Heavily executed categories to treat with high adjacency scrutiny: calendar/seasonal (H91/H140/H142/H168/NF-12), credit/macro rates regime/shape (H94/H95/H100/H141/H146/H154/H155/H163/H171), correlation/regime (H96/H127/H134/H137/H165), RV-stress/realized-moment (H122/H128/H132/H135/H143/H149/H151/H156/H164), dispersion (H118/H160/H162), FX (H95/H103/H106/H161), VIX-complex/VRP/vol-shape (H86/H89/H104/H113/H123/H126/H131/H158/H159/H167), carry (H161), overnight futures lead-lag (H169), leveraged ETF flows (H170), relmom (H144/H145/H152/H157), breadth/beta/IVOL cross-sectional (H117/H129/H130).
3. **Reassess carried-forward/deferred pool with evidence (no silent drops):** NF-20261109-15 tax-loss harvesting (4.20 reassessed; constituent/YTD-loser universe construction decisive risk on free yfinance), NF-20261109-16 dividend capture (3.95; microstructure/event alignment/overnight-open costs), NF-20261109-22 RSP-SPY breadth relmom (3.75; adjacency to H97 same pair — different mechanism must be explicit), NF-20261109-23 USMV-SPY low-vol relmom (3.55; 2011 inception/style adjacency), NF-20261109-12 holiday drift (4.00; calendar adjacency), NF-20261109-18 S&P inclusion/deletion discrete (3.90; low frequency/external data), NF-20261109-19 options dealer GEX (3.50; options construction complexity), NF-20261109-20 stock split (3.10), NF-04 blocked (PIT term-structure/roll), NF-05 deferred (turnover/net-of-cost), NF-08-16 held (Halloween), NF-09-03 deferred/data-limited (breakeven). Do not blindly select a runner-up.
4. **Verify NF roots** against executed H-IDs/artifacts/runners before selection (no collisions; H99/H149/H164-draft precedents).
5. **Pre-register** highest-expected-information **feasible** candidate as **H172** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
6. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
7. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H172, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 86, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Approaches that failed / evidence (do not blindly repeat)
- H171 failed Sharpe/PF/worst-regime/benchmark; inverse much weaker (direction supported) but no edge. Do not rerun same ^TYX-^FVX slope construction without materially different mechanism.
- H170 failed Sharpe/PF/worst-regime/benchmark/perturbation; random flow comparable. Do not rerun leveraged ETF rebalancing flow construction.
- H169 failed Sharpe/PF/worst-regime/benchmark. Do not rerun overnight futures lead-lag construction.
- H168 failed Sharpe/PF/worst-regime/benchmark; random-window control matched base. Do not rerun quarterly index-rebalance window de-risking.
- H166/H167 VRP/KRE-XLF constructions failed benchmark/worst-regime families.
- All H85–H171 rejected on free, point-in-time data. Avoid silent recycling of exhausted construction classes without a *materially different* mechanism/observable and explicit novelty justification.

## Deferred (no silent drops; full list in NEW_FAMILY_RESEARCH_REGISTER.md)
NF-04 blocked (PIT term-structure/roll); NF-05 deferred (turnover/net-of-cost); NF-08-16 held (Halloween/calendar adjacency); NF-09-03 deferred/data-limited (breakeven ^T5YIE/^T10YIE unavailable); NF-20261109-12/13/15/16/18/19/20/22/23 unexecuted alternatives reassessed with evidence (see Cycle 85 register). NF-07/08/10/11/13/15/17/20/21 and other long-standing deferred items remain as previously recorded — reassess with concrete evidence before recycling.
