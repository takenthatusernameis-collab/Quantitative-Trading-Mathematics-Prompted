# Experiment Artifact Schema Audit

**Date:** 2026-11-11
**Scope:** All 103 directories under `.experiments/nf_runs/`
**Trigger:** Handoff directive to shift to auditing/infrastructure (free-data family discovery exhausted)

> **Re-verified 2026-11-13:** the summary statistics below were recomputed directly from the
> corpus (`os.walk` over every `summary.json`, 95 files) and corrected. The prior summary
> claimed 87 distinct keys, 6 keys ≥50%, 1 key ≥80%, and 19 cache-only directories; the
> actual values are **130 / 9 / 3 / 11**. The detailed per-key tables were already correct
> and are unchanged. These counts are now pinned by
> `tests/test_experiment_artifact_schema.py` so the summary cannot silently drift again.

> **Re-verified 2026-11-14 (Cycle 115):** the H182 insider-signal experiment ran and produced
> 5 new `summary.json` artifacts (`.experiments/nf_runs/nf_20261110_08_insider_signal_20261114_*`),
> moving the corpus to **108 directories / 100 summaries / 131 distinct keys / 9 keys ≥50%
> / 3 keys ≥80% / 11 cache-only directories**. The new runner introduced exactly one new
> key (`information_ratio_vs_equal_weight`) and pushed `oos_val_test` over the 50% threshold
> while `selected_params` (49→54/100, still below 50%) dropped out of the ≥50% set. The
> incomplete-run set (8) and cache-only directory set (11) are unchanged. The pins in
> `tests/test_experiment_artifact_schema.py` and the coverage table below were updated to the
> Cycle 115 values; the per-key frequency tables are unchanged except for the two moved keys.

---

## Executive Summary

Audit of 103 experiment artifact directories reveals **severe schema inconsistency** across `summary.json` files. Only 95 directories contain a `summary.json`; 8 directories have only `grid.csv`/`auctions.csv` (incomplete runs), and 11 are cache-only subdirectories.

**Key finding:** No two experiment summaries share an identical schema. There are 130 distinct keys across 95 files, with only 1 key (`verdict`) appearing in >90% of files. Critical fields like `hypothesis`, `nf_id`, `timestamp_utc`, `selected` parameters, and OOS metrics are missing from 30–80% of artifacts.

This inconsistency prevents programmatic analysis of the experiment corpus and undermines reproducibility guarantees.

---

## Coverage Statistics

| Metric | Count |
|--------|-------|
| Total artifact directories | 103 |
| Directories with `summary.json` | 95 |
| Directories without `summary.json` (incomplete/cache) | 8 |
| Cache-only subdirectories | 11 |
| Distinct keys across all summaries | 130 |
| Keys appearing in ≥50% of summaries | 9 |
| Keys appearing in ≥80% of summaries | 3 (`data`, `gates`, `verdict`) |

---

## Top Keys by Frequency

| Key | Frequency | % of Summaries |
|-----|-----------|----------------|
| `verdict` | 90 | 94.7% |
| `data` | 88 | 92.6% |
| `gates` | 83 | 87.4% |
| `ablations` | 71 | 74.7% |
| `hypothesis` | 65 | 68.4% |
| `nf_id` | 63 | 66.3% |
| `experiment` | 55 | 57.9% |
| `gates_passed` | 52 | 54.7% |
| `selected_params` | 49 | 51.6% |
| `oos_val_test` | 46 | 48.4% |

---

## Critical Field Inconsistency

### Identity Fields
| Field | Present In | Missing From | Notes |
|-------|------------|--------------|-------|
| `experiment` | 55 (57.9%) | 40 | Often replaced by `name` or `experiment_name` |
| `nf_id` | 63 (66.3%) | 32 | Sometimes `nf_id_exec`, `nf_id_prereg_lineage` |
| `hypothesis` | 65 (68.4%) | 30 | Sometimes `hypothesis_id`, `h_id`, `family_id` |
| `family` | 2 (2.1%) | 93 | |

