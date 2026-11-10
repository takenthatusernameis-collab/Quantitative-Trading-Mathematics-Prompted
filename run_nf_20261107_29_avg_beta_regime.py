"""NF-20261107-29 / H129 (pre-registered, Cycle 43): Cross-sectional average
sector beta regime timing for SPY.

Mechanism: average trailing beta of liquid sector ETFs vs SPY captures
systematic risk-appetite / beta-expansion-contraction. When avg-beta z-score is
abnormally high (beta expansion / crowded systematic exposure), reduce vol-
targeted SPY exposure continuously; otherwise maintain normal exposure.

Repo-relative novelty (honest): different observable from H117 (average
pairwise sector correlation, contagion/regime) and H96/H127 (pairwise
cross-asset correlations). Beta mixes co-movement and relative volatility;
construction class (cross-sectional sector statistic z-score → SPY exposure,
1-bar delay via engine shift, vol-target, long-only) is adjacent to H117 and
scored honestly lower on novelty. Distinct from H93 (idiosyncratic vol level,
different observable), H124 (MAX/lottery), TSMOM/regime/corr pairs.

Causality/timing: betas computed from trailing returns through t-1 only
(rolling windows on past returns); signals shifted by 1 bar by engine.
Data: yfinance daily adjusted close (free). Signal ETFs: XLB,XLE,XLF,XLI,XLK,
XLP,XLU,XLV,XLY (9 SPDR sectors with full 2010+ history). Traded: SPY.
Splits: Train 2010-01-04..2019-12-31; Val 2020-01-01..2021-12-31; Test
(protected) 2022-01-03..2025-01-03. Bounded grid: beta_window {21,63} x
z_window {126} x entry_scale {1.0,1.5,2.0} x vol_target {0.10,0.15} (12).
Selection = best train-only 4-fold WF Sharpe (mean of fold Sharpes); Test
protected. OOS Val+Test gates pre-registered.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from qtr.backtest.engine import (  # noqa: E402
    AssetClass,
    BacktestConfig,
    CostModel,
    run_backtest,
)
from qtr.validation.statistics import (  # noqa: E402
    benchmark_significance_gate,
    compare_to_benchmark,
    sharpe_ratio,
    walk_forward_splits,
)

EXPERIMENT_NAME = "nf_20261107_29_avg_beta_regime"
NF_ID = "NF-20261107-29"
HYPOTHESIS_ID = "H129"
SPY = "SPY"
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
UNIVERSE = [SPY, *SECTORS]
START = "2010-01-01"
END = "2025-01-06"
TRAIN_END = "2019-12-31"
VAL_END = "2021-12-31"
SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5

BETA_WINDOWS = [21, 63]
Z_WINDOWS = [126]
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


def download_prices() -> pd.DataFrame:
    raw = yf.download(UNIVERSE, start=START, end=END, auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    raw = raw.dropna(how="any")
    for c in raw.columns:
        if (raw[c] <= 0).any():
            raise ValueError(f"non-positive prices in {c}")
    return raw[UNIVERSE]


def split_masks(index: pd.DatetimeIndex):
    train = index <= pd.Timestamp(TRAIN_END)
    val = (index > pd.Timestamp(TRAIN_END)) & (index <= pd.Timestamp(VAL_END))
    test = index > pd.Timestamp(VAL_END)
    return train, val, test


def avg_beta_z(prices: pd.DataFrame, beta_window: int, z_window: int) -> pd.Series:
    rets = prices.pct_change()
    spy = rets[SPY]
    betas = {}
    for s in SECTORS:
        cov = rets[s].rolling(beta_window, min_periods=beta_window).cov(spy)
        var = spy.rolling(beta_window, min_periods=beta_window).var()
        betas[s] = cov / var.replace(0.0, np.nan)
    avg = pd.DataFrame(betas).mean(axis=1)
    mu = avg.rolling(z_window, min_periods=z_window).mean()
    sigma = avg.rolling(z_window, min_periods=z_window).std(ddof=0)
    return (avg - mu) / sigma.replace(0.0, np.nan)


def build_signals(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    z = avg_beta_z(prices, params["beta_window"], params["z_window"]).fillna(0.0)
    rets = prices[SPY].pct_change()
    realized_vol = rets.rolling(63, min_periods=21).std() * np.sqrt(252)
    vol_scale = (params["vol_target"] / realized_vol.replace(0.0, np.nan)).clip(0.0, 1.0)
    vol_scale = vol_scale.fillna(0.0)
    # pre-registered mapping: high avg-beta z (beta expansion/risk appetite)
    # => reduce SPY exposure continuously.
    stress = (z / max(params["entry_scale"], 1e-12)).clip(0.0, 1.0)
    stress = stress.where(z > 0.0, 0.0)
    exposure = params["vol_target"] * (1.0 - stress) * vol_scale
    sig = pd.DataFrame(
        {SPY: exposure.astype(float).clip(0.0, params["vol_target"])},
        index=prices.index,
    )
    warmup = max(params["z_window"], 63) + params["beta_window"]
    sig.iloc[:warmup] = 0.0
    sig[sig.isna()] = 0.0
    for s in SECTORS:
        sig[s] = 0.0
    return sig[UNIVERSE]


def _profit_factor(returns: np.ndarray) -> float:
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 1e-12:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def evaluate_gates(oos_res, train_res, benchmark_oos, prices, oos_mask, selected_params, cfg):
    oos_rets = oos_res.returns.fillna(0.0).values
    train_rets = train_res.returns.fillna(0.0).values
    metrics = oos_res.metrics
    sharpe = float(metrics.get("sharpe", 0.0))
    trades = int(metrics.get("num_trades", 0))
    pf = _profit_factor(oos_rets)
    max_dd_abs = abs(float(metrics.get("max_drawdown", 1.0)))

    wf_stab = 0.0
    if len(train_rets) > 0 and np.std(train_rets) > 1e-12:
        train_sh = float(sharpe_ratio(train_rets))
        if abs(train_sh) > 1e-12:
            wf_stab = float(sharpe / train_sh)
        elif abs(sharpe) < 1e-12:
            wf_stab = 1.0

    roll_window = 252
    s = pd.Series(oos_rets)
    roll = s.rolling(roll_window).apply(
        lambda x: sharpe_ratio(x.values) if np.std(x) > 1e-12 else 0.0, raw=False
    )
    worst_reg = float(roll.dropna().min()) if roll.notna().any() else 0.0

    try:
        cmp = compare_to_benchmark(
            oos_res.returns.fillna(0.0),
            benchmark_oos.returns.fillna(0.0),
        )
        pval = float(cmp.get("alpha_p_value", 1.0))
        ir = float(cmp.get("information_ratio", -1.0))
    except Exception:
        cmp = {}
        pval, ir = 1.0, -1.0

    base_sh = sharpe if abs(sharpe) > 1e-12 else 1e-12
    pert_ratios = []
    for mult in (0.8, 1.2):
        for key in ("beta_window", "entry_scale", "vol_target"):
            p = dict(selected_params)
            if key == "beta_window":
                p[key] = max(5, int(round(p[key] * mult)))
            else:
                p[key] = float(p[key] * mult)
            try:
                sig = build_signals(prices, p)
                res = run_backtest(prices.loc[oos_mask, UNIVERSE], sig.loc[oos_mask], cfg)
                pert_ratios.append(float(res.metrics.get("sharpe", 0.0)) / base_sh)
            except Exception:
                pert_ratios.append(0.0)
    pert = float(np.min(pert_ratios)) if pert_ratios else 0.0

    pass_sh = sharpe >= GATES["min_sharpe"]
    pass_tr = trades >= GATES["min_trades"]
    pass_pf = pf >= GATES["min_profit_factor"]
    pass_dd = max_dd_abs <= GATES["max_drawdown"]
    pass_wf = (wf_stab >= GATES["min_walkforward_stability"]) if np.isfinite(wf_stab) else False
    pass_reg = worst_reg >= GATES["min_worst_regime_sharpe"] if np.isfinite(worst_reg) else False
    pass_bench = (
        (benchmark_significance_gate(pval, ir, GATES["max_p_value"]))
        if (np.isfinite(pval) and np.isfinite(ir))
        else False
    )
    pass_pert = pert >= GATES["min_perturbed_sharpe_ratio"]

    gates = {
        "sharpe_ge_1_0": {"value": sharpe, "threshold": GATES["min_sharpe"], "pass": pass_sh},
        "trades_ge_200": {"value": trades, "threshold": GATES["min_trades"], "pass": pass_tr},
        "profit_factor_ge_1_3": {
            "value": pf,
            "threshold": GATES["min_profit_factor"],
            "pass": pass_pf,
        },
        "max_drawdown_le_15pct": {
            "value": max_dd_abs,
            "threshold": GATES["max_drawdown"],
            "pass": pass_dd,
        },
        "walkforward_stability_ge_0_7": {
            "value": wf_stab,
            "threshold": GATES["min_walkforward_stability"],
            "pass": pass_wf,
        },
        "worst_regime_rolling252_sharpe_ge_0_3": {
            "value": worst_reg,
            "threshold": GATES["min_worst_regime_sharpe"],
            "pass": pass_reg,
        },
        "benchmark_p_le_0_05_ir_ge_0": {
            "value": {"p_value": pval, "information_ratio": ir},
            "threshold": {"p": GATES["max_p_value"], "ir": GATES["min_information_ratio"]},
            "pass": pass_bench,
        },
        "perturbation_min_ratio_ge_0_5": {
            "value": pert,
            "threshold": GATES["min_perturbed_sharpe_ratio"],
            "pass": pass_pert,
        },
    }
    passed = sum(1 for g in gates.values() if g["pass"])
    verdict = "PASS" if passed == len(gates) else "REJECT"
    return {
        "verdict": verdict,
        "passed": passed,
        "total": len(gates),
        "gates": gates,
        "comparison": cmp,
    }


def _select_on_train(prices: pd.DataFrame, train_mask: pd.Series, cfg: BacktestConfig):
    tr_prices = prices.loc[train_mask, UNIVERSE]
    rows = []
    for bw in BETA_WINDOWS:
        for zw in Z_WINDOWS:
            for es in ENTRY_SCALES:
                for vt in VOL_TARGETS:
                    params = {
                        "beta_window": bw,
                        "z_window": zw,
                        "entry_scale": es,
                        "vol_target": vt,
                    }
                    try:
                        sig = build_signals(prices, params)
                        tr_rets = (
                            run_backtest(tr_prices, sig.loc[train_mask], cfg)
                            .returns.fillna(0.0)
                            .values
                        )
                    except Exception:
                        continue
                    fold_sh = []
                    try:
                        for _tr_i, te_i in walk_forward_splits(
                            len(tr_rets), n_splits=WF_FOLDS_SELECTION
                        ):
                            if len(te_i) < 30:
                                continue
                            fold_sh.append(float(sharpe_ratio(tr_rets[te_i])))
                    except Exception:
                        continue
                    rows.append(
                        {**params, "wf_mean_sharpe": float(np.mean(fold_sh)) if fold_sh else -9.0}
                    )
    if not rows:
        raise RuntimeError("No valid train-selection candidates")
    df = pd.DataFrame(rows).sort_values("wf_mean_sharpe", ascending=False)
    best = df.iloc[0].to_dict()
    best["beta_window"] = int(best["beta_window"])
    best["z_window"] = int(best["z_window"])
    return best, df


def _ablations(
    prices: pd.DataFrame, oos_mask: pd.Series, selected_params: dict, cfg: BacktestConfig
):
    spy_rets = prices[SPY].pct_change().fillna(0.0)
    bh = run_backtest(
        prices.loc[oos_mask, [SPY]], pd.DataFrame({SPY: 1.0}, index=prices.loc[oos_mask].index), cfg
    )
    sig = build_signals(prices, selected_params).loc[oos_mask, [SPY]]
    exposed = sig[SPY].values > 1e-9
    exp_frac = float(exposed.mean())
    rng = np.random.default_rng(SEED)
    rand_mask = rng.random(len(sig)) < exp_frac
    rand_sig = pd.DataFrame({SPY: np.where(rand_mask, sig[SPY].values, 0.0)}, index=sig.index)
    rand = run_backtest(prices.loc[oos_mask, [SPY]], rand_sig, cfg)
    inv_sig = pd.DataFrame(
        {SPY: np.where(sig[SPY].values <= 1e-9, selected_params["vol_target"], 0.0)},
        index=sig.index,
    )
    inv = run_backtest(prices.loc[oos_mask, [SPY]], inv_sig, cfg)

    def ms(r):
        return {
            "sharpe": float(r.metrics.get("sharpe", 0.0)),
            "profit_factor": _profit_factor(r.returns.fillna(0.0).values),
            "max_drawdown": float(r.metrics.get("max_drawdown", 0.0)),
            "trades": int(r.metrics.get("num_trades", 0)),
        }

    return {
        "buy_hold_spy": ms(bh),
        "random_exposure_matched": ms(rand),
        "inverse_beta_regime_long": ms(inv),
    }


def main():
    t0 = time.time()
    np.random.seed(SEED)
    prices = download_prices()
    train_m, val_m, test_m = split_masks(prices.index)
    oos_m = val_m | test_m
    cfg = make_equity_config()
    selected, grid_df = _select_on_train(prices, train_m, cfg)
    sel_params = {k: selected[k] for k in ["beta_window", "z_window", "entry_scale", "vol_target"]}
    sig = build_signals(prices, sel_params)
    train_res = run_backtest(prices.loc[train_m, UNIVERSE], sig.loc[train_m], cfg)
    oos_res = run_backtest(prices.loc[oos_m, UNIVERSE], sig.loc[oos_m], cfg)
    bh_oos = run_backtest(
        prices.loc[oos_m, [SPY]], pd.DataFrame({SPY: 1.0}, index=prices.loc[oos_m].index), cfg
    )
    gates = evaluate_gates(oos_res, train_res, bh_oos, prices, oos_m, sel_params, cfg)
    ab = _ablations(prices, oos_m, sel_params, cfg)
    summary = {
        "experiment_name": EXPERIMENT_NAME,
        "nf_id": NF_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "verdict": gates["verdict"],
        "selected_params": sel_params,
        "selection_score": selected.get("wf_mean_sharpe"),
        "train_metrics": train_res.metrics,
        "oos_metrics": oos_res.metrics,
        "gates_detail": gates,
        "ablations_oos": ab,
        "data": {
            "start": str(prices.index[0].date()),
            "end": str(prices.index[-1].date()),
            "rows": int(len(prices)),
            "universe": UNIVERSE,
            "sectors": SECTORS,
            "train_rows": int(train_m.sum()),
            "val_rows": int(val_m.sum()),
            "test_rows": int(test_m.sum()),
        },
        "grid_size": len(grid_df),
        "gates": GATES,
        "runtime_sec": round(time.time() - t0, 3),
    }
    outdir = Path(".experiments/nf_runs/nf_20261107_29_avg_beta_regime")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    grid_df.to_csv(outdir / "grid.csv", index=False)
    (outdir / "data_meta.json").write_text(json.dumps(summary["data"], indent=2))
    print(
        json.dumps(
            {
                "verdict": gates["verdict"],
                "gates_passed": gates["passed"],
                "selected": sel_params,
                "oos_sharpe": oos_res.metrics.get("sharpe"),
                "summary": str(outdir / "summary.json"),
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
