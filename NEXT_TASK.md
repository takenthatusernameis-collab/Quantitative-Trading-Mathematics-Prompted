# Session complete (2026-11-21, Cycle 249 — H195 price-delay bug fixed + valid execution recorded)

## What changed (this session)

The prior session (commit `c18a8c7`) committed the H195 pre-registration
(`run_nf_20261121_05_price_delay.py` + test + artifact) but left the execution
**unfinished and buggy**. Per the fallback rule I diagnosed and fixed the root
cause, produced a valid artifact, and completed all bookkeeping.

- **Root-cause bug (fixed):** `trailing_delay` discarded an *entire day* whenever
  *any* of the 98 names had a NaN in the trailing window
  (`if np.isnan(returns_window).any(): continue`). Many S&P 100 constituents IPO'd
  after 2011 (DELL, GEV, ANET, PLTR, UBER, SNDK, ...), so ~95% of the delay panel was
  NaN -> the signal produced **zero positions** and a vacuous all-zero in-sample
  Sharpe. The committed artifact had only a `grid.csv` (all `wf_train_sharpe = 0.0`)
  and no `summary.json`/`data_meta.json`, and it left
  `tests/test_experiment_artifact_schema.py` **red** (extra incomplete-run dir;
  total-dirs 121 vs 120). This was NOT a genuine null result.
- **Fix:** estimate each name on **its own valid rows** within the window (require
  `>= max(n_lags+5, window//2)` non-NaN observations; vectorized shared solve for
  complete windows + per-stock least-squares for gapped names), preserving the
  market-design warm-up guard (complete names NaN until row `window-1+n_lags`).
  Coverage is now ~90% of cells (delay_126 92.6%, delay_252 89.6%; 3995/3863 active
  days) with 97-98 active names in recent years, vs ~200 active days before.
- **Second latent bug (fixed):** `train_mechanism_separation` computed
  momentum/volatility from `returns` (actual yfinance trading days) but indexed them
  against the synthetic `pd.bdate_range` calendar (which includes market holidays),
  so the exact-label Spearman lookup raised `KeyError` on e.g. 2011-01-17 (MLK Day).
  Momentum/volatility are now reindexed onto the delay panel's calendar.
- **New regression test:** `tests/test_nf_20261121_05_price_delay.py::
  test_trailing_delay_handles_per_stock_gaps` — a gapped name must not erase the
  whole day's delay; complete names still estimated while the gapped name is below
  `min_valid`, and the gapped name fills once it accumulates enough valid rows.
- **Regenerated artifact:** `.experiments/nf_runs/nf_20261121_05_price_delay_20261121_214249/`
  (summary.json + grid.csv + data_meta.json), runtime 50.488 s. The buggy
  `…_20261121_213513` directory was deleted (it was an incomplete-run with only a
  zeroed grid.csv).
- **Schema pins updated** (`tests/test_experiment_artifact_schema.py`): `EXPECTED_TOTAL_DIRS
  120->121`, `EXPECTED_SUMMARY_COUNT 112->113`, `EXPECTED_DISTINCT_KEYS 155->156`
  (new key `train_input_collinearity_delay126_vs_delay252`); `EXPECTED_INCOMPLETE` (8),
  `EXPECTED_CACHE_ONLY_DIRS` (11), `EXPECTED_KEYS_GE_50_PCT`, `EXPECTED_KEYS_GE_80_PCT`
  unchanged (recomputed). Cycle 249 comment added.
- **Register:** `NEW_FAMILY_RESEARCH_REGISTER.md` Cycle 249 section records H195 **REAL
  REJECT (2/8)** with the §4 three-candidate discovery scan + honest scoring,
  pre-registration, mechanism separation from H93/H128/H194/momentum, data availability,
  execution outcome, the bug-fix disclosure, lineage map, and durable family-status
  consequence.
- **AGENTS.md** stale H-range note updated to **H1–H195** (Cycles 215–249), with H195
  artifact cited and a note that price-delay / market-friction cross-sections and the
  yfinance close panel are NOT data-blocked (H195 failed on mechanism *strength*, not
  data).
- **Incidental format repair:** `ruff format` on the two H195 files (missing trailing
  newlines + a slice-spacing nit) — formatting only, verified via diff.

## H195 result (from `nf_20261121_05_price_delay_20261121_214249/summary.json`)

- Mechanism: market frictions / slow information diffusion (Hou & Moskowitz 2005,
  "Market Frictions, Delay, and the Response of Stock Prices", RFS). Long top-k
  high-delay (slow response) / short bottom-k low-delay. Distinct from H93 (idiosyncratic
  vol), H128 (realized skew), H194 (coskewness), and momentum/reversal (own past return).
- Universe: 98/98 S&P 100 names (minus XOM/BKNG), min 441 valid daily returns. Offline.
- Selected `feature=delay_252, entry_z=1.0, exit_z=0.0, k=10, vol_target=0.15`
  (train WF 0.717; train Sharpe 0.779). delay_126 vs delay_252 collinearity 0.666.
- OOS Val+Test (1275 periods, 101 trades): Sharpe **0.083**, PF **1.014**, maxDD
  **-14.70%**, trades **101**, worst rolling-252 Sharpe **-1.314**, total return +0.018.
- Gates PASS (2, both **genuine**): trades>=50 (101), maxDD<=15% (-14.70%).
  Gates FAIL (6): Sharpe>=1.0 (0.083), PF>=1.3 (1.014), WF stability>=0.7 (0.107, large
  decay), worst-regime>=0.3 (-1.314), benchmark p<=0.05 & IR>=0 (p 0.0697, IR -0.808),
  perturbation min ratio>=0.5 (-1.66).
