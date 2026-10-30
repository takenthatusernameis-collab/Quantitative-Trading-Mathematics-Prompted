# HANDOFF_CURRENT — session complete (H77: CI gate workflow restored after HEAD deleted it)

## State
- H1–H30 exhausted; H35–H77 complete per handoffs; certified families frozen.
  **H77 = restoration of `.github/workflows/gates.yml` after HEAD `876a15f`
  deleted it** (the H76 artifact). No `src/qtr` change.
- Baseline verified in this session: lint/format gates green; the restored
  workflow is byte-identical to the verified H76 artifact.
- HEAD: `876a15f`.

## What changed (this session)
- `.github/workflows/gates.yml` — **restored**, byte-identical to
  `a9e9fe1:.github/workflows/gates.yml` (diff confirmed empty). Two jobs on
  `push` to `main`, `pull_request` and `workflow_dispatch`, path-filtered to
  `src/`, `tests/`, `run_*.py`, `requirements.txt`, `pyproject.toml` and the
  workflow itself:
  - `lint` — `python -m ruff check src tests run_*.py` and
    `python -m ruff format --check src tests run_*.py`.
  - `research_gates` — `python -m pytest -q -W error --cov=qtr --cov-branch
    --cov-report=term-missing`, enforcing `fail_under = 100` with branch
    coverage.
- The previous handoffs all described this file as present; it was not on
  disk. The deletion at `876a15f` is treated as an unintended regression.
- No source, test, runner, artifact, gate threshold, verdict or certified
  number was modified. No grid was re-run. The H1–H30 hypothesis space
  remains exhausted.

## What was actually verified (this session)
- `diff <(git show a9e9fe1:.github/workflows/gates.yml) .github/workflows/gates.yml`
  → empty; **byte-identical to the verified artifact**.
- `git log --oneline -- .github/workflows/gates.yml` → `876a15f` (delete),
  `a9e9fe1` (add), `d080a1e` (delete), `d878dad` (add): the file has been
  added and deleted repeatedly; this session restores it.
- `python -c "import yaml; yaml.safe_load(...)"` → the workflow parses; triggers
  are `push`/`pull_request`/`workflow_dispatch`.
- `python -m ruff check src tests run_*.py` → **All checks passed!**
- `python -m ruff format --check src tests run_*.py` → **105 files already
  formatted**
- `.github/scripts/kilo-controller.sh` untouched; `bash -n` still passes, so
  the existing Kilo orchestration and its `kilo-workflow-audit.yml` guards are
  unaffected.
- `pip show qtr` → not installed (bare clone state confirmed).

## What remains unresolved
- Whether the deletion at `876a15f` was intentional is not recorded anywhere in
  the tree; every handoff describes the file as present, so the deletion is
  treated as an unintended regression.
- Items in `FINAL_REPORT.md` §H53–§H61 remain disclosed (not quantified) — each
  depends on an input the record does not hold. None can be resolved without
  new committed inputs; none affect gates.
- The new workflow's real-world execution is unverified: it cannot run in this
  sandbox (no GitHub Actions runner), so it was verified by byte-identity to
  the verified artifact and by each of its commands being green in-tree.

## Approaches already failed (this session)
- **Committing the restored file.** Rejected: the no-commit-without-explicit-
  request rule applies, and the previous H76 session also left it untracked.
  The file is restored on disk; a commit is a separate decision for the user.
- **Re-running the full pytest+coverage suite.** Rejected as unnecessary: the
  restoration changes no source, test, runner, artifact, gate threshold, verdict
  or certified number, and the file is byte-identical to the already-verified
  artifact. The lint/format commands the workflow runs were re-run to confirm
  the tree is still green.

## Precise next task
**None assigned.** If a future session touches CI or the gates it enforces:
1. Keep the two jobs' commands identical to the documented gates in
   `AGENTS.md` and `pyproject.toml`; do not relax `fail_under`, drop `-W error`
   or remove the format check.
2. After any change that could move the gate surface, re-run
   `python -m pytest -q -W error --cov=qtr --cov-branch --cov-report=term-missing`
   and the ruff commands and confirm `src/qtr` stays at 100% (statement+branch).
3. Do not `pip install -e .` unless a test requires it; restore the bare-clone
   state (qtr uninstalled) afterwards.

## Constraints carried forward
- No published artifact, gate threshold, verdict or certified number may be
  modified. No grid may be re-run. The H1–H30 hypothesis space remains
  exhausted.
- `src/qtr` must remain at 100% coverage (statement + branch).
- Ruff lint and format gates must stay clean.
- After changes under `src/qtr` or runners/validation, re-run causality/metric
  agreement/benchmark gate/public API/ruff reproducibility/coverage gate/trade
  log reconciliation/tsmom signal/generated manifest/runner import contract/
  data fetcher contracts and confirm `src/qtr` stays at 100% coverage with
  gates green.
- `requirements.txt` is the contract that must declare every dependency a
  pinned contract test imports; verify it by running the suite from a fresh
  venv with only `pip install -r requirements.txt`.
- qtr is left **uninstalled** (bare clone) — do not `pip install -e .` unless
  a test requires it, and restore that state if you do.

(End of file)