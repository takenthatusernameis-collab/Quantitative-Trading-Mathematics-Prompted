# Next task (Cycle 185, 2026-11-17)

## What changed this session
- Fixed a reproduced `qtr.utils.config.load_config` save-target clobber: loading an explicit but missing config path returned `{}` but left `_CONFIG_PATH` pointing at the previously loaded config, so a later `save_config()` (no path) overwrote that prior config file. `load_config` now records the explicit missing path as the save target and clears `_CONFIG_PATH` only when search-and-not-found.
- Added `tests/test_config.py::TestNonMappingConfigDocument::test_load_config_explicit_missing_path_sets_save_target`.
- Files: `src/qtr/utils/config.py`, `tests/test_config.py`, `HANDOFF.md`, `NEXT_TASK.md`.

## What was actually verified (own evidence, 2026-11-17)
- `tests/test_gates_workflow.py` red on `origin/main`: **7 failed** (lint ruff targets missing `scripts`, path filters missing `scripts/**`, `research_gates` missing editable install + perf regression gate).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` → **clean**.
- Applied patch temporarily → `tests/test_gates_workflow.py` **7 passed**; reverted `.github/workflows/gates.yml` afterwards so working tree is clean (no durable workflow change possible by agent).
- (Config fix from prior session preserved: `tests/test_config.py` → 56 passed; `ruff check` on config files clean.)

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** `patches/0001-gates-workflow-contract-fix.patch` must be applied and pushed to `origin/main` by a maintainer with `workflows` scope (no agent token; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` each session, so in-tree workflow edits do not persist). After push, run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **H182 selection:** free-data point-in-time strategy-family queue exhausted (H1–H181 rejected/recorded, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96). No honest free-data H182 pre-registrable without new authorized data; do not invent candidates or treat parameter/timeframe/universe variations as new mechanism families.
- No other new reproduced defect found in `src/qtr`/runners/corpus metadata this session.

## One precise next task
**Maintainer:** apply and push `patches/0001-gates-workflow-contract-fix.patch` on `origin/main`, then run `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
**Agent (next session):** no agent-assigned code change. If a new reproduced defect appears in `src/qtr`/runners/corpus metadata, fix it with the smallest verifiable change and rerun focused tests, `ruff check`/`format --check`, and `python scripts/backtest_perf_regression_gate.py` with own evidence; otherwise make no changes.

## Approaches already tried and why they should not be repeated
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py` — failures are the maintainer-gated contract block; the fix is the workflow patch.
- Do not re-audit already-pinned defect classes without new evidence (cache normalization/dedup, config boundaries, EDGAR handling, annualization/`bars_per_year`/`periods_per_year`/`sharpe_ratio` guards, split/CV/purged-CV operand guards, engine cost/metric/position/impact guards, `CostModel`/`_adv_for_symbol`/`equity_impact_bps_per_pct_adv` degenerate-input guards, `statistics.multiple_testing_correction(alpha=...)` guard, `Experiment.__init__`/`record_artifact`/`load_metadata` path containment, `load_config`/`_set_nested`, duplicate index/column handling, `max_leverage`/`initial_capital`/`max_position_size`, `filing_documents` malformed-EDGAR item/name handling, etc.).
- Do not use `--cov=<dotted.module>` for coverage collection (causes collection `ImportError`); rely on focused tests or the full pinned suite with `--cov=qtr`.
- Do not trust handoff pass/fail/coverage counts — re-run gates.
