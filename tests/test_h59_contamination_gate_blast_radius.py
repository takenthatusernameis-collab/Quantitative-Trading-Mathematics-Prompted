"""H59: the full gate blast radius of the H58 price contamination.

H58 measured that the ``ir`` gate of nine published summaries flips from
True to False when the two zero-crossing sessions are removed from the
series.  It measured *one* gate.  The record publishes **eight** gates per
summary, and the contamination reaches more than one of them:

- in the **nine** families whose *benchmark* carries the contaminated bar,
  only the benchmark-fed gates can move, and only the ``ir`` gate does;
- in the **two** families whose *strategy* equity carries the contaminated
  bar -- the ones whose published equity curve goes **negative** -- the
  strategy-fed gates move as well, and **two** of them flip:

  | summary | gate | published | counterfactual | threshold |
  |---|---|---:|---:|---:|
  | ``exp_2026-10-10T21-58-28-353634Z`` | ``stab`` | **False** (-0.5125) | **True** (+0.7149) | >= 0.7 |
  | ``exp_2026-10-10T21-58-28-353634Z`` | ``worst`` | **False** (-1.6784) | **True** (+0.3250) | >= 0.3 |
  | ``exp_2026-10-10T21-59-16-546117Z`` | ``stab`` | **False** (-0.5125) | **True** (+0.7149) | >= 0.7 |
  | ``exp_2026-10-10T21-59-16-546117Z`` | ``worst`` | **False** (-1.6784) | **True** (+0.3250) | >= 0.3 |

So the contamination decides **thirteen** published gate booleans: it
manufactures nine passes (H58) and it destroys two passes in each of the
two strategy-contaminated families.  The direction matters: a published
``False`` on ``stab`` and ``worst`` is *not* evidence that the family fails
those gates -- the evidence is a single negative print in a Yahoo
continuous-contract splice.

Two honest caveats are pinned by this contract:

1. **The two new flips are marginal.**  The counterfactual clears the
   ``stab`` gate by 0.0149 (2.1 % of the threshold) and the ``worst`` gate
   by 0.0250 (8.3 %).  The contract pins the margins so that a reader can
   see that the *direction* is decided by the contamination while the
   *outcome* sits close to the line.  Both flips survive a second,
   independent counterfactual (dropping the two sessions instead of
   zeroing them), so the direction is not an artefact of one choice.
2. **The published ``oos_max_dd`` of those two families is arithmetically
   impossible**: -1.5096 is a drawdown of **-150.96 %** of the normalised
   OOS equity, which can only happen because the equity curve goes
   negative (the published minimum is -463 814.84 on a long-only
   strategy).  It is a data artifact, not a loss.

No published verdict moves: every affected summary is a REJECT, and the
certified families (H10, H21, H22, H25) never see the crossing.  Nothing
under ``src/qtr`` is changed by this audit, no artifact is rewritten, no
grid is re-run.

Scope: read-only against the committed artifacts.  The contract re-derives
the published statistics of the eleven affected summaries from their own
frozen equity curves (the *control*), applies the H58 counterfactual, and
pins the resulting gate booleans.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from qtr.validation.statistics import (  # noqa: E402
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
)

ARTIFACTS = ROOT / ".experiments" / "artifacts"

HYPOTHESIS = "H59"

# --------------------------------------------------------------------------- #
# frozen constants (the measurement, not a parameter of the audit)            #
# --------------------------------------------------------------------------- #
CAPITAL = 1_000_000.0
TRAIN_END = pd.Timestamp("2019-12-31")
ZERO_CROSSING_SESSIONS = (pd.Timestamp("2020-04-20"), pd.Timestamp("2020-04-21"))

# The gate thresholds the four families publish (identical across them).
GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
}

# The four producer conventions the eleven affected summaries were written
# on.  ``dd`` is the drawdown convention, ``align`` is how the strategy is
# aligned to the benchmark before the comparison, ``regime`` is how the VIX
# series is mapped onto the OOS window.
#
# * ``h7``   -- ``run_futures_tsmom_experiment.py``: absolute drawdown on
#              the normalised OOS equity, no alignment, VIX reindexed by
#              the runner and committed as ``vix_close.parquet``.
# * ``ddcv`` -- ``run_ddcv_experiment.py``: absolute drawdown, no
#              alignment, same VIX handling.
# * ``h6``   -- ``run_h6_vix_ddcv_experiment.py``: absolute drawdown, no
#              alignment, same VIX handling.
# * ``h8``   -- ``run_h8_rolladjusted_tsmom_experiment.py``: *percentage*
#              drawdown on the OOS equity level, the strategy is aligned
#              to the benchmark's OOS length, and the VIX is reindexed
#              onto the OOS window at use time.
CONVENTIONS = {
    "h7": {"dd": "absolute", "align": None, "regime": "committed"},
    "ddcv": {"dd": "absolute", "align": None, "regime": "committed"},
    "h6": {"dd": "absolute", "align": None, "regime": "committed"},
    "h8": {"dd": "percent", "align": "tail", "regime": "reindex"},
}

# The eleven affected summaries: the artifact directory, the strategy
# equity file, the producer family, and whether the *strategy* equity
# carries the contaminated bar.
AFFECTED = (
    ("exp_2026-10-10T21-58-28-353634Z", "ensemble_equity.parquet", "h7", True),
    ("exp_2026-10-10T21-59-16-546117Z", "ensemble_equity.parquet", "h7", True),
    ("exp_2026-10-10T22-59-01-182037Z", "ensemble_equity.parquet", "h7", False),
    ("exp_2026-10-11T00-26-35-750834Z", "best_ddcv_equity.parquet", "ddcv", False),
    ("exp_2026-10-11T00-34-05-381535Z", "best_ddcv_equity.parquet", "ddcv", False),
    ("exp_2026-10-11T02-44-40-301520Z", "best_equity.parquet", "h6", False),
    ("exp_2026-10-11T02-46-37-311994Z", "best_equity.parquet", "h6", False),
    ("exp_2026-10-11T07-18-39-160945Z", "best_equity.parquet", "h6", False),
    ("exp_2026-10-11T08-02-22-999214Z", "best_equity.parquet", "h6", False),
    ("exp_2026-10-14T08-27-02-650342Z", "ensemble_equity.parquet", "h7", False),
    ("exp_2026-10-11T15-21-31-333870Z", "best_equity_w0.5.parquet", "h8", False),
)

# The re-derived published statistics of every affected summary, and the
# counterfactual's.  The control reproduces the published values to 1e-12;
# the counterfactual values are the measurement.
MEASURED = {
    "exp_2026-10-10T21-58-28-353634Z": {
        "control": {
            "sharpe": -0.4037945993424417,
            "pf": 0.7423116804276377,
            "dd": -1.5095951367917253,
            "stab": -0.5124851046944916,
            "worst": -1.6784412527322672,
            "ir": -0.6399266589647274,
            "p": 0.15319090320870165,
        },
        "counterfactual": {
            "sharpe": 0.5632528296738288,
            "pf": 1.1569729072245707,
            "dd": -0.3828121059705952,
            "stab": 0.7148651464033289,
            "worst": 0.32498268870960764,
            "ir": -0.2660349072071191,
            "p": 0.5525096556153159,
        },
    },
    "exp_2026-10-10T21-59-16-546117Z": {
        "control": {
            "sharpe": -0.4037945993424417,
            "pf": 0.7423116804276377,
            "dd": -1.5095951367917253,
            "stab": -0.5124851046944916,
            "worst": -1.6784412527322672,
            "ir": -0.6399266589647274,
            "p": 0.15319090320870165,
        },
        "counterfactual": {
            "sharpe": 0.5632528296738288,
            "pf": 1.1569729072245707,
            "dd": -0.3828121059705952,
            "stab": 0.7148651464033289,
            "worst": 0.32498268870960764,
            "ir": -0.2660349072071191,
            "p": 0.5525096556153159,
        },
    },
    "exp_2026-10-10T22-59-01-182037Z": {
        "control": {
            "sharpe": 0.3757006004618035,
            "pf": 1.0852012383313925,
            "dd": -0.4742574931561758,
            "stab": 0.5280342040048286,
            "worst": -1.7090749064174349,
            "ir": 0.33150832181222434,
            "p": 0.45920035161545285,
        },
        "counterfactual": {
            "sharpe": 0.3774516959703639,
            "pf": 1.0856429301743094,
            "dd": -0.4742574931561758,
            "stab": 0.5304953081960026,
            "worst": -1.7018385495922546,
            "ir": -0.41197920944771954,
            "p": 0.35768858901999106,
        },
    },
    "exp_2026-10-11T00-26-35-750834Z": {
        "control": {
            "sharpe": 0.5090151736170241,
            "pf": 1.1081174438770556,
            "dd": -0.35318281368735016,
            "stab": 0.6387045372368757,
            "worst": -1.4971257560130993,
            "ir": 0.3943394550648367,
            "p": 0.3786380296798876,
        },
        "counterfactual": {
            "sharpe": 0.5102456980086196,
            "pf": 1.1084253871445005,
            "dd": -0.35318281368735016,
            "stab": 0.6402485807211146,
            "worst": -1.4915227013988948,
            "ir": -0.28500991820648836,
            "p": 0.5245388435698296,
        },
    },
    "exp_2026-10-11T00-34-05-381535Z": {
        "control": {
            "sharpe": 0.5090151736170241,
            "pf": 1.1081174438770556,
            "dd": -0.35318281368735016,
            "stab": 0.6387045372368757,
            "worst": -1.4971257560130993,
            "ir": 0.3943394550648367,
            "p": 0.3786380296798876,
        },
        "counterfactual": {
            "sharpe": 0.5102456980086196,
            "pf": 1.1084253871445005,
            "dd": -0.35318281368735016,
            "stab": 0.6402485807211146,
            "worst": -1.4915227013988948,
            "ir": -0.28500991820648836,
            "p": 0.5245388435698296,
        },
    },
    "exp_2026-10-11T02-44-40-301520Z": {
        "control": {
            "sharpe": 0.7082311410075322,
            "pf": 1.1596363911271954,
            "dd": -0.19692757195302246,
            "stab": 0.8027342965957407,
            "worst": -2.3980682751769677,
            "ir": 0.35981069144282585,
            "p": 0.42177834933464325,
        },
        "counterfactual": {
            "sharpe": 0.7084391730935906,
            "pf": 1.1596959147960187,
            "dd": -0.1969539898353884,
            "stab": 0.8029700875197741,
            "worst": -2.3980682751769677,
            "ir": -0.3628828643247474,
            "p": 0.4178268502251785,
        },
    },
    "exp_2026-10-11T02-46-37-311994Z": {
        "control": {
            "sharpe": 0.7082311410075322,
            "pf": 1.1596363911271954,
            "dd": -0.19692757195302246,
            "stab": 0.8027342965957407,
            "worst": -2.3980682751769677,
            "ir": 0.35981069144282585,
            "p": 0.42177834933464325,
        },
        "counterfactual": {
            "sharpe": 0.7084391730935906,
            "pf": 1.1596959147960187,
            "dd": -0.1969539898353884,
            "stab": 0.8029700875197741,
            "worst": -2.3980682751769677,
            "ir": -0.3628828643247474,
            "p": 0.4178268502251785,
        },
    },
    "exp_2026-10-11T07-18-39-160945Z": {
        "control": {
            "sharpe": 0.7082311410075322,
            "pf": 1.1596363911271954,
            "dd": -0.19692757195302246,
            "stab": 0.8027342965957407,
            "worst": -2.3980682751769677,
            "ir": 0.35981069144282585,
            "p": 0.42177834933464325,
        },
        "counterfactual": {
            "sharpe": 0.7084391730935906,
            "pf": 1.1596959147960187,
            "dd": -0.1969539898353884,
            "stab": 0.8029700875197741,
            "worst": -2.3980682751769677,
            "ir": -0.3628828643247474,
            "p": 0.4178268502251785,
        },
    },
    "exp_2026-10-11T08-02-22-999214Z": {
        "control": {
            "sharpe": 0.7082311410075322,
            "pf": 1.1596363911271954,
            "dd": -0.19692757195302246,
            "stab": 0.8027342965957407,
            "worst": -2.3980682751769677,
            "ir": 0.35981069144282585,
            "p": 0.42177834933464325,
        },
        "counterfactual": {
            "sharpe": 0.7084391730935906,
            "pf": 1.1596959147960187,
            "dd": -0.1969539898353884,
            "stab": 0.8029700875197741,
            "worst": -2.3980682751769677,
            "ir": -0.3628828643247474,
            "p": 0.4178268502251785,
        },
    },
    "exp_2026-10-14T08-27-02-650342Z": {
        "control": {
            "sharpe": 0.3757006004618035,
            "pf": 1.0852012383313925,
            "dd": -0.4742574931561758,
            "stab": 0.5280342040048286,
            "worst": -1.7090749064174349,
            "ir": 0.33150832181222434,
            "p": 0.45920035161545285,
        },
        "counterfactual": {
            "sharpe": 0.3774516959703639,
            "pf": 1.0856429301743094,
            "dd": -0.4742574931561758,
            "stab": 0.5304953081960026,
            "worst": -1.7018385495922546,
            "ir": -0.41197920944771954,
            "p": 0.35768858901999106,
        },
    },
    "exp_2026-10-11T15-21-31-333870Z": {
        "control": {
            "sharpe": 0.8142482924033249,
            "pf": 1.1568339174846136,
            "dd": -0.2085072641498924,
            "stab": 0.8826959617559388,
            "worst": -1.9135756604794327,
            "ir": 0.5248619387848141,
            "p": 0.24132725822205583,
        },
        "counterfactual": {
            "sharpe": 0.8158655199246963,
            "pf": 1.157222278680081,
            "dd": -0.2085072641498924,
            "stab": 0.8844491373061012,
            "worst": -1.9030776780216773,
            "ir": -0.017530752291060953,
            "p": 0.9687744158631806,
        },
    },
}

# The published statistic keys, per producer family.  The H8 family publishes
# its numbers inside ``gate_metrics``; the other three publish them at the
# top level and their benchmark comparison inside ``alpha_vs_benchmark``.
_FLAT_KEYS = {
    "sharpe": ("oos_sharpe",),
    "pf": ("oos_pf",),
    "dd": ("oos_max_dd",),
    "stab": ("wf_stability",),
    "worst": ("worst_regime_sharpe",),
    "ir": ("alpha_vs_benchmark", "information_ratio"),
    "p": ("alpha_vs_benchmark", "p_value"),
}
PUBLISHED_KEYS = {
    "h7": _FLAT_KEYS,
    "ddcv": _FLAT_KEYS,
    "h6": _FLAT_KEYS,
    "h8": {
        "sharpe": ("gate_metrics", "oos_sharpe"),
        "pf": ("gate_metrics", "oos_pf"),
        "dd": ("gate_metrics", "oos_max_dd"),
        "stab": ("gate_metrics", "wf_stability"),
        "worst": ("gate_metrics", "worst_regime_sharpe"),
        "ir": ("gate_metrics", "information_ratio"),
        "p": ("gate_metrics", "benchmark_p_value"),
    },
}

# The three ``h7`` summaries were produced before H33 fixed the library's
# p-value key, so their published ``p_value`` is the runner's default
# (``1.0``) and their ``p`` gate never tested anything.  That is the H33
# disclosure: the published value does not re-derive and is not rewritten.
PRE_H33_FAMILIES = ("h7",)

# The gate booleans the contamination decides.
IR_FLIPS = 9
STAB_FLIPS = 2
WORST_FLIPS = 2
TOTAL_FLIPS = IR_FLIPS + STAB_FLIPS + WORST_FLIPS

# The margins of the two new flips, as a fraction of their threshold.
STAB_MARGIN = 0.7148651464033289 - GATES["min_walkforward_stability"]
WORST_MARGIN = 0.32498268870960764 - GATES["min_worst_regime_sharpe"]

# The published equity minimum of the two strategy-contaminated families:
# negative, on a long-only strategy.
STRATEGY_EQUITY_MINIMUM = -463814.8436171526

# The certified families never see the crossing.
CERTIFIED = {
    "H10": "exp_2026-10-11T17-41-18-169363Z",
    "H21": "exp_2026-10-13T23-27-52-101656Z",
    "H22": "exp_2026-10-14T18-52-08-943792Z",
    "H25": "exp_2026-10-14T20-08-34-613690Z",
}


# --------------------------------------------------------------------------- #
# helpers                                                                     #
# --------------------------------------------------------------------------- #
def _summary(artifact: str) -> dict:
    with open(ARTIFACTS / artifact / "summary.json") as handle:
        return json.load(handle)


def _equity(artifact: str, name: str) -> pd.Series:
    return pd.read_parquet(ARTIFACTS / artifact / name).iloc[:, 0]


def _returns(equity: pd.Series) -> pd.Series:
    """The engine's net returns, recovered from a committed equity curve."""
    returns = equity.pct_change()
    returns.iloc[0] = equity.iloc[0] / CAPITAL - 1.0
    return returns


