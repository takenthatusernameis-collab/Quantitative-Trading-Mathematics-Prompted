"""H35 — the published gates must fail closed.

H33 found three benchmark gates that evaluated a *constant* instead of a
statistic, and H34 re-specified the benchmark-significance gate so that it
is direction-aware. H35 closes the remaining half of that defect class: a
gate that is a constant, or that compares a placeholder constant, can never
fail, so it contributes a free PASS to the published tally.

The detectors below are static (no grid is re-run, no artifact is touched):

1. **No permissive threshold default.** A runner must not read a gate
   threshold through ``GATES.get(key, default)``: a permissive default
   silently turns the gate into a constant if the key is ever removed.
2. **Every threshold key exists.** Every ``GATES["key"]`` a runner reads
   must be a key of that runner's ``GATES`` dict, resolved through the
   ``from X import GATES`` chain.
3. **No gate is a constant.** Every gate expression must depend on a
   computed statistic. The gates that are a constant, or that compare a
   placeholder constant, are pinned to the *disclosed* set, so a new
   always-true gate cannot appear silently.

The disclosed gates belong to families that are REJECT in the published
record; the artifact test below recomputes the tallies offline and shows
that forcing those gates to False changes no verdict.
"""

import ast
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The names under which a runner stores its gate results.
GATE_DICT_NAMES = {"gates", "passes", "gate_results"}

# The published gates that are known NOT to evaluate a statistic: they are a
# constant, or they compare a placeholder constant. Disclosed in
# HYPOTHESIS_SPEC.md section H35 and in FINAL_REPORT.md; pinned here so that
# they cannot change silently.
DISCLOSED_NON_EVALUATING_GATES = {
    # H7 never computes a perturbation ratio or a worst-regime Sharpe; both
    # gates are hard-coded True.
    ("run_h7_intraday_tsmom_experiment.py", "min_perturbed_sharpe_ratio"),
    ("run_h7_intraday_tsmom_experiment.py", "min_worst_regime_sharpe"),
    # H18 never computes a perturbation ratio: it is a placeholder constant.
    ("run_h18_overnight_intraday_experiment.py", "perturbation_ratio"),
}

# The published artifact of each family that owns a disclosed gate, and the
# key under which the artifact records its gate booleans.
PUBLISHED_ARTIFACTS = {
    "H7": ("exp_2026-10-19T18-56-08-872500Z", "gates"),
    "H18": ("exp_2026-10-13T22-14-50-729923Z", "gate_metrics"),
}

ARTIFACTS = ROOT / ".experiments" / "artifacts"


# --------------------------------------------------------------------------- #
# the detectors
# --------------------------------------------------------------------------- #
def _runner_files() -> list[pathlib.Path]:
    files = sorted(ROOT.glob("run_*.py"))
    assert len(files) >= 10, f"expected the runner scripts, found {len(files)}"
    return files


def _parse(path: pathlib.Path) -> ast.AST:
    return ast.parse(path.read_text())


def _gates_dict(path: pathlib.Path, _seen: frozenset = frozenset()) -> dict[str, float] | None:
    """The ``GATES`` dict a runner uses.

    ``None`` means the runner has no ``GATES`` literal of its own and does not
    import one (it therefore has no threshold to read).
    """
    if path in _seen:
        return None
    _seen = _seen | {path}
    tree = _parse(path)

    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Dict)
            and any(
                isinstance(t, ast.Name) and t.id == "GATES" for t in node.targets
            )
        ):
            return {
                key.value: value.value
                for key, value in zip(node.value.keys, node.value.values)
                if isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and isinstance(value, ast.Constant)
            }

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module
            and any(alias.name == "GATES" for alias in node.names)
        ):
            source = ROOT / f"{node.module}.py"
            if source.exists():
                return _gates_dict(source, _seen)
    return None


def _gates_keys(path: pathlib.Path, _seen: frozenset = frozenset()) -> set[str] | None:
    """The keys of the ``GATES`` dict a runner uses."""
    gates = _gates_dict(path, _seen)
    return None if gates is None else set(gates)


def _gates_values(path: pathlib.Path) -> dict[str, float]:
    """The numeric values of the ``GATES`` dict a runner uses."""
    gates = _gates_dict(path)
    assert gates is not None, f"{path.name} has no GATES dict"
    return gates


def _permissive_threshold_reads(tree: ast.AST) -> list[str]:
    """``GATES.get(key, default)`` reads: a permissive default for a
    threshold."""
    offenders = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "GATES"
            and len(node.args) >= 2
        ):
            offenders.append(f"line {node.lineno}: {ast.unparse(node)}")
    return offenders


