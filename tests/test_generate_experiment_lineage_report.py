import json
from pathlib import Path

import pytest

from scripts import generate_experiment_lineage_report as g


def _write_jsonl(path: Path, records):
    with path.open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def test_load_experiments_basic(tmp_path):
    p = tmp_path / "exp.jsonl"
    _write_jsonl(p, [{"a": 1}, {"b": 2}])
    assert g.load_experiments(p) == [{"a": 1}, {"b": 2}]


def test_load_experiments_skips_blank_and_bad(tmp_path):
    p = tmp_path / "exp.jsonl"
    p.write_text('{"x":1}\n\nnot json\n{"y":2}\n')
    out = g.load_experiments(p)
    assert out == [{"x": 1}, {"y": 2}]


def test_extract_key_info_metadata_nested():
    exp = {
        "metadata": {
            "experiment_id": "E1",
            "name": "foo",
            "description": "d",
            "timestamp": "t",
            "git_commit": "abcdef1234",
            "config": {"k": "v"},
        },
        "metrics": {"m": 1.0},
        "status": {"verdict": True, "gates": {"g": True}},
        "artifacts": {"a": "p"},
    }
    info = g.extract_key_info(exp)
    assert info["exp_id"] == "E1"
    assert info["name"] == "foo"
    assert info["git_commit"] == "abcdef12"
    assert info["config"] == {"data_source": "unknown"}
    assert info["verdict"] == "PASS"


def test_extract_key_info_top_level_fallback():
    exp = {"config": {"k": "v"}, "status": False}
    info = g.extract_key_info(exp)
    assert info["config"] == {"data_source": "unknown"}
    assert info["verdict"] == "False"


def test_format_metrics_empty():
    assert g.format_metrics({}) == "—"


def test_categorize_experiment_returns_str():
    info = {"name": "foo", "description": "", "config": {}}
    assert isinstance(g.categorize_experiment(info), str)


def test_generate_report_writes_file(tmp_path):
    out = tmp_path / "report.md"
    g.generate_report([], out)
    assert out.exists() and out.stat().st_size >= 0


def test_main_runs(tmp_path, monkeypatch):
    jsonl = tmp_path / "experiments.jsonl"
    _write_jsonl(jsonl, [])
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".experiments").mkdir()
    (tmp_path / ".experiments" / "experiments.jsonl").write_text("")
    g.main()
    assert (tmp_path / "EXPERIMENT_LINEAGE_REPORT.md").exists()
