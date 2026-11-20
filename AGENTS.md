# AGENTS.md

## Quick start
```bash
pip install -r requirements.txt
```

## Testing
```bash
python -m pytest -q
python -m pytest -q -W error  # as used in handoffs
```

## Lint and format
```bash
python -m ruff check src tests run_*.py scripts
python -m ruff format --check src tests run_*.py scripts
```

## Coverage
```bash
python -m pytest -q --cov=qtr --cov-branch --cov-report=term-missing
```
Coverage is enforced at 100% for `src/qtr` (see `pyproject.toml`).

## Notes
- Source lives in `src/qtr/`; tests in `tests/`.
- Many experiment artifacts and reports are committed. Published numbers and gates are treated as frozen per handoff conventions.
- **Stale H-range claim (re-verified 2026-11-20, Cycle 231):** the lines below read "H1–H30 is exhausted" and "hypotheses through H84 are documented". Both are stale by ~155 hypotheses: the executed record is **H1–H187 exhausted/rejected** (H184 commodity term-structure carry REJECT 2/8, Cycle 215; H185 commodity open-interest positioning REJECT 1/8, Cycle 216; H186 commodity commercial hedging pressure REJECT 2/8, Cycle 219; **H187 equity accounting accruals + asset growth REJECT 2/8, Cycle 231**, artifact `nf_20261120_01_equity_accruals_20261120_062010`), per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 215–232. **H188 (NF-20261120-02, net share issuance / external financing) is pre-registered in `HYPOTHESIS_SPEC.md` §Cycle 232 and is NOT yet executed** (usable universe 91/100 names; mechanism separation from H187 written). NF-20261120-03 (gross profitability) remains deferred for measured data thinness — `CostOfRevenue` annual facts cover only 31/99 names, below the 40-name minimum. The SEC XBRL `companyfacts` API remains free, public and point-in-time (98/100 usable accrual observations, 50.75-day median filing lag; XOM and BKNG are measured exclusions) — H187 failed as a *mechanism after costs*, not for lack of data. Do not re-conclude "queue exhausted" and do not re-declare PIT accounting fundamentals as blocked.
- **Free-data availability corrections are durable.** "Data-blocked" classifications must name the source that was probed. FRED (Cycle 140), `data.binance.vision` public archives (Cycle 213), and the Chinese futures exchanges SHFE/INE/CZCE/CFFEX (Cycle 214, official daily per-contract settlement cross-sections) all serve data older registers declared unavailable; do not re-declare crypto funding rates, breakeven inflation, or commodity per-contract roll/contango as blocked. Probe tool: `scripts/probe_commodity_termstructure_availability.py` (4/4 sources usable 2026-11-18; coverage SHFE 2010→, CZCE 2015-12→, INE 2018-03→, CFFEX 2010-04→). Still-blocked sources are listed in the module docstring (Nasdaq/Quandl CHRIS 403+key-gated, CME 403 IP block, Yahoo single-contract 429, stooq JS challenge, LME 403, DCE 412).
- Do not treat parameter, timeframe, indicator, market, or universe variations as new strategy families. Build a mechanism-level lineage map and search for genuinely distinct return-generating mechanisms.
- Preserve all existing statistical gates, protected-holdout rules, free-data preference, and 100% source coverage requirement.
- **Workflow files are maintainer-managed and agent-unreachable.** `.github/workflows/**` is restored from `origin/main` after every session and excluded from staging (`.github/scripts/kilo-controller.sh`), and the repository GitHub App token has no `workflows` permission, so a committed workflow edit cannot reach `main`. Do not try to fix CI workflow content in a commit; capture it as an apply-ready patch under `patches/` and record the maintainer action in `NEXT_TASK.md`. Do not weaken the contract test that pins the workflow.
- **`tests/test_gates_workflow.py` is red on `origin/main` by design of this block.** As of 2026-11-13 it is the only failing test file; the fix is `patches/0001-gates-workflow-contract-fix.patch`.
