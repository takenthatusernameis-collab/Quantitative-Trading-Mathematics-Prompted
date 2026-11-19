# Next task (2026-11-19, Cycle 215)

## What changed this session
- **The Cycle 214 pre-registration was executed and closed out.** The runner + artifact +
  schema pins for H184 (commodity term-structure carry) were already committed by the
  session that ran it; this session **reproduced the run deterministically**, verified it,
  and reconciled every durable document so the record is not left half-written.
- **New/updated durable docs:** `HYPOTHESIS_SPEC.md` H184 execution section + lineage row
  (**PRE-REGISTERED → EXECUTED — REJECT 2/8**) + grid-label correction (24 → **36** combos;
  the enumerated sets multiply to 36, all were pre-registered in Cycle 214, so this is an
  arithmetic-label fix, not a search expansion); `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 215
  section; `AGENTS.md` H-range note (**H1–H184 exhausted/rejected, H185 unassigned**);
  `HANDOFF.md` Cycle 215 banner; this file.
- **No change** to `src/qtr`, gates, other artifacts/sidecars/hashes, frozen numbers, or
  `.github/workflows/**`. Artifact-schema pins are already at 111 dirs / 103 summaries /
  139 distinct keys from the H184 artifact commit — do not re-bump them.

## H184 result (own evidence, 2026-11-19)
Artifact: `.experiments/nf_runs/nf_20261114_01_commodity_termstructure_carry_20261119_cycle215/`
(summary.json + grid.csv, 36 rows).

| Slice | Sharpe | PF | maxDD | trades | worst roll-252 |
|---|---|---|---|---|---|
| OOS Val+Test | **0.672** | 1.142 | −19.28% | 1,203 | −0.663 |
| Val | 1.110 | 1.222 | −8.96% | 368 | +0.633 |
| Test (protected) | 0.372 | 1.081 | −19.28% | 460 | −0.232 |
| Passive front-month long (OOS) | **1.004** | 1.215 | −12.65% | 2,493 | −0.482 |

- Gates PASS only **trades ≥ 50** and **WF stability ≥ 0.7 (1.402)** → **REJECT (2/8)**.
  FAIL: Sharpe, PF, maxDD, worst-regime, benchmark **p 0.792 / IR −0.141**, perturbation
  **0.169**.
- Ablations: random ranking OOS −0.171, inverse slope −0.921 → the slope *sign* is the
  pre-registered one; the timing overlay simply subtracts from holding the front month
  after CNY costs. **The mechanism failed, not the data** (commodity per-contract data are
  still AVAILABLE free/PIT).

## What was actually verified (own evidence, 2026-11-19)
- `python run_nf_20261114_01_commodity_termstructure_carry.py --out /tmp/h184_repro` →
  identical summary to the committed artifact in every field except `timestamp_utc` /
  `runtime_sec`, and **byte-identical `grid.csv`** (deterministic; cache hit).
- `python -m pytest -q tests/test_nf_20261114_01_commodity_termstructure_carry.py
  tests/test_probe_commodity_termstructure_availability.py
  tests/test_experiment_artifact_schema.py` → **158 passed**.
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **347 files already formatted**.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4434 passed,
  51 skipped, 0 failed** (410.48 s), `src/qtr` coverage **100.00%** (1692 stmts / 642
  branches / 0 miss).
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.424 s < 5 s,
  10.7 MB peak, 13668 trades).
- `python scripts/verify_gates_workflow_patch.py` → patch applies and resolves all 7 live
  violations, exit 0; `pytest -q tests/test_gates_workflow.py` → 7 failed (known,
  maintainer-gated).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials.
- **H1–H184 exhausted/rejected; H185 unassigned.** No further H184 variants are legitimate.
- Remaining candidate classes and why they are not simply runnable: options dealer GEX (no
  free historical chain), PIT analyst revisions (no free PIT history), index
  reconstitution/splits (underpowered), relmom/calendar/vol-complex branches
  (adjacency-recycled). The only unexecuted free-PIT proxy on the newly probed sources is
  **open interest** (positioning / hedging pressure), which no executed H-ID uses as its
  primary signal on Chinese futures.
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197,
  hash_mismatches=11, orphaned_files=528, missing_meta_files=0.

## One precise next task
**Maintainer:** `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am
"fix(ci): satisfy gates workflow contract" && git push origin main`, then
`python scripts/verify_gates_workflow_patch.py` (expect `CONTRACT SATISFIED`) and
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).

**Agent — candidate assessment, then pre-register H185 only if it survives:**

1. **Write the mechanism-distinction argument first, in `HYPOTHESIS_SPEC.md`**, before any
   outcome is computed. Proposed H185 mechanism: **open-interest / hedging-pressure
   positioning** — cross-sectional OI *level* and OI *change* per contract as a proxy for
   hedging demand / crowding (Bessembinder-type hedging-pressure premium: net hedging
   pressure earns a return premium), **not** roll yield (`H184`, rejected) and **not**
   volume/price prediction (`H19`/`H20`, US ETFs). Required: explain why OI-as-positioning is
   not a re-skin of H184's slope signal (different input field, different economic force),
   and why the Chinese-futures venue does not make it a mere "universe variation" — if that
   argument is not convincing in writing, **do not run it**.
2. **If it survives, pre-register** (same discipline as H184): universe SHFE RB/CU/AL/ZN/AU/AG
   + INE SC with per-product first dates; PIT timing from day-t settlement cross-section with
   an explicit `shift(1)` and a lookahead test; OI-based signal definition (level and change,
   declared windows/z-scores); CNY cost model reused **unchanged** (5 bps one-way + 1 bps
   roll); sample 2016-01-04→2026-11-17 with Train →2023-06-30 / Val 2023-07-01→2024-12-31 /
   Test protected 2025-01-01→2026-11-17; a bounded grid declared in full; the **same 8
   fail-closed OOS gates**; ablations = passive front-month long, random ranking (seed 42),
   inverse signal, OAT ±20%.
3. **Implementation reuse is mandatory:** import the parsers/URL builders from
   `scripts/probe_commodity_termstructure_availability.py` and the settlement-cache loader
   from `run_nf_20261114_01_commodity_termstructure_carry.py`; do **not** fork a second copy;
   reuse `.cache/commodity_settlements/` (already warm, ~328 MB) so no bulk re-download.
4. **Verification before reporting:** focused tests (incl. lookahead/causality and parser
   fixtures), `ruff check`, `ruff format --check`, the full pinned coverage suite
   (`--ignore=tests/test_gates_workflow.py`, 100% `src/qtr`), and
   `python scripts/backtest_perf_regression_gate.py`. Bump the artifact-schema pins only if a
   new artifact directory is committed.
5. **If the distinction argument fails:** do not substitute a maintenance audit. Record the
   explicit, evidenced conclusion that free-data family discovery is exhausted (with the
   deferred/blocked table), and leave that as the deliverable.

## Approaches already tried and why they should not be repeated
- Do not re-run H184 or any variant of it (CZCE/CFFEX breadth, other k/entry thresholds,
  longer SHFE history, alternative vol targets) — REJECT 2/8 is a family-level result.
- Do not classify commodity per-contract roll/contango as data-blocked (Cycle 214 probe,
  4/4 sources usable) — the data exist; the mechanism failed.
- Do not re-probe CHRIS/CME/Yahoo/stooq/LME/DCE as "maybe free" (all probed and blocked).
- Do not treat parameter/timeframe/universe/indicator variations as new families.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py`.
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization.
- Do not trust handoff pass/fail/coverage counts — re-run the gates.

## HEAD
- `0e83f42` at session start (contains the H184 runner rewrite, artifact, and schema-pin
  update). This session adds documentation only; the controller checkpoints it with
  `.github/workflows/**` excluded from staging.
