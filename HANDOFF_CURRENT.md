# HANDOFF — H34: benchmark gate re-specified as one-sided (2026-10-20)

## What changed

H34 — pre-registered re-specification of the benchmark-significance gate as one-sided (strategy > benchmark) to avoid passing when alpha is significantly negative. No published artifacts, runner gates, thresholds, verdicts or certified numbers were modified; no grid was re-run. The published rows remain as the historical record.

### New
- (No new code yet - this is pre-registration; specification changes to be applied in code as needed)

### Changed
- `HYPOTHESIS_SPEC.md` — added H34 pre-registration
- `NEXT_TASK.md` — updated to reflect H34 as current task
- `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md` (created/updating)

## What was actually verified

- Reviewed benchmark gate implementation: `compare_to_benchmark()` in `src/qtr/validation/statistics.py` already computes `alpha_p_value_one_sided` (strategy > benchmark when t>0, else 1.0 - p/2.0). Many runners (H9, H10, H16, H17, H19, H20, H23) already read `alpha_p_value_one_sided`.
- Confirmed direction issue: two-sided p passes when significantly negative (e.g. H19 IR -0.88 p=0.0026, H20 IR -0.704 p=0.0159, H23 IR -3.07 p=0.0009).
- Verified no grids rerun; no artifacts modified.

## What remains unresolved

- Apply one-sided gate consistently across all families with p-gates (ensure all use one-sided).
- For families that currently pass for negative alpha under two-sided, gate should fail under one-sided (p >= 0.05). Certified families (H10, H22, H25) pass with positive IR and remain valid under one-sided.
- Dead code: `deflated_sharpe_ratio` in `src/qtr/validation/statistics.py` is unreachable (not exported, no calls). Need to settle (remove or document/export). The H32 coverage claim was wrong (baseline 94%, not 99%).

## Approaches that failed / were not taken

- Re-running grids (forbidden).
- Modifying published artifacts/rows (forbidden).
- Changing thresholds or verdicts for published results (forbidden).

## One precise next task

Implement consistent one-sided benchmark gate application (prefer reading `alpha_p_value_one_sided` from library where available), document the change, and report the direction-positive pass table for all families with p-gates (H4, H6, H7, H9, H10, H16, H17, H18, H19, H20, H22, H23, H25). Do not modify published results. Address dead `deflated_sharpe_ratio` in statistics.py.
## H34 — Direction-positive benchmark p-gate analysis (offline, from committed artifacts; no re-runs, no published rows modified)

For each family with a p-gate (H4, H6, H7, H9, H10, H16, H17, H18, H19, H20, H22, H23, H25), recomputed via `compare_to_benchmark` from committed artifact equity/benchmark equity (where available) or using repaired published values from H33 where direct artifact reconstruction not unambiguous. The one-sided p is `alpha_p_value_one_sided` (strategy > benchmark): equals p_two_sided/2 if t>0, else 1 - p_two_sided/2.

| Family | IR (from artifacts/published record) | alpha sign | p_two_sided (approx/recomputed) | p_one_sided (strategy>bench) | Pass under two-sided (p<0.05)? | Pass under one-sided (p<0.05 AND alpha>0)? |
|---|---|---|---|---|---|---|
| H4 | +0.3315 | positive | 0.4592 | ~0.230 | False | False |
| H6 | (as published) | — | — | — | (not directly measured from artifacts shown; treat as per gates in runners) | — |
| H7 | +0.3002 (repaired) | positive | 0.3432 | ~0.172 | False | False |
| H9 | ~ -0.235 | negative | ~0.1128 | ~0.944 | False | False |
| H10 | +0.9248 | positive | 4.80e-10 | ~2.40e-10 | True | True |
| H16 | ~ -0.487 | negative | ~0.0594 | ~0.970 | False | False |
| H17 | ~ -0.412 | negative | ~0.1108 | ~0.945 | False | False |
| H18 | -0.5968 | negative | 0.0410 (repaired) | ~0.9795 | True (repaired) | False |
| H19 | -0.8798 | negative | 0.00260 | ~0.9987 | True | False |
| H20 | -0.7040 | negative | 0.01595 | ~0.9920 | True | False |
| H22 | +1.3467 | positive | 1.34e-19 | ~6.68e-20 | True | True |
| H23 (negative-IR case) | -3.0739 | negative | 0.00090 | ~0.9996 | True | False |
| H23 (positive-IR case) | +0.8001 | positive | ~0.383 | ~0.192 | False | False |
| H25 | +1.3459 | positive | 1.40e-19 | ~7.02e-20 | True | True |

Key:
- Families that pass two-sided but fail one-sided due to negative alpha: **H18, H19, H20, H23 (the negative-IR selection)** — exactly as identified.
- Certified families with positive IR: **H10, H22, H25** survive (pass under one-sided).
- This matches the specification in H34.
