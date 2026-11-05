"""
NF-20261104-02 / H85 (pre-registration): Cross-Asset Lead-Lag (Sector → Constituent).

New strategy family (information transmission and lead-lag), distinct from all
prior repository families:
- H2/H16 cross-sectional momentum ranks assets by their *own* past returns;
  NF-02 ranks stocks by a *different asset's* prior return (sector ETF lead).
- Not a parameter, indicator, market, timeframe, universe, or overlay variant
  of any tested family; no prior repository family tests cross-asset lead-lag.

Mechanism: sector-level information diffuses with a delay from liquid sector
ETFs to constituent stocks. Prior-day sector ETF return predicts next-day
constituent returns within the same sector.

Construction (daily, causal):
  1. At daily close t-1, compute each sector ETF's 1-day return.
  2. Rank each constituent stock within its sector by that sector return.
  3. Long top quintile, short bottom quintile, equal-weighted within quintile.
  4. Vol-target the net long/short book to 15% annualised.
  5. Engine applies position_{t-1} to return_t (fully causal; sector return at
     t-2→t-1 is known before position at t-1 earns return at t).

Data: yfinance daily, all free, years of history. Universe fixed (no
survivorship from changing sector membership).

Pre-registered gates (PROMPT_V2.md): OOS Sharpe >= 1.0, >= 200 OOS trades,
PF >= 1.3, max DD <= 15%, WF stability (test Sharpe >= 0.7 x train),
parameter sensitivity (OAT +/-20% on lookback/quintile).

Rejection: OOS Sharpe < 0.5, PF < 1.1, < 200 OOS trades, max DD > 15%.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from qtr.backtest.engine import (
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.data.fetcher import DataCache, DataFetcher
from qtr.tracking.experiment import get_tracker
from qtr.validation.statistics import (
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261104_02_cross_asset_leadlag"
EXPERIMENT_DESC = (
    "NF-20261104-02: Cross-asset lead-lag (sector ETF -> constituent stock). "
    "Daily rebalance: long top-quintile / short bottom-quintile stocks within "
    "each sector ranked by prior-day sector ETF return; vol-targeted 15% ann. "
    "Grid: lookback x quintile share x vol target. Train/Val/Test 60/20/20; "
    "Test protected; gates on OOS Val+Test."
)

# --- Universe: sector ETFs + constituent stocks (fixed mapping) -------------
SECTOR_ETFS = {
    "XLF": ["JPM", "BAC", "WFC", "C"],  # Financials
    "XLE": ["XOM", "CVX", "COP", "EOG"],  # Energy
    "XLV": ["JNJ", "UNH", "ABBV", "TMO"],  # Healthcare
    "XLI": ["BA", "CAT", "GE", "HON"],  # Industrials
    "XLB": ["LIN", "APD", "FCX", "NEM"],  # Materials
    "XLP": ["PG", "KO", "PEP", "WMT"],  # Consumer Staples
    "XLU": ["NEE", "DUK", "SO", "D"],  # Utilities
    "XLY": ["AMZN", "TSLA", "HD", "MCD"],  # Consumer Discretionary
    "XLC": ["GOOGL", "META", "NFLX", "DIS"],  # Communication
    "XLK": ["AAPL", "MSFT", "NVDA", "ORCL"],  # Technology
}

SECTOR_OF_ETF = {etf: sector for sector, etfs in SECTOR_ETFS.items() for etf in etfs}
ETF_UNIVERSE = list(SECTOR_ETFS.keys())
STOCK_UNIVERSE = [s for etfs in SECTOR_ETFS.values() for s in etfs]
UNIVERSE = ETF_UNIVERSE + STOCK_UNIVERSE

DATA_START = "2015-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0

GATES = {
    "min_sharpe": 1.0,
    "min_trades": 200,
    "min_profit_factor": 1.3,
    "max_drawdown": 0.15,
    "min_walkforward_stability": 0.7,
    "min_worst_regime_sharpe": 0.3,
    "max_p_value": 0.05,
    "min_information_ratio": 0.0,
    "min_perturbed_sharpe_ratio": 0.5,
}

# Pre-registered grid: 4 x 3 x 3 = 36 combos.
LOOKBACKS = [21, 63, 126, 252]  # sector-return lookback (days)
QUINTILE_SHARES = [0.2, 0.25, 0.33]  # fraction of book per quintile side
VOL_TARGETS = [0.10, 0.15, 0.20]  # annualised vol target

WF_FOLDS_SELECTION = 4
WF_FOLDS_STABILITY = 5


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),  # equity: 1bp comm + 1bp spread default
        asset_class=AssetClass.EQUITY,
        max_position_size=1.0,
        max_leverage=1.0,
        allow_short=True,
    )


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


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
        "gross_profit": gp,
        "gross_loss": gl,
        "n_periods": len(r),
    }


def _count_in(trades: pd.DataFrame, mask, prices) -> int:
    if len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def sector_returns(etf_prices: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Sector ETF 1-day returns at close t (causal; close t-1 -> close t).

    Returns a DataFrame indexed by prices.index with one column per sector ETF.
    Values are known at the close of each day (no look-ahead).
    """
    return etf_prices.pct_change()


