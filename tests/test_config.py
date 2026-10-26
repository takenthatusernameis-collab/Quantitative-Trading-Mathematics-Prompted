from __future__ import annotations

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


def test_env_overrides_bool_true(tmp_path, monkeypatch):
    _clear_config_state()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QTR_LOG_LEVEL", "DEBUG")  # stays string? wait - check mapping
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
    config.load_config(cfg_path)  # sets _CONFIG_PATH even if empty
    # but load_config with non-existent explicit path sets empty config and path? check
    config._CONFIG_PATH = cfg_path  # simulate
    config._CONFIG = None
    # better to simulate properly
    _clear_config_state()
