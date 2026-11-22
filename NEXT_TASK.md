# Next Task

## Where to resume

Cycle 252 (2026-11-22). `src/qtr`, all runners, tests, and every completed NF experiment
(`.experiments/nf_runs/nf_*`) are complete and preserved unchanged. This cycle is a §3
**inventory-reconciliation / record-correction** cycle: it corrects two factually false claims in
the Cycle 251 handoff and leaves an accurate executed-vs-untested map. No code, runner, test, or
artifact changed.

Commit for this cycle: the Cycle 252 register append + this file (see "Commit" below).

## What changed this cycle (durable, evidence-based)

- **Corrected two false Cycle-251 claims.** The prior handoff / register line 1987 stated
  "NF-01 VIX term-structure slope (proposed, never executed), NF-02 cross-asset lead-lag (proposed,
  never executed)". Both are false:
  - **NF-20261104-02 (cross-asset lead-lag) = H85, executed, REJECT 2/8.** Runner
    `run_nf_20261104_02_cross_asset_leadlag.py`; `HYPOTHESIS_SPEC.md` `## H85` (OOS Sharpe −1.615).
  - **NF-20261104-01 (VIX term-structure) = H86, executed, REJECT 2/9.** Runner
    `run_nf_20261104_01_vix_termstructure.py`; `HYPOTHESIS_SPEC.md` `## H86` (OOS Sharpe −0.118);
    plus variants H113 / `nf_20261106_26_vix9d_vix_termstructure` / `nf_20261107_34_vix_termstructure_regime`
    (all REJECT).
- **Corrected other stale "Deferred"/"Blocked" table entries that were actually executed:** H176
  (tax-loss), H177 (Treasury auction), H180 (dividend capture), H181 (ES-SPY basis), H182 (insider /
  Form 4 / 13F), H119 (short-term reversal), H184 (commodity carry — was "BLOCKED", unblocked via
  Chinese exchanges), H175 (macro regime / breakeven). Full evidence table:
  `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 252 §3.2.
- **No new H-ID fabricated.** Per directive §4.3/§4.6, H197 is not fabricated and no
  sign-inverted / parameter-variant grid of an executed family is run.

## Verified this session

- **Full suite: `python -m pytest -q` → 4720 passed / 51 skipped / 7 failed.** The 7 are the
  pre-existing, agent-unreachable `tests/test_gates_workflow.py` failures (unchanged from Cycle 250/
  251). Baseline preserved because no code changed.
- **Environment:** dependencies were already installed this session (`numpy 2.5.5 / pandas 3.1.1 /
  scipy 1.18.1 / yfinance 1.8.0`), so the "179 collection errors" did not occur. A fresh checkout
  needs `pip install -r requirements.txt` first; the pre-install errors are the missing-dependency
  symptom, not a regression.
- Ruff clean on changed files (documentation only). No `src/qtr` gate, coverage, or runner touched.

## Accurate research state (Cycle 252)

Free-data family discovery on the **98-name survivorship-biased S&P-100-minus-2 mega-cap universe**
is effectively exhausted. H1–H196 are all executed and rejected; H189 is data-blocked (gross
profitability, 28–29/98 names). The **structural root cause** of the 10-cycle REJECT streak
(H187–H196) is that the **passive equal-weight long book (OOS Sharpe ≈1.0–1.17) dominates** every
long-short anomaly, and several anomalies are sign-inverted yet still fail the ≥1.0 gate. That is a
universe/benchmark problem, not a mechanism-search failure; per directive §2, changing
universe/benchmark is **not** a new family and is a maintainer decision.

### Genuinely untested candidates (the only accurate "remaining" list)

- **Capital-structure / financial distress (Campbell-Hilscher-Szilagyi 2008; Merton 1974
  distance-to-default).** The only remaining free-data-feasible, never-executed, genuinely distinct
  mechanism. Deferred on **novelty (3.90, score 3)**, **not** on data — SEC XBRL + yfinance covers
  ~75/98 names (same PIT loader as H187/H188/H191). Distinct from accruals/value/beta/coskewness/
  delay/turnover. Honest caveat: on 98 mega-caps distress dispersion is minimal → likely trivial
  REJECT, and it is still the same long-short cross-section construction that failed H187–H196.
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
   (4720/51/7) without this.
3. **Maintainer decision to escape survivorship-bias / passive-book dominance.** The only way to make
   the "keep discovering new families" mandate productive is a different universe/benchmark
   (mid/small-cap or ex-US PIT universe, or a non-passive benchmark), or formally closing the
   equity-cross-section program as exhausted. Out of agent scope per directive §2.

## Approaches already tried and why they failed (do not blindly repeat)

- **New equity cross-section on the 98-name survivorship-biased S&P 100 (H187 accruals, H188
  issuance, H191 value, H192 innovation, H193 beta, H194 coskewness, H195 delay, H196 turnover):
  ALL REJECT.** Passive equal-weight long book (OOS Sharpe ~1.0–1.17) dominates; every anomaly's
  OOS Sharpe is far below the ≥1.0 gate and several are sign-inverted. Running another equity
  cross-section on this universe (e.g. capital-structure/distress) repeats this failed construction.
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

## Precise next task (one bounded task)

Pick **one** of these, in order of value:

1. **Maintainer/authorization (highest value):** apply `patches/0001-gates-workflow-contract-fix.patch`
   on `origin/main` to clear the 7 `test_gates_workflow.py` failures, and decide the
   universe/benchmark question (item 3 above). This is the only path that makes further research
   productive.
2. **If a new free-data mechanism is mandated (agent-executable):** execute the one remaining
   distinct candidate — **capital-structure / financial distress (H197)** — reusing the H187/H188/
   H191 XBRL loader (~75/98 names). Pre-register in `HYPOTHESIS_SPEC.md`, add
   `run_nf_<date>_xx_financial_distress.py` + focused tests, run the standard 8 gates, and record the
   honest verdict. Expected outcome is REJECT for the same structural reason; this is acceptable
   per directive §4.6 only as a genuinely-distinct mechanism, not as a re-run of a rejected family.
   Do **not** run any sign-inverted / parameter / universe / window variant of H187–H196, and do
   **not** fabricate a PASS.

## Commit

Stage only `NEW_FAMILY_RESEARCH_REGISTER.md` and `NEXT_TASK.md` (this cycle's record correction),
then commit with a message such as:
`Cycle 252: reconcile research inventory; correct false NF-01/NF-02 "never executed" claims`.
Do not modify `src/qtr`, runners, tests, artifacts, `.github/workflows/**`, or any frozen number.