#!/usr/bin/env python3
"""H28: Causal re-certification of the intraday futures TSMOM family.

Pre-registered in ``HYPOTHESIS_SPEC.md`` §H28 (2026-10-19).  Trigger: H27
returned ``LOOKAHEAD_CONFIRMED`` -- the published construction positions every
session at its own **open** with the signal computed at its own **close**
(``_daily_target_from_hourly`` = ``resample("1D").last()`` expanded back with
``reindex(..., method="ffill")``).

This runner re-runs the *published* H10 / H21 / H22 / H25 pipelines with exactly
one change: the daily collapse is lagged by one calendar day.  The published
runners are **not** edited -- the change is installed by patching the
module-global ``_daily_target_from_hourly`` (the same minimal intervention H27
used) and the experiment identity is swapped for an H28 id.

For every family two runs are performed:

* **control** -- the published (same-day) expansion.  It must reproduce the
  published artifact **bit-exactly**; if it does not, that family's causal run
  is void and is not reported.
* **causal** -- the lagged expansion, gate-evaluated with the *unchanged*
  gates, splits, selection rule and cost model.

No gate, threshold, published verdict or certified number is changed.
"""

import json
import os
import shutil
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import run_h9_intraday_tsmom_experiment as h9
import run_h10_intraday_tsmom_pfopt_experiment as h10
import run_h21_futures_tsmom_multicontract as h21
import run_h22_futures_tsmom_voltarget as h22
import run_h25_futures_tsmom_pfmargin as h25

# The causal collapse is *the same object* the H27 audit used, so the H27
# look-ahead regression test and the H28 counterfactual cannot drift apart.
from run_h27_pnl_level_audit import causal_daily_target_from_hourly

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / ".experiments" / "artifacts"
ART_DIR = ARTIFACTS / "h28_causal_recertification"
RUNS_DIR = ART_DIR / "runs"

HYPOTHESIS = "H28"

# Modules whose module-global ``_daily_target_from_hourly`` must be replaced.
# H10's ``build_hourly_target`` resolves that global at *call* time, so H21 /
# H22 / H25 inherit the causal collapse through H10; their own module-level
# binding is patched as well so that the logged ``daily_target_h10`` artifact
# matches the computation.
COLLAPSE_MODULES = (h9, h10, h21, h22, h25)

# Frozen families (pre-registration §H28).
FAMILY_SPECS = (
    {
        "family": "H10",
        "module": h10,
        "published_artifact": "exp_2026-10-11T17-41-18-169363Z",
        "published_verdict": "PASS",
        "grid_size": 13824,
    },
    {
        "family": "H21",
        "module": h21,
        "published_artifact": "exp_2026-10-13T23-27-52-101656Z",
        "published_verdict": "REJECT",
        "grid_size": 16,
    },
    {
        "family": "H22",
        "module": h22,
        "published_artifact": "exp_2026-10-14T18-52-08-943792Z",
        "published_verdict": "PASS",
        "grid_size": 8,
    },
    {
        "family": "H25",
        "module": h25,
        "published_artifact": "exp_2026-10-14T20-08-34-613690Z",
        "published_verdict": "PASS",
        "grid_size": 8,
    },
)

# The certified family (H10, H22, H25) -- all three must be CAUSAL_CERTIFIED.
CERTIFIED_FAMILY = ("H10", "H22", "H25")

# Artifacts compared bit-exactly by the negative control.  ``grid_results``
# is included: it pins the *selection* (every combo's Val metrics), so a
# control that reproduces it has reproduced the whole grid.
CONTROL_ARTIFACTS = (
    "grid_results",
    "positions",
    "basket_positions",
    "per_contract_positions",
    "returns",
    "equity",
    "trades",
    "hourly_target_selected",
    "daily_target_h9",
    "daily_target_h10",
    "benchmark_equity",
    "benchmark_returns",
    "regime_factors",
)

# Keys of ``summary.json`` that are expected to differ between two runs
# (identity and wall-clock), and are therefore compared field-by-field
# instead of as a whole.
SUMMARY_VOLATILE_KEYS = (
    "experiment_id",
    "grid_elapsed_sec",
    "total_elapsed_sec",
    "compute_cpu_hours",
)

