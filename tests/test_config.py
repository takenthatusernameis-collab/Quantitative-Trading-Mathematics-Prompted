from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from qtr.utils import config


def _clear_config_state():
    # Reset module globals to ensure isolation
    config._CONFIG = None
    config._CONFIG_PATH = None


def test_load_config_from_explicit_path(tmp_path):
    _clear_config_state()
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"data": {"cache_dir": "/tmp/cache"}}))
    result = config.load_config(cfg_path)
    assert result["data"]["cache_dir"] == "/tmp/cache"
    assert config._CONFIG_PATH == cfg_path
    _clear_config_state()


def test_load_config_returns_cached_when_no_path(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"a": 1}))
    first = config.load_config()
    # Change file; cached should be returned
    cfg_path.write_text(yaml.dump({"a": 2}))
    second = config.load_config()
    assert first is second
    assert second["a"] == 1
    _clear_config_state()


def test_load_config_searches_standard_locations_and_finds(tmp_path, monkeypatch):
    _clear_config_state()
    # Put config in cwd
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"found": True}))
    result = config.load_config()
    assert result["found"] is True
    _clear_config_state()


def test_load_config_searches_yml_extension(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(yaml.dump({"yml": True}))
    result = config.load_config()
    assert result["yml"] is True
    _clear_config_state()


def test_load_config_returns_empty_when_no_file_found(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    # ensure no config files
    result = config.load_config()
    assert result == {}
    _clear_config_state()


def test_get_config_loads_if_none(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"x": 5}))
    result = config.get_config()
    assert result["x"] == 5
    _clear_config_state()


def test_get_config_returns_cached_if_exists():
    _clear_config_state()
    config._CONFIG = {"cached": True}
    result = config.get_config()
    assert result == {"cached": True}
    _clear_config_state()


