"""Statistical validation utilities for quantitative trading research."""

from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import stats


def bootstrap_confidence_interval(
    data: np.ndarray,
    statistic: callable = np.mean,
    confidence: float = 0.95,
    n_bootstrap: int = 1000,
    random_state: int | None = None,
) -> tuple[float, float]:
    """
    Compute bootstrap confidence interval for a statistic.

    Args:
        data: Input data array
        statistic: Function to compute statistic (default: mean)
        confidence: Confidence level (default: 0.95)
        n_bootstrap: Number of bootstrap samples
        random_state: Random seed for reproducibility

    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    rng = np.random.default_rng(random_state)

    n = len(data)
    if n == 0:
        return (np.nan, np.nan)

    bootstrap_stats = []
    for _ in range(n_bootstrap):
        sample = data[rng.integers(0, n, n)]
        bootstrap_stats.append(statistic(sample))

    alpha = (1 - confidence) / 2
    lower = np.percentile(bootstrap_stats, 100 * alpha)
    upper = np.percentile(bootstrap_stats, 100 * (1 - alpha))
    return (lower, upper)


def sharpe_ratio(
    returns: np.ndarray,
    risk_free: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Compute annualized Sharpe ratio."""
    returns = np.asarray(returns, dtype=float)
    if returns.size == 0:
        return 0.0
    excess = returns - risk_free / periods_per_year
    # Tolerance guard: a constant return series has std ~1e-19 from float
    # noise, not exactly 0.0, so an exact `== 0` check misses it and
    # divides by a near-zero value, producing a garbage huge Sharpe.
    if returns.std() <= 1e-15:
        return 0.0
    return excess.mean() / returns.std() * np.sqrt(periods_per_year)


def bars_per_year(index: pd.DatetimeIndex) -> float:
    """
    Empirical number of bars per calendar year implied by a bar index.

    The annualization multiplier of a Sharpe ratio (and of any other
    mean/volatility statistic) is only meaningful if it matches the bar
    frequency of the series being summarized. This helper derives that
    multiplier from the timestamps themselves, so an hourly series is scaled
    by its own bar count per year rather than by a hard-coded daily constant.

    Args:
        index: Bar timestamps (DatetimeIndex, or anything convertible to one)

    Returns:
        Bars per calendar year. NaN when the index has fewer than two bars
        or spans no measurable time.
    """
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2:
        return float("nan")
    span_days = (idx[-1] - idx[0]).total_seconds() / 86400.0
    if span_days <= 0:
        return float("nan")
    return float(len(idx) / (span_days / 365.25))


def annualized_sharpe(
    returns: np.ndarray | pd.Series,
    index: pd.DatetimeIndex,
    risk_free: float = 0.0,
) -> float:
    """
    Sharpe ratio annualized by the bar frequency of ``index``.

    Unlike :func:`sharpe_ratio` with its default ``periods_per_year=252``,
    the multiplier is derived from the bar timestamps, so an hourly series
    is scaled by ``sqrt(bars_per_year)`` (its own frequency) and a daily
    series by ``sqrt(252)``.

    Args:
        returns: Per-bar return series
        index: Bar timestamps for ``returns`` (same length, aligned)
        risk_free: Annual risk-free rate

    Returns:
        Annualized Sharpe ratio (0.0 when the frequency cannot be inferred).
    """
    bpy = bars_per_year(index)
    if not np.isfinite(bpy) or bpy <= 0:
        return 0.0
    return sharpe_ratio(
        np.asarray(returns, dtype=float), risk_free=risk_free, periods_per_year=bpy
    )


def sharpe_ratio_ci(
    returns: np.ndarray,
    risk_free: float = 0.0,
    periods_per_year: int = 252,
    confidence: float = 0.95,
    n_bootstrap: int = 1000,
    random_state: int | None = None,
) -> tuple[float, float]:
    """Bootstrap confidence interval for Sharpe ratio."""

    def sharpe_func(x):
        return sharpe_ratio(x, risk_free, periods_per_year)

    return bootstrap_confidence_interval(
        returns, sharpe_func, confidence, n_bootstrap, random_state
    )


