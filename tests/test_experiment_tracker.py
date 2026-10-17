import pandas as pd
import pytest

from qtr.tracking.experiment import ExperimentTracker, get_tracker


def test_tracker_start_and_finish(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    eid = t.start_experiment("exp", description="d", config={"a": 1})
    assert eid.startswith("exp_")
    assert t.current_experiment is not None
    r = t.finish_experiment()
    assert r.status == "completed"
    assert t.current_experiment is None
    assert (tmp_path / "logs" / "experiments.jsonl").exists()


def test_log_metric_requires_experiment(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    with pytest.raises(RuntimeError):
        t.log_metric("m", 1.0)


def test_log_metric_and_metrics(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    t.start_experiment("exp")
    t.log_metric("m", 1.0)
    t.log_metrics({"a": 2.0, "b": 3.0}, step=1)
    r = t.finish_experiment()
    assert "m" in r.metrics
    assert "a_step1" in r.metrics


def test_log_artifact_missing(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    t.start_experiment("exp")
    with pytest.raises(FileNotFoundError):
        t.log_artifact("a", tmp_path / "nope.txt")
    t.finish_experiment(status="failed")


def test_log_artifact(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    t.start_experiment("exp")
    p = tmp_path / "f.txt"
    p.write_text("hi")
    h = t.log_artifact("a", p, metadata={"x": 1})
    assert isinstance(h, str)
    r = t.finish_experiment()
    assert any("a_" in k for k in r.artifacts)


def test_log_dataframe(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    t.start_experiment("exp")
    df = pd.DataFrame({"x": [1, 2]})
    h = t.log_dataframe("df", df)
    assert isinstance(h, str)
    t.finish_experiment()


def test_finish_without_experiment(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    with pytest.raises(RuntimeError):
        t.finish_experiment()


def test_load_experiment(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    eid = t.start_experiment("exp")
    t.log_metric("m", 5.0)
    t.finish_experiment()
    loaded = t.load_experiment(eid)
    assert loaded is not None
    assert loaded.metrics["m"] == 5.0


def test_load_missing(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    assert t.load_experiment("nope") is None


def test_list_experiments(tmp_path):
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    t.start_experiment("exp")
    t.finish_experiment()
    assert len(t.list_experiments()) == 1


def test_get_tracker_singleton():
    a = get_tracker()
    b = get_tracker()
    assert a is b


def test_experiment_context_and_artifacts(tmp_path):
    from qtr.tracking.experiment import Experiment, create_experiment

    exp = Experiment("testexp", base_dir=tmp_path)
    exp.record_artifact("data.csv", pd.DataFrame({"a": [1, 2]}))
    exp.record_artifact("data.parquet", pd.DataFrame({"a": [1, 2]}))
    exp.record_artifact("meta.json", {"k": "v"})
    exp.record_artifact("text.txt", "hello")
    exp.record_artifact("bin.bin", b"bytes")
    exp.record_artifact("other.obj", {"nested": 1})  # dict again
    exp.log_metadata(key="value")
    exp.log_params({"p": 1})
    exp.log_results({"r": 0.5})
    meta = exp.load_metadata()
    assert meta["key"] == "value"
    assert meta["params"]["p"] == 1
    assert meta["results"]["r"] == 0.5

    with create_experiment("ctx", base_dir=tmp_path) as ex:
        assert ex is not None


def test_experiment_load_metadata_corrupt(tmp_path):
    from qtr.tracking.experiment import Experiment

    exp = Experiment("bad", base_dir=tmp_path)
    exp.metadata_path.write_text("not valid json")
    assert exp.load_metadata() == {}


def test_log_artifact_no_experiment(tmp_path):
    import pytest

    from qtr.tracking.experiment import ExperimentTracker

    t = ExperimentTracker(log_dir=tmp_path / "logs")
    p = tmp_path / "x.txt"
    p.write_text("hi")
    with pytest.raises(RuntimeError):
        t.log_artifact("a", p)


def test_load_experiment_no_match(tmp_path):
    # line 267: load_experiment returns None when the log exists but has no matching ID
    from qtr.tracking.experiment import ExperimentTracker

    t = ExperimentTracker(log_dir=tmp_path / "logs")
    eid = t.start_experiment("exp")
    t.finish_experiment()
    assert t.load_experiment(eid) is not None
    assert t.load_experiment("does_not_exist") is None


def test_list_experiments_no_logfile(tmp_path):
    # line 273: list_experiments returns [] when the JSONL log does not exist
    from qtr.tracking.experiment import ExperimentTracker

    t = ExperimentTracker(log_dir=tmp_path / "logs")
    assert t.list_experiments() == []


def test_record_artifact_fallback_unknown_type(tmp_path):
    # lines 335-337: record_artifact falls back to JSON-serializing unknown types
    from qtr.tracking.experiment import Experiment

    exp = Experiment("fallback", base_dir=tmp_path)
    p = exp.record_artifact("num", 42)
    assert p.exists()
    assert p.read_text() == "42"


def test_tracker_git_and_deps_exception(tmp_path, monkeypatch):
    # Simulate git failure
    import subprocess

    from qtr.tracking.experiment import ExperimentTracker

    orig = subprocess.call

    def bad_call(*args, **kwargs):
        raise RuntimeError("git fail")

    monkeypatch.setattr(subprocess, "call", bad_call)
    t = ExperimentTracker(log_dir=tmp_path / "logs")
    commit, dirty = t._get_git_info()
    assert commit == "unknown"
    assert dirty is False
    monkeypatch.setattr(subprocess, "call", orig)

    # Simulate importlib.metadata failure
    import sys

    # remove if exists
    if "importlib.metadata" in sys.modules:
        del sys.modules["importlib.metadata"]

    # monkeypatch import
    import builtins

    real_import = builtins.__import__

    def bad_import(name, *args, **kwargs):
        if name == "importlib.metadata":
            raise ImportError("nope")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", bad_import)
    t2 = ExperimentTracker(log_dir=tmp_path / "logs2")
    deps = t2._get_dependencies()
    assert deps == {}
    monkeypatch.setattr(builtins, "__import__", real_import)


def test_load_experiment_missing_error(tmp_path):
    import json

    from qtr.tracking.experiment import ExperimentTracker

    t = ExperimentTracker(log_dir=tmp_path / "logs")
    eid = t.start_experiment("exp")
    t.finish_experiment()
    # Re-read the log file and add a record without error
    log = t.log_dir / "experiments.jsonl"
    # replace last line by one without error
    with open(log) as f:
        lines = f.readlines()
    if lines:
        rec = json.loads(lines[-1])
        rec["error"] = None
        rec["metadata"]["experiment_id"] = eid + "_2"
        lines[-1] = json.dumps(rec) + "\n"
    # also add one where error missing
    rec2 = rec.copy()
    rec2["metadata"]["experiment_id"] = eid + "_3"
    rec2.pop("error", None)
    lines.append(json.dumps(rec2) + "\n")
    with open(log, "w") as f:
        f.writelines(lines)
    loaded = t.load_experiment(eid + "_3")
    assert loaded is not None
    assert loaded.error is None
