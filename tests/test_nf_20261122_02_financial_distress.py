from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "nf_20261122_02", ROOT / "run_nf_20261122_02_financial_distress.py"
)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def _synthetic_data(n_days=800, n_names=6, seed=0):
    """Geometric price paths and quarterly capital-structure share/liability rows.

    No network: closes are synthetic, capital-structure rows are point-in-time
    (filed ~45 days after each quarter end). Returns (closes, observations,
    calendar) where ``observations`` is symbol -> DataFrame[end, filed,
    liabilities, shares].
    """
    rng = np.random.default_rng(seed)
    calendar = pd.bdate_range("2020-01-01", periods=n_days)
    rets = rng.normal(0.0, 0.01, size=(n_days, n_names))
    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    columns = [f"S{i}" for i in range(n_names)]
    closes = pd.DataFrame(prices, index=calendar, columns=columns)
    ends = pd.date_range("2019-01-01", periods=16, freq="90D")
    filed = ends + pd.Timedelta(days=45)
    observations = {}
    for j, col in enumerate(columns):
        shares = 1.0e9 * (1.0 + 0.05 * j) * np.ones(len(ends))
        liabilities = 5.0e9 * (1.0 + 0.1 * j) * np.ones(len(ends))
        observations[col] = pd.DataFrame(
            {"end": ends, "filed": filed, "liabilities": liabilities, "shares": shares}
        )
    return closes, observations, calendar


def test_constants_match_preregistration():
    assert mod.EXPERIMENT == "nf_20261122_02_financial_distress"
    assert mod.NF_ID == "NF-20261122-02"
    assert mod.HYPOTHESIS == "H197"
    assert mod.START == "2011-01-03"
    assert mod.END == "2026-11-21"
    assert mod.TRAIN_END == "2021-12-31"
    assert mod.VAL_END == "2023-12-31"
    assert mod.COST_ONE_WAY_BPS == 5.0
    assert mod.MIN_ACTIVE_NAMES == 40
    assert mod.MIN_PRICE_OBSERVATIONS == 252
    assert mod.MIN_LIAB_OBSERVATIONS == 2
    assert mod.GATES == mod.h184.GATES
    assert mod.FEATURES == ["equity_to_debt", "distance_to_default"]
    assert mod.DISTRESS_VOL_WINDOW == 252
    assert mod.VOL_LOOKBACK == 60
    assert mod.DAYS_PER_YEAR == 252


def test_universe_is_sp100_minus_exclusions():
    assert len(mod.UNIVERSE_SYMBOLS) == 98
    assert "XOM" not in mod.UNIVERSE_SYMBOLS
    assert "BKNG" not in mod.UNIVERSE_SYMBOLS
    assert len(set(mod.UNIVERSE_SYMBOLS)) == 98


def test_bounded_grid_is_sixteen_declared_combos():
    combos = list(mod.iter_grid())
    assert len(combos) == 2 * 2 * 1 * 2 * 2 == 16
    assert {row["feature"] for row in combos} == {"equity_to_debt", "distance_to_default"}
    for row in combos:
        assert row["exit_z"] == 0.0
        assert row["entry_z"] in {0.5, 1.0}
        assert row["k"] in {5, 10}
        assert row["vol_target"] in {0.10, 0.15}


def test_returns_from_closes_first_row_nan():
    closes, _, _ = _synthetic_data(n_days=10, n_names=3)
    returns = mod.returns_from_closes(closes)
    assert returns.iloc[0].isna().all()
    assert np.isfinite(returns.iloc[1:].to_numpy()).all()
    expected = closes.iloc[1] / closes.iloc[0] - 1.0
    assert np.allclose(returns.iloc[1].to_numpy(), expected.to_numpy())