def walk_forward_splits(
    n_samples: int,
    n_splits: int = 5,
    train_ratio: float = 0.7,
    gap: int = 0,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Generate walk-forward train/test splits.

    Args:
        n_samples: Total number of samples
        n_splits: Number of walk-forward windows
        train_ratio: Fraction of each window for training
        gap: Gap between train and test (to prevent leakage)

    Returns:
        List of (train_indices, test_indices) tuples
    """
    if n_splits <= 0:
        return []
    window_size = n_samples // n_splits
    if window_size == 0:
        return []
    splits = []

    for i in range(n_splits):
        start = i * window_size
        # Last window absorbs any trailing samples dropped by integer division,
        # so the full series is covered instead of silently ignoring the tail.
        end = n_samples if i == n_splits - 1 else (i + 1) * window_size
        window_indices = np.arange(start, end)

        split_point = start + int(len(window_indices) * train_ratio)
        train_idx = np.arange(start, split_point)
        test_idx = np.arange(split_point + gap, end)

        if len(train_idx) > 0 and len(test_idx) > 0:
            splits.append((train_idx, test_idx))

    return splits


def multiple_testing_correction(
    p_values: np.ndarray,
    method: str = "bonferroni",
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply multiple testing correction.

    Args:
        p_values: Array of p-values
        method: "bonferroni" or "benjamini_hochberg" (FDR)
        alpha: Significance level

    Returns:
        Tuple of (rejected, adjusted_p_values)
    """
    p_values = np.asarray(p_values)
    n = len(p_values)

    if method == "bonferroni":
        adjusted = np.minimum(p_values * n, 1.0)
        rejected = adjusted < alpha
    elif method == "benjamini_hochberg":
        sorted_idx = np.argsort(p_values)
        sorted_p = p_values[sorted_idx]
        adjusted = np.zeros_like(p_values)
        for i, idx in enumerate(sorted_idx):
            adjusted[idx] = min(sorted_p[i] * n / (i + 1), 1.0)
        # Ensure monotonicity
        for i in range(n - 2, -1, -1):
            adjusted[sorted_idx[i]] = min(
                adjusted[sorted_idx[i]], adjusted[sorted_idx[i + 1]]
            )
        rejected = adjusted < alpha
    else:
        raise ValueError(f"Unknown method: {method}")

    return rejected, adjusted


def parameter_sensitivity(
    returns: np.ndarray,
    param_values: np.ndarray,
    metric_func: callable = sharpe_ratio,
    n_bootstrap: int = 500,
) -> dict[str, Any]:
    """
    Analyze parameter sensitivity using bootstrap.

    Args:
        returns: Returns for each parameter setting (2D: n_params x n_obs)
        param_values: Parameter values tested
        metric_func: Metric function to evaluate
        n_bootstrap: Bootstrap samples per parameter

    Returns:
        Dictionary with sensitivity metrics
    """
    n_params = len(param_values)
    metrics = np.zeros(n_params)
    ci_lower = np.zeros(n_params)
    ci_upper = np.zeros(n_params)

    for i in range(n_params):
        metrics[i] = metric_func(returns[i])
        ci_lower[i], ci_upper[i] = bootstrap_confidence_interval(
            returns[i], metric_func, n_bootstrap=n_bootstrap
        )

    # Find optimal parameter
    opt_idx = np.argmax(metrics)
    opt_param = param_values[opt_idx]
    opt_metric = metrics[opt_idx]

    # Stability: fraction of params within 1 std of optimum
    metric_std = metrics.std()
    stable = np.sum(metrics >= opt_metric - metric_std) / n_params

    return {
        "param_values": param_values,
        "metrics": metrics,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "optimal_param": opt_param,
        "optimal_metric": opt_metric,
        "stability_ratio": stable,
        "metric_std": metric_std,
    }


def regime_analysis(
    returns: np.ndarray,
    regime_labels: np.ndarray,
    metric_func: callable = sharpe_ratio,
) -> dict[str, float]:
    """
    Compute metrics per regime.

    Args:
        returns: Return series
        regime_labels: Regime label for each period
        metric_func: Metric function

    Returns:
        Dictionary with per-regime metrics
    """
    unique_regimes = np.unique(regime_labels)
    results = {}

    for regime in unique_regimes:
        mask = regime_labels == regime
        regime_returns = returns[mask]
        if len(regime_returns) > 1:
            results[f"regime_{regime}_sharpe"] = metric_func(regime_returns)
            results[f"regime_{regime}_count"] = len(regime_returns)
            results[f"regime_{regime}_mean"] = regime_returns.mean()
            results[f"regime_{regime}_std"] = regime_returns.std()

    return results


def stressed_cost_test(
    base_returns: np.ndarray,
    base_costs: np.ndarray,
    stress_multipliers: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    Test strategy robustness under stressed cost assumptions.

    Args:
        base_returns: Gross returns before costs
        base_costs: Base transaction costs
        stress_multipliers: Dict with keys 'commission', 'spread', 'slippage', 'impact'

    Returns:
        Dictionary with stressed metrics
    """
    if stress_multipliers is None:
        stress_multipliers = {
            "commission": 2.0,
            "spread": 2.0,
            "slippage": 2.0,
            "impact": 5.0,
        }

    results = {}
    for name, mult in stress_multipliers.items():
        stressed_costs = base_costs * mult
        stressed_returns = base_returns - stressed_costs
        results[f"stressed_{name}_sharpe"] = sharpe_ratio(stressed_returns)
        results[f"stressed_{name}_return"] = stressed_returns.mean() * 252

    # Combined stress
    total_stress = sum(stress_multipliers.values()) / len(stress_multipliers)
    combined_costs = base_costs * total_stress
    combined_returns = base_returns - combined_costs
    results["stressed_combined_sharpe"] = sharpe_ratio(combined_returns)

    return results


def capacity_estimate(
    returns: np.ndarray,
    adv: float,
    max_participation: float = 0.1,
    impact_model: Optional[callable] = None,  # noqa: UP045 -- `callable \| None` raises TypeError at annotation-evaluation time
) -> dict[str, float]:
    """
    Estimate strategy capacity based on market impact.

    Args:
        returns: Strategy returns at current scale
        adv: Average daily volume (shares or contracts)
        max_participation: Max participation rate (fraction of ADV)
        impact_model: Function (participation_rate) -> impact_bps

    Returns:
        Dictionary with capacity estimates
    """
    if impact_model is None:
        # Simple square-root impact model
        impact_model = lambda p: 10 * np.sqrt(p / 0.01)  # 10 bps at 1% ADV

    current_sharpe = sharpe_ratio(returns)
    results = {"current_sharpe": current_sharpe}

    # Estimate max AUM before Sharpe decays by 50%
    target_sharpe = current_sharpe * 0.5

    # Binary search for max participation
    low, high = 0.0, max_participation
    for _ in range(20):
        mid = (low + high) / 2
        impact_bps = impact_model(mid)
        # Rough adjustment: reduce returns by impact
        adjusted_returns = returns - impact_bps / 10000
        adj_sharpe = sharpe_ratio(adjusted_returns)
        if adj_sharpe >= target_sharpe:
            low = mid
        else:
            high = mid

    max_participation_rate = (low + high) / 2
    max_aum = max_participation_rate * adv * 100  # Assuming price ~100 for conversion

    results["max_participation_rate"] = max_participation_rate
    results["estimated_max_aum"] = max_aum
    results["sharpe_at_max_aum"] = sharpe_ratio(
        returns - impact_model(max_participation_rate) / 10000
    )

    return results


def deflated_sharpe_ratio(
    observed_sr: float,
    n_trials: int,
    n_obs: int,
    var_trials: float,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    periods_per_year: int = 252,
) -> tuple[float, float]:
    """
    Compute Deflated Sharpe Ratio (DSR) per Bailey & Lopez de Prado (2014).

    Args:
        observed_sr: Annualized Sharpe ratio of the selected strategy
        n_trials: Number of trials/strategies tested
        n_obs: Number of observations
        var_trials: Variance of Sharpe ratios across trials (annualized scale)
        skewness: Skewness of returns
        kurtosis: Kurtosis of returns (fisher=False convention)
        periods_per_year: Periods per year for annualization

    Returns:
        Tuple of (dsr_adjusted_sharpe, p_value) where p_value = P(SR_true > 0 | selection)
    """
    if n_trials <= 0 or n_obs < 2:
        return 0.0, 1.0
    if var_trials <= 0:
        var_trials = 1e-18
    emc = 0.5772156649
    max_z = (1.0 - emc) * stats.norm.ppf(1.0 - 1.0 / n_trials) + emc * stats.norm.ppf(
        1.0 - 1.0 / (n_trials * np.e)
    )
    sr_per_bar = observed_sr / np.sqrt(periods_per_year)
    var_trials_per_bar = var_trials / periods_per_year
    sr0_per_bar = np.sqrt(max(1e-18, var_trials_per_bar)) * max_z
    numerator = (sr_per_bar - sr0_per_bar) * np.sqrt(n_obs - 1.0)
    skew_term = 1.0 - skewness * sr_per_bar
    kurt_term = (kurtosis - 1.0) / 4.0 * sr_per_bar**2
    denom = float(np.sqrt(max(1e-12, skew_term + kurt_term)))
    dsr_adj = numerator / denom
    p = float(stats.norm.cdf(dsr_adj))
    return float(observed_sr * p), float(1.0 - p)


def compare_to_benchmark(
    strategy_returns: np.ndarray | pd.Series,
    benchmark_returns: np.ndarray | pd.Series,
    risk_free: float = 0.0,
    periods_per_year: int = 252,
) -> dict[str, float]:
    """
    Compare strategy to benchmark with statistical tests.

    Args:
        strategy_returns: Strategy return series
        benchmark_returns: Benchmark return series
        risk_free: Risk-free rate (annual)
        periods_per_year: Periods per year for annualization

    Returns:
        Dictionary with comparison metrics
    """
    # A multi-symbol benchmark (e.g. a DataFrame slice of a futures
    # universe) is reduced to a single series by averaging across symbols,
    # so the comparison is against the equal-weighted benchmark return.
    # Without this, `excess = strat - bench` raises "The truth value of a
    # Series is ambiguous" on the boolean-mask expressions below.
    if isinstance(benchmark_returns, pd.DataFrame):
        benchmark_returns = benchmark_returns.mean(axis=1)
    elif not isinstance(benchmark_returns, pd.Series):
        arr = np.asarray(benchmark_returns, dtype=float)
        benchmark_returns = arr.mean(axis=1) if arr.ndim > 1 else arr

    if not isinstance(strategy_returns, pd.Series):
        strategy_returns = np.asarray(strategy_returns, dtype=float)

    # Align
    min_len = min(len(strategy_returns), len(benchmark_returns))
    strat = strategy_returns[-min_len:]
    bench = benchmark_returns[-min_len:]

    # Excess returns
    excess = strat - bench

    # Information ratio
    ir = (
        excess.mean() / excess.std() * np.sqrt(periods_per_year)
        if excess.std() > 0
        else 0
    )

    # Alpha / Beta (CAPM). beta is the OLS regression slope of strategy
    # returns on benchmark returns, cov(S, B) / var(B) with a CONSISTENT
    # ddof on both terms. np.cov defaults to ddof=1 (sample) while np.var
    # defaults to ddof=0 (population); mixing them inflates beta by
    # n/(n-1) relative to the OLS slope (np.polyfit / scipy.stats.linregress).
    # With a consistent ddof=1, beta is the OLS slope and alpha reduces to
    # the OLS intercept (mean(S) - beta * mean(B)), net of the risk-free
    # term, which is the standard CAPM alpha.
    if bench.std() > 0:
        beta = np.cov(strat, bench, ddof=1)[0, 1] / np.var(bench, ddof=1)
        alpha = (
            strat.mean()
            - risk_free / periods_per_year
            - beta * (bench.mean() - risk_free / periods_per_year)
        )
        alpha_annual = alpha * periods_per_year
    else:
        beta = 0
        alpha_annual = 0

    # T-test for alpha
    if excess.std() > 1e-12:
        t_stat, p_value = stats.ttest_1samp(excess, 0)
    else:
        t_stat, p_value = 0.0, 1.0

    # Win rate
    win_rate = (excess > 0).mean()

    return {
        "information_ratio": ir,
        "alpha_annualized": alpha_annual,
        "beta": beta,
        "alpha_t_stat": t_stat,
        "alpha_p_value": p_value,
        "win_rate": win_rate,
        "excess_return_annual": excess.mean() * periods_per_year,
        "excess_vol_annual": excess.std() * np.sqrt(periods_per_year),
    }


def statistical_power_analysis(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
    std: float = 1.0,
) -> int:
    """
    Compute required sample size for given effect size and power.

    Args:
        effect_size: Expected effect size (Cohen's d)
        alpha: Type I error rate
        power: Desired power (1 - Type II error)
        std: Standard deviation of outcome

    Returns:
        Required sample size per group
    """
    from scipy.stats import norm

    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)
    n = 2 * ((z_alpha + z_beta) * std / effect_size) ** 2
    return int(np.ceil(n))


def validate_strategy(
    returns: np.ndarray | pd.Series,
    trades: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Comprehensive strategy validation against PROMPT_V2.md criteria.

    Args:
        returns: Net returns series
        trades: Trade DataFrame
        config: Validation config with thresholds

    Returns:
        Dictionary with pass/fail for each criterion
    """
    defaults = {
        "min_sharpe": 1.0,
        "min_trades": 200,
        "min_profit_factor": 1.3,
        "max_drawdown": 0.15,
        "min_walkforward_stability": 0.7,
        "min_param_stability": 0.8,
    }
    thresholds = {**defaults, **config}

    # Convert to pandas Series for easier manipulation
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)

    # Degenerate input guard: an empty return series cannot be annualized
    # (252 / len(returns) divides by zero) and yields no walk-forward folds,
    # so it must fail every evidence gate rather than crash.
    if len(returns) == 0:
        return {
            "sharpe": 0.0,
            "sharpe_pass": False,
            "n_trades": len(trades),
            "trades_pass": False,
            "profit_factor": 1.0,
            "profit_factor_pass": False,
            "max_drawdown": 0.0,
            "drawdown_pass": True,
            "walkforward_stability": 0.0,
            "walkforward_pass": False,
            "param_stability": 0.0,
            "param_stability_pass": False,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "total_return": 0.0,
            "all_pass": False,
        }

    n_trades = len(trades)
    total_return = (1 + returns).prod() - 1
    ann_return = (1 + total_return) ** (252 / len(returns)) - 1
    ann_vol = returns.std() * np.sqrt(252)
    sharpe = sharpe_ratio(returns.values)

    # Drawdown
    equity = (1 + returns).cumprod()
    rolling_max = equity.expanding().max()
    drawdown = (equity - rolling_max) / rolling_max
    max_dd = drawdown.min()

    # Profit factor
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

    # Walk-forward stability (simplified: compare first half vs second half).
    # The ratio only measures persistence when BOTH halves are profitable:
    # a negative in-sample Sharpe means the strategy is already broken, and a
    # negative out-of-sample Sharpe means the edge did not persist. Without
    # this guard the ratio is sign-sensitive and can exceed the gate threshold
    # when both halves are losing (e.g. Sharpe -18 / -14 => 0.76 => PASS), which
    # is the opposite of "stable". See test_walkforward_passes_with_both_halves_losing.
    mid = len(returns) // 2
    sharpe_first = sharpe_ratio(returns.iloc[:mid].values)
    sharpe_second = sharpe_ratio(returns.iloc[mid:].values)
    if sharpe_first <= 0 or sharpe_second <= 0:
        wf_stability = 0.0
    else:
        wf_stability = sharpe_second / sharpe_first

    # Parameter stability: the PROMPT_V2.md evidence gates require a
    # "performance stable within +/-1 standard deviation of optimal
    # parameters" check. Without a parameter grid here we proxy it with the
    # walk-forward fold Sharpes: the fraction of folds that remain
    # out-of-sample profitable (Sharpe > 0) measures how sensitive the
    # strategy is to which sub-sample is held out. A perfectly stable
    # strategy scores 1.0 (every fold profitable); a wildly unstable one
    # scores 0.0. Threshold 0.8 = >=80% of folds profitable.
    _wf_splits = walk_forward_splits(len(returns), n_splits=5)
    _fold_sharpes = [
        sharpe_ratio(returns.iloc[te].values) for _, te in _wf_splits if len(te) > 1
    ]
    if len(_fold_sharpes) > 0:
        param_stability = float(np.mean(np.array(_fold_sharpes) > 0))
    else:
        param_stability = 0.0

    results = {
        "sharpe": sharpe,
        "sharpe_pass": sharpe >= thresholds["min_sharpe"],
        "n_trades": n_trades,
        "trades_pass": n_trades >= thresholds["min_trades"],
        "profit_factor": profit_factor,
        "profit_factor_pass": profit_factor >= thresholds["min_profit_factor"],
        "max_drawdown": max_dd,
        "drawdown_pass": max_dd >= -thresholds["max_drawdown"],
        "walkforward_stability": wf_stability,
        "walkforward_pass": wf_stability >= thresholds["min_walkforward_stability"],
        "param_stability": param_stability,
        "param_stability_pass": param_stability >= thresholds["min_param_stability"],
        "annualized_return": ann_return,
        "annualized_volatility": ann_vol,
        "total_return": total_return,
    }

    results["all_pass"] = all(
        [
            results["sharpe_pass"],
            results["trades_pass"],
            results["profit_factor_pass"],
            results["drawdown_pass"],
            results["walkforward_pass"],
            results["param_stability_pass"],
        ]
    )

    return results


from itertools import combinations as _combinations


def purged_kfold_splits(
    n_samples: int,
    n_splits: int = 5,
    purge: int = 0,
    embargo: int = 0,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Generate purged k-fold train/test splits with optional embargo."""
    if n_samples <= 0 or n_splits <= 0:
        return []
    fold_size = n_samples // n_splits
    if fold_size == 0:
        return []
    splits = []
    for i in range(n_splits):
        test_start = i * fold_size
        test_end = n_samples if i == n_splits - 1 else (i + 1) * fold_size
        test_idx = np.arange(test_start, test_end)
        mask = np.ones(n_samples, dtype=bool)
        mask[test_start:test_end] = False
        lo = max(0, test_start - purge)
        hi = min(n_samples, test_end + purge)
        mask[lo:hi] = False
        emb_start = test_end
        emb_end = min(n_samples, test_end + embargo)
        mask[emb_start:emb_end] = False
        train_idx = np.where(mask)[0]
        if len(train_idx) > 0 and len(test_idx) > 0:
            splits.append((train_idx, test_idx))
    return splits


def combinatorial_purged_cv(
    n_samples: int,
    n_splits: int = 5,
    n_test_splits: int = 2,
    purge: int = 0,
    embargo: int = 0,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Generate combinatorial purged cross-validation splits."""
    if (
        n_samples <= 0
        or n_splits <= 0
        or n_test_splits <= 0
        or n_test_splits >= n_splits
    ):
        return []
    fold_size = n_samples // n_splits
    if fold_size == 0:
        return []
    groups = []
    for i in range(n_splits):
        s = i * fold_size
        e = n_samples if i == n_splits - 1 else (i + 1) * fold_size
        groups.append((s, e))
    splits = []
    for test_groups in _combinations(range(n_splits), n_test_splits):
        test_idx = np.concatenate(
            [np.arange(groups[g][0], groups[g][1]) for g in test_groups]
        )
        mask = np.ones(n_samples, dtype=bool)
        for g in test_groups:
            s, e = groups[g]
            mask[s:e] = False
            lo = max(0, s - purge)
            hi = min(n_samples, e + purge)
            mask[lo:hi] = False
            emb_start = e
            emb_end = min(n_samples, e + embargo)
            mask[emb_start:emb_end] = False
        train_idx = np.where(mask)[0]
        if len(train_idx) > 0 and len(test_idx) > 0:
            splits.append((train_idx, test_idx))
    return splits