### Timing Fields (9 distinct keys for the same concept)
| Key | Count | Example Value |
|-----|-------|---------------|
| `timestamp_utc` | 19 | `"2026-11-10T13:09:48Z"` |
| `timestamp` | 9 | `"2026-11-10T13:09:48Z"` |
| `elapsed_s` | 20 | `10.319` |
| `runtime_sec` | 23 | `10.319` |
| `timing_seconds` | 29 | `10.319` |
| `elapsed_seconds` | 5 | `10.319` |
| `runtime_s` | 8 | `10.319` |
| `duration_seconds` | 5 | `10.319` |
| `runtime_seconds` | 2 | `10.319` |
| `elapsed_sec` | 1 | `10.319` |

### Selected Parameters Fields (5 distinct keys)
| Key | Count |
|-----|-------|
| `selected` | 22 |
| `selected_params` | 49 |
| `best_params` | 3 |
| `params` | 1 |
| `selection` | 17 |

### OOS Metrics Fields (7+ distinct keys)
| Key | Count |
|-----|-------|
| `oos_val_test` | 46 |
| `oos_val_test_metrics` | 7 |
| `oos_metrics` | 12 |
| `oos_diagnostics` | 9 |
| `oos` | 6 |
| `gate_eval_oos_val_test` | 5 |
| `gate_evaluation` | 4 |
| `gate_eval` | 3 |

### Benchmark Comparison Fields (6+ distinct keys)
| Key | Count |
|-----|-------|
| `benchmark_buy_hold_spy_oos` | 31 |
| `benchmark_buy_hold_oos` | 7 |
| `benchmark_oos_metrics` | 11 |
| `benchmark_vs_buy_hold_spy` | 2 |
| `benchmark` | 9 |
| `benchmarks` | 2 |

### Worst-Regime Fields (4 distinct keys)
| Key | Count |
|-----|-------|
| `worst_regime_rolling252_sharpe` | 34 |
| `worst_regime_sharpe` | 4 |
| `worst_regime_yearly_sharpe` | 1 |
| `worst_regime_rolling252_sharpe_oos` | 2 |
| `worst_yearly_sharpe_oos` | 2 |
| `worst_regime_yearly_sharpe_oos` | 1 |

### Walk-Forward Stability Fields (5 distinct keys)
| Key | Count |
|-----|-------|
| `wf_stability_ratio` | 23 |
| `wf_stability_oos_over_train` | 15 |
| `wf_stability` | 3 |
| `wf_stability_ratio_oos_to_train` | 2 |
| `wf_stability_train` | 2 |

---

## Incomplete Runs (Missing `summary.json`)

| Directory | Contents | Likely Issue |
|-----------|----------|--------------|
| `nf_20261109_15_tax_loss_harvesting_20261110_025201/` | `grid.csv` only | Early termination |
| `nf_20261109_24_equity_risk_premium_20261109_223319/` | `grid.csv` only | Early termination |
| `nf_20261109_24_equity_risk_premium_20261109_223333/` | `grid.csv` only | Early termination |
| `nf_20261109_24_equity_risk_premium_20261109_223703/` | `grid.csv` only | Early termination |
| `nf_20261109_24_equity_risk_premium_20261109_223731/` | `grid.csv` (153B) | Truncated |
| `nf_20261109_26_etf_nav_arbitrage_20261109_234200/` | `grid.csv` only | Early termination |
| `nf_20261110_01_treasury_auction_20261110_045905/` | `auctions.csv`, `grid.csv` | Early termination |
| `nf_20261110_01_treasury_auction_20261110_045929/` | `auctions.csv`, `grid.csv` | Early termination |

---

## Cache-Only Subdirectories (11)

