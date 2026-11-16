from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

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


def test_record_artifact_parquet_deduplicates_columns_before_writing(tmp_path):
    """A duplicated column label must not crash parquet artifact writing.

    ``Experiment.record_artifact`` is the sibling DataFrame-write path to
    ``ExperimentTracker.log_dataframe``. Real panels can carry a repeated
    label (repeated ticker, overlapping concat, cached/vendor frame) and
    parquet refuses it; canonicalize once (keep first) so a clean/unique
    frame is bit-identical and a duplicated-label frame degrades instead of
    crashing at the artifact boundary.
    """
    exp = experiment.Experiment("a1d", base_dir=tmp_path)
    df = pd.DataFrame([[1.0, 999.0, 2.0], [3.0, 4.0, 5.0]], columns=["A", "A", "B"])
    path = exp.record_artifact("dup.parquet", df)
    written = pd.read_parquet(path)
    assert list(written.columns) == ["A", "B"]
    assert written["A"].tolist() == [1.0, 3.0]


def test_record_artifact_csv_deduplicates_columns_before_writing(tmp_path):
    """CSV writing must canonicalize duplicated labels instead of mangling.

    Without the keep-first guard pandas auto-renames duplicates on readback
    (``A``, ``A.1``), silently changing the recorded schema. Canonicalize so
    the artifact preserves the intended first column.
    """
    exp = experiment.Experiment("a1dc", base_dir=tmp_path)
    df = pd.DataFrame([[1.0, 999.0, 2.0], [3.0, 4.0, 5.0]], columns=["A", "A", "B"])
    path = exp.record_artifact("dup.csv", df)
    written = pd.read_csv(path)
    assert list(written.columns) == ["A", "B"]
    assert written["A"].tolist() == [1.0, 3.0]


def test_record_artifact_dataframe_unique_columns_untouched(tmp_path):
    """The dedup guard is a no-op on a clean frame: bit-identical write."""
    exp = experiment.Experiment("a1u", base_dir=tmp_path)
    df = pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0]})
    path = exp.record_artifact("clean.parquet", df)
    written = pd.read_parquet(path)
    pd.testing.assert_frame_equal(written, df)


def test_record_artifact_pre_fix_duplicate_parquet_crash(tmp_path):
    """Behavioural negative control: bare parquet write rejects duplicates."""
    df = pd.DataFrame([[1.0, 999.0, 2.0]], columns=["A", "A", "B"])
    with pytest.raises(ValueError, match="Duplicate column names"):
        df.to_parquet(tmp_path / "raw.parquet")


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


def test_log_metadata_serializes_non_json_values(tmp_path):
    """A non-JSON-serializable value (numpy array) must not crash the writer.

    ``json.dump`` raises ``TypeError: Object of type ndarray is not JSON
    serializable`` on the first such value, so a caller logging a numpy array
    -- the natural shape for a parameter grid, a metric vector, or a result
    array -- loses the whole experiment record and the metadata file it was
    mid-write. The writer falls back to ``default=str`` (the same policy the
    JSONL tracker uses in ``_save_experiment``), so the value is persisted as
    its string representation rather than aborting the write.
    """
    import numpy as np

    exp = experiment.Experiment("s1", base_dir=tmp_path)
    exp.log_metadata(grid=np.array([0.1, 0.5, 1.0]), name="grid")
    exp.log_params({"alpha": np.array([1.0, 2.0])})
    exp.log_results({"series": np.array([1.0, 2.0, 3.0])})

    data = json.loads(exp.metadata_path.read_text())
    assert data["name"] == "grid"
    assert data["grid"] == str(np.array([0.1, 0.5, 1.0]))
    assert data["params"]["alpha"] == str(np.array([1.0, 2.0]))
    assert data["results"]["series"] == str(np.array([1.0, 2.0, 3.0]))


def test_log_metadata_pre_fix_form_crashes_on_non_json_value(tmp_path):
    """Behavioural negative control: the bare ``json.dump`` form raises.

    Reconstructs the pre-fix writer over a numpy-array value and requires it
    to raise ``TypeError``, proving the corrected writer is what makes the
    path safe rather than merely lucky.
    """
    import numpy as np

    meta = {"grid": np.array([0.1, 0.5, 1.0])}
    with pytest.raises(TypeError):
        json.dumps(meta)
