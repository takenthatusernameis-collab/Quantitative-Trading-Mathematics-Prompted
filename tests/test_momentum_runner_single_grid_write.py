"""Guard: each momentum runner logs ``param_grid_results`` exactly once.

**The defect (fixed in the runners, Cycle 243).**
``run_ts_momentum_experiment.py``, ``run_cs_momentum_experiment.py`` and
``run_regime_gated_momentum_experiment.py`` each called
``tracker.log_dataframe("param_grid_results", ...)`` twice inside one run: once
with the pre-correction grid (before the walk-forward p-value columns were
attached) and once with the final grid. ``ExperimentTracker.log_dataframe``
writes ``<artifact_dir>/param_grid_results.parquet`` in place, so the second
write overwrote the first; the experiment record then carried the *first*
write's SHA-256 suffix, which can never match the file on disk. That is the
"8 × ``param_grid_results``" block of the 11 ``hash_mismatches`` in
``REPRODUCIBILITY_AUDIT_REPORT.md`` §2 (three runners × their repeat runs).

**The correction.** Each runner now writes ``param_grid_results`` once, at the
final path, after all columns are attached. The first write was always
superseded, so removing it leaves the on-disk artifact byte-identical; only the
stale recorded hash disappears from future runs.

**Why the parse is static.** The runners are heavyweight experiment harnesses
that need a market-data panel; no test in this suite executes their ``main()``
(the committed artifacts were produced out-of-band). A behavioural test would
therefore have to re-run a full backtest grid to observe the double write. The
contract is about how many times the runner *writes* the artifact, which is a
property of the source, so it is pinned with an AST count. ``ast`` ignores
comments and string literals, so the explanatory comments above the surviving
call do not perturb the count.

``test_the_detector_fires_on_the_pre_fix_double_write`` is the negative
control: it runs the same detector against a verbatim reconstruction of the
pre-fix call pattern and shows the count is 2 there, so the single-write
assertion is discriminating rather than vacuous.

Read-only: does not modify ``src/qtr``, frozen-contract tests, or artifacts.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUNNERS = [
    "run_ts_momentum_experiment.py",
    "run_cs_momentum_experiment.py",
    "run_regime_gated_momentum_experiment.py",
]
ARTIFACT_NAME = "param_grid_results"


def _grid_write_count(source: str) -> int:
    """Count ``<tracker>.log_dataframe("param_grid_results", <df>)`` calls.

    Only calls whose first positional argument is the literal artifact name are
    counted; a call that passes a variable (or a different literal) is not a
    ``param_grid_results`` write and is ignored.
    """
    tree = ast.parse(source)
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "log_dataframe"):
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and first.value == ARTIFACT_NAME:
            count += 1
    return count


def _count_for(runner: str) -> int:
    return _grid_write_count((ROOT / runner).read_text())


@pytest.mark.parametrize("runner", RUNNERS)
def test_runner_logs_param_grid_results_exactly_once(runner):
    """Each momentum runner must write ``param_grid_results`` to one path once."""
    assert _count_for(runner) == 1, (
        f"{runner} writes {ARTIFACT_NAME!r} {_count_for(runner)} times; "
        "log_dataframe overwrites the same parquet path in place, so every "
        "write after the first leaves a stale hash in the experiment record "
        "(REPRODUCIBILITY_AUDIT_REPORT.md §2)."
    )


def test_the_detector_fires_on_the_pre_fix_double_write():
    """Negative control: the pre-fix double write is counted as two.

    This reconstructs the exact pre-fix pattern (an early grid write, then a
    final write of the same artifact name) and shows the detector used above
    reports two calls, so the single-write contract above is not vacuous.
    """
    pre_fix_source = (
        "combos = pd.DataFrame(records)\n"
        'tracker.log_dataframe("param_grid_results", combos)\n'
        "for r, ap, j in zip(records, adj, rej):\n"
        '    r["wf_oos_adj_pvalue"] = float(ap)\n'
        '    r["wf_oos_significant"] = bool(j)\n'
        'tracker.log_dataframe("param_grid_results", pd.DataFrame(records))\n'
    )
    assert _grid_write_count(pre_fix_source) == 2


def test_the_detector_ignores_other_artifacts_and_non_literal_names():
    """The count is specific to the ``param_grid_results`` literal.

    A call logging a different artifact, or one whose first argument is a
    variable, must not be counted -- otherwise a runner that legitimately logs
    several distinct artifacts would trip the guard.
    """
    source = (
        'tracker.log_dataframe("selected_equity", equity)\n'
        "tracker.log_dataframe(name, frame)\n"
        'tracker.log_dataframe("param_grid_results", grid)\n'
    )
    assert _grid_write_count(source) == 1
