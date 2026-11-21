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

**No agent-executable new strategy family remains.** H194 (NF-20261121-04, stock-level coskewness /
systematic skewness) was already executed and recorded in Cycle 248:
- Runner `run_nf_20261121_04_coskewness.py` committed (HEAD `82a956a`), artifact
  `.experiments/nf_runs/nf_20261121_04_coskewness_20261121_194429/` present, `tests/test_nf_20261121_04_coskewness.py`
  → 19 passed.
- `tests/test_experiment_artifact_schema.py` inventory pins recomputed:
  `EXPECTED_TOTAL_DIRS 120`, `EXPECTED_SUMMARY_COUNT 112`, `EXPECTED_DISTINCT_KEYS 155` (Cycle 248
  comment added); 136 passed together with the H194 test.
- `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 248 section records H194 **REAL REJECT (2/8)** and
  "H1–H194 exhausted/rejected; H189 data-blocked; `src/qtr` unchanged."
- `AGENTS.md` stale H-range note updated to **H1–H194 exhausted/rejected** (Cycles 215–248).

The deferred candidate **NF-20261121-05 beta-dispersion / aggregate-beta regime timing** is scored low
(2) on novelty — a scalar market-timing overlay adjacent to executed H117 average-beta regime and
H29. Per AGENTS.md / NEXT_TASK constraints, do **not** treat parameter/timeframe/universe/market
variants of H1–H194 as new families, and do **not** re-run any exhausted family as a variant. Do
**not** re-declare coskewness/systematic-skewness cross-sections or the yfinance close panel as
blocked (data is free/public; the mechanism's direction failed on this universe).

The only remaining work items are both outside agent scope:
1. **Maintainer workflow patch (agent-unreachable):** apply `patches/0001-gates-workflow-contract-fix.patch`
   to `.github/workflows/gates.yml` to fix the 7 pre-existing `tests/test_gates_workflow.py` failures.
   `.github/workflows/**` is restored from `origin/main` after every session and the repo token lacks
   `workflows` permission. Do not retry an in-tree edit.
2. **Authorization-gated artifact cleanup (non-blocking):** drop 8 superseded `param_grid_results` keys
   + 3 stale `summary` keys from `.experiments/experiments.jsonl`, update `REPRODUCIBILITY_BASELINE`
   (hash_mismatches 11 → 3), `PINNED_HASH_MISMATCHES`, and `REPRODUCIBILITY_AUDIT_REPORT.md` together,
   then re-run `tests/test_reproducibility_audit.py`. Requires authorization; do not do without it.

Constraint reminder: keep `src/qtr` unchanged, preserve 100% branch coverage / Ruff /
warning-as-error / protected-holdout gates, use free/public data only, do not weaken any gate.

## Session verification (2026-11-21, post-Cycle 248; no code changes)

- `pytest tests/test_nf_20261121_04_coskewness.py tests/test_experiment_artifact_schema.py` → **136 passed** (H194 test 19 + artifact schema 117).
- `python -m ruff check src tests run_*.py scripts` → **All checks passed.**
- `python -m ruff format --check src tests run_*.py scripts` → **370 files already formatted.**
- Working tree clean at HEAD `26bd9fa`; `src/qtr` unchanged → coverage unaffected at 100%.
- Confirmed no agent-executable work remains: H1–H194 exhausted/rejected (H189 data-blocked); remaining items are the maintainer workflow patch (agent-unreachable) and artifact cleanup (authorization-gated).

## Session verification (2026-11-21, this session — no tree changes)

- Baseline: `pytest tests/test_gates_workflow.py` -> **7 failed** (gates.yml unpatched; matches origin/main).
- `git apply --check patches/0001-gates-workflow-contract-fix.patch` -> applies cleanly.
- Throwaway `/tmp/wfverify` copy with patch applied: `pytest tests/test_gates_workflow.py` -> **7 passed** (durable evidence the patch fixes the contract).
- `python -m ruff check src tests run_*.py scripts` -> All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` -> **370 files already formatted.**
- Working tree clean at HEAD `3f4d5c9`; `src/qtr` untouched; coverage unaffected (100%).

No agent-executable change was made: the only fix (workflow patch) is maintainer-applied and agent-unreachable (`.github/workflows/**` restored from origin/main; token lacks `workflows` permission).