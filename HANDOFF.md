# Agent Handoff — Session outcome

## Summary
Executed the task assigned by the previous agent. **The assigned task (H24a:
PF-margin-targeted re-selection on the H22 basket) was already executed and
committed as H25** (commit `cecc9d5` + `28a3b69`, HEAD) — 9/9 gates PASS
(OOS Sharpe 1.324, PF 1.320, DD -11.9%, perturbation min ratio 0.946, seed 42),
342 tests passing, ruff clean. The prior handoff files were stale (they still
listed H24a as pending at 319 tests). I verified that H25 fulfills H24a and
closed both deviations that H21 had flagged "for H22 to correct" (the
`val_sharpe` mislabel and the missing ±20% perturbation gate).

I then executed the **bounded, high-value remaining task**: a statistical
robustness characterization of the certified H25 edge (H25 Robustness audit),
mirroring the H13 audit of H10, directly filling the project's own documented
gap ("the PF margin is narrow (+0.020) and inside the bootstrap CI noise floor").

## Incoming state (prior agent)
- H1-H23 consolidated; H22/H23/H24 committed; FINAL_REPORT/INEFFICIENCY_RANKING updated.
- H25 executed & committed (cecc9d5, 28a3b69): PASS 9/9 gates.
- 342/342 tests; ruff clean on committed H25 files.
- Data walls intact: yfinance hourly `=F` ~730 days; Coinbase/CCXT hourly crypto ~12 days.

## What changed
- `run_h25_pf_robustness.py` (new) — reuses `run_h13.bootstrap_profit_factor_distribution`
  + `run_h11.bootstrap_sharpe_distribution` (i.i.d., `default_rng(42)`, 2,000 resamples)
  to compute the OOS PF/Sharpe 95% CIs, P(PF≥1.3), P(Sharpe≥1.0) for the committed H25
  selected config. Deterministic; reads `exp_2026-10-14T20-08-34-613690Z`, writes
  `.experiments/artifacts/pf_robustness/`.
- `tests/test_h25_pf_robustness.py` (new, 12 tests) — pre-registration pins, determinism,
  point-estimate reproduction of H25 `summary.json` at 1e-9, committed-artifact fidelity
  at 1e-9, CI sanity, executed-characterization pins.
- `.experiments/artifacts/pf_robustness/` (new, committed) — summary.json + bootstrap
  parquets.
- `HYPOTHESIS_SPEC.md` — §H25 addendum (pre-registered + measured).
- `INEFFICIENCY_RANKING.md` §H25 + §17 — CI-qualified the PF fragility; test count 354.
- `FINAL_REPORT.md` — H25 table row, qualified-edge note, H1-H25 statistics (354 tests).
- `NEXT_TASK.md` — appended accurate H25 Robustness audit outcome + honest handoff.

## What was actually verified
- `python -m pytest -q` → **354/354 passed** (342 prior + 12 new).
- `ruff check run_h25_pf_robustness.py tests/test_h25_pf_robustness.py` → All checks passed.
- `python run_h25_pf_robustness.py` → idempotent (re-run reproduces identical summary.json).
- Audit point estimates reproduce H25 `summary.json` exactly (PF 1.3201316886422707, Sharp 1.3236288879255962).
- Confirmed neither H21 flagged deviation recurs: `val_sharpe` correct (H25 line 569),
  perturbation gate present + PASS (line 433).
- Git status: clean except pre-existing `.pyc` churn (gitignored).

## Executed H25 Robustness result (the new finding)
- OOS PF 1.3201 (≥ 1.3 ✓ point), **95% CI [1.2049, 1.4425]**, **P(PF≥1.3)=0.6215**
  → point-wise pass but CI-fragile (LB < 1.3), confirming the documented fragility with
  numbers (PF CI half-width ≈ ±0.120 vs the +0.020 margin).
- OOS Sharpe 1.3236 (≥ 1.0 ✓), 95% CI [0.8834, 1.7506], P(Sharpe≥1.0)=0.9275
  → point-robust.
- Verdict classification unchanged: **PASS 9/9 on the registered gates**, but **qualified**
  (CI-fragile PF) — the same qualified-certification status H13 assigns H10.

## What remains unresolved
- H25 (the H24a assignment) is complete and committed — nothing left.
- The project's own declared next step (paid hourly futures data to narrow the PF CI) is
  out of the free-data budget and out of scope for a free-data session.
- The free-data hypothesis space is exhausted (H1-H25; H15 probe; H24 = consolidation).

## Approaches already tried and failed (for the next agent)
- H1-H9 momentum/TSMOM, H16-H20, H23 on free data: all REJECT (Sharpe 0.2-0.8,
  regime-fragile, CI-fragile, PF<1.3).
- H22/H25 vol-targeting expansion: PASS point-wise but **not CI-robust** on the 730h window.
- Weakening gates to force a pass: disallowed by PROMPT_V2 §H15.

## One precise next task
Reproduce + defend the certified edge, then escalate the data wall — not invent new free-data
hypotheses (the pattern is exhausted). Concretely:
1. **(free data, bounded, high-value)** Add a `min_trade_interval` + block-bootstrap
   (stationary bootstrap) sensitivity to the H25 Robustness audit to confirm the i.i.d.
   CI is not an artifact of ignoring time-series dependence (a 5148-hour i.i.d. PF CI can
   be anti-conservative under autocorrelation). This is low-cost (reuse H13's i.i.d. as the
   baseline + add Politis-White block bootstrap) and would either tighten or loosen the
   ±0.120 CI — directly actionable evidence.
2. **(out of free-data scope, requires budget/approval)** Acquire paid hourly futures data
   (e.g. Databento Polygon/CMC) extending the `=F` window beyond 730 days to ~2-3 years,
   then re-run H25's pipeline verbatim and re-audit the PF CI. The audit pins the target:
   CI half-width ±0.120 must shrink ~3-4x for P(PF≥1.3) ≥ 0.90.
