#!/usr/bin/env python3
"""H57 — the equity record is on a **price-return** basis: dividend/distribution gap,
level bars booked as losses, and the benchmark-significance statistics that depend on it.

Pre-registered in ``HYPOTHESIS_SPEC.md`` §H57 (2026-10-22, before execution).

This is an **audit of the committed record**, not a new hypothesis and not a new
selection: no strategy is re-run, no grid is re-run, no gate, threshold, verdict or
certified number is changed, and nothing is written outside the H57 artifact
directory. Everything it reports is a **disclosure**.

What it measures
----------------

1. **The convention.** Every runner builds its price series from the vendor's raw
   ``close`` and never from the vendor's total-return column ``adj_close``, which the
   fetcher commits into the same cache file (``src/qtr/data/fetcher.py:120-129``).
   Every equity return series in the record is therefore a *price* return.
2. **The gap.** Per symbol, the annualised total-return excess over the committed
   window, from ``close`` vs ``adj_close`` in the committed cache.
3. **The level bars.** The bars where the raw close and the total-return series
   disagree: a distribution ex-date is booked as a loss by every return series built
   on the raw close.
4. **The decision-relevant counterfactual.** For each audited family the published
   benchmark comparison is reproduced from the committed artifacts (the *control*),
   then recomputed with the strategy and the benchmark on the total-return basis.

Run: ``python run_h57_total_return_audit.py``
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from qtr.validation.statistics import compare_to_benchmark, sharpe_ratio  # noqa: E402

CACHE_DIR = ROOT / ".cache" / "data"
ARTIFACTS = ROOT / ".experiments" / "artifacts"
ART_DIR = ARTIFACTS / "h57_total_return"

# A bar whose implied distribution exceeds this fraction of the price is a
# "corporate-action bar": the raw close moved, the total-return series did not.
CORPORATE_ACTION_FRAC = 0.01
# A price move larger than this on a corporate-action bar is a *level* bar.
LEVEL_BAR_FRAC = 0.10
# The published benchmark-significance gate's threshold (PROMPT_V2, every family).
GATE_P_VALUE = 0.05


# --------------------------------------------------------------------------- #
# 1. The cache index                                                          #
# --------------------------------------------------------------------------- #
def cache_key(source: str, symbol: str, start: str, end: str, interval: str) -> str:
    """The cache key, identical to ``qtr.data.fetcher.DataCache._cache_key``."""
    key = f"{source}:{symbol}:{start}:{end}:{interval}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _runner_tokens() -> tuple[set[str], set[str], set[str]]:
    """The symbols, dates and intervals that appear in the runners' source."""
    symbols: set[str] = set()
    dates: set[str] = set()
    intervals: set[str] = set()
    for path in sorted(ROOT.glob("run_*.py")):
        text = path.read_text(encoding="utf-8")
        for token in re.findall(r'"([^"\n]{1,12})"', text):
            # A symbol may carry a digit (``^VIX3M``); the equity grammar is
            # "one leading letter, up to five more letters or digits, an
            # optional ``=F`` futures suffix".
            if re.fullmatch(r"\^?[A-Z][A-Z0-9]{0,5}(=F)?", token):
                symbols.add(token)
            elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
                dates.add(token)
            elif token in {"1d", "1h", "1m", "5m", "15m", "30m", "1wk", "1mo"}:
                intervals.add(token)
    return symbols, dates, intervals


def index_cache() -> dict[str, dict]:
    """Map every committed cache file to the request that produced it.

    The mapping is recomputed from the runners' own source tokens, so it is
    deterministic and offline: no network, no data download.
    """
    symbols, dates, intervals = _runner_tokens()
    files = {p.stem: p for p in sorted(CACHE_DIR.glob("*.parquet"))}
    index: dict[str, dict] = {}
    # Every loop is over a *sorted* sequence: the index is read back by
    # :func:`load_cached`, which breaks ties between equally covering cache
    # files, and a tie broken by a set's iteration order would make the
    # audit's numbers depend on the process's hash seed.
    for symbol in sorted(symbols):
        for start in sorted(dates):
            for end in sorted(dates):
                for interval in sorted(intervals or {"1d"}):
                    for source in ("yahoo", "yahoo_futures", "ccxt"):
                        key = cache_key(source, symbol, start, end, interval)
                        path = files.get(key)
                        if path is not None and key not in index:
                            index[key] = {
                                "file": path.name,
                                "source": source,
                                "symbol": symbol,
                                "start": start,
                                "end": end,
                                "interval": interval,
                            }
    return index


