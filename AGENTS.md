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
- **Stale H-range claim (re-verified 2026-11-21, Cycle 248):** the lines below read "H1–H30 is exhausted" and "hypotheses through H84 are documented". Both are stale by ~160 hypotheses: the executed record is **H1–H194 exhausted/rejected** (H184 commodity term-structure carry REJECT 2/8, Cycle 215; H185 commodity open-interest positioning REJECT 1/8, Cycle 216; H186 commodity commercial hedging pressure REJECT 2/8, Cycle 219; H187 equity accounting accruals + asset growth REJECT 2/8, Cycle 231, artifact `nf_20261120_01_equity_accruals_20261120_062010`; H188 net share issuance / external financing REJECT 3/8, Cycle 233, artifact `nf_20261120_02_net_share_issuance_20261120_075812`; **H190 crypto perpetual funding/basis cross-section REJECT 1/8, Cycle 235**, artifact `nf_20261120_04_crypto_funding_carry_20261120_101548`; H191 equity value / book-to-price & cash-flow-yield cross-section REJECT 4/8, Cycle 245, artifact `nf_20261121_01_equity_value_20261121_144056`; H192 innovation intensity / R&D cross-section REJECT 3/8, Cycle 246, artifact `nf_20261121_02_innovation_intensity_20261121_174135`; **H193 beta-sorted cross-section / betting-against-beta REJECT 3/8, Cycle 247**, artifact `nf_20261121_03_bab_beta_20261121_184109` — BAB direction empirically inverted in this universe (inverse anti-beta OOS Sharpe +0.959, still < 1.0 gate); the WF-stability/perturbation "passes" are negative/negative-ratio artifacts, not robustness; **H194 stock-level coskewness / systematic skewness REJECT 2/8, Cycle 248**, artifact `nf_20261121_04_coskewness_20261121_194429` — coskewness direction empirically inverted in this universe (inverse anti-coskew OOS Sharpe +0.459, still < 1.0 gate); WF-stability negative (train +, OOS -), perturbation pass is negative-ratio artifact), per `NEW_FAMILY_RESEARCH_REGISTER.md` Cycles 215–248. **H189 (NF-20261120-03, gross profitability) confirmed data-blocked**: revenue AND cost reported on the same 10-K end (required for gross margin) cover only 28/100 names via `CostOfRevenue` and 29/100 via `CostOfGoodsSold`, below the 40-name minimum — no executable H189 test exists on this source (verified offline against the cached 100-name companyfacts bundles, 2026-11-20). The SEC XBRL `companyfacts` API remains free, public and point-in-time (88/91 usable share observations, 50.75-day median filing lag; 9 measured share-count exclusions) — H187 and H188 failed as *mechanisms after costs*, not for lack of data. Do not re-conclude "queue exhausted" and do not re-declare PIT accounting fundamentals as blocked. Beta / systematic-risk cross-sections, coskewness / higher-moment cross-sections, and the yfinance close panel are likewise NOT data-blocked (H193 failed on mechanism direction, not data; H194 failed on mechanism direction, not data).
- **Free-data availability corrections are durable.** "Data-blocked" classifications must name the source that was probed. FRED (Cycle 140), `data.binance.vision` public archives (Cycle 213), and the Chinese futures exchanges SHFE/INE/CZCE/CFFEX (Cycle 214, official daily per-contract settlement cross-sections) all serve data older registers declared unavailable; do not re-declare crypto funding rates, breakeven inflation, or commodity per-contract roll/contango as blocked. Probe tool: `scripts/probe_commodity_termstructure_availability.py` (4/4 sources usable 2026-11-18; coverage SHFE 2010→, CZCE 2015-12→, INE 2018-03→, CFFEX 2010-04→). Still-blocked sources are listed in the module docstring (Nasdaq/Quandl CHRIS 403+key-gated, CME 403 IP block, Yahoo single-contract 429, stooq JS challenge, LME 403, DCE 412).
- Do not treat parameter, timeframe, indicator, market, or universe variations as new strategy families. Build a mechanism-level lineage map and search for genuinely distinct return-generating mechanisms.
- Preserve all existing statistical gates, protected-holdout rules, free-data preference, and 100% source coverage requirement.
- **Workflow files are maintainer-managed and agent-unreachable.** `.github/workflows/**` is restored from `origin/main` after every session and excluded from staging (`.github/scripts/kilo-controller.sh`), and the repository GitHub App token has no `workflows` permission, so a committed workflow edit cannot reach `main`. Do not try to fix CI workflow content in a commit; capture it as an apply-ready patch under `patches/` and record the maintainer action in `NEXT_TASK.md`. Do not weaken the contract test that pins the workflow.
- **`tests/test_gates_workflow.py` is red on `origin/main` by design of this block.** As of 2026-11-13 it is the only failing test file; the fix is `patches/0001-gates-workflow-contract-fix.patch`.
