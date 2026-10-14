# Agent Handoff — For the next agent

## State you are inheriting
The repo is at **HEAD `987a44a`** (H25 Robustness audit committed at `6c15e34`,
with a later `987a44a` touching only `summary.json`). Everything through H25 is
committed and verifiable. The real baseline is **354/354 tests**.

## What this session just did (so you don't repeat it)
Found and fixed a real defect in the committed `run_h25_pf_robustness.py`: it
contained **8 duplicate top-level `main()` definitions** (728 lines; canonical is
286). Python uses the last one, so behavior was unchanged — but the file was
dead-code bloat. Removed the 7 redundant copies; verified the cleaned script
reproduces the committed `summary.json` byte-for-byte (excluding the wall-clock
`elapsed_sec`) and that the full suite still passes at 354/354. ruff clean on both
files. No logic, imports, or output changed. Working tree now has only
`run_h25_pf_robustness.py` (−442 lines) and a regenerated `summary.json`
(`elapsed_sec` 57.338 → 57.087) as non-`.pyc` changes.

## Precise next task (your call)
The free-data hypothesis space is **exhausted** (H1-H25, H15 probe). The sole
passing edge family (intraday futures TSMOM: H10/H11/H22/H25) is real but
**qualified/CI-fragile** on the ~730-hour free window. The only two non-redundant
next steps are:

1. **H25 Robustness — block-bootstrap sensitivity formalization (FREE data,
   bounded, ~high-value).** The block bootstrap is **already implemented** in
   `run_h25_pf_robustness.py` (`stationary_block_bootstrap`,
   `_optimal_block_length_pwh`, block-bootstrap parquets + CI in
   `summary.json`: PF block CI [1.2046, 1.4458], P(PF≥1.3)=0.6460; block
   length selected = 2) — it just was never pre-registered or interpreted as a
   formal hypothesis. To make it a real task: pre-register the interpretation
   threshold (block-boot CI LB vs i.i.d. CI LB) in `HYPOTHESIS_SPEC.md`, add
   tests pinning the block-bootstrap outputs, and interpret the result. With
   block length 2 the block CI is nearly identical to i.i.d. (both LB ≈ 1.205),
   so the honest conclusion is that time-series dependence does not rescue the
   PF margin — the fragility stands. Deliverable: tests + committed artifact +
   doc update. **This is the safest next task and stays fully in free data.**
2. **Acquire paid hourly futures data (NEEDS BUDGET/APPROVAL — out of free-data
   scope).** The audit pins the target: the PF CI half-width (±0.120) must shrink
   ~3-4x for P(PF≥1.3) ≥ 0.90, which needs ~3-4x more bars (≈2-3 years of hourly
   `=F`, e.g. Databento/Polygon/CMC). Re-run H25's pipeline verbatim
   (`run_h25_futures_tsmom_pfmargin.py`) on the longer window, then re-run
   `run_h25_pf_robustness.py`. **Do NOT** run any new free-data hypothesis —
   H1-H25 already prove free-data families land at Sharpe 0.2-0.8 / CI-fragile
   PF < 1.3.

## Constraints handed down
- No paid data available in this session (free only); respect the ≤2 CPU-h budget.
- Do NOT weaken gates (PROMPT_V2 §H15): the honest outcome is "qualified pass,
  CI-fragile," not a forced pass.
- Do NOT re-run/repurpose committed H25 artifacts or tests — they're pinned at
  1e-9 (the audit's point estimates reproduce H25 `summary.json` exactly).
- Commit-per-experiment convention; exclude `.pyc`.

## Files changed this session (NOT yet committed)
- `run_h25_pf_robustness.py` — 728 → 286 lines (removed 7 duplicate `main()` defs).
- `.experiments/artifacts/pf_robustness/summary.json` — regenerated (only
  `elapsed_sec` differs).
- `HANDOFF.md`, `HANDOFF_NEXT.md` — this session's record.

Run `python -m pytest -q` and `python -m ruff check run_h25_pf_robustness.py
tests/test_h25_pf_robustness.py` to confirm the green baseline (354 passed, ruff
clean) before starting.