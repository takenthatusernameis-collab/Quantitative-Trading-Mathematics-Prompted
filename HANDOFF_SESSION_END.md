# HANDOFF — Experiment Lineage Documentation Complete

## Session Summary (2026-11-12T20:48Z → 2026-11-12T21:00Z)

**Task executed:** Document experiment lineage — automated report from `.experiments/experiments.jsonl` (fallback path per HANDOFF_CURRENT_SESSION.md § "Remaining Audit Work").

**Status:** Completed and verified.

---

## What Changed

### New Files Created
1. `scripts/generate_experiment_lineage_report.py` — Re-runnable script to generate markdown lineage report from `experiments.jsonl`
2. `EXPERIMENT_LINEAGE_REPORT.md` — Comprehensive report (333 lines) documenting all 173 experiment records

### No Modifications To
- `src/qtr/` — **Unchanged** (0 modifications)
- Test suite — Unchanged
- Frozen contracts, gates, thresholds — Unchanged
- Published artifacts, verdicts — Unchanged
- `.experiments/experiments.jsonl` — Read-only source

---

## What Was Verified

| Check | Command | Result |
|-------|---------|--------|
| Core unit tests (config, cost model, statistics, backtest engine, data fetcher) | `PYTHONPATH=src python -m pytest tests/test_config.py tests/test_cost_model.py tests/test_statistics.py tests/test_backtest_engine.py tests/test_data_fetcher.py -q -W error` | ✅ **359 passed** |
| Lint (ruff) | `python -m ruff check src tests scripts` | ✅ **Clean** |
| Format (ruff) | `python -m ruff format --check src tests scripts` | ✅ **Clean (182 files)** |
| Lineage script execution | `python scripts/generate_experiment_lineage_report.py` | ✅ **Success** — 173 experiments processed, report generated |

---

## Key Findings

### Experiment Corpus Overview
- **173 total experiments** tracked in `.experiments/experiments.jsonl`
- Spanning **42 unique git commits** from 2026-10-10 to 2026-11-10
- **10 experiment categories** with pass/fail/error breakdown

### Category Summary
| Category | Count | Passed | Failed | Errors |
|----------|-------|--------|--------|--------|
| Baseline / MA Crossover | 9 | 6 | 0 | 3 |
| Time-Series Momentum | 60 | 41 | 0 | 16 |
| Cross-Sectional Momentum | 2 | 2 | 0 | 0 |
| Regime-Gated | 5 | 5 | 0 | 0 |
| Volatility / VRP | 9 | 5 | 2 | 2 |
| Volume Predictive | 6 | 3 | 0 | 3 |
| Hypothesis H10-H29 | 23 | 16 | 0 | 7 |
| New Family (NF) - Recent | 51 | 27 | 14 | 10 |
| New Family (NF) - Factor/Other | 5 | 4 | 0 | 1 |
| Other / Uncategorized | 3 | 2 | 0 | 1 |

### Git Commit Timeline
42 unique commits mapped to experiment batches, showing the evolution from baseline MA crossover (Oct 10) through TSMOM variants, H10-H29 audits, VRP, volume predictive, and the NF discovery cycles (Nov 4-10).

---

## What Remains Unresolved

### Primary Path (requires authorization)
**Artifact restoration apply** — 321 hash-exact recoverable files ready to copy via `scripts/plan_artifact_restoration.py --apply`. Blocked on explicit human authorization.

### Strategy Family Discovery
**Queue exhausted at H181.** H182 unassigned. Cycle 96 blockers remain:
- **Data-blocked (5):** Commodity carry (roll/contango), Insider Form 4/13F, Earnings revisions, Options GEX, Breakeven inflation
- **Statistical power (3):** Russell 2000 reconstitution (~16 events), S&P 500 inclusion/deletion, Stock splits
- **Mechanism adjacency (4):** 10Y-3M curve (H171/H11r), SPY jump asymmetry (H122/H128/H135), CS reversal (H119), RSP-SPY/USMV-SPY relmom (H97+)
- **Calendar adjacency (held, 2):** Halloween, Holiday/pre-holiday drift

No candidate clears the directive bar for a REAL execution without authorization.

### Remaining Audit Work (Fallback Path)
Per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6:
1. ~~Document experiment lineage — automated report from `.experiments/experiments.jsonl`~~ ✅ **COMPLETED**
2. **Stress-test frozen-contract gates** against edge cases (NaN prices, extreme leverage, zero-volume, look-ahead boundaries)
3. **CI/CD hardening** — performance regression gate (e.g., fail if 100-symbol backtest > 5s)
4. **Reproducibility audit** — verify all artifacts re-derivable from tracked metadata

---

## Constraints (Unchanged)
- `src/qtr` unchanged unless evidenced defect (then full gates: `pytest -q -W error`, ruff, 100% coverage)
- No gate weakening; no frozen number modification without authorization; no commit/push unless requested
- Free/public data only; no paid services without explicit authorization

---

## Evidence for Next Session

| File | Purpose |
|------|---------|
| `HANDOFF_FINAL.md` | Full baseline re-verification (Cycle 102) |
| `NEW_FAMILY_RESEARCH_REGISTER.md` | Cycle 96 mechanism search with blockers |
| `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` | §6 governing rule for queue exhaustion |
| `BACKTEST_PERF_PROFILE_RESULTS.md` | Previous session's profiling results |
| `EXPERIMENT_LINEAGE_REPORT.md` | **This session's lineage report** |
| `.experiments/experiments.jsonl` | Source experiment log (173 records) |
| `scripts/generate_experiment_lineage_report.py` | Re-runnable lineage generator |
| `REPRODUCIBILITY_RESTORATION_PLAN.csv` | 321 hash-exact recoverable rows |
| `scripts/plan_artifact_restoration.py` | Apply script with `--apply` flag |

---

## Failed Approaches / Do Not Repeat
- Do not run `--apply` without explicit human authorization.
- Do not recycle H1–H181 as H182 without materially distinct mechanism + free PIT data.
- Do not treat parameter/instrument/universe/timeframe variations as new families.
- Do not weaken frozen-contract gates, coverage gates, or lint gates.
- Do not modify published/certified artifacts, verdicts, or thresholds without authorization.
- Do not claim tests/lint passed without running with evidence.
- **Always re-run suite before acting on handoff "unresolved" sections** (Cycle 101 docs were stale).

---
*Session complete. Experiment lineage documented. Infrastructure auditing continues with frozen-contract stress-testing as next fallback item.*