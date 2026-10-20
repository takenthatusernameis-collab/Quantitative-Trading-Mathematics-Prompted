# HANDOFF — H33: three vacuous benchmark gates repaired, contract pinned (2026-10-20)

## What changed

**H33 — the audit of all 17 `compare_to_benchmark` call sites found three defects that made a
published benchmark gate evaluate a constant instead of a statistic. They are repaired, pinned by
an executable contract, and disclosed. No published artifact, runner gate, threshold, verdict or
certified number was modified; no grid was re-run.**

### New
- `tests/test_benchmark_gate_contract.py` — 12 tests. The **static contract** over every
  `compare_to_benchmark` call site in every `run_*.py`: at most two positional arguments (the two
  return series — the third is `risk_free`) and every key read off the result is a key the
  library actually returns. Plus behavioural tests for the library (pinned key set, the
  `TypeError` on a non-scalar `risk_free`, the pair-wise NaN drop, the degenerate inputs failing
  closed, the empty-side case) and for H7's benchmark being a return series.

### Changed
- `src/qtr/validation/statistics.py:compare_to_benchmark` —
  (i) `risk_free` is validated (`TypeError` if not scalar; H18's boolean mask used to turn
  `alpha_annualized` into an array);
  (ii) the tail-aligned rows where **either** side is NaN are dropped pair-wise, because
  `np.cov`/`np.var` do not skip NaN (before: one NaN left alpha/beta/p NaN while IR/win_rate
  stayed finite — an internally inconsistent dict that silently voided any gate reading it); for
  a NaN-free input every statistic is **bit-identical**;
  (iii) fewer than two paired observations return an explicit "no evidence" result
  (`_no_comparison()`: IR 0, alpha 0, beta 0, t 0, **p = 1.0**, win rate 0) instead of NaN fields
  plus a `Degrees of freedom <= 0` RuntimeWarning; the empty-side case is handled too
  (`x[-0:]` is the whole array).
- `run_futures_tsmom_experiment.py:522` (H4) — `alpha_res.get("p_value", 1.0)` →
  `alpha_res.get("alpha_p_value", 1.0)`. The `p` gate was always False.
- `run_h18_overnight_intraday_experiment.py:742` (H18) — the third positional argument
  (`oos_mask`, i.e. `risk_free`) is dropped; `.get("p_value", 1.0)` → `.get("alpha_p_value", 1.0)`.
  The `benchmark_p` gate was always False.
- `run_h7_intraday_tsmom_experiment.py` (H7) — a new module-level
  `benchmark_comparison(strategy_returns, prices)` builds the equal-weighted **return**
  benchmark (`prices.pct_change().mean(axis=1)`, verified equal to the repo's committed
  `benchmark_returns.parquet` with max abs diff **0.0**) and reads `alpha_annualized` /
  `alpha_p_value`; `main()` calls it. The old call compared returns against **price levels**:
  IR −38.34, "annualized" excess return −767 093, alpha p-value 0.0 — i.e. had the key names
  been right, H7 would have published an *apparently significant* alpha computed from a unit
  mismatch. The NaN default was the only thing that protected the record.
- `HYPOTHESIS_SPEC.md` §H33 (pre-registration frozen before the change + the measure log),
  `FINAL_REPORT.md` (§H33, the table footnote, the summary statistics, the Next Task section),
  `NEXT_TASK.md`, `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md`, `HANDOFF.md`.

## What was actually verified

- `python -m pytest -q` → **725 passed** (713 + 12 new), 0 warnings.
- `python -m pytest -W error -q` → **725 passed**.
- `python -m pytest --cov=qtr --cov-report=term-missing -q` → 725 passed; `src/qtr` coverage
  **94%**, the same 16 uncovered statements as the HEAD baseline (the dead
  `deflated_sharpe_ratio` body) — no regression, and H33's new code is fully covered.
- `python -m ruff check src tests run_*.py` → All checks passed.
- `python -m ruff format --check src tests run_*.py` → 78 files already formatted.
- `bash -n .github/scripts/*.sh` OK; `bash .github/scripts/test_kilo_progress.sh` OK.
- **Negative control**: the same suite run against the pre-fix source (`git stash -u`) fails **8
  tests** and names the three defect sites —
  `run_futures_tsmom_experiment.py:518 reads ['p_value']`,
  `run_h18_overnight_intraday_experiment.py:742 reads ['p_value']`,
  `run_h7_intraday_tsmom_experiment.py:403 reads ['alpha', 'p_value']`.
