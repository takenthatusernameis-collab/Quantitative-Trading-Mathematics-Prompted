import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "run_nf_20261107_16_credit_relmom", ROOT / "run_nf_20261107_16_credit_relmom.py"
)
MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = MOD
_SPEC.loader.exec_module(MOD)


def _series(n=500, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-02", periods=n)
    hyg = 80 * np.exp(np.cumsum(rng.normal(0, 0.005, n)))
    lqd = 110 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    spy = 300 * np.exp(np.cumsum(rng.normal(0.0002, 0.01, n)))
    return pd.Series(hyg, index=idx), pd.Series(lqd, index=idx), pd.Series(spy, index=idx)


def test_relmom_z_finite():
    h, l, _ = _series()
    z = MOD.relmom_z(h, l, 21, 63)
    assert np.isfinite(z.dropna()).all()


def test_build_exposure_bounded():
    idx = pd.bdate_range("2020-01-01", periods=80)
    z = pd.Series(np.random.default_rng(0).normal(0, 1, 80), index=idx)
    e = MOD.build_exposure(z, 1.5, 0.5, 0.10)
    assert (e >= -1e-12).all()
    assert (e <= 0.10 + 1e-12).all()


def test_vol_scale_bounded():
    idx = pd.bdate_range("2020-01-01", periods=80)
    r = pd.Series(np.random.default_rng(1).normal(0, 0.01, 80), index=idx)
    s = MOD.vol_scale(r, 0.10)
    assert (s >= 0).all() and (s <= 1.0 + 1e-12).all()