def _counterfactual_equity(equity: pd.Series) -> pd.Series:
    """The counterfactual equity curve: the two sessions contribute no return.

    Zeroing the two returns removes them from the series; every later bar is
    a ratio of consecutive levels and is therefore unchanged, so the
    counterfactual is the published path with the crossing removed.
    """
    cleaned = _returns(equity).copy()
    for session in ZERO_CROSSING_SESSIONS:
        if session in cleaned.index:
            cleaned.loc[session] = 0.0
    return CAPITAL * (1.0 + cleaned).cumprod()


def _dropped_equity(equity: pd.Series) -> pd.Series:
    """A second, independent counterfactual: the two sessions are removed."""
    kept = _returns(equity)
    kept = kept[~kept.index.isin(ZERO_CROSSING_SESSIONS)]
    return CAPITAL * (1.0 + kept).cumprod()


def _regimes(vix: pd.Series) -> pd.Series:
    regimes = pd.Series(index=vix.index, dtype=object)
    filled = vix.ffill()
    regimes[filled < 20] = "bull"
    regimes[(filled >= 20) & (filled <= 30)] = "sideways"
    regimes[filled > 30] = "bear"
    return regimes


def _measure(
    artifact: str,
    family: str,
    strategy_equity: pd.Series,
    benchmark_equity: pd.Series,
) -> dict:
    """The seven published statistics and the gate booleans they decide."""
    convention = CONVENTIONS[family]
    vix = _equity(artifact, "vix_close.parquet")
    returns = _returns(strategy_equity)
    benchmark = _returns(benchmark_equity)

    train = returns[returns.index <= TRAIN_END]
    oos = returns[returns.index > TRAIN_END]
    benchmark_oos = benchmark[benchmark.index > TRAIN_END]

    sharpe = float(sharpe_ratio(oos.values)) if len(oos) else 0.0
    train_sharpe = float(sharpe_ratio(train.values)) if len(train) else 0.0

    if convention["dd"] == "percent":
        level = strategy_equity[strategy_equity.index > TRAIN_END]
        drawdown = float((level / level.expanding().max() - 1.0).min())
    else:
        level = (1.0 + oos).cumprod()
        drawdown = float((level - level.expanding().max()).min())

    gross_profit = oos[oos > 0].sum()
    gross_loss = abs(oos[oos < 0].sum())
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else np.inf

    stability = sharpe / train_sharpe if abs(train_sharpe) > 1e-18 else 0.0

    if convention["regime"] == "reindex":
        regimes = _regimes(vix.reindex(oos.index))
    else:
        regimes = _regimes(vix).loc[oos.index]
    worst = np.inf
    for label in ("bull", "sideways", "bear"):
        mask = regimes == label
        if len(mask) > 0 and mask.any():
            subset = oos[mask]
            if len(subset) > 1 and subset.std() > 0:
                worst = min(worst, float(sharpe_ratio(subset.values)))
    if worst == np.inf:
        worst = sharpe

    if convention["align"] == "tail":
        comparison = compare_to_benchmark(
            oos.values[-len(benchmark_oos) :], benchmark_oos.values
        )
    else:
        comparison = compare_to_benchmark(oos.values, benchmark_oos.values)
    information_ratio = float(comparison["information_ratio"])
    p_value = float(comparison.get("alpha_p_value", 1.0))

    gates = {
        "sharpe": bool(sharpe >= GATES["min_sharpe"]),
        "pf": bool(profit_factor >= GATES["min_profit_factor"]),
        "dd": bool(abs(drawdown) <= GATES["max_drawdown"]),
        "stab": bool(stability >= GATES["min_walkforward_stability"]),
        "worst": bool(worst >= GATES["min_worst_regime_sharpe"]),
        "p": bool(benchmark_significance_gate(p_value, information_ratio, GATES["max_p_value"])),
        "ir": bool(information_ratio > GATES["min_information_ratio"]),
    }
    return {
        "sharpe": sharpe,
        "pf": profit_factor,
        "dd": drawdown,
        "stab": stability,
        "worst": float(worst),
        "ir": information_ratio,
        "p": p_value,
        "gates": gates,
    }


