"""
Configuration management for QTR.
"""

import math
import os
from pathlib import Path
from typing import Any

import yaml

_CONFIG: dict[str, Any] | None = None
_CONFIG_PATH: Path | None = None


def load_config(config_path: Path | None = None) -> dict[str, Any]:
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


def get_config() -> dict[str, Any]:
    """Get current configuration (loads if not already loaded)."""
    if _CONFIG is None:
        return load_config()
    return _CONFIG


def reset_config() -> None:
    """Clear the cached configuration and config path.

    The next call to :func:`load_config` or :func:`get_config` re-reads
    the config file from disk (or returns an empty dict if none is found).
    Used by tests and by callers that need to force a re-read after the
    config file has changed on disk.
    """
    global _CONFIG, _CONFIG_PATH
    _CONFIG = None
    _CONFIG_PATH = None


def _apply_env_overrides(config: dict[str, Any]) -> None:
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


def config_value(config: dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    """Resolve a dotted config key from a nested mapping, with a flat fallback.

    ``_apply_env_overrides`` writes **nested** mappings (the override
    ``QTR_CACHE_DIR`` becomes ``{"data": {"cache_dir": ...}}``, pinned by
    ``tests/test_config.py::test_env_override_cache_dir_string``), so a nested
    document is the canonical shape of a loaded config.  Early call sites read
    the same setting as a literal flat key (``config.get("data.cache_dir")``),
    which can only ever match a hand-written ``data.cache_dir:`` line -- the
    nested document the loader itself produces was silently ignored.  Both
    shapes therefore resolve here: walk the nested path first, and fall back to
    the literal flat key only when the walk fails.  A node that exists but is
    not a mapping (``data: 5``) is a walk failure, not a value.

    Args:
        config: The loaded configuration mapping.
        dotted_key: Dot-separated key, e.g. ``"data.cache_dir"``.
        default: Returned when neither shape holds the key.

    Returns:
        The configured value, or ``default``.
    """
    node: Any = config
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return config.get(dotted_key, default)
        node = node[part]
    return node


def config_path(config: dict[str, Any], dotted_key: str, default: str) -> Path:
    """Resolve a dotted config key to a filesystem path, fail-closed.

    A path setting is only usable if it is something ``Path`` can represent.
    A missing key falls back to ``default``; a present-but-unusable value
    (a list, a mapping, a boolean, an empty string) also falls back rather
    than constructing a nonsensical path or raising out of a constructor
    every caller treats as infallible.  Numeric values are coerced through
    ``str``: ``_set_nested`` parses a numeric env value (``QTR_CACHE_DIR=10``
    becomes ``10``), and the caller's literal text is the intended path
    component, so ``10`` resolves to the relative path ``"10"``.

    Args:
        config: The loaded configuration mapping.
        dotted_key: Dot-separated key, e.g. ``"data.cache_dir"``.
        default: Path used when the key is absent or unusable.

    Returns:
        The configured path.
    """
    value = config_value(config, dotted_key, default)
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        return Path(value) if value else Path(default)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return Path(str(value))
    return Path(default)


def _set_nested(d: dict[str, Any], keys: list, value: str) -> None:
    """Set nested dictionary value, creating intermediate dicts as needed."""
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    # Try to parse as int/float/bool
    try:
        value = int(value)
    except ValueError:
        try:
            parsed = float(value)
        except ValueError:
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
        else:
            if math.isfinite(parsed):
                value = parsed
            # non-finite (nan/inf) stays as the original string
    d[keys[-1]] = value


def save_config(config: dict[str, Any], path: Path | None = None) -> None:
    """Save configuration to YAML file."""
    global _CONFIG, _CONFIG_PATH
    path = path or _CONFIG_PATH or Path.cwd() / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    _CONFIG = config
    _CONFIG_PATH = path
