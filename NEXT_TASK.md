# Session complete (2026-11-21, Cycle 246 — H192 recorded + tested)

## What changed (this session)

The prior handoff's only assigned task was **maintainer-only** (apply
`patches/0001-gates-workflow-contract-fix.patch`), which is agent-unreachable per
AGENTS.md (`.github/workflows/**` restored from `origin/main`; token lacks `workflows`
permission). With no agent-executable assignment, per the fallback rule I selected and
executed the next on-pattern high-value task (directive §6): a **new strategy family**.

- **H192 (NF-20261121-02, innovation intensity / R&D cross-section) is now fully executed
  and recorded.** New files:
  - `run_nf_20261121_02_innovation_intensity.py` — reuses H184/H187/H191 primitives; new
    R&D+revenue (and R&D/assets) PIT loader from cached SEC XBRL companyfacts; long-high
    (long top-k R&D intensity, short bottom-k) hysteresis signal; standard 8 gates.
  - `tests/test_nf_20261121_02_innovation_intensity.py` — 24 hermetic tests (synthetic
    fixtures, no network/cache): constants, universe, bounded 16-cell grid, PIT `filed`
    rules, revenue-tag fallback, non-10-K exclusion, instant-vs-duration `Assets` loader,
    panel shape/values + a **transpose-bug regression guard**, winsorized z, long-high /
    short-low signal, hysteresis + exit, insufficient-active zeroing, walk-forward
    sentinel/finite, 4-point perturbation, collinearity bounds + a **proportional-panel
    regression guard** (locks the instant-tag fix), and summary/grid artifact assertions.
  - Artifact `.experiments/nf_runs/nf_20261121_02_innovation_intensity_20261121_174135/`
    (summary.json + grid.csv + data_meta.json), runtime 39.447 s.
- Updated `tests/test_experiment_artifact_schema.py` inventory pins (recomputed from the
  corpus): `EXPECTED_TOTAL_DIRS 117→118`, `EXPECTED_SUMMARY_COUNT 109→110`,
  `EXPECTED_DISTINCT_KEYS 151→152` (new key `train_input_collinearity_rd_intensity_vs_rd_to_assets`);
  `EXPECTED_CACHE_ONLY_DIRS` (11), `EXPECTED_KEYS_GE_50_PCT`, `EXPECTED_KEYS_GE_80_PCT`
  unchanged (recomputed). Cycle 246 comment added.
- Recorded H192 (REAL REJECT 3/8) in `NEW_FAMILY_RESEARCH_REGISTER.md` (new Cycle 246 section
  with the §4 three-candidate discovery scan + honest scoring, pre-registration, mechanism
  separation from H187/H188/H189/H191, data availability, execution outcome, lineage map,
  and durable family-status consequence).
- Updated the `AGENTS.md` stale H-range note additively: executed record is now **H1–H192**
  (Cycles 215–246), with H191/H192 artifacts cited.

## H192 result (from `.experiments/nf_runs/nf_20261121_02_innovation_intensity_20261121_174135/summary.json`)

- Mechanism: accounting expenses R&D, so book equity understates intangible capital and the
  market underreacts to the future payoff of R&D (Lev & Sougiannis 1996; Chan-Lakonishok-
  Sottile 1996). Distinct from H187 (accruals/assets), H188 (issuance), H189 (profitability),
  H191 (value = price-scaled); directionally opposite to value (R&D firms have low B/P).
- Universe: 57/98 names with ≥2 annual R&D-and-revenue 10-K observations (measured; well
  above the 40-name minimum — R&D is NOT data-blocked, unlike H189).
- Selected `feature=rd_to_assets, entry_z=1.0, exit_z=0.0, k=10, vol_target=0.10` (train WF
  0.407; train Sharpe 0.660). rd_intensity vs rd_to_assets collinearity 0.913 (denominators agree).
- OOS Val+Test (1272 periods, 16181 trades): Sharpe **0.423**, PF **1.073**, maxDD **−13.63%**,
  worst rolling-252 Sharpe **−0.981**, total return 0.206.
- Gates PASS (3): trades, maxDD, OAT perturbation min ratio (1.051). Gates FAIL (5): Sharpe ≥ 1.0
  (0.423), PF ≥ 1.3 (1.073), WF stability ≥ 0.7 (0.641), worst-regime ≥ 0.3 (−0.981),
  benchmark p ≤ 0.05 with IR ≥ 0 (p 0.0298 but IR −0.968, negative).
- Passive equal-weight long book OOS Sharpe 1.173 (total return 0.849) dominates; random ranking
  −2.971 and inverse signal −0.440 confirm the R&D *sign* is right but the capturable spread is
  below the gate after 5 bps costs — same failure mode as H191 value. **Verdict: REJECT (3/8).**

## What was actually verified (this session)

- `python -m pytest tests/test_nf_20261121_02_innovation_intensity.py` → **24 passed**.
- `python -m pytest tests/test_experiment_artifact_schema.py` → **115 passed** (inventory pins
  updated; +1 from the new summary.json parametrization).
