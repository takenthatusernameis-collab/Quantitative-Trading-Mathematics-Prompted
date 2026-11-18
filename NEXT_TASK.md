# Next task (2026-11-18, Cycle 214)

## What changed this session
- **Executed the assigned probe instead of leaving the data blocker unproven.** The prior
  handoff's agent task was: "the only non-adjacent mechanism class still untested is
  commodity per-contract term structure — probe a free PIT per-contract source read-only
  first and record the result." Done, and the result is a **correction**: the data exists
  free and key-less on the Chinese futures exchanges.
- **New durable artifacts:**
  - `scripts/probe_commodity_termstructure_availability.py` (read-only; downloads to memory;
    per-date contracts/products/curves plus a front/second spread proof; exit 1 if nothing
    parses; still-blocked sources documented in the module docstring).
  - `tests/test_probe_commodity_termstructure_availability.py` — **20 tests** (URL builders,
    SHFE/INE JSON incl. legacy rows without `PRODUCTGROUPID`, CZCE pipe text incl. legacy GBK
    and 3-digit `YMM` decade normalization, CFFEX GBK CSV with option-row filtering,
    term-structure selection/spread, probe statuses, `main` exit codes).
- **Docs recorded (durable):** `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 214 entry,
  `HYPOTHESIS_SPEC.md` Cycle 214 data-correction section, `AGENTS.md` free-data note,
  `HANDOFF.md` Cycle 214 banner, this file. Lineage unchanged: **H1–H183 exhausted/rejected,
  H184 unassigned** (now *executable*).
- **No change** to `src/qtr`, runners, gates, `.experiments`, sidecars/hashes, frozen numbers,
  or `.github/workflows/**`. No H-ID executed; no gate weakened; no parameter/universe variant
  of H183 run.

## Probe evidence (own live run, 2026-11-18; exit 0, 4/4 sources usable)
| Source | URL (key-less) | Coverage verified | 2024-01-02 cross-section |
|---|---|---|---|
| SHFE | `https://www.shfe.com.cn/data/tradedata/future/dailydata/kx{YYYYMMDD}.dat` (JSON) | 5/5 probe dates, 2010-01-04 → 2026-11-17 | 275 contracts / 23 products / 23 curves; RB 2401/2402 **+212.7 bps** |
| INE | `https://www.ine.cn/data/tradedata/future/dailydata/kx{YYYYMMDD}.dat` (JSON) | 2020/2024/2026 OK; HTTP 200 on 2018-03-26 (crude launch) | 61 / 5 / 5; LU 2402/2403 +52.9 bps |
| CZCE | `http://www.czce.com.cn/cn/DFSStaticFiles/Future/{YYYY}/{YYYYMMDD}/FutureDataDaily.txt` (pipe text; UTF-8 new / GBK legacy) | 2016/2020/2024/2026 OK; earliest 200 probed 2015-12-01 | 214 / 25 / 25; TA 202401/202402 −57.3 bps |
| CFFEX | `http://www.cffex.com.cn/sj/hqsj/rtj/{YYYYMM}/{DD}/{YYYYMMDD}_1.csv` (GBK CSV) | 2016/2020/2024/2026 OK; 2010-01-04 EMPTY (listed 2010-04) | 28 / 8 / 8; IC 2401/2402 +20.0 bps |

Still blocked (probed this session, named): Nasdaq/Quandl CHRIS deferred contracts → HTTP 403
(Incapsula; free tier key-gated); CME settlement APIs → 403 IP block; Yahoo single-contract
tickers → 429 (persisted across a 20 s backoff); stooq → JS challenge; LME daily API →
Cloudflare 403; DCE daily POST → 412.

## What was actually verified (own evidence, 2026-11-18)
- `python scripts/probe_commodity_termstructure_availability.py` → live 4/4 usable, exit 0
  (table above).
- `python -m pytest -q tests/test_probe_commodity_termstructure_availability.py` → **20 passed**.
- `python -m ruff check src tests run_*.py scripts` → All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` → **345 files already formatted**.
- Full pinned suite `python -m pytest -q -W error --cov=qtr --cov-branch
  --cov-report=term-missing --ignore=tests/test_gates_workflow.py` → **4401 passed,
  51 skipped, 0 failed** (664.90 s), `src/qtr` coverage **100.00%** (1692 stmts / 642
  branches / 0 miss).
- `python scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.783 s < 5 s,
  10.7 MB peak, 13668 trades).
- `python -m pytest -q tests/test_experiment_artifact_schema.py` → **107 passed** (no new
  `.experiments` dirs, so inventory pins are unchanged).
- Baseline contract checks: `scripts/verify_gates_workflow_patch.py` → 7 live violations,
  patch still valid, exit 0; `pytest -q tests/test_gates_workflow.py` → 7 failed (known,
  maintainer-gated).

## What remains unresolved
- **Maintainer-gated (agent-unreachable):** apply/push
  `patches/0001-gates-workflow-contract-fix.patch` with `workflows`-scoped credentials.
- **H184 is not pre-registered.** Pre-registration must precede inspection of any forward
  return or validation/test outcome. The probe only established data availability.
- **Reproducibility backlog (frozen, authorization-gated):** missing_files=197,
  hash_mismatches=11, orphaned_files=528, missing_meta_files=0.

## One precise next task
**Maintainer:** `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am
"fix(ci): satisfy gates workflow contract" && git push origin main`, then
`python scripts/verify_gates_workflow_patch.py` (expect `CONTRACT SATISFIED`) and
`python -m pytest -q tests/test_gates_workflow.py` (expect 7 passed).

**Agent — pre-register and execute H184 (commodity term-structure carry), in this order:**

1. **Pre-register first, in `HYPOTHESIS_SPEC.md`**, before downloading any forward return:
   - **Mechanism.** Physically delivered futures embed inventory/carry: a curve sloping down
     (front > deferred, backwardation) pays a long position positive roll yield as it ages,
     and vice versa in contango; hedgers pay speculators to warehouse. Null (H0): the
     front/second settlement slope has no predictive power for next-period roll-adjusted
     returns after CNY costs, i.e. no incremental value over a passive front-month long book.
   - **PIT timing.** The cross-section file is the official settlement record for trade date t.
     Signal from settlements known at t's settle; positions formed no earlier than t+1 (use
     `shift(1)` explicitly and add a lookahead test).
   - **Universe (declare first-available dates).** Start with SHFE liquid products: RB, CU, AL,
     ZN, AU, AG; INE: SC (from 2018-03). Optional breadth: CZCE TA, MA, SR (from 2015-12).
     Exclude contracts whose delivery month equals the current month (delivery-window pricing).
   - **Signal.** Annualized slope `ln(F1/F2) * 12 / months_between(F1, F2)` using the two nearest
     contracts with settlement > 0 and open interest above a declared floor; cross-sectional
     rank long top-k / short bottom-k (k declared), equal weight; hysteresis entry/exit
     thresholds from a small bounded grid selected on train-only walk-forward.
   - **Sample.** 2016-01-04 → 2026-11-17 (bounded first scope; extend SHFE to 2010 only if the
     download budget allows). Train →2023-06-30; Val 2023-07-01→2024-12-31; Test protected
     2025-01-01→2026-11-17.
   - **Costs (CNY, explicit).** Commission + slippage + roll crossing modelled at a declared
     bps/side (no US/EU cost assumptions); note T+1 and daily price limits as constraints.
   - **Gates (OOS Val+Test, fail-closed, same 8).** Sharpe≥1.0; trades≥50; PF≥1.3; maxDD≤15%;
     WF stability≥0.7; worst rolling-252 Sharpe≥0.3; benchmark p≤0.05 with IR≥0 vs the passive
     front-month long book; perturbation min ratio≥0.5.
   - **Ablations/falsifiers.** Passive front-month long; random ranking (same active days, seed
     42); inverse-slope; OAT ±20% perturbation.
2. **Implementation constraints.**
   - Resumable on-disk cache (skip existing files) under `.cache/commodity_settlements/…`;
     one request per trade date per venue (~4,000 dates for full SHFE) — cache and a bounded
     date range are mandatory; tolerate 404 holidays and record per-product first dates.
   - Reuse the parsers/URL builders from `scripts/probe_commodity_termstructure_availability.py`
     (import them, do not fork a second copy).
   - Artifact under `.experiments/nf_runs/<name>_<timestamp>/summary.json` + `grid.csv`;
     update `tests/test_experiment_artifact_schema.py` inventory pins only if a new artifact
     directory is committed (Cycle 213 precedent: 109→110 / 101→102).
3. **Verification before reporting:** focused tests (incl. lookahead/causality and parser
   fixtures), `ruff check`, `ruff format --check`, the full pinned coverage suite, and
   `python scripts/backtest_perf_regression_gate.py`.

## Approaches already tried and why they should not be repeated
- Do not classify commodity per-contract roll/contango as data-blocked (probed 2026-11-18,
  4/4 Chinese sources usable); do not re-probe CHRIS/CME/Yahoo/stooq/LME/DCE as "maybe free".
- Do not re-run H183 or its variants; its record is `…_20261118_194621` (REJECT 6/8).
- Do not treat product add/drop, window shifts, or threshold changes as new families.
- Do not edit `.github/workflows/**` or weaken `tests/test_gates_workflow.py`.
- Do not edit momentum runners' `param_grid_results` logging without maintainer authorization.
- Do not trust handoff pass/fail/coverage counts — re-run the gates.

## HEAD
- `9c64cef` at session start (Cycle 214 adds the probe script, its tests, and docs; the
  controller checkpoints them, `.github/workflows/**` excluded from staging).