def _threshold_key_reads(tree: ast.AST) -> list[tuple[str, int]]:
    """Every ``GATES["key"]`` read: (key, line)."""
    reads = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "GATES"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            reads.append((node.slice.value, node.lineno))
    return reads


def _constant_assigned_names(tree: ast.AST) -> set[str]:
    """Names whose value is fixed: assigned a plain numeric/boolean constant
    and never anything else.

    A name that is *also* assigned a computed value is not fixed (a fallback
    branch may set a constant while the normal branch computes the
    statistic), so it is deliberately not reported.
    """
    constants: set[str] = set()
    computed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if (
                isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, (int, float, bool))
            ):
                constants.add(target.id)
            else:
                computed.add(target.id)
    return constants - computed


def _gate_expressions(tree: ast.AST) -> list[tuple[str, int, ast.expr]]:
    """Every gate expression: (gate name, line, expression).

    Two shapes are recognised: a flat mapping of gate name to boolean
    expression (``passes = {...}``) and a mapping of gate name to a nested
    gate record whose ``pass``/``passes`` entry is the expression
    (``gates = {...}``).
    """
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id in GATE_DICT_NAMES for t in node.targets
        ):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if not (
                isinstance(key, ast.Constant) and isinstance(key.value, str)
            ):
                continue
            if isinstance(value, ast.Dict):
                for inner_key, inner_value in zip(value.keys, value.values):
                    if (
                        isinstance(inner_key, ast.Constant)
                        and inner_key.value in ("pass", "passes")
                    ):
                        found.append((key.value, inner_value.lineno, inner_value))
            else:
                found.append((key.value, value.lineno, value))
    return found


def _non_evaluating_gates(tree: ast.AST) -> list[tuple[str, int]]:
    """Gates whose outcome cannot depend on the data."""
    constants = _constant_assigned_names(tree)
    offenders = []
    for name, lineno, expr in _gate_expressions(tree):
        if isinstance(expr, ast.Constant):
            offenders.append((name, lineno))
            continue
        if isinstance(expr, ast.Compare):
            loaded = {
                node.id for node in ast.walk(expr) if isinstance(node, ast.Name)
            }
            if loaded & constants:
                offenders.append((name, lineno))
    return offenders


# --------------------------------------------------------------------------- #
# 1. the threshold contract
# --------------------------------------------------------------------------- #
def test_no_runner_reads_a_gate_threshold_through_a_permissive_default():
    """``GATES.get(key, default)`` for a *threshold* is the H33 defect class in
    waiting: with a permissive default the gate passes whatever the data
    says, and the missing key is invisible. The threshold must be read by
    direct subscript so a missing key fails loudly."""
    offenders = []
    for path in _runner_files():
        for offender in _permissive_threshold_reads(_parse(path)):
            offenders.append(f"{path.name}:{offender}")
    assert offenders == []


def _missing_threshold_keys(tree: ast.AST, gates_keys: set[str]) -> list[str]:
    """The ``GATES["key"]`` reads whose key the runner's ``GATES`` does not
    define."""
    return [
        f"line {lineno}: {key!r}"
        for key, lineno in _threshold_key_reads(tree)
        if key not in gates_keys
    ]


def test_every_threshold_key_a_runner_reads_exists():
    """A runner that reads a key its own ``GATES`` does not define either
    raises at run time or falls back to a default that silently changes the
    gate. The threshold set must be closed."""
    offenders = []
    for path in _runner_files():
        keys = _gates_keys(path)
        if keys is None:
            continue
        for offender in _missing_threshold_keys(_parse(path), keys):
            offenders.append(f"{path.name}:{offender}")
    assert offenders == []


def test_the_gate_set_is_shared_with_the_derived_runners():
    """The runners that import their gate set must resolve it, so the
    threshold contract above actually covers them."""
    derived = [
        "run_h10_intraday_tsmom_pfopt_experiment.py",
        "run_h11_robustness_experiment.py",
        "run_h12_selection_bias_audit.py",
        "run_h21_futures_tsmom_multicontract.py",
        "run_h22_futures_tsmom_voltarget.py",
        "run_h25_futures_tsmom_pfmargin.py",
    ]
    for name in derived:
        keys = _gates_keys(ROOT / name)
        assert keys is not None, f"{name} does not resolve a GATES dict"
        assert "min_sharpe" in keys
        assert "max_p_value" in keys


# --------------------------------------------------------------------------- #
# 2. the non-evaluating gate contract
# --------------------------------------------------------------------------- #
def test_the_non_evaluating_gates_are_the_disclosed_ones():
    """Only the disclosed gates may fail to evaluate a statistic."""
    found = set()
    for path in _runner_files():
        for name, _lineno in _non_evaluating_gates(_parse(path)):
            found.add((path.name, name))
    assert found == DISCLOSED_NON_EVALUATING_GATES


