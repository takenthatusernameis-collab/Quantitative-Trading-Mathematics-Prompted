"""NF-20261106-04 / H101 (pre-registered): Copper/Gold ratio macro growth-regime equity timing.

The copper/gold ratio (HG=F / GC=F) proxies global growth expectations and risk
appetite: copper is an industrial/growth metal, gold is a safe-haven/real-rate
asset. A rising ratio signals growth optimism and equity tailwinds; a falling
ratio signals growth fear and equity headwinds. A vol-targeted long SPY position
is held when the trailing ratio z-score is benign (falling/rising within the
risk-on regime) and the regime is not in a falling-growth state; the position
goes flat when the ratio z-score is falling (growth fear), with hysteresis and a
1-bar execution delay.

New family dimension (cross-asset macro growth-regime timing), distinct from:
- H94 credit flight-to-quality (HYG-IEF).
- H95 USD macro risk timing (UUP).
- H96 equity-bond rolling return-correlation regime (SPY/TLT).
- H100 rates-vol / Treasury implied-vol stress transmission (^MOVE).
No prior repository family uses an industrial-metal vs precious-metal relative
price as a growth-regime equity-timing observable.

Causality / timing (pre-registered): the ratio z-score for day t is computed
from prices through close t only (trailing windows, min_periods). Signals are
shifted by 1 bar (signals.shift(1)), so the target set at close t earns the
return t -> t+1 -- no same-day look-ahead.

Data: yfinance daily HG=F, GC=F, SPY (free, cached), 2010-01-01 -> 2026-10-31.
Splits: Train 2010-01-01 -> 2019-12-31; Val 2020-01-01 -> 2022-12-31;
Test 2023-01-01 -> 2026-10-31 (protected holdout).
Grid: lookback {63,126,252} x entry_z {1.0,1.5,2.0} x exit_z {0.0,0.5} x
vol_target {0.10,0.15} (36 combos). Selection = best train-only 4-fold
walk-forward Sharpe; Test protected; gates on OOS Val+Test.
Cost model: equity (1 bp commission + 0.5 bp spread + 0.1 bp impact per 1%
ADV). Turnover low (slow-moving macro/regime signal).

Gates (PROMPT_V2 Phase 4, OOS Val+Test): OOS Sharpe>=1.0, >=200 trades,
PF>=1.3, max DD<=15%, WF stability test>=0.7*train when train>0, worst-regime
rolling-252 Sharpe>=0.3, benchmark p<=0.05 vs buy-hold SPY, IR>=0,
perturbation min ratio>=0.5.
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

EXPERIMENT_NAME = "nf_20261106_04_copper_gold"
EXPERIMENT_DESC = (
    "NF-20261106-04/H101: copper/gold ratio macro growth-regime equity timing. "
    "Vol-targeted long SPY when trailing (HG=F/GC=F) z-score is benign (rising or "
    "within risk-on), flat when falling (growth fear), hysteresis + 1-bar delay. "
    "Grid search on Train/WF; Test protected; gates on OOS Val+Test."
)

COPPER = "HG=F"
GOLD = "GC=F"
SPY = "SPY"
UNIVERSE = [COPPER, GOLD, SPY]

DATA_START = "2010-01-01"
DATA_END = "2026-10-31"
TRAIN_END = "2019-12-31"
VAL_END = "2022-12-31"

SEED = 42
INITIAL_CAPITAL = 1_000_000.0
MAX_POS = 0.5
ZSCORE_WINDOW = 252

LOOKBACKS = [63, 126, 252]
ENTRY_ZS = [1.0, 1.5, 2.0]
EXIT_ZS = [0.0, 0.5]
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


def _period_metrics(ret: pd.Series, n_trades: int) -> dict:
    r = ret.dropna()
    sr = float(sharpe_ratio(r.values)) if len(r) > 1 else 0.0
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
    if trades is None or len(trades) == 0:
        return 0
    ts = pd.to_datetime(trades["timestamp"])
    if len(prices.index[mask]) == 0:
        return 0
    lo = prices.index[mask].min()
    hi = prices.index[mask].max()
    return int(((ts >= lo) & (ts <= hi)).sum())


def build_copper_gold_targets(
    prices: pd.DataFrame,
    lookback: int,
    entry_z: float,
    exit_z: float,
    vol_target: float,
) -> pd.DataFrame:
    """Vol-targeted SPY targets from trailing copper/gold ratio z-score.

    ratio[t] = HG=F_t / GC=F_t (both through close t, past-only).
    z[t] = (ratio_t - rolling_mean(ratio, L)) / rolling_std(ratio, L), trailing,
    min_periods=L. Hysteresis: z >= entry_z -> long (risk-on: ratio elevated
    signals growth optimism); z <= exit_z -> flat (risk-off: ratio falling
    signals growth fear); between thresholds hold prior state. Initial state
    flat. No look-ahead: z[t] uses only observations through close t.
    Vol targeting uses trailing 21-day realized SPY vol (annualized).
    Engine applies signals.shift(1): target at close t earns return t->t+1.
    """
    idx = prices.index
    targets = pd.DataFrame(0.0, index=idx, columns=[SPY])
    if SPY not in prices.columns or COPPER not in prices.columns or GOLD not in prices.columns:
        return targets
    lookback = int(max(2, lookback))
    entry_z = float(entry_z)
    exit_z = float(exit_z)
    vol_target = float(max(0.01, vol_target))

    ratio = (prices[COPPER].astype(float) / prices[GOLD].astype(float))
    mu = ratio.rolling(lookback, min_periods=lookback).mean()
    sd = ratio.rolling(lookback, min_periods=lookback).std()
    z = (ratio - mu) / sd.replace(0, np.nan)

    state = pd.Series(np.nan, index=idx, dtype=float)
    state[z >= entry_z] = 1.0
    state[z <= exit_z] = 0.0
    side = state.ffill().fillna(0.0)
    side = side.where(z.notna(), 0.0)

    realized = prices[SPY].astype(float).pct_change().rolling(21, min_periods=21).std() * np.sqrt(
        252
    )
    scale = (vol_target / realized.replace(0, np.nan)).clip(upper=MAX_POS).fillna(0.0)
    targets[SPY] = (side * scale).clip(0.0, MAX_POS)
    return targets


def train_only_wf_sharpe(returns: pd.Series, train_mask, n_splits=WF_FOLDS_SELECTION) -> float:
    train_r = returns[train_mask].dropna()
    if len(train_r) < 120:
        return 0.0
    try:
        splits = walk_forward_splits(len(train_r), n_splits=n_splits)
    except Exception:
        return 0.0
    sharpes = []
    for _, te_idx in splits:
        r = train_r.iloc[te_idx].dropna()
        if len(r) > 20:
            sharpes.append(float(sharpe_ratio(r.values)))
    return float(np.mean(sharpes)) if sharpes else 0.0


def _stability_test_vs_train(train_sharpe: float, test_sharpe: float) -> float:
    if train_sharpe > 0:
        return test_sharpe / train_sharpe
    if train_sharpe == 0:
        return test_sharpe
    return 0.0


def full_gate_eval(result, oos_mask, val_mask, test_mask, prices, bench_result):
    rets = result.returns
    oos_r = rets[oos_mask].dropna()
    train_r = rets[prices.index <= pd.Timestamp(TRAIN_END)].dropna()
    val_r = rets[val_mask].dropna()
    test_r = rets[test_mask].dropna()

    oos_m = _period_metrics(oos_r, _count_in(result.trades, oos_mask, prices))
    train_m = _period_metrics(
        train_r, _count_in(result.trades, prices.index <= pd.Timestamp(TRAIN_END), prices)
    )
    test_m = _period_metrics(test_r, _count_in(result.trades, test_mask, prices))
    wf_stab = _stability_test_vs_train(train_m["sharpe"], test_m["sharpe"])

    bench_p = 1.0
    ir = 0.0
    try:
        cmp = compare_to_benchmark(rets, bench_result.returns)
        bench_p = float(cmp.get("alpha_p_value", 1.0))
        ir = float(cmp.get("information_ratio", 0.0))
    except Exception:
        pass

    if len(oos_r) >= 252:
        roll = oos_r.rolling(252).apply(lambda x: sharpe_ratio(x.values), raw=False)
        worst_regime = float(roll.min()) if roll.notna().any() else 0.0
    else:
        worst_regime = oos_m["sharpe"]

    passes = {
        "sharpe": oos_m["sharpe"] >= GATES["min_sharpe"],
        "trades": oos_m["trades"] >= GATES["min_trades"],
        "profit_factor": oos_m["profit_factor"] >= GATES["min_profit_factor"],
        "max_drawdown": oos_m["max_drawdown"] >= -GATES["max_drawdown"],
        "walkforward_stability": wf_stab >= GATES["min_walkforward_stability"],
        "worst_regime_sharpe": worst_regime >= GATES["min_worst_regime_sharpe"],
        "p_value": bench_p <= GATES["max_p_value"],
        "information_ratio": ir >= GATES["min_information_ratio"],
    }
    return {
        "oos_metrics": oos_m,
        "train_sharpe": train_m["sharpe"],
        "val_sharpe": float(sharpe_ratio(val_r.values)) if len(val_r) > 1 else 0.0,
        "test_metrics": test_m,
        "wf_stability": wf_stab,
        "worst_regime_sharpe": worst_regime,
        "benchmark_p": bench_p,
        "information_ratio": ir,
        "passes": passes,
        "gate_pass_count": sum(passes.values()),
    }
