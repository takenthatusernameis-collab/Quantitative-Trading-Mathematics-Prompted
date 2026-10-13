# Next Task: Extend H10-family robustness beyond the current data horizon (bounded, data-dependent)

## Status of previous work
H10 (intraday TSMOM PF-optimized) passed all pre-registered gates. H11 confirmed frozen-pipeline reproducibility and robustness (bit-exact splits). H12 (selection bias audit) showed Sharpe/deflation robustness and PBO consistent with signal; selection artifacts do not explain the edge. H13 (OOS deflation + PF-margin fragility audit) found: worst-case DSR-adj OOS Sharpe 1.2745, p = 0.00102 (PASS for deflation) but OOS PF bootstrap 95% CI [1.190, 1.425], P(PF ≥ 1.3)=51.7% (FAIL) and symbol dispensability failed (CL=F, GC=F indispensable). H14 (PF-margin-targeted selection audit, top-K=50 by Val PF margin, excluding H10) found 0/50 configs passed all three gates (all DSR≥1.0 but CI LB max 1.199 and none fully dispensable) — verdict REJECT; PF-margin fragility is a family property on the available window.

Evidence/artifacts: H13 `.experiments/artifacts/exp_2026-10-13T14-35-58-316759Z/`, H14 `.experiments/artifacts/exp_2026-10-13T19-01-59-371405Z/`. Scripts: `run_h13_oos_deflation_pf_audit.py`, `run_h14_pf_margin_selection_audit.py`. Tests: 109/109 passing (including new `tests/test_h14_artifacts.py`).

## What changed in this session
- Added `tests/test_h14_artifacts.py` to validate H14 artifacts (schema, gates, counts).
- Verified full test suite passes (109/109). Clean working tree (no uncommitted source changes).

## What was verified
- All existing tests still pass (including H13, H11, H12, H10, core unit tests).
- H14 artifact invariants verified: 50 configs evaluated, 0 passing, DSR≥1.0 for all, CI LB<1.3 for all, all_symbols_dispensable all False.
- Code compiles; scripts execute logic as written.

## What remains unresolved
- PF-margin fragility is a structural property on ~730-day hourly window (free yfinance hard cap on `=F` series). The margin (+0.004 over 1.3) is smaller than bootstrap noise and depends on CL=F, GC=F loss-offsetting.
- Data horizon constraint: cannot extend free hourly `=F` beyond ~2026-10-09; longer OOS window requires paid data source.
- No config in PF-margin-top-50 family satisfies all H13 gates; remedies untested with extended data.

## Approaches already failed and why
- PF-margin-targeted selection over top-K by Val PF margin (H14): failed because dispensability/blocker symbols persist; Sharpe deflation not the issue.
- Bootstrap CI gate alone (H13) fails due to sampling noise relative to thin margin.

## One precise next task (bounded, verifiable)
Implement a bounded feasibility probe: assess whether extending the evaluation window (via an alternate data adapter/path, with clear data provenance and no recomputation of frozen artifacts) could plausibly move PF bootstrap CI LB ≥ 1.3 while preserving symbol dispensability. 
Constraints:
- Do not change frozen pipeline logic or committed H10/H11/H12/H13/H14 artifacts.
- If paid/alternate data unavailable in this environment, produce a structured feasibility report (with required fields: data source, available bars, split feasibility, estimated power/CI width impact, assumptions, risks) that can be evaluated without running full grid.
- Verification: produce a single markdown/report file under `.experiments/probes/` with all required fields, and a minimal unit test that validates the report schema. Keep runtime < 0.01 CPU-h, no external network fetches if data not present.
- If alternate data found, validate shape and coverage only (read-only), do not overwrite existing artifacts.

## Evidence/constraints
- Data cap: free yfinance hourly `=F` ~730 days (no bars beyond 2026-10-09).
- H13 gates: PF CI LB≥1.3, worst-case DSR-adj SR≥1.0, all symbols dispensable.
- Family property established (H14). Changes must be reversible and non-destructive.
