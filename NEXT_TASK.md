# NEXT_TASK.md — Cycle 96 (after H181 REJECT 4/8): discovery complete, no feasible H182

## Status: Cycle 96 complete — directive §4 discovery done; strategy-family queue exhausted; H182 NOT pre-registered/executed

## H181 result (REAL, not fabricated) — REJECT 4/8
- Runner `run_nf_20261104_03_es_spy_basis.py` (NF-20261104-03, relative value / cash-futures basis convergence). Tests `tests/test_nf_20261104_03_es_spy_basis.py` (8 passed, 1 third-party DeprecationWarning). `py_compile` ok; `ruff check/format --check` clean. Artifact `.experiments/nf_runs/nf_20261104_03_es_spy_basis_20261110_cycle95/summary.json` (+`grid.csv`, ~10.3s).
- OOS Val+Test (1969 periods, 99 trades): Sharpe 0.297 fail, PF 1.162 fail, maxDD −6.16% pass, trades 99 pass, WF stability 1.208 pass, worst-regime −1.410 fail, benchmark p 0.992 / IR −0.877 vs buy-hold SPY 0.911/+90.75% fail, perturbation min ratio 0.552 pass. Return +6.89%. → REJECT 4/8. Buy-hold dominates; inverse/random ablations near zero/negative.
- `src/qtr` unchanged; no gate weakening; no commit/push.

## Lineage
- H85–H181 all rejected/recorded. Next unused H-ID **H182** (H24/H68–H73/H76–H79 unassigned, not recycled). **H182 is unassigned and not pre-registered.** `src/qtr` unchanged.

## Directive §4 discovery (Cycle 96) — completed
- Proposed ≥3 repo-new candidates across ≥3 broad mechanism categories and scored each 1–5 honestly (25/25/20/15/10/5). Full table and deferred-pool reassessment in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96.
- **Result: no candidate selected as H182.** Every remaining candidate is blocked/deferred/held:
  - Data-blocked: commodity carry (no free PIT roll/contango), insider Form 4/13F (no free PIT source), earnings-estimate revisions (no free PIT history), options dealer GEX (no free historical options chain), breakeven inflation (^T5YIE/^T10YIE unavailable).
  - Statistical power: Russell 2000 annual reconstitution (~16 events/16 yr), S&P 500 inclusion/deletion (few/yr), stock split effects (low frequency).
  - Mechanism adjacency to executed families: 10Y-3M curve (H171/H11r), SPY jump asymmetry (H122/H128/H135), short-term CS reversal (H119 REJECT 3/8), RSP-SPY/USMV-SPY relmom (H97 + exhausted relmom).
  - Calendar adjacency (held): Halloween (H91/H140/H142), holiday/pre-holiday drift (H91/H140/H142/H168).
- NF-root check: no Cycle 96 candidate appears as an executed H-ID or artifact; no label reuse. Tracked draft `run_nf_20261110_07_es_basis.py` is NF-20261110-09/TBD (incomplete/unexecuted, no `main`) — not treated as executed.

## Integrity constraints
- No H182 pre-registration or execution this cycle (directive §6: queue exhausted). Do **not** fabricate a runner, results, or verdict to manufacture an H182.
- No gate weakening; no published/certified artifact, verdict, threshold, or frozen number modification; no commit/push unless explicitly authorized.
- `src/qtr` unchanged unless evidenced defect (then rerun pinned 100% suite). Free/public data only. Protected holdout never touched.

## Precise next task (for the next agent)
Either (a) resolve a data gap under explicit authorization — futures roll/contango data for carry (NF-04), PIT insider/earnings data (NF-20261110-08/NF-20261109-02), or PIT options-chain/GEX data (NF-20261109-19) — then re-run directive §4 discovery and select H182; or (b) conclude free-data point-in-time family discovery is exhausted and shift to auditing/infrastructure. Do not select H182 from the blocked/deferred/held pool without resolving its blocker first. Record any decision in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, and `HANDOFF_NEXT.md`.