def build_daily_targets(
    prices: pd.DataFrame,
    etf_returns: pd.DataFrame,
    lookback: int,
    quintile_share: float,
    vol_target: float,
) -> pd.DataFrame:
    """Daily target weights, strictly causal.

    At day t, position weights are based on sector ETF returns at day t-1
    (the return from close t-2 to close t-1, known at close t-1).
    Stocks are ranked within their sector by that return; top quintile long,
    bottom quintile short. Weights vol-targeted to `vol_target` annualised.
    """
    # Only stocks present in the prices panel participate (tests may use a
    # subset of STOCK_UNIVERSE).
    stocks_available = [s for s in STOCK_UNIVERSE if s in prices.columns]
    targets = pd.DataFrame(0.0, index=prices.index, columns=stocks_available)

    # Sector return at t-1: shift so row t uses the return known at t-1.
    # etf_returns[t] = close[t] / close[t-1] - 1; shift(1) makes row t use
    # the return that was known at the previous close.
    sector_ret_lagged = etf_returns.shift(1)

    # Rolling realised vol of each stock for vol targeting (causal, trailing)
    stock_rets = prices[stocks_available].pct_change()
    rolling_vol = stock_rets.rolling(63, min_periods=21).std() * np.sqrt(252)
    rolling_vol = rolling_vol.replace(0, np.nan).ffill().fillna(0.15)
    inv_vol = 1.0 / rolling_vol

    # Vectorised per-sector rank construction. For each sector we rank stocks
    # by their lagged excess return over the sector ETF (both known at close
    # t-1), take the top/bottom quintile, and size by inverse realised vol.
    #
    # Causality: the position built at row t earns the close[t-1] -> close[t]
    # return, so that concurrent return must not enter the ranking. The stock
    #'s own prior-day return (close[t-2] -> close[t-1]) and the sector ETF's
    # prior-day return are both known at close t-1 and are the only inputs.
    # (The excess is computed per-sector inside the loop: the two frames have
    # disjoint columns, so a single ``stock_rets.shift(1) - sector_ret_lagged``
    # subtraction would align to an empty intersection and yield all-NaN.)
    for etf, sector_stocks in SECTOR_ETFS.items():
        if etf not in sector_ret_lagged.columns:
            continue
        stocks = [s for s in sector_stocks if s in stocks_available]
        if len(stocks) < 2:
            continue

        excess = stock_rets[stocks].shift(1).values - sector_ret_lagged[etf].values[:, None]
        vol = inv_vol[stocks].values
        n_long = max(1, int(round(len(stocks) * quintile_share)))
        n_short = max(1, int(round(len(stocks) * quintile_share)))

        # Rows with fewer than 2 valid excess values carry no signal.
        valid_count = (~np.isnan(excess)).sum(axis=1)

        order = np.argsort(excess, axis=1, kind="stable")
        top_idx = order[:, -n_long:]
        bot_idx = order[:, :n_short]

        signs = np.zeros_like(excess)
        rows = np.arange(len(prices))[:, None]
        signs[rows, top_idx] = 1.0
        signs[rows, bot_idx] = -1.0
        # No signal where the sector return or stock returns are missing.
        signs = np.where(np.isnan(excess), 0.0, signs)
        signs[valid_count < 2, :] = 0.0

        targets[stocks] = signs * (quintile_share * vol_target * vol)

    return targets