# The only summary field a control run cannot reproduce bit-exactly.
#
# The published artifacts were produced before the 2026-10-19 09:28 library
# change to ``walk_forward_splits`` (the last walk-forward window now absorbs
# the trailing samples; 1 bar in 11,441 before).  The published H25
# ``wf_stability`` is reproduced *bit-exactly* by the pre-change
# implementation, and every other summary field -- including every gate
# boolean and the verdict -- reproduces under both implementations.  The
# drift is therefore documented, mechanical and completely independent of the
# H28 intervention.  The gate that consumes it (``passes.stab``) is NOT
# exempt: a control whose gate outcome differs is not a valid control.
DOCUMENTED_DRIFT_FIELDS = ("metrics.wf_stability",)


# --------------------------------------------------------------------------- #
# installation of the causal collapse
# --------------------------------------------------------------------------- #
@contextmanager
def causal_collapse():
    """Install the causal daily collapse in every runner module.

    ``build_hourly_target`` (H10) and ``apply_path_dependent_exits_hourly`` (H9)
    call the module-global ``_daily_target_from_hourly``; patching the module
    attribute is the *minimal* intervention -- every other stage of the
    pipeline is untouched.  The originals are restored on exit.
    """
    originals = {m: m._daily_target_from_hourly for m in COLLAPSE_MODULES}
    try:
        for m in COLLAPSE_MODULES:
            m._daily_target_from_hourly = causal_daily_target_from_hourly
        yield
    finally:
        for m, fn in originals.items():
            m._daily_target_from_hourly = fn


@contextmanager
def experiment_identity(module, name, desc):
    """Temporarily give a published runner an H28 experiment identity."""
    originals = (module.EXPERIMENT_NAME, module.EXPERIMENT_DESC)
    module.EXPERIMENT_NAME = name
    module.EXPERIMENT_DESC = desc
    try:
        yield
    finally:
        module.EXPERIMENT_NAME, module.EXPERIMENT_DESC = originals


class _TrackerProxy:
    """Proxy around the experiment tracker that captures the new experiment id."""

    def __init__(self, tracker):
        self._tracker = tracker
        self.experiment_id = None

    def start_experiment(self, *args, **kwargs):
        self.experiment_id = self._tracker.start_experiment(*args, **kwargs)
        return self.experiment_id

    def __getattr__(self, name):
        return getattr(self._tracker, name)


@contextmanager
def tracker_capture(module):
    """Capture the experiment id created by ``module.main()``."""
    tracker = module.get_tracker()
    proxy = _TrackerProxy(tracker)
    original = module.get_tracker
    module.get_tracker = lambda: proxy
    try:
        yield proxy
    finally:
        module.get_tracker = original


# --------------------------------------------------------------------------- #
# where a run's artifacts live
# --------------------------------------------------------------------------- #
def run_dir(exp_id: str) -> Path:
    """Locate a run's artifact directory (before or after relocation)."""
    live = ARTIFACTS / exp_id
    if live.exists():
        return live
    return RUNS_DIR / exp_id


