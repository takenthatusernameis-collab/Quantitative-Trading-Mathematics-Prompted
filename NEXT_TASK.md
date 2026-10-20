# Next Task — H35 complete; every published gate fails closed (2026-10-20)

## State

**H34 and its follow-up are COMPLETE, and H35 is COMPLETE.** The benchmark-significance
gate is direction-aware in code and published (H34); the *remaining* gate-defect class —
gates that are a constant, or that compare a placeholder, and can therefore never fail —
has been audited, disclosed and pinned (H35). The published record is re-disclosed in full.
**No published artifact, gate threshold, verdict, certified number or published row was
modified; no grid was re-run.**

### What changed (H35)

- `src/qtr/validation/statistics.py:compare_to_benchmark` — the docstring now states
  explicitly that `alpha_p_value_one_sided` is an **informational** view and **not** the
  gate's statistic (a one-sided test at 5% is a two-sided test at 10%, so it is strictly
  *looser* than the published gate). This closes the item H34 carried forward.
- `run_futures_tsmom_experiment.py:547` (H4), `run_ddcv_experiment.py:457` (H5),
  `run_h6_vix_ddcv_experiment.py:553` (H6) — the IR threshold is read by direct subscript
  (`GATES["min_information_ratio"]`) instead of `GATES.get("min_information_ratio", -1e18)`.
  **Behaviour-preserving:** the key exists in all three runners and its value (`0.0`) is
  unchanged, so no published number, tally, threshold or verdict changes; a *missing*
  threshold now fails loudly instead of silently making the gate unconditionally true.
- `tests/test_gate_vacuity_contract.py` (new, 11 tests) — the executable invariant (below).
- `tests/test_benchmark_gate_contract.py` — one new test pins that the one-sided p-value is
  strictly looser than the gate (and therefore must never be substituted for it).
- `HYPOTHESIS_SPEC.md` §H35, `FINAL_REPORT.md` §H35, `FINAL_REPORT.md` §H34's verification
  paragraph, and this file.

### The audit (offline static — no grid re-run)

| # | Site | Class | Effect on the published record |
|---|------|-------|------------------------------|
| F1 | `run_h7_intraday_tsmom_experiment.py:466-467` | constant | `min_perturbed_sharpe_ratio` and `min_worst_regime_sharpe` are hard-coded `True`; H7 never computes either statistic. **Two of H7's nine gates can never fail.** |
| F2 | `run_h18_overnight_intraday_experiment.py:764` | placeholder | `perturbation_ratio = 1.0  # Placeholder`, so the `perturbation_ratio` gate (`>= 0.5`) can never fail. **One of H18's nine gates can never fail.** |
| F3 | `run_h18_overnight_intraday_experiment.py:768-807, 831-874` | drift risk | H18 is the only runner that spells its nine thresholds out instead of reading a shared `GATES` dict. The values are currently **equal** to the shared PROMPT_V2 gate set (now pinned). |
| F4 | H4 / H5 / H6 (see above) | permissive default | **latent**: the sentinel made the IR gate unconditionally true if the key were ever removed. Fixed. |

**No certified family is affected:** the audit finds a non-evaluating gate in **H7 and H18
only**. The certified families (H9, H10, H11, H12, H21, H22, H25) and every other family
evaluate all of their gates.

### The disclosed non-evaluating gates (recomputed offline from the artifacts)

| Family | published tally | free PASSes | tally on the evaluable gates | verdict |
|--------|-----------------|-------------|------------------------------|---------|
| H7 | **4/9** (`exp_2026-10-19T18-56-08-872500Z`) | 2 | **2/7** | REJECT (unchanged) |
| H18 | **2/9** (`exp_2026-10-13T22-14-50-729923Z`) | 1 | **1/8** | REJECT (unchanged) |

Forcing the disclosed gates to False leaves both families short of an all-pass, so **no
published verdict rests on a gate that never tests anything**. F1–F3 are **disclosed and
pinned, not silently repaired**: implementing the missing perturbation / worst-regime
statistics would require re-running the H7 and H18 grids (forbidden) and would change
published tallies.

### A correction to the H34 disclosure tables (citation only)