def _published_statistic(artifact: str, family: str, key: str):
    """The value the summary publishes under ``key``."""
    summary = _summary(artifact)
    path = PUBLISHED_KEYS[family][key]
    value = summary
    for part in path:
        value = value[part]
    return value


def _as_bool(value) -> bool:
    """A published gate boolean, including the ones stored as text.

    Three of the four producers wrote their ``passes`` block through
    ``json.dump(..., default=str)``, so a numpy boolean reached the file as
    the *string* ``"False"`` or ``"True"``.  The strings are read back as
    booleans here; the published bytes are left alone.
    """
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


def _control(artifact: str, family: str, strategy_file: str) -> dict:
    return _measure(
        artifact,
        family,
        _equity(artifact, strategy_file),
        _equity(artifact, "benchmark_equity.parquet"),
    )


def _counterfactual(artifact: str, family: str, strategy_file: str) -> dict:
    return _measure(
        artifact,
        family,
        _counterfactual_equity(_equity(artifact, strategy_file)),
        _counterfactual_equity(_equity(artifact, "benchmark_equity.parquet")),
    )


def _dropped(artifact: str, family: str, strategy_file: str) -> dict:
    return _measure(
        artifact,
        family,
        _dropped_equity(_equity(artifact, strategy_file)),
        _dropped_equity(_equity(artifact, "benchmark_equity.parquet")),
    )


