# HANDOFF_CURRENT_SESSION.md — CI installs package for manifest contract (2026-11-13)

## What changed
- `.github/workflows/gates.yml` (working tree before this session was stale vs prior handoff claims):
  - added `scripts/**` to both `push` and `pull_request` path triggers;
  - changed lint steps to `python -m ruff check src tests run_*.py scripts` and
    `python -m ruff format --check src tests run_*.py scripts`;
  - added `python -m pip install -e . --no-deps` install step in both `lint` and
    `research_gates` jobs after `pip install -r requirements.txt`;
  - added `Performance regression gate`
    (`python scripts/backtest_perf_regression_gate.py`) step in `research_gates`
    before pytest.
- `tests/test_gates_workflow.py`:
  - added `test_jobs_install_the_package_editably` parametrized over `lint` and
    `research_gates` to pin the editable install step.
- No `src/qtr`, runner, gate threshold, verdict, frozen artifact, or published number changed.

## Why this was necessary (baseline evidence)
- At session start (HEAD `f86d732`, clean tree except untracked none), `tests/test_gates_workflow.py`
  failed **5/5** (missing `scripts` in lint/paths and missing perf gate step). Prior handoff
  claimed a committed fix that was not present in this checkout.
- `tests/test_generated_manifest_contract.py` had **11 passed / 3 skipped** without an installed
  `qtr` distribution in CI-relevant setup; installed-distribution checks were skipped.

## Actually verified (this session, own evidence)
- `python -m pip install -e . --no-deps` → succeeded (qtr-0.1.0 editable installed).
- Focused contracts: `python -m pytest -q -W error tests/test_gates_workflow.py tests/test_generated_manifest_contract.py`
  → **18 passed** (5 workflow tests + 2 parametrized install checks + 11 manifest tests, 0 skipped).
- `python -m pytest -q -W error tests/test_performance_regression_gate.py tests/test_backtest_perf_regression_gate.py`
  → **6 passed** (perf gate tests unchanged).
- Full suite: `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
  → **3751 passed, 48 skipped, 0 failed**; `src/qtr` coverage **100%** (1211 stmts / 422 branches / 0 miss).
  (Count consistent with prior 3748p/51s: 3 manifest skips became passes after editable install.)
- Lint/format: `python -m ruff check src tests run_*.py scripts` → All checks passed;
  `python -m ruff format --check src tests run_*.py scripts` → 327 files already formatted.
- Performance gate: `python scripts/backtest_perf_regression_gate.py` → `PERF GATE PASSED`
  (0.288s vs 5s limit, 10.7MB peak, 13668 trades).

## What remains unresolved
- **H182 discovery:** free-data PIT strategy-family discovery is exhausted at H181
  (Cycle 96, `NEW_FAMILY_RESEARCH_REGISTER.md`,
  `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6). Carry/insider/earnings/options/
  breakeven candidates are data-blocked; the rest are adjacency- or power-blocked.
  Requires explicit human authorization and an authorized free/PIT source for a
  materially new mechanism. Do not invent/execute H182.
- **Artifact restoration apply:** blocked on explicit human authorization and a no-op
  on this checkout (`--dry-run` → Recoverable 0 / Excluded 172 / Unrecoverable 25;
  baseline in `tests/test_reproducibility_audit.py`).
- **Generated inventories/pins remain frozen;** mutating `.experiments/experiments.jsonl`
  will fail pinned inventory tests until deliberately regenerated.
- Working tree has uncommitted changes to `.github/workflows/gates.yml`,
  `tests/test_gates_workflow.py`, `HANDOFF_CURRENT_SESSION.md`, and `NEXT_TASK.md`
  (no commit/push performed).

## Failed approaches / do not repeat
- Do not trust committed handoff/task docs as current truth without re-running the
  producing/contract checks.
- Do not invent/execute H182 from exhausted/adjacent families or blocked data.
- Do not run `scripts/plan_artifact_restoration.py --apply` (no-op; needs authorization).
- Do not time performance gates with `tracemalloc` active.
- Do not mass-edit frozen contracts/tests to force green.
- Do not commit/push unless explicitly requested.

## One precise next task
**Resolve the H182 discovery blocker or formally close discovery (authorization-gated).**
Per `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 and `NEW_FAMILY_RESEARCH_REGISTER.md`
Cycle 96, H1–H181 are exhausted/rejected and no feasible free-data PIT family remains
(carry/insider/earnings/options/breakeven data-blocked; others adjacency/power-blocked).
Next session must either: (a) obtain explicit human authorization plus an authorized free/PIT
data source for a materially new mechanism and pre-register H182 per directive §4 (honest
scoring, lineage check, smallest decisive test) before any runner execution; or (b) with
explicit authorization, document free-data family discovery as exhausted and shift effort to
auditing/infrastructure only. Do not invent H182 or modify frozen artifacts/gates. Re-verify
baseline first: `pytest -q -W error` (expect 3751 passed, 48 skipped), ruff check/format clean,
perf gate passed, 100% `src/qtr` coverage.