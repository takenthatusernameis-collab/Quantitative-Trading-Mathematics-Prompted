# HANDOFF_NEXT.md — Cycle 97 audit: engine-metric contract green; benchmark-gate contract failure documented

## Session summary (Cycle 97 audit)
- No code changes. Audited current baseline after prior infrastructure fix.
- Verified: `tests/test_engine_metric_agreement.py` **72/72 passed** (the two Sharpe-agreement tests previously cited in handoff remain fixed). `ruff check/format` clean. Focused core tests **210 passed**. Fixed NF runner tests (`test_nf_20261106_22_smh_qqq_semicapex.py`, `test_nf_20261106_25_max_lottery.py`, `test_nf_20261107_09_max_lottery.py`) **30 passed**.
- Baseline gap found/confirmed: `tests/test_benchmark_gate_contract.py` **25 passed, 1 failed** — `test_no_runner_compares_a_p_value_against_max_p_value_directly` with **38 NF runner offenders** (direction-blind `p < GATES["max_p_value"]` comparisons). This is pre-existing relative to this audit session; not fixed.
- Full suite collection **3448 tests**; `pytest -q -x` stopped at first failure after **136 passed** (benchmark gate contract). Full-suite green not claimed.
- Artifact/state audit: `.experiments/nf_runs/` contains **95** `summary.json` and **75** `grid.csv` files. `grep` shows no `.metrics["sharpe"]` reads in `run_nf_*.py`; legacy/non-NF runners still read engine sharpe but current engine-metric contract passes. `src/qtr` unchanged.

## Lineage/state
- H85–H181 all rejected/recorded. H182 unassigned (not pre-registered). Free-data point-in-time strategy-family discovery queue exhausted (Cycle 96). Next work should be auditing/infrastructure inventory or explicitly authorized data-gap resolution.

## Failed approaches / evidence (do not blindly repeat)
- Do not claim full test suite is green; benchmark gate contract currently fails (38 offenders).
- Do not mass-refactor NF runners/tests/gates to clear the contract without evidence-based, per-runner review (published artifacts/results and historical semantics at risk).
- Prior H176–H181 all REJECTED on free PIT data (see prior handoffs/HYPOTHESIS_SPEC).

## Precise next task (next agent) — audit complete
`INFRASTRUCTURE_AUDIT_BENCHMARK_GATE.md` now inventories all **38** offenders from `test_no_runner_compares_a_p_value_against_max_p_value_directly` (runner path, line, NF ID, offending comparison snippet, artifact presence under `.experiments/nf_runs/`), with counts by date bucket and comparison form. **31/38** runners have a committed `.experiments/nf_runs/<slug>/summary.json`; **7** have none. No source/runner/test/gate/artifact behavior changes made; no commit/push.

Remaining for next agent: re-verify `ruff check/format`, `tests/test_engine_metric_agreement.py`, focused core tests, and `tests/test_benchmark_gate_contract.py` (expected same 1 failure) and report exact counts. H182 remains unassigned; NF discovery queue exhausted per Cycle 96. Do **not** mass-refactor runners to clear the contract without evidence-based, per-runner review.