The H34 tables in `FINAL_REPORT.md` and `HYPOTHESIS_SPEC.md` cited H18's artifact as
`exp_2026-10-13T22-13-37-475937Z`. H18's **published** row is
`exp_2026-10-13T22-14-50-729923Z` (named in H18's Measure Log and in the H33 evidence
section; the only one with the published 2/9 tally). The two earlier siblings record a 3/9
tally — their `max_drawdown` gate still read `True` although the OOS drawdown is 22.2%
against a 15% limit (the drawdown gate was corrected before the published run). The H34
rows' **numbers** are identical in all three artifacts, so only the **pointer** changed.

### The executable invariant

`tests/test_gate_vacuity_contract.py`:

1. no runner may read a gate threshold through `GATES.get(key, default)`;
2. every `GATES["key"]` a runner reads must exist in that runner's `GATES` dict, resolved
   through the `from X import GATES` chain (the derived runners are covered too);
3. the set of gates that are a constant or that compare a placeholder is **pinned to the
   disclosed set** — a new always-true gate fails the suite;
4. forcing the disclosed gates to False changes no published verdict (recomputed offline
   from the committed artifacts);
5. H18's hard-coded thresholds are pinned **equal** to the shared gate set;
6. the published H18 artifact is pinned to the one its Measure Log names;
7. a synthetic negative control proves the detectors fire.

### Verification

- `python -m pytest -q -W error` → **748 passed** (736 + 12 new).
- `python -m pytest --cov=qtr --cov-report=term-missing` → `src/qtr` coverage **100%**
  (1010 statements, 0 missed).
- **Negative control:** the new module run against the pre-H35 runner sources fails **1**
  test and names the three permissive-default sites, so the contract really binds the
  change.
- No published artifact, gate threshold, verdict or certified number was modified; no grid
  was re-run; no hypothesis was added.

## Status (this session — COMPLETE)

1. The gate-vacuity class is audited, disclosed and pinned (H35).
2. The one latent permissive-default read is fixed (behaviour-preserving).
3. The `alpha_p_value_one_sided` item H34 carried forward is **closed**: the field is kept
   as a documented informational output, explicitly *not* the gate's statistic, and the
   non-equivalence is pinned by a test.
4. The published record is consistent again: the stale `## Next Task (updated 2026-10-20,
   after H34)` section of `FINAL_REPORT.md` (which still assigned the three-part H34
   follow-up) now describes the state after H35, the H34 verification paragraph states that
   the suite has since grown, and the `Summary statistics` bullets are re-baselined.

## The next task (one, precise)

**None assigned — the pre-registered free-data hypothesis space (H1–H30) is exhausted and
every gate class that has produced a defect so far is now closed by an executable
invariant.** Two small, self-contained items remain open and are recorded here so that a
future session can pick them up without re-deriving them:

1. **Make the `ruff` verification step reproducible from the declared dependency set.**
   `ruff check` / `ruff format --check` is quoted as a verification step throughout
   `HYPOTHESIS_SPEC.md`, `FINAL_REPORT.md` and `NEXT_TASK.md`, and the sources carry
   `# noqa: BLE001` / `# noqa: UP045` markers that assume a **non-default** ruff rule
   selection — but ruff is **not** declared in `pyproject.toml` or `requirements.txt`, is
   **not** installed in the agent environment (`python -m ruff` → "No module named ruff"),
   and **no ruff configuration is committed** (there is no `[tool.ruff]` section, no
   `ruff.toml` and no `.ruff.toml`). The quoted lint result therefore cannot be
   reproduced from the repository as it stands. The bounded fix is to declare ruff in
   `pyproject.toml` (`[project.optional-dependencies] lint`) and commit the ruff
   configuration that makes the quoted commands meaningful — and to check whether the
   installed ruff reports the tree clean under that configuration before quoting it again.
   **Evidence to re-check first:** `pip install ruff` (network), then
   `ruff check src tests run_*.py` and `ruff format --check src tests run_*.py`.
2. **Nothing else is warranted.** Do **not** re-run any grid, do **not** modify a published
   artifact, gate threshold, verdict or certified number, and do **not** add a hypothesis:
   the free-data hypothesis space is exhausted and the H1–H30 records are frozen.

## Constraints carried forward

- No published artifact, gate threshold, verdict or certified number may be modified.
- No grid may be re-run; every recomputed number is a **disclosure**, not a rewrite.
- The pre-existing H1–H30 hypothesis space remains exhausted — no new hypothesis is
  warranted.
- The certified families' numbers and verdicts are frozen (H10, H11, H12, H22, H25).