def symbol_frames(index: dict[str, dict]) -> dict[str, list[dict]]:
    """Group the cache index by symbol."""
    by_symbol: dict[str, list[dict]] = {}
    for entry in index.values():
        by_symbol.setdefault(entry["symbol"], []).append(entry)
    return by_symbol


def cache_coverage(index: dict[str, dict]) -> dict:
    """How much of the committed cache the index reaches.

    The index is rebuilt from the runners' own source tokens, so a cache file
    whose request cannot be reconstructed from a literal in a runner stays out
    of it. The crypto files are in that position: the CCXT path keys its
    cache on ``ccxt:{exchange_id}:{SYMBOL_PAIR}``, a token the equity
    grammar does not match. They carry no distribution either -- a crypto
    spot series has no ex-date -- so they are outside H57's question, but the
    count is reported rather than left silent.
    """
    on_disk = {p.stem for p in CACHE_DIR.glob("*.parquet")}
    indexed = set(index)
    return {
        "n_cache_files_on_disk": len(on_disk),
        "n_cache_files_indexed": len(indexed),
        "n_cache_files_not_indexed": len(on_disk - indexed),
    }


def load_cached(
    symbol: str, entries: list[dict], index: pd.DatetimeIndex
) -> tuple[pd.DataFrame, dict] | tuple[None, None]:
    """The cached frame for ``symbol`` that best covers ``index``.

    Several cache files can exist for one symbol (different windows). The one with
    the largest overlap with the artifact's index is used; its *ratios* are
    window-independent, so the window only has to cover the bars that are used.

    The choice is **deterministic**: the overlap comes first, then the longer
    frame, then the file name. The last two tie-breaks matter because several
    windows cover the same index equally well, and the vendor's adjustment
    factors differ slightly between fetches -- an arbitrary pick would make
    the audit's numbers depend on the order the files were read in.
    """
    best = None
    best_entry = None
    best_key = (-1, -1, "")
    for entry in sorted(entries, key=lambda e: e["file"]):
        frame = pd.read_parquet(CACHE_DIR / entry["file"])
        overlap = len(index.intersection(frame.index))
        key = (overlap, len(frame), entry["file"])
        if key > best_key:
            best, best_entry, best_key = frame, entry, key
    if best is None or best_key[0] <= 0:
        return None, None
    return best, best_entry


