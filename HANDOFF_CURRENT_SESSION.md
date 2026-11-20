# Current session handoff (2026-11-20, Cycle 230 — SEC XBRL feasibility measured; H187 pre-registered)

## What changed

- `HYPOTHESIS_SPEC.md`: new §Cycle 230 — directive §4 discovery (three candidates scored), and
  **H187 (NF-20261120-01) equity accounting accruals + asset growth pre-registered, not executed**.
- `NEW_FAMILY_RESEARCH_REGISTER.md`: new Cycle 230 — measured SEC XBRL availability, exclusions,
  and the family-status change (unclassified → pre-registered).
- `AGENTS.md`: corrected the stale "free-data queue exhausted / no H-ID awaits a free-data source"
  bullet; it now records H187 as pre-registered and the SEC XBRL source as usable PIT.
- `NEXT_TASK.md`, this file, `HANDOFF_NEXT_SESSION.md`: refreshed to point at executing H187.
- No change to `src/qtr`, `tests`, `run_*.py`, artifacts, sidecars, hashes, gates, or frozen
  numbers. No new artifact directory, so no schema-inventory pin moved.

## What was actually verified (own evidence, 2026-11-20)

- **Workflow token refusal (definitive, not inferred).** Pushed a scratch branch containing a
  one-line `.github/workflows/gates.yml` edit: GitHub returned
  `! [remote rejected] … (refusing to allow a GitHub App to create or update workflow
  '.github/workflows/gates.yml' without 'workflows' permission)`. Branch deleted; `git status`
  clean. This ends the recurring "maybe the push would work" uncertainty.
- **Full-universe XBRL probe**, EXIT=0: `symbols_requested=100`, `symbols_with_bundle=100`,
  `symbols_with_annual_data=99`, `symbols_with_two_plus_accrual_observations=98`,
  `median_filing_lag_days=50.75`, `first_filed=2009-10-27`, `last_filed=2026-11-17`.
  Weak rows: XOM (0 annual rows) and BKNG (1 usable). Both diagnosed at the tag level, not guessed.
- `tests/test_gates_workflow.py` still **7 failed** (unchanged, maintainer-gated).
- 131 tests passed across the spec-reading suites
  (`test_probe_sec_xbrl_fundamentals`, `test_h22_*`, `test_h28_*`, `test_h29_*`,
  `test_gate_vacuity_contract`) — the doc append breaks no pinned assertion.
- `python -m ruff check src tests run_*.py scripts` → **All checks passed**;
  `python -m ruff format --check …` → **354 files already formatted**.

## What remains unresolved

- **H187 not executed.** Pre-registration is locked; the runner, tests and artifact are the next
  session's bounded task (see `NEXT_TASK.md`).
- **Maintainer-gated workflow patch** — provably agent-unreachable (evidence above).
- **25 unrecoverable missing artifacts / 11 hash mismatches** — authorization-gated.
- **NF-20261120-02 (net share issuance) and NF-20261120-03 (gross profitability)** — deferred,
  recorded, not rejected; only pre-register them after H187 is executed.

## Approaches already tried and why they should not be repeated

- Do not retry an agent-token workflow push (refused; evidenced).
- Do not re-probe the same 100-name SEC XBRL universe; coverage is measured and recorded.
- Do not reclassify XOM/BKNG as parser bugs — XOM is an entity-continuity gap (2026 successor
  entity), BKNG is a tag/filing discontinuity that `ProfitLoss` does not close.
- Do not re-run H184/H185/H186 or price-based CS-momentum variants as "new families".
- Do not touch the reproducibility backlog without authorization (baseline + both digests +
  audit report must move in one commit).
- Do not weaken `.github/workflows` contract tests or any gate.

## HEAD

- Session started at `49e74c4` (== origin/main, clean tree).