- **Honest caveats:** unlike H193/H194 the direction is **NOT inverted** (inverse
  anti-delay OOS Sharpe **-0.094**, also unprofitable) — the mechanism is simply weak
  and non-persistent on this universe (Hou-Moskowitz delay is a small/less-liquid-stock
  phenomenon; frictions are minimal in the most liquid mega-caps; train 0.78 -> OOS
  0.08). Passive equal-weight benchmark (OOS Sharpe 1.128) dominates. Mechanism
  separation confirms delay is distinct: vs beta_252 -0.367, vs momentum_252 -0.086,
  vs realized_vol_252 -0.037. **Verdict: REJECT (2/8).**

## What was actually verified (this session)

- `python -m pytest tests/test_nf_20261121_05_price_delay.py` -> **23 passed** (was 21
  pass + 1 artifact-skip; +1 new regression test, +2 artifact-gated tests now active).
- `python -m pytest tests/test_experiment_artifact_schema.py` -> **117 passed** (pins
  updated; the 2 failures the prior agent introduced are fixed).
- H195 + schema together -> **140 passed**.
- Focused sibling regression set (H191 value, H192 innovation, H193 BAB, H194 coskew,
  H195 delay, artifact schema) -> **224 passed**.
- **Full suite (`python -m pytest -q`): 4693 passed / 51 skipped / 7 failed** — the 7
  failures are exactly the pre-existing maintainer-gated `tests/test_gates_workflow.py`
  (unchanged from origin/main by design); **zero new failures** from this session. (The
  prior agent's commit had 2 *additional* schema failures from the buggy artifact; this
  session fixed those.)
- `python run_nf_20261121_05_price_delay.py` -> valid artifact, verdict REJECT 2/8.
- `python -m ruff check src tests run_*.py scripts` -> All checks passed.
- `python -m ruff format --check src tests run_*.py scripts` -> **372 files already
  formatted** (2 H195 files reformatted: missing newlines + slice spacing).
- No `src/qtr` edit -> coverage unaffected at 100%. No gate weakening; no
  published/certified artifact/threshold modified.

## Remaining unresolved

- **`tests/test_gates_workflow.py` — 7 failures** because `.github/workflows/gates.yml` is
  unpatched (unchanged from prior handoffs). The test pins `scripts/**` in both
  `push`/`pull_request` path filters, `scripts` in both ruff targets, `python -m pip
  install -e . --no-deps` in both jobs, and `python scripts/backtest_perf_regression_gate.py`
  in `research_gates`.
- Fix = maintainer applies `patches/0001-gates-workflow-contract-fix.patch`
  (`.github/workflows/gates.yml`), commits, pushes. **Agent-unreachable**:
  `.github/workflows/**` is restored from `origin/main` after every session
  (`.github/scripts/kilo-controller.sh`) and the repo token lacks `workflows` permission.
- Evidence the fix works: the patch applied in a clean `/tmp` checkout makes
  `pytest tests/test_gates_workflow.py` -> 7 passed (re-verified Cycles 106, 121, 235,
  245, 247; still red here because the workflow file is intentionally unpatched).

## Approaches already failed / do not repeat

- In-tree edit of `.github/workflows/gates.yml`: does not persist (restored from
  origin/main; token lacks workflows permission). Do not retry.
- **Do not revert the `trailing_delay` per-stock fix to the all-or-nothing mask** — that
  was the bug that produced the fake all-zero artifact (95% NaN panel, zero positions).
- Do not re-run H195 (or any exhausted family) as a parameter/universe/window variant;
  the full-window pre-registered run is the record.

## One precise next task (for the next agent)

**No agent-executable new strategy family remains.** H1–H195 are exhausted/rejected
(H189 confirmed data-blocked). The two remaining work items are both outside agent scope:
1. **Maintainer workflow patch (agent-unreachable):** apply
   `patches/0001-gates-workflow-contract-fix.patch` to `.github/workflows/gates.yml` to fix
   the 7 pre-existing `tests/test_gates_workflow.py` failures. `.github/workflows/**` is
   restored from origin/main after every session and the token lacks `workflows` permission.
   Do not retry an in-tree edit.
2. **Authorization-gated artifact cleanup (non-blocking):** drop 8 superseded
   `param_grid_results` keys + 3 stale `summary` keys from `.experiments/experiments.jsonl`,
   update `REPRODUCIBILITY_BASELINE` (hash_mismatches 11 -> 3), `PINNED_HASH_MISMATCHES`, and
   `REPRODUCIBILITY_AUDIT_REPORT.md` together, then re-run `tests/test_reproducibility_audit.py`.
   Requires authorization; do not do without it.

Deferred (do not treat as new families without a fresh §4 scan): beta-dispersion /
aggregate-beta regime timing (scalar market-timing variant of H117/H29) and a
realized-kurtosis / tail-risk cross-section (adjacent to H128/H194 higher-moment families).
Do not re-declare price-delay / market-friction cross-sections, coskewness / systematic-skewness
cross-sections, beta / systematic-risk cross-sections, or the yfinance close panel as blocked.

Constraint reminder: keep `src/qtr` unchanged, preserve 100% branch coverage / Ruff /
warning-as-error / protected-holdout gates, use free/public data only, do not weaken any gate.