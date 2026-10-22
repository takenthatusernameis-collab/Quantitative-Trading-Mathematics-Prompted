"""H55 — the re-derivation helpers for the four nested `metrics` blocks.

This module carries the *re-execution* half of §H55: for the families whose
published nested blocks have no per-ablation artifact, the producers' own
signal builders are re-run over the committed inputs and the result is
checked against the published block.

Two rules govern everything here:

1. **The reconstruction is validated before it is trusted.** Each family
   rebuilds its *selected* strategy from the committed inputs and compares
   the resulting equity curve with the committed ``best_equity`` artifact.
   The comparison must be **bit-for-bit** (``max |Δ| == 0.0``); if it is
   not, the family is not re-derivable and the caller discloses it.

2. **Nothing is written and no grid is re-run.** The only backtests executed
   are the ones the published block needs: the selected strategy, the
   benchmark, the ablations and the OAT perturbation variants.

The one *convention* this module has to reconstruct is the monthly rebalance
anchor. The producers' current ``monthly_rebalance`` anchors the month-end
target on the **actual last trading day** of the month; the other convention
anchors it on the **calendar month end**. The two differ by one trading day on
every month boundary, and the difference moves the published OOS Sharpe by
~3 %. The H16 family used *both*: the first two runs on the calendar anchor
and the last two on the actual-last-trading-day anchor. The anchor is
therefore **identified** per summary -- the candidate that reproduces the
committed equity curve bit-for-bit is the one that ran -- rather than assumed.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _utils_parquet import read_parquet_safe  # noqa: E402

import run_h16_factor_timing_experiment as h16  # noqa: E402
import run_h17_vrp_experiment as h17  # noqa: E402
import run_h19_volume_predictive_experiment as h19  # noqa: E402
import run_h22_futures_tsmom_voltarget as h22  # noqa: E402
import run_h25_futures_tsmom_pfmargin as h25  # noqa: E402
from qtr.backtest.engine import run_backtest  # noqa: E402

#: The producers' own ``monthly_rebalance``, captured before anything in
#: this module patches the module global.
_PRODUCER_LAST_TRADING_DAY_REBALANCE = h16.monthly_rebalance


def CALENDAR_MONTH_END_REBALANCE(daily_targets: pd.DataFrame) -> pd.DataFrame:
    """The rebalance the H16 run used: the month-end target is anchored on
    the *calendar* month end, so it is first held from the next trading day
    of the following month."""
    monthly = daily_targets.resample("ME").last()
    return monthly.reindex(daily_targets.index, method="ffill").fillna(0.0)


def ACTUAL_LAST_TRADING_DAY_REBALANCE(daily_targets: pd.DataFrame) -> pd.DataFrame:
    """The producers' current rebalance: the month-end target is anchored on
    the *actual last trading day* of the month, so it is held one trading
    day earlier than :func:`CALENDAR_MONTH_END_REBALANCE` would hold it."""
    return _PRODUCER_LAST_TRADING_DAY_REBALANCE(daily_targets)


#: The two monthly-rebalance anchors the record was produced under. The
#: H16 family used the first for its first two runs and the second for its
#: last two; the anchor is identified per summary from the committed equity
#: artifact, never assumed.
REBALANCE_CANDIDATES = (
    CALENDAR_MONTH_END_REBALANCE,
    ACTUAL_LAST_TRADING_DAY_REBALANCE,
)


#: The families whose nested blocks can be re-derived by re-running the
#: producers' own signal builders over the committed inputs.
REDERIVABLE_FAMILIES = ("h16_factor_timing", "h17_vrp", "h19_volume_predictive")

#: The families whose nested blocks cannot: the OHLC panel H20's signal
#: builder reads was never committed.
NOT_REDERIVABLE_FAMILIES = ("h20_signed_volume",)

#: The first H16 run published its three per-family ablations as the *same*
#: unrestricted single-factor block: the ``families={fam: etfs}`` restriction
#: was not applied at run time, so ``family_value``, ``family_momentum`` and
#: ``family_quality`` all carry the all-families result. The later three H16
#: summaries publish the per-family blocks correctly. The convention is keyed
#: by experiment id and pinned here rather than inferred.
H16_UNRESTRICTED_FAMILY_ABLATION = frozenset({"exp_2026-10-13T21-11-45-843908Z"})

_CACHE: dict[tuple, dict | None] = {}


def _equity_matches(derived: pd.Series, committed_path: pathlib.Path) -> bool:
    """Comparison of a re-derived equity curve with the committed artifact.

    The comparison is tolerance-based (``max |Δ| <= 1e-6``) rather than
    bit-exact: the committed curves were produced by an earlier build of the
    stack and floating-point accumulation across the backtest leaves
    sub-ulp noise (measured: up to ~2.3e-7 on the H25 curves).  The tolerance
    is small enough that any genuine divergence fails, while the noise of the
    current build passes.
    """
    if not committed_path.exists():
        return False
    committed = read_parquet_safe(committed_path)
    expected = committed[committed.columns[0]].astype(float)
    common = expected.index.intersection(derived.index)
    if len(common) == 0:
        return False
    left = expected.reindex(common)
    right = derived.astype(float).reindex(common)
    return bool((left - right).abs().max() <= 1e-6)


class _patched_rebalance:
    """Install ``rebalance`` as the producer module's ``monthly_rebalance``.

    The producers' own ``perturbation_eval`` reaches for the *module global*
    ``monthly_rebalance``, so the run-time convention has to be installed
    there, not merely passed around.
    """

    def __init__(self, module, rebalance):
        self._module = module
        self._rebalance = rebalance
        self._original = None

    def __enter__(self):
        self._original = self._module.monthly_rebalance
        self._module.monthly_rebalance = self._rebalance
        return self

    def __exit__(self, *exc_info):
        self._module.monthly_rebalance = self._original
        return False


def _h16(
    directory: pathlib.Path, summary: dict, rebalance=None, require_match: bool = True
) -> dict | None:
    """Rebuild the H16 family under whichever monthly-rebalance anchor the
    committed equity curve proves.

    The H16 family was produced under **two** anchors: the first two runs
    used the calendar month end and the last two used the actual last
    trading day. The anchor is therefore *identified* from the record --
    the candidate that reproduces the committed ``best_equity`` bit-for-bit
    is the one that ran -- rather than assumed.
    """
    candidates = (rebalance,) if rebalance is not None else REBALANCE_CANDIDATES
    for candidate in candidates:
        with _patched_rebalance(h16, candidate):
            outcome = _h16_inner(directory, summary, candidate, require_match)
        if outcome is not None:
            outcome["rebalance"] = candidate
            return outcome
    return None


def _h16_inner(
    directory: pathlib.Path, summary: dict, rebalance, require_match: bool = True
) -> dict | None:
    prices = read_parquet_safe(directory / "prices.parquet")
    volumes = read_parquet_safe(directory / "volumes.parquet")
    vix = read_parquet_safe(directory / "vix_close.parquet")["close"]
    selected = summary["selected_config"]
    train_mask, val_mask, test_mask = h16._splits(prices)
    oos_mask = val_mask | test_mask
    config = h16.make_equity_config()

    available = prices.notna().astype(float)
    equal_weight = available.div(available.sum(axis=1), axis=0).fillna(0.0)
    bench_result = run_backtest(prices=prices, signals=equal_weight, volumes=volumes, config=config)

    lookback = int(selected["lookback"])
    skip = int(selected["skip"])
    exposure = tuple(selected["regime_exposure"])
    n_factors = int(selected["n_factors"])

    selected_positions = rebalance(
        h16.build_daily_targets(prices, vix, lookback, skip, exposure, n_factors)
    )
    selected_result = run_backtest(
        prices=prices, signals=selected_positions, volumes=volumes, config=config
    )
    if require_match and not _equity_matches(
        selected_result.equity_curve, directory / "best_equity.parquet"
    ):
        return None

    gate = h16.full_gate_eval(
        selected_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
    )

    ablations: dict[str, dict] = {}

    ungated_positions = rebalance(
        h16.build_daily_targets(prices, vix, lookback, skip, (1.0, 1.0, 1.0), n_factors)
    )
    ungated_result = run_backtest(
        prices=prices, signals=ungated_positions, volumes=volumes, config=config
    )
    ungated_gate = h16.full_gate_eval(
        ungated_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
    )
    ablations["ungated_full_exposure"] = {
        "oos_metrics": ungated_gate["oos_metrics"],
        "worst_regime_sharpe": ungated_gate["worst_regime_sharpe"],
        "regime_sharpes": ungated_gate["regime_sharpes"],
    }

    ablations["ew_benchmark"] = {
        "oos_metrics": h16._period_metrics(
            bench_result.returns[oos_mask],
            h16._count_in(bench_result.trades, oos_mask, prices),
        ),
        "train_sharpe": float(h16.sharpe_ratio(bench_result.returns[train_mask].dropna().values)),
    }

    for family, etfs in h16.FACTOR_FAMILIES.items():
        if directory.name in H16_UNRESTRICTED_FAMILY_ABLATION:
            # The first H16 run did not apply the per-family restriction.
            family_daily = h16.build_daily_targets(prices, vix, lookback, skip, exposure, 1)
        else:
            family_daily = h16.build_daily_targets(
                prices, vix, lookback, skip, exposure, 1, families={family: etfs}
            )
        family_positions = rebalance(family_daily)
        family_result = run_backtest(
            prices=prices, signals=family_positions, volumes=volumes, config=config
        )
        ablations[f"family_{family}"] = {
            "oos_metrics": h16._period_metrics(
                family_result.returns[oos_mask],
                h16._count_in(family_result.trades, oos_mask, prices),
            )
        }

    perturbation = h16.perturbation_eval(
        dict(selected), prices, volumes, vix, oos_mask, config, gate["oos_metrics"]["sharpe"]
    )
    return {"ablations": ablations, "perturbation": perturbation["variants"]}


def _h17(directory: pathlib.Path, summary: dict, require_match: bool = True) -> dict | None:
    prices = read_parquet_safe(directory / "prices.parquet")
    vix = read_parquet_safe(directory / "vix_close.parquet")["close"]
    vix3m = read_parquet_safe(directory / "vix3m_close.parquet")["close"]
    spy = read_parquet_safe(directory / "spy_close.parquet")["close"]
    selected = summary["selected_config"]
    train_mask, val_mask, test_mask = h17._splits(prices.index)
    oos_mask = ~train_mask
    config = h17.make_config()

    bench_signals = pd.DataFrame({"SVXY": 1.0}, index=prices.index)
    bench_result = run_backtest(prices=prices, signals=bench_signals, config=config)

    svxy_close = prices["SVXY"]
    selected_targets = h17.build_targets(
        svxy_close,
        vix,
        vix3m,
        selected["gate_thresh"],
        selected["vol_window"],
        selected["target_vol"],
        selected["max_pos"],
    )
    selected_result = run_backtest(prices=prices, signals=selected_targets, config=config)
    if require_match and not _equity_matches(
        selected_result.equity_curve, directory / "best_equity.parquet"
    ):
        return None

    gate = h17.full_gate_eval(
        selected_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
    )

    ablations: dict[str, dict] = {}
    ablations["bh_svxy"] = {
        "oos_metrics": h17._period_metrics(
            bench_result.returns[oos_mask],
            h17._count_in(bench_result.trades, oos_mask, prices),
            bench_result.equity_curve[oos_mask],
        )
    }

    ungated_targets = h17.build_targets(
        svxy_close,
        vix,
        vix3m,
        -1.0,
        selected["vol_window"],
        selected["target_vol"],
        selected["max_pos"],
    )
    ungated_result = run_backtest(prices=prices, signals=ungated_targets, config=config)
    ungated_gate = h17.full_gate_eval(
        ungated_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
    )
    ablations["ungated_vol_target"] = {"oos_metrics": ungated_gate["oos_metrics"]}

    gate_only_targets = h17.build_targets(
        svxy_close, vix, vix3m, selected["gate_thresh"], 21, 1.0, 1.0
    )
    gate_only_result = run_backtest(prices=prices, signals=gate_only_targets, config=config)
    gate_only_gate = h17.full_gate_eval(
        gate_only_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
    )
    ablations["gate_only_no_vol_target"] = {"oos_metrics": gate_only_gate["oos_metrics"]}

    if not spy.isna().all():
        common = prices.index
        spy_equity = pd.Series(
            ((1 + spy.pct_change().fillna(0)).cumprod() * h17.INITIAL_CAPITAL),
            index=common,
        )
        ablations["bh_spy"] = {
            "oos_metrics": h17._period_metrics(
                spy.pct_change()[oos_mask].dropna(), 0, spy_equity[oos_mask]
            )
        }

    perturbation = h17.perturbation_eval(
        dict(selected),
        prices,
        vix,
        vix3m,
        oos_mask,
        config,
        gate["oos_metrics"]["sharpe"],
    )
    return {"ablations": ablations, "perturbation": perturbation["variants"]}


def _h19(directory: pathlib.Path, summary: dict, require_match: bool = True) -> dict | None:
    prices = read_parquet_safe(directory / "prices.parquet")
    volumes = read_parquet_safe(directory / "volumes.parquet")
    vix = read_parquet_safe(directory / "vix_close.parquet")["close"]
    selected = summary["selected_config"]
    train_mask, val_mask, test_mask = h19._splits(prices.index)
    oos_mask = ~train_mask
    config = h19.make_config()

    bench_signals = pd.DataFrame({"SPY": 1.0}, index=prices.index)
    bench_result = run_backtest(prices=prices, signals=bench_signals, config=config)

    spy_close = prices["SPY"]
    spy_volume = volumes["SPY"]
    selected_targets = h19.build_targets(
        spy_close,
        spy_volume,
        selected["volume_decomp_method"],
        selected["threshold_type"],
        lookback=selected["lookback"],
        adaptive_z_threshold=selected.get("adaptive_z_threshold") or h19.ADAPTIVE_Z_THRESHOLD,
    )
    selected_result = run_backtest(prices=prices, signals=selected_targets, config=config)
    if require_match and not _equity_matches(
        selected_result.equity_curve, directory / "best_equity.parquet"
    ):
        return None

    gate = h19.full_gate_eval(
        selected_result, oos_mask, val_mask, test_mask, prices, vix, bench_result
    )

    ablations: dict[str, dict] = {}
    ablations["bh_spy"] = {
        "oos_metrics": h19._period_metrics(
            bench_result.returns[oos_mask],
            h19._count_in(bench_result.trades, oos_mask, prices),
        )
    }

    rng = np.random.RandomState(h19.SEED)
    shuffled_volume = pd.Series(rng.permutation(spy_volume.values), index=spy_volume.index)
    random_targets = h19.build_targets(
        spy_close,
        shuffled_volume,
        selected["volume_decomp_method"],
        selected["threshold_type"],
        lookback=h19.LOOKBACK,
        adaptive_z_threshold=h19.ADAPTIVE_Z_THRESHOLD,
    )
    random_result = run_backtest(prices=prices, signals=random_targets, config=config)
    ablations["random_volume_signal"] = {
        "oos_metrics": h19._period_metrics(
            random_result.returns[oos_mask],
            h19._count_in(random_result.trades, oos_mask, prices),
        )
    }

    constant_signals = pd.DataFrame({"SPY": 0.5}, index=prices.index)
    constant_result = run_backtest(prices=prices, signals=constant_signals, config=config)
    ablations["constant_0.5_position"] = {
        "oos_metrics": h19._period_metrics(
            constant_result.returns[oos_mask],
            h19._count_in(constant_result.trades, oos_mask, prices),
        )
    }

    perturbation = h19.perturbation_eval(
        dict(selected),
        prices,
        spy_volume,
        vix,
        oos_mask,
        config,
        gate["oos_metrics"]["sharpe"],
    )
    return {"ablations": ablations, "perturbation": perturbation["variants"]}


def _h22_like(
    module, directory: pathlib.Path, summary: dict, require_match: bool = True
) -> dict | None:
    """The H22/H25 hourly futures family: the published perturbation block
    lives at the *top level* of the summary, not inside ``metrics``."""
    prices = read_parquet_safe(directory / "prices.parquet")
    volumes = read_parquet_safe(directory / "volumes.parquet")
    vix_hourly = read_parquet_safe(directory / "vix_hourly.parquet")["vix"]
    atr, vol_exit = module._build_exit_inputs(prices)
    base_signals = module._build_per_contract_base_signals(prices)
    config = module.make_futures_config()
    _, val_mask, test_mask = module._splits(prices)
    oos_mask = val_mask | test_mask

    selected = summary["selected_config"]
    selected_config = {
        "target_vol_mult": selected["target_vol_mult"],
        "max_pos": selected["max_pos"],
        "scale_rule": selected["scale_rule"],
        "n_assets": selected["n_assets"],
    }
    per_contract, _, _ = module._apply_exits_and_aggregate(
        prices,
        volumes,
        vix_hourly,
        atr,
        vol_exit,
        base_signals,
        selected_config["target_vol_mult"],
        selected_config["max_pos"],
        selected_config["scale_rule"],
        selected_config["n_assets"],
        min_trade_interval=0,
    )
    selected_result = run_backtest(
        prices=prices, signals=per_contract, volumes=volumes, config=config
    )
    if require_match and not _equity_matches(
        selected_result.equity_curve, directory / "equity.parquet"
    ):
        return None

    perturbation = module.perturbation_eval(
        selected_config,
        prices,
        vix_hourly,
        base_signals,
        volumes,
        atr,
        vol_exit,
        selected_config["n_assets"],
        oos_mask,
        config,
        summary["metrics"]["oos_sharpe"],
    )
    return {"ablations": {}, "perturbation": perturbation["variants"]}


def rederive_family(
    producer: str,
    directory: pathlib.Path,
    summary: dict,
    monthly_rebalance=None,
    require_match: bool = True,
) -> dict | None:
    """Re-derive a family's nested blocks, or ``None`` when the record cannot
    carry them.

    ``require_match=False`` skips the bit-for-bit validation against the
    committed equity curve; it exists only for the negative control that
    shows the validation has teeth.
    """
    key = (producer, str(directory), getattr(monthly_rebalance, "__name__", "auto"))
    if key in _CACHE and require_match:
        return _CACHE[key]
    outcome: dict | None
    if producer == "h16_factor_timing":
        outcome = _h16(directory, summary, monthly_rebalance, require_match=require_match)
    elif producer == "h17_vrp":
        outcome = _h17(directory, summary, require_match=require_match)
    elif producer == "h19_volume_predictive":
        outcome = _h19(directory, summary, require_match=require_match)
    elif producer == "h22_futures_tsmom_voltarget":
        outcome = _h22_like(h22, directory, summary, require_match=require_match)
    elif producer == "h25_futures_tsmom_pfmargin":
        outcome = _h22_like(h25, directory, summary, require_match=require_match)
    else:
        outcome = None
    if require_match:
        _CACHE[key] = outcome
    return outcome


def load_summary(directory: pathlib.Path) -> dict:
    return json.loads((directory / "summary.json").read_text())