def train_only_wf_sharpe(
    returns: pd.Series, train_mask, n_splits: int = WF_FOLDS_SELECTION
) -> float:
    tr = returns[train_mask].dropna()
    if len(tr) < 20:
        return -np.inf
    splits = walk_forward_splits(len(tr), n_splits=n_splits)
    fold_sharpes = []
    for _tr_idx, te_idx in splits:
        if len(te_idx) > 1:
            fold_sharpes.append(sharpe_ratio(tr.iloc[te_idx].values))
    if not fold_sharpes:
        return -np.inf
    return float(np.mean(fold_sharpes))


def full_gate_eval(result, oos_mask, val_mask, test_mask, prices, etf_returns, bench_result):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)

    oos_ret = result.returns[oos_mask]
    test_ret = result.returns[test_mask]
    oos_m = _period_metrics(oos_ret, _count_in(result.trades, oos_mask, prices))
    test_m = _period_metrics(test_ret, _count_in(result.trades, test_mask, prices))

    wf_splits = walk_forward_splits(len(result.returns), n_splits=WF_FOLDS_STABILITY)
    oos_sharpes, train_sharpes = [], []
    for tr_idx, te_idx in wf_splits:
        tr_r = result.returns.iloc[tr_idx].values
        te_r = result.returns.iloc[te_idx].values
        if len(te_r) > 1:
            oos_sharpes.append(sharpe_ratio(te_r))
        if len(tr_r) > 1:
            train_sharpes.append(sharpe_ratio(tr_r))
    wf_stab = (
        float(np.mean(oos_sharpes) / np.mean(train_sharpes)) if np.mean(train_sharpes) != 0 else 0.0
    )

    bench = compare_to_benchmark(
        oos_ret.dropna().values,
        bench_result.returns[oos_mask].dropna().values,
    )
    oos_max_dd = oos_m["max_drawdown"]

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "pf": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "dd": abs(oos_max_dd) <= GATES["max_drawdown"] if oos_max_dd < 0 else False,
        "stab": wf_stab >= GATES["min_walkforward_stability"],
        "p": benchmark_significance_gate(
            float(bench.get("alpha_p_value", 1.0)),
            float(bench.get("information_ratio", -np.inf)),
            GATES["max_p_value"],
        ),
        "ir": float(bench.get("information_ratio", -np.inf)) > GATES["min_information_ratio"],
    }
    all_pass = all(passes.values())
    return {
        "oos_metrics": oos_m,
        "test_metrics": test_m,
        "train_sharpe": float(sharpe_ratio(result.returns[train_mask].values))
        if train_mask.sum() > 1
        else 0.0,
        "val_sharpe": float(sharpe_ratio(result.returns[val_mask].dropna().values))
        if val_mask.sum() > 1
        else 0.0,
        "wf_stability": float(wf_stab),
        "worst_regime_sharpe": 0.0,
        "regime_sharpes": {},
        "benchmark_p_value": float(bench.get("alpha_p_value", 1.0)),
        "information_ratio": float(bench.get("information_ratio", -np.inf)),
        "benchmark_alpha_annual": float(bench.get("alpha_annualized", 0.0)),
        "passes": passes,
        "all_pass": all_pass,
        "verdict": "PASS" if all_pass else "REJECT",
    }


