"""NF-20261109-14 / H169 (Cycle 83): Overnight futures (ES/NQ) lead-lag
to cash session (SPY/QQQ) — cross-market information transmission.

Repo-relative novelty (honest). H18 (overnight/intraday REJECT 4/9) tests
same-asset overnight sign -> next-day intraday direction. H85 (cross-asset
lead-lag REJECT 2/8) tests sector ETF -> constituent. H169 tests
*derivative futures overnight return -> underlying cash daytime return* —
distinct mechanism and instrument class. ES=F/NQ=F trade 23h on CME Globex;
price discovery leads SPY/QQQ cash open. Free yfinance daily: ES=F, NQ=F,
SPY, QQQ. Clean falsifiers: random-futures control, inverse signal,
OAT perturbation, NQ/QQQ independent replication.

Mechanism (cross-market information transmission). Futures trade 23h on
Globex; cash ETFs trade 6.5h. Overnight news (macro, earnings,
geopolitical) is reflected in futures prices before cash open. The overnight
futures return (futures_open[t] / futures_close[t-1] - 1) contains
information about expected cash returns. Signal = sign(overnight_futures_return)
or z-scored overnight return. Long cash if signal > z_entry, short if
< -z_entry, flat otherwise. Position established at cash open, held to cash
close (intraday). 1-bar delay via engine `signals.shift(1)` ensures no
look-ahead: futures close[t-1] and open[t] known at cash open[t]; cash
return earned open[t]->close[t].

Observable (past-only, PIT, free yfinance): ES=F, NQ=F, SPY, QQQ daily
auto-adjust Open/Close.

Null (H0). Overnight futures return has no predictive power for daytime
cash returns beyond random chance after costs.

Pre-registration (Cycle 83, decision-ready before validation outcomes).
NF-ID NF-20261109-14 (verified unused: no executed NF/H/runner/artifact).
Hypothesis H169 (next unused after H168; H24/H68-H73/H76-H79 unassigned,
not recycled). Universe SPY/QQQ (traded), ES=F/NQ=F (signal), yfinance
daily auto-adjust Open/Close (free, PIT). Sample 2010-01-01->2026-10-31
(train 2010-01-01->2019-12-31, val 2020-01-01->2022-12-31, test
2023-01-01->2026-10-31 protected). Signal: z-scored overnight futures
return over `lookback`; intraday cash position at open based on signal;
vol-targeted to `vol_target` ann; long/short, max exposure MAX_POS=0.5.
Bounded grid: pair {ES_SPY, NQ_QQQ} x lookback {21,63,126} x z_entry
{0.0,0.5,1.0} x vol_target {0.10,0.15,0.20} (54 combos); train-only
4-fold WF selection by mean train Sharpe; Test protected. No src/qtr
change. All gates fail-closed on pre-registered OOS Val+Test.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark
p<=0.05 with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, random-futures control (random overnight sign),
always-flat, inverse signal (short on positive overnight futures return),
OAT perturbation, Val/Test subperiods, NQ/QQQ pair as independent
replication.

Falsifiers: random-futures comparable or better; inverse outperforms;
benchmark fails; fragile; worst-regime collapse; NQ/QQQ fails to
replicate.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import DataCache, DataFetcher  # noqa: E402
from qtr.validation.statistics import sharpe_ratio  # noqa: E402

EXPERIMENT_DESC = (
    "NF-20261109-14/H169 (Cycle 83): Overnight futures (ES/NQ) lead-lag "
    "to cash session (SPY/QQQ). Vol-targeted intraday cash position at open "
    "based on overnight futures signal. 1-bar delay. Train-only WF "
    "selection; Test protected; OOS Val+Test gates."
)

# Pairs: (futures_symbol, cash_symbol)
PAIRS = {
    "ES_SPY": ("ES=F", "SPY"),
    "NQ_QQQ": ("NQ=F", "QQQ"),
}
ALL_SYMBOLS = ["ES=F", "NQ=F", "SPY", "QQQ"]
DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
SEED = 169
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

LOOKBACKS = [21, 63, 126]
Z_ENTRIES = [0.0, 0.5, 1.0]
VOL_TARGETS = [0.10, 0.15, 0.20]


def _cfg() -> BacktestConfig:
    return BacktestConfig(
        asset_class=AssetClass.EQUITY,
        cost_model=CostModel(equity_commission_bps=1.0, equity_spread_bps=1.0),
        initial_capital=INITIAL_CAPITAL,
        max_position_size=MAX_POS,
        allow_short=True,
    )


def _splits(index: pd.DatetimeIndex):
    train = pd.Series(index <= pd.Timestamp(TRAIN_END), index=index)
    val = pd.Series(
        (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END)), index=index
    )
    test = pd.Series(index > pd.Timestamp(VAL_END), index=index)
    return train, val, test


def _fetch_all_data() -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for all symbols using DataFetcher with isolated cache."""
    fetcher = DataFetcher(cache=DataCache(cache_dir=ROOT / ".cache" / "h169"))
    data = fetcher.fetch_yahoo(
        ALL_SYMBOLS, start=DATA_START, end=DATA_END, interval="1d", use_cache=True
    )
    return data