- Runner-wide static contracts over the new `run_nf_20261121_02_*.py` (auto-globbed):
  `test_runner_import_contract`, `test_benchmark_gate_contract`, `test_gate_vacuity_contract`
  → **337 passed**; `test_engine_metric_agreement`, `test_engine_total_return_consistency`,
  `test_causality_invariant`, `test_h57_total_return_audit` → **194 passed / 1 skipped**
  (pre-existing skip).
- Focused regression set (tshmom long-only, runner metric agreement, h29 lookahead sweep,
  h54 non-metrics disclosure, reproducibility audit, experiments.jsonl no-duplicate,
  momentum single grid write, artifact schema, H191, H192) → **292 passed**.
- **Full suite (`python -m pytest -q`): 4624 passed / 51 skipped / 7 failed** — the 7 failures
  are exactly the pre-existing maintainer-gated `tests/test_gates_workflow.py`; **zero new
  failures** from this session. (Prior baseline 4600/48/7 at Cycle 245; +24 passed = the 24 new
  H192 tests, plus artifact-param skips in parametrized artifact tests. `src/qtr` untouched →
  coverage unaffected at 100%.)
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **365 files already formatted**
  (was 363; +2 = new runner + new test).
- No `src/qtr` edit, no gate weakening, no published/certified artifact/threshold modified; the
  H191/H192 full-window runs are the record (not re-run as variants).

## Remaining unresolved

- **`tests/test_gates_workflow.py` — 7 failures** because `.github/workflows/gates.yml` is
  unpatched (unchanged from the Cycle 245 handoff). The test pins: `scripts/**` in both
  `push`/`pull_request` path filters, `scripts` in both ruff targets, `python -m pip install -e .
  --no-deps` in both jobs, and `python scripts/backtest_perf_regression_gate.py` in
  `research_gates`.
- Fix = maintainer applies `patches/0001-gates-workflow-contract-fix.patch`
  (`.github/workflows/gates.yml`), commits, pushes. **Agent-unreachable**: `.github/workflows/**`
  is restored from `origin/main` after every session (`.github/scripts/kilo-controller.sh`) and the
  repo-scoped GitHub App token has no `workflows` permission, so an in-tree edit does not persist.
- Evidence the fix works: the patch applied in a clean `/tmp` checkout makes
  `pytest tests/test_gates_workflow.py` → 7 passed (re-verified Cycles 106, 121, 235, 245; still
  red here because the workflow file is intentionally unpatched).

## Approaches already failed / do not repeat

- In-tree edit of `.github/workflows/gates.yml`: does not persist (restored from origin/main; token
  lacks workflows permission). Do not retry.
- Do not re-run H187/H188/H190/H191/H192 (or any exhausted family) as a parameter/universe/window
  variant; the full-window pre-registered runs are the record.
- Do not force a "new family" that is really an accounting ratio scaled by assets (leverage, ROA,
  asset turnover) — that is the H187/H188/H189 construction and scores low on repository novelty
  (see the Cycle 246 discovery scan). Do not re-declare R&D/intangible or PIT accounting fundamentals
  as data-blocked; SEC XBRL is free/PIT and R&D covers 57/98.
- Do not reintroduce a hard dependency on `.cache/xbrl/**` in tests: that cache is git-ignored and
  absent on fresh checkouts/CI. Tests must be hermetic (synthetic fixtures), as the H192 test is.
  (The *runner* may use the cache/network; the *tests* may not.)
- Pitfall fixed this session (now test-guarded): `Assets` is an XBRL *instant* tag — loading it via
  the duration (340–380 day) filter empties it and silently zeroed the rd_to_assets collinearity
  diagnostic; use `_instant_usd`. And never transpose the dict-of-series panel (reindex(calendar)
  then matches nothing → all-NaN → vacuous flat strategy).

## One precise next task (next session)

**New-family discovery cycle (directive §4) on a genuinely NEW free-data domain not yet probed.**
The free-data S&P 100 SEC-fundamentals + yfinance space is now heavily mined: H187 accruals,
H188 issuance, H189 profitability (data-blocked), H191 value, H192 innovation intensity. The leading
un-probed domain is **SEC Form 13F institutional holdings** (free, public, point-in-time via SEC
EDGAR; ~45-day filing lag) for an *institutional-flow / herding* mechanism distinct from every prior
family. First step is a data-availability probe (mirror `scripts/probe_sec_xbrl_fundamentals.py`)
that measures PIT 13F coverage over a fixed universe **before** any runner is written — do not
assume coverage. If 13F PIT coverage is infeasible, document the blocker and conclude that free-data
S&P 100 discovery is exhausted; the only remaining actionable item is then the maintainer-applied
gates patch above (agent-unreachable). Do not default to maintenance-only work or parameter/universe
variants (directive §6 governing rule).

(End of file - total 88 lines)