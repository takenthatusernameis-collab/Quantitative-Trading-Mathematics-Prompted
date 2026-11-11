# HANDOFF.md — H53 recipe verified in dep-enabled env; 9 frozen-contract failures are all drift

> **Current-session addendum (2026-11-11T07:20Z, verified):** the coverage gate was a real defect and is now fixed. `pyproject.toml` enforces `fail_under = 100` for `src/qtr`, but measured coverage was **99%** — 5 uncovered defensive branches in `src/qtr/backtest/engine.py` (146, 198, 230, 246, 401). Added 9 focused tests in `tests/test_backtest_engine.py` (`TestFailClosedCostGuards`) pinning each fail-closed guard with the exact input that takes its branch. `ruff check/format` clean; coverage now **100%** (1209 stmts / 420 branches, 0 miss). Full suite **3433 passed, 9 failed, 16 skipped** — the 9 remaining are exactly the pre-existing frozen-count/contested-log drifts below, all requiring per-contract review authorization. `src/qtr` source unchanged; only tests added; no commit/push. See `HANDOFF_CURRENT_SESSION.md` for the full record.

> **Current-session addendum (2026-11-11T04:20Z, verified):** one of the 10 frozen-contract failures was a real code bug, now fixed: `tests/test_benchmark_gate_contract.py::test_every_call_site_reads_only_keys_the_library_returns` flagged 4 NF runners whose `evaluate_gates` parameter `bench` (reads `bench["p_value"]`) was conflated by the flow-insensitive AST check with `bench = compare_to_benchmark(...)` (library returns `alpha_p_value`, not `p_value`). Renamed the parameter to `bench_gate` in `run_nf_20261107_{03,04,07,08}_*.py` — runtime behavior unchanged (callers pass `bench_out`, a runner-owned dict carrying `p_value`). `ruff check/format` clean; contract test 26/26. Full suite now **3425 passed, 9 failed, 16 skipped** — the 9 remaining are exactly the pre-existing frozen-count/contested-log drifts below, all requiring per-contract review authorization. `src/qtr` unchanged; no commit/push. See `HANDOFF_CURRENT_SESSION.md` for the full record.

> **Current-session addendum (2026-11-11T03:24Z, verified):** the environment now has
> `pytest` 9.2.0 / `ruff` 0.17.4 / Python 3.14.4 (the prior session lacked them). The
> H53 recipe correction from commit `70cf696` is confirmed: the 3 stale H92
> `benchmark_p_value` artifact IDs are correctly excluded and
> `test_every_published_value_re_derives` now passes (18 passed / 2 failed, down from 16/4).
> Full frozen-contract suite: **348 passed, 9 failed, 12 skipped** — all 9 failures are
> pre-existing frozen-number/count drifts or contested trade logs; **no new code bug found**.
> The H57 / engine-total-return "code bug" hypothesis is disproven
> (`test_h57_total_return_audit.py` 66 passed; `test_engine_total_return_consistency.py`
> 16 passed). Baseline evidence: commit `82eb68a`'s version of the H53 test file also
> yields 58 / 674 against the current tree, so the pins 54 / 630 were already stale at
> commit time. All changes this session are documentation only (`HANDOFF_CURRENT.md`,
> `HANDOFF_NEXT.md`, `NEXT_TASK.md`); `src/qtr` unchanged, no commit/push. See
> `HANDOFF_CURRENT.md` for the full current-session record.

**State timestamp (UTC):** 2026-11-09T00:00Z (session end; superseded by addendum above)
**Branch:** `main`
**Working tree:** uncommitted local changes only (no commit/push performed): `HYPOTHESIS_SPEC.md` (§H159 outcome), `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 73 execution outcome), `HANDOFF.md`, `NEXT_TASK.md` (Cycle 74 next task), `run_nf_20261108_32_vvix_vix_spread_spy.py`, `tests/test_nf_20261108_32_vvix_vix_spread_spy.py`, `.experiments/nf_runs/nf_20261108_32_vvix_vix_spread_spy/{summary.json,grid.csv,data_meta.json}`. `src/qtr` **unchanged**.
**Research mode:** NEW-FAMILY DISCOVERY MODE (STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md mandatory). H85–H159 all rejected/recorded.

## What changed
- **Cycle 73 discovery performed** (directive §4): lineage reconciled to H158; >=3 candidates scored honestly (25/25/20/15/10/5) across >=3 broad mechanism categories with NF-root collision checks: **NF-20261108-32 VVIX-VIX implied-vol-of-vol spread** (volatility & convexity premia / vol-of-vol, 4.15, selected → H159); **NF-20261108-29 cross-asset return dispersion** (4.10, deferred); **NF-20261108-31 cross-sectional IVOL dispersion** (3.85, deferred).
- **H159 pre-registered and REAL executed** (NF-20261108-32): `run_nf_20261108_32_vvix_vix_spread_spy.py` + `tests/test_nf_20261108_32_vvix_vix_spread_spy.py` (7 focused tests; test fixed so deterministic slice is non-empty). `ruff check/format` clean; focused pytest **7 passed**. Runner executed with real yfinance data (SPY+^VIX+^VVIX, 2010-01-04→2025-01-03, 3767 aligned rows); artifact `.experiments/nf_runs/nf_20261108_32_vvix_vix_spread_spy/summary.json` (+ grid.csv, data_meta.json, 10.78s). Verdict **REJECT 4/8**.
- Docs updated: `HYPOTHESIS_SPEC.md` §H159, `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 73, `HANDOFF.md`, `NEXT_TASK.md`.