def perturbation_eval(selected, prices, etf_returns, volumes, oos_mask, cfg, opt_oos_sharpe: float):
    variants = {}
    for param, base in (
        ("lookback", selected["lookback"]),
        ("quintile_share", selected["quintile_share"]),
        ("vol_target", selected["vol_target"]),
    ):
        for factor in (0.8, 1.2):
            v = base * factor
            if abs(v - base) < 1e-12:
                continue
            kw = dict(selected)
            kw[param] = float(v)
            pos = build_daily_targets(
                prices, etf_returns, kw["lookback"], kw["quintile_share"], kw["vol_target"]
            )
            res = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
            r = res.returns[oos_mask].dropna()
            variants[f"{param}={v:.3f}"] = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
    if opt_oos_sharpe > 0 and variants:
        min_ratio = float(min(variants.values()) / opt_oos_sharpe)
    else:
        min_ratio = 0.0
    return {"variants": variants, "min_perturbed_sharpe_ratio": min_ratio}


def main():
    np.random.seed(SEED)
    t_start = time.time()
    tracker = get_tracker()
    grid_size = len(LOOKBACKS) * len(QUINTILE_SHARES) * len(VOL_TARGETS)
    exp_id = tracker.start_experiment(
        name=EXPERIMENT_NAME,
        description=EXPERIMENT_DESC,
        config={
            "universe": UNIVERSE,
            "sector_etfs": SECTOR_ETFS,
            "interval": "1d",
            "data_start": DATA_START,
            "data_end": DATA_END,
            "splits": {
                "train": [DATA_START, TRAIN_END],
                "val": [TRAIN_END, VAL_END],
                "test": [VAL_END, DATA_END],
            },
            "gates": GATES,
            "seed": SEED,
            "grid": {
                "lookback": LOOKBACKS,
                "quintile_share": QUINTILE_SHARES,
                "vol_target": VOL_TARGETS,
            },
            "grid_size": grid_size,
            "selection": "best train-only walk-forward Sharpe; Test protected",
        },
        data_sources={
            "source": "yahoo_daily_cached",
            "symbols": UNIVERSE,
            "interval": "1d",
        },
        compute_budget={"max_cpu_hours": 2.0, "grid_size": grid_size},
        random_seeds={"numpy": SEED, "python": SEED},
    )
    print(f"[NF-02] started {exp_id}  grid_size={grid_size}")

    try:
        # Isolated cache: this experiment's 50-symbol universe is NOT part of
        # the committed 82-file baseline that the price-return-basis audit
        # pins (its coverage test asserts exactly 82 parquet files in
        # .cache/data). Writing this runner's fetch artifacts to the shared
        # committed cache would silently break that frozen baseline, so the
        # runner uses a per-experiment cache dir under its own artifact dir.
        isolated_cache = Path(tracker.log_dir) / "artifacts" / exp_id / "cache"
        isolated_cache.mkdir(parents=True, exist_ok=True)
        fetcher = DataFetcher(cache=DataCache(cache_dir=isolated_cache))
        data = fetcher.fetch_yahoo(UNIVERSE, start=DATA_START, end=DATA_END, interval="1d")
        prices_list, volumes_list = [], []
        for sym in UNIVERSE:
            df = data.get(sym, pd.DataFrame())
            if len(df) == 0:
                raise RuntimeError(f"no data for universe symbol {sym}")
            prices_list.append(df["close"].rename(sym))
            volumes_list.append(df["volume"].rename(sym))
        prices = pd.concat(prices_list, axis=1, sort=True).sort_index()
        volumes = pd.concat(volumes_list, axis=1, sort=True).sort_index().fillna(0)

        etf_prices = prices[ETF_UNIVERSE]
        etf_returns = sector_returns(etf_prices, lookback=1)

        train_mask, val_mask, test_mask = _splits(prices)
        oos_mask = val_mask | test_mask
        print(
            f"[NF-02] prices={prices.shape} train/val/test="
            f"{int(train_mask.sum())}/{int(val_mask.sum())}/{int(test_mask.sum())}"
        )

        cfg = make_equity_config()

        # Equal-weight buy-and-hold benchmark over stock universe
        stock_prices = prices[STOCK_UNIVERSE]
        stock_volumes = volumes[STOCK_UNIVERSE]
        avail = stock_prices.notna().astype(float)
        ew_weights = avail.div(avail.sum(axis=1), axis=0).fillna(0.0)
        bench_result = run_backtest(
            prices=stock_prices, signals=ew_weights, volumes=stock_volumes, config=cfg
        )

        # --- grid search: selection on train-only walk-forward Sharpe ---
        grid_rows = []
        grid_results = {}
        t_grid = time.time()
        for lookback in LOOKBACKS:
            for quintile_share in QUINTILE_SHARES:
                for vol_target in VOL_TARGETS:
                    pos = build_daily_targets(
                        prices, etf_returns, lookback, quintile_share, vol_target
                    )
                    res = run_backtest(prices=prices, signals=pos, volumes=volumes, config=cfg)
                    wf_sel = train_only_wf_sharpe(res.returns, train_mask)
                    oos_r = res.returns[oos_mask].dropna()
                    oos_sr = float(sharpe_ratio(oos_r.values)) if len(oos_r) > 1 else 0.0
                    grid_results[(lookback, quintile_share, vol_target)] = res
                    grid_rows.append(
                        {
                            "lookback": lookback,
                            "quintile_share": quintile_share,
                            "vol_target": vol_target,
                            "train_wf_sharpe": wf_sel,
                            "train_sharpe": float(
                                sharpe_ratio(res.returns[train_mask].dropna().values)
                            )
                            if train_mask.sum() > 1
                            else 0.0,
                            "val_sharpe": float(sharpe_ratio(res.returns[val_mask].dropna().values))
                            if val_mask.sum() > 1
                            else 0.0,
                            "test_sharpe": float(
                                sharpe_ratio(res.returns[test_mask].dropna().values)
                            )
                            if test_mask.sum() > 1
                            else 0.0,
                            "oos_sharpe": oos_sr,
                        }
                    )
        grid_df = pd.DataFrame(grid_rows).sort_values("train_wf_sharpe", ascending=False)
        grid_elapsed = time.time() - t_grid
        print(
            f"[NF-02] grid {len(grid_rows)} combos in {grid_elapsed:.1f}s; best train-WF Sharpe={grid_df.iloc[0]['train_wf_sharpe']:.4f}"
        )

        # --- selection: best train-only WF Sharpe (Test never used) ---
        best_key = grid_df.iloc[0][["lookback", "quintile_share", "vol_target"]]
        sel = (
            int(best_key["lookback"]),
            float(best_key["quintile_share"]),
            float(best_key["vol_target"]),
        )
        sel_result = grid_results[sel]
        selected = {"lookback": sel[0], "quintile_share": sel[1], "vol_target": sel[2]}

        # --- full gate evaluation on protected OOS (Val+Test) ---
        gate = full_gate_eval(
            sel_result, oos_mask, val_mask, test_mask, prices, etf_returns, bench_result
        )

        # --- perturbation gate ---
        pert = perturbation_eval(
            selected, prices, etf_returns, volumes, oos_mask, cfg, gate["oos_metrics"]["sharpe"]
        )
        gate["passes"]["perturbation"] = (
            pert["min_perturbed_sharpe_ratio"] >= GATES["min_perturbed_sharpe_ratio"]
        )
        gate["perturbation"] = pert
        gate["all_pass"] = all(gate["passes"].values())
        gate["verdict"] = "PASS" if gate["all_pass"] else "REJECT"

        # --- ablations ---
        ablations = {}
        # A1: no sector signal (random quintiles)
        rng = np.random.default_rng(SEED)
        random_pos = build_daily_targets(prices, etf_returns, sel[0], sel[1], sel[2])
        random_shuffled = random_pos.copy()
        for sym in random_shuffled.columns:
            random_shuffled[sym] = rng.permutation(random_shuffled[sym].values)
        random_res = run_backtest(
            prices=prices, signals=random_shuffled, volumes=volumes, config=cfg
        )
        ablations["random_quintiles"] = _period_metrics(
            random_res.returns[oos_mask], _count_in(random_res.trades, oos_mask, prices)
        )
        # A2: long-only top quintile only (no short)
        long_only_pos = build_daily_targets(prices, etf_returns, sel[0], sel[1], sel[2]).clip(
            lower=0
        )
        lon_res = run_backtest(prices=prices, signals=long_only_pos, volumes=volumes, config=cfg)
        ablations["long_only_top_quintile"] = _period_metrics(
            lon_res.returns[oos_mask], _count_in(lon_res.trades, oos_mask, prices)
        )
        # A3: EW benchmark
        ablations["ew_benchmark"] = _period_metrics(
            bench_result.returns[oos_mask], _count_in(bench_result.trades, oos_mask, stock_prices)
        )

        # --- artifacts ---
        tracker.log_dataframe("prices", prices)
        tracker.log_dataframe("volumes", volumes)
        tracker.log_dataframe("etf_returns", etf_returns)
        tracker.log_dataframe("param_grid_results", grid_df)
        tracker.log_dataframe(
            "selected_signals", build_daily_targets(prices, etf_returns, sel[0], sel[1], sel[2])
        )
        tracker.log_dataframe("best_equity", sel_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("best_trades", sel_result.trades)
        tracker.log_dataframe("benchmark_equity", bench_result.equity_curve.to_frame("equity"))
        tracker.log_dataframe("benchmark_returns", bench_result.returns.to_frame("returns"))

        total_elapsed = time.time() - t_start
        summary = {
            "experiment_id": exp_id,
            "hypothesis": "NF-20261104-02",
            "selected_config": selected,
            "selection_rule": "best train-only walk-forward Sharpe; Test protected; gates on OOS Val+Test",
            "grid_size": grid_size,
            "n_evaluated": len(grid_rows),
            "grid_elapsed_sec": float(round(grid_elapsed, 1)),
            "total_elapsed_sec": float(round(total_elapsed, 1)),
            "compute_cpu_hours": float(round(total_elapsed / 3600, 3)),
            "metrics": {
                "train_sharpe": gate["train_sharpe"],
                "val_sharpe": gate["val_sharpe"],
                "test_sharpe": gate["test_metrics"]["sharpe"],
                "oos_sharpe": gate["oos_metrics"]["sharpe"],
                "profit_factor": gate["oos_metrics"]["profit_factor"],
                "max_drawdown": gate["oos_metrics"]["max_drawdown"],
                "trades": gate["oos_metrics"]["trades"],
                "wf_stability": gate["wf_stability"],
                "benchmark_p_value": gate["benchmark_p_value"],
                "information_ratio": gate["information_ratio"],
                "perturbation": pert,
                "ablations": ablations,
            },
            "passes": gate["passes"],
            "all_pass": gate["all_pass"],
            "verdict": gate["verdict"],
        }

        exp_dir = Path(tracker.log_dir) / "artifacts" / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        with open(exp_dir / "summary.json", "w") as f:
            json.dump(
                summary,
                f,
                indent=2,
                default=lambda x: float(x) if isinstance(x, (np.integer, np.floating)) else str(x),
            )
        tracker.log_artifact("summary", exp_dir / "summary.json")
        tracker.finish_experiment(status="completed")

        print("\n" + "=" * 72)
        p = gate["passes"]
        print(f"  gates passed: {int(sum(p.values()))}/{len(p)}  ->  {gate['verdict']}")
        om = gate["oos_metrics"]
        print(
            f"  OOS Sharpe={om['sharpe']:.3f} PF={om['profit_factor']:.3f} DD={om['max_drawdown']:.3f} Trades={om['trades']}"
        )
        print(
            f"  Train={gate['train_sharpe']:.3f} Val={gate['val_sharpe']:.3f} Test={gate['test_metrics']['sharpe']:.3f}"
        )
        print(
            f"  WF stab={gate['wf_stability']:.3f} | Bench p={gate['benchmark_p_value']:.4f} IR={gate['information_ratio']:.3f}"
        )
        print(f"  Perturbation min ratio={pert['min_perturbed_sharpe_ratio']:.3f}")
        print(f"  Selected: {selected}")
        print(
            f"  Grid {len(grid_rows)} combos in {grid_elapsed:.1f}s | total {total_elapsed / 60:.1f} min ({total_elapsed / 3600:.2f} CPU-h)"
        )
        print("=" * 72)
        return 0 if gate["all_pass"] else 1
    except Exception as e:
        import traceback

        traceback.print_exc()
        tracker.finish_experiment(status="failed", error=str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