def test_the_detectors_fire_on_a_synthetic_offender():
    """Negative control: the detectors must actually detect the defects they
    claim to rule out, otherwise the contract above is vacuous."""
    source = (
        "GATES = {'min_sharpe': 1.0, 'min_information_ratio': 0.0}\n"
        "def f(x, ir):\n"
        "    placeholder = 1.0\n"
        "    passes = {\n"
        "        'sharpe': x >= GATES['min_sharpe'],\n"
        "        'ir': ir > GATES.get('min_information_ratio', -1e18),\n"
        "        'typo': x >= GATES['min_sharpe_typo'],\n"
        "        'constant_gate': True,\n"
        "        'placeholder_gate': placeholder >= 0.5,\n"
        "    }\n"
        "    gates = {\n"
        "        'sharpe': {'value': x, 'threshold': 1.0, 'pass': x >= 1.0},\n"
        "    }\n"
        "    return passes, gates\n"
    )
    tree = ast.parse(source)

    permissive = _permissive_threshold_reads(tree)
    assert len(permissive) == 1
    assert "min_information_ratio" in permissive[0]

    reads = dict(_threshold_key_reads(tree))
    assert reads["min_sharpe"] == 5
    assert reads["min_sharpe_typo"] == 7
    assert "min_information_ratio" not in reads

    # the missing-key detector must actually flag the typo
    missing = _missing_threshold_keys(tree, {"min_sharpe", "min_information_ratio"})
    assert len(missing) == 1
    assert "min_sharpe_typo" in missing[0]

    non_evaluating = {name for name, _ in _non_evaluating_gates(tree)}
    assert non_evaluating == {"constant_gate", "placeholder_gate"}

    # the hard-coded-threshold detector must find the spelled-out threshold
    assert _hard_coded_thresholds(tree) == {"sharpe": 1.0}