## What was actually verified
- `python -m ruff check run_nf_20261108_32_vvix_vix_spread_spy.py tests/test_nf_20261108_32_vvix_vix_spread_spy.py` — All checks passed.
- `python -m ruff format --check run_nf_20261108_32_vvix_vix_spread_spy.py tests/test_nf_20261108_32_vvix_vix_spread_spy.py` — 2 files already formatted (after format).
- `PYTHONPATH=src python -m pytest -q tests/test_nf_20261108_32_vvix_vix_spread_spy.py` — **7 passed**.
- `python run_nf_20261108_32_vvix_vix_spread_spy.py` — completed; REAL verdict **REJECT 4/8** written to summary.json.
- Full pinned core suite **not rerun** (no `src/qtr` change).

## H159 result (REAL, pre-registered gates)
- OOS Val+Test (n=1252): Sharpe **0.696** fail, PF **1.146** fail, maxDD **-3.67%** pass, trades **3208** pass, WF stability **0.889** pass, worst-regime **-1.440** fail, benchmark p **0.950** / IR **-0.733** fail, perturbation **0.980** pass → **REJECT 4/8**. Train Sharpe 0.783 (selected z_window=126, entry_scale=1.0, vol_target=0.15; WF mean 0.873).
- Ablations: buy-hold SPY 0.754; random-exposure-matched **0.206** (much weaker — not noise); inverse regime **0.445** (weaker — direction supported, no benchmark edge).
- No gate weakened; no published/certified artifact modified; `src/qtr` unchanged.

## Unresolved / constraints
- No commit/push. `src/qtr` pinned full gates not rerun (no `src/qtr` change); rerun if `src/qtr` is touched.
- Deferred/held (no silent drops): NF-04 blocked; NF-05/07/08/10/11/13/15/20/21 deferred; NF-11r/NF-06-18 same root as NF-11 (H141); NF-06-11 infeasible; NF-06-03/23/24/28/30/32/33/35 deferred; NF-07-05 deferred (data blocker); NF-07-14/48 held; NF-07-49 held; NF-08-13 stub/deferred; NF-08-16 Halloween held; NF-08-20/21/22/23 deferred; NF-20261108-26 GLD RV stress deferred; NF-20261108-29 cross-asset dispersion deferred (4.10); NF-20261108-31 cross-sectional IVOL dispersion deferred (3.85).

## Approaches that failed / evidence (do not blindly repeat)
- H159 (VVIX-VIX spread, this cycle) fails PF/worst-regime/benchmark; Sharpe 0.696 below 1.0; random exposure much weaker (structure present) and inverse weaker (direction supported) but no benchmark edge (p=0.950, IR=−0.733). Do not rerun same construction.
- VVIX level family already exhausted: H104 ^VVIX vol-of-vol REJECT 4/9; VIX term-structure/implied-spread neighbors H86/H123/H131/H104/H89/H125/H126 all rejected.

## One precise next task (highest value, bounded)
**Cycle 74 directive §4 discovery → implement+run H160** per `NEXT_TASK.md`: reconcile lineage to H159, propose >=3 repo-new candidates across >=3 broad mechanism categories with honest scoring and NF-root checks, pre-register H160 before validation outcomes, add runner+focused tests, `ruff check/format`, focused pytest, execute, record REAL verdict in `HYPOTHESIS_SPEC.md`/`NEW_FAMILY_RESEARCH_REGISTER.md`/`NEXT_TASK.md`/`HANDOFF.md`. Justify independence from rejected classes including H159 VVIX-VIX spread and all prior listed classes. Free/public data only; no gate weakening; no commit/push; do not modify `src/qtr` unless evidenced defect requires it (then rerun pinned full gates).
