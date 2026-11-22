# Next Task

## Where to resume

Cycle 254 (2026-11-22). `src/qtr`, all runners, tests, and every completed NF experiment
(`.experiments/nf_runs/nf_*`) are complete and preserved unchanged. **Cycle 253 executed H197
(capital-structure / financial-distress cross-section) — the one remaining genuinely-distinct,
free-data-feasible mechanism — and recorded an honest REJECT (1/8).** New this cycle:
`run_nf_20261122_02_financial_distress.py`, `tests/test_nf_20261122_02_financial_distress.py` (24
passed), one artifact `nf_20261122_02_financial_distress_20261122_033354/`, register + spec + these
docs updated. `src/qtr` untouched; no gate weakening; no published number changed.

## Cycle 253 (2026-11-22) — H197 capital-structure / financial-distress cross-section (EXECUTED, REJECT 1/8)

- **What changed (durable).** Executed the handoff's precise next task (option 2). H197 sorts the
  98-name S&P-100-minus-2 universe by a **solvency / bankruptcy-risk** characteristic (book market
  leverage `equity_to_debt` and Merton-style `distance_to_default`) — a genuinely-distinct return
  mechanism vs H187–H196 (accruals/issuance/profitability/value/innovation/beta/coskewness/delay/
  turnover). Reused the H191 share-count loader + H187/H184 backtest/metric/gate primitives + H191
  long-high hysteresis weights; only the distress row loader and the leverage/DD panel are new code.
  PIT by max(filed), monthly refresh, engine shift(1), 5 bps one-way costs (no borrow cost modelled,
  disclosed optimistic), standard 8 gates unchanged (two-sided benchmark p preserved).
- **Result.** Selected `equity_to_debt`, k=10, vol_target=0.10 (train-only WF). **OOS Sharpe 0.522**,
  PF 1.094, maxDD -15.59%, worst-regime -1.260, 12276 trades. Passive equal-weight long benchmark
  **1.029** dominates; IR -0.846, two-sided p 0.0574. Inverse (anti-distress) -0.538 — direction
  NOT inverted (both signs weak). Train collinearity e2d-vs-DD 0.973 (expected); mechanism
  separation vs beta/momentum/vol all |<0.17| (confirms distinct). **REJECT 1/8** (only the genuine
  trades gate passes; no negative/negative-ratio artifacts). 96/98 names had capital-structure data
  — distress is NOT data-blocked; it failed on mechanism strength/dispersion in mega-caps.
- **Verified this session.** Full suite `python -m pytest -q` → **4747 passed / 51 skipped / 7 failed**
  (the 7 are the pre-existing agent-unreachable `tests/test_gates_workflow.py` failures, unchanged);
  ruff check + format clean on `src tests run_*.py scripts` (376 files). Artifact-schema pins updated:
  TOTAL_DIRS 122→123, SUMMARY_COUNT 114→115, DISTINCT_KEYS 157→158 (new collinearity key; >=50%/
  >=80% key sets unchanged).
- **Bug fixed during the cycle (durable).** The first H197 run silently zeroed the `distance_to_default`
  panel (sigma all-NaN) because daily returns were computed on the unaligned yfinance grid (NaN on
  every market holiday, so a 252-day rolling vol never reached min_periods). Fixed by calendar-aligning
  ffilled closes before `pct_change` (the H191 convention) — guarded by two regression tests. The broken
  first artifact was deleted; the recorded artifact is the corrected run.
- **Approaches already tried / structural finding.** H187–H197 (11 consecutive long-short
  cross-sections) all REJECT on this universe because the passive equal-weight long book (OOS Sharpe
  ~1.0–1.17) dominates and distress/liquidity/quality dispersion is minimal in 98 survivorship-biased
  mega-caps. This is a universe/benchmark problem, not a mechanism-search failure; escaping it is a
  maintainer decision (item 3 below).

## Cycle 253 session verification (prior, 2026-11-22)

