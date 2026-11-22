"""Tests for ``scripts/analyze_equity_cross_section_rejects.py``.

The script is a read-only root-cause diagnostic over the committed
``summary.json`` artifacts.  The synthetic fixtures below exercise the parsing
and aggregation logic independently of the real corpus, and one integration
test runs it against this repository so the diagnostic stays honest as
artifacts are added.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_equity_cross_section_rejects.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("analyze_equity_cross_section_rejects", SCRIPT)
    assert spec is not None and spec.loader is not None, f"cannot load {SCRIPT}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary(
    *,
    name: str = "nf_test",
    universe_symbols: list[str] | None = None,
    strategy_sharpe: float = 0.5,
    benchmark_sharpe: float = 1.0,
    train_sharpe: float = 0.8,
    val_sharpe: float = 0.3,
    test_sharpe: float = 0.2,
    full_sample_sharpe: float = 0.5,
    beta: float = 0.0,
    information_ratio: float = -0.5,
    alpha: float = -0.02,
    verdict: str = "REJECT",
) -> dict:
    """Build a minimal but schema-faithful summary document."""
    data: dict = {"equity_source": "yfinance"}
    if universe_symbols is not None:
        data["universe_symbols"] = universe_symbols
    return {
        "experiment": name,
        "nf_id": name,
        "data": data,
        "wf_train_sharpe": train_sharpe,
        "val": {"sharpe": val_sharpe},
        "test": {"sharpe": test_sharpe},
        "full_sample": {"sharpe": full_sample_sharpe},
        "oos_val_test": {"sharpe": strategy_sharpe},
        "benchmark_passive_equal_weight_long_oos": {"sharpe": benchmark_sharpe},
        "benchmark_comparison": {
            "beta": beta,
            "information_ratio": information_ratio,
            "alpha_annualized": alpha,
        },
        "verdict": verdict,
        "gates_passed": 2,
        "gates_total": 8,
    }


def _write_summary(root: Path, name: str, summary: dict) -> Path:
    run_dir = root / ".experiments" / "nf_runs" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "summary.json"
    path.write_text(json.dumps(summary))
    return path


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #


def test_is_equity_cross_section_requires_universe_symbols():
    module = _load_script()
    assert module.is_equity_cross_section({"universe_symbols": ["AAPL", "MSFT"]})
    assert not module.is_equity_cross_section({"universe": ["CL", "GC"]})
    assert not module.is_equity_cross_section({})
    assert not module.is_equity_cross_section(None)
    assert not module.is_equity_cross_section(["not", "a", "dict"])


def test_exposure_class_bands_and_boundaries():
    module = _load_script()
    assert module.exposure_class(0.8) == "long_biased"
    assert module.exposure_class(0.5) == "long_biased"  # boundary is inclusive
    assert module.exposure_class(0.0) == "market_neutral"
    assert module.exposure_class(-0.5) == "short_biased"  # boundary is inclusive
    assert module.exposure_class(-0.9) == "short_biased"
    assert module.exposure_class(None) == "unknown"


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def test_load_record_normalises_equity_summary(tmp_path):
    module = _load_script()
    path = _write_summary(tmp_path, "nf_test", _summary(universe_symbols=["AAPL"]))

    record = module.load_record(path)

    assert record is not None
    assert record["run"] == "nf_test"
    assert record["strategy_sharpe"] == 0.5
    assert record["benchmark_sharpe"] == 1.0
    assert record["train_sharpe"] == 0.8
    assert record["val_sharpe"] == 0.3
    assert record["test_sharpe"] == 0.2
    assert record["full_sample_sharpe"] == 0.5
    assert record["beta"] == 0.0
    assert record["information_ratio"] == -0.5
    assert record["alpha_annualized"] == -0.02
    assert record["gates_total"] == 8


def test_load_record_skips_non_equity_and_malformed(tmp_path):
    module = _load_script()
    commodity = _write_summary(tmp_path, "nf_commodity", _summary(universe_symbols=None))
    # give the commodity run a generic ``universe`` key instead of a symbol list
    commodity_summary = json.loads(commodity.read_text())
    commodity_summary["data"] = {"universe": "FUTURES"}
    commodity.write_text(json.dumps(commodity_summary))

    broken = tmp_path / ".experiments" / "nf_runs" / "nf_broken"
    broken.mkdir(parents=True)
    (broken / "summary.json").write_text("{not valid json")

    assert module.load_record(commodity) is None
    assert module.load_record(broken / "summary.json") is None
    assert module.load_record(tmp_path / "does_not_exist.json") is None


def test_load_record_tolerates_missing_comparison_fields(tmp_path):
    module = _load_script()
    summary = _summary(universe_symbols=["AAPL"])
    summary["benchmark_comparison"] = {}
    path = _write_summary(tmp_path, "nf_test", summary)

    record = module.load_record(path)

    assert record is not None
    assert record["beta"] is None
    assert record["information_ratio"] is None


def test_load_record_tolerates_missing_train_val_test_blocks(tmp_path):
    module = _load_script()
    summary = _summary(universe_symbols=["AAPL"])
    summary.pop("wf_train_sharpe", None)
    summary.pop("val", None)
    summary.pop("test", None)
    summary.pop("full_sample", None)
    path = _write_summary(tmp_path, "nf_test", summary)

    record = module.load_record(path)

    assert record is not None
    assert record["train_sharpe"] is None
    assert record["val_sharpe"] is None
    assert record["test_sharpe"] is None
    assert record["full_sample_sharpe"] is None
    # the OOS path still loads from oos_val_test
    assert record["strategy_sharpe"] == 0.5


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


def _record(
    beta: float,
    strategy: float,
    benchmark: float,
    alpha: float,
    ir: float,
    train: float = 0.8,
    val: float = 0.3,
    test: float = 0.2,
    full_sample: float = 0.5,
) -> dict:
    module = _load_script()
    record = {
        "run": "r",
        "strategy_sharpe": strategy,
        "benchmark_sharpe": benchmark,
        "train_sharpe": train,
        "val_sharpe": val,
        "test_sharpe": test,
        "full_sample_sharpe": full_sample,
        "beta": beta,
        "information_ratio": ir,
        "alpha_annualized": alpha,
        "verdict": "REJECT",
        "gates_passed": 1,
        "gates_total": 8,
    }
    record["beta_class"] = module.exposure_class(beta)
    return record


def test_summarize_flags_uniform_long_bias_artifact():
    module = _load_script()
    records = [
        _record(0.8, 0.3, 1.1, -0.05, -0.9),
        _record(0.9, 0.4, 1.0, -0.03, -0.7),
        _record(0.7, 0.2, 1.2, -0.06, -1.1),
    ]

    summary = module.summarize(records)

    assert summary["uniform_long_bias_artifact"] is True
    assert summary["benchmark_dominates"] is True
    assert "artifact" in summary["conclusion"]
    assert summary["n_long_biased"] == 3
    assert summary["n_strategy_beats_benchmark"] == 0


def test_summarize_span_spectrum_is_not_artifact_and_notes_weak_alpha():
    module = _load_script()
    records = [
        _record(0.8, 0.3, 1.1, -0.05, -0.9),
        _record(0.0, 0.2, 1.0, -0.02, -0.8),
        _record(-0.6, 0.1, 1.2, -0.04, -1.2),
    ]

    summary = module.summarize(records)

    assert summary["uniform_long_bias_artifact"] is False
    assert summary["benchmark_dominates"] is True
    assert summary["n_market_neutral"] == 1
    assert summary["n_short_biased"] == 1
    assert summary["genuine_negative_alpha"] is True
    assert "not a uniform long-bias artifact" in summary["conclusion"]
    assert "genuine mechanism weakness" in summary["conclusion"]


def test_summarize_reports_train_val_test_path_and_decay():
    module = _load_script()
    # run A decays (train 1.0 -> OOS 0.2), run B holds (train 0.4 -> OOS 0.5)
    records = [
        _record(0.0, 0.2, 1.0, -0.02, -0.8, train=1.0, val=0.6, test=0.3, full_sample=0.9),
        _record(0.0, 0.5, 1.0, 0.01, 0.4, train=0.4, val=0.45, test=0.5, full_sample=0.45),
        _record(0.0, 0.1, 1.0, -0.01, -0.6, train=None, val=0.2, test=0.1, full_sample=None),
    ]

    summary = module.summarize(records)

    assert summary["train_sharpe_median"] == 0.7  # median of [1.0, 0.4]
    assert summary["val_sharpe_median"] == 0.45  # median of [0.6, 0.45, 0.2]
    assert summary["test_sharpe_median"] == 0.3  # median of [0.3, 0.5, 0.1]
    assert summary["full_sample_sharpe_median"] == 0.675  # median of [0.9, 0.45]
    # decay measured only where both train and OOS present: runs A and B
    assert summary["n_train_measured"] == 2
    assert summary["n_train_to_oos_decay"] == 1  # only run A decays (0.2 < 1.0)
    assert abs(summary["train_to_oos_decay_median"] - (-0.35)) < 1e-9  # median of [-0.8, +0.1]


def test_summarize_empty_is_explicit():
    module = _load_script()
    summary = module.summarize([])

    assert summary["n_runs"] == 0
    assert summary["conclusion"] == "no equity cross-section artifacts found"


def test_summarize_benchmark_dominance_requires_majority_loss():
    module = _load_script()
    # Two of three runs beat the passive book -> benchmark does NOT dominate.
    records = [
        _record(0.0, 1.2, 1.0, 0.05, 0.4),
        _record(0.0, 1.1, 1.0, 0.03, 0.3),
        _record(0.0, 0.5, 1.0, -0.02, -0.4),
    ]

    summary = module.summarize(records)

    assert summary["n_strategy_beats_benchmark"] == 2
    assert summary["benchmark_dominates"] is False


# --------------------------------------------------------------------------- #
# Collection and CLI
# --------------------------------------------------------------------------- #


def test_collect_records_filters_to_equity_cross_sections(tmp_path):
    module = _load_script()
    _write_summary(tmp_path, "nf_equity_a", _summary(name="nf_equity_a", universe_symbols=["AAPL"]))
    _write_summary(tmp_path, "nf_equity_b", _summary(name="nf_equity_b", universe_symbols=["MSFT"]))
    _write_summary(tmp_path, "nf_commodity", _summary(universe_symbols=None))
    (tmp_path / ".experiments" / "nf_runs" / "nf_commodity" / "summary.json").write_text(
        json.dumps({**_summary(universe_symbols=None), "data": {"universe": "FUTURES"}})
    )

    records = module.collect_records(tmp_path)

    names = sorted(r["run"] for r in records)
    assert names == ["nf_equity_a", "nf_equity_b"]
    assert all("beta_class" in r for r in records)


def test_collect_records_missing_directory_is_empty(tmp_path):
    module = _load_script()
    assert module.collect_records(tmp_path) == []


def test_main_reports_summary_on_real_repository(capsys):
    module = _load_script()

    exit_code = module.main(["--repo-root", str(ROOT)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "conclusion:" in out
    assert "passive" in out


def test_main_json_emits_summary_and_runs(capsys):
    module = _load_script()

    exit_code = module.main(["--repo-root", str(ROOT), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["summary"]["n_runs"] >= 1
    assert len(payload["runs"]) == payload["summary"]["n_runs"]


def test_main_on_empty_repository_reports_and_fails(tmp_path, capsys):
    module = _load_script()

    exit_code = module.main(["--repo-root", str(tmp_path)])

    assert exit_code == 1
    assert "no equity cross-section artifacts found" in capsys.readouterr().out


def test_main_tolerates_partial_records_without_numeric_fields(tmp_path, capsys):
    # An equity cross-section artifact can be present yet lack the numeric
    # blocks (oos_val_test / benchmark / comparison).  The text table must
    # degrade to ``n/a`` rather than raising ``TypeError`` on a ``None`` median.
    module = _load_script()
    summary = _summary(universe_symbols=["AAPL"])
    for key in (
        "oos_val_test",
        "benchmark_passive_equal_weight_long_oos",
        "benchmark_comparison",
        "wf_train_sharpe",
        "val",
        "test",
        "full_sample",
    ):
        summary.pop(key, None)
    _write_summary(tmp_path, "nf_partial", summary)

    exit_code = module.main(["--repo-root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "median OOS Sharpe: strategy n/a vs passive book n/a" in out
    assert "beta range: [n/a, n/a]" in out
    assert "inconclusive" in out


def test_main_tolerates_missing_beta_range(tmp_path, capsys):
    # Numeric Sharpe but no benchmark beta: the beta-range line must print n/a
    # instead of crashing on ``summary["beta_min"]:.3f`` when it is ``None``.
    module = _load_script()
    summary = _summary(universe_symbols=["AAPL"], beta=None)
    _write_summary(tmp_path, "nf_nobeta", summary)

    exit_code = module.main(["--repo-root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "median OOS Sharpe: strategy 0.500 vs passive book 1.000" in out
    assert "beta range: [n/a, n/a]" in out


def test_format_table_contains_header_and_runs():
    module = _load_script()
    records = [_record(0.4, 0.3, 1.0, -0.02, -0.6)]
    records[0]["run"] = "nf_example"

    table = module.format_table(records)

    assert "oosSh" in table
    assert "nf_example" in table
    assert "market_neutral" in table
    assert "train" in table
    assert "val" in table
    assert "test" in table
    assert " 0.800 " in table  # default train_sharpe
