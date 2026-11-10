# HANDOFF_NEXT.md — Cycle 97 (after infrastructure audit fix): auditing/infrastructure shift complete

## Session summary (this session — Cycle 97)
- **Infrastructure audit fix completed.** Fixed 3 NF runners (`run_nf_20261106_22_smh_qqq_semicapex.py`, `run_nf_20261106_25_max_lottery.py`, `run_nf_20261107_09_max_lottery.py`) to comply with `test_engine_metric_agreement.py` contract. Replaced `.metrics["sharpe"]` reads with `sharpe_ratio()` from `qtr.validation.statistics` (population ddof=0 convention) in `_perturbation` and `evaluate_gates` functions.
- **Tests fixed:** `test_no_runner_gates_on_the_engine_sharpe` and `test_every_engine_sharpe_comparison_is_engine_against_engine` now pass (72/72 tests in `test_engine_metric_agreement.py`).
- **Code quality:** `ruff check/format --check` clean across `src/`, `tests/`, `run_*.py`. Focused core tests pass (210 passed). NF runner tests pass (30 passed).
- **Strategy family discovery status:** Per Cycle 96 conclusion, free-data point-in-time queue exhausted (H1–H181 all rejected). No H182 executed. `src/qtr` unchanged.

## Baseline verified
- `PYTHONPATH=src pytest -q` focused fast tests pass: `test_config.py`, `test_public_api_contract.py`, `test_coverage_gate_contract.py`, `test_backtest_engine.py`, `test_data_fetcher.py`, `test_cost_model.py` — 210 passed.
- `PYTHONPATH=src pytest -q tests/test_engine_metric_agreement.py` — **72 passed** (was 3 failing).
- `PYTHONPATH=src pytest -q` NF runner tests for fixed files — **30 passed**.
- `ruff check/format --check` — clean.
- `src/qtr` unchanged; no gate weakening; no published/certified artifact, verdict, threshold, or frozen number modified; no commit/push.

## Lineage state
- H85–H181 all rejected/recorded. Next unused H-ID **H182** (unassigned). `src/qtr` unchanged.
- Free-data point-in-time strategy-family queue exhausted (Cycle 96 conclusion, directive §6).

## Failed approaches / evidence (do not blindly repeat)
- H181 basis MR REJECT 4/8; H180 dividend capture REJECT 2/8; H179 short interest REJECT 2/8; H178 P/C REJECT 4/8; H177 Treasury auction REJECT 5/8; H176 tax-loss REJECT 3/8; H175 macro REJECT 7/8; H174 ETF prem/disc invalid (no PIT NAV); H173 ERP REJECT 7/8; H121 Amihud REJECT 4/8; H90 FOMC REJECT 1/9; H91 turn-of-month REJECT 3/9; H140 monthly OPX REJECT 4/8; H168 index rebalance REJECT 4/8; H150 ES managed-money (COT) REJECT 4/8. All H85–H181 rejected on free PIT data.
- Infrastructure test failures were due to NF runners reading engine Sharpe directly instead of using the record's `sharpe_ratio` (ddof=0 convention). Fixed by using `qtr.validation.statistics.sharpe_ratio` consistently.

## Precise next task (next agent)
Continue auditing/infrastructure work OR resolve a data gap under explicit authorization:

**Option A (auditing/infrastructure — no authorization needed):**
- Run full test suite audit (identify any other infrastructure contract violations).
- Verify experiment artifact consistency across `.experiments/nf_runs/`.
- Audit published numbers in `HYPOTHESIS_SPEC.md` against committed artifacts.
- Check for any remaining runners that read `.metrics["sharpe"]` (grep shows 3 fixed; verify no others).

**Option B (data gap resolution — requires explicit authorization):**
- **(a) Add futures roll/contango data** (authorized source) → revisit NF-04 commodity carry as H182.
- **(b) Add PIT insider / earnings-revision / options-chain data** (authorized source) → revisit NF-20261110-08 / NF-20261109-02 / NF-20261109-19.

Do not select H182 from the blocked/deferred/held pool without first resolving its blocker. Record the decision in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, `HANDOFF_NEXT.md`. No commit/push unless explicitly authorized.