# Next Task

## Where to resume

Cycle 254 (2026-11-22). `src/qtr`, all runners, tests, and every completed NF experiment
(`.experiments/nf_runs/nf_*`) are complete and preserved unchanged. **Cycle 254 produced a
decision-grade root-cause diagnostic of the H187–H197 reject streak** (not a new strategy family):
new `scripts/analyze_equity_cross_section_rejects.py` (read-only, stdlib-only, offline) and
`tests/test_analyze_equity_cross_section_rejects.py` (**15 passed**). No artifact, gate, verdict,
threshold, or frozen number was touched; `src/qtr` is unchanged.

## Cycle 254 (2026-11-22) — root-cause decomposition of the H187–H197 reject streak (diagnostic)

- **Why.** Cycle 253 asserted "the passive equal-weight long book dominates" and called the
  11-cycle streak a "universe/benchmark problem", but qualitatively. Directive §6 requires the
  blocker to be identified as data / execution / capital / power / weak-mechanism before declaring
  exhaustion. This cycle quantifies it from the *committed* `summary.json` artifacts.
- **How.** The script keeps the 9 equity cross-sections (identified by `data.universe_symbols`; the
  CFTC commodity and Binance crypto runs record a generic `universe` and are excluded) and reports,
  per run, OOS strategy Sharpe, passive-book Sharpe, beta to the passive book, information ratio,
  and annualised alpha.
- **Result (own evidence).** Median OOS Sharpe **strategy 0.187 vs passive book 1.075**; beta range
  **[-0.522, +0.841]** (3 long-biased / 5 market-neutral / 1 short-biased); **negative IR 9/9**;
  alpha 6 negative / 3 positive. Full per-run table is in `NEW_FAMILY_RESEARCH_REGISTER.md`
  §Cycle 254.
- **Finding (refines the structural diagnosis).** The streak is **not** a uniform long-bias
  artifact: strategies span short-biased (BAB, beta -0.522) → market-neutral (accruals, beta -0.009,
  OOS Sharpe 0.187 vs passive 1.075) → long-biased (distress, beta 0.841), and **every** run has
  negative IR. So the binding constraint is **genuine mechanism weakness (no alpha) against a strong
  equal-weight bull-market benchmark in a survivorship-biased mega-cap universe**, not a
  construction/beta mismatch. Re-benchmarking or re-weighting the *same* 98 names cannot rescue the
  program; escaping requires a **higher-dispersion universe** (more names / mid-small-cap / ex-US
  PIT) or formally closing the equity-cross-section program — both maintainer decisions (directive §2).

## Verified this session (Cycle 254)

- **Full suite: `python -m pytest -q` → 4762 passed / 51 skipped / 7 failed.** Net +15 passing
  tests (4747→4762) from the new diagnostic suite. The 7 are the pre-existing, agent-unreachable
  `tests/test_gates_workflow.py` failures (unchanged from Cycles 250–253).
- **`ruff check` + `ruff format --check` clean** on `src tests run_*.py scripts`.
- **Coverage:** `src/qtr` untouched → the 100% source/branch coverage gate is unaffected.
- **Offline / dependency-free:** the diagnostic uses only the standard library and reads committed
  artifacts; no network, no artifact writes.

## Unresolved work (maintainer / authorization only — NOT agent-executable)

1. **Workflow contract patch (agent-unreachable, maintainer action).** `origin/main:.github/workflows/gates.yml`
   is intentionally unpatched; 7 tests in `tests/test_gates_workflow.py` expect `-W error`, explicit
   `--cov=qtr`, `--cov-branch`, `scripts/**` in ruff targets and path triggers,
   `python -m pip install -e . --no-deps`, and `python scripts/backtest_perf_regression_gate.py`.
   Agent edits to `.github/workflows/**` are discarded by `.github/scripts/kilo-controller.sh`
   (restore from `origin/main` + staging exclude) and the repo token lacks `workflows` permission.
   **Apply-ready fix: `patches/0001-gates-workflow-contract-fix.patch`** (gates.yml only), still
   guarded green by `scripts/verify_gates_workflow_patch.py`
   (`pytest tests/test_verify_gates_workflow_patch.py` → 15 passed). Apply on `origin/main`:
   `git apply --check patches/0001-gates-workflow-contract-fix.patch && git apply
   patches/0001-gates-workflow-contract-fix.patch`. Do **not** retry an in-tree workflow edit.
