# NEXT_TASK.md — Cycle 83 (after H168 REJECT 4/8)

## Status: Cycle 82 complete (H168 executed REAL; REJECT) — Cycle 83 discovery required

## H168 result (REAL, not fabricated) — REJECT 4/8
- Runner `run_nf_20261109_11_spy_index_rebalance.py` + tests `tests/test_nf_20261109_11_spy_index_rebalance.py` (9 passed). `ruff check/format` clean. Artifact `.experiments/nf_runs/nf_20261109_11_spy_index_rebalance/summary.json` (+`grid.csv`, `data_meta.json`, 6.44s).
- OOS Val+Test (n=1717): Sharpe **0.803** fail (≥1.0), trades **700** pass (≥200), PF **1.151** fail (≥1.3), max DD **-3.44%** pass (≤15%), WF stability **0.752** pass (≥0.7; train 1.0674→OOS 0.803), worst-regime **-1.210** fail (≥0.3), benchmark p **0.982** / IR **-0.759** fail (p≤0.05 & IR≥0), perturbation min ratio **0.982** pass (≥0.5).
- Critical falsifier: random-window control **0.839** matches/exceeds base 0.803 → structural-flow mechanism not validated.
- Documented in `HYPOTHESIS_SPEC.md` §H168 (REJECT 4/8, verdict rationale, lineage map) and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 82.

## Lineage
**Lineage:** H85–H168 all rejected/recorded. Next unused H-ID: **H169** (H24/H68–H73/H76–H79 unassigned, not recycled). `src/qtr` unchanged; no published/certified artifact, verdict, threshold, or frozen number modified. Selection/validation uses no protected-test feedback. Free/public yfinance data only. No commit/push unless explicitly authorized.

## One precise next task (Cycle 83 / H169)
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4`:
1. **Reconcile lineage/collisions first (evidence-based):** confirm H85–H168 rejected/recorded, H169 next unused. Confirm no tracked draft collides with H169 (NF-09-06/-07 removed Cycle 79; do not reuse).
2. **Directive §4 discovery scan:** propose **>=3 repo-new/decisive candidates across >=3 broad mechanism categories** with honest 25/25/20/15/10/5 scoring and concrete deferred reassessment (no silent drops). Reassess carried-forward pool with evidence — it is low-expected-information: **NF-04** commodity carry (BLOCKED — no free PIT term-structure/roll proxy), **NF-05** short-term CS reversal (DEFERRED — turnover/net-of-cost; H119 weekly REJECT 3/8), **NF-08-16** Halloween seasonal (held 3.90, calendar adjacency H91/H140/H142), **NF-09-03** breakeven-inflation (data-limited — ^T5YIE/^T10YIE unavailable on yfinance). **Search materially different mechanism categories before recycling.**
   Unexecuted Cycle 82 alternatives remain available for reassessment with evidence: **NF-20261109-12 holiday/pre-holiday drift SPY timing** (calendar microstructure, 4.15 runner-up; honest adjacency to H91/H140/H142/H90 calendar families), **NF-20261109-13 low-volatility factor timing USMV/SPLV vs SPY** (factor anomaly, 3.45; adjacency to H114/H129/H130). Do not blindly select a runner-up — reassess against fresh candidates.
3. **Verify NF roots** against executed H-IDs/artifacts/runners before selection (no collisions; H99/H149/H164-draft precedents).
4. **Pre-register** highest-expected-information **feasible** candidate as **H169** before validation outcomes (decision-ready: mechanism, PIT observable, causal path, null/falsifiers, bounded grid, costs, splits, gates).
5. Implement runner `run_nf_...py` + focused tests `tests/test_nf_...py`; run `python -m ruff check/format --check` on new files and `PYTHONPATH=src python -m pytest -q` focused tests (all pass).
6. Execute REAL; record verdict/artifacts in `HYPOTHESIS_SPEC.md` §H169, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 83, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. **Do not fabricate results.** No gate weakening; no published/certified artifact modification.

## Constraints
- Free/public data only; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect. If `src/qtr` touched, rerun pinned 100% suite: `python -m ruff check src tests run_*.py && python -m ruff format --check src tests run_*.py && PYTHONPATH=src python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`.
- Selection/validation uses no protected-test feedback. All gates fail-closed on pre-registered OOS Val+Test.

## Deferred (no silent drops; full list in NEW_FAMILY_RESEARCH_REGISTER.md)
NF-04 blocked (PIT term-structure/roll); NF-05/07/08/10/11/13/15/17/20/21 deferred; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible (CBOE PC); NF-06-01→H149; NF-06-03/23/24/27/28/30/32/33/35; NF-07-05 data blocker (CPI); NF-07-14/48 held (IV-spread H125/H126); NF-07-49 held (correlation); NF-07-52→H148; NF-08-04/05/07/08/10; NF-08-13 ES-SPY basis stub; NF-08-16 Halloween held (3.90); NF-08-20 IEF RV stress deferred; NF-08-21/22/23 deferred; NF-09-03 breakeven deferred/data-limited; NF-20261109-12/13 unexecuted Cycle 82 alternatives (reassess with evidence).

## Approaches that failed / evidence (do not blindly repeat)
- H166 passed Sharpe (1.105) but failed PF/worst-regime/benchmark; inverse weaker, direction consistent but no edge. Do not rerun same KRE/XLF basket construction.
- H167 failed Sharpe/worst-regime/benchmark/PF; inverse weaker, direction consistent but no edge. Do not rerun same VRP-spread construction.
- H168 failed Sharpe/PF/worst-regime/benchmark; random-window control matches base (0.839 vs 0.803) → structural index-rebalance flow not validated. Do not rerun same quarterly-rebalance-window de-risk construction.
- All H85–H168 rejected on free, point-in-time data. Rejection classes to avoid silently recycling: correlation-regime H96/H127/H134/H137/H165; RV-stress H151/H156/H164; credit H94/H108/H146/H163; dispersion H118/H160/H162; FX H95/H103/H106/H161; VIX-complex H158/H159; VRP H17/H100/H167; carry H161; calendar-seasonal H91/H140/H142/H90/H168.
