"""
Configuration management for QTR.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


_CONFIG: Optional[Dict[str, Any]] = None
_CONFIG_PATH: Optional[Path] = None


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    global _CONFIG, _CONFIG_PATH

    if _CONFIG is not None and config_path is None:
        return _CONFIG

    if config_path is None:
        # Search for config in standard locations
        search_paths = [
            Path.cwd() / "config.yaml",
            Path.cwd() / "config.yml",
            Path(__file__).parent.parent.parent / "config.yaml",
            Path(__file__).parent.parent.parent / "config.yml",
        ]
        for p in search_paths:
            if p.exists():
                config_path = p
                break

    if config_path and config_path.exists():
        with open(config_path) as f:
            _CONFIG = yaml.safe_load(f) or {}
        _CONFIG_PATH = config_path
    else:
        _CONFIG = {}

    # Apply environment variable overrides
    _apply_env_overrides(_CONFIG)

    return _CONFIG


def get_config() -> Dict[str, Any]:
    """Get current configuration (loads if not already loaded)."""
    if _CONFIG is None:
        return load_config()
    return _CONFIG


def _apply_env_overrides(config: Dict[str, Any]) -> None:
    """Apply environment variable overrides to config."""
    env_mappings = {
        "QTR_CACHE_DIR": "data.cache_dir",
        "QTR_LOG_LEVEL": "logging.level",
        "QTR_MAX_CPU_HOURS": "compute.max_cpu_hours",
    }

    for env_var, config_key in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None:
            _set_nested(config, config_key.split("."), value)


def _set_nested(d: Dict[str, Any], keys: list, value: str) -> None:
    """Set nested dictionary value, creating intermediate dicts as needed."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    # Try to parse as int/float/bool
    try:
        if "." in value:
            value = float(value)
        else:
            value = int(value)
    except ValueError:
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
    d[keys[-1]] = value


def save_config(config: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Save configuration to YAML file."""
    global _CONFIG, _CONFIG_PATH
    path = path or _CONFIG_PATH or Path.cwd() / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    _CONFIG = config
    _CONFIG_PATH = path