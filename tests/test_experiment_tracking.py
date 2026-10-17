from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from qtr.tracking import experiment


def test_experiment_init_and_attributes(tmp_path):
    exp = experiment.Experiment("test_exp", base_dir=tmp_path)
    assert exp.name == "test_exp"
    assert exp.base_dir == tmp_path
    assert exp.artifact_dir.exists()
    assert exp.metadata_dir.exists()
    assert exp.metadata_path.exists()


def test_experiment_init_with_default_base_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exp = experiment.Experiment("default")
    assert exp.base_dir == Path.cwd() / "experiments"


def test_record_artifact_csv(tmp_path):
    exp = experiment.Experiment("a1", base_dir=tmp_path)
    df = pd.DataFrame({"x": [1, 2, 3]})
    path = exp.record_artifact("data.csv", df)
    assert path.exists()
    assert path.name == "data.csv"


def test_record_artifact_json(tmp_path):
    exp = experiment.Experiment("a2", base_dir=tmp_path)
    meta = {"k": 1}
    path = exp.record_artifact("meta.json", meta)
    assert path.exists()
    content = json.loads(path.read_text())
    assert content == {"k": 1}


def test_record_artifact_str(tmp_path):
    exp = experiment.Experiment("a3", base_dir=tmp_path)
    path = exp.record_artifact("log.txt", "hello")
    assert path.read_text() == "hello"


def test_record_artifact_bytes(tmp_path):
    exp = experiment.Experiment("a4", base_dir=tmp_path)
    path = exp.record_artifact("bin.dat", b"abc")
    assert path.read_bytes() == b"abc"


def test_record_artifact_other(tmp_path):
    exp = experiment.Experiment("a5", base_dir=tmp_path)
    path = exp.record_artifact("obj.json", [1, 2])
    assert json.loads(path.read_text()) == [1, 2]


def test_log_metadata(tmp_path):
    exp = experiment.Experiment("m1", base_dir=tmp_path)
    exp.log_metadata(key="value", num=5)
    data = json.loads(exp.metadata_path.read_text())
    assert "key" in data
    assert data["num"] == 5


def test_log_params(tmp_path):
    exp = experiment.Experiment("p1", base_dir=tmp_path)
    params = {"alpha": 0.1}
    exp.log_params(params)
    data = json.loads(exp.metadata_path.read_text())
    assert data["params"] == params


def test_log_results(tmp_path):
    exp = experiment.Experiment("r1", base_dir=tmp_path)
    results = {"sr": 1.0}
    exp.log_results(results)
    data = json.loads(exp.metadata_path.read_text())
    assert data["results"] == results


def test_load_metadata(tmp_path):
    exp = experiment.Experiment("l1", base_dir=tmp_path)
    exp.log_metadata(a=1)
    loaded = exp.load_metadata()
    assert loaded["a"] == 1


def test_context_manager(tmp_path):
    with experiment.Experiment("ctx", base_dir=tmp_path) as exp:
        exp.log_metadata(in_ctx=True)
    assert exp.metadata_path.exists()


def test_create_experiment(tmp_path):
    exp = experiment.create_experiment("c1", base_dir=tmp_path)
    assert isinstance(exp, experiment.Experiment)