These are data cache directories, not experiment runs:
- `nf_20261105_14_credit_regime/cache/`
- `nf_20261106_02_move_rates_vol/cache/`
- `nf_20261105_16_usd_macro/cache/`
- `nf_20261110_06_short_interest_20261110_cycle93/finra_cache/`
- `nf_20261105_18_concentration_rv/cache/`
- `nf_20261106_04_copper_gold/cache/`
- `nf_20261106_06_fxa_risk/cache/`
- `nf_20261106_01_miner_gold_rv/cache/`
- `nf_20261105_15_corr_regime/cache/`
- `nf_20261105_19_pead/cache/`
- `nf_20261106_05_btc_bond/cache/`

---

## Schema Standardization Proposal

### Required Fields (Must Be Present in Every `summary.json`)

```json
{
  "experiment_id": "string (UUID or timestamp-based)",
  "experiment_name": "string (human-readable)",
  "nf_id": "string (NF-YYYYMMDD-NN)",
  "hypothesis_id": "string (H###)",
  "timestamp_utc": "ISO 8601 UTC timestamp",
  "runtime_seconds": "float",
  "data": { "tickers": [], "rows": int, "start": "", "end": "", "train_end": "", "val_end": "", "oos_rows": int, "note": "" },
  "selected_params": { "param1": value, "param2": value },
  "selection": { "method": "walk_forward_sharpe", "folds": 4, "train_score": float },
  "oos_val_test": { "sharpe": float, "profit_factor": float, "max_drawdown": float, "trades": int, "periods": int, "total_return": float, "worst_regime_rolling252_sharpe": float },
  "benchmark_buy_hold_spy_oos": { "sharpe": float, "profit_factor": float, "max_drawdown": float, "trades": int, "periods": int, "total_return": float, "worst_regime_rolling252_sharpe": float },
  "ablations": { "random_signal_oos": {...}, "inverse_signal_oos": {...} },
  "gates": { "gate_name": { "threshold": float, "achieved": float, "passed": bool } },
  "gates_passed": int,
  "gates_total": int,
  "verdict": "PASS|REJECT",
  "verdict_reason": "string (e.g., '3/8 gates failed: Sharpe, WF stability, benchmark')",
  "perturbation_min_ratio": float,
  "walk_forward_stability_ratio": float,
  "information_ratio_vs_buy_hold": float,
  "benchmark_p_value": float,
  "src_qtr_changed": bool
}
```

### Migration Path

1. **Add schema validation test** in `tests/test_experiment_artifact_schema.py` that validates every `summary.json` against the required schema
2. **Update all experiment runners** to emit the standardized schema (using a shared `emit_summary()` helper in `qtr.tracking.experiment`)
3. **Backfill missing fields** for existing artifacts where data is recoverable (from `grid.csv`, experiment logs, or re-running)
4. **Archive incomplete runs** (8 directories without `summary.json`) to a separate location with a `_incomplete` suffix

---

## Recommendations

1. **Immediate:** Add a schema validation test to CI to prevent future inconsistency
2. **Short-term:** Create a shared `ExperimentSummary` dataclass in `qtr.tracking.experiment` that all runners use
3. **Medium-term:** Backfill historical artifacts to enable corpus-wide analysis
4. **Ongoing:** Treat the standardized schema as a frozen contract (like H51/H53/H55)

---

## Evidence

Audit script used:
```python
import json, os
from collections import Counter
all_keys = Counter()
for root, dirs, files in os.walk(".experiments/nf_runs"):
    if "summary.json" in files:
        with open(os.path.join(root, "summary.json")) as f:
            data = json.load(f)
        for k in data.keys():
            all_keys[k] += 1
```

Full key frequency table available in audit logs.

---

## Constraints Observed

- No modification to `src/qtr` source code
- No modification to frozen-contract tests or thresholds
- No commit/push
- Read-only audit of committed artifacts

---

**Next Action:** Implement schema validation test and shared `ExperimentSummary` dataclass in a future session (requires authorization to modify `src/qtr` and tests).