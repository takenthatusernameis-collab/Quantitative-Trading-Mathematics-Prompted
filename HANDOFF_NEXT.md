# Agent Handoff — For the next agent

## State you are inheriting
The repo is at **HEAD `28a3b69`** (with H25 committed at `cecc9d5`). Everything through
H25 is committed and verifiable. The **task the previous (stale) handoff assigned —
"H24a: PF-margin-targeted re-selection on the H22 basket" — is already done** (it is H25:
PASS 9/9, OOS Sharpe 1.324, PF 1.320, DD -11.9%, perturbation-robust 0.946, seed 42).
Do NOT redo it. The previous handoff files said "319 tests, H24a pending" — that is
stale; the real baseline is **354/354 tests** (see `HANDOFF.md` for the full diff
between then and now).

## What this session just did (so you don't repeat it)
Ran a **H25 Robustness bootstrap-CI audit** (post-hoc, mirrors H13's audit of H10;
does NOT re-select on Test, does NOT weaken any gate):
- `run_h25_pf_robustness.py` reuses `run_h13.bootstrap_profit_factor_distribution` +
  `run_h11.bootstrap_sharpe_distribution` (i.i.d., `default_rng(42)`, 2,000 resamples)
  on the H25 OOS slice (Val+Test, n=5,148, via H25 `_splits`).
- Result (committed in `.experiments/artifacts/pf_robustness/summary.json`):
  **PF 95% CI [1.2049, 1.4425], P(PF≥1.3)=0.6215; Sharpe 95% CI [0.8834, 1.7506],
  P(Sharpe≥1.0)=0.9275.** H25 stays PASS 9/9 but is **CI-fragile** on PF (the margin
  +0.020 is inside the ±0.120 CI half-width).
- `tests/test_h25_pf_robustness.py` (12 tests) pins everything to the committed
  artifact at 1e-9 and asserts determinism. Full suite: **354/354 passing**, ruff clean
  on both new files.

## Precise next task (your call, but these are the only two that aren't re-treading exhausted ground)
The free-data hypothesis space is **exhausted** (H1-H25, H15 probe). The sole passing
edge family (intraday futures TSMOM: H10/H11/H22/H25) is real but **qualified/CI-fragile**
on the ~730-hour free window. So the only non-redundant next steps are:

1. **H25 Robustness — block-bootstrap sensitivity (FREE data, bounded, ~high-value).** Confirm the i.i.d. CI is not anti-conservative under time-series dependence by adding a stationary (Politis-White) block bootstrap alongside the i.i.d. baseline. Expected: either the CI widens (reinforcing "fragile") or stays (reinforcing "point-robust"). Reuse H13's i.i.d. as baseline; the change is in the audit only. Deliverable: extend `run_h25_pf_robustness.py`, add tests, commit. Pre-register the interpretation threshold (block-boot CI LB vs i.i.d. CI LB) in `HYPOTHESIS_SPEC.md` before running. **This is the safest next task and stays fully in free data.**
2. **Acquire paid hourly futures data (NEEDS BUDGET/APPROVAL — out of free-data scope).** The audit pins the target: the PF CI half-width (±0.120) must shrink ~3-4x for P(PF≥1.3) ≥ 0.90, which needs ~3-4x more bars (≈2-3 years of hourly `=F`, e.g. Databento/Polygon/CMC). Re-run H25's pipeline verbatim (`run_h25_futures_tsmom_pfmargin.py`) on the longer window, then re-run `run_h25_pf_robustness.py`. **Do NOT** run any new free-data hypothesis — H1-H25 already prove free-data families land at Sharpe 0.2-0.8 / CI-fragile PF < 1.3.

## Constraints handed down
- No paid data available in this session (free only); respect the ≤2 CPU-h budget.
- Do NOT weaken gates (PROMPT_V2 §H15): the honest outcome is "qualified pass, CI-fragile,"
  not a forced pass.
- Do NOT re-run/repurpose committed H25 artifacts or tests — they're pinned at 1e-9.
- Commit-per-experiment convention; exclude `.pyc`.

## Files added this session (committed)
- `run_h25_pf_robustness.py`, `tests/test_h25_pf_robustness.py`
- `.experiments/artifacts/pf_robustness/{summary.json, pf_bootstrap.parquet, sharpe_bootstrap.parquet}`
- Edits to `HYPOTHESIS_SPEC.md`, `INEFFICIENCY_RANKING.md`, `FINAL_REPORT.md`, `NEXT_TASK.md`, `HANDOFF.md`, `HANDOFF_NEXT.md`.

Run `python -m pytest -q` and `python -m ruff check run_h25_pf_robustness.py tests/test_h25_pf_robustness.py` to confirm the green baseline before starting.