def relocate_runs(records: list[dict]) -> dict[str, str]:
    """Move the H28 run artifacts under the H28 audit directory.

    The published family artifacts must stay the only *depth-1* experiment
    directories carrying a ``hypothesis`` label: the repo's artifact-discovery
    helpers (``run_h25_pf_robustness.py::_find_latest_h25_dir`` and the
    ``_latest_hXX_dir`` helpers in the family test files) select the
    lexicographically last matching directory, so an H28 run directory would
    silently take the published run's place.  Grouping the H28 runs under the
    audit directory keeps the published record unambiguous and matches the
    layout H26/H27 use for their outputs.
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for rec in records:
        exp_id = rec.get("experiment_id")
        if not exp_id:
            continue
        src = ARTIFACTS / exp_id
        dst = RUNS_DIR / exp_id
        if src.exists() and not dst.exists():
            shutil.move(str(src), str(dst))
        rec["artifact_path"] = str(dst.relative_to(ROOT))
        paths[exp_id] = rec["artifact_path"]
    return paths


# --------------------------------------------------------------------------- #
# running a family
# --------------------------------------------------------------------------- #
def run_family(spec: dict, mode: str) -> dict:
    """Run one family in ``mode`` ("control" or "causal") and return its record."""
    module = spec["module"]
    name = f"h28_{spec['family'].lower()}_{mode}"
    causal = mode == "causal"
    desc = (
        f"H28 causal re-certification of {spec['family']} ({mode}): identical to "
        f"{spec['family']} except the daily collapse is "
        + (
            "lagged by one calendar day (causal)."
            if causal
            else "the published same-day expansion (negative control)."
        )
    )
    t0 = time.time()
    with tracker_capture(module) as proxy, experiment_identity(module, name, desc):
        if causal:
            with causal_collapse():
                rc = module.main()
        else:
            rc = module.main()
    return {
        "family": spec["family"],
        "mode": mode,
        "experiment_name": name,
        "experiment_id": proxy.experiment_id,
        "return_code": rc,
        "elapsed_sec": float(round(time.time() - t0, 1)),
    }


# --------------------------------------------------------------------------- #
# the negative control
# --------------------------------------------------------------------------- #
def _compare_frames(a: pd.DataFrame, b: pd.DataFrame) -> dict:
    """Bit-exact comparison of two artifact frames (values, index, columns)."""
    out = {
        "shape_match": a.shape == b.shape,
        "columns_match": list(a.columns) == list(b.columns),
        "index_match": a.index.equals(b.index),
        "max_abs_diff": None,
    }
    if not (out["shape_match"] and out["columns_match"] and out["index_match"]):
        return out
    diffs = []
    for col in a.columns:
        x, y = a[col], b[col]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            diffs.append(
                _max_abs_diff(x.to_numpy(dtype=float), y.to_numpy(dtype=float))
            )
        else:
            diffs.append(0.0 if x.equals(y) else np.inf)
    out["max_abs_diff"] = float(np.nanmax(diffs)) if diffs else 0.0
    return out


def _max_abs_diff(x: np.ndarray, y: np.ndarray) -> float:
    """Max absolute difference, NaN-safe (an all-NaN column is a perfect match)."""
    if x.shape != y.shape:
        return np.inf
    same_nan = np.isnan(x) == np.isnan(y)
    if not same_nan.all():
        return np.inf
    finite = ~np.isnan(x)
    if not finite.any():
        return 0.0
    return float(np.max(np.abs(x[finite] - y[finite])))


def compare_to_published(spec: dict, control_exp_id: str) -> dict:
    """Compare a control run against the frozen published artifact."""
    pub_dir = ARTIFACTS / spec["published_artifact"]
    ctl_dir = run_dir(control_exp_id)
    result = {
        "published_artifact": spec["published_artifact"],
        "control_artifact": control_exp_id,
        "artifacts": {},
        "bit_exact": True,
    }
    for name in CONTROL_ARTIFACTS:
        pub_file = pub_dir / f"{name}.parquet"
        ctl_file = ctl_dir / f"{name}.parquet"
        if not pub_file.exists():
            continue
        if not ctl_file.exists():
            result["artifacts"][name] = {"present_in_control": False}
            result["bit_exact"] = False
            continue
        cmp = _compare_frames(pd.read_parquet(pub_file), pd.read_parquet(ctl_file))
        cmp["present_in_control"] = True
        ok = (
            cmp["shape_match"]
            and cmp["columns_match"]
            and cmp["index_match"]
            and cmp["max_abs_diff"] is not None
            and cmp["max_abs_diff"] == 0.0
        )
        cmp["bit_exact"] = bool(ok)
        if not ok:
            result["bit_exact"] = False
        result["artifacts"][name] = cmp

    # summary.json: every field except the identity / wall-clock ones.
    pub_sum_file = pub_dir / "summary.json"
    ctl_sum_file = ctl_dir / "summary.json"
    if pub_sum_file.exists() and ctl_sum_file.exists():
        pub_sum = json.loads(pub_sum_file.read_text())
        ctl_sum = json.loads(ctl_sum_file.read_text())
        pub_flat = _flatten(pub_sum)
        ctl_flat = _flatten(ctl_sum)
        diffs = {}
        for key in sorted(set(pub_flat) | set(ctl_flat)):
            if key in SUMMARY_VOLATILE_KEYS:
                continue
            if pub_flat.get(key) != ctl_flat.get(key):
                diffs[key] = {
                    "published": pub_flat.get(key),
                    "control": ctl_flat.get(key),
                }
        drift = {k: v for k, v in diffs.items() if k in DOCUMENTED_DRIFT_FIELDS}
        unexpected = {
            k: v for k, v in diffs.items() if k not in DOCUMENTED_DRIFT_FIELDS
        }
        result["summary_differences"] = diffs
        result["documented_library_drift"] = drift
        result["unexpected_differences"] = unexpected
        result["summary_bit_exact"] = not diffs
        # the gate booleans and the verdict must be identical
        result["gate_outcomes_match"] = pub_sum.get("passes") == ctl_sum.get("passes")
        result["verdict_match"] = pub_sum.get("verdict") == ctl_sum.get("verdict")
        if (
            unexpected
            or not result["gate_outcomes_match"]
            or not result["verdict_match"]
        ):
            result["bit_exact"] = False
    else:
        result["summary_differences"] = {"_missing": True}
        result["documented_library_drift"] = {}
        result["unexpected_differences"] = {"_missing": True}
        result["summary_bit_exact"] = False
        result["gate_outcomes_match"] = False
        result["verdict_match"] = False
        result["bit_exact"] = False
    return result


def _flatten(obj, prefix: str = "") -> dict:
    """Flatten a nested summary into dotted field paths."""
    out: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    else:
        out[prefix] = obj
    return out


# --------------------------------------------------------------------------- #
# the causal verdict
# --------------------------------------------------------------------------- #
def causal_verdict(spec: dict, causal_exp_id: str, control_ok: bool) -> dict:
    """Evaluate a family's causal run against the *unchanged* published gates."""
    ctl_dir = run_dir(causal_exp_id)
    summary_file = ctl_dir / "summary.json"
    out = {
        "family": spec["family"],
        "causal_artifact": causal_exp_id,
        "control_reproduced": bool(control_ok),
        "published_verdict": spec["published_verdict"],
    }
    if not summary_file.exists():
        out["verdict"] = "CAUSAL_REJECTED"
        out["reason"] = "causal run produced no summary.json"
        return out
    s = json.loads(summary_file.read_text())
    m = s.get("metrics", {})
    out["selected_config"] = s.get("selected_config")
    out["selection_rule"] = s.get("selection_rule")
    out["passes"] = s.get("passes")
    out["all_pass"] = bool(s.get("all_pass"))
    out["published_gate_verdict"] = s.get("verdict")
    out["oos_sharpe"] = m.get("oos_sharpe")
    out["val_sharpe"] = m.get("val_sharpe")
    out["test_sharpe"] = m.get("test_sharpe")
    out["profit_factor"] = m.get("profit_factor")
    out["max_drawdown"] = m.get("max_drawdown")
    out["trades"] = m.get("trades")
    out["wf_stability"] = m.get("wf_stability")
    out["worst_regime_sharpe"] = m.get("worst_regime_sharpe")
    out["benchmark_p_value"] = m.get("benchmark_p_value")
    out["information_ratio"] = m.get("information_ratio")
    if not control_ok:
        out["verdict"] = "CAUSAL_REJECTED"
        out["reason"] = "negative control did not reproduce the published artifact"
        return out
    out["verdict"] = "CAUSAL_CERTIFIED" if out["all_pass"] else "CAUSAL_REJECTED"
    out["reason"] = (
        "all unchanged gates pass on the protected OOS window"
        if out["all_pass"]
        else "at least one unchanged gate fails on the protected OOS window"
    )
    return out


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def build_report(records: list[dict], controls: dict, verdicts: dict) -> dict:
    certified = [
        f
        for f in CERTIFIED_FAMILY
        if verdicts.get(f, {}).get("verdict") == "CAUSAL_CERTIFIED"
    ]
    return {
        "hypothesis": HYPOTHESIS,
        "pre_registered": "2026-10-19",
        "certified_family": list(CERTIFIED_FAMILY),
        "causal_certified_members": certified,
        "family_verdict": (
            "CAUSAL_CERTIFIED"
            if len(certified) == len(CERTIFIED_FAMILY)
            else "CAUSAL_REJECTED"
        ),
        "verdict_rule": (
            "per family: CAUSAL_CERTIFIED iff the negative control reproduced the "
            "published artifact bit-exactly AND the causal run passes every "
            "unchanged gate on the protected OOS window; family: CAUSAL_CERTIFIED "
            "iff all three certified members are CAUSAL_CERTIFIED"
        ),
        "gates_unchanged": True,
        "splits_unchanged": True,
        "selection_rule_unchanged": True,
        "cost_model_unchanged": True,
        "published_artifacts_rewritten": False,
        "published_runners_edited": False,
        "runs": records,
        "controls": controls,
        "verdicts": verdicts,
    }


