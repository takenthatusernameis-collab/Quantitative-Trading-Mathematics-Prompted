"""NF-20261109-17 / H170 (Cycle 84): Leveraged ETF daily rebalancing flows
SPY timing — structural derivative hedging / pro-cyclical flow.

Repo-relative novelty (honest). H168 (S&P 500 index rebalance flow timing REJECT
4/8) tests quarterly index-fund rebalancing calendar windows. H170 tests *daily
derivative hedging flow from leveraged ETF issuers* — distinct mechanism
(daily pro-cyclical hedging vs quarterly index-fund calendar), distinct
frequency, distinct causal channel. Leveraged ETFs (SSO 2×, UPRO 3×, SDS -2×,
SPXL 3×, SPXS -3×) must rebalance daily to maintain target leverage. This
creates pro-cyclical end-of-day order flow: on up days, issuers buy more SPY
exposure; on down days, they sell. Net flow amplifies the daily trend, creating
momentum persistence in SPY. Free yfinance daily: SPY, SSO, UPRO, SDS, SPXL,
SPXS. Clean falsifiers: inverse flow, random flow control, OAT perturbation.

Mechanism (structural derivative hedging / pro-cyclical flow). Leveraged ETF
AUM × leverage factor × daily return = required rebalancing trade (notional).
Net flow across all major leveraged ETFs on SPY is pro-cyclical (same sign as
SPY return). This flow executes near the close, pushing prices further in the
direction of the day's move. The next day's overnight/close-to-close return
continues in the same direction (momentum persistence from flow pressure).
Signal = sign(net_leveraged_etf_flow), where flow ≈ Σ(AUM_i × leverage_i ×
return_i) for i ∈ {SSO, UPRO, SDS, SPXL, SPXS}. Position established at close,
held to next close (overnight). 1-bar delay via engine `signals.shift(1)`
ensures no look-ahead: leveraged ETF returns and AUM known at close t; SPY
return earned close[t]→close[t+1].

Observable (past-only, PIT, free yfinance): SPY, SSO, UPRO, SDS, SPXL, SPXS
daily auto-adjust Close. AUM static from fund fact sheets (slow-moving;
conservative constant approximation).

Null (H0). Net leveraged ETF rebalancing flow has no predictive power for
next-day SPY returns beyond random chance after costs.

Pre-registration (Cycle 84, decision-ready before validation outcomes).
NF-ID NF-20261109-17 (verified unused: no executed NF/H/runner/artifact).
Hypothesis H170 (next unused after H169; H24/H68-H73/H76-H79 unassigned,
not recycled). Universe SPY (traded), SSO/UPRO/SDS/SPXL/SPXS (signal), yfinance
daily auto-adjust Close (free, PIT). Sample 2010-01-01->2026-10-31
(train 2010-01-01->2019-12-31, val 2020-01-01->2022-12-31, test
2023-01-01->2026-10-31 protected). Signal: z-scored net leveraged ETF flow
over `lookback`; overnight SPY position at close based on signal;
vol-targeted to `vol_target` ann; long/short, max exposure MAX_POS=0.5.
Bounded grid: leverage_set {{SSO,UPRO,SDS}, {SSO,UPRO,SDS,SPXL,SPXS}} x
lookback {5,21,63} x vol_target {0.10,0.15,0.20} (18 combos); train-only
4-fold WF selection by mean train Sharpe; Test protected. No src/qtr
change. All gates fail-closed on pre-registered OOS Val+Test.

Gates (OOS Val+Test): Sharpe>=1.0, trades>=200, PF>=1.3, maxDD<=15%,
WF stability>=0.7, worst-regime rolling-252 Sharpe>=0.3, benchmark
p<=0.05 with IR>=0, perturbation min ratio>=0.5.

Ablations: buy-hold SPY, always-flat, inverse signal (short on positive net
flow), random flow control (shuffle leveraged ETF return signs), OAT
perturbation, Val/Test subperiods, equal-weight vs AUM-weighted basket.

Falsifiers: random flow comparable or better; inverse outperforms;
benchmark fails; fragile; worst-regime collapse; equal-weight fails to
replicate AUM-weighted.
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
    "NF-20261109-17/H170 (Cycle 84): Leveraged ETF daily rebalancing flows "
    "SPY timing. Vol-targeted overnight SPY position at close based on net "
    "leveraged ETF flow. 1-bar delay. Train-only WF selection; Test protected; "
    "OOS Val+Test gates."
)

# Leveraged ETFs on SPY with leverage factors
LEVERAGED_ETFS = {
    "SSO": 2.0,   # 2x long
    "UPRO": 3.0,  # 3x long
    "SDS": -2.0,  # 2x short (inverse)
    "SPXL": 3.0,  # 3x long
    "SPXS": -3.0, # 3x short (inverse)
}

# Two leverage sets to test
LEVERAGE_SETS = {
    "core_3": ["SSO", "UPRO", "SDS"],
    "full_5": ["SSO", "UPRO", "SDS", "SPXL", "SPXS"],
}

# Static AUM estimates (billions USD) from fund fact sheets ~2024
# Used as constant weights for flow calculation (slow-moving, conservative)
AUM_ESTIMATES = {
    "SSO": 3.5,
    "UPRO": 4.0,
    "SDS": 2.5,
    "SPXL": 2.0,
    "SPXS": 1.5,
}

ALL_SYMBOLS = ["SPY"] + list(LEVERAGED_ETFS.keys())
DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"
SEED = 170
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
WF_FOLDS_SELECTION = 4

LOOKBACKS = [5, 21, 63]
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
    fetcher = DataFetcher(cache=DataCache(cache_dir=ROOT / ".cache" / "h170"))
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

    # Merge with prefixed columns (only need Close for returns)
    frames = []
    for sym in ALL_SYMBOLS:
        if sym in data and not data[sym].empty:
            df = data[sym].reindex(common_idx)[["close"]]
            df.columns = [f"close_{sym}"]
            frames.append(df)
    merged = pd.concat(frames, axis=1)
    merged = merged.dropna().sort_index()
    merged = merged[(merged > 0).all(axis=1)]
    if merged.empty:
        raise RuntimeError("empty merged data")
    return merged


def _compute_returns(prices: pd.DataFrame, sym: str) -> pd.Series:
    """Compute daily close-to-close returns for a symbol."""
    close = prices[f"close_{sym}"]
    ret = close.pct_change()
    return ret


def _net_leveraged_etf_flow(prices: pd.DataFrame, leverage_set: list[str]) -> pd.Series:
    """Compute net leveraged ETF rebalancing flow.

    Flow_i = AUM_i * leverage_i * return_i (notional USD)
    Net flow = sum(Flow_i) across leverage_set
    Positive flow = net buying pressure (pro-cyclical on up days)
    """
    spy_ret = _compute_returns(prices, "SPY")
    flows = []
    for etf in leverage_set:
        etf_ret = _compute_returns(prices, etf)
        leverage = LEVERAGED_ETFS[etf]
        aum = AUM_ESTIMATES[etf]
        # Flow = AUM * leverage * return (notional)
        flow = aum * leverage * etf_ret
        flows.append(flow)

    net_flow = pd.concat(flows, axis=1).sum(axis=1)
    return net_flow


def _zscore(series: pd.Series, lookback: int) -> pd.Series:
    """Rolling z-score with min_periods = lookback."""
    mean = series.rolling(lookback, min_periods=lookback).mean()
    std = series.rolling(lookback, min_periods=lookback).std(ddof=0)
    z = (series - mean) / std.replace(0.0, np.nan)
    return z


def _vol_scale(returns: pd.Series, vol_target: float) -> pd.Series:
    """Vol scaling based on return volatility."""
    rv = returns.rolling(21, min_periods=21).std(ddof=0) * np.sqrt(252.0)
    return (vol_target / rv.replace(0.0, np.nan)).clip(0.0, 1.0)


def _build_strategy_returns(prices: pd.DataFrame, params: dict) -> tuple[pd.Series, pd.Series]:
    """Build strategy return series and position series for a given parameter set."""
    leverage_set_name = params["leverage_set"]
    leverage_set = LEVERAGE_SETS[leverage_set_name]
    lookback = params["lookback"]
    vol_target = params["vol_target"]

    # Net leveraged ETF flow (known at close)
    net_flow = _net_leveraged_etf_flow(prices, leverage_set)
    # Z-score over lookback for normalization
    z = _zscore(net_flow, lookback)
    # Signal: long if z > 0, short if z < 0, flat if z == 0 (or NaN)
    signal = pd.Series(0.0, index=prices.index)
    signal = signal.where(z <= 0, 1.0)   # long on positive flow
    signal = signal.where(z >= 0, -1.0)  # short on negative flow

    # SPY overnight return (close[t] -> close[t+1])
    spy_ret = _compute_returns(prices, "SPY")

    # Vol scaling on SPY returns
    vscale = _vol_scale(spy_ret, vol_target)

    # Position size = signal * vol_target * vscale, clipped to MAX_POS
    pos = (signal * vol_target * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)

    # Strategy return = position (shifted by 1 for no look-ahead) * SPY return
    strat_ret = pos.shift(1).fillna(0.0) * spy_ret
    return strat_ret, pos


def _make_synthetic_price(strat_ret: pd.Series) -> pd.DataFrame:
    """Create synthetic price series from strategy returns."""
    strat_price = (1.0 + strat_ret).cumprod()
    strat_price.iloc[0] = 1.0
    return pd.DataFrame({"STRAT": strat_price.values}, index=strat_ret.index)


def _evaluate_strategy(prices: pd.DataFrame, params: dict, cfg: BacktestConfig) -> tuple:
    """Evaluate strategy and return (BacktestResult, strat_ret, pos)."""
    strat_ret, pos = _build_strategy_returns(prices, params)
    p_strat = _make_synthetic_price(strat_ret)
    s_strat = pd.DataFrame(1.0, index=p_strat.index, columns=["STRAT"])
    res = run_backtest(prices=p_strat, signals=s_strat, volumes=None, config=cfg)
    return res, strat_ret, pos


def _benchmark_returns(prices: pd.DataFrame) -> pd.Series:
    """Buy-and-hold SPY returns."""
    return _compute_returns(prices, "SPY")


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
    for leverage_set_name in LEVERAGE_SETS.keys():
        for lookback in LOOKBACKS:
            for vol_target in VOL_TARGETS:
                params = {
                    "leverage_set": leverage_set_name,
                    "lookback": lookback,
                    "vol_target": vol_target,
                }
                wf = _wf_selection_mean(prices, train_mask, params, cfg)
                rows.append({**params, "wf_train_mean_sharpe": wf})
    rows.sort(key=lambda r: r["wf_train_mean_sharpe"], reverse=True)
    best = {k: rows[0][k] for k in ("leverage_set", "lookback", "vol_target")}
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
        lb = int(np.clip(best["lookback"] * (1 + dl), 3, 252))
        p = {**best, "lookback": lb}
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


def _make_inverse_returns(prices: pd.DataFrame, params: dict) -> pd.Series:
    """Falsifier: inverse signal (short on positive net flow)."""
    leverage_set_name = params["leverage_set"]
    leverage_set = LEVERAGE_SETS[leverage_set_name]
    lookback = params["lookback"]
    vol_target = params["vol_target"]

    net_flow = _net_leveraged_etf_flow(prices, leverage_set)
    z = _zscore(net_flow, lookback)
    signal = pd.Series(0.0, index=prices.index)
    signal = signal.where(z <= 0, -1.0)  # short on positive flow
    signal = signal.where(z >= 0, 1.0)   # long on negative flow

    spy_ret = _compute_returns(prices, "SPY")
    vscale = _vol_scale(spy_ret, vol_target)
    pos = (signal * vol_target * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    strat_ret = pos.shift(1).fillna(0.0) * spy_ret
    return strat_ret


def _make_flat_returns(prices: pd.DataFrame) -> pd.Series:
    """Falsifier: always flat."""
    spy_ret = _compute_returns(prices, "SPY")
    return pd.Series(0.0, index=prices.index)


def _make_random_flow_returns(prices: pd.DataFrame, params: dict) -> pd.Series:
    """Falsifier: random flow signs (shuffle leveraged ETF return signs)."""
    rng = np.random.default_rng(SEED)
    leverage_set_name = params["leverage_set"]
    leverage_set = LEVERAGE_SETS[leverage_set_name]
    lookback = params["lookback"]
    vol_target = params["vol_target"]

    # Compute net flow with randomized signs
    spy_ret = _compute_returns(prices, "SPY")
    flows = []
    for etf in leverage_set:
        etf_ret = _compute_returns(prices, etf)
        leverage = LEVERAGED_ETFS[etf]
        aum = AUM_ESTIMATES[etf]
        flow = aum * leverage * etf_ret
        flows.append(flow)

    net_flow = pd.concat(flows, axis=1).sum(axis=1)

    # Randomize signs of the net flow
    valid = net_flow.notna()
    if valid.any():
        signs = net_flow[valid].to_numpy().copy()
        rng.shuffle(signs)
        net_flow_rand = net_flow.copy()
        net_flow_rand.loc[valid] = signs * np.abs(net_flow_rand.loc[valid])
        net_flow = net_flow_rand

    z = _zscore(net_flow, lookback)
    signal = pd.Series(0.0, index=prices.index)
    signal = signal.where(z <= 0, 1.0)
    signal = signal.where(z >= 0, -1.0)

    vscale = _vol_scale(spy_ret, vol_target)
    pos = (signal * vol_target * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    strat_ret = pos.shift(1).fillna(0.0) * spy_ret
    return strat_ret


def _make_equal_weight_returns(prices: pd.DataFrame, params: dict) -> pd.Series:
    """Falsifier: equal-weight leveraged ETF basket (vs AUM-weighted)."""
    leverage_set_name = params["leverage_set"]
    leverage_set = LEVERAGE_SETS[leverage_set_name]
    lookback = params["lookback"]
    vol_target = params["vol_target"]

    # Equal weight flow: AUM = 1 for all
    spy_ret = _compute_returns(prices, "SPY")
    flows = []
    for etf in leverage_set:
        etf_ret = _compute_returns(prices, etf)
        leverage = LEVERAGED_ETFS[etf]
        flow = 1.0 * leverage * etf_ret  # equal weight
        flows.append(flow)

    net_flow = pd.concat(flows, axis=1).sum(axis=1)
    z = _zscore(net_flow, lookback)
    signal = pd.Series(0.0, index=prices.index)
    signal = signal.where(z <= 0, 1.0)
    signal = signal.where(z >= 0, -1.0)

    vscale = _vol_scale(spy_ret, vol_target)
    pos = (signal * vol_target * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    strat_ret = pos.shift(1).fillna(0.0) * spy_ret
    return strat_ret


def main() -> None:
    t0 = time.time()
    print(f"[{EXPERIMENT_DESC}]")
    data = _fetch_all_data()
    prices = _align_and_merge(data)
    train, val, test = _splits(prices.index)
    oos = val | test
    cfg = _cfg()

    # Benchmark: buy-and-hold SPY
    bench_ret = _benchmark_returns(prices)
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
    # Buy-hold SPY
    bench_pos = pd.Series(1.0, index=prices.index)
    ablations["buy_hold_spy"] = _period_metrics(bench_oos_ret, _count_trades(bench_pos, oos))
    # Always flat
    flat_ret = _make_flat_returns(prices)
    flat_pos = pd.Series(0.0, index=prices.index)
    p_flat = _make_synthetic_price(flat_ret)
    s_flat = pd.DataFrame(1.0, index=p_flat.index, columns=["STRAT"])
    flat_res = run_backtest(prices=p_flat, signals=s_flat, volumes=None, config=cfg)
    ablations["always_flat"] = _period_metrics(
        flat_res.returns[oos].dropna(), _count_trades(flat_pos, oos)
    )
    # Inverse signal
    inv_ret = _make_inverse_returns(prices, best)
    leverage_set = LEVERAGE_SETS[best["leverage_set"]]
    spy_ret = _compute_returns(prices, "SPY")
    net_flow = _net_leveraged_etf_flow(prices, leverage_set)
    z = _zscore(net_flow, best["lookback"])
    inv_signal = pd.Series(0.0, index=prices.index)
    inv_signal = inv_signal.where(z <= 0, -1.0)
    inv_signal = inv_signal.where(z >= 0, 1.0)
    vscale = _vol_scale(spy_ret, best["vol_target"])
    inv_pos = (inv_signal * best["vol_target"] * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    p_inv = _make_synthetic_price(inv_ret)
    s_inv = pd.DataFrame(1.0, index=p_inv.index, columns=["STRAT"])
    inv_res = run_backtest(prices=p_inv, signals=s_inv, volumes=None, config=cfg)
    ablations["inverse_signal"] = _period_metrics(
        inv_res.returns[oos].dropna(), _count_trades(inv_pos, oos)
    )
    # Random flow control
    rand_ret = _make_random_flow_returns(prices, best)
    rand_signal = pd.Series(0.0, index=prices.index)
    net_flow_rand = _net_leveraged_etf_flow(prices, leverage_set)
    valid = net_flow_rand.notna()
    if valid.any():
        signs = net_flow_rand[valid].to_numpy().copy()
        np.random.default_rng(SEED).shuffle(signs)
        net_flow_rand.loc[valid] = signs * np.abs(net_flow_rand.loc[valid])
    z_rand = _zscore(net_flow_rand, best["lookback"])
    rand_signal = rand_signal.where(z_rand <= 0, 1.0)
    rand_signal = rand_signal.where(z_rand >= 0, -1.0)
    rand_pos = (rand_signal * best["vol_target"] * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    p_rand = _make_synthetic_price(rand_ret)
    s_rand = pd.DataFrame(1.0, index=p_rand.index, columns=["STRAT"])
    rand_res = run_backtest(prices=p_rand, signals=s_rand, volumes=None, config=cfg)
    ablations["random_flow_control"] = _period_metrics(
        rand_res.returns[oos].dropna(), _count_trades(rand_pos, oos)
    )
    # Equal-weight basket
    eqw_ret = _make_equal_weight_returns(prices, best)
    eqw_flows = []
    for etf in leverage_set:
        etf_ret = _compute_returns(prices, etf)
        leverage = LEVERAGED_ETFS[etf]
        eqw_flows.append(1.0 * leverage * etf_ret)
    eqw_net_flow = pd.concat(eqw_flows, axis=1).sum(axis=1)
    eqw_z = _zscore(eqw_net_flow, best["lookback"])
    eqw_signal = pd.Series(0.0, index=prices.index)
    eqw_signal = eqw_signal.where(eqw_z <= 0, 1.0)
    eqw_signal = eqw_signal.where(eqw_z >= 0, -1.0)
    eqw_pos = (eqw_signal * best["vol_target"] * vscale).clip(-MAX_POS, MAX_POS).fillna(0.0)
    p_eqw = _make_synthetic_price(eqw_ret)
    s_eqw = pd.DataFrame(1.0, index=p_eqw.index, columns=["STRAT"])
    eqw_res = run_backtest(prices=p_eqw, signals=s_eqw, volumes=None, config=cfg)
    ablations["equal_weight_basket"] = _period_metrics(
        eqw_res.returns[oos].dropna(), _count_trades(eqw_pos, oos)
    )

    out = {
        "nf_id": "NF-20261109-17",
        "h_id": "H170",
        "verdict": verdict,
        "gates": f"{pass_count}/8",
        "gate_detail": gates,
        "best": best,
        "train": train_ev,
        "oos": oos_ev,
        "ablations": ablations,
        "elapsed_s": round(time.time() - t0, 2),
    }
    out_dir = ROOT / ".experiments" / "nf_runs" / "nf_20261109_17_leveraged_etf_rebalancing"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    pd.DataFrame(grid_rows).to_csv(out_dir / "grid.csv", index=False)
    meta = {
        "nf_id": "NF-20261109-17",
        "h_id": "H170",
        "universe": ["SPY"] + list(LEVERAGED_ETFS.keys()),
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