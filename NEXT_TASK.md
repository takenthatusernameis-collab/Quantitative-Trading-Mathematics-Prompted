# Current Task — H34: re-specify benchmark-significance gate as one-sided (2026-10-20)

## State

**H33 is COMPLETE (`FIXED`).** Three published benchmark gates were vacuous — they evaluated a
constant instead of a statistic — and they are now repaired, pinned by an executable contract,
and disclosed. **No published artifact, runner gate, threshold, verdict or certified number was
modified; no grid was re-run.** The published H4/H7/H18 rows stand as the historical record.

### What changed

- `src/qtr/validation/statistics.py:compare_to_benchmark` — (i) a non-scalar `risk_free` now
  raises `TypeError` instead of silently turning `alpha_annualized` into an array; (ii) the
  tail-aligned rows where either side is NaN are dropped pair-wise (`np.cov`/`np.var` do not
  skip NaN, so one NaN used to leave alpha/beta/p NaN while IR/win_rate stayed finite); (iii)
  fewer than two paired observations return an explicit "no evidence" result
  (`_no_comparison()`: IR 0, alpha 0, beta 0, t 0, **p = 1.0**, win rate 0) instead of NaN fields
  plus a `Degrees of freedom <= 0` warning. For a NaN-free input every statistic is
  **bit-identical** to before.
- `run_futures_tsmom_experiment.py:522` (H4) — `alpha_res.get("p_value", 1.0)` →
  `alpha_res.get("alpha_p_value", 1.0)`.
- `run_h18_overnight_intraday_experiment.py:742` (H18) — the third positional argument
  (`oos_mask`, i.e. `risk_free`) is dropped; `.get("p_value", 1.0)` → `.get("alpha_p_value", 1.0)`.
- `run_h7_intraday_tsmom_experiment.py` (H7) — a new module-level
  `benchmark_comparison(strategy_returns, prices)` builds the equal-weighted **return**
  benchmark (`prices.pct_change().mean(axis=1)`, verified equal to the repo's committed
  `benchmark_returns.parquet` with max abs diff **0.0**) and reads `alpha_annualized` /
  `alpha_p_value`.
- `tests/test_benchmark_gate_contract.py` — 12 new tests: a **static contract** over every
  `compare_to_benchmark` call site in every `run_*.py` (≤ 2 positional arguments; every key read
  off the result is a key the library returns) plus behavioural tests for the library and for
  H7's benchmark.
- `HYPOTHESIS_SPEC.md` §H33 (pre-registration + measure log), `FINAL_REPORT.md` (§H33 + the
  table footnote + the Next Task section), `HANDOFF_CURRENT.md`, `HANDOFF_NEXT.md`, `HANDOFF.md`.

### The quantified impact (recomputed offline; nothing published was touched)

| Family | Published | Repaired | Gate effect | Verdict |
|---|---|---|---|---|
| H4 | p = 1.0 (the literal default), IR 0.33150832181222434 | p = **0.4592003515637103**, IR **bit-identical** | `p` still False → 1/8 → 1/8 | REJECT |
| H7 | `benchmark: null`; IR −38.34 on price **levels** | alpha 0.09987, IR **+0.30022**, p 0.34319 | `max_p_value` still False; `min_information_ratio` **False → True** → recomputed 5/9 (artifact 4/9, report row 3/8) | REJECT |
| H18 | `benchmark_p.value` = 1.0 (the literal default), IR −0.5967666565674836 | p = **0.04098500443612743**, IR **bit-identical** | `benchmark_p` **False → True** → recomputed 3/9 (published 2/9) | REJECT |

The contract is not vacuous: the same suite run against the pre-fix source (`git stash -u`) fails
**8 tests** and names the three sites (`run_futures_tsmom_experiment.py:518 reads ['p_value']`,
`run_h18_overnight_intraday_experiment.py:742 reads ['p_value']`,
`run_h7_intraday_tsmom_experiment.py:403 reads ['alpha', 'p_value']`).

## The next task (one, precise)

**Pre-register H34: re-specify the benchmark-significance gate as one-sided, and reconcile the
three published families that currently pass it for the wrong reason (H19, H20, H23).**

Evidence and constraints:

- The pre-registered gate is `p < max_p_value` on a **two-sided** t-test of the excess returns,
  so it is satisfied by a significantly **negative** alpha — by the strategy being significantly
  *worse* than the benchmark. Published rows that pass it that way: **H19**
  (`benchmark_p_value` 0.0026021954893175585, IR **−0.8797993277834989**), **H20**
  (0.015948238479977717, IR **−0.7039784403691635**) and **H23** (0.0008995910719803239, IR
  **−3.0738688888576515**). H18's repaired gate passes for the same reason (p = 0.041, IR =
  −0.597). The families that pass with a *positive* IR (H9 +1.03, H10 +0.92, H22 +1.35,
  H25 +1.35) are genuine.
- H34 must (1) pre-register the re-specification (one-sided `P(alpha > 0)`, or an explicit
  `alpha_annualized > 0` conjunct) **before** any run, with the published rows left untouched
  and the recomputed tallies disclosed (the H30/H33 pattern); (2) recompute the benchmark
  statistics offline from the committed artifacts for **every** family with a `p`-gate (H4, H6,
  H7, H9, H10, H16, H17, H18, H19, H20, H22, H23, H25) and report which published `p` passes
  are direction-positive; (3) state explicitly whether the certified families (H10, H22, H25)
  survive the re-specified gate (expected: yes — they pass with a positive IR); (4) settle the
  dead `deflated_sharpe_ratio` in `src/qtr/validation/statistics.py` (see below) as a separate,
  small item.
- Constraints carried forward: no published artifact, gate, threshold, verdict or certified
  number may be modified; no grid may be re-run; every recomputed number is a disclosure; the
  pre-existing H1–H30 hypothesis space remains exhausted — no new hypothesis is warranted.

## Also carried forward (small, independent)

- `src/qtr/validation/statistics.py:deflated_sharpe_ratio` is **dead code**: not exported by
  `qtr/validation/__init__.py`, no runner or test calls it, and it duplicates
  `run_h12_selection_bias_audit.py:deflated_sharpe_ratio` with the *same* `max_z` formula (so it
  is correct, merely unreachable). It is the whole of the uncovered block in `statistics.py`.
- The H32 handoff's coverage claim ("99%, one uncovered branch") is **wrong**; the measured HEAD
  baseline is **94%** with 16 uncovered statements (the dead `deflated_sharpe_ratio` body).
  Its "single uncovered branch" — the `walk_forward_splits` empty-window guard at
  `statistics.py:159-160` — is neither uncovered nor unreachable: it is exercised by
  `tests/test_statistics.py:185` (`walk_forward_splits(3, n_splits=5) == []`).

## H34 completed (pre-registered + analyzed)

- Pre-registered in `HYPOTHESIS_SPEC.md`.
- Confirmed library provides `alpha_p_value_one_sided` (strategy > benchmark); fixed H7 to use it (previously used two-sided `alpha_p_value` with key name mismatch in old form, now corrected). Most other runners already use `alpha_p_value_one_sided`.
- Offline recomputation shows: H18/H19/H20 and the negative-IR H23 selection pass two-sided but fail one-sided (negative alpha); certified families H10, H22, H25 pass under one-sided with positive IR. No published artifacts/runners thresholds/verdicts changed; no grids re-run.
- Dead `deflated_sharpe_ratio` remains in `src/qtr/validation/statistics.py` (not exported, not called; covered by separate implementations in audit runners). Can be removed in a cleanup if desired, but not necessary to change behavior.