def _flips(control: dict, counterfactual: dict) -> dict[str, tuple[bool, bool]]:
    return {
        key: (control["gates"][key], counterfactual["gates"][key])
        for key in control["gates"]
        if control["gates"][key] != counterfactual["gates"][key]
    }


# --------------------------------------------------------------------------- #
# the control: the published statistics re-derive from the frozen record      #
# --------------------------------------------------------------------------- #
class TestTheControl:
    """Every published statistic of the eleven affected summaries re-derives."""

    @pytest.mark.parametrize("artifact,strategy_file,family,contaminated", AFFECTED)
    def test_every_published_statistic_re_derives(
        self, artifact, strategy_file, family, contaminated
    ):
        measured = _control(artifact, family, strategy_file)
        for key, expected in MEASURED[artifact]["control"].items():
            published = _published_statistic(artifact, family, key)
            assert measured[key] == pytest.approx(expected, rel=1e-9, abs=1e-12), (
                artifact,
                key,
            )
            if family in PRE_H33_FAMILIES and key == "p":
                continue
            assert published == pytest.approx(expected, rel=1e-9, abs=1e-12), (
                artifact,
                key,
            )

    @pytest.mark.parametrize("artifact,strategy_file,family,contaminated", AFFECTED)
    def test_the_control_reproduces_the_published_gate_booleans(
        self, artifact, strategy_file, family, contaminated
    ):
        measured = _control(artifact, family, strategy_file)
        published = _summary(artifact)["passes"]
        for key, value in measured["gates"].items():
            assert _as_bool(published[key]) == value, (artifact, key)

    def test_the_conventions_are_the_four_measured_ones(self):
        assert {family for _, _, family, _ in AFFECTED} == set(CONVENTIONS)
        assert CONVENTIONS["h8"]["dd"] == "percent"
        assert CONVENTIONS["h8"]["align"] == "tail"
        assert {CONVENTIONS[f]["dd"] for f in ("h7", "ddcv", "h6")} == {"absolute"}
        assert {CONVENTIONS[f]["align"] for f in ("h7", "ddcv", "h6")} == {None}

    def test_the_h7_family_published_a_default_p_value(self):
        """The pre-H33 library returned no ``alpha_p_value`` key.

        The four ``h7`` summaries publish ``p_value = 1.0`` -- the runner's
        default -- so their ``p`` gate never tested anything.  This is the
        H33 disclosure, not a defect of the record, and it is why the
        control's ``p`` is not the published one for that family.
        """
        for artifact, _, family, _ in AFFECTED:
            if family not in PRE_H33_FAMILIES:
                continue
            summary = _summary(artifact)
            assert summary["alpha_vs_benchmark"]["p_value"] == 1.0
            assert not _as_bool(summary["passes"]["p"])

    def test_the_other_families_publish_a_re_derivable_p_value(self):
        for artifact, strategy_file, family, _ in AFFECTED:
            if family in PRE_H33_FAMILIES:
                continue
            measured = _control(artifact, family, strategy_file)
            assert measured["p"] == pytest.approx(
                _published_statistic(artifact, family, "p"), rel=1e-9, abs=1e-12
            )


