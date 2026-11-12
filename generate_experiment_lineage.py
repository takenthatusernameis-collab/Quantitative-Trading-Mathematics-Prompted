#!/usr/bin/env python3
"""
Generate experiment lineage report from .experiments/experiments.jsonl

Produces EXPERIMENT_LINEAGE_REPORT.md with comprehensive experiment tracking.
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def get_status_str(exp: dict) -> str:
    """Extract status string from experiment."""
    status = exp.get("status", "unknown")
    if isinstance(status, dict):
        return status.get("verdict", "completed")
    if isinstance(status, str):
        return status
    return "unknown"


def load_experiments(jsonl_path: Path):
    """Load all experiment records from JSONL file."""
    experiments = []
    with open(jsonl_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                exp = json.loads(line)
                experiments.append(exp)
            except json.JSONDecodeError as e:
                print(f"Warning: Line {line_num} invalid JSON: {e}", file=sys.stderr)
    return experiments


def extract_family_name(name: str) -> str:
    """Extract strategy family from experiment name."""
    name_lower = name.lower()
    if "nf_" in name_lower or name_lower.startswith("nf-"):
        return "NF (New Family)"
    elif "h" in name_lower and any(c.isdigit() for c in name_lower.split("h")[1][:3]):
        return "H-series"
    elif "ma_crossover" in name_lower:
        return "MA Crossover"
    elif "tsmom" in name_lower or "time_series_momentum" in name_lower:
        return "TSMOM"
    elif "vrp" in name_lower or "vol_risk_prem" in name_lower:
        return "VRP"
    elif "regime" in name_lower:
        return "Regime-gated"
    elif "cross_sectional" in name_lower or "cs_momentum" in name_lower:
        return "Cross-sectional Momentum"
    elif "overnight" in name_lower or "intraday" in name_lower:
        return "Overnight/Intraday"
    elif "vol_pca" in name_lower or "pca" in name_lower:
        return "Vol PCA"
    elif "carry" in name_lower:
        return "Carry"
    elif "tax_loss" in name_lower:
        return "Tax-loss Harvesting"
    elif "treasury_auction" in name_lower:
        return "Treasury Auction"
    elif "equity_pc" in name_lower or "put_call" in name_lower:
        return "Put/Call Ratio"
    elif "short_interest" in name_lower:
        return "Short Interest"
    elif "dividend_capture" in name_lower:
        return "Dividend Capture"
    elif "es_spy_basis" in name_lower or "basis" in name_lower:
        return "Basis Mean Reversion"
    elif "vix" in name_lower and "term" in name_lower:
        return "VIX Term Structure"
    elif "gld" in name_lower and "tlt" in name_lower:
        return "GLD/TLT Correlation"
    elif "credit" in name_lower:
        return "Credit"
    elif "realized" in name_lower and (
        "vol" in name_lower or "skew" in name_lower or "kurt" in name_lower or "semi" in name_lower
    ):
        return "Realized Moments"
    else:
        return "Other"


def format_timestamp(ts_str: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts_str


def get_metrics_summary(metrics: dict) -> dict:
    """Extract key metrics from experiment."""
    if not metrics:
        return {}
    # Focus on OOS step1 metrics
    key_metrics = {}
    for k in [
        "sharpe_step1",
        "total_return_step1",
        "max_drawdown_step1",
        "profit_factor_step1",
        "n_trades_step1",
        "walkforward_stability_step1",
        "all_pass_step1",
        "benchmark_sharpe_step0",
        "benchmark_total_return_step0",
    ]:
        if k in metrics:
            key_metrics[k] = metrics[k]
    return key_metrics


def generate_report(experiments: list) -> str:
    """Generate markdown report from experiments."""
    lines = []
    lines.append("# Experiment Lineage Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("**Source:** `.experiments/experiments.jsonl`")
    lines.append(f"**Total Records:** {len(experiments)}")
    lines.append("")

    # Overall statistics
    status_counts = Counter(get_status_str(exp) for exp in experiments)
    lines.append("## Overall Statistics")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {status} | {count} |")
    lines.append("")

    # Family distribution
    family_counts = Counter()
    for exp in experiments:
        meta = exp.get("metadata", {})
        name = meta.get("name", "")
        family = extract_family_name(name)
        family_counts[family] += 1

    lines.append("## Strategy Family Distribution")
    lines.append("")
    lines.append("| Family | Experiments |")
    lines.append("|--------|-------------|")
    for family, count in sorted(family_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {family} | {count} |")
    lines.append("")

    # Timeline
    lines.append("## Experiment Timeline")
    lines.append("")
    lines.append("| Date | Experiment ID | Name | Family | Status | Key Metrics |")
    lines.append("|------|---------------|------|--------|--------|-------------|")

    # Sort by timestamp
    sorted_exps = sorted(
        experiments, key=lambda e: e.get("metadata", {}).get("timestamp", ""), reverse=True
    )

    for exp in sorted_exps:
        meta = exp.get("metadata", {})
        exp_id = meta.get("experiment_id", "unknown")
        name = meta.get("name", "unknown")
        timestamp = meta.get("timestamp", "")
        status = get_status_str(exp)
        family = extract_family_name(name)
        metrics = get_metrics_summary(exp.get("metrics", {}))

        # Format key metrics
        metric_parts = []
        if "sharpe_step1" in metrics:
            metric_parts.append(f"Sharpe={metrics['sharpe_step1']:.3f}")
        if "total_return_step1" in metrics:
            metric_parts.append(f"Ret={metrics['total_return_step1']:.3f}")
        if "max_drawdown_step1" in metrics:
            metric_parts.append(f"DD={metrics['max_drawdown_step1']:.3f}")
        if "profit_factor_step1" in metrics:
            metric_parts.append(f"PF={metrics['profit_factor_step1']:.3f}")
        if "n_trades_step1" in metrics:
            metric_parts.append(f"Trades={int(metrics['n_trades_step1'])}")
        if "all_pass_step1" in metrics:
            metric_parts.append(f"Pass={metrics['all_pass_step1']}")

        metrics_str = ", ".join(metric_parts) if metric_parts else "N/A"

        date_str = format_timestamp(timestamp) if timestamp else "N/A"
        # Truncate long names
        name_short = name[:50] + "..." if len(name) > 50 else name

        lines.append(
            f"| {date_str} | {exp_id} | {name_short} | {family} | {status} | {metrics_str} |"
        )

    lines.append("")

    # Detailed experiment records
    lines.append("## Detailed Experiment Records")
    lines.append("")

    for exp in sorted_exps:
        meta = exp.get("metadata", {})
        exp_id = meta.get("experiment_id", "unknown")
        name = meta.get("name", "unknown")
        timestamp = meta.get("timestamp", "")
        git_commit = meta.get("git_commit", "unknown")[:8]
        git_dirty = meta.get("git_dirty", False)
        status = get_status_str(exp)
        error = exp.get("error")
        config = meta.get("config", {})
        data_sources = meta.get("data_sources", {})
        metrics = exp.get("metrics", {})
        artifacts = exp.get("artifacts", {})

        lines.append(f"### {exp_id}")
        lines.append("")
        lines.append(f"- **Name:** {name}")
        lines.append(f"- **Timestamp:** {format_timestamp(timestamp) if timestamp else 'N/A'}")
        lines.append(f"- **Git Commit:** {git_commit}{' (dirty)' if git_dirty else ''}")
        lines.append(f"- **Status:** {status}")
        if error:
            lines.append(f"- **Error:** {error[:200]}{'...' if len(error) > 200 else ''}")
        lines.append("")

        # Configuration
        if config:
            lines.append("**Configuration:**")
            lines.append("")
            symbols = config.get("symbols", [])
            if symbols:
                lines.append(
                    f"- **Symbols:** {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}"
                )
            strategy = config.get("strategy", "unknown")
            lines.append(f"- **Strategy:** {strategy}")
            strategy_params = config.get("strategy_params", {})
            if strategy_params:
                lines.append(f"- **Strategy Params:** {strategy_params}")
            backtest = config.get("backtest", {})
            if backtest:
                lines.append(f"- **Asset Class:** {backtest.get('asset_class', 'unknown')}")
                lines.append(f"- **Max Position:** {backtest.get('max_position_size', 'N/A')}")
                lines.append(f"- **Max Leverage:** {backtest.get('max_leverage', 'N/A')}")
                lines.append(f"- **Allow Short:** {backtest.get('allow_short', 'N/A')}")
            data_splits = config.get("data_splits", {})
            if data_splits:
                lines.append(f"- **Train End:** {data_splits.get('train_end', 'N/A')}")
                lines.append(f"- **Val End:** {data_splits.get('val_end', 'N/A')}")
                lines.append(f"- **Test Start:** {data_splits.get('test_start', 'N/A')}")
            lines.append("")

        # Data sources
        if data_sources:
            lines.append("**Data Sources:**")
            lines.append("")
            if isinstance(data_sources, dict):
                lines.append(f"- **Source:** {data_sources.get('source', 'unknown')}")
                lines.append(f"- **Symbols:** {', '.join(data_sources.get('symbols', []))}")
                lines.append(
                    f"- **Period:** {data_sources.get('start', 'N/A')} to {data_sources.get('end', 'N/A')}"
                )
                lines.append(f"- **Interval:** {data_sources.get('interval', 'unknown')}")
            elif isinstance(data_sources, list):
                for i, ds in enumerate(data_sources):
                    if isinstance(ds, dict):
                        lines.append(f"- **Source {i + 1}:** {ds.get('source', 'unknown')}")
                        lines.append(f"  - **Symbols:** {', '.join(ds.get('symbols', []))}")
                        lines.append(
                            f"  - **Period:** {ds.get('start', 'N/A')} to {ds.get('end', 'N/A')}"
                        )
                        lines.append(f"  - **Interval:** {ds.get('interval', 'unknown')}")
            lines.append("")

        # Key metrics
        if metrics:
            lines.append("**Key Metrics (OOS Step 1):**")
            lines.append("")
            key_metrics = get_metrics_summary(metrics)
            for k, v in sorted(key_metrics.items()):
                if isinstance(v, float):
                    lines.append(f"- {k}: {v:.6f}")
                else:
                    lines.append(f"- {k}: {v}")
            lines.append("")

        # Artifacts
        if artifacts:
            lines.append(f"**Artifacts ({len(artifacts)} files):**")
            lines.append("")
            for art_name, art_path in sorted(artifacts.items()):
                lines.append(f"- `{art_name}`: {art_path}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    jsonl_path = Path(".experiments/experiments.jsonl")
    if not jsonl_path.exists():
        print(f"Error: {jsonl_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading experiments from {jsonl_path}...")
    experiments = load_experiments(jsonl_path)
    print(f"Loaded {len(experiments)} experiment records")

    print("Generating report...")
    report = generate_report(experiments)

    output_path = Path("EXPERIMENT_LINEAGE_REPORT.md")
    with open(output_path, "w") as f:
        f.write(report)

    print(f"Report written to {output_path}")
    print(f"Report size: {len(report)} characters, {len(report.splitlines())} lines")


if __name__ == "__main__":
    main()
