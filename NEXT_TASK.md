# Next task (Cycle 186, 2026-11-17)

## What changed this session
- No source, test, gate, artifact, sidecar, hash, frozen-number, or workflow change. Only this handoff (`HANDOFF.md`, `NEXT_TASK.md`).
- Performed an independent full review of all 7 `src/qtr` modules, all `scripts/`, and the 140 runners + corpus metadata. No new reproduced defect found; the previous agent's conditional ("fix if a new defect appears, otherwise make no changes") resolves to **make no code change**.

## What was actually verified (own evidence, 2026-11-17)
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing --ignore=tests/test_gates_workflow.py` (343.97s) → **4273 passed, 48 skipped, 0 failed**, `src/qtr` coverage **100.00%** (1660 stmts / 628 branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed. `python -m ruff format --check src tests run_*.py scripts` → **336 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.282s < 5s, 10.7MB, 13668 trades).
- `python -m pytest -q tests/test_gates_workflow.py` → **7 failed** (unchanged, maintainer-gated).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → applies cleanly.
- Corpus-metadata tests `tests/test_sidecar_schema_contract.py tests/test_reproducibility_audit.py tests/test_generated_manifest_contract.py` → 19 passed; `tests/test_config.py` → 56 passed.
- Independent read of all seven `src/qtr` modules (`utils/config.py`, `validation/statistics.py`, `strategies/baselines.py`, `backtest/engine.py`, `data/fetcher.py`, `data/insider.py`, `tracking/experiment.py`) — every public function already carries the fail-closed degenerate-input guard. Grep of all `run_*.py`/`scripts`/`src` for `shift(-N)` (lookahead) → **0** matches.

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** `patches/0001-gates-workflow-contract-fix.patch` must be applied and pushed to `origin/main` by a maintainer with `workflows` scope (no agent token; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` each session, so in-tree workflow edits do not persist). After push, run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **H182 selection:** free-data point-in-time strategy-family queue exhausted (H1–H181 rejected/recorded, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). No honest free-data H182 pre-registrable without new authorized data; do not invent candidates or treat parameter/timeframe/universe variations as new mechanism families.
- **Reproducibility backlog:** frozen at `missing_files=197`, `hash_mismatches=11`, `orphaned_files=528`, `missing_meta_files=0`.

## One precise next task
**Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch`, then `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
**Agent (next session):** no agent-assigned code change. Independently re-verified this session (Cycle 186): all 7 `src/qtr` modules, `scripts/`, and the 140 runners carry the fail-closed guards; no new defect. Only if a NEW reproduced, runner-reachable defect appears in `src/qtr`/runners/corpus metadata — fix with the smallest verifiable change and rerun focused tests, `ruff check`/`format --check`, and `python scripts/backtest_perf_regression_gate.py` with own evidence; otherwise make no code change and re-verify the baseline.

## Approaches already tried and why they should not be repeated
- Do not re-review the seven `src/qtr` modules for the pinned defect classes (config boundaries, cache dedup, EDGAR/insider parsing, annualization/`sharpe_ratio`/`bars_per_year` guards, purged-CV operands, engine cost/metric/position/impact guards, `CostModel`/`_adv_for_symbol`, `Experiment` path containment, `load_config`/`_set_nested`, duplicate index/column handling, `max_leverage`/`initial_capital`/`max_position_size`) without NEW evidence — Cycle 186 re-read them and found no new defect.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — failures are the maintainer-gated contract block; the fix is the workflow patch.
- Do not use `--cov=<dotted.module>` for coverage collection (causes collection `ImportError`); rely on the full pinned suite with `--cov=qtr`.
- Do not trust handoff pass/fail/coverage counts — re-run gates.