# --------------------------------------------------------------------------- #
# the blast radius                                                            #
# --------------------------------------------------------------------------- #
class TestTheBlastRadius:
    """The gates the contamination decides."""

    @pytest.mark.parametrize("artifact,strategy_file,family,contaminated", AFFECTED)
    def test_the_counterfactual_is_measured(self, artifact, strategy_file, family, contaminated):
        measured = _counterfactual(artifact, family, strategy_file)
        for key, expected in MEASURED[artifact]["counterfactual"].items():
            assert measured[key] == pytest.approx(expected, rel=1e-9, abs=1e-12), (
                artifact,
                key,
            )

    def test_the_ir_gate_flips_in_nine_summaries(self):
        flips = {
            artifact: _flips(
                _control(artifact, family, strategy_file),
                _counterfactual(artifact, family, strategy_file),
            )
            for artifact, strategy_file, family, _ in AFFECTED
        }
        ir_flips = [a for a, f in flips.items() if "ir" in f]
        assert len(ir_flips) == IR_FLIPS
        for artifact in ir_flips:
            assert flips[artifact]["ir"] == (True, False), artifact

    def test_the_stab_gate_flips_in_two_summaries(self):
        flips = {
            artifact: _flips(
                _control(artifact, family, strategy_file),
                _counterfactual(artifact, family, strategy_file),
            )
            for artifact, strategy_file, family, _ in AFFECTED
        }
        stab_flips = {a: f["stab"] for a, f in flips.items() if "stab" in f}
        assert len(stab_flips) == STAB_FLIPS
        for artifact, (before, after) in stab_flips.items():
            assert (before, after) == (False, True), artifact

    def test_the_worst_gate_flips_in_two_summaries(self):
        flips = {
            artifact: _flips(
                _control(artifact, family, strategy_file),
                _counterfactual(artifact, family, strategy_file),
            )
            for artifact, strategy_file, family, _ in AFFECTED
        }
        worst_flips = {a: f["worst"] for a, f in flips.items() if "worst" in f}
        assert len(worst_flips) == WORST_FLIPS
        for artifact, (before, after) in worst_flips.items():
            assert (before, after) == (False, True), artifact

    def test_no_other_gate_flips(self):
        flips = {
            artifact: _flips(
                _control(artifact, family, strategy_file),
                _counterfactual(artifact, family, strategy_file),
            )
            for artifact, strategy_file, family, _ in AFFECTED
        }
        for artifact, flip in flips.items():
            assert set(flip) <= {"ir", "stab", "worst"}, (artifact, flip)
        total = sum(len(flip) for flip in flips.values())
        assert total == TOTAL_FLIPS

    def test_the_two_new_flips_are_in_the_strategy_contaminated_families(self):
        contaminated = {a for a, _, _, c in AFFECTED if c}
        assert contaminated == {
            "exp_2026-10-10T21-58-28-353634Z",
            "exp_2026-10-10T21-59-16-546117Z",
        }
        for artifact in contaminated:
            flips = _flips(
                _control(artifact, "h7", "ensemble_equity.parquet"),
                _counterfactual(artifact, "h7", "ensemble_equity.parquet"),
            )
            assert set(flips) == {"stab", "worst"}, artifact

    def test_the_new_flips_are_marginal(self):
        """The honest caveat: the direction is decided, the margin is thin."""
        assert STAB_MARGIN == pytest.approx(0.014865146403328902, abs=1e-12)
        assert WORST_MARGIN == pytest.approx(0.024982688709607638, abs=1e-12)
        assert STAB_MARGIN < 0.05 * GATES["min_walkforward_stability"]
        assert WORST_MARGIN < 0.1 * GATES["min_worst_regime_sharpe"]

    def test_the_new_flips_survive_a_second_counterfactual(self):
        """Dropping the two sessions agrees with zeroing them."""
        for artifact, strategy_file, family, _ in AFFECTED:
            dropped = _flips(
                _control(artifact, family, strategy_file),
                _dropped(artifact, family, strategy_file),
            )
            zeroed = _flips(
                _control(artifact, family, strategy_file),
                _counterfactual(artifact, family, strategy_file),
            )
            assert set(dropped) == set(zeroed), artifact
            assert dropped == zeroed, artifact

    def test_the_published_max_drawdown_is_impossible(self):
        """-150.96 % of the OOS equity can only come from a negative equity."""
        for artifact in ("exp_2026-10-10T21-58-28-353634Z", "exp_2026-10-10T21-59-16-546117Z"):
            summary = _summary(artifact)
            assert summary["oos_max_dd"] < -1.0
            equity = _equity(artifact, "ensemble_equity.parquet")
            assert equity.min() == pytest.approx(STRATEGY_EQUITY_MINIMUM, abs=1e-2)
            assert equity.min() < 0.0
            measured = _counterfactual(artifact, "h7", "ensemble_equity.parquet")
            assert measured["dd"] > -1.0

    def test_no_published_verdict_moves(self):
        for artifact, _, _, _ in AFFECTED:
            summary = _summary(artifact)
            assert summary["all_pass"] is False, artifact
            assert summary.get("verdict", "REJECT") == "REJECT", artifact

    def test_the_contamination_does_not_reach_the_certified_families(self):
        affected = {artifact for artifact, _, _, _ in AFFECTED}
        for family, artifact in CERTIFIED.items():
            assert artifact not in affected, family
            panel = pd.read_parquet(ARTIFACTS / artifact / "prices.parquet")
            for timestamp in ZERO_CROSSING_SESSIONS:
                assert timestamp not in panel.index, family
            assert panel.to_numpy().min() > 0.0, family


