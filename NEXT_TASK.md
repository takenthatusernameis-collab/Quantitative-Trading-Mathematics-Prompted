# NEXT_TASK.md — Cycle 97 (after infrastructure audit fix): auditing/infrastructure shift in progress

## Status: Cycle 97 complete — infrastructure audit fix done; free-data family discovery exhausted; H182 NOT pre-registered/executed

## Infrastructure fix completed (Cycle 97)
- **Fixed 3 NF runners** to comply with `test_engine_metric_agreement.py` contract:
  - `run_nf_20261106_22_smh_qqq_semicapex.py` (NF-20261106-22 / H111)
  - `run_nf_20261106_25_max_lottery.py` (NF-20261106-25 / H114)
  - `run_nf_20261107_09_max_lottery.py` (NF-20261107-09 / H117)
- **Change:** Replaced `.metrics["sharpe"]` reads with `sharpe_ratio()` from `qtr.validation.statistics` (population ddof=0 convention) in `_perturbation` and `evaluate_gates` functions.
- **Tests fixed:** `test_no_runner_gates_on_the_engine_sharpe` and `test_every_engine_sharpe_comparison_is_engine_against_engine` now pass (72/72 tests in `test_engine_metric_agreement.py`).
- **Code quality:** `ruff check/format --check` clean. Focused core tests pass (210 passed). NF runner tests pass (30 passed).

## H181 result (REAL, Cycle 95) — REJECT 4/8 (context)
- Runner `run_nf_20261104_03_es_spy_basis.py` (NF-20261104-03). OOS Val+Test: Sharpe 0.297 fail, PF 1.162 fail, worst-regime −1.410 fail, benchmark fail. `src/qtr` unchanged.

## Lineage
- H85–H181 all rejected/recorded. Next unused H-ID **H182** (H24/H68–H73/H76–H79 unassigned, not recycled). **H182 is unassigned and not pre-registered.** `src/qtr` unchanged.

## Directive §4 discovery (Cycle 96) — completed; queue exhausted
- Proposed ≥3 repo-new candidates across ≥3 broad mechanism categories, honest scoring. No candidate selected as H182. All blocked/deferred/held with concrete evidence (data, power, adjacency).
- NF-root check clean; no label reuse.

## Integrity constraints
- No H182 pre-registration or execution (directive §6: queue exhausted). Do not fabricate runner/results/verdict.
- No gate weakening; no published/certified artifact modification; no commit/push unless authorized.
- `src/qtr` unchanged unless evidenced defect. Free/public data only. Protected holdout never touched.

## Precise next task (for the next agent)
**Continue auditing/infrastructure (Option A, no authorization needed):**
- Run full test suite audit (identify any other infrastructure contract violations).
- Verify experiment artifact consistency across `.experiments/nf_runs/`.
- Audit published numbers in `HYPOTHESIS_SPEC.md` against committed artifacts.
- Check for any remaining runners that read `.metrics["sharpe"]` (grep shows 3 fixed; verify no others).

**OR resolve a data gap under explicit authorization (Option B):**
- **(a) Add futures roll/contango data** (authorized source) → revisit NF-04 commodity carry as H182.
- **(b) Add PIT insider / earnings-revision / options-chain data** (authorized source) → revisit NF-20261110-08 / NF-20261109-02 / NF-20261109-19.

Do not select H182 from the blocked/deferred/held pool without resolving its blocker first. Record any decision in `HYPOTHESIS_SPEC.md`, `NEW_FAMILY_RESEARCH_REGISTER.md`, `NEXT_TASK.md`, and `HANDOFF_NEXT.md`.