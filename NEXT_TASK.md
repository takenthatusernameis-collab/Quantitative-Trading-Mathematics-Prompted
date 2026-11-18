# Next task (2026-11-18, Cycle 213)

## What changed this session
- **Completed the assigned H183 execution instead of leaving it truncated.** The prior session
  (HEAD `dc3ac84`) pre-registered H183 / NF-20261114-02 (crypto perpetual funding-rate carry) and
  ran it, but the recorded artifact
  `.experiments/nf_runs/nf_20261114_02_crypto_funding_carry_20261118_163437` stopped at
  `2024-12-31` with **`test_rows: 0`** — the pre-registered protected Test window
  (2025-01-01→2026-10-31) was silently absent because 2025+ spot kline archives use
  microsecond epoch stamps. Re-ran the committed runner (no code change) with
  `PYTHONPATH=src python run_nf_20261114_02_crypto_funding_carry.py`.
- **New authoritative artifact:**
  `.experiments/nf_runs/nf_20261114_02_crypto_funding_carry_20261118_194621/summary.json`
  (+`grid.csv`), 73.4 s. 2496 rows 2020-01-01→2026-10-31; train 1277 / val 550 /
  **test 669** / OOS 1219; all 7 symbols reach 2026-10-31.
  Selected `funding_window=14, entry_bps=0.5, exit_bps=0.25` (train WF 7.330).
  OOS Val+Test: Sharpe **7.676**, PF **5.637**, maxDD **−0.384%**, trades **133**,
  WF stability **1.108**, worst rolling-252 **−0.356 (fail)**, benchmark p **0.329** /
  IR **0.197** vs passive always-on carry (Sharpe **6.971**), perturbation min ratio
  **0.899**. **REJECT (6/8)**.
- **Docs recorded (durable):** `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 213 entry,
  `HYPOTHESIS_SPEC.md` H183 section, `AGENTS.md` H-range + free-data-correction notes,
  `HANDOFF.md` Cycle 213 banner. Lineage is now **H1–H183 exhausted/rejected,
  H184 unassigned**. The old truncated artifact is preserved and marked superseded.
- **Data-availability correction:** `data.binance.vision` monthly public archives serve
  fundingRate + daily spot/perp klines free and key-less (HTTP 200 for 2020-01…2026-10).
  The Cycles 96/116 "crypto funding is data-blocked" claim is retired — same standing rule
  Cycle 140 set for FRED.
- **One test-pin update (required by the new artifact, not a gate change):**
  `tests/test_experiment_artifact_schema.py` `EXPECTED_TOTAL_DIRS` 109→110 and
  `EXPECTED_SUMMARY_COUNT` 101→102, with a comment recording the Cycle 213 addition.
  Key-frequency pins are unchanged (134 distinct keys; same >=50% / >=80% sets).
- No change to `src/qtr`, runners, gates, other artifacts/sidecars/hashes, frozen numbers,
  or `.github/workflows/**`. No gate weakening.

## What was actually verified (own evidence, 2026-11-18)
- `python scripts/verify_gates_workflow_patch.py` → 7 live violations, patch still valid,
  exit 0 (baseline check per prior handoff).
- `python -m pytest -q tests/test_nf_20261114_02_crypto_funding_carry.py
  tests/test_probe_binance_funding_availability.py` → **27 passed** (includes
  `test_epoch_timestamps_detects_microsecond_archives` and
  `test_spot_archive_until_2026_present_after_unit_fix`; the microsecond fix is now
  confirmed end-to-end on real data, not only in unit tests).
- `curl` probe: `…/fundingRate/BTCUSDT/BTCUSDT-fundingRate-{2025-01,2025-12,2026-09,2026-10}.zip`
  → all HTTP 200.
- Determinism cross-check: the earlier (truncated) run and the full-window run produce
  identical train-side numbers (`wf_train_sharpe` 7.33002259388738,
  `train_selected_sharpe` 6.929185457213459) — the only differences come from the added
  OOS rows.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4381 passed,
  51 skipped, 0 failed** (666.78s), `src/qtr` coverage **100.00%** (1692 stmts / 642
  branches / 0 miss).
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **343 files already formatted**.
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.797s < 5s,
  10.7MB peak, 13668 trades).
- `python -m pytest -q tests/test_experiment_artifact_schema.py` → **107 passed**
  (after the inventory pin update above).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials.
  `scripts/verify_gates_workflow_patch.py` proves the patch is still valid and complete.
- **Strategy-family discovery:** H1–H183 exhausted/rejected; **H184 unassigned**. Remaining
  candidate categories and their *probed* blockers: commodity per-contract roll/contango
  (no free PIT per-contract series — yfinance `=F` is spliced-continuous), options
  dealer GEX / PIT options chain (none free), PIT analyst revisions (none free), index
  reconstitution/inclusion/splits (annual → power), calendar/Halloween/holiday and
  relmom/curve families (adjacency to executed H-IDs).
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197,
  hash_mismatches=11, orphaned_files=528, missing_meta_files=0.
- **H183 headline-Sharpe caveat (documented, not a defect):** both the timed and passive
  carry books report Sharpe ≈7 because PnL is a modeled 1×-notional funding accrual without
  borrow/custody/margin/liquidation costs. Do not quote this as a live Sharpe; the verdict
  rests on the timing null (p 0.329, IR 0.197) and the −0.356 worst rolling-252 window.

## One precise next task
- **Maintainer:** `git apply patches/0001-gates-workflow-contract-fix.patch && git commit
  -am "fix(ci): satisfy gates workflow contract" && git push origin main`, then run
  `python scripts/verify_gates_workflow_patch.py` (expect `CONTRACT SATISFIED`) and
  `python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).
- **Agent:** run `python scripts/verify_gates_workflow_patch.py` as the first baseline
  check. Then, if pursuing H184, the only non-adjacent mechanism class still untested is
  **commodity per-contract term structure** — but it needs a *newly probed* free PIT
  per-contract/deferred series (e.g. CME/NYMEX settlement archives, Nasdaq Data Link
  free tier). Probe availability with a read-only script first and record the result in
  the register; do **not** run H183 variants (different windows/thresholds/universe are
  parameter variations, not new families) and do not re-declare crypto funding as blocked.
  Otherwise only act on NEW concrete evidence of a runner-reachable defect, then rerun
  focused tests, both ruff checks, the full pinned coverage suite, and the perf gate.

## Approaches already tried and why they should not be repeated
- Do not re-run H183 as a "new" experiment: it is executed and rejected on the full
  pre-registered window; the artifact is `…_20261118_194621`.
- Do not treat the truncated `…_20261118_163437` artifact as the record — it has
  `test_rows: 0`.
- Do not classify crypto funding/perpetual basis as "data-blocked" (`data.binance.vision`
  probed 2026-11-18) or breakeven inflation as blocked (FRED, Cycle 140).
- Do not re-audit `src/qtr`/runners for the pinned defect classes without NEW evidence.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py`.
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization.
- Do not trust handoff pass/fail/coverage counts — re-run the gates.

## HEAD
- `dc3ac84` at session start (cycle 213 adds the H183 docs/artifact; the controller
  checkpoints them, `.github/workflows/**` excluded from staging).
