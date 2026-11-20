# Next session handoff (2026-11-20, Cycle 230 — H187 pre-registered, ready to execute)

## Summary

Cycle 230 measured the SEC XBRL `companyfacts` source across the full 100-name S&P 100 universe
and **pre-registered H187** (NF-20261120-01, equity accounting accruals + asset growth) in
`HYPOTHESIS_SPEC.md` §Cycle 230. The "free-data family queue exhausted" conclusion is withdrawn
for accounting fundamentals: 98/100 names yield ≥2 usable PIT accrual observations with a
50.75-day median filing lag.

## Verified (2026-11-20, own evidence)

- Full probe: 100/100 bundles, 99 with annual rows, **98 usable**, lag 50.75 d, PIT span
  2009-10-27 → 2026-11-17. Exclusions measured: XOM (2026 successor entity) and BKNG (tag gap).
- Workflow token refusal is now evidenced by a real remote rejection, not inferred.
- 131 spec-reading tests passed; ruff check/format clean (354 files).

## Blocked (separate, unchanged)

1. **Workflow patch** — maintainer-only; the agent token is refused by GitHub for workflow files.
2. **Reproducibility backlog** (25 missing / 11 mismatches) — authorization-gated; baseline,
   both identity digests and `REPRODUCIBILITY_AUDIT_REPORT.md` must move in one commit.

## Next session should

**Execute H187 exactly as pre-registered**: write `run_nf_20261120_01_equity_accruals.py`
importing the probe's `annual_observations`, reuse the H186 runner's engine/gate/benchmark
helpers, run the fixed 16-combo grid with train-only WF selection, emit the artifact under
`.experiments/nf_runs/nf_20261120_01_equity_accruals_<timestamp>/`, add the focused test, bump the
artifact-schema inventory pins, and record the verdict as Cycle 231. Full instructions and
constraints are in `NEXT_TASK.md`.

## HEAD

`49e74c4` at session start; this session adds documentation-only changes (spec, register,
`AGENTS.md`, handoffs).