# --------------------------------------------------------------------------- #
# 2. The dividend / distribution profile of a price series                    #
# --------------------------------------------------------------------------- #
def implied_dividends(close: pd.Series, adj_close: pd.Series) -> pd.Series:
    """The per-bar implied distribution implied by ``close`` and ``adj_close``.

    Yahoo's adjusted close satisfies ``adj_t / adj_{t-1} = (close_t + d_t) / close_{t-1}``
    (the dividend is added back on the ex-date), so

        ``d_t = close_{t-1} - close_t * adj_{t-1} / adj_t``.

    The ratio ``adj_t / adj_{t-1}`` depends only on the distribution at ``t``, so it
    is the same in any window that covers ``t`` and ``t-1``.
    """
    close = close.astype(float)
    adj_close = adj_close.astype(float)
    prev_close = close.shift(1)
    prev_adj = adj_close.shift(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        dividend = prev_close - close * (prev_adj / adj_close)
    return dividend.replace([np.inf, -np.inf], np.nan)


def distribution_profile(close: pd.Series, adj_close: pd.Series) -> dict:
    """Measure the total-return gap and the corporate-action bars of one series."""
    close = close.astype(float)
    adj_close = adj_close.astype(float)
    dividend = implied_dividends(close, adj_close)
    with np.errstate(divide="ignore", invalid="ignore"):
        total_return = adj_close.pct_change()
    price_return = close.pct_change()
    gap = (dividend / close.shift(1)).replace([np.inf, -np.inf], np.nan)

    corporate = gap.abs() > CORPORATE_ACTION_FRAC
    level = corporate & (price_return.abs() > LEVEL_BAR_FRAC)

    years = (close.index[-1] - close.index[0]).days / 365.25 if len(close) > 1 else np.nan
    price_total = close.iloc[-1] / close.iloc[0] if len(close) > 1 else np.nan
    total_total = adj_close.iloc[-1] / adj_close.iloc[0] if len(close) > 1 else np.nan
    if years and years > 0 and price_total > 0 and total_total > 0:
        annual_gap = float((total_total / price_total) ** (1.0 / years) - 1.0)
    else:
        annual_gap = float("nan")

    bars = []
    for ts in close.index[corporate.fillna(False)]:
        bars.append(
            {
                "date": str(ts)[:10],
                "price_return": float(price_return.at[ts]),
                "total_return": float(total_return.at[ts]),
                "implied_distribution_per_share": float(dividend.at[ts]),
                "distribution_frac_of_price": float(gap.at[ts]),
                "level_bar": bool(level.at[ts]),
            }
        )
    return {
        "n_bars": int(len(close)),
        "first": str(close.index[0])[:10],
        "last": str(close.index[-1])[:10],
        "annualised_total_return_excess": annual_gap,
        "total_distribution_frac": float(gap.sum()),
        "n_corporate_action_bars": int(corporate.sum()),
        "n_level_bars": int(level.sum()),
        "corporate_action_bars": bars,
    }


# --------------------------------------------------------------------------- #
# 3. The families under audit                                                 #
# --------------------------------------------------------------------------- #
# The OOS window is the family's own ``index > TRAIN_END`` split, cited to the
# runner that defines it. ``max_leverage`` / ``max_position_size`` / ``allow_short``
# are the engine constraints of the *selected* configuration, cited to the runner.
# ``benchmark`` is the benchmark's construction, cited to the runner:
#   * ``equal_weight`` -- the equal-weight buy-and-hold over the family's price
#     columns (the weights are target weights, so the portfolio return of a bar is
#     the mean of the symbols' returns on that bar);
#   * ``single`` -- the buy-and-hold of one symbol.
FAMILIES = [
    {
        "hypothesis": "H1",
        "runner": "run_ts_momentum_experiment.py",
        "artifact": "exp_2026-10-10T21-08-54-188263Z",
        "oos_start": "2020-01-01",
        "strategy_equity": "selected_equity.parquet",
        "benchmark_equity": "benchmark_equity.parquet",
        "benchmark_returns": None,
        "max_leverage": 5.0,
        "max_position_size": 2.0,
        "allow_short": False,
        "benchmark": {"kind": "equal_weight"},
    },
    {
        "hypothesis": "H3",
        "runner": "run_regime_gated_momentum_experiment.py",
        "artifact": "exp_2026-10-10T21-27-13-928282Z",
        "oos_start": "2020-01-01",
        "strategy_equity": "selected_equity.parquet",
        "benchmark_equity": "benchmark_equity.parquet",
        "benchmark_returns": None,
        "max_leverage": 5.0,
        "max_position_size": 2.0,
        "allow_short": True,
        "benchmark": {"kind": "equal_weight"},
    },
    {
        "hypothesis": "H16",
        "runner": "run_h16_factor_timing_experiment.py",
        "artifact": "exp_2026-10-13T21-11-45-843908Z",
        "oos_start": "2018-01-01",
        "strategy_equity": "best_equity.parquet",
        "benchmark_equity": "benchmark_equity.parquet",
        "benchmark_returns": "benchmark_returns.parquet",
        "max_leverage": 1.0,
        "max_position_size": 1.0,
        "allow_short": False,
        "benchmark": {"kind": "equal_weight"},
    },
    {
        "hypothesis": "H17",
        "runner": "run_h17_vrp_experiment.py",
        "artifact": "exp_2026-10-13T21-51-45-034237Z",
        "oos_start": "2020-01-01",
        "strategy_equity": "best_equity.parquet",
        "benchmark_equity": "benchmark_equity.parquet",
        "benchmark_returns": "benchmark_returns.parquet",
        "max_leverage": 1.0,
        "max_position_size": 1.0,
        "allow_short": True,
        "benchmark": {"kind": "single", "symbol": "SVXY"},
    },
    {
        "hypothesis": "H19",
        "runner": "run_h19_volume_predictive_experiment.py",
        "artifact": "exp_2026-10-13T22-40-41-870350Z",
        "oos_start": "2015-01-01",
        "strategy_equity": "best_equity.parquet",
        "benchmark_equity": "benchmark_equity.parquet",
        "benchmark_returns": "benchmark_returns.parquet",
        "max_leverage": 1.0,
        "max_position_size": 1.0,
        "allow_short": True,
        "benchmark": {"kind": "single", "symbol": "SPY"},
    },
    {
        "hypothesis": "H20",
        "runner": "run_h20_signed_volume_experiment.py",
        "artifact": "exp_2026-10-13T23-06-33-191710Z",
        "oos_start": "2015-01-01",
        "strategy_equity": "best_equity.parquet",
        "benchmark_equity": "benchmark_equity.parquet",
        "benchmark_returns": "benchmark_returns.parquet",
        "max_leverage": 1.0,
        "max_position_size": 1.0,
        "allow_short": True,
        "benchmark": {"kind": "single", "symbol": "SPY"},
    },
]


def engine_positions(
    signals: pd.DataFrame,
    max_leverage: float,
    max_position_size: float,
    allow_short: bool,
) -> pd.DataFrame:
    """The positions the engine would use, mirroring ``engine.py:148-165``.

    The engine forward-fills the signals, normalises any row whose gross
    leverage exceeds the cap, clips each position to the per-asset cap and
    (when shorting is not allowed) clips the negatives away. Reproducing this
    exactly is what lets the audit recover the *engine's* positions from the
    logged signals for the two families that log pre-engine signals.
    """
    signals = signals.ffill().fillna(0.0)
    gross_leverage = signals.abs().sum(axis=1)
    over_leverage = gross_leverage > max_leverage
    if over_leverage.any():
        signals.loc[over_leverage] = (
            signals.loc[over_leverage].div(gross_leverage[over_leverage], axis=0) * max_leverage
        )
    signals = signals.clip(-max_position_size, max_position_size)
    if not allow_short:
        signals = signals.clip(lower=0.0)
    return signals


def published_comparison(summary: dict) -> dict:
    """The published information ratio / alpha / p-value, from any summary shape."""
    block = summary.get("benchmark_comparison")
    if isinstance(block, dict) and block:
        return {
            "information_ratio": block.get("information_ratio"),
            "alpha_p_value": block.get("alpha_p_value"),
            "alpha_annualized": block.get("alpha_annualized"),
        }
    metrics = summary.get("metrics") or {}
    return {
        "information_ratio": metrics.get("information_ratio"),
        "alpha_p_value": metrics.get("benchmark_p_value"),
        "alpha_annualized": metrics.get("benchmark_alpha_annual"),
    }


def published_strategy_metrics(summary: dict) -> dict:
    """The published OOS Sharpe / profit factor / max drawdown."""
    block = summary.get("oos_metrics")
    if isinstance(block, dict) and block:
        return {
            "sharpe": block.get("sharpe", block.get("oos_sharpe")),
            "profit_factor": block.get("profit_factor"),
            "max_drawdown": block.get("max_drawdown"),
        }
    metrics = summary.get("metrics") or {}
    return {
        "sharpe": metrics.get("oos_sharpe"),
        "profit_factor": metrics.get("profit_factor"),
        "max_drawdown": metrics.get("max_drawdown"),
    }


def _period_metrics(returns: pd.Series) -> dict:
    """Sharpe, max drawdown and profit factor of a return series.

    The formulas are the ones the runners use (``_period_metrics`` in
    ``run_h19_volume_predictive_experiment.py:192-211``): the library's
    ``sharpe_ratio`` (mean/std with ddof=0, annualised by sqrt(252)), the
    drawdown of the compounded series, and gross profit over gross loss.
    """
    r = returns.dropna()
    if len(r) == 0:
        return {"sharpe": float("nan"), "profit_factor": float("nan"), "max_drawdown": float("nan")}
    cum = (1 + r).cumprod()
    drawdown = (cum / cum.cummax() - 1.0).min()
    gross_profit = float(r[r > 0].sum())
    gross_loss = float(abs(r[r < 0].sum()))
    return {
        "sharpe": float(sharpe_ratio(r.to_numpy())),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "max_drawdown": float(drawdown),
    }


def published_significance_gate(summary: dict) -> dict:
    """The published benchmark-significance gate, in the shape the family used.

    Two families publish the gate itself (a ``pass`` boolean and its
    threshold); the rest publish only the p-value it is built on. The
    published rule is **direction-blind** (``p < threshold``): H33/H34 already
    disclosed that the direction-aware rule (``p < threshold AND IR > 0``)
    is the one the library applies now, and that the three families carrying
    a ``p`` PASS all have a *negative* alpha.
    """
    gates = summary.get("gates") or {}
    block = gates.get("benchmark_significance")
    if isinstance(block, dict):
        return {
            "gate_block_published": True,
            "value": block.get("value"),
            "threshold": block.get("threshold", GATE_P_VALUE),
            "pass": block.get("pass"),
            "information_ratio": block.get("information_ratio"),
        }
    metrics = summary.get("metrics") or {}
    if "benchmark_p_value" in metrics:
        return {
            "gate_block_published": False,
            "value": metrics.get("benchmark_p_value"),
            "threshold": GATE_P_VALUE,
            "pass": None,
            "information_ratio": metrics.get("information_ratio"),
        }
    return {
        "gate_block_published": False,
        "value": None,
        "threshold": GATE_P_VALUE,
        "pass": None,
        "information_ratio": None,
    }


def published_verdict(summary: dict) -> dict:
    """The family's published verdict, in the shape it published it."""
    return {
        "verdict": summary.get("verdict"),
        "all_pass": summary.get("all_pass", summary.get("all_gates_pass")),
    }


def verdict_impact(
    published_gate: dict, counterfactual_p: float, counterfactual_ir: float
) -> dict:
    """Does a published gate boolean move under the counterfactual?

    The published rule is direction-blind (``p < threshold``): H33/H34 already
    disclosed that the direction-aware rule (``p < threshold AND IR > 0``) is
    the one the library applies now, and that the three families carrying a
    ``p`` PASS all have a *negative* alpha. Both are reported, so a reader can
    see the gate under either rule.
    """
    threshold = published_gate["threshold"] if published_gate["threshold"] is not None else GATE_P_VALUE
    counter_pass = bool(counterfactual_p < threshold)
    published_pass = published_gate["pass"]
    return {
        "published_gate_block": published_gate["gate_block_published"],
        "published_pass": published_pass,
        "published_value": published_gate["value"],
        "threshold": threshold,
        "counterfactual_value": float(counterfactual_p),
        "counterfactual_pass": counter_pass,
        "counterfactual_pass_direction_aware": bool(
            counterfactual_p < threshold and counterfactual_ir > 0
        ),
        "gate_boolean_moves": bool(published_pass is not None and bool(published_pass) != counter_pass),
    }


def _one_column(frame: pd.DataFrame) -> pd.Series:
    if isinstance(frame, pd.Series):
        return frame.astype(float)
    return frame.iloc[:, 0].astype(float)


def audit_family(spec: dict, cache_by_symbol: dict[str, list[dict]]) -> dict:
    """Control + counterfactual for one family."""
    art = ARTIFACTS / spec["artifact"]
    out: dict = {
        "hypothesis": spec["hypothesis"],
        "runner": spec["runner"],
        "artifact": spec["artifact"],
        "oos_start": spec["oos_start"],
    }
    if not art.is_dir():
        out["status"] = "artifact_missing"
        return out

    summary = json.loads((art / "summary.json").read_text(encoding="utf-8"))
    published = published_comparison(summary)
    out["published"] = published
    out["published_gate"] = published_significance_gate(summary)
    out["published_verdict"] = published_verdict(summary)

    prices = pd.read_parquet(art / "prices.parquet")
    prices = prices.apply(pd.to_numeric, errors="coerce")
    strategy_equity = _one_column(pd.read_parquet(art / spec["strategy_equity"]))
    bench_equity = _one_column(pd.read_parquet(art / spec["benchmark_equity"]))
    bench_returns = (
        _one_column(pd.read_parquet(art / spec["benchmark_returns"]))
        if spec["benchmark_returns"]
        else bench_equity.pct_change()
    )

    # --- the strategy's positions and its cost residual ---------------------
    signals_path = art / "selected_signals.parquet"
    weights = None
    if signals_path.exists():
        weights = pd.read_parquet(signals_path).apply(pd.to_numeric, errors="coerce")
        weights = weights.reindex(columns=prices.columns)

    price_returns = prices.pct_change()
    if weights is not None:
        positions = engine_positions(
            weights,
            spec["max_leverage"],
            spec["max_position_size"],
            spec["allow_short"],
        )
        gross = (positions.shift(1) * price_returns).sum(axis=1)
    else:
        positions = None
        gross = pd.Series(np.nan, index=prices.index)

    strategy_returns = strategy_equity.pct_change()
    out["control"] = {
        "strategy_return_from_positions_max_abs_diff": (
            float(np.nanmax(np.abs((gross - strategy_returns).to_numpy()))) if positions is not None else None
        ),
        "cost_residual_mean_abs": (
            float(np.nanmean(np.abs((gross - strategy_returns).to_numpy()))) if positions is not None else None
        ),
    }

    # --- the OOS window -----------------------------------------------------
    oos_index = strategy_equity.index[strategy_equity.index >= pd.Timestamp(spec["oos_start"])]
    strat_oos = strategy_returns.reindex(oos_index)
    bench_oos = bench_returns.reindex(oos_index).ffill()
    mask = ~(strat_oos.isna() | bench_oos.isna())
    strat_oos = strat_oos[mask]
    bench_oos = bench_oos[mask]
    out["oos_bars"] = int(len(strat_oos))

    control_cmp = compare_to_benchmark(strat_oos.to_numpy(), bench_oos.to_numpy())
    out["control"]["information_ratio"] = float(control_cmp["information_ratio"])
    out["control"]["alpha_p_value"] = float(control_cmp["alpha_p_value"])
    out["control"]["alpha_annualized"] = float(control_cmp["alpha_annualized"])
    out["control"]["alpha_t_stat"] = float(control_cmp["alpha_t_stat"])

    # --- the total-return series of every traded symbol ---------------------
    # The record's total-return column is the vendor's ``adj_close``. It is
    # committed in the same cache file as the raw ``close`` the runners read,
    # but for some symbols the two are *equal*: the record carries no
    # adjustment for them at all. Those symbols are named, because the
    # counterfactual below corrects the distributions it can measure and
    # leaves the others at zero.
    tr_returns = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    symbols_without_cache = []
    symbols_without_adjustment = []
    adjustment_deviation: dict[str, float] = {}
    cache_file_used: dict[str, str] = {}
    for symbol in prices.columns:
        entries = cache_by_symbol.get(symbol)
        if not entries:
            symbols_without_cache.append(symbol)
            continue
        cached, entry = load_cached(symbol, entries, prices.index)
        if cached is None or "adj_close" not in cached.columns:
            symbols_without_cache.append(symbol)
            continue
        cache_file_used[symbol] = entry["file"]
        adj = cached["adj_close"].astype(float).reindex(prices.index)
        raw = cached["close"].astype(float).reindex(prices.index)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = (adj / raw).replace([np.inf, -np.inf], np.nan)
        deviation = float(np.nanmax(np.abs(ratio - 1.0))) if ratio.notna().any() else 0.0
        adjustment_deviation[symbol] = deviation
        if deviation <= 0.0:
            symbols_without_adjustment.append(symbol)
        tr_returns[symbol] = adj.pct_change()
    out["symbols_without_total_return"] = symbols_without_cache
    out["symbols_without_adjustment"] = symbols_without_adjustment
    out["max_adjustment_deviation"] = adjustment_deviation
    out["cache_file_used"] = cache_file_used

    if positions is None or symbols_without_cache:
        out["status"] = "insufficient_record"
        return out

    # --- the counterfactual -------------------------------------------------
    # The distributions the record omitted: per bar, the position held over the
    # ex-date times the difference between the total return and the price return.
    distribution = tr_returns - price_returns

    # A bar on which a symbol's price is known but its distribution is not is
    # a bar the correction cannot reach. It is counted, never dropped: a
    # silent zero would understate the correction without saying so.
    unreachable = price_returns.notna() & distribution.isna()
    out["correction_unreachable_bars"] = int(unreachable.to_numpy().sum())

    strat_distribution = (positions.shift(1) * distribution).sum(axis=1)

    # The benchmark's book is the engine's own: constant target weights
    # between rebalances, no notional drift, so the benchmark's per-bar
    # return is the (possibly notional) mean of the symbols' returns and
    # the mean of their distributions is its exact first-order correction.
    bench_kind = spec["benchmark"]["kind"]
    if bench_kind == "equal_weight":
        bench_distribution = distribution.mean(axis=1)
    else:
        symbol = spec["benchmark"]["symbol"]
        bench_distribution = distribution[symbol]

    strat_tr = strategy_returns + strat_distribution
    bench_tr = bench_returns + bench_distribution

    strat_tr_oos = strat_tr.reindex(oos_index)[mask]
    bench_tr_oos = bench_tr.reindex(oos_index)[mask]

    counter_cmp = compare_to_benchmark(strat_tr_oos.to_numpy(), bench_tr_oos.to_numpy())
    out["counterfactual_total_return"] = {
        "information_ratio": float(counter_cmp["information_ratio"]),
        "alpha_p_value": float(counter_cmp["alpha_p_value"]),
        "alpha_annualized": float(counter_cmp["alpha_annualized"]),
        "alpha_t_stat": float(counter_cmp["alpha_t_stat"]),
        "win_rate": float(counter_cmp["win_rate"]),
        "mean_strategy_distribution_per_bar": float(strat_distribution.reindex(oos_index)[mask].mean()),
        "mean_benchmark_distribution_per_bar": float(bench_distribution.reindex(oos_index)[mask].mean()),
    }

    # --- does a published gate boolean move? --------------------------------
    gate = out["published_gate"]
    counter_p = float(counter_cmp["alpha_p_value"])
    counter_ir = float(counter_cmp["information_ratio"])
    out["verdict_impact"] = verdict_impact(gate, counter_p, counter_ir)
    out["verdict_impact"]["published_verdict"] = out["published_verdict"]
    # A family whose universe carries no adjustment at all cannot be
    # measured on the total-return question: its counterfactual is the
    # control by construction, and that is a null result, not a finding.
    out["counterfactual_informative"] = bool(len(symbols_without_adjustment) < len(prices.columns))

    # --- the strategy's own gates that are functions of the return series ----
    out["strategy_metrics"] = {
        "control_published_basis": _period_metrics(strat_oos),
        "total_return_basis": _period_metrics(strat_tr_oos),
        "published": published_strategy_metrics(summary),
    }

    # --- sensitivity: the correction computed with the *logged* weights ------
    logged_distribution = (weights.shift(1) * distribution).sum(axis=1)
    strat_tr_logged = strategy_returns + logged_distribution
    sensitivity = compare_to_benchmark(
        strat_tr_logged.reindex(oos_index)[mask].to_numpy(), bench_tr_oos.to_numpy()
    )
    out["sensitivity_logged_weights"] = {
        "information_ratio": float(sensitivity["information_ratio"]),
        "alpha_p_value": float(sensitivity["alpha_p_value"]),
        "alpha_t_stat": float(sensitivity["alpha_t_stat"]),
    }
    out["status"] = "audited"
    return out


# --------------------------------------------------------------------------- #
# 4. The audit                                                               #
# --------------------------------------------------------------------------- #
def build_report() -> dict:
    """The whole audit, as a dictionary.

    Nothing is written and nothing is fetched: the report is a function of
    the committed cache and the committed artifacts alone, so it can be
    rebuilt and compared against the committed summary.
    """
    started = time.time()
    index = index_cache()
    cache_by_symbol = symbol_frames(index)

    report: dict = {
        "hypothesis": "H57",
        "kind": "audit_of_the_published_record",
        "preregistered_in": "HYPOTHESIS_SPEC.md §H57",
        "convention": (
            "Every runner builds its price series from the vendor's raw `close`; the "
            "vendor's total-return column `adj_close` is committed in the same cache "
            "file and is never read by a runner. Every equity return series in the "
            "record is therefore a price return (dividends and distributions excluded)."
        ),
        "n_cache_files_indexed": len(index),
        "n_symbols_indexed": len(cache_by_symbol),
        "cache_coverage": cache_coverage(index),
        "symbol_profiles": {},
        "families": [],
    }

    # The per-symbol distribution profile of every cached equity series.
    for symbol, entries in sorted(cache_by_symbol.items()):
        frames = []
        for entry in sorted(entries, key=lambda e: e["file"]):
            frame = pd.read_parquet(CACHE_DIR / entry["file"])
            if "adj_close" not in frame.columns or len(frame) < 50:
                continue
            if not frame.index.is_monotonic_increasing:
                frame = frame.sort_index()
            frames.append((entry, frame))
        if not frames:
            continue
        entry, frame = max(frames, key=lambda item: (len(item[1]), item[0]["file"]))
        profile = distribution_profile(frame["close"], frame["adj_close"])
        profile["file"] = entry["file"]
        profile["source"] = entry["source"]
        profile["window"] = [entry["start"], entry["end"]]
        profile["interval"] = entry["interval"]
        report["symbol_profiles"][symbol] = profile

    for spec in FAMILIES:
        report["families"].append(audit_family(spec, cache_by_symbol))

    # The tally the deliverable is judged on: no published gate boolean moves.
    audited = [f for f in report["families"] if f.get("status") == "audited"]
    report["verdict_tally"] = {
        "n_families": len(report["families"]),
        "n_audited": len(audited),
        "n_gate_booleans_published": sum(
            1 for f in audited if f["verdict_impact"]["published_pass"] is not None
        ),
        "n_gate_booleans_moved": sum(1 for f in audited if f["verdict_impact"]["gate_boolean_moves"]),
        "n_counterfactuals_informative": sum(
            1 for f in audited if f.get("counterfactual_informative")
        ),
        "n_counterfactual_unreachable_bars": sum(
            f.get("correction_unreachable_bars", 0) for f in audited
        ),
    }

    report["elapsed_sec"] = round(time.time() - started, 3)
    return report


def main() -> int:
    report = build_report()

    ART_DIR.mkdir(parents=True, exist_ok=True)
    (ART_DIR / "summary.json").write_text(
        json.dumps(report, indent=2, default=lambda x: str(x)), encoding="utf-8"
    )

    # --- the console report --------------------------------------------------
    print("H57 — price-return vs total-return audit")
    coverage = report["cache_coverage"]
    print(
        f"cache files: {coverage['n_cache_files_on_disk']} on disk, "
        f"{coverage['n_cache_files_indexed']} indexed, "
        f"{coverage['n_cache_files_not_indexed']} not indexed (the CCXT crypto files)"
    )
    print()
    print("annualised total-return excess (the dividend/distribution the record omits):")
    for symbol, profile in sorted(
        report["symbol_profiles"].items(), key=lambda kv: -kv[1]["annualised_total_return_excess"]
    ):
        print(
            f"  {symbol:6s} {profile['annualised_total_return_excess'] * 100:6.2f}%/yr  "
            f"corporate-action bars={profile['n_corporate_action_bars']:4d}  "
            f"level bars={profile['n_level_bars']:2d}  "
            f"({profile['first']}..{profile['last']})"
        )
    print()
    for family in report["families"]:
        print(f"--- {family['hypothesis']}  {family['artifact']}  status={family.get('status')}")
        if family.get("status") != "audited":
            continue
        ctl = family["control"]
        ctr = family["counterfactual_total_return"]
        pub = family["published"]
        print(
            f"    published : IR={pub['information_ratio']}  p={pub['alpha_p_value']}  "
            f"alpha={pub['alpha_annualized']}"
        )
        print(
            f"    control   : IR={ctl['information_ratio']:.6f}  p={ctl['alpha_p_value']:.6f}  "
            f"alpha={ctl['alpha_annualized']:.6f}  t={ctl['alpha_t_stat']:.6f}"
        )
        print(
            f"    total-ret : IR={ctr['information_ratio']:.6f}  p={ctr['alpha_p_value']:.6f}  "
            f"alpha={ctr['alpha_annualized']:.6f}  t={ctr['alpha_t_stat']:.6f}"
        )
        impact = family["verdict_impact"]
        print(
            f"    gate      : published={impact['published_pass']}  "
            f"counterfactual={impact['counterfactual_pass']}  "
            f"moves={impact['gate_boolean_moves']}  "
            f"informative={family.get('counterfactual_informative')}"
        )
    print()
    tally = report["verdict_tally"]
    print(
        f"verdict tally: {tally['n_audited']} audited, "
        f"{tally['n_gate_booleans_published']} published gate booleans, "
        f"{tally['n_gate_booleans_moved']} moved, "
        f"{tally['n_counterfactuals_informative']} informative counterfactuals"
    )
    print()
    print(f"elapsed: {report['elapsed_sec']}s -> {ART_DIR / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
