# Session complete (2026-11-21, Cycle 247 — H193 recorded + tested)

## What changed (this session)

The prior handoff's only assigned task was **maintainer-only** (apply
`patches/0001-gates-workflow-contract-fix.patch`), which is agent-unreachable per
AGENTS.md (`.github/workflows/**` restored from `origin/main`; token lacks `workflows`
permission). With no agent-executable assignment, per the fallback rule I selected and
executed the next on-pattern high-value task (directive §6): a **new strategy family**.

- **H193 (NF-20261121-03, beta-sorted equity cross-section / betting-against-beta) is
  now fully executed and recorded.** New files:
  - `run_nf_20261121_03_bab_beta.py` — reuses the H184/H187 backtest engine, metrics,
    gate helpers and cross-sectional/hysteresis primitives; new code is only the
    trailing-beta panel construction (`Cov(r_i, r_mkt)/Var(r_mkt)`, causal) and the
    long-low-beta / short-high-beta hysteresis signal. Monthly refresh; standard 8 gates.
  - `tests/test_nf_20261121_03_bab_beta.py` — 19 hermetic tests (synthetic geometric
    prices, no network/cache): constants, universe (98 = S&P100 − XOM/BKNG), bounded
    16-cell grid, `returns_from_closes` first-row-NaN, `trailing_beta` recovers known
    betas + window warmup, monthly beta panel shape/values + **all-NaN regression guard**,
    winsorized z, long-low/short-high signal, hysteresis + exit, insufficient-active
    zeroing, walk-forward sentinel/finite, 4-point perturbation, collinearity bounds +
    **proportional-panel regression guard**, and summary/grid artifact assertions.
  - Artifact `.experiments/nf_runs/nf_20261121_03_bab_beta_20261121_184109/`
    (summary.json + grid.csv + data_meta.json), runtime 41.799 s.
- Updated `tests/test_experiment_artifact_schema.py` inventory pins (recomputed from the
  corpus): `EXPECTED_TOTAL_DIRS 118→119`, `EXPECTED_SUMMARY_COUNT 110→111`,
  `EXPECTED_DISTINCT_KEYS 152→153` (new key `train_input_collinearity_beta126_vs_beta252`);
  `EXPECTED_CACHE_ONLY_DIRS` (11), `EXPECTED_KEYS_GE_50_PCT`, `EXPECTED_KEYS_GE_80_PCT`
  unchanged (recomputed). Cycle 247 comment added.
- Recorded H193 (REAL REJECT 3/8) in `NEW_FAMILY_RESEARCH_REGISTER.md` (new Cycle 247 section
  with the §4 three-candidate discovery scan + honest scoring, pre-registration, mechanism
  separation from H93/H117/H29, data availability, execution outcome, an **explicit note that
  the WF-stability/perturbation passes are negative/negative-ratio artifacts**, lineage map, and
  durable family-status consequence).
- Updated the `AGENTS.md` stale H-range note additively: executed record is now **H1–H193**
  (Cycles 215–247), with H193 artifact cited and a note that beta / systematic-risk
  cross-sections and the yfinance close panel are NOT data-blocked.
- **Incidental baseline repair:** `scripts/probe_sec_13f_holdings.py` (added by HEAD commit
  `0b2ecc2`, unmodified in the tree) was failing the required `ruff format --check` gate. I ran
  `ruff format` on it (line-wrapping only, verified formatting-only via diff, still parses,
  `ruff check` clean). This is a cheap deterministic blocker fix, not a functional change.

## H193 result (from `.experiments/nf_runs/nf_20261121_03_bab_beta_20261121_184109/summary.json`)

- Mechanism: leverage constraints (margin, borrow costs, unleverable low-beta portfolios) flatten
  the realised Security Market Line, so long low-beta / short high-beta should earn a premium
  (Frazzini & Pedersen 2014). Distinct from H93 (idiosyncratic vol), H117/H29 (scalar beta timing).
- Universe: 98/98 S&P 100 names (minus XOM/BKNG) with ≥252 valid daily returns (min 441). Offline.
- Selected `feature=beta_126, entry_z=0.5, exit_z=0.0, k=5, vol_target=0.10` (train WF −0.540;
  train Sharpe −0.550). beta_126 vs beta_252 collinearity 0.931 (denominators agree).
- OOS Val+Test (1272 periods, 12716 trades): Sharpe **−0.977**, PF **0.848**, maxDD **−52.09%**,
  worst rolling-252 Sharpe **−2.828**, total return −0.430.
- Gates PASS (3): trades, WF stability (1.778), OAT perturbation min ratio (0.920). Gates FAIL (5):
  Sharpe ≥ 1.0 (−0.977), PF ≥ 1.3 (0.848), maxDD ≤ 15% (−52.09%), worst-regime ≥ 0.3 (−2.828),
  benchmark p ≤ 0.05 with IR ≥ 0 (p 0.0067 but IR −1.209, negative).
