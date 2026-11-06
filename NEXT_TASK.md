# NEXT_TASK.md — Cycle 21 discovery / pre-registration of H107

Cycle 20 executed H106 (NF-20261106-14 FXY JPY safe-haven/funding-unwind stress timing SPY) — **REJECT 4/8** (`exp_2026-11-06T13-53-01-203238Z`, `.experiments/nf_runs/nf_20261106_14_fxy_safehaven/summary.json`): fails Sharpe 0.832/PF 1.165/worst-regime -0.754/benchmark-p null/IR -0.377. `src/qtr` unchanged.

**Next (Cycle 21, directive §4):** reconcile lineage to H106 (H85–H106 rejected, next H107). Propose/score >=3 mechanism candidates across >=3 categories (honest novelty); reassess NF-04/05/07/08/10/11/13/15/17/20/21 and NF-11r (TNX-FVX is NF-11 data-resolution, **same root mechanism — honest novelty if pursued**; NF-06-11 PC ratio infeasible). Pre-register H107 (smallest decisive test) before validation/protected outcomes; implement runner+tests, run `ruff check/format --check` + focused pytest, execute, record verdict. No gate weakening; no published/certified artifact changes; no commit/push.