2. **Universe/benchmark decision (the actual research bottleneck).** Cycle 254 shows that escaping
   the REJECT streak requires a higher-dispersion universe (or formally closing the equity
   cross-section program). This is out of agent scope per directive §2. Authorize a mid/small-cap or
   ex-US PIT universe, or close the program.
3. **Authorization-gated reproducibility artifact cleanup (non-blocking).**
   `REPRODUCIBILITY_AUDIT_REPORT.md` #6 (11 artifact hash_mismatches, 24h) and #5 (rebuild-excluded
   artifacts, 7d). Safe cleanup would reduce hash_mismatches to 3 (legitimate 24h PIT recutoff
   differences). Requires explicit authorization; do not do without it. The suite is green
   (4762/51/7) without this.

## Approaches already tried and why they failed (do not blindly repeat)

- **New equity cross-section on the 98-name survivorship-biased S&P 100 (H187 accruals, H188
  issuance, H191 value, H192 innovation, H193 beta, H194 coskewness, H195 delay, H196 turnover,
  H197 distress): ALL REJECT.** Cycle 254 now shows *why*: no alpha against a strong passive book,
  across the full beta spectrum. There is no further equity cross-section on this universe to run —
  the mechanism space is exhausted, not the data. Do not run another one.
- **Re-editing `.github/workflows/gates.yml` in a commit: fails every session** (controller restores
  it; fix not agent-reachable). Capture/verify via `patches/` + `scripts/verify_gates_workflow_patch.py`
  only.
- **Classifying a candidate "data-blocked" without probing the named source.** FRED (Cycle 140),
  `data.binance.vision` (Cycle 213), Chinese futures SHFE/INE/CZCE/CFFEX (Cycle 214), and SEC XBRL
  (Cycle 230) all serve data older registers declared unavailable. Always probe first.
- **Declaring exhaustion from a stale inventory.** Cycle 251 did this; Cycle 252 corrected it. Always
  reconcile against `.experiments/nf_runs/*` and `HYPOTHESIS_SPEC.md` H-ID verdicts first.
- **Computing returns on the unaligned yfinance grid for a rolling-vol signal.** H195 and H197 both
  hit this. Always calendar-align ffilled closes before `pct_change` (the H191 convention).

## Precise next task (one bounded task)

The agent-executable equity-cross-section mechanism space is exhausted and Cycle 254 has now
quantified the structural cause (no alpha vs a strong passive book, across the full beta spectrum).
**Do not run another 98-name equity cross-section and do not fabricate H198.**

If the maintainer **authorizes a higher-dispersion universe** (mid/small-cap or ex-US PIT), the
bounded agent task is to re-run `scripts/analyze_equity_cross_section_rejects.py` on that universe
and execute **one** anomaly there (H198), pre-registered in `HYPOTHESIS_SPEC.md`.

If the maintainer does **not** authorize a new universe, the only remaining work is item 1 (the
workflow patch, maintainer-only). A concrete, agent-executable, read-only extension that is
available offline and does **not** repeat a rejected construction: extend the Cycle 254 diagnostic to
also report the train → val → test Sharpe path from each committed `summary.json` (`full_sample` /
`val` / `test` / `oos_val_test` are all present), quantifying the in-sample→out-of-sample decay of
each anomaly as further evidence for the universe decision. This is bounded, offline, and additive.

## Commit

This session added `scripts/analyze_equity_cross_section_rejects.py`,
`tests/test_analyze_equity_cross_section_rejects.py`, and the Cycle 254 register entry. The
maintainer workflow patch (item 1) is a separate maintainer action on `origin/main`.