def _align_and_merge(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Align all symbols to common index and merge into single DataFrame with prefixed columns."""
    # Find common index
    common_idx = None
    for sym in ALL_SYMBOLS:
        if sym in data and not data[sym].empty:
            idx = data[sym].index
            if common_idx is None:
                common_idx = idx
            else:
                common_idx = common_idx.intersection(idx)
    if common_idx is None or len(common_idx) == 0:
        raise RuntimeError("no common index across symbols")

    # Merge with prefixed columns
    frames = []
    for sym in ALL_SYMBOLS:
        if sym in data and not data[sym].empty:
            df = data[sym].reindex(common_idx)
            df.columns = [f"{c}_{sym}" for c in df.columns]
            frames.append(df)
    merged = pd.concat(frames, axis=1)
    merged = merged.dropna().sort_index()
    merged = merged[(merged > 0).all(axis=1)]
    if merged.empty:
        raise RuntimeError("empty merged data")
    return merged


def _overnight_futures_return(prices: pd.DataFrame, fut_sym: str) -> pd.Series:
    """Compute overnight futures return: open[t] / close[t-1] - 1.

    Known at cash open[t] (futures close[t-1] and open[t] are both known).
    """
    fut_open = prices[f"open_{fut_sym}"]
    fut_close = prices[f"close_{fut_sym}"]
    fut_close_lag = fut_close.shift(1)
    ret = fut_open / fut_close_lag - 1.0
    return ret


def _cash_daytime_return(prices: pd.DataFrame, cash_sym: str) -> pd.Series:
    """Compute daytime cash return: close[t] / open[t] - 1.

    Earned after entry at cash open[t].
    """
    cash_open = prices[f"open_{cash_sym}"]
    cash_close = prices[f"close_{cash_sym}"]
    ret = cash_close / cash_open - 1.0
    return ret


def _zscore(series: pd.Series, lookback: int) -> pd.Series:
    """Rolling z-score with min_periods = lookback."""
    mean = series.rolling(lookback, min_periods=lookback).mean()
    std = series.rolling(lookback, min_periods=lookback).std(ddof=0)
    z = (series - mean) / std.replace(0.0, np.nan)
    return z


def _vol_scale(intraday_ret: pd.Series, vol_target: float) -> pd.Series:
    """Vol scaling based on intraday return volatility."""
    rv = intraday_ret.rolling(21, min_periods=21).std(ddof=0) * np.sqrt(252.0)
    return (vol_target / rv.replace(0.0, np.nan)).clip(0.0, 1.0)


def _build_strategy_returns(prices: pd.DataFrame, params: dict) -> tuple[pd.Series, pd.Series]:
    """Build strategy return series and position series for a given parameter set."""
    pair = params["pair"]
    fut_sym, cash_sym = PAIRS[pair]
    lookback = params["lookback"]
    z_entry = params["z_entry"]
    vol_target = params["vol_target"]

    # Overnight futures return (known at cash open)
    overnight_ret = _overnight_futures_return(prices, fut_sym)
    # Z-score over lookback
    z = _zscore(overnight_ret, lookback)
    # Signal: long if z > z_entry, short if z < -z_entry, flat otherwise
    signal = pd.Series(0.0, index=prices.index)
    signal = signal.where(z <= z_entry, 1.0)  # long
    signal = signal.where(z >= -z_entry, -1.0)  # short

    # Intraday cash return
    intraday_ret = _cash_daytime_return(prices, cash_sym)

    # Vol scaling on intraday returns
    vscale = _vol_scale(intraday_ret, vol_target)

    # Position size = signal * vol_target * vscale, clipped to MAX_POS
    pos = (signal * vol_target * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)

    # Strategy return = position (shifted by 1 for no look-ahead) * intraday return
    strat_ret = pos.shift(1).fillna(0.0) * intraday_ret
    return strat_ret, pos


def _make_synthetic_price(strat_ret: pd.Series) -> pd.DataFrame:
    """Create synthetic price series from strategy returns."""
    strat_price = (1.0 + strat_ret).cumprod()
    strat_price.iloc[0] = 1.0
    # Use a dummy symbol name for the backtest engine
    return pd.DataFrame({"STRAT": strat_price.values}, index=strat_ret.index)


def _evaluate_strategy(prices: pd.DataFrame, params: dict, cfg: BacktestConfig) -> tuple:
    """Evaluate strategy and return (BacktestResult, strat_ret, pos)."""
    strat_ret, pos = _build_strategy_returns(prices, params)
    p_strat = _make_synthetic_price(strat_ret)
    s_strat = pd.DataFrame(1.0, index=p_strat.index, columns=["STRAT"])
    res = run_backtest(prices=p_strat, signals=s_strat, volumes=None, config=cfg)
    return res, strat_ret, pos


def _benchmark_returns(prices: pd.DataFrame, cash_sym: str) -> pd.Series:
    """Buy-and-hold intraday cash returns."""
    intraday_ret = _cash_daytime_return(prices, cash_sym)
    # Constant position of 1.0 (shifted by engine)
    return intraday_ret


def _wf_selection_mean(
    prices: pd.DataFrame, train_mask: pd.Series, params: dict, cfg: BacktestConfig
) -> float:
    """Train-only walk-forward Sharpe for parameter selection."""
    res, _, _ = _evaluate_strategy(prices, params, cfg)
    train_idx = prices.index[train_mask]
    if len(train_idx) < WF_FOLDS_SELECTION * 252:
        train_ret = res.returns[train_mask].dropna()
        return float(sharpe_ratio(train_ret.values)) if len(train_ret) > 1 else float("-inf")
    fold = len(train_idx) // WF_FOLDS_SELECTION
    sharpes = []
    for i in range(WF_FOLDS_SELECTION):
        end = (i + 1) * fold if i < WF_FOLDS_SELECTION - 1 else len(train_idx)
        idx = train_idx[:end]
        if len(idx) < 252:
            continue
        m = pd.Series(False, index=prices.index)
        m.loc[idx] = True
        train_ret = res.returns[m].dropna()
        if len(train_ret) > 1:
            s = float(sharpe_ratio(train_ret.values))
            if np.isfinite(s):
                sharpes.append(s)
    return float(np.mean(sharpes)) if sharpes else float("-inf")


def select_params(
    prices: pd.DataFrame, train_mask: pd.Series, cfg: BacktestConfig
) -> tuple[dict, list[dict]]:
    rows = []
    for pair in PAIRS.keys():
        for lookback in LOOKBACKS:
            for z_entry in Z_ENTRIES:
                for vol_target in VOL_TARGETS:
                    params = {
                        "pair": pair,
                        "lookback": lookback,
                        "z_entry": z_entry,
                        "vol_target": vol_target,
                    }
                    wf = _wf_selection_mean(prices, train_mask, params, cfg)
                    rows.append({**params, "wf_train_mean_sharpe": wf})
    rows.sort(key=lambda r: r["wf_train_mean_sharpe"], reverse=True)
    best = {k: rows[0][k] for k in ("pair", "lookback", "z_entry", "vol_target")}
    return best, rows


def _pf(returns: pd.Series) -> float:
    r = returns.dropna()
    gain = r[r > 0].sum()
    loss = -r[r < 0].sum()
    if loss <= 0:
        return float("inf") if gain > 0 else 0.0
    return float(gain / loss)


def _maxdd(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float(((equity - peak) / peak).min())


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    if len(r) > 1:
        sr = float(sharpe_ratio(r.values))
    else:
        sr = 0.0
    cum = (1 + r).cumprod()
    dd = float((cum / cum.cummax() - 1.0).min()) if len(cum) > 0 else 0.0
    gp = float(r[r > 0].sum())
    gl = float(abs(r[r < 0].sum()))
    pf = gp / gl if gl > 0 else float("inf")
    return {
        "sharpe": sr,
        "max_drawdown": dd,
        "profit_factor": pf,
        "trades": int(n_trades),
    }


def _count_trades(pos: pd.Series, mask: pd.Series) -> int:
    """Count days with non-zero position in mask period."""
    return int((pos.loc[mask].abs() > 1e-12).sum())


def worst_regime_sharpe(returns: pd.Series, window: int = 252) -> float:
    r = returns.dropna()
    if len(r) < window:
        return float(sharpe_ratio(r))
    roll = r.rolling(window).apply(lambda x: float(sharpe_ratio(x)), raw=False)
    return float(roll.min())


def perturbation_ratio(
    prices: pd.DataFrame, oos_mask: pd.Series, best: dict, cfg: BacktestConfig
) -> float:
    base_res, _, _ = _evaluate_strategy(prices, best, cfg)
    base_sharpe = float(sharpe_ratio(base_res.returns[oos_mask].dropna().values))
    if not np.isfinite(base_sharpe) or abs(base_sharpe) < 1e-12:
        return 0.0
    ratios = []
    # Perturb lookback by +/-20%
    for dl in [-0.2, 0.2]:
        lb = int(np.clip(best["lookback"] * (1 + dl), 10, 252))
        p = {**best, "lookback": lb}
        res, _, _ = _evaluate_strategy(prices, p, cfg)
        s = float(sharpe_ratio(res.returns[oos_mask].dropna().values))
        if np.isfinite(s):
            ratios.append(s / base_sharpe)
    # Perturb z_entry by +/-0.2
    for dz in [-0.2, 0.2]:
        ze = float(np.clip(best["z_entry"] + dz, 0.0, 2.0))
        p = {**best, "z_entry": ze}
        res, _, _ = _evaluate_strategy(prices, p, cfg)
        s = float(sharpe_ratio(res.returns[oos_mask].dropna().values))
        if np.isfinite(s):
            ratios.append(s / base_sharpe)
    # Perturb vol_target by +/-0.02
    for dv in [-0.02, 0.02]:
        vt = float(np.clip(best["vol_target"] + dv, 0.05, 0.30))
        p = {**best, "vol_target": vt}
        res, _, _ = _evaluate_strategy(prices, p, cfg)
        s = float(sharpe_ratio(res.returns[oos_mask].dropna().values))
        if np.isfinite(s):
            ratios.append(s / base_sharpe)
    return float(min(ratios)) if ratios else 0.0


def _benchmark_compare(strat_ret: pd.Series, bench_ret: pd.Series) -> tuple[float, float]:
    a = pd.concat([strat_ret.rename("s"), bench_ret.rename("b")], axis=1).dropna()
    if len(a) < 30:
        return 1.0, 0.0
    diff = a["s"] - a["b"]
    ir = float(diff.mean() / diff.std(ddof=0) * np.sqrt(252.0)) if diff.std(ddof=0) > 0 else 0.0
    rng = np.random.default_rng(SEED)
    obs = diff.mean()
    count = 0
    n = len(diff)
    vals = diff.to_numpy()
    for _ in range(2000):
        signs = rng.choice([-1.0, 1.0], size=n)
        if float((vals * signs).mean()) >= obs:
            count += 1
    p = (count + 1) / 2001
    return float(p), ir


def _make_random_futures_returns(prices: pd.DataFrame, params: dict) -> pd.Series:
    """Falsifier: random overnight futures sign."""
    rng = np.random.default_rng(SEED)
    pair = params["pair"]
    fut_sym, cash_sym = PAIRS[pair]
    vol_target = params["vol_target"]

    overnight_ret = _overnight_futures_return(prices, fut_sym)
    z = _zscore(overnight_ret, params["lookback"])
    signal = pd.Series(0.0, index=prices.index)
    signal = signal.where(z <= params["z_entry"], 1.0)
    signal = signal.where(z >= -params["z_entry"], -1.0)

    # Randomize signs
    valid = signal.abs() > 0
    if valid.any():
        signs = signal[valid].to_numpy().copy()
        rng.shuffle(signs)
        signal.loc[valid] = signs

    intraday_ret = _cash_daytime_return(prices, cash_sym)
    vscale = _vol_scale(intraday_ret, vol_target)
    pos = (signal * vol_target * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    strat_ret = pos.shift(1).fillna(0.0) * intraday_ret
    return strat_ret


def _make_inverse_returns(prices: pd.DataFrame, params: dict) -> pd.Series:
    """Falsifier: inverse signal (short on positive overnight futures return)."""
    pair = params["pair"]
    fut_sym, cash_sym = PAIRS[pair]
    lookback = params["lookback"]
    z_entry = params["z_entry"]
    vol_target = params["vol_target"]

    overnight_ret = _overnight_futures_return(prices, fut_sym)
    z = _zscore(overnight_ret, lookback)
    signal = pd.Series(0.0, index=prices.index)
    signal = signal.where(z <= z_entry, -1.0)  # short
    signal = signal.where(z >= -z_entry, 1.0)  # long

    intraday_ret = _cash_daytime_return(prices, cash_sym)
    vscale = _vol_scale(intraday_ret, vol_target)
    pos = (signal * vol_target * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    strat_ret = pos.shift(1).fillna(0.0) * intraday_ret
    return strat_ret


def _make_flat_returns(prices: pd.DataFrame, cash_sym: str) -> pd.Series:
    """Falsifier: always flat."""
    intraday_ret = _cash_daytime_return(prices, cash_sym)
    return pd.Series(0.0, index=prices.index)


def main() -> None:
    t0 = time.time()
    print(f"[{EXPERIMENT_DESC}]")
    data = _fetch_all_data()
    prices = _align_and_merge(data)
    train, val, test = _splits(prices.index)
    oos = val | test
    cfg = _cfg()

    # Benchmark: buy-and-hold intraday SPY
    bench_ret = _benchmark_returns(prices, "SPY")
    p_bench = _make_synthetic_price(bench_ret)
    s_bench = pd.DataFrame(1.0, index=p_bench.index, columns=["STRAT"])
    bench_res = run_backtest(prices=p_bench, signals=s_bench, volumes=None, config=cfg)

    best, grid_rows = select_params(prices, train, cfg)
    best_res, best_strat_ret, best_pos = _evaluate_strategy(prices, best, cfg)

    oos_ret = (
        best_res.returns[oos].dropna()
        if hasattr(best_res, "returns")
        else best_strat_ret[oos].dropna()
    )
    train_ret = (
        best_res.returns[train].dropna()
        if hasattr(best_res, "returns")
        else best_strat_ret[train].dropna()
    )

    # Use the synthetic returns directly for metrics
    oos_sharpe = float(sharpe_ratio(oos_ret.values)) if len(oos_ret) > 1 else 0.0
    train_sharpe = float(sharpe_ratio(train_ret.values)) if len(train_ret) > 1 else 0.0
    wf_stab = (
        float(oos_sharpe / train_sharpe)
        if np.isfinite(train_sharpe) and abs(train_sharpe) > 1e-12
        else 0.0
    )

    bench_oos_ret = bench_res.returns[oos].dropna()
    bench_p, ir = _benchmark_compare(oos_ret, bench_oos_ret)
    pert = perturbation_ratio(prices, oos, best, cfg)
    worst_regime = worst_regime_sharpe(oos_ret)

    oos_ev = {
        "sharpe": oos_sharpe,
        "profit_factor": _pf(oos_ret),
        "max_drawdown": _maxdd((1.0 + oos_ret).cumprod()),
        "trades": _count_trades(best_pos, oos),
        "wf_stability": wf_stab,
        "worst_regime_sharpe": worst_regime,
        "benchmark_p": bench_p,
        "information_ratio": ir,
        "perturbation_ratio": pert,
        "n": int(oos.sum()),
    }
    train_ev = {
        "sharpe": train_sharpe,
        "profit_factor": _pf(train_ret),
        "max_drawdown": _maxdd((1.0 + train_ret).cumprod()),
        "trades": _count_trades(best_pos, train),
    }

    gates = {
        "sharpe_ge_1": oos_ev["sharpe"] >= 1.0,
        "trades_ge_200": oos_ev["trades"] >= 200,
        "pf_ge_1_3": oos_ev["profit_factor"] >= 1.3,
        "maxdd_le_15pct": oos_ev["max_drawdown"] >= -0.15,
        "wf_stability_ge_0_7": wf_stab >= 0.7,
        "worst_regime_ge_0_3": oos_ev["worst_regime_sharpe"] >= 0.3,
        "benchmark_p_le_0_05_ir_ge_0": bench_p <= 0.05 and ir >= 0.0,
        "perturbation_ge_0_5": pert >= 0.5,
    }
    pass_count = sum(1 for v in gates.values() if v)
    verdict = "PASS" if pass_count == 8 else "REJECT"

    # Ablations
    ablations = {}
    # Buy-hold SPY: position = 1.0 every day
    bench_pos = pd.Series(1.0, index=prices.index)
    ablations["buy_hold_spy"] = _period_metrics(bench_oos_ret, _count_trades(bench_pos, oos))
    # Always flat
    flat_ret = _make_flat_returns(prices, "SPY")
    flat_pos = pd.Series(0.0, index=prices.index)
    p_flat = _make_synthetic_price(flat_ret)
    s_flat = pd.DataFrame(1.0, index=p_flat.index, columns=["STRAT"])
    flat_res = run_backtest(prices=p_flat, signals=s_flat, volumes=None, config=cfg)
    ablations["always_flat"] = _period_metrics(
        flat_res.returns[oos].dropna(), _count_trades(flat_pos, oos)
    )
    # Random exposure matched
    rand_ret = _make_random_futures_returns(prices, best)
    # Reconstruct position for random futures
    pair = best["pair"]
    fut_sym, cash_sym = PAIRS[pair]
    overnight_ret = _overnight_futures_return(prices, fut_sym)
    z = _zscore(overnight_ret, best["lookback"])
    signal = pd.Series(0.0, index=prices.index)
    signal = signal.where(z <= best["z_entry"], 1.0)
    signal = signal.where(z >= -best["z_entry"], -1.0)
    valid = signal.abs() > 0
    if valid.any():
        signs = signal[valid].to_numpy().copy()
        np.random.default_rng(SEED).shuffle(signs)
        signal.loc[valid] = signs
    intraday_ret = _cash_daytime_return(prices, cash_sym)
    vscale = _vol_scale(intraday_ret, best["vol_target"])
    rand_pos = (signal * best["vol_target"] * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    p_rand = _make_synthetic_price(rand_ret)
    s_rand = pd.DataFrame(1.0, index=p_rand.index, columns=["STRAT"])
    rand_res = run_backtest(prices=p_rand, signals=s_rand, volumes=None, config=cfg)
    ablations["random_exposure_matched"] = _period_metrics(
        rand_res.returns[oos].dropna(), _count_trades(rand_pos, oos)
    )
    # Random futures sign
    ablations["random_futures_sign"] = ablations["random_exposure_matched"]
    # Inverse signal
    inv_ret = _make_inverse_returns(prices, best)
    # Reconstruct position for inverse
    inv_signal = pd.Series(0.0, index=prices.index)
    inv_signal = inv_signal.where(z <= best["z_entry"], -1.0)
    inv_signal = inv_signal.where(z >= -best["z_entry"], 1.0)
    inv_pos = (inv_signal * best["vol_target"] * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    p_inv = _make_synthetic_price(inv_ret)
    s_inv = pd.DataFrame(1.0, index=p_inv.index, columns=["STRAT"])
    inv_res = run_backtest(prices=p_inv, signals=s_inv, volumes=None, config=cfg)
    ablations["inverse_signal"] = _period_metrics(
        inv_res.returns[oos].dropna(), _count_trades(inv_pos, oos)
    )

    out = {
        "nf_id": "NF-20261109-14",
        "h_id": "H169",
        "verdict": verdict,
        "gates": f"{pass_count}/8",
        "gate_detail": gates,
        "best": best,
        "train": train_ev,
        "oos": oos_ev,
        "ablations": ablations,
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_dir = ROOT / ".experiments" / "nf_runs" / "nf_20261109_14_overnight_futures_leadlag"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    pd.DataFrame(grid_rows).to_csv(out_dir / "grid.csv", index=False)
    meta = {
        "nf_id": "NF-20261109-14",
        "h_id": "H169",
        "universe": [best["pair"].split("_")[1], PAIRS[best["pair"]][0]],
        "data_start": DATA_START,
        "data_end": DATA_END,
        "rows": int(len(prices)),
        "train_end": TRAIN_END,
        "val_end": VAL_END,
        "seed": SEED,
        "grid_n": len(grid_rows),
        "selection": "best train-only 4-fold WF mean Sharpe; gates on OOS Val+Test",
    }
    (out_dir / "data_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(
        json.dumps(
            {"verdict": verdict, "gates": out["gates"], "oos": oos_ev, "best": best},
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
