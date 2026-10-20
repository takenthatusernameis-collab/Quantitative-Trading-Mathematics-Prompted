# HANDOFF_NEXT — H34 next steps

## Immediate
1. Ensure benchmark gate uses one-sided p-value (strategy > benchmark). Library already provides `alpha_p_value_one_sided`; runners that use `alpha_p_value` (two-sided) need updating where they gate on significance.
2. For families that gate: check each runner - some already use one-sided (H9/H10/H16/H17/H19/H20/H23). H4 uses `alpha_p_value` from bench result? Let us look up how H4 does it.
3. Recompute offline: for each family, with one-sided p, does it pass significance? Report table. Do not change published artifacts.
4. Settle `deflated_sharpe_ratio` in `src/qtr/validation/statistics.py` - either remove if truly dead/unnecessary, or export if used. It's duplicated in `run_h12_selection_bias_audit.py`. Better to remove dead code to clean up coverage.

## Constraints
- No re-runs, no changes to published numbers/verdicts
- Pre-register done
- All changes must be verifiable with tests
