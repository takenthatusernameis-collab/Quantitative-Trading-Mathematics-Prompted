"""``parameter_sensitivity`` must be reproducible when it is seeded.

**The defect (fixed in ``src/qtr/validation/statistics.py``).**
``parameter_sensitivity`` is part of the package's public API
(``qtr.validation.__all__``) and it was the *only* bootstrap caller in the
package that could not be seeded: it called ``bootstrap_confidence_interval``
**without** a ``random_state``, so ``np.random.default_rng(None)`` drew from
OS entropy and two calls on the same input returned *different* confidence
intervals.

Measured on a fixed input (``n_bootstrap=200``, two parameter rows)::

    ci_lower, run 1: [-0.7393122  -2.54308907]
    ci_lower, run 2: [-0.93933284 -3.07895489]

Its siblings already do the right thing -- ``sharpe_ratio_ci`` and
``bootstrap_confidence_interval`` both accept ``random_state`` -- and every
runner that calls the bootstrap directly passes one
(``run_cs_momentum_experiment.py:385``, ``run_ts_momentum_experiment.py:563``,
``run_regime_gated_momentum_experiment.py:725``).

**The correction.** ``parameter_sensitivity`` now takes an optional
``random_state``. The default stays ``None``, so no existing caller changes
behaviour; an integer seed is expanded into **one independent stream per
parameter row** (so the rows are not resampled with a shared pattern), and
the whole call becomes a pure function of the seed.

**The published record is unaffected.** No runner calls
``parameter_sensitivity``, and ``validate_strategy`` derives its published
``param_stability`` from the walk-forward fold Sharpes -- not from
``parameter_sensitivity``. Both facts are pinned below, so the disclosure
cannot silently lapse.

**How the negative control is made behavioural.** The seeded assertions go
through the adapter in ``_seeded()``, which passes ``random_state`` when the
signature takes it and otherwise calls the function without it. Against the
*pre-fix* implementation the adapter therefore exercises the unseeded path
and the contract fails on the *behaviour* (the bounds move), not on a
``TypeError`` for a missing keyword. A control that only says "the new
keyword exists" would not distinguish a fixed engine from an unfixed one.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from qtr.validation import statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATISTICS = ROOT / "src" / "qtr" / "validation" / "statistics.py"

N_BOOTSTRAP = 200
SEED = 42


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _returns(seed: int = 5, n: int = 400) -> np.ndarray:
    """A fixed two-row return matrix (one row per parameter setting)."""
    rng = np.random.default_rng(seed)
    return np.array(
        [
            rng.normal(0.0010, 0.01, n),
            rng.normal(-0.0005, 0.01, n),
        ]
    )


def _params() -> np.ndarray:
    return np.array([1.0, 2.0])


def _takes_random_state() -> bool:
    """Does ``parameter_sensitivity`` accept a ``random_state``?"""
    return "random_state" in inspect.signature(st.parameter_sensitivity).parameters


def _seeded(returns: np.ndarray, param_values: np.ndarray, seed: int = SEED) -> dict:
    """Call ``parameter_sensitivity`` with a seed, under either engine version.

    Against the pre-fix implementation (no ``random_state`` parameter) the
    call goes down the unseeded path -- which is precisely the behaviour the
    contract forbids -- so the assertions fail on the *bounds moving* rather
    than on a missing keyword.
    """
    kwargs: dict = {"n_bootstrap": N_BOOTSTRAP}
    if _takes_random_state():
        kwargs["random_state"] = seed
    return st.parameter_sensitivity(returns, param_values, **kwargs)


def _prefix_parameter_sensitivity(
    returns: np.ndarray,
    param_values: np.ndarray,
    metric_func=st.sharpe_ratio,
    n_bootstrap: int = N_BOOTSTRAP,
    random_state: int | None = None,
) -> dict:
    """The pre-fix behaviour: the seed is accepted but never reaches the bootstrap.

    This is the negative control -- it reconstructs the engine *before* the
    fix, so the contract below can be shown to be discriminating rather than
    vacuous.
    """
    n_params = len(param_values)
    metrics = np.zeros(n_params)
    ci_lower = np.zeros(n_params)
    ci_upper = np.zeros(n_params)

    for i in range(n_params):
        metrics[i] = metric_func(returns[i])
        # No random_state: the pre-fix call site dropped the seed on the floor.
        ci_lower[i], ci_upper[i] = st.bootstrap_confidence_interval(
            returns[i], metric_func, n_bootstrap=n_bootstrap
        )

    opt_idx = int(np.argmax(metrics))
    metric_std = metrics.std()
    return {
        "param_values": param_values,
        "metrics": metrics,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "optimal_param": param_values[opt_idx],
        "optimal_metric": metrics[opt_idx],
        "stability_ratio": float(np.sum(metrics >= metrics[opt_idx] - metric_std) / n_params),
        "metric_std": metric_std,
    }


# --------------------------------------------------------------------------- #
# the contract
# --------------------------------------------------------------------------- #
class TestSeededParameterSensitivity:
    def test_the_same_seed_reproduces_the_bounds_exactly(self):
        """Two calls with the same seed must agree bit-for-bit."""
        returns = _returns()
        a = _seeded(returns, _params())
        b = _seeded(returns, _params())

        np.testing.assert_array_equal(a["ci_lower"], b["ci_lower"])
        np.testing.assert_array_equal(a["ci_upper"], b["ci_upper"])

    def test_the_bounds_are_independent_of_the_global_numpy_random_state(self):
        """The seed must be the *only* source of randomness.

        The legacy global ``np.random.seed`` must not be able to move the
        result: a caller who seeds the global RNG elsewhere in the program
        still gets the same bounds.
        """
        returns = _returns()
        np.random.seed(0)
        a = _seeded(returns, _params())
        np.random.seed(1)
        b = _seeded(returns, _params())

        np.testing.assert_array_equal(a["ci_lower"], b["ci_lower"])
        np.testing.assert_array_equal(a["ci_upper"], b["ci_upper"])

    def test_a_different_seed_gives_different_bounds(self):
        """The seed must actually reach the bootstrap, not be ignored."""
        returns = _returns()
        a = _seeded(returns, _params(), seed=SEED)
        b = _seeded(returns, _params(), seed=SEED + 1)

        assert not (
            np.array_equal(a["ci_lower"], b["ci_lower"])
            and np.array_equal(a["ci_upper"], b["ci_upper"])
        ), "two different seeds produced identical bounds: the seed is not reaching the bootstrap"

    def test_the_point_estimates_do_not_depend_on_the_seed(self):
        """The seed moves the bounds only; the point estimates are fixed.

        This is the property the published record relies on: the *ranking* of
        the parameter settings was always deterministic, which is why the
        defect was invisible in the point estimates.
        """
        returns = _returns()
        a = _seeded(returns, _params(), seed=SEED)
        b = _seeded(returns, _params(), seed=SEED + 1)

        np.testing.assert_array_equal(a["metrics"], b["metrics"])
        assert a["optimal_param"] == b["optimal_param"]
        assert a["optimal_metric"] == b["optimal_metric"]
        assert a["stability_ratio"] == b["stability_ratio"]
        assert a["metric_std"] == b["metric_std"]

    def test_each_parameter_row_is_bootstrapped_with_its_own_stream(self):
        """Two identical rows must not share one resampling pattern.

        If every row were bootstrapped with the same seed, two rows holding
        the *same* data would report the *same* interval -- the rows would be
        perfectly correlated. Independent streams make them differ.
        """
        row = _returns()[0]
        duplicated = np.array([row, row])
        res = _seeded(duplicated, np.array([1.0, 2.0]))

        assert not np.array_equal(res["ci_lower"][0], res["ci_lower"][1]), (
            "two identical parameter rows produced identical intervals: the rows "
            "are sharing one bootstrap stream"
        )

    def test_extending_the_grid_does_not_perturb_the_rows_already_analysed(self):
        """A row's seed must not depend on how many rows the grid holds.

        Adding a parameter setting to the grid must not move the intervals
        already reported for the existing ones -- otherwise a study would
        have to re-interpret its earlier numbers every time the grid grew.
        """
        returns = _returns()
        two = _seeded(returns, np.array([1.0, 2.0]))
        three = _seeded(np.vstack([returns, returns[0]]), np.array([1.0, 2.0, 3.0]))

        np.testing.assert_array_equal(two["ci_lower"], three["ci_lower"][:2])
        np.testing.assert_array_equal(two["ci_upper"], three["ci_upper"][:2])

    def test_the_seeded_result_is_reproducible_across_processes(self):
        """The strongest form of the claim: a fresh interpreter agrees.

        Reproducibility inside one process could be an artefact of cached
        state; a second interpreter starts from a clean OS entropy pool, so
        agreement across processes is the property a reader of the record
        actually relies on.
        """
        script = "\n".join(
            [
                "import inspect, json, sys",
                "sys.path.insert(0, 'src')",
                "import numpy as np",
                "from qtr.validation import statistics as st",
                "rng = np.random.default_rng(5)",
                "returns = np.array([rng.normal(0.0010, 0.01, 400),"
                " rng.normal(-0.0005, 0.01, 400)])",
                f"kwargs = {{'n_bootstrap': {N_BOOTSTRAP}}}",
                "if 'random_state' in inspect.signature(st.parameter_sensitivity).parameters:",
                f"    kwargs['random_state'] = {SEED}",
                "res = st.parameter_sensitivity(returns, np.array([1.0, 2.0]), **kwargs)",
                "print(json.dumps([res['ci_lower'].tolist(), res['ci_upper'].tolist()]))",
            ]
        )
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=env,
            check=True,
        )

        ci_lower, ci_upper = json.loads(proc.stdout.strip().splitlines()[-1])
        local = _seeded(_returns(), _params())
        np.testing.assert_array_equal(local["ci_lower"], np.array(ci_lower))
        np.testing.assert_array_equal(local["ci_upper"], np.array(ci_upper))


# --------------------------------------------------------------------------- #
# the negative control: the pre-fix call site must fail the contract
# --------------------------------------------------------------------------- #
class TestNegativeControl:
    def test_the_unseeded_path_really_moves(self):
        """The default path is genuinely non-reproducible.

        Without this the whole contract could be vacuous: if the *unseeded*
        path happened to be stable, "the seeded path is stable" would prove
        nothing about the seed.
        """
        returns = _returns()
        a = st.parameter_sensitivity(returns, _params(), n_bootstrap=N_BOOTSTRAP)
        b = st.parameter_sensitivity(returns, _params(), n_bootstrap=N_BOOTSTRAP)

        assert not (
            np.array_equal(a["ci_lower"], b["ci_lower"])
            and np.array_equal(a["ci_upper"], b["ci_upper"])
        ), (
            "two unseeded calls produced identical bounds: the unseeded path is "
            "not actually drawing fresh randomness"
        )

    def test_the_pre_fix_call_site_fails_the_reproducibility_contract(self):
        """The contract is discriminating, not vacuous.

        The pre-fix implementation -- the seed accepted but never threaded
        into the bootstrap -- is reconstructed here and shown to violate the
        invariant the tests above assert.
        """
        returns = _returns()
        a = _prefix_parameter_sensitivity(returns, _params(), random_state=SEED)
        b = _prefix_parameter_sensitivity(returns, _params(), random_state=SEED)

        assert not (
            np.array_equal(a["ci_lower"], b["ci_lower"])
            and np.array_equal(a["ci_upper"], b["ci_upper"])
        ), (
            "the pre-fix call site satisfies the reproducibility invariant, so "
            "the contract cannot distinguish it from the fixed implementation"
        )

    def test_the_pre_fix_call_site_leaves_the_point_estimates_alone(self):
        """Only the *bounds* were broken; the point estimates always agreed.

        This is why the defect was invisible in every published number.
        """
        returns = _returns()
        a = _prefix_parameter_sensitivity(returns, _params(), random_state=SEED)
        b = _prefix_parameter_sensitivity(returns, _params(), random_state=SEED)

        np.testing.assert_array_equal(a["metrics"], b["metrics"])
        assert a["optimal_param"] == b["optimal_param"]
        assert a["stability_ratio"] == b["stability_ratio"]


# --------------------------------------------------------------------------- #
# the published record: a disclosure, not a rewrite
# --------------------------------------------------------------------------- #
class TestPublishedRecordDisclosure:
    """Nothing in the published record reads ``parameter_sensitivity``."""

    def _runners(self) -> list[pathlib.Path]:
        return sorted(p for p in ROOT.iterdir() if p.is_file() and p.name.startswith("run_"))

    def test_no_runner_calls_parameter_sensitivity(self):
        """No runner may depend on the unseeded bounds."""
        offenders: list[str] = []
        for runner in self._runners():
            tree = ast.parse(runner.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == "parameter_sensitivity":
                    offenders.append(f"{runner.name}:{node.lineno}")
                elif isinstance(node, ast.Attribute) and node.attr == "parameter_sensitivity":
                    offenders.append(f"{runner.name}:{node.lineno}")
        assert not offenders, (
            f"a runner now calls parameter_sensitivity ({offenders}); the seeded "
            "bounds must be threaded into it and the record re-checked"
        )

    def test_validate_strategy_does_not_derive_its_stability_from_the_bootstrap(self):
        """The published ``param_stability`` must not come from the bootstrap.

        ``validate_strategy`` computes it from the walk-forward fold Sharpes
        (``src/qtr/validation/statistics.py``), so the ``min_param_stability``
        gate stays deterministic and no published number moves.
        """
        tree = ast.parse(STATISTICS.read_text())
        validate = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "validate_strategy"
        )
        referenced = {
            node.id
            for node in ast.walk(validate)
            if isinstance(node, ast.Name)
            and node.id in {"parameter_sensitivity", "bootstrap_confidence_interval"}
        }
        assert not referenced, (
            f"validate_strategy now references {sorted(referenced)}: the published "
            "param_stability would depend on the bootstrap bounds"
        )

    def test_the_published_param_stability_is_the_walk_forward_fold_fraction(self):
        """The value is recomputed independently from the fold Sharpes."""
        rng = np.random.default_rng(3)
        returns = pd.Series(rng.normal(0.0008, 0.01, 500))
        trades = pd.DataFrame({"symbol": ["A"] * 10})

        res = st.validate_strategy(returns, trades, {"min_trades": 0})

        splits = st.walk_forward_splits(len(returns), n_splits=5)
        fold_sharpes = [
            st.sharpe_ratio(returns.iloc[test].values) for _, test in splits if len(test) > 1
        ]
        expected = float(np.mean(np.array(fold_sharpes) > 0))
        assert res["param_stability"] == pytest.approx(expected)

    def test_the_published_gate_is_deterministic(self):
        """``validate_strategy`` gives the same answer every time.

        The published ``param_stability`` gate must not move between calls or
        between runs -- it is computed from the fold Sharpes, not from any
        resampling.
        """
        rng = np.random.default_rng(3)
        returns = pd.Series(rng.normal(0.0008, 0.01, 500))
        trades = pd.DataFrame({"symbol": ["A"] * 10})

        first = st.validate_strategy(returns, trades, {"min_trades": 0})
        np.random.seed(99)
        second = st.validate_strategy(returns, trades, {"min_trades": 0})

        assert first["param_stability"] == second["param_stability"]
        assert first["param_stability_pass"] == second["param_stability_pass"]
        assert first["all_pass"] == second["all_pass"]