# --------------------------------------------------------------------------- #
# 3. the disclosed gates do not carry a published verdict
# --------------------------------------------------------------------------- #
def _as_bool(value) -> bool:
    """The artifacts record gate booleans as real booleans and (in the older
    families) as the strings "True"/"False"."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value in ("True", "False"):
        return value == "True"
    raise AssertionError(f"not a gate boolean: {value!r}")


def _published_gates(family: str) -> dict[str, bool]:
    artifact_id, key = PUBLISHED_ARTIFACTS[family]
    with open(ARTIFACTS / artifact_id / "summary.json") as f:
        summary = json.load(f)
    recorded = summary.get(key)
    assert recorded, f"{family} artifact carries no {key!r}"
    if key == "gates":
        return {name: _as_bool(value) for name, value in recorded.items()}
    return {
        name: _as_bool(value["passes"]) for name, value in recorded.items()
    }


@pytest.mark.parametrize("family", sorted(PUBLISHED_ARTIFACTS))
def test_forcing_the_disclosed_gates_to_false_changes_no_verdict(family):
    """The disclosed gates can never fail, so they add a free PASS to the
    published tally. Recomputed offline from the committed artifacts (no grid
    is re-run): with the disclosed gates forced to False the family is still
    not an all-pass, so no published verdict rests on them."""
    gates = _published_gates(family)
    published_pass = [name for name, passed in gates.items() if passed]
    assert published_pass, f"{family} has no passing gate to recompute"

    disclosed = {
        name
        for runner, name in DISCLOSED_NON_EVALUATING_GATES
        if runner.startswith(f"run_{family.lower()}_")
    }
    assert disclosed, f"{family} owns no disclosed gate"

    recomputed_pass = [
        name
        for name, passed in gates.items()
        if passed and name not in disclosed
    ]
    assert len(published_pass) > len(recomputed_pass)
    assert recomputed_pass != published_pass
    # the family is not an all-pass as published ...
    assert not all(gates.values())
    # ... and it does not become one without the free PASSes
    assert not all(gates[name] for name in gates if name not in disclosed)


@pytest.mark.parametrize("family", sorted(PUBLISHED_ARTIFACTS))
def test_the_disclosed_gate_families_are_rejected(family):
    """The families that own a disclosed gate must be REJECT in the published
    record."""
    artifact_id, key = PUBLISHED_ARTIFACTS[family]
    with open(ARTIFACTS / artifact_id / "summary.json") as f:
        summary = json.load(f)
    verdict = summary.get("verdict")
    if verdict is None:
        # Not every runner records the verdict in its summary; the all-pass
        # flag is the equivalent, and the gate booleans are checked above.
        return
    assert str(verdict).upper() == "REJECT"


# --------------------------------------------------------------------------- #
# 4. the published H18 artifact
# --------------------------------------------------------------------------- #
# H18 has three committed artifacts. The published row is the one its Measure
# Log names; the two earlier siblings are not the published row.
H18_EARLIER_SIBLINGS = (
    "exp_2026-10-13T22-13-37-475937Z",
    "exp_2026-10-13T22-14-26-107907Z",
)


def test_the_published_h18_artifact_is_the_one_named_in_the_spec():
    """The published H18 row is ``exp_2026-10-13T22-14-50-729923Z`` (named in
    HYPOTHESIS_SPEC.md section H18), with a 2/9 tally. The two earlier
    siblings record a 3/9 tally -- their ``max_drawdown`` gate still read
    True although the OOS drawdown is 22.2% against a 15% limit -- so they
    are not the published row."""
    published_id, _ = PUBLISHED_ARTIFACTS["H18"]
    spec = (ROOT / "HYPOTHESIS_SPEC.md").read_text()
    assert published_id in spec, "the published H18 artifact is not named in the spec"

    gates = _published_gates("H18")
    assert sum(gates.values()) == 2, "the published H18 tally is 2/9"
    assert gates["max_drawdown"] is False, "the published drawdown gate must fail"
    assert gates["perturbation_ratio"] is True, "the disclosed placeholder gate"

    for sibling in H18_EARLIER_SIBLINGS:
        path = ARTIFACTS / sibling / "summary.json"
        if not path.exists():
            continue
        with open(path) as f:
            summary = json.load(f)
        sibling_gates = summary["gate_metrics"]
        sibling_passes = sum(
            1 for value in sibling_gates.values() if _as_bool(value["passes"])
        )
        assert sibling_passes == 3, f"{sibling} is not an earlier H18 sibling"
        assert _as_bool(sibling_gates["max_drawdown"]["passes"]) is True


# --------------------------------------------------------------------------- #
# 5. H18's hard-coded thresholds stay equal to the shared gate set
# --------------------------------------------------------------------------- #
# H18 is the only runner that does not read its thresholds from a shared
# ``GATES`` dict: it spells them out. The values are correct today, but a
# change to the shared set would silently not apply to H18, so the equality is
# pinned here.
H18_GATE_TO_SHARED_KEY = {
    "sharpe": ("min_sharpe", 1.0),
    "trades": ("min_trades", 1.0),
    "profit_factor": ("min_profit_factor", 1.0),
    "max_drawdown": ("max_drawdown", -1.0),
    "walk_forward_stability": ("min_walkforward_stability", 1.0),
    "worst_regime_sharpe": ("min_worst_regime_sharpe", 1.0),
    "benchmark_p": ("max_p_value", 1.0),
    "information_ratio": ("min_information_ratio", 1.0),
    "perturbation_ratio": ("min_perturbed_sharpe_ratio", 1.0),
}


def _numeric_literal(node: ast.expr) -> float | None:
    """The value of a numeric literal, including a negated one."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.USub)
        and isinstance(node.operand, ast.Constant)
        and isinstance(node.operand.value, (int, float))
    ):
        return -float(node.operand.value)
    return None


def _hard_coded_thresholds(tree: ast.AST) -> dict[str, float]:
    """The thresholds a runner spells out inside its gate records."""
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id in GATE_DICT_NAMES for t in node.targets
        ):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                continue
            if not isinstance(value, ast.Dict):
                continue
            for inner_key, inner_value in zip(value.keys, value.values):
                if (
                    isinstance(inner_key, ast.Constant)
                    and inner_key.value == "threshold"
                ):
                    number = _numeric_literal(inner_value)
                    if number is not None:
                        found[key.value] = number
    return found


def test_the_hard_coded_h18_thresholds_match_the_shared_gate_set():
    """H18's thresholds must equal the shared PROMPT_V2 gate set."""
    shared = _gates_keys(ROOT / "run_h9_intraday_tsmom_experiment.py")
    assert shared is not None

    thresholds = _hard_coded_thresholds(
        _parse(ROOT / "run_h18_overnight_intraday_experiment.py")
    )
    assert set(thresholds) == set(H18_GATE_TO_SHARED_KEY)

    shared_values = _gates_values(ROOT / "run_h9_intraday_tsmom_experiment.py")
    for gate, (key, sign) in H18_GATE_TO_SHARED_KEY.items():
        assert thresholds[gate] == pytest.approx(sign * shared_values[key]), (
            f"H18's {gate} threshold {thresholds[gate]} != {sign * shared_values[key]}"
        )
