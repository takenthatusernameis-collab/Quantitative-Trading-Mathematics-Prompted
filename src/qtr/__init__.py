"""Quantitative Trading Research (qtr) package.

The top level re-exports the public API of every subpackage, so that both
``from qtr import sharpe_ratio`` and ``from qtr import *`` reach the same
symbols.  The exported set is composed from the subpackages' own ``__all__``
lists, so it cannot drift from them.
"""

from qtr.backtest import *  # noqa: F401,F403
from qtr.backtest import __all__ as _backtest_all
from qtr.data import *  # noqa: F401,F403
from qtr.data import __all__ as _data_all
from qtr.strategies import *  # noqa: F401,F403
from qtr.strategies import __all__ as _strategies_all
from qtr.tracking import *  # noqa: F401,F403
from qtr.tracking import __all__ as _tracking_all
from qtr.utils import *  # noqa: F401,F403
from qtr.utils import __all__ as _utils_all
from qtr.validation import *  # noqa: F401,F403
from qtr.validation import __all__ as _validation_all

__version__ = "0.1.0"

__all__ = [
    "__version__",
    *_backtest_all,
    *_data_all,
    *_strategies_all,
    *_tracking_all,
    *_utils_all,
    *_validation_all,
]
