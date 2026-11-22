# Handoff — Next Session (Cycle 251 Complete)

## Verified State (2026-11-22)

**Environment:** Fresh checkout → `pip install -r requirements.txt` (no deps by default; pre-install "179 collection errors" are missing `numpy`/`pandas`/`scipy`/`yfinance`, NOT a code regression).

**Test Suite:** 4778 tests collected.
- **4720 passed / 51 skipped / 7 failed** (the 7 = `tests/test_gates_workflow.py`, maintainer-gated).
- `ruff check src tests run_*.py scripts` → **All checks passed**.
- `ruff format --check src tests run_*.py scripts` → **374 files already formatted**.
- Coverage: `src/qtr` at **100%** (enforced in `pyproject.toml`).

**New Family Execution (Cycle 250):** H196 = stock-level **share turnover / liquidity cross-section** (Datar-Naik-Radcliffe 1998 + Baker-Wurgler 2013). REJECT 3/8. OOS Sharpe −0.774; inverse anti-turnover +0.756 (direction empirically inverted); passive equal-weight book OOS Sharpe 1.033 dominates. Artifact: `.experiments/nf_runs/nf_20261122_01_share_turnover_20261122_003934/`. Tests: 24 passed.

**Discovery Scan (Cycle 251):** Required §4 search across ≥3 mechanism categories. Two candidates evaluated:
- NF-20261122-02 realized-kurtosis cross-section → adjacent to H128/H132 higher-moment families (novelty 3, **not a new family**).
- NF-20261122-03 beta-dispersion regime timing → scalar-timing variant of H117/H129/H29 (novelty 2, **not a new family**).
No third repo-new candidate found. **No H197 fabricated; no runner created.** Full record in `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 251.

**Lineage:** H1–H196 all rejected/recorded; H189 (gross profitability) confirmed **data-blocked** on SEC XBRL (28–29/98 names, below 40-name minimum). `src/qtr` unchanged throughout.

## Unresolved (Maintainer / Authorization Only)

1. **Workflow contract fix (agent-unreachable):** `tests/test_gates_workflow.py` 7 failures. The fix is `patches/0001-gates-workflow-contract-fix.patch` (9 insertions, `gates.yml` only). **Verified:** `git apply --check` succeeds; patched workflow yields `pytest tests/test_gates_workflow.py` → 7 passed in clean `/tmp` checkout at HEAD. Agent cannot land: repo GitHub App token lacks `workflows` permission; `.github/scripts/kilo-controller.sh` restores `.github/workflows/**` from `origin/main` after every session.
   - **Maintainer action:** `git apply patches/0001-gates-workflow-contract-fix.patch && git commit -am "fix(ci): satisfy gates workflow contract" && git push origin main`

2. **Reproducibility artifact cleanup (non-blocking, authorization-gated):** `REPRODUCIBILITY_AUDIT_REPORT.md` #6 (11 `hash_mismatches`, 24h) and #5 (rebuild-excluded artifacts, 7d). Requires explicit authorization; do not modify published/certified artifacts without it. Suite is green (4720/51/7) without this.

## Approaches Already Tried — Do Not Repeat

- New equity cross-sections on 98-name S&P 100 (H187–H196): **ALL REJECT**. Passive equal-weight long book (OOS Sharpe ~1.0–1.17) dominates; every anomaly OOS Sharpe far below ≥1.0 gate; several sign-inverted (H193 beta, H194 coskewness, H196 turnover).
- In-tree `.github/workflows/gates.yml` edits: **fail every session** (controller restores; fix not agent-reachable). Capture via `patches/` + `NEXT_TASK.md` only.
- "Data-blocked" claims without probing: **FRED (Cycle 140), `data.binance.vision` (Cycle 213), SHFE/INE/CZCE/CFFEX (Cycle 214)** all serve data older registers declared unavailable. Share turnover is NOT data-blocked (failed on mechanism direction, not data). Always probe named source first.

## Next Agent Task

**There is no agent-executable research task.** Free-data family discovery is exhausted per honest §4 scan (Cycle 251 complete). The only remaining actions are the two maintainer/authorization items above. Do NOT repeat the §4 scan, do NOT fabricate H197, do NOT attempt in-tree workflow edits.

If authorization is granted for reproducibility cleanup, that work is scoped to `REPRODUCIBILITY_AUDIT_REPORT.md` #5/#6 and does not touch `src/qtr`, gates, or frozen numbers.