- **Impact, recomputed offline from the committed artifacts** (nothing published was touched):

  | Family | Published | Repaired | Gate effect | Verdict |
  |---|---|---|---|---|
  | H4 | p = 1.0 (the literal default), IR 0.33150832181222434 | p = 0.4592003515637103, IR **bit-identical** | `p` still False → 1/8 → 1/8 | REJECT |
  | H7 | `benchmark: null`; IR −38.34 on price levels | alpha 0.09987, IR **+0.30022**, p 0.34319 | `min_information_ratio` False → True → recomputed 5/9 (artifact 4/9, report row 3/8) | REJECT |
  | H18 | `benchmark_p.value` = 1.0 (the literal default), IR −0.5967666565674836 | p = 0.04098500443612743, IR **bit-identical** | `benchmark_p` False → True → recomputed 3/9 (published 2/9) | REJECT |

  The H4 recomputation reuses the H29 `rebuild_h4` ensemble and reproduces the published OOS
  Sharpe **0.3757006004618035** to the digit; the H18 recomputation uses the cached
  SPY/QQQ/IWM/^VIX daily bars (no network).

## What remains unresolved

- **The benchmark-significance gate is direction-blind.** The pre-registered gate is
  `p < max_p_value` on a **two-sided** t-test of the excess returns, so it is satisfied by a
  *significantly negative* alpha — by the strategy being significantly **worse** than the
  benchmark. Three published families already carry such a PASS: **H19** (p = 0.00260, IR
  −0.8798), **H20** (p = 0.01595, IR −0.7040), **H23** (p = 0.00090, IR −3.0739); H18's repaired
  gate passes for the same reason (p = 0.041, IR −0.5968). The families that pass with a
  *positive* IR (H9 +1.03, H10 +0.92, H22 +1.35, H25 +1.35) are genuine. The gate **definition**
  is pre-registered, so H33 does not change it — it is disclosed and named as the next task.
- **The dead `deflated_sharpe_ratio`** in `src/qtr/validation/statistics.py` (lines 394–435) is
  unreachable: not exported by `qtr/validation/__init__.py`, no runner or test calls it, and it
  duplicates `run_h12_selection_bias_audit.py:deflated_sharpe_ratio` with the *same* `max_z`
  formula (correct, merely unreachable). It is the whole of the uncovered block.
- **The H32 handoff's coverage claim is wrong** ("99%, one uncovered branch"): the measured HEAD
  baseline is **94%**, and its named "uncovered branch" (the `walk_forward_splits` empty-window
  guard at `statistics.py:159-160`) is covered by `tests/test_statistics.py:185`.

## Approaches that failed / were not taken

- Fixing the runners by adding alias keys to the library's return dict was rejected: it would
  leave the callers wrong and mask the next typo. The library's key names are the contract and
  the static test enforces it.
- Changing the direction of the benchmark gate was **not** attempted: the gate definition is
  pre-registered and changing it would change published gates. It is disclosed instead.
- Re-running the H4/H7/H18 grids was **not** done (forbidden by the repo's rules and
  unnecessary): the benchmark statistics were recomputed from the committed artifacts offline,
  which reproduces the published OOS Sharpe and IR bit-exactly.

## One precise next task

**Pre-register H34: re-specify the benchmark-significance gate as one-sided (or add an explicit
`alpha_annualized > 0` conjunct) and reconcile the three published families that currently pass it
for the wrong reason (H19, H20, H23).** Constraints: pre-register before any run; do not rewrite
the published rows; recompute the benchmark statistics offline from the committed artifacts for
every family with a `p`-gate (H4, H6, H7, H9, H10, H16, H17, H18, H19, H20, H22, H23, H25) and
report which published `p` passes are direction-positive; state explicitly whether the certified
families (H10, H22, H25) survive (expected: yes — they pass with a positive IR); and settle the
dead `deflated_sharpe_ratio` as a separate small item. Evidence and the full task statement are
in `NEXT_TASK.md` and `FINAL_REPORT.md` §Next Task.
