# Handoff — Next Session (Cycle 274 Complete)

## Verified State (2026-11-23)

**Environment:** Fresh checkout → `pip install -r requirements.txt` (no deps by default; pre-install "collection errors" are missing `numpy`/`pandas`/`scipy`/`yfinance`, NOT a code regression).

**Test Suite:** 5254 tests collected (approx).
- **4916 passed / 51 skipped / 7 failed** (the 7 = `tests/test_gates_workflow.py`, maintainer-gated).
- `python -m pytest -q -W error tests/test_experiment_artifact_schema.py` → **122 passed**
- `python -m pytest -q -W error tests/test_verify_hypothesis_inventory.py` → **13 passed**
- `python -m pytest -q -W error tests/test_probe_script_coverage.py` → **2 passed**
- `python -m pytest -q -W error tests/test_probe_broad_universe_shares_availability.py` → **20 passed**
- `python -m pytest -q -W error tests/test_verify_gates_workflow_patch.py` → **15 passed**
- `ruff check src tests run_*.py scripts` → **All checks passed**
- `ruff format --check src tests run_*.py scripts` → **395 files already formatted**
- Coverage: `src/qtr` at **100%** (enforced in `pyproject.toml`)

**Hypothesis Inventory:** H1–H199 all exhausted/rejected (H189 data-blocked); IN SYNC (`python scripts/verify_hypothesis_inventory.py` → H199 == H199).

**Latest Execution (Cycle 273):** H199 = market-cap size premium on broad S&P 500/400/600 universe (1502 names, 1346 tradeable). REJECT 3/8. OOS Sharpe −0.366 (train 0.000); passive equal-weight book OOS Sharpe +0.462 dominates. Artifact: `.experiments/nf_runs/nf_20261122_04_size_premium_20261123_004459/`.

**Lineage:** The equity cross-section mechanism space on the broad universe has tested its only genuinely-distinct, repo-new mechanism (size premium). All 12 prior cross-sections on 98-name S&P 100 (H187–H198) were REJECT. No further genuinely-distinct, free-data-feasible equity cross-section mechanism remains untested on this universe.

## Unresolved (Maintainer / Authorization Only)

1. **Workflow contract fix (agent-unreachable):** `tests/test_gates_workflow.py` 7 failures. The fix is `patches/0001-gates-workflow-contract-fix.patch` (7 violations resolved, `gates.yml` only). **Verified:** `git apply --check` succeeds; `python scripts/verify_gates_workflow_patch.py` confirms patch resolves all 7 violations. Agent cannot land: repo GitHub App token lacks `workflows` permission; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` after every session.
   - **Maintainer action:** `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`

2. **Universe/benchmark decision (the real research bottleneck):** Complete through H199 on broad S&P 500/400/600 universe (1502 names); passive equal-weight long book (+0.462 OOS Sharpe, H199) dominates every tested mechanism. Per directive §6, the universe/benchmark — not the mechanism search — is the binding constraint. Authorize a different universe (ex-US, micro-cap, other asset classes) OR formally close the equity cross-section program.

3. **Reproducibility artifact cleanup (non-blocking, authorization-gated):** `REPRODUCIBILITY_AUDIT_REPORT.md` #6 (11 `hash_mismatches`, 24h) and #5 (rebuild-excluded artifacts, 7d). Requires explicit authorization; do not modify published/certified artifacts without it. Suite is green (4916/51/7) without this.

## Approaches Already Tried — Do Not Repeat

- New equity cross-sections on 98-name S&P 100 (H187–H198): **ALL REJECT**. Passive equal-weight long book (OOS Sharpe ~0.9–1.2) dominates; every anomaly OOS Sharpe far below ≥1.0 gate; several sign-inverted (H193 beta, H194 coskewness, H196 turnover).
- Equity cross-sections on broad S&P 500/400/600 universe (H199): **REJECT 3/8**. Size premium mechanism too weak (train 0.000 → OOS −0.366); passive book +0.462 dominates.
- In-tree `.github/workflows/gates.yml` edits: **fail every session** (controller restores; fix not agent-reachable). Capture via `patches/` + `NEXT_TASK.md` only.
- "Data-blocked" claims without probing: **FRED (Cycle 140), `data.binance.vision` (Cycle 213), SHFE/INE/CZCE/CFFEX (Cycle 214), SEC frames API (Cycle 272)** all serve data older registers declared unavailable. Always probe named source first.
- Discovery scans / baseline-verification loops: **failed Cycles 96/116/251/257-269**. Repeating an unchanged scan is not a materially different approach.

## Next Agent Task

**There is no agent-executable research task.** The equity cross-section mechanism space on the broad S&P 500/400/600 universe is exhausted (H199 tested, REJECT 3/8; passive book dominates). The only remaining actions are the three maintainer/authorization items above. Do NOT repeat the §4 discovery scan, do NOT fabricate H200, do NOT attempt in-tree workflow edits.

If authorization is granted for a new universe, the next task would be: pre-register a genuinely-distinct mechanism (per directive §2 lineage test) on the authorized universe in `HYPOTHESIS_SPEC.md` (bumping the `AGENTS.md` marker + spec together), implement a runner reusing the existing engine + 8 gates, and execute.

If authorization is granted for reproducibility cleanup, that work is scoped to `REPRODUCIBILITY_AUDIT_REPORT.md` #5/#6 and does not touch `src/qtr`, gates, or frozen numbers.