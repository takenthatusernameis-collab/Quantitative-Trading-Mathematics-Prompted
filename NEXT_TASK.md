# NEXT_TASK.md — Cycle 23 discovery / pre-registration of H109

Cycle 22 executed H108 (NF-20261106-19 LQD-HYG credit-quality dispersion) — REJECT 4/8 (exp_2026-11-06T14-46-17-382075Z). src/qtr unchanged.

Cycle 23 discovery: reconcile lineage to H108 (H85–H108 rejected). Three candidates proposed:
1. NF-20261106-17 XOP/XLE energy-sector relative-strength / supply-shock transmission timing SPY (sectoral supply-shock) — selected as H109 (repo-new root family distinct from H98/H101 commodity-vol/growth).
2. NF-20261106-18 TNX-FVX Treasury term-slope (deferred, NF-11 resolution path, honest lower novelty).
3. NF-20261106-03 VVIX vol-of-vol (deferred, VIX-complex adjacency).

Deferred candidates NF-04/05/07/08/10/11/13/15/17/20/21 and NF-11r reassessed with concrete evidence; NF-06-11 CBOE PC ratio infeasible. NF-20261106-17 XOP/XLE reassessed/selected.

Pre-register H109 in HYPOTHESIS_SPEC.md + register Cycle 23; smallest decisive test: trailing XOP/XLE relative-strength z-score → vol-targeted long SPY reduced when energy sector abnormally weak, 1-bar delay, free yfinance XOP/XLE/SPY. No gate weakening.

Next: implement run_nf_20261106_17_xop_xle_energy.py + tests, ruff, pytest, execute, record verdict.
