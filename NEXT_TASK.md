# NEXT_TASK — Cycle 41 discovery / pre-register & execute H127

Cycle 40 completed: H126 **REJECT 2/8** (NF-20261107-13 cross-asset gold-vs-equity implied-vol spread timing SPY, `GVZ−VIX`; `.experiments/nf_runs/nf_20261107_13_gvz_vix_spread/summary.json`). H85–H126 all rejected/recorded. `src/qtr` unchanged.

Cycle 41 discovery required per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §4` and `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 40 tail:
1. Reconcile lineage to H126; propose >=3 repo-new mechanism candidates across >=3 broad categories with honest adjacency notes; score 25/25/20/15/10/5.
2. Reassess deferred candidates NF-04/05/07/08/10/11/13/15/17/20/21, NF-11r/NF-06-18 (TNX-FVX, SAME root as NF-11 — not a new root), NF-06-11 (infeasible), NF-20261106-03/23/24/28/30/32/33/35, NF-20261107-05 (CPI event drift), and held NF-20261107-11 (cross-sectional IVOL spread timing — PIT separation from H93), NF-20261107-12 (credit-vs-equity vol divergence — separation from H94/H100/H125), NF-20261107-14 (OVX−VIX energy-options spread — same construction class as H125/H126, materially different design required), NF-20261107-15 (GLD–TLT correlation regime — adjacent to H96, different pair) with concrete evidence (no silent drops). NF-20261107-13/H126 executed/rejected — do not rerun without materially different pre-registered construction.
3. Pre-register highest-expected-information feasible candidate as **H127** in `HYPOTHESIS_SPEC.md`; record in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 41.
4. If decision-ready with free/public data and no `src/qtr` change: implement runner + focused tests, ruff clean, execute, record verdict (OOS Val+Test only). Do not weaken gates or modify published/certified artifacts.

Next unused H-ID: **H127** (H24/H68–H73/H76–H79 unassigned, not recycled). Free/public data only; no gate weakening; no commit/push.