# --------------------------------------------------------------------------- #
# the screen: every price column, not only the close                           #
# --------------------------------------------------------------------------- #
class TestTheScreenCoversEveryPriceColumn:
    """The hole the record itself demonstrates, and its closure.

    The H58 screen screened the *close* of a fetched panel.  The committed
    H8 artifact shows why that is not enough: the same WTI splice printed
    ``-14.0`` as the **open** of 2020-04-21 -- a session whose close was
    positive -- so a close-only screen declared that session clean.
    """

    ARTIFACT = "exp_2026-10-11T15-21-31-333870Z"
    SESSION = pd.Timestamp("2020-04-21")

    def _panel(self) -> pd.DataFrame:
        opens = pd.read_parquet(ARTIFACTS / self.ARTIFACT / "opens.parquet")
        prices = pd.read_parquet(ARTIFACTS / self.ARTIFACT / "prices.parquet")
        return pd.DataFrame(
            {
                "open": opens["CL=F"],
                "high": opens["CL=F"],
                "low": prices["CL=F"],
                "close": prices["CL=F"],
                "volume": [100] * len(opens),
            }
        )

    def test_the_record_carries_a_non_positive_open_on_a_positive_close(self):
        panel = self._panel()
        assert panel.loc[self.SESSION, "open"] == -14.0
        assert panel.loc[self.SESSION, "close"] > 0.0

    def test_the_close_only_screen_misses_it(self):
        """The pre-H59 screen, reconstructed: it looks at the close only."""
        panel = self._panel()
        closes = panel["close"]
        offending = closes[(closes <= 0) & closes.notna()]
        assert len(offending) == 0

    def test_the_screen_catches_the_open(self):
        panel = self._panel()
        bad = non_positive_prices(panel)
        assert len(bad) == 1
        assert bad.iloc[0]["symbol"] == "open"
        assert bad.iloc[0]["timestamp"] == self.SESSION
        assert bad.iloc[0]["price"] == -14.0

    def test_a_zero_volume_is_not_a_price(self):
        panel = pd.DataFrame(
            {
                "open": [1.0, 2.0],
                "high": [1.0, 2.0],
                "low": [1.0, 2.0],
                "close": [1.0, 2.0],
                "volume": [0, 0],
            }
        )
        assert len(non_positive_prices(panel)) == 0

    def test_the_fetcher_refuses_a_panel_with_a_non_positive_open(self, tmp_path, monkeypatch):
        import sys
        import types

        frame = pd.DataFrame(
            {
                "open": [18.27, -14.0, 10.01],
                "high": [18.27, 10.01, 10.01],
                "low": [18.27, -14.0, 10.01],
                "close": [18.27, 10.01, 10.01],
                "volume": [100, 100, 100],
            },
            index=pd.to_datetime(["2020-04-17", "2020-04-21", "2020-04-22"]),
        )

        class FakeTicker:
            def history(self, **kwargs):
                return frame

        fake_yf = types.ModuleType("yfinance")
        fake_yf.Ticker = lambda symbol: FakeTicker()
        monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

        fetcher = DataFetcher(cache=DataCache(cache_dir=tmp_path))
        with pytest.raises(ValueError, match="non-positive close"):
            fetcher.fetch_futures(["CL=F"], "2020-04-01", "2020-05-01", use_cache=False)


