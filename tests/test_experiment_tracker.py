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