- **Honest caveats:** the WF-stability and perturbation "passes" are negative/negative-ratio
  artifacts (strategy unprofitable in-sample and OOS), NOT robustness. The **inverse signal
  (anti-beta, long high-beta / short low-beta) OOS Sharpe +0.959** shows the BAB *sign* is
  empirically inverted in this post-2011 mega-cap universe (high-beta names outperformed); even
  the profitable mirror direction fails the Sharpe ≥ 1.0 gate. **Verdict: REJECT (3/8).**

## What was actually verified (this session)

- `python -m pytest tests/test_nf_20261121_03_bab_beta.py` → **19 passed**.
- `python -m pytest tests/test_experiment_artifact_schema.py` → **116 passed** (inventory pins
  updated; +1 from the new summary.json parametrization).
- Focused regression set (H191 value, H192 innovation, artifact schema, H193) → **181 passed**.
- Runner-wide static contracts (auto-globbed) `test_runner_import_contract`,
  `test_benchmark_gate_contract`, `test_gate_vacuity_contract` and engine/causality contracts →
  **466 passed / 1 skipped** (pre-existing skip); the only failure was ruff format on the new
  runner, fixed by `ruff format`.
- **Full suite (`python -m pytest -q`): 4646 passed / 51 skipped / 7 failed** — the 7 failures
  are exactly the pre-existing maintainer-gated `tests/test_gates_workflow.py`; **zero new
  failures** from this session. (Prior baseline 4624/51/7 at Cycle 246; +22 passed = 19 new H193
  tests +1 artifact-schema parametrize +2 auto-globbed runner-contract cases. `src/qtr` untouched
  → coverage unaffected at 100%.)
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **368 files already formatted**
  (was 367 failing-on-1; +2 = new runner + new test; the probe script baseline fix).
- `python run_nf_20261121_03_bab_beta.py --download-only` → 98/98 names with enough history.
- No `src/qtr` edit, no gate weakening, no published/certified artifact/threshold modified.

## Remaining unresolved

- **`tests/test_gates_workflow.py` — 7 failures** because `.github/workflows/gates.yml` is
  unpatched (unchanged from the Cycle 246 handoff). The test pins: `scripts/**` in both
  `push`/`pull_request` path filters, `scripts` in both ruff targets, `python -m pip install -e .
  --no-deps` in both jobs, and `python scripts/backtest_perf_regression_gate.py` in
  `research_gates`.
- Fix = maintainer applies `patches/0001-gates-workflow-contract-fix.patch`
  (`.github/workflows/gates.yml`), commits, pushes. **Agent-unreachable**: `.github/workflows/**`
  is restored from `origin/main` after every session (`.github/scripts/kilo-controller.sh`) and the
  repo-scoped GitHub App token has no `workflows` permission, so an in-tree edit does not persist.
- Evidence the fix works: the patch applied in a clean `/tmp` checkout makes
  `pytest tests/test_gates_workflow.py` → 7 passed (re-verified Cycles 106, 121, 235, 245, 247;
  still red here because the workflow file is intentionally unpatched).

## Approaches already failed / do not repeat

- In-tree edit of `.github/workflows/gates.yml`: does not persist (restored from origin/main; token
  lacks workflows permission). Do not retry.
- Do not re-run H187/H188/H190/H191/H192/H193 (or any exhausted family) as a
  parameter/universe/window variant; the full-window pre-registered runs are the record.

## One precise next task (for the next agent)

Select and execute the next **distinct** new strategy family (Cycle 248 → H194). Two
already-scored, genuinely-distinct, offline-feasible deferred candidates from the Cycle 247
discovery scan are queued — pick one and run it pre-registered with the standard 8 gates:

1. **NF-20261121-04 stock-level coskewness / systematic skewness** (Harvey & Siddique 2000;
   category: higher-moment risk / lottery demand). Distinct from H93 (idiosyncratic vol) and
   H124/125 (MAX) — the observable is the *systematic* co-skewness with the market, not residual
   vol or a single-day max. Offline-feasible on the cached yfinance close panel
   (`.cache/xbrl/equity_closes.csv`, 98 names). Constrain: pre-register the universe
   (S&P100 − XOM/BKNG, ≥252 returns), the coskewness estimator and its PIT/causality, a bounded
   ≤16-cell grid, train-only WF selection, protected test, standard 8 gates, and a collinearity
   diagnostic vs beta/IVOL. Do not re-declare the close panel or higher-moment risk as blocked.
2. **NF-20261121-05 beta-dispersion / aggregate-beta regime timing** — but note this is
   **scored low (2) on novelty** because it is a scalar market-timing overlay adjacent to the
   executed H117 average-beta regime / H29. Prefer candidate 1 unless the coskewness construction
   proves infeasible offline, in which case document the blocker and leave candidate 2 as a
   documented variant rather than running it as a "new" family.

Constraint reminder: keep `src/qtr` unchanged, preserve the 100% coverage / Ruff /
warning-as-error / protected-holdout gates, use free/public data only, and do not weaken any
gate to make a candidate pass. After executing, record the cycle in
`NEW_FAMILY_RESEARCH_REGISTER.md`, update the `AGENTS.md` stale H-range note additively, and
recompute the `tests/test_experiment_artifact_schema.py` inventory pins.