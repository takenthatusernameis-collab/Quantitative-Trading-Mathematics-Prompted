import warnings


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