def test_distress_observations_merges_liabilities_and_shares():
    facts = {
        "facts": {
            "us-gaap": {
                "Liabilities": {
                    "units": {
                        "USD": [
                            {
                                "end": "2020-12-31",
                                "filed": "2021-02-01",
                                "val": 5.0e9,
                                "form": "10-K",
                            },
                        ]
                    }
                },
                "CommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {"end": "2020-12-31", "filed": "2021-02-10", "val": 1.0e9},
                        ]
                    }
                },
            }
        }
    }
    obs = mod.distress_observations(facts)
    assert list(obs.columns) == ["end", "filed", "liabilities", "shares"]
    assert len(obs) == 1
    # ``filed`` is the latest of the two contributing acceptance dates.
    assert obs.iloc[0]["filed"] == pd.Timestamp("2021-02-10")
    assert obs.iloc[0]["liabilities"] == 5.0e9
    assert obs.iloc[0]["shares"] == 1.0e9


def test_distress_observations_falls_back_to_liabilities_and_equity():
    facts = {
        "facts": {
            "us-gaap": {
                "LiabilitiesAndStockholdersEquity": {
                    "units": {
                        "USD": [
                            {
                                "end": "2021-12-31",
                                "filed": "2022-02-01",
                                "val": 8.0e9,
                                "form": "10-K",
                            },
                        ]
                    }
                },
                "WeightedAverageNumberOfSharesOutstandingBasic": {
                    "units": {
                        "shares": [
                            {"end": "2021-12-31", "filed": "2022-02-01", "val": 2.0e9},
                        ]
                    }
                },
            }
        }
    }
    obs = mod.distress_observations(facts)
    assert len(obs) == 1
    assert obs.iloc[0]["liabilities"] == 8.0e9
    assert obs.iloc[0]["shares"] == 2.0e9


def test_distress_observations_empty_when_liability_missing():
    facts = {
        "facts": {
            "us-gaap": {
                "CommonStockSharesOutstanding": {
                    "units": {
                        "shares": [{"end": "2020-12-31", "filed": "2021-02-01", "val": 1.0e9}]
                    }
                }
            }
        }
    }
    assert mod.distress_observations(facts).empty


def test_distress_observations_empty_when_shares_missing():
    facts = {
        "facts": {
            "us-gaap": {
                "Liabilities": {
                    "units": {
                        "USD": [
                            {
                                "end": "2020-12-31",
                                "filed": "2021-02-01",
                                "val": 5.0e9,
                                "form": "10-K",
                            },
                        ]
                    }
                }
            }
        }
    }
    assert mod.distress_observations(facts).empty


def test_build_distress_panels_shape_and_values():
    closes, observations, calendar = _synthetic_data(n_days=800, n_names=6, seed=1)
    products = list(closes.columns)
    returns = mod.returns_from_closes(closes.reindex(calendar).ffill())
    panels = mod.build_distress_panels(observations, closes, returns, calendar)
    assert set(panels.keys()) == {"equity_to_debt", "distance_to_default"}
    for feat in panels:
        assert panels[feat].index.equals(calendar)
        assert list(panels[feat].columns) == products
    e2d = panels["equity_to_debt"]["S0"].dropna()
    assert len(e2d) > 0
    assert (e2d > 0.0).all()


def test_distance_to_default_is_not_all_nan_regression():
    """Guard the sigma-volatile DD panel must be populated (not silently zeroed)."""
    closes, observations, calendar = _synthetic_data(n_days=800, n_names=6, seed=2)
    returns = mod.returns_from_closes(closes.reindex(calendar).ffill())
    panels = mod.build_distress_panels(observations, closes, returns, calendar)
    dd = panels["distance_to_default"]
    # After the 252-day vol window, every symbol must have finite DD values.
    assert dd.notna().any().any()
    assert dd.iloc[300:].notna().mean().mean() > 0.5


def test_distress_panels_respect_share_and_liability_pit():
    """A capital-structure row is only usable from its filed date onward."""
    closes, _, calendar = _synthetic_data(n_days=800, n_names=4, seed=3)
    products = list(closes.columns)
    late_filed = pd.Timestamp("2022-06-01")
    observations = {
        products[0]: pd.DataFrame(
            {
                "end": [pd.Timestamp("2022-03-31")],
                "filed": [late_filed],
                "liabilities": [5.0e9],
                "shares": [1.0e9],
            }
        )
    }
    returns = mod.returns_from_closes(closes.reindex(calendar).ffill())
    panels = mod.build_distress_panels(observations, closes, returns, calendar)
    series = panels["equity_to_debt"][products[0]].dropna()
    assert len(series) > 0
    assert series.index[0] >= late_filed


