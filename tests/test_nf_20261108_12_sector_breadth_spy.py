import importlib.util
import pathlib
import py_compile

py_compile.compile("run_nf_20261108_12_sector_breadth_spy.py", doraise=True)


def test_compiles():
    assert True
