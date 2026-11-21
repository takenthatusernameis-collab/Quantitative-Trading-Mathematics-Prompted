# Handoff — Session Verification Complete (2026-11-21)

## Executive Summary
**No agent-executable task remains.** The free-data point-in-time strategy-family queue is exhausted (H1–H195). The only two remaining work items are outside agent scope:
1. **Maintainer workflow patch** (agent-unreachable: token lacks `workflows` permission, `.github/workflows/**` restored from `origin/main` post-session)
2. **Authorization-gated artifact cleanup** (requires explicit authorization; non-blocking)

---

## Verified State (This Session)

### Test Results
| Test Group | Result | Details |
|------------|--------|---------|
| `test_gates_workflow.py` | **7 FAILED** (expected) | Contract pins `scripts/**` in path triggers, `scripts` in ruff targets, `pip install -e . --no-deps` in both jobs, perf gate in `research_gates`. Unpatched on `origin/main` by design. |
| `test_nf_20261121_05_price_delay.py` | **23 PASSED** | H195 bug fix verified; new regression test `test_trailing_delay_handles_per_stock_gaps` passes. |
| `test_experiment_artifact_schema.py` | **117 PASSED** | Schema pins updated for H195 artifact (120→121 dirs, 112→113 summaries, 155→156 keys). |
| Core unit tests (engine, baselines, cost model, statistics) | **526 PASSED** | |
| Frozen contracts (H51, H53, H55, benchmark gate) | **336 PASSED, 47 SKIPPED** | |
| Recent experiments (H191 value, H192 innovation, H193 BAB, H194 coskew, H195 delay) | **84 PASSED** | |
| Focused sibling regression (H191–H195 + artifact schema) | **224 PASSED** (per NEXT_TASK.md) | |

### Code Quality
- `ruff check src tests run_*.py scripts` → **All checks passed**
- `ruff format --check src tests run_*.py scripts` → **372 files already formatted**
- `scripts/backtest_perf_regression_gate.py` → **PERF GATE PASSED** (0.413s, limit 5s, 10.7MB peak)

### Coverage
Per handoff records and Cycle 249 re-verification: **src/qtr 100%** (branch coverage enforced in `pyproject.toml`).