def main() -> int:
    t0 = time.time()
    ART_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    controls: dict = {}
    verdicts: dict = {}

    for spec in FAMILY_SPECS:
        print("=" * 100)
        print(f"[H28] {spec['family']}  control (published expansion) ...")
        ctl = run_family(spec, "control")
        records.append(ctl)
        if ctl["experiment_id"] is None:
            controls[spec["family"]] = {"bit_exact": False, "error": "no experiment id"}
            verdicts[spec["family"]] = {
                "family": spec["family"],
                "verdict": "CAUSAL_REJECTED",
                "reason": "control run failed",
                "control_reproduced": False,
            }
            continue
        cmp = compare_to_published(spec, ctl["experiment_id"])
        controls[spec["family"]] = cmp
        print(
            f"[H28] {spec['family']} control bit-exact vs published: {cmp['bit_exact']}"
        )

        print("=" * 100)
        print(f"[H28] {spec['family']}  causal (lagged daily collapse) ...")
        cau = run_family(spec, "causal")
        records.append(cau)
        if cau["experiment_id"] is None:
            verdicts[spec["family"]] = {
                "family": spec["family"],
                "verdict": "CAUSAL_REJECTED",
                "reason": "causal run failed",
                "control_reproduced": bool(cmp.get("bit_exact")),
            }
            continue
        verdicts[spec["family"]] = causal_verdict(
            spec, cau["experiment_id"], bool(cmp.get("bit_exact"))
        )
        v = verdicts[spec["family"]]
        print(
            f"[H28] {spec['family']} causal verdict: {v['verdict']} "
            f"(OOS Sharpe {v.get('oos_sharpe')}, PF {v.get('profit_factor')}, "
            f"DD {v.get('max_drawdown')})"
        )

    report = build_report(records, controls, verdicts)
    report["run_artifact_paths"] = relocate_runs(records)
    report["elapsed_sec"] = float(round(time.time() - t0, 2))
    with open(ART_DIR / "summary.json", "w") as f:
        json.dump(report, f, indent=2, default=lambda x: str(x))

    rows = []
    for fam, v in verdicts.items():
        rows.append(
            {
                "family": fam,
                "published_verdict": v.get("published_verdict"),
                "causal_verdict": v.get("verdict"),
                "control_bit_exact": controls.get(fam, {}).get("bit_exact"),
                "causal_artifact": v.get("causal_artifact"),
                "oos_sharpe": v.get("oos_sharpe"),
                "val_sharpe": v.get("val_sharpe"),
                "test_sharpe": v.get("test_sharpe"),
                "profit_factor": v.get("profit_factor"),
                "max_drawdown": v.get("max_drawdown"),
                "trades": v.get("trades"),
                "wf_stability": v.get("wf_stability"),
                "worst_regime_sharpe": v.get("worst_regime_sharpe"),
                "n_gates_passed": (
                    int(sum(bool(x) for x in v["passes"].values()))
                    if v.get("passes")
                    else None
                ),
            }
        )
    pd.DataFrame(rows).to_parquet(ART_DIR / "recertification_table.parquet")

    print("=" * 100)
    print("[H28] causal re-certification (pre-registered)")
    print(
        f"  {'fam':<6}{'published':>11}{'control':>9}{'causal':>16}"
        f"{'OOS SR':>10}{'PF':>8}{'DD':>9}{'gates':>7}"
    )
    for r in rows:
        gates = f"{r['n_gates_passed']}" if r["n_gates_passed"] is not None else "-"
        print(
            f"  {r['family']:<6}{r['published_verdict']:>11}"
            f"{r['control_bit_exact']!s:>9}{r['causal_verdict']:>16}"
            f"{(r['oos_sharpe'] if r['oos_sharpe'] is not None else float('nan')):>10.4f}"
            f"{(r['profit_factor'] if r['profit_factor'] is not None else float('nan')):>8.3f}"
            f"{(r['max_drawdown'] if r['max_drawdown'] is not None else float('nan')):>9.4f}"
            f"{gates:>8}"
        )
    print(f"  certified family verdict: {report['family_verdict']}")
    print(f"  wrote {ART_DIR}  ({report['elapsed_sec']}s)")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
