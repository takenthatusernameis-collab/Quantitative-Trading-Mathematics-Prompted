# HANDOFF — H26 Sharpe annualization-scale audit (2026-10-19)

## What changed

**H26 — a pre-registered audit of the published Sharpe scale (new hypothesis-instance
H26; no strategy was re-run, no gate, threshold, verdict or certified number changed).**

### New
- `run_h26_sharpe_scale_audit.py` — deterministic, offline audit over the frozen
  artifacts (H9/H10/H21/H22/H23/H25 + a daily control, H16). Reproduces each audited
  artifact's published OOS Sharpe bit-close from its own `returns.parquet`, then
  characterizes the annualization scale (as-published √252-per-bar, the repo's own
  `√(252·6.5)` vol-target convention, the empirical calendar convention, and an
  independent daily-aggregation estimate), the bootstrap CI at each scale, and the
  dependence diagnostics (autocorrelation, Newey–West long-run variance).
- `.experiments/artifacts/h26_sharpe_scale/summary.json` + `scale_table.parquet`.
- `tests/test_h26_sharpe_scale_audit.py` — 44 tests (reproduction, scale factors, CI
  rescaling, recomputed gate fractions, daily control, H9 exclusion + both diagnoses,
  dependence, library helpers, negative guards).
- `qtr.validation.statistics.bars_per_year(index)` and
  `qtr.validation.statistics.annualized_sharpe(returns, index)` (+ exports in
  `qtr/validation/__init__.py`) — the frequency-aware annualization used by the audit.

### Changed
- `HYPOTHESIS_SPEC.md` — new §H26 with the **pre-registration written before execution**,
  the **measure log** (results, F1–F5, Amendment 1, what does *not* change).
- `FINAL_REPORT.md` — results-table scale note (+ H9 PF-window footnote), new §H26 detail
  section, corrected Conclusion bullet, corrected Summary statistics (27 instances,
  586/586 tests), corrected §Next Task, and a tempered executive-summary claim
  ("genuine market inefficiency" → backtested, not established).

## What was actually verified

- `python -m pytest -q` → **586 passed** (542 before + 44 new), ~3:28, 0 warnings.
- `python -m pytest -W error -q` → clean.
- `python -m pytest --cov=qtr --cov-report=term-missing` → coverage unchanged except the
  new helpers (covered).
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → clean.
- `bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
- Audit self-consistency: the as-published H25 CI reproduced by the audit
  ([0.8833604790, 1.7506423152], P = 0.9275) is **bit-identical** to the committed
  `pf_robustness` artifact, i.e. the audit re-derives the quoted caveat and then
  re-characterizes it. The audit's OOS Sharpe reproduction is exact (|Δ| = 0.0) for
  H10/H21/H22/H23/H25.

## The finding (headline)

Every published "OOS Sharpe" is `sharpe_ratio(returns)` with the default
`periods_per_year=252` = **per-bar** mean/vol × `√252`. For the daily families the bar
is a trading day, so `√252` *is* the calendar annualization; for the **intraday (1h)**
families the bar is one hour, so the published number is **not** an annualized Sharpe and
**understates** it by 2.55× (repo vol convention) to 4.76× (empirical calendar):

| Family | Published | ×2.5495 | ×4.7566 | daily-agg (independent) |
|---|---|---|---|---|
| H10 (PASS) | 1.2758 | 3.2526 | 6.0682 | 5.0366 |
| H22 (PASS) | 1.3725 | 3.4991 | 6.5283 | 5.1973 |
| H25 (PASS) | 1.3236 | 3.3746 | 6.2959 | 5.0916 |
| H21 (REJECT) | 0.8394 | 2.1400 | 3.9925 | 3.5293 |
| H23 (REJECT) | −7.1871 | −18.3236 | −42.5481 | −12.5024 |
| H16 daily control | — | — | ratio **0.9995** → already annualized | — |

Consequences: (1) the results table mixed two scales — intraday rows are now flagged and
the correction *understates* nothing, it *over*-credits the intraday family; (2) the
**"Sharpe CI-fragile" caveat was a scale artifact** (H25 CI [0.8834, 1.7506] → [2.2521,
4.4633], P(Sharpe≥1.0) 0.9275 → 1.0000), while the **PF margin fragility stands**
(scale-invariant); (3) no verdict changed.

Two further defects were found by the reproduction anchor (H9 excluded, causes
diagnosed): H9 was published with the *sample*-std (ddof=1) Sharpe estimator while
H10+ use *population*-std (ddof=0) (relative ≈1e-4, H9 no longer bit-reproducible with
the current library), and **H9's published "OOS profit factor" is the full-sample
(train+val+test) PF** — the correct OOS-window PF is 1.2529, still below the 1.3 gate,
so H9 stays REJECTED (the defect was conservative).

## What remains unresolved

- **The level of the certified P&L is unaudited.** The scale correction implies an
  annualized Sharpe of 3.25–6.53 for the certified family, far above the ≈0.5–1.5 of
  published real-world futures TSMOM results. Either the sample is extraordinary or the
  backtest has a level/scale bug that would invalidate the certified family. H26
  deliberately did **not** attempt this; it is the next task.
- `src/qtr/validation/statistics.py:114` remains the single uncovered branch
  (unreachable `walk_forward_splits` empty-window guard, pre-existing).
- H9's artifact is still not bit-reproducible with the current library (ddof drift);
  the H26 tests pin both conventions, but the artifact itself was not rewritten
  (rewriting a certified artifact was out of scope).
- The paid-data task (widen the OOS window so the **PF** bootstrap CI clears its gate
  with margin) is still outstanding and out of scope for a free-data session.

## Which approaches have already failed and why

- No failed approaches this session. The one deviation from the pre-registration is
  documented in the spec as **Amendment 1**: two diagnostic checks (Sharpe
  standard-deviation convention, profit-factor *window*) were added after the first
  execution to explain the H9 exclusion, and are now applied to every audited artifact.
  The pre-registered exclusion rule itself was not changed — H9 stays excluded.

## One precise next task

**Audit the level of the certified intraday P&L** (free data, bounded, verifiable):
recompute the per-bar dollar P&L from `prices.parquet` + `positions.parquet` +
`trades.parquet` of the H10 and H25 artifacts using the engine's contract maths
(contracts = weight × 1e6 / (price × multiplier); P&L = contracts × Δprice × multiplier),
recompute the cost drag from the same position changes, and check the vol-target
coherence (15% target at `√(252·6.5)` vs ≈10.5% calendar-annualized realized vol at
≈32% calendar-annualized return). Pre-register the verdict rule (`LEVEL_CONFIRMED` iff
the recomputed P&L matches the logged returns to ≤1e-9 and the implied annualized
Sharpe is reproduced from position/price/contract inputs alone; `LEVEL_DEFECT`
otherwise) before executing, then pin the outcome in a new test file and write it to
`HYPOTHESIS_SPEC.md`. Full scope and constraints: `NEXT_TASK.md`.