- **Pushed `daea2dd` (Cycle 252 record correction) to `origin/main`** — the Cycle 252 register correction (`NEW_FAMILY_RESEARCH_REGISTER.md` + `NEXT_TASK.md`) is now durable on `origin/main`.
- **Re-confirmed `tests/test_gates_workflow.py` → 7 failed** — all failures are because `.github/workflows/gates.yml` is unpatched. Agent-unreachable: `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` after every session, excludes workflow paths from staging, and the repo token lacks `workflows` permission. The apply-ready fix is already captured at `patches/0001-gates-workflow-contract-fix.patch` (verified clean-apply; `pytest tests/test_gates_workflow.py` → 7 passed in clean `/tmp` checkouts at Cycles 104/106/121).
- **Ruff check and format: clean** on `src tests run_*.py scripts` (374 files formatted).
- **H197 (capital-structure / financial distress) evaluated and declined as the next task.** It repeats the H187–H196 long-short cross-section construction on the same 98-name survivorship-biased S&P-100-minus-2 mega-cap universe — all 10 (H187–H196) REJECTed because the passive equal-weight long book (OOS Sharpe ≈1.0–1.17) dominates. Per rule 2 (change approach after repeated failure), do not run an 11th cross-section on the same failed construction. Listed under "approaches already tried and why they failed" in §Cycle 252.
- **No agent-executable bounded task produces durable progress in this session.** Source, runners, tests, artifacts, gates, coverage, and thresholds are all complete and frozen. The only remaining work is the maintainer-applied workflow contract patch (item 1 below).

## What changed this cycle (Cycle 253, durable, evidence-based)

- **Executed H197 (capital-structure / financial-distress cross-section).** New runner
  `run_nf_20261122_02_financial_distress.py`, new tests
  `tests/test_nf_20261122_02_financial_distress.py` (24 passed), new artifact
  `.experiments/nf_runs/nf_20261122_02_financial_distress_20261122_033354/`. Reused the H191
  share-count loader, H187/H184 backtest/metric/gate primitives and H191 long-high hysteresis; only
  the distress row loader (Liabilities + shares, PIT by max(filed)) and the `equity_to_debt` /
  `distance_to_default` panel are new code. **Verdict REJECT 1/8** (OOS Sharpe 0.522 vs passive
  benchmark 1.029; only the genuine trades gate passes).
- **Recorded the honest verdict** in `NEW_FAMILY_RESEARCH_REGISTER.md` (Cycle 253 entry + lineage),
  `HYPOTHESIS_SPEC.md` (new `## H197` pre-registration + execution-result section), and this file.
- **Updated the artifact-schema inventory pins** in `tests/test_experiment_artifact_schema.py`:
  TOTAL_DIRS 122→123, SUMMARY_COUNT 114→115, DISTINCT_KEYS 157→158 (new key
  `train_input_collinearity_equity_to_debt_vs_distance_to_default`; >=50% / >=80% key sets unchanged).
- **Fixed a silent H197 data bug** (durable): the first run zeroed the `distance_to_default` panel
  because daily returns were computed on the unaligned yfinance grid (NaN on market holidays → a
  252-day rolling vol never reached min_periods). Fixed by calendar-aligning ffilled closes before
  `pct_change` (the H191 convention); guarded by two regression tests. The broken artifact was
  deleted; the recorded artifact is the corrected run.

## Verified this session (Cycle 253)

- **Full suite: `python -m pytest -q` → 4747 passed / 51 skipped / 7 failed.** The 7 are the
  pre-existing, agent-unreachable `tests/test_gates_workflow.py` failures (unchanged from
  Cycles 250–252). Net +23 passing tests (4724→4747) from the new H197 suite.
- **Ruff check + format: clean** on `src tests run_*.py scripts` (376 files formatted).
- **Coverage:** `src/qtr` untouched, so the 100% source/branch coverage gate is unaffected.
- **Environment:** dependencies were already installed this session (`numpy 2.5.5 / pandas 3.1.1 /
  scipy 1.18.1 / yfinance 1.8.0`); the H197 data came from the cached `.cache/xbrl/` companyfacts
  bundles (96/98 names) and cached `equity_closes.csv` — no network needed.

