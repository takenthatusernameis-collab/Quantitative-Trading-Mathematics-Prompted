#!/usr/bin/env python3
"""
Generate experiment lineage report from .experiments/experiments.jsonl.

This script creates a comprehensive markdown report documenting all experiments
tracked in the experiment lineage log, including their configurations, metrics,
status, and relationships.
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_experiments(jsonl_path: Path) -> list[dict]:
    """Load all experiment records from the JSONL file."""
    experiments = []
    with open(jsonl_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                experiments.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line {line_num}: {e}", file=sys.stderr)
    return experiments


def extract_key_info(exp: dict) -> dict:
    """Extract standardized key information from an experiment record."""
    metadata = exp.get("metadata", {})
    config = exp.get("config", {})
    metrics = exp.get("metrics", {})
    status = exp.get("status", {})
    artifacts = exp.get("artifacts", {})
    error = exp.get("error")

    # Handle both old (dict) and new (dict with verdict/gates) status formats
    if isinstance(status, dict):
        verdict = status.get("verdict", status.get("all_pass_step1", "unknown"))
        if isinstance(verdict, bool):
            verdict = "PASS" if verdict else "FAIL"
    else:
        verdict = str(status)

    # Extract git commit
    git_commit = metadata.get("git_commit", "unknown")[:8]

    # Extract experiment name and ID
    exp_id = metadata.get("experiment_id", "unknown")
    name = metadata.get("name", "unknown")
    description = metadata.get("description", "")
    timestamp = metadata.get("timestamp", "")

    # Parse timestamp
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        ts_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        ts_str = timestamp

    # Extract key metrics
    key_metrics = {}
    if isinstance(metrics, dict):
        # Standard OOS metrics
        for key in [
            "oos_sharpe",
            "oos_trades",
            "oos_pf",
            "oos_max_dd",
            "wf_ratio",
            "worst_regime",
            "benchmark_p",
            "benchmark_ir",
            "perturb_min_ratio",
            "gates_passed",
            "sharpe_step1",
            "profit_factor_step1",
            "max_drawdown_step1",
            "walkforward_stability_step1",
            "total_return_step1",
            "annualized_return_step1",
            "annualized_volatility_step1",
            "total_return_step0",
            "sharpe_step0",
        ]:
            if key in metrics:
                key_metrics[key] = metrics[key]

    # Extract config summary
    config_summary = {}
    if isinstance(config, dict):
        if "symbols" in config:
            config_summary["symbols"] = config["symbols"]
        if "strategy" in config:
            config_summary["strategy"] = config["strategy"]
        if "strategy_params" in config:
            config_summary["strategy_params"] = config["strategy_params"]
        if "lookbacks" in config:
            config_summary["lookbacks"] = config["lookbacks"]
        if "vol_targets" in config:
            config_summary["vol_targets"] = config["vol_targets"]
        if "signal_modes" in config:
            config_summary["signal_modes"] = config["signal_modes"]
        if "start_date" in config:
            config_summary["start_date"] = config["start_date"]
        if "end_date" in config:
            config_summary["end_date"] = config["end_date"]
        if "interval" in config:
            config_summary["interval"] = config["interval"]

    # Data sources
    data_sources = exp.get("data_sources", {})
    if isinstance(data_sources, dict):
        src = data_sources.get("source", data_sources.get("symbols", "unknown"))
        config_summary["data_source"] = src

    return {
        "exp_id": exp_id,
        "name": name,
        "description": description,
        "timestamp": ts_str,
        "git_commit": git_commit,
        "verdict": verdict,
        "metrics": key_metrics,
        "config": config_summary,
        "artifacts": list(artifacts.keys()) if isinstance(artifacts, dict) else [],
        "error": error,
    }


def categorize_experiment(info: dict) -> str:
    """Categorize experiment by name/type."""
    name = info["name"].lower()
    if "ma_crossover" in name or "baseline" in name:
        return "Baseline / MA Crossover"
    elif "ts_momentum" in name or "tsmom" in name or "intraday" in name:
        return "Time-Series Momentum"
    elif "cs_momentum" in name:
        return "Cross-Sectional Momentum"
    elif "regime" in name:
        return "Regime-Gated"
    elif "vix" in name or "vrp" in name:
        return "Volatility / VRP"
    elif "overnight" in name:
        return "Overnight/Intraday Decomposition"
    elif "volume" in name:
        return "Volume Predictive"
    elif "order_flow" in name or "imbalance" in name:
        return "Order Flow"
    elif "factor" in name or "nf_20261109" in name:
        return "New Family (NF) - Factor/Other"
    elif "nf_202611" in name:
        return "New Family (NF) - Recent"
    elif (
        "h10" in name
        or "h11" in name
        or "h12" in name
        or "h13" in name
        or "h14" in name
        or "h15" in name
        or "h16" in name
        or "h17" in name
        or "h18" in name
        or "h19" in name
        or "h20" in name
        or "h21" in name
        or "h22" in name
        or "h23" in name
        or "h24" in name
        or "h25" in name
        or "h26" in name
        or "h27" in name
        or "h28" in name
        or "h29" in name
    ):
        return "Hypothesis H10-H29"
    elif "ddcv" in name:
        return "DDCV / Selection Bias"
    elif "param" in name:
        return "Parameter Sweep"
    elif "alternatives" in name:
        return "Alternatives / Stress Test"
    else:
        return "Other / Uncategorized"


def format_metrics(metrics: dict) -> str:
    """Format metrics for markdown table."""
    if not metrics:
        return "—"
    parts = []
    key_order = [
        "oos_sharpe",
        "sharpe_step1",
        "sharpe_step0",
        "oos_trades",
        "n_trades_step1",
        "num_trades_step0",
        "oos_pf",
        "profit_factor_step1",
        "profit_factor_step0",
        "oos_max_dd",
        "max_drawdown_step1",
        "max_drawdown_step0",
        "wf_ratio",
        "walkforward_stability_step1",
        "worst_regime",
        "benchmark_p",
        "benchmark_ir",
        "perturb_min_ratio",
        "gates_passed",
        "all_pass_step1",
        "total_return_step1",
        "annualized_return_step1",
    ]
    for key in key_order:
        if key in metrics:
            val = metrics[key]
            if isinstance(val, float):
                parts.append(f"{key}={val:.4f}")
            else:
                parts.append(f"{key}={val}")
    return "<br>".join(parts[:8]) + ("..." if len(parts) > 8 else "")


def generate_report(experiments: list[dict], output_path: Path):
    """Generate the markdown lineage report."""
    # Categorize all experiments
    categorized = defaultdict(list)
    for exp in experiments:
        info = extract_key_info(exp)
        cat = categorize_experiment(info)
        categorized[cat].append(info)

    # Sort categories and experiments within categories
    category_order = [
        "Baseline / MA Crossover",
        "Time-Series Momentum",
        "Cross-Sectional Momentum",
        "Regime-Gated",
        "Volatility / VRP",
        "Overnight/Intraday Decomposition",
        "Volume Predictive",
        "Order Flow",
        "Hypothesis H10-H29",
        "DDCV / Selection Bias",
        "Parameter Sweep",
        "Alternatives / Stress Test",
        "New Family (NF) - Recent",
        "New Family (NF) - Factor/Other",
        "Other / Uncategorized",
    ]

    lines = []
    lines.append("# Experiment Lineage Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("**Source:** `.experiments/experiments.jsonl`")
    lines.append(f"**Total Experiments:** {len(experiments)}")
    lines.append("")

    # Summary table
    lines.append("## Summary by Category")
    lines.append("")
    lines.append("| Category | Count | Passed | Failed | Errors |")
    lines.append("|---|---:|---:|---:|---:|")
    for cat in category_order:
        exps = categorized.get(cat, [])
        if not exps:
            continue
        passed = sum(1 for e in exps if str(e["verdict"]).upper() in ("PASS", "TRUE", "COMPLETED"))
        failed = sum(1 for e in exps if str(e["verdict"]).upper() in ("FAIL", "FALSE", "REJECT"))
        errors = sum(1 for e in exps if e["error"])
        lines.append(f"| {cat} | {len(exps)} | {passed} | {failed} | {errors} |")
    lines.append("")

    # Detailed experiment listings
    lines.append("## Detailed Experiment Records")
    lines.append("")

    for cat in category_order:
        exps = categorized.get(cat, [])
        if not exps:
            continue

        lines.append(f"### {cat}")
        lines.append("")
        lines.append(
            "| Exp ID | Name | Timestamp | Git Commit | Verdict | Key Metrics | Config | Artifacts | Error |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")

        # Sort by timestamp
        exps_sorted = sorted(exps, key=lambda x: x["timestamp"])

        for info in exps_sorted:
            exp_id_short = (
                info["exp_id"].split("T")[-1].replace("Z", "")
                if "T" in info["exp_id"]
                else info["exp_id"][:20]
            )
            name = info["name"]
            if len(name) > 30:
                name = name[:27] + "..."

            metrics_str = format_metrics(info["metrics"])
            config_str = ""
            if info["config"]:
                config_items = []
                for k, v in info["config"].items():
                    if isinstance(v, (list, dict)):
                        v = str(v)[:50]
                    config_items.append(f"{k}={v}")
                config_str = "<br>".join(config_items[:3])

            artifacts_str = f"{len(info['artifacts'])} artifacts" if info["artifacts"] else "—"
            error_str = (
                info["error"][:50] + "..."
                if info["error"] and len(info["error"]) > 50
                else (info["error"] or "—")
            )

            lines.append(
                f"| {exp_id_short} | {name} | {info['timestamp']} | {info['git_commit']} | {info['verdict']} | {metrics_str} | {config_str} | {artifacts_str} | {error_str} |"
            )

        lines.append("")

    # Git commit timeline
    lines.append("## Git Commit Timeline")
    lines.append("")
    lines.append("| Git Commit | Date | Experiments | Categories |")
    lines.append("|---|---|---|---|")

    commit_map = defaultdict(lambda: {"dates": [], "exps": [], "cats": set()})
    for exp in experiments:
        info = extract_key_info(exp)
        cat = categorize_experiment(info)
        commit_map[info["git_commit"]]["dates"].append(info["timestamp"])
        commit_map[info["git_commit"]]["exps"].append(info["exp_id"])
        commit_map[info["git_commit"]]["cats"].add(cat)

    for commit, data in sorted(commit_map.items(), key=lambda x: min(x[1]["dates"])):
        date_range = (
            min(data["dates"]) + " to " + max(data["dates"])
            if len(data["dates"]) > 1
            else data["dates"][0]
        )
        lines.append(
            f"| {commit} | {date_range} | {len(data['exps'])} | {', '.join(sorted(data['cats']))} |"
        )

    lines.append("")

    # Write output
    output_path.write_text("\n".join(lines))
    print(f"Report written to {output_path}")


def main():
    jsonl_path = Path(".experiments/experiments.jsonl")
    if not jsonl_path.exists():
        print(f"Error: {jsonl_path} not found", file=sys.stderr)
        sys.exit(1)

    output_path = Path("EXPERIMENT_LINEAGE_REPORT.md")

    experiments = load_experiments(jsonl_path)
    print(f"Loaded {len(experiments)} experiment records")

    generate_report(experiments, output_path)


if __name__ == "__main__":
    main()
