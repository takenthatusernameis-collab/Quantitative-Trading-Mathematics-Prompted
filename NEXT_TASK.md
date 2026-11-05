# NEXT_TASK.md — H87 (NF-20261105-01 opening-gap fill) complete — REJECT

H87 implemented in `run_nf_20261105_01_opening_gap.py` with focused tests in
`tests/test_nf_20261105_01_opening_gap.py`. Formalized in HYPOTHESIS_SPEC.md §H87
and registered in NEW_FAMILY_RESEARCH_REGISTER.md §8–9.

Result: **REJECT (1/9 gates).** OOS Sharpe = −0.348, PF = 0.940, max DD = −40.4%,
0 OOS trades, IR = −0.577 vs SPY benchmark. Selected config: lookback 5,
zscore_thresh 0.0, vol_target 0.15. Experiment `exp_2026-11-05T11-33-50-642571Z`.

Runner fixes applied:
- Replaced bare `bench_p <= GATES["max_p_value"]` with `benchmark_significance_gate(bench_p, ir)` (H34 direction-aware gate contract).
- Replaced noise-based perturbation_eval with OAT ±20% parameter sensitivity (lookback, zscore_thresh, vol_target).

All nf-focused tests pass; ruff lint and format clean. Two pre-existing failures in
`run_nf_20261104_01_vix_termstructure.py` remain (bare p-value comparison and
non-evaluating worst_regime_sharpe gate) — not part of H87 scope.

Next: Per directive §6, H1–H30 exhausted and H85/H86/H87 all rejected. A new
mechanism search across distinct return-generating categories is required before
selecting the next experiment. Next unused H-ID is H88.