## Accurate research state (Cycle 253)

Free-data family discovery on the **98-name survivorship-biased S&P-100-minus-2 mega-cap universe**
is now exhausted across **all** genuinely-distinct equity cross-section mechanisms. H1–H197 are all
executed and rejected; H189 is data-blocked (gross profitability, 28–29/98 names). The **structural
root cause** of the 11-cycle REJECT streak (H187–H197) is that the **passive equal-weight long book
(OOS Sharpe ≈1.0–1.17) dominates** every long-short anomaly, and several anomalies are sign-inverted
yet still fail the ≥1.0 gate. That is a universe/benchmark problem, not a mechanism-search failure;
per directive §2, changing universe/benchmark is **not** a new family and is a maintainer decision.

### Remaining candidates (honest status)

- **Capital-structure / financial distress (H197): EXECUTED, REJECT 1/8 (Cycle 253).** No longer a
  candidate — it was the last genuinely-distinct free-data-feasible equity cross-section mechanism.
  NOT data-blocked (96/98 names have PIT liabilities + shares); it failed on mechanism
  strength/dispersion in mega-caps.
- **Blocked (data/power):** S&P 500 inclusion/deletion (external calendar, low power), Russell 2000
  reconstitution (annual, low power), stock splits (incomplete free data), options dealer GEX (no
  free historical options chain), earnings-revision momentum (no free PIT revisions),
  dividend-initiation/payout signalling (rare among mega-caps).
- **Variants / adjacency (NOT new families per directive §2):** RSP-SPY breadth relmom, USMV-SPY
  low-vol relmom, holiday/pre-holiday drift, 10Y-3M inversion depth, SPY jump asymmetry,
  realized-kurtosis (NF-20261122-02), beta-dispersion timing (NF-20261122-03).

## Unresolved work (maintainer / authorization only — NOT agent-executable)

1. **Workflow contract patch (agent-unreachable, maintainer action).** `origin/main:.github/workflows/gates.yml`
   is intentionally unpatched; 7 tests in `tests/test_gates_workflow.py` read it and expect
   `-W error`, explicit `--cov=qtr`, `--cov-branch`, `scripts/**` in ruff targets and path triggers,
   `python -m pip install -e . --no-deps`, and `python scripts/backtest_perf_regression_gate.py`.
   Agent edits to `.github/workflows/**` are discarded by `.github/scripts/kilo-controller.sh`
   (restore from `origin/main` + staging exclude) and the repo token lacks `workflows` permission,
   so a committed workflow edit cannot reach `main`. **Apply-ready fix:
   `patches/0001-gates-workflow-contract-fix.patch`** (gates.yml only). Verified clean-apply and
   `pytest tests/test_gates_workflow.py` → 7 passed in a clean `/tmp` checkout at HEAD. Apply on
   `origin/main`: `git apply --check patches/0001-gates-workflow-contract-fix.patch && git apply
   patches/0001-gates-workflow-contract-fix.patch`. Do **not** retry an in-tree workflow edit.
2. **Authorization-gated reproducibility artifact cleanup (non-blocking).**
   `REPRODUCIBILITY_AUDIT_REPORT.md` #6 (11 artifact hash_mismatches, 24h) and #5 (rebuild-excluded
   artifacts, 7d). Safe cleanup would reduce hash_mismatches to 3 (legitimate 24h PIT recutoff
   differences). Requires explicit authorization; do not do without it. Full suite is green
   (4747/51/7) without this.
3. **Maintainer decision to escape survivorship-bias / passive-book dominance.** With H197 REJECT,
   there is now **no** remaining genuinely-distinct free-data equity cross-section mechanism on this
   universe. The only way to make the "keep discovering new families" mandate productive is a
   different universe/benchmark (mid/small-cap or ex-US PIT universe, or a non-passive benchmark), or
   formally closing the equity-cross-section program as exhausted. Out of agent scope per directive §2.

