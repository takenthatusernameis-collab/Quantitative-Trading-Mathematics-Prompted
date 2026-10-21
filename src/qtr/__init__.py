"""Quantitative Trading Research (qtr) package."""

__version__ = "0.1.0"

from qtr.backtest import *  # noqa: F401,F403
from qtr.data import *  # noqa: F401,F403
from qtr.strategies import *  # noqa: F401,F403
from qtr.tracking import *  # noqa: F401,F403
from qtr.utils import *  # noqa: F401,F403
from qtr.validation import *  # noqa: F401,F403

__all__ = ["__version__"]
