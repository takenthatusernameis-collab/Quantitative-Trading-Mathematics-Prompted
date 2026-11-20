# Next task (2026-11-20, Cycle 230 — H187 pre-registered; execute it)

## State at the start of this session (what the previous session left)

- HEAD `49e74c4` == origin/main, clean tree. That commit was **real code work**, not a handoff:
  `scripts/probe_sec_xbrl_fundamentals.py` was refined to separate "bundle downloaded" from
  "annual rows extracted", plus `tests/test_probe_sec_xbrl_fundamentals.py` (219 lines).
  The handoff files still said "no code change possible" — they were stale. Trust the commit,
  not the prose.

## What changed this session

- **H187 pre-registered** in `HYPOTHESIS_SPEC.md` §Cycle 230 (NF-20261120-01, equity accounting
  accruals + asset growth) with a full §4 three-candidate search, PIT rules, bounded 16-combo
  grid, protected test window, standard 8 gates, and disclosed survivorship/tag-join biases.
- **`NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 230** records the measured availability evidence and
  moves NF-20261120-01 to pre-registered. NF-20261120-02/03 are recorded as deferred.
- **`AGENTS.md`** stale-claim bullet corrected: the "free-data queue exhausted / no H-ID awaits a
  free-data source" conclusion is withdrawn for PIT accounting fundamentals.
- No change to `src/qtr`, `tests`, `run_*.py`, artifacts, hashes, gates, or frozen numbers.

## What was actually verified (own evidence, 2026-11-20)

- **Workflow push permission, definitively closed.** A scratch branch carrying a one-line
  `.github/workflows/gates.yml` edit was rejected by GitHub:
  `refusing to allow a GitHub App to create or update workflow '.github/workflows/gates.yml'
  without 'workflows' permission`. The branch was deleted; tree clean. Stop attributing this to
  configuration guesswork — the token provably cannot land the patch.
- **Full XBRL coverage probe** (`python scripts/probe_sec_xbrl_fundamentals.py --out
  .cache/xbrl/probe_full.json`, EXIT=0): 100/100 bundles, 99 with annual 10-K rows, **98 with
  ≥2 usable accrual observations**, median filing lag **50.75 days**, PIT span 2009-10-27 →
  2026-11-17. Exclusions: XOM (CIK 0002115436 = 2026 ExxonMobil Holdings successor entity, no
  10-K history) and BKNG (1 usable observation; `NetIncomeLoss` stops 2010, CFO resumes 2016,
  `ProfitLoss` fallback stops 2015).
- `python -m pytest -q tests/test_probe_sec_xbrl_fundamentals.py tests/test_h22_futures_tsmom_voltarget.py
  tests/test_h28_causal_recertification.py tests/test_h29_lookahead_sweep.py
  tests/test_gate_vacuity_contract.py` → **131 passed** (spec readers unaffected by the append).
- `python -m ruff check src tests run_*.py scripts` → clean; `ruff format --check` → **354 files
  already formatted**.

## One precise next task

**Execute H187 exactly as pre-registered** (`HYPOTHESIS_SPEC.md` §Cycle 230):

1. Write `run_nf_20261120_01_equity_accruals.py`. Import `annual_observations` / `probe` from
   `scripts/probe_sec_xbrl_fundamentals.py` — do **not** fork the tag logic. Reuse the engine,
   metrics, gate, benchmark and cross-sectional/hysteresis helpers from
   `run_nf_20261119_02_commodity_hedging_pressure.py`.
2. Signals: `accruals = (NI − CFO)/avg(Assets)` and `asset_growth = Assets_t/Assets_{t−1} − 1`;
   availability stamp = **max** of the three `filed` dates, then engine `shift(1)`; monthly
   refresh, forward-filled to the daily calendar; skip a rebalance with < 40 active names.
3. Universe: the probe's 100-name snapshot minus XOM and BKNG. Sample 2011-01-03 → 2026-11-17;
   Train → 2021-12-31; Val 2022-01-01 → 2023-12-31; Test protected 2024-01-01 → 2026-11-17.
   Grid exactly 16: feature {accruals, asset_growth} × entry_z {0.5, 1.0} × k {10, 20} ×
   vol_target {0.10, 0.15}, exit_z = 0.0, train-only 4-fold WF selection. 5 bps one-way per leg.
4. Emit `.experiments/nf_runs/nf_20261120_01_equity_accruals_<timestamp>/summary.json` +
   `grid.csv` + `data_meta.json`; add `tests/test_nf_20261120_01_equity_accruals.py`; bump the
   `tests/test_experiment_artifact_schema.py` inventory pins only for the new artifact directory
   (Cycle 219 precedent). Record the verdict in the register as Cycle 231.
5. If the run cannot fetch equity closes (yfinance 429), record the failure and stop — do not
   substitute a different price source inside the same pre-registered test.

**Maintainer (unchanged, separate):** apply/push
`patches/0001-gates-workflow-contract-fix.patch`, then verify `CONTRACT SATISFIED` and 7 passing
contract tests. The agent cannot land it (hard evidence above).

## Approaches already tried and why they should not be repeated

- Do not re-attempt a workflow push from the agent token; its refusal is now evidenced, not assumed.
- Do not re-conclude "free-data family queue exhausted" — H187 is pre-registered and feasible.
- Do not re-run the coverage probe for the same 100 names; the measurement is recorded. New
  probes are only justified for a *different* source or a *different* universe.
- Do not run H187 as a variant of H184/H185/H186 (commodity curve/OI/hedging) or of price-based
  CS momentum; the mechanism is accounting-statement information.
- Do not modify the 25 unrecoverable-missing / 11 hash-mismatch backlog without authorization; the
  baseline, both identity digests and `REPRODUCIBILITY_AUDIT_REPORT.md` must move in one commit.
- Do not edit `.github/workflows/**` or weaken any gate or contract test.

## HEAD

- Session started at `49e74c4` (== origin/main, clean tree).