### Repository State
- Working tree: **CLEAN**
- HEAD: `4b6359f` (1 commit ahead of `origin/main`)
- Commit `4b6359f`: "Cycle 249: fix H195 price-delay runner bugs and record valid REJECT (2/8)"
  - Fixed `trailing_delay` all-or-nothing NaN mask bug (was discarding entire day if any name had NaN)
  - Fixed calendar-index alignment bug in `train_mechanism_separation` (KeyError on market holidays)
  - Regenerated valid artifact: `nf_20261121_05_price_delay_20261121_214249` (REJECT 2/8)
  - Added regression test `test_trailing_delay_handles_per_stock_gaps`
  - Updated `AGENTS.md` stale H-range note to **H1–H195** (Cycles 215–249)
  - Updated `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 249 with full H195 record

---

## H195 Result Summary (from regenerated artifact)

| Metric | Value | Gate | Status |
|--------|-------|------|--------|
| OOS Sharpe (Val+Test) | 0.083 | ≥1.0 | **FAIL** |
| Profit Factor | 1.014 | ≥1.3 | **FAIL** |
| Max Drawdown | −14.70% | ≤15% | **PASS** (genuine) |
| Trades | 101 | ≥50 | **PASS** (genuine) |
| WF Stability | 0.107 | ≥0.7 | **FAIL** |
| Worst-regime rolling-252 Sharpe | −1.314 | ≥0.3 | **FAIL** |
| Benchmark p / IR | 0.0697 / −0.808 | p≤0.05, IR≥0 | **FAIL** |
| Perturbation min ratio | −1.66 | ≥0.5 | **FAIL** |

**Verdict: REJECT (2/8)** — Mechanism (Hou-Moskowitz price delay) is weak/non-persistent on liquid mega-caps (train 0.78 → OOS 0.08). Direction NOT inverted (inverse anti-delay Sharpe −0.094). Passive EW benchmark Sharpe 1.128 dominates.

---

## Strategy Family Discovery Status: EXHAUSTED (H1–H195)

| Range | Status | Notes |
|-------|--------|-------|
| H1–H190 | **EXECUTED/REJECTED** | All free-data PIT families tested; none passed gates |
| H189 | **DATA-BLOCKED** | Gross profitability: `CostOfRevenue` 28/100, `CostOfGoodsSold` 29/100 co-reported with Revenues on same 10-K end (below 40-name minimum) |
| H191–H195 | **EXECUTED/REJECTED** | Equity value, innovation intensity, BAB beta, coskewness, price delay — all failed on mechanism strength/direction, NOT data |
| **H196+** | **NOT PRE-REGISTERED** | No candidate clears directive §6 bar (materially different mechanism + free PIT data + smallest decisive test) |

**Durable corrections (per AGENTS.md):**
- Commodity term-structure carry: **NOT data-blocked** (SHFE/INE/CZCE/CFFEX official daily per-contract settlements usable; probe script verified 2026-11-18)
- Crypto funding rates: **NOT data-blocked** (Binance public archives usable; H190 executed on this source)
- Breakeven inflation: **NOT data-blocked** (FRED usable; Cycle 140)
- Beta/coskewness/price-delay cross-sections: **NOT data-blocked** (yfinance close panel; H193/H194/H195 failed on mechanism, not data)

---

## Failed Approaches / Do Not Repeat

1. **In-tree edit of `.github/workflows/gates.yml`** — Does not persist (restored from `origin/main`; token lacks `workflows` permission). Do not retry.
2. **Revert `trailing_delay` per-stock fix to all-or-nothing mask** — Was the bug producing fake all-zero artifact (95% NaN panel, zero positions).
3. **Re-run H195 (or any exhausted family) as parameter/universe/window variant** — Full-window pre-registered run is the record.
4. **Declare any H1–H195 family as data-blocked without naming probed source** — Must cite specific source probed (SHFE/INE/CZCE/CFFEX, Binance archives, FRED, SEC XBRL, yfinance).
5. **Treat parameter/timeframe/universe/market variants as new families** — Requires fresh §4 scan across ≥3 repo-new broad mechanism categories.

---

## Next Task (For Maintainer / Authorized Agent)

### Primary (Maintainer-only)
Apply workflow contract fix:
```bash
git apply patches/0001-gates-workflow-contract-fix.patch
git commit -am "fix(ci): satisfy gates workflow contract"
git push origin main
```
**Evidence it works:** Patch applies cleanly; `pytest tests/test_gates_workflow.py` → 7 passed in clean `/tmp` checkouts (Cycles 104, 106, 121, 235, 245, 247).

### Secondary (Requires Authorization)
Artifact cleanup per `REPRODUCIBILITY_RESTORATION_PLAN.md`:
- Drop 8 superseded `param_grid_results` keys + 3 stale `summary` keys from `.experiments/experiments.jsonl`
- Update `REPRODUCIBILITY_BASELINE` (hash_mismatches 11 → 3), `PINNED_HASH_MISMATCHES`, `REPRODUCIBILITY_AUDIT_REPORT.md`
- Re-run `tests/test_reproducibility_audit.py`

### Deferred (Do Not Treat as New Families Without Fresh §4 Scan)
- Beta-dispersion / aggregate-beta regime timing (scalar market-timing variant of H117/H29)
- Realized-kurtosis / tail-risk cross-section (adjacent to H128/H194 higher-moment families)

---

## Constraints (Unchanged)
- `src/qtr` unchanged unless evidenced defect requires it (then rerun pinned full gates: `pytest -q -W error`, ruff check/format, coverage 100% for `src/qtr`)
- No gate weakening
- No published/certified artifact, verdict, threshold, or frozen number modified without authorization
- No commit/push unless explicitly requested
- Free/public data only
- Protected-holdout gates preserved

---

*Generated 2026-11-21 — Session verification complete. No agent-executable work remains.*