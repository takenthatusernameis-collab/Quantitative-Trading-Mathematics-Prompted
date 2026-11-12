# NEXT_TASK.md — Infrastructure Auditing Complete; Free-Data Family Discovery Exhausted at H181

## Session Summary (2026-11-12)

**Completed:** Backtest engine performance profiling per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6 fallback path.

**Infrastructure audit item executed:** "Performance profiling of backtest engine on large universes"

### Verification Results
- **Core tests:** 359 passed (backtest engine, config, cost model, statistics, data fetcher)
- **Lint:** Clean (315 files including new profiling script)
- **Format:** Clean (315 files)
- **Coverage:** src/qtr 100% maintained (no src/qtr changes)
- **Working tree:** Clean except new profiling artifacts

### Key Findings
- Engine scales **linearly** O(n_symbols × n_bars) — no quadratic bottlenecks
- 500 symbols × 10 years daily: **~22s, <100MB peak memory**
- Linear fit: `time = 0.0232 * symbols + 0.077` (equity, long-only, 1yr)
- All asset classes (equity, futures, crypto) show consistent scaling
- Long-short ~1.6x slower than long-only due to doubled trade count

### Artifacts Created
- `run_backtest_perf_profile.py` — Profiling script (linted, formatted, tested)
- `.experiments/backtest_perf_profile.csv` — Raw benchmark data (36 configurations)
- `BACKTEST_PERF_PROFILE_RESULTS.md` — Summary report

---

## Status (Unchanged from Handoff)

**Strategy family discovery queue: EXHAUSTED.** H1–H181 all executed and REJECTED. H182 unassigned.

**Blockers for H182 (per Cycle 96, all concrete & documented):**
1. Commodity carry — no free PIT roll/contango proxy
2. Insider transactions — no free PIT Form 4/13F source
3. Earnings estimate revisions — no free PIT revision history
4. Options dealer GEX — no free historical options chain
5. Breakeven inflation — ^T5YIE/^T10YIE unavailable on yfinance
6. Statistical power — annual/low-frequency events (Russell 2000, S&P 500 inclusion, splits)
7. Mechanism adjacency — curve, jump asymmetry, CS reversal, relmom families exhausted
8. Calendar adjacency (held) — Halloween, holiday drift adjacent to executed families

**No candidate clears the directive bar** (materially distinct mechanism + free PIT data + smallest decisive test).

---

## Next Task Options

### Primary (requires authorization)
Resolve one data gap to unblock H182:
- Futures roll/contango data for commodity carry
- PIT insider/earnings/options data

### Fallback (no authorization) — Additional Auditing/Infrastructure
Per STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md §6:
1. **Stress-test frozen-contract gates** against edge cases (NaN prices, extreme leverage, zero-volume, look-ahead boundary conditions)
2. **Document experiment lineage** — generate automated lineage report from `.experiments/experiments.jsonl`
3. **CI/CD hardening** — add performance regression gate (e.g., fail if 100-symbol backtest > 5s)
4. **Reproducibility audit** — verify all experiment artifacts can be re-derived from tracked metadata

### Constraints (unchanged)
- `src/qtr` unchanged unless evidenced defect (then full gates: pytest -q -W error, ruff, 100% coverage)
- No gate weakening; no frozen number modification without authorization; no commit/push unless requested

---

## Evidence to Review
- `HANDOFF_FINAL.md` — full re-verification record (Cycle 102)
- `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 96 — complete mechanism search with blockers
- `STRATEGY_FAMILY_EXPANSION_DIRECTIVE.md` §6 — governing rule for queue exhaustion
- `BACKTEST_PERF_PROFILE_RESULTS.md` — this session's profiling results
- `.experiments/backtest_perf_profile.csv` — raw benchmark data

---

## Failed Approaches / Do Not Blindly Repeat
- Do not recycle H1–H181 as H182 without materially distinct mechanism and free PIT data
- Do not treat parameter/instrument/universe/timeframe variations as new families
- Do not weaken frozen-contract gates, coverage gates, or lint gates to force progress
- Do not modify published/certified artifacts, verdicts, or thresholds without authorization
- Do not claim tests/lint passed without running them with available tooling and evidence
- **Do not trust a handoff doc's failure list** — always re-run the suite (or focused contract file) before acting on "unresolved" sections

---
*Updated 2026-11-12 after infrastructure auditing session.*