# --------------------------------------------------------------------------- #
# the negative controls                                                       #
# --------------------------------------------------------------------------- #
class TestTheNegativeControls:
    """The checks must fire on a record that does not have the defect."""

    def test_the_counterfactual_moves_the_statistic(self):
        artifact, strategy_file, family, _ = AFFECTED[2]
        control = _control(artifact, family, strategy_file)
        counterfactual = _counterfactual(artifact, family, strategy_file)
        assert control["ir"] != counterfactual["ir"]
        assert control["ir"] > 0.0 > counterfactual["ir"]

    def test_a_nudged_published_number_breaks_the_control(self):
        artifact, strategy_file, family, _ = AFFECTED[0]
        published = _published_statistic(artifact, family, "sharpe")
        measured = _control(artifact, family, strategy_file)["sharpe"]
        assert measured == pytest.approx(published, rel=1e-9, abs=1e-12)
        assert measured != pytest.approx(published + 1e-6, rel=1e-9, abs=1e-12)

    def test_an_uncontaminated_family_flips_no_gate(self):
        """The counterfactual machinery alone flips nothing.

        This artifact's panel carries no non-positive close, so the two
        zero-crossing sessions are ordinary bars for it: the flips the audit
        reports are caused by the contamination, not by the construction.
        """
        artifact = "exp_2026-10-10T21-08-54-188263Z"
        strategy_file = "selected_equity.parquet"
        panel = pd.read_parquet(ARTIFACTS / artifact / "prices.parquet")
        assert panel.to_numpy().min() > 0.0
        control = _measure(
            artifact,
            "h7",
            _equity(artifact, strategy_file),
            _equity(artifact, "benchmark_equity.parquet"),
        )
        counterfactual = _measure(
            artifact,
            "h7",
            _counterfactual_equity(_equity(artifact, strategy_file)),
            _counterfactual_equity(_equity(artifact, "benchmark_equity.parquet")),
        )
        assert _flips(control, counterfactual) == {}
        assert control["ir"] != counterfactual["ir"], "the counterfactual must be live"

    def test_the_verdict_is_the_expected_one(self):
        assert HYPOTHESIS == "H59"