def test_env_overrides_int(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QTR_MAX_CPU_HOURS", "10")
    result = config.load_config()
    assert result["compute"]["max_cpu_hours"] == 10
    _clear_config_state()


def test_env_overrides_float(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QTR_MAX_CPU_HOURS", "10.5")
    result = config.load_config()
    assert result["compute"]["max_cpu_hours"] == 10.5
    _clear_config_state()


def test_env_overrides_nonfinite_float_stays_string(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QTR_MAX_CPU_HOURS", "nan")
    result = config.load_config()
    assert result["compute"]["max_cpu_hours"] == "nan"
    _clear_config_state()


def test_env_overrides_non_bool_string_stays_string(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QTR_LOG_LEVEL", "DEBUG")
    result = config.load_config()
    assert result["logging"]["level"] == "DEBUG"
    assert isinstance(result["logging"]["level"], str)
    _clear_config_state()


def test_env_overrides_non_finite_stays_string(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QTR_MAX_CPU_HOURS", "nan")
    result = config.load_config()
    assert result["compute"]["max_cpu_hours"] == "nan"
    _clear_config_state()


def test_env_overrides_bool_parsing(tmp_path, monkeypatch):
    _clear_config_state()
    # we need to control how values parsed; QTR_LOG_LEVEL maps to logging.level - parsed as bool only if true/false
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QTR_LOG_LEVEL", "true")
    result = config.load_config()
    assert result["logging"]["level"] is True
    _clear_config_state()
    monkeypatch.setenv("QTR_LOG_LEVEL", "FALSE")
    result = config.load_config()
    assert result["logging"]["level"] is False
    _clear_config_state()


def test_env_override_cache_dir_string(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QTR_CACHE_DIR", "/data/cache")
    result = config.load_config()
    assert result["data"]["cache_dir"] == "/data/cache"
    _clear_config_state()


def test_save_config_to_specified_path(tmp_path):
    _clear_config_state()
    save_path = tmp_path / "saved.yaml"
    config.save_config({"test": 123}, save_path)
    assert save_path.exists()
    loaded = yaml.safe_load(save_path.read_text())
    assert loaded["test"] == 123
    assert config._CONFIG == {"test": 123}
    assert config._CONFIG_PATH == save_path
    _clear_config_state()


def test_save_config_uses_default_cwd(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    config.save_config({"a": 1})
    default_path = tmp_path / "config.yaml"
    assert default_path.exists()
    _clear_config_state()


def test_save_config_uses_config_path_fallback(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "existing.yaml"
    # Create an existing config file so load_config sets _CONFIG_PATH
    cfg_path.write_text("a: 1\n")
    config.load_config(cfg_path)  # sets _CONFIG_PATH from existing file
    assert config._CONFIG_PATH == cfg_path
    # Save without explicit path should use _CONFIG_PATH as fallback
    config.save_config({"b": 2})
    assert cfg_path.exists()
    loaded = yaml.safe_load(cfg_path.read_text())
    assert loaded["b"] == 2
    assert config._CONFIG == {"b": 2}
    assert config._CONFIG_PATH == cfg_path
    _clear_config_state()


def test_reset_config_clears_cache(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"a": 1}))
    first = config.load_config()
    assert first["a"] == 1

    config.reset_config()
    assert config._CONFIG is None
    assert config._CONFIG_PATH is None

    # After reset, get_config re-reads from disk
    second = config.get_config()
    assert second["a"] == 1
    assert second is not first
    _clear_config_state()


def test_reset_config_then_load_explicit_path(tmp_path):
    _clear_config_state()
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"a": 1}))
    config.load_config(cfg_path)
    assert config._CONFIG == {"a": 1}

    config.reset_config()
    assert config._CONFIG is None
    assert config._CONFIG_PATH is None

    # load_config with no path re-searches standard locations (none here)
    result = config.load_config()
    assert result == {}
    _clear_config_state()


def test_reset_config_reachable_from_top_level(tmp_path, monkeypatch):
    """reset_config is exported through qtr.utils and reachable via qtr import."""
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump({"a": 1}))
    config.load_config()
    assert config._CONFIG == {"a": 1}

    config.reset_config()
    assert config._CONFIG is None

    import qtr

    assert hasattr(qtr, "reset_config")
    qtr.reset_config()
    assert config._CONFIG is None
    _clear_config_state()


# --------------------------------------------------------------------------- #
# Dotted-key resolution: nested (loader) shape and flat (legacy) shape
# --------------------------------------------------------------------------- #
class TestConfigValue:
    """``config_value`` resolves both the nested and the flat config shape.

    The loader writes nested mappings (``_apply_env_overrides`` turns
    ``QTR_CACHE_DIR`` into ``{"data": {"cache_dir": ...}}``), so a nested
    document is canonical; the literal flat ``"data.cache_dir"`` key is the
    older convention and is the fallback.
    """

    def test_nested_key_resolves(self):
        cfg = {"data": {"cache_dir": "/nested"}}
        assert config.config_value(cfg, "data.cache_dir") == "/nested"

    def test_deeply_nested_key_resolves(self):
        cfg = {"a": {"b": {"c": 7}}}
        assert config.config_value(cfg, "a.b.c") == 7

    def test_flat_key_is_the_fallback(self):
        cfg = {"data.cache_dir": "/flat"}
        assert config.config_value(cfg, "data.cache_dir") == "/flat"

    def test_nested_wins_over_flat(self):
        cfg = {"data": {"cache_dir": "/nested"}, "data.cache_dir": "/flat"}
        assert config.config_value(cfg, "data.cache_dir") == "/nested"

    def test_missing_key_returns_default(self):
        assert config.config_value({}, "data.cache_dir", ".cache/data") == ".cache/data"

    def test_missing_key_default_is_none(self):
        assert config.config_value({}, "data.cache_dir") is None

    def test_non_mapping_node_falls_back_to_the_flat_key(self):
        # ``data: 5`` is a walk failure, not a value: the flat key must still
        # be honoured instead of returning the scalar.
        cfg = {"data": 5, "data.cache_dir": "/flat"}
        assert config.config_value(cfg, "data.cache_dir") == "/flat"

    def test_non_mapping_node_without_flat_key_returns_default(self):
        cfg = {"data": 5}
        assert config.config_value(cfg, "data.cache_dir", ".cache/data") == ".cache/data"

    def test_present_none_is_a_value_not_a_miss(self):
        # A key that exists with a ``None`` value resolves to ``None``; the
        # caller decides what a null setting means (``config_path`` rejects it).
        cfg = {"data": {"cache_dir": None}}
        assert config.config_value(cfg, "data.cache_dir", ".cache/data") is None

    def test_the_env_override_shape_resolves(self):
        # The exact mapping the loader produces for QTR_CACHE_DIR.
        cfg = {"data": {"cache_dir": "/data/cache"}}
        assert config.config_value(cfg, "data.cache_dir") == "/data/cache"


class TestConfigPath:
    """``config_path`` coerces a dotted key to a path, fail-closed."""

    def test_nested_string_value(self):
        cfg = {"data": {"cache_dir": "/nested"}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path("/nested")

    def test_flat_string_value(self):
        cfg = {"data.cache_dir": "/flat"}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path("/flat")

    def test_missing_key_returns_the_default_path(self):
        assert config.config_path({}, "data.cache_dir", ".cache/data") == Path(".cache/data")

    def test_path_value_passes_through(self):
        cfg = {"data": {"cache_dir": Path("/as-path")}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path("/as-path")

    def test_empty_string_falls_back_to_the_default(self):
        cfg = {"data": {"cache_dir": ""}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path(".cache/data")

    def test_numeric_value_is_coerced_through_str(self):
        # ``QTR_CACHE_DIR=10`` is parsed to the int ``10`` by
        # ``_set_nested``; the caller's literal text is the intended path.
        cfg = {"data": {"cache_dir": 10}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path("10")

    def test_float_value_is_coerced_through_str(self):
        cfg = {"data": {"cache_dir": 1.5}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path("1.5")

    def test_boolean_value_falls_back_to_the_default(self):
        # ``bool`` is an ``int`` subclass, but ``True`` is never a path.
        cfg = {"data": {"cache_dir": True}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path(".cache/data")

    def test_null_value_falls_back_to_the_default(self):
        cfg = {"data": {"cache_dir": None}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path(".cache/data")

    def test_sequence_value_falls_back_to_the_default(self):
        cfg = {"data": {"cache_dir": ["/a", "/b"]}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path(".cache/data")

    def test_mapping_value_falls_back_to_the_default(self):
        cfg = {"data": {"cache_dir": {"nested": "/a"}}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path(".cache/data")

    def test_non_mapping_node_falls_back_to_the_default(self):
        cfg = {"data": 5}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path(".cache/data")

    def test_the_env_override_shape_resolves_end_to_end(self):
        _clear_config_state()
        cfg = {"data": {"cache_dir": "/data/cache"}}
        assert config.config_path(cfg, "data.cache_dir", ".cache/data") == Path("/data/cache")
        _clear_config_state()


# --------------------------------------------------------------------------- #
# Non-mapping config documents and non-mapping intermediate nodes
# --------------------------------------------------------------------------- #
class TestNonMappingConfigDocument:
    """A config file that is valid YAML but not a mapping must not crash.

    ``config.yaml`` is user-editable. A document that parses to a list, a
    scalar or a string is not a usable config -- every consumer indexes it by
    key (``config["validation"]``, ``config.get(...)``) -- so it is the same
    class as the empty document and must fail closed to ``{}``. Returned
    verbatim it crashed the first ``DataCache``/``ExperimentTracker``
    construction with ``AttributeError: 'list' object has no attribute 'get'``.
    """

    @pytest.mark.parametrize("text", ["[1, 2, 3]", "5", "hello", "true", "", "null"])
    def test_non_mapping_document_loads_as_empty(self, tmp_path, text):
        _clear_config_state()
        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(text)
        assert config.load_config(cfg_path) == {}
        _clear_config_state()

    def test_non_mapping_document_with_env_override_still_applies(self, tmp_path, monkeypatch):
        _clear_config_state()
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.yaml").write_text("[1, 2, 3]")
        monkeypatch.setenv("QTR_CACHE_DIR", "/data/cache")
        # The malformed document is dropped; the env override then lands on the
        # empty dict instead of crashing in ``_set_nested``.
        assert config.load_config() == {"data": {"cache_dir": "/data/cache"}}
        _clear_config_state()

    def test_data_cache_constructs_with_non_mapping_config(self, tmp_path, monkeypatch):
        _clear_config_state()
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.yaml").write_text("[1, 2, 3]")
        from qtr.data.fetcher import DataCache

        cache = DataCache()
        assert cache.cache_dir == Path(".cache/data")
        _clear_config_state()


class TestSetNestedNonMapping:
    """``_set_nested`` tolerates a non-mapping node anywhere on the path."""

    def test_non_mapping_intermediate_is_replaced(self):
        d = {"data": 5}
        config._set_nested(d, ["data", "cache_dir"], "/x")
        assert d == {"data": {"cache_dir": "/x"}}

    def test_non_mapping_document_is_ignored(self):
        d = [1, 2, 3]
        config._set_nested(d, ["data", "cache_dir"], "/x")
        assert d == [1, 2, 3]

    def test_existing_mapping_is_descended(self):
        d = {"data": {"cache_dir": "/old", "other": 1}}
        config._set_nested(d, ["data", "cache_dir"], "/new")
        assert d == {"data": {"cache_dir": "/new", "other": 1}}

    def test_env_override_replaces_non_mapping_intermediate_end_to_end(self, tmp_path, monkeypatch):
        _clear_config_state()
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.yaml").write_text(yaml.dump({"data": 5}))
        monkeypatch.setenv("QTR_CACHE_DIR", "/data/cache")
        assert config.load_config() == {"data": {"cache_dir": "/data/cache"}}
        _clear_config_state()


    def test_load_config_explicit_missing_path_sets_save_target(self, tmp_path):
        """An explicit but missing config path must not overwrite a prior config.

        ``save_config()`` falls back to ``_CONFIG_PATH`` when no path is given.
        Loading a missing explicit path returns an empty config; it must record
        that explicit path as the save target so a later save writes there rather
        than clobbering a previously loaded config file.
        """
        _clear_config_state()
        old_path = tmp_path / "old.yaml"
        old_path.write_text("x: 1\n")
        config.load_config(old_path)

        missing = tmp_path / "new.yaml"
        assert config.load_config(missing) == {}
        assert config._CONFIG_PATH == missing
        config.save_config({"y": 2})
        assert old_path.read_text() == "x: 1\n"
        assert missing.read_text().strip() == "y: 2"
        _clear_config_state()