## Approaches already tried and why they failed (do not blindly repeat)

- **New equity cross-section on the 98-name survivorship-biased S&P 100 (H187 accruals, H188
  issuance, H191 value, H192 innovation, H193 beta, H194 coskewness, H195 delay, H196 turnover,
  H197 distress): ALL REJECT.** Passive equal-weight long book (OOS Sharpe ~1.0–1.17) dominates;
  every anomaly's OOS Sharpe is far below the ≥1.0 gate and several are sign-inverted. There is no
  further equity cross-section on this universe to run — the mechanism space is exhausted, not the
  data. Do not run another one.
- **Re-editing `.github/workflows/gates.yml` in a commit: fails every session** (controller restores
  it; fix not agent-reachable). Capture/verify via `patches/` + this file only.
- **Classifying a candidate "data-blocked" without probing the named source.** FRED (Cycle 140),
  `data.binance.vision` (Cycle 213), Chinese futures SHFE/INE/CZCE/CFFEX (Cycle 214), and SEC XBRL
  (Cycle 230) all serve data older registers declared unavailable. Always probe first. Conversely,
  the "deferred" tables are stale: many entries (H85/H86/H176/H177/H180/H181/H182/H184/H119/H175)
  were executed after being listed as deferred — verify status against artifacts before deciding.
- **Declaring exhaustion from a stale inventory.** Cycle 251 did this (claimed NF-01/NF-02 never
  executed). Always reconcile the inventory against `.experiments/nf_runs/*` and `HYPOTHESIS_SPEC.md`
  H-ID verdicts before declaring exhaustion.
- **Computing returns on the unaligned yfinance grid for a rolling-vol signal.** H195 and H197 both
  hit this: a 252-day rolling vol over raw yfinance returns (NaN on market holidays) never reaches
  min_periods and silently zeros the panel. Always calendar-align ffilled closes before `pct_change`
  (the H191 convention) when the signal uses a trailing volatility.

## Precise next task (one bounded task)

The agent-executable equity-cross-section mechanism space is now exhausted (H197 REJECT closed it).
Pick **one** of these, in order of value:

1. **Maintainer/authorization (highest value, NOT agent-executable):** apply
   `patches/0001-gates-workflow-contract-fix.patch` on `origin/main` to clear the 7
   `test_gates_workflow.py` failures, and decide the universe/benchmark question (item 3 above). This
   is the only path that makes further *productive* research possible.
2. **If a NEW free-data mechanism outside equity cross-sections on this universe is mandated
   (agent-executable):** search genuinely-distinct mechanism categories that do **not** reduce to a
   parameter/instrument/universe/timeframe variant of an executed family (directive §2) — e.g.
   non-equity or event/flow/auction mechanisms with free PIT data. Reuse the existing engine and data
   pipeline; pre-register in `HYPOTHESIS_SPEC.md`, add a runner + focused tests, run the standard 8
   gates, record the honest verdict. Do **not** run another single-stock equity cross-section on the
   98-name mega-cap universe and do **not** fabricate a PASS.
3. **If neither is authorized:** this session's durable output is the H197 REJECT record + the
   corrected distance-to-default panel. Preserve it and leave this handoff.

## Commit

Stage only the Cycle-253 files: `run_nf_20261122_02_financial_distress.py`,
`tests/test_nf_20261122_02_financial_distress.py`,
`tests/test_experiment_artifact_schema.py`, `NEW_FAMILY_RESEARCH_REGISTER.md`,
`HYPOTHESIS_SPEC.md`, `NEXT_TASK.md`, and the new artifact
`.experiments/nf_runs/nf_20261122_02_financial_distress_20261122_033354/`. Then commit with a
message such as:
`H197 (Cycle 253): capital-structure / financial-distress cross-section EXECUTED, REJECT 1/8`.
Do not modify `src/qtr`, `.github/workflows/**`, or any frozen number.