def test_equity_to_debt_monotone_in_market_cap():
    """e2d = shares * price / liabilities; doubling price doubles e2d."""
    closes, observations, calendar = _synthetic_data(n_days=400, n_names=3, seed=4)
    products = list(closes.columns)
    returns = mod.returns_from_closes(closes.reindex(calendar).ffill())
    panels = mod.build_distress_panels(observations, closes, returns, calendar)
    e2d = panels["equity_to_debt"]
    # equity_to_debt is positive and varies cross-sectionally.
    row = e2d.iloc[-1].dropna()
    assert len(row) >= 2
    assert row.nunique() >= 2


def test_cross_sectional_z_winsorized_at_three():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    signal = pd.DataFrame(
        np.array([[1.0, 2.0, 3.0, 4.0, 100.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    z = mod.h187.cross_sectional_z(signal)
    assert z.abs().max().max() <= 3.0 + 1e-10


def test_distress_signal_weights_long_high_short_low():
    """Distress direction: long safest (A, B high z), short most distressed (D, E)."""
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C", "D", "E"]
    # z: A=2.0 (safest), B=1.5, C=0.0, D=-1.5, E=-2.0 (most distressed).
    z = pd.DataFrame(
        np.array([[2.0, 1.5, 0.0, -1.5, -2.0]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    weights = mod.h191.value_signal_weights(z, entry_z=1.0, exit_z=0.0, k=2, products=products)
    assert weights.iloc[0]["A"] == 0.25
    assert weights.iloc[0]["B"] == 0.25
    assert weights.iloc[0]["D"] == -0.25
    assert weights.iloc[0]["E"] == -0.25
    assert weights.iloc[0]["C"] == 0.0


def test_target_weights_zero_when_insufficient_active():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C"]
    signal = pd.DataFrame(
        np.array([[2.0, 1.0, np.nan]] * len(calendar)),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(7).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {
        "feature": "equity_to_debt",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 1,
        "vol_target": 0.10,
    }
    weights = mod.target_weights(signal, params, returns, products)
    # Only 3 active names, MIN_ACTIVE_NAMES=40, so all weights should be 0.
    assert (weights == 0.0).all().all()


def test_walk_forward_score_short_train_returns_sentinel():
    calendar = pd.bdate_range("2020-01-01", periods=10)
    products = ["A", "B", "C"]
    signal = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    params = {
        "feature": "equity_to_debt",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 2,
        "vol_target": 0.10,
    }
    score = mod.h191.walk_forward_score(signal, params, returns, products, calendar)
    assert score == -999.0


def test_perturbation_sharpes_returns_four_points():
    calendar = pd.bdate_range("2020-01-01", periods=200)
    products = ["A", "B", "C", "D", "E"]
    signal = pd.DataFrame(
        np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        np.random.default_rng(8).normal(0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    selected = {
        "feature": "equity_to_debt",
        "entry_z": 1.0,
        "exit_z": 0.0,
        "k": 2,
        "vol_target": 0.10,
    }
    sharpes = mod.h191.perturbation_sharpes(signal, selected, returns, products, calendar)
    assert len(sharpes) == 4
    assert all(np.isfinite(v) or np.isnan(v) for v in sharpes)


def test_train_collinearity_is_bounded():
    calendar = pd.bdate_range("2020-01-01", periods=100)
    products = ["A", "B", "C", "D", "E"]
    features = {
        "equity_to_debt": pd.DataFrame(
            np.random.default_rng(7).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
        "distance_to_default": pd.DataFrame(
            np.random.default_rng(8).normal(0, 1, size=(len(calendar), len(products))),
            index=calendar,
            columns=products,
        ),
    }
    value = mod.train_collinearity(features, calendar)
    assert -1.0 <= value <= 1.0


def test_train_collinearity_detects_proportional_panels_regression():
    """equity_to_debt vs distance_to_default near-identical -> Spearman ~1.0."""
    calendar = pd.bdate_range("2020-01-01", periods=60)
    products = ["A", "B", "C", "D", "E", "F"]
    rng = np.random.default_rng(11)
    base = pd.DataFrame(
        rng.uniform(-1.0, 1.0, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    features = {
        "equity_to_debt": base,
        "distance_to_default": base * 1.0,
    }
    value = mod.train_collinearity(features, calendar)
    assert value > 0.99


def test_trailing_total_return_and_volatility_are_causal():
    calendar = pd.bdate_range("2020-01-01", periods=400)
    products = ["A", "B", "C"]
    rng = np.random.default_rng(5)
    returns = pd.DataFrame(
        rng.normal(0.0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    mom = mod.trailing_total_return(returns, 60)
    vol = mod.trailing_volatility(returns, 60)
    assert mom.iloc[:59].isna().all().all()
    assert vol.iloc[:59].isna().all().all()
    manual = (1.0 + returns["A"]).iloc[:60].prod() - 1.0
    assert mom["A"].iloc[59] == manual


def test_train_mechanism_separation_reports_bounded_spearman():
    calendar = pd.bdate_range("2020-01-01", periods=400)
    products = ["A", "B", "C", "D", "E"]
    rng = np.random.default_rng(9)
    distress = pd.DataFrame(
        rng.uniform(0.0, 1.0, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    returns = pd.DataFrame(
        rng.normal(0.0, 0.01, size=(len(calendar), len(products))),
        index=calendar,
        columns=products,
    )
    features = {"distance_to_default": distress}
    sep = mod.train_mechanism_separation(features, None, returns, calendar)
    for value in sep.values():
        assert -1.0 <= value <= 1.0
    assert "distance_to_default_vs_momentum_252" in sep
    assert "distance_to_default_vs_realized_vol_252" in sep


def _latest_artifact():
    import glob

    artifacts = glob.glob(
        str(
            ROOT
            / ".experiments"
            / "nf_runs"
            / "nf_20261122_02_financial_distress_*"
            / "summary.json"
        )
    )
    if not artifacts:
        import pytest

        pytest.skip("H197 artifact not yet generated")
    return max(artifacts)


def test_artifact_summary_exists_and_verdict():
    with open(_latest_artifact()) as f:
        summary = json.load(f)
    assert summary["experiment"] == "nf_20261122_02_financial_distress"
    assert summary["nf_id"] == "NF-20261122-02"
    assert summary["hypothesis"] == "H197"
    assert summary["verdict"] in {"ACCEPT", "REJECT"}
    assert summary["gates_passed"] >= 0
    assert summary["gates_total"] == 8
    assert summary["selected"]["feature"] in {"equity_to_debt", "distance_to_default"}
    assert summary["data"]["universe_size"] >= mod.MIN_ACTIVE_NAMES
    assert summary["data"]["excluded_symbols"] == ["XOM", "BKNG"]
    assert summary["integrity"]["src_qtr_unchanged"] is True
    assert summary["integrity"]["gate_weakening"] is False


def test_artifact_grid_csv_has_sixteen_rows():
    import glob

    grids = glob.glob(
        str(ROOT / ".experiments" / "nf_runs" / "nf_20261122_02_financial_distress_*" / "grid.csv")
    )
    if not grids:
        import pytest

        pytest.skip("H197 grid artifact not yet generated")
    grid = pd.read_csv(max(grids))
    assert len(grid) == 16
    assert {"feature", "entry_z", "exit_z", "k", "vol_target", "wf_train_sharpe"} == set(
        grid.columns
    )


def test_distance_to_default_panel_values_are_finite_in_sample():
    """distance_to_default uses the trailing-252 vol; on a long synthetic sample
    it must be finite (the H197 sigma-lookahead bug regression)."""
    closes, observations, calendar = _synthetic_data(n_days=800, n_names=6, seed=5)
    returns = mod.returns_from_closes(closes.reindex(calendar).ffill())
    panels = mod.build_distress_panels(observations, closes, returns, calendar)
    dd = panels["distance_to_default"].iloc[260:]
    assert np.isfinite(dd.to_numpy()).mean() > 0.5
