"""Safe parquet reader for test artifacts with engine fallback.

Test suites read parquet artifacts produced by the run_*.py experiments.
The parquet engine available in a given environment (pyarrow, fastparquet,
or neither) varies, so reads must degrade gracefully instead of failing on
a missing optional dependency.
"""

from __future__ import annotations

import importlib
from typing import Any

import pandas as pd

_RETRY_EXCEPTIONS = (ImportError, OSError, ValueError, AttributeError)


def _engine_available(engine: str) -> bool:
    try:
        importlib.import_module(engine)
        return True
    except ImportError:
        return False


def read_parquet_safe(path: Any, **kwargs: Any) -> Any:
    """Read a parquet file, falling back across engines.

    Tries engine="pyarrow" if importable, then engine="fastparquet" if
    importable, and finally pandas' default engine. Catches
    ImportError, OSError, ValueError, and AttributeError per strategy and
    retries with the next one; the final error is re-raised if every
    strategy fails.
    """
    strategies = []
    if _engine_available("pyarrow"):
        call_kwargs = dict(kwargs)
        call_kwargs["engine"] = "pyarrow"
        strategies.append(call_kwargs)
    if _engine_available("fastparquet"):
        call_kwargs = dict(kwargs)
        call_kwargs["engine"] = "fastparquet"
        strategies.append(call_kwargs)
    strategies.append(dict(kwargs))

    last_error: Exception | None = None
    for call_kwargs in strategies:
        try:
            return pd.read_parquet(path, **call_kwargs)
        except _RETRY_EXCEPTIONS as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    raise ImportError(f"no parquet engine available to read {path!r}")
