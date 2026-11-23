import warnings

import pytest


def pytest_collection(session):
    # Under `-W error`, command-line filters take precedence over ini/conftest
    # filters applied before collection, and pytest clears warning registries
    # on every collection entry. Re-apply the ignore inside the collection
    # context so yfinance's google.protobuf import
    # (datetime.datetime.utcfromtimestamp deprecation) does not escalate to an
    # error and abort collection of experiment test modules. Project code stays
    # subject to -W error outside this third-party module.
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="google\\.protobuf",
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    # pytest resets ``warnings.filters`` around every test item (setup/call/
    # teardown each run inside a fresh ``catch_warnings`` context), so a filter
    # installed at collection time does not survive into a test *call*. A few
    # frozen experiment runners import yfinance lazily at call time (e.g. the
    # ``test_runner_import_contract.py`` import probe); yfinance, via
    # google.protobuf's well_known_types, calls the deprecated
    # ``datetime.datetime.utcfromtimestamp()``, which ``-W error`` promotes and
    # aborts the import. The runners are frozen experiment artifacts and must not
    # be edited, so the third-party deprecation is ignored for the duration of
    # each test call. Project code stays subject to -W error.
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r"datetime\.datetime\.utcfromtimestamp\(\) is deprecated",
    )
    yield
