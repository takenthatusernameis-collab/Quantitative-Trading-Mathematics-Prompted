"""NF-20261106-06 / H103 (pre-registered): AUD commodity-currency global
risk-appetite regime timing SPY (continuous exposure).

FXA (Australian dollar ETF) is a pro-cyclical commodity/export currency proxy.
Strengthening AUD signals global risk appetite, commodity-demand optimism, and
carry positioning into risky assets (equity tailwinds); weakening AUD signals
risk-off / carry unwind (equity headwinds). A vol-targeted, continuously scaled
long SPY position is held proportional to the trailing FXA-momentum z-score
(floored at zero, long-only), with a 1-bar execution delay.

New family dimension (commodity-currency risk-appetite / carry-unwind transmission
timing), distinct from H95 (UUP broad USD basket tightening/risk-off; H95 REJECT
3/9, sparse hysteresis 88 OOS trades). NF-06 differs in (1) instrument/channel:
AUD pro-cyclical commodity currency vs broad USD safe-haven basket; (2) signal
direction: FXA strength = risk-on vs UUP strength = risk-off; (3) construction:
continuous exposure scaling (addresses sparsity/trade-count failure mode) rather
than binary hysteresis. Adjacency to H95 (FX/macro -> equity) is acknowledged;
novelty scored honestly as moderate. Distinct from H101 (HG=F/GC=F industrial
metal growth ratio), H102 (BTC/TLT crypto risk appetite), H94 credit, H100
rates-vol.

Causality / timing (pre-registered): FXA trailing momentum z-score for day t uses
prices through close t only (trailing windows, min_periods). Signals are shifted
by 1 bar (signals.shift(1)), so target at close t earns return t -> t+1.

Data: yfinance daily FXA, SPY (free, cached), 2010-01-01 -> 2026-10-31.
Splits (pre-registered): Train 2010-01-01 -> 2019-12-31; Val 2020-01-01 ->
2022-12-31; Test 2023-01-01 -> 2026-10-31 (protected holdout).
Grid: lookback {63,126} x z_window {126,252} x entry_scale {1.0,1.5,2.0} x
vol_target {0.10,0.15} (24 combos). Selection = best train-only 4-fold
walk-forward Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity defaults.

Gates (OOS Val+Test): OOS Sharpe>=1.0, >=200 trades, PF>=1.3, max DD<=15%,
WF stability test>=0.7*train when train>0, worst-regime rolling-252 Sharpe>=0.3,
benchmark p<=0.05 with IR>=0, perturbation min ratio>=0.5.
Rejection: OOS Sharpe<0.5, PF<1.1, max DD>15%, <200 trades.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

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
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261106_06_fxa_risk"
EXPERIMENT_DESC = (
    "NF-20261106-06/H103: AUD commodity-currency (FXA) global risk-appetite "
    "regime timing SPY. Continuous vol-targeted long SPY exposure scaled by "
    "trailing FXA-momentum z-score (long-only), 1-bar delay. Train-only WF "
    "selection; Test protected; gates on OOS Val+Test."
)

FXA = "FXA"
SPY = "SPY"
UNIVERSE = [FXA, SPY]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

LOOKBACKS = [63, 126]
Z_WINDOWS = [126, 252]
ENTRY_SCALES = [1.0, 1.5, 2.0]
VOL_TARGETS = [0.10, 0.15]
WF_FOLDS_SELECTION = 4

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


def make_equity_config() -> BacktestConfig:
    return BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(),
        asset_class=AssetClass.EQUITY,
        max_position_size=MAX_POS,
        max_leverage=1.0,
        allow_short=False,
    )


def _splits(prices: pd.DataFrame):
    train_mask = prices.index <= pd.Timestamp(TRAIN_END)
    val_mask = (prices.index > pd.Timestamp(TRAIN_END)) & (prices.index <= pd.Timestamp(VAL_END))
    test_mask = prices.index > pd.Timestamp(VAL_END)
    return train_mask, val_mask, test_mask


def _align_prices(fetcher: DataFetcher, symbols, start, end) -> pd.DataFrame:
    raw = fetcher.fetch_yahoo(symbols, start=start, end=end)
    if not isinstance(raw, dict):
        raise RuntimeError(f"fetch_yahoo returned {type(raw)}, expected dict")
    closes = {}
    for s in symbols:
        df = raw.get(s)
        if df is None or df.empty:
            raise RuntimeError(f"Data fetch failed for {s}")
        col = (
            "close"
            if "close" in df.columns
            else ("Close" if "Close" in df.columns else df.columns[0])
        )
        close = df[col].astype(float)
        if (close <= 0).any():
            raise RuntimeError(f"Non-positive prices in {s}")
        closes[s] = close.rename(s)
    prices = pd.concat(closes, axis=1).sort_index().ffill().dropna()
    return prices


def build_fxa_signal(
    prices: pd.DataFrame,
    lookback: int,
    z_window: int,
    entry_scale: float,
    vol_target: float,
) -> pd.DataFrame:
    """Continuous causal FXA risk-appetite signal on SPY (no shift here).

    FXA trailing momentum z-score (past-only, min_periods) scaled to [0,1]
    long-only exposure, then vol-targeted. Higher z = AUD strength / risk-on.
    Engine applies signals.shift(1) for 1-bar execution delay.
    """
    if FXA not in prices.columns or SPY not in prices.columns:
        raise ValueError(f"prices must contain {FXA} and {SPY}")
    mom = prices[FXA].pct_change(lookback)
    mp = max(60, z_window // 2)
    z = (mom - mom.rolling(z_window, min_periods=mp).mean()) / mom.rolling(
        z_window, min_periods=mp
    ).std()
    raw = (z / entry_scale).clip(0.0, 1.0)
    spy_ret = prices[SPY].pct_change()
    vol = spy_ret.rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (vol_target / vol.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)
    sig = (raw * scale * MAX_POS).fillna(0.0)
    return pd.DataFrame({SPY: sig}, index=prices.index)


def _trade_count(result) -> int:
    return int(result.metrics.get("num_trades", 0))


def _wf_stability(train_rets: pd.Series, n_splits: int = 4) -> float:
    if len(train_rets) < n_splits * 60:
        return 0.0
    wfs = []
    for tr_i, te_i in walk_forward_splits(len(train_rets), n_splits=n_splits):
        if len(te_i) < 20:
            continue
        wfs.append(sharpe_ratio(train_rets.iloc[te_i]))
    return float(np.nanmean(wfs)) if wfs else 0.0


def _worst_regime_sharpe(returns: pd.Series, window: int = 252) -> float:
    if len(returns) < window:
        return float("nan")
    rolling = returns.rolling(window).apply(lambda x: sharpe_ratio(x.values), raw=False)
    return float(rolling.min())


def _perturbation_ratio(
    prices: pd.DataFrame,
    oos_mask: pd.Series,
    best: dict,
    base_sharpe: float,
    cfg: BacktestConfig,
) -> float:
    if base_sharpe == 0 or not np.isfinite(base_sharpe):
        return 0.0
    ratios = []
    for key, deltas in [
        ("lookback", [-0.2, 0.2]),
        ("z_window", [-0.2, 0.2]),
        ("entry_scale", [-0.2, 0.2]),
        ("vol_target", [-0.2, 0.2]),
    ]:
        for d in deltas:
            p = dict(best)
            val = p[key]
            p[key] = type(val)(val * (1 + d)) if isinstance(val, int) else val * (1 + d)
            if key in ("lookback", "z_window"):
                p[key] = max(20, int(round(p[key])))
            try:
                sig = build_fxa_signal(prices, **p)
                r = run_backtest(prices.loc[oos_mask, [SPY]], sig.loc[oos_mask], cfg)
                s = float(r.metrics.get("sharpe", 0.0))
                if np.isfinite(s):
                    ratios.append(s / base_sharpe)
            except Exception:
                pass
    return float(min(ratios)) if ratios else 0.0


def evaluate_gates(
    oos_result,
    train_result,
    bench_result,
    prices: pd.DataFrame,
    oos_mask: pd.Series,
    best: dict,
    cfg: BacktestConfig,
) -> dict:
    oos_sh = float(oos_result.metrics.get("sharpe", 0.0))
    train_sh = float(train_result.metrics.get("sharpe", 0.0))
    trades = _trade_count(oos_result)
    pf = float(oos_result.metrics.get("profit_factor", 0.0))
    mdd = abs(float(oos_result.metrics.get("max_drawdown", 1.0)))
    wf = oos_sh / train_sh if train_sh > 0 else 0.0
    worst = _worst_regime_sharpe(oos_result.returns)
    cmp = compare_to_benchmark(oos_result.returns, bench_result.returns)
    pval = cmp.get("p_value")
    ir = cmp.get("information_ratio")
    pert = _perturbation_ratio(prices, oos_mask, best, oos_sh, cfg)
    gates = {
        "sharpe>=1.0": oos_sh >= GATES["min_sharpe"],
        "trades>=200": trades >= GATES["min_trades"],
        "pf>=1.3": pf >= GATES["min_profit_factor"],
        "max_dd<=15%": mdd <= GATES["max_drawdown"],
        "wf_stability>=0.7*train": wf >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe>=0.3": (
            np.isfinite(worst) and worst >= GATES["min_worst_regime_sharpe"]
        ),
        "benchmark_p<=0.05": (pval is not None and float(pval) <= GATES["max_p_value"]),
        "ir>=0": (ir is not None and float(ir) >= GATES["min_information_ratio"]),
        "perturbation_min_ratio>=0.5": pert >= GATES["min_perturbed_sharpe_ratio"],
    }
    return {
        "gates": gates,
        "gates_passed": sum(gates.values()),
        "gates_total": len(gates),
        "metrics": {
            "oos_sharpe": oos_sh,
            "train_sharpe": train_sh,
            "trades": trades,
            "profit_factor": pf,
            "max_drawdown": mdd,
            "wf_stability_ratio": wf,
            "worst_regime_sharpe_252": worst,
            "benchmark_p_value": pval,
            "information_ratio": ir,
            "perturbation_min_ratio": pert,
        },
        "benchmark_comparison": {
            k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in cmp.items()
        },
    }


def run_ablations(
    prices: pd.DataFrame,
    oos_mask: pd.Series,
    best: dict,
    cfg: BacktestConfig,
):
    rng = np.random.default_rng(SEED)
    base_sig = build_fxa_signal(prices, **best).loc[oos_mask]
    po = prices.loc[oos_mask, [SPY]]

    def met(r):
        return {
            k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
            for k, v in r.metrics.items()
        }

    # random-exposure-matched
    vals = base_sig[SPY].values.copy()
    rng.shuffle(vals)
    rand_sig = pd.DataFrame({SPY: vals}, index=base_sig.index)
    r_rand = run_backtest(po, rand_sig, cfg)

    # buy-hold
    bh = pd.DataFrame({SPY: np.full(len(po), MAX_POS)}, index=po.index)
    r_bh = run_backtest(po, bh, cfg)

    # inverse: low FXA z (risk-off/carry unwind) -> long (opposite of pre-reg direction)
    mom = prices[FXA].pct_change(best["lookback"])
    mp = max(60, best["z_window"] // 2)
    z = (mom - mom.rolling(best["z_window"], min_periods=mp).mean()) / mom.rolling(
        best["z_window"], min_periods=mp
    ).std()
    raw_inv = ((-z) / best["entry_scale"]).clip(0.0, 1.0)
    vol = prices[SPY].pct_change().rolling(21, min_periods=21).std() * np.sqrt(252)
    scale = (best["vol_target"] / vol.replace(0.0, np.nan)).clip(0.0, 1.0).fillna(0.0)
    inv_sig = pd.DataFrame({SPY: (raw_inv * scale * MAX_POS).fillna(0.0)}, index=prices.index).loc[
        oos_mask
    ]
    r_inv = run_backtest(po, inv_sig, cfg)

    return {
        "random_exposure_matched": met(r_rand),
        "buy_hold_spy": met(r_bh),
        "inverse_risk_off_long": met(r_inv),
    }


def main():
    start = time.time()
    tracker = get_tracker()
    tracker.start_experiment(EXPERIMENT_NAME, EXPERIMENT_DESC)
    cfg = make_equity_config()
    cache = DataCache(cache_dir=Path(".experiments/nf_runs/nf_20261106_06_fxa_risk/cache"))
    fetcher = DataFetcher(cache=cache)

    print(f"Fetching {UNIVERSE} {DATA_START}..{DATA_END}")
    prices = _align_prices(fetcher, UNIVERSE, DATA_START, DATA_END)
    train_mask, val_mask, test_mask = _splits(prices)
    oos_mask = val_mask | test_mask
    print(
        f"Rows: total={len(prices)} train={train_mask.sum()} val={val_mask.sum()} test={test_mask.sum()}"
    )

    grid = [
        dict(lookback=lb, z_window=zw, entry_scale=es, vol_target=vt)
        for lb in LOOKBACKS
        for zw in Z_WINDOWS
        for es in ENTRY_SCALES
        for vt in VOL_TARGETS
    ]
    print(f"Grid size: {len(grid)}")

    rows = []
    train_prices = prices.loc[train_mask, [SPY]]
    for i, params in enumerate(grid, 1):
        sig = build_fxa_signal(prices, **params)
        tr_sig = sig.loc[train_mask]
        r_tr = run_backtest(train_prices, tr_sig, cfg)
        wf = _wf_stability(r_tr.returns, n_splits=WF_FOLDS_SELECTION)
        rows.append(
            {
                "params": params,
                "train_sharpe": float(r_tr.metrics.get("sharpe", 0.0)),
                "train_wf_sharpe": wf,
                "train_trades": _trade_count(r_tr),
            }
        )
        if i % 6 == 0 or i == len(grid):
            print(f"  {i}/{len(grid)}")
    rows.sort(key=lambda r: r["train_wf_sharpe"], reverse=True)
    best = rows[0]["params"]
    print(f"Selected (train-only WF): {best} wf={rows[0]['train_wf_sharpe']:.4f}")

    sig_best = build_fxa_signal(prices, **best)
    r_train = run_backtest(train_prices, sig_best.loc[train_mask], cfg)
    r_oos = run_backtest(prices.loc[oos_mask, [SPY]], sig_best.loc[oos_mask], cfg)
    r_val = run_backtest(prices.loc[val_mask, [SPY]], sig_best.loc[val_mask], cfg)
    r_test = run_backtest(prices.loc[test_mask, [SPY]], sig_best.loc[test_mask], cfg)
    bh_oos = pd.DataFrame({SPY: np.full(oos_mask.sum(), MAX_POS)}, index=prices.index[oos_mask])
    r_bh = run_backtest(prices.loc[oos_mask, [SPY]], bh_oos, cfg)

    eval_out = evaluate_gates(r_oos, r_train, r_bh, prices, oos_mask, best, cfg)
    ablations = run_ablations(prices, oos_mask, best, cfg)

    summary = {
        "hypothesis": "H103",
        "family_id": "NF-20261106-06",
        "mechanism": "AUD commodity-currency (FXA) global risk-appetite regime timing SPY, continuous exposure",
        "selected_params": best,
        "grid_size": len(grid),
        "data_rows": {
            "total": int(len(prices)),
            "train": int(train_mask.sum()),
            "val": int(val_mask.sum()),
            "test": int(test_mask.sum()),
        },
        "train": r_train.metrics,
        "val": r_val.metrics,
        "test_protected": r_test.metrics,
        "oos_val_test": r_oos.metrics,
        "evaluation": eval_out,
        "ablations": ablations,
        "grid_ranking_top5": rows[:5],
        "elapsed_seconds": round(time.time() - start, 2),
    }
    out_dir = Path(".experiments/nf_runs/nf_20261106_06_fxa_risk")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    passed = eval_out["gates_passed"]
    total = eval_out["gates_total"]
    verdict = "ACCEPT" if passed == total else "REJECT"
    print(f"\nVERDICT: {verdict} ({passed}/{total} gates)")
    print(json.dumps(eval_out["metrics"], indent=2, default=str))
    try:
        tracker.finish_experiment(status="completed")
    except Exception:
        pass
    summary["experiment_id"] = getattr(tracker, "current_experiment_id", None)
    summary["verdict"] = verdict
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


if __name__ == "__main__":
    main()
