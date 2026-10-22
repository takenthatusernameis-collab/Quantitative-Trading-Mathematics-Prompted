"""H55 — the four *nested* `metrics` blocks re-derive from the frozen record.

The gap
-------
§H53 re-derived the thirteen **scalar** keys of the `metrics` block and §H54
re-derived the blocks of the **43** summaries that publish no `metrics` block
at all. Neither pass touched the four **nested** blocks that live *inside* the
`metrics` block of the summaries that do publish one:

=======================  ==========  ========================================
key                      summaries   what it holds
=======================  ==========  ========================================
``ablations``            27          a per-variant metric table (4-11 leaves)
``perturbation``         7           the OAT +/-20 % variant Sharpes + ratio
``perturbation_min_ratio``  7        the perturbation gate's ratio alone
``cross_validation``     2           the QQQ/IWM transfer Sharpes
=======================  ==========  ========================================

Every one of them is a **published** value that gates or informs a published
verdict, and not one of them had ever been re-derived.

§H55 also picks up a fifth block that **no** earlier pass covered: the
**top-level** ``perturbation`` block of the five summaries that publish both a
``metrics`` block and a top-level ``perturbation`` block (H22 x3, H25 x2).
§H53 covered the ``metrics`` block of those summaries and §H54 covered the
summaries with no ``metrics`` block at all, so the top-level block fell
between the two.

What §H55 measured
------------------
**736** published leaf values across **27** summaries. The record splits into
three re-derivation routes, and the split is a *finding*, not a convenience:

1. **The committed ablation equity curves** (20 summaries: H9 x3, H10 x2,
   H21 x1, H22 x5, H23 x7, H25 x2). The engine's equity curve determines its
   own return series exactly, so the OOS-window Sharpe, profit factor,
   maximum drawdown and the Test-window Sharpe re-derive from the artifact
   that published them. The **86** published ablation *trade counts* do not:
   the record holds the ablation's equity curve but never its trade log.
2. **The committed strategy inputs** (11 summaries: H16 x4, H17, H19, H22 x3,
   H25 x2, plus H20 as the exception). These families publish no per-ablation
   artifact at all, but they *do* commit the prices, the volumes and the VIX
   series the strategies were built from, so the blocks can be re-derived by
   re-running the producers' own signal builders over the frozen inputs.
   Every such re-derivation is validated **bit-for-bit** against the committed
   ``best_equity`` / ``equity`` artifact *before* it is used to check any
   published value, which is what makes it a re-derivation and not a guess.
   **H20** cannot: its signal builder needs the daily OHLC panel and the
   record only ever committed the close.
3. **The gate inputs that were never committed** (the two cross-validation
   blocks and H20's whole block). The QQQ/IWM closes the cross validation
   reads, and the OHLC panel H20's signal reads, were fetched at run time and
   never written. Those values are **not functions of the record** and are
   disclosed as such.

The conventions the record hides
--------------------------------
Five distinct conventions hide inside these blocks, and three of them are
*within* a single summary:

1. **The H9 family's ablation block mixes two windows.** Its
   ``oos_sharpe`` and ``max_drawdown`` are OOS-window values, but its
   ``profit_factor`` and ``trades`` are **whole-sample** values — the
   producer read them off the engine's own full-sample metric block. Every
   other family publishes an OOS-window profit factor under the ``oos_``
   prefix.
2. **The H9 family's ablation Sharpe is on the POPULATION standard
   deviation** (``ddof=0``) because the producer passed ``.values`` to
   ``sharpe_ratio`` — while the *same* summary's top-level Sharpes are on
   the SAMPLE standard deviation (``ddof=1``), because there it passed a
   ``pandas.Series``. §H53 recorded the second half of this split; H55
   records the first.
3. **The H16 family was produced under two different monthly-rebalance
   anchors.** The producers' current ``monthly_rebalance`` anchors the
   month-end target on the *actual last trading day* of the month; the other
   convention anchors it on the *calendar* month end. The two differ by one
   trading day on every month boundary, and the difference is enough to move
   the published OOS Sharpe by 3 % (see the negative control). The **first
   two** H16 runs used the calendar anchor and the **last two** used the
   actual-last-trading-day anchor. The contract does not *assume* the anchor:
   it identifies it per summary from the committed equity curve, which
   reproduces bit-for-bit under exactly one of the two.
4. **The first H16 summary published its three per-family ablations as the
   same block.** ``exp_2026-10-13T21-11-45-843908Z`` publishes identical
   values under ``family_value``, ``family_momentum`` and
   ``family_quality``; the block is the *unrestricted* single-factor result
   (all three families, ``n_factors=1``), reproduced here bit-for-bit. The
   three later H16 summaries publish the per-family blocks correctly. The
   block is exploratory — no gate reads it — so no verdict moves.
5. **The H23 family's ``perturbation_min_ratio`` is a fallback, not a
   measurement.** The producer publishes
   ``gate["perturbation"]["min_perturbed_sharpe_ratio"]``, and the ratio is
   ``0.0`` whenever the base OOS Sharpe is not positive — which is the case
   in all **seven** H23 summaries (five publish an OOS Sharpe of exactly
   ``0.0``, two publish a negative one). The published perturbation gate
   therefore reports *the fallback branch*, not a robustness measurement.

The blast radius
----------------
No published gate reads an ``ablations`` block or a ``cross_validation``
block. The published **perturbation** gate reads exactly one number — the
ratio — and that number re-derives exactly in every summary that publishes
it, including the one whose variant Sharpes cannot be re-derived. No
published number moves.

Scope of this module
--------------------
This module is **read-only** against the frozen artifacts: it writes
nothing, touches no network and re-runs no grid. It *does* re-execute a
bounded number of backtests (the producers' own signal builders over the
committed inputs) for the summaries of route 2 whose re-derivation is
possible; each such re-execution is validated bit-for-bit against the
committed equity artifact first, and nothing is published or rewritten.
"""

from __future__ import annotations

import json
import pathlib
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "tests", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from _utils_parquet import read_parquet_safe  # noqa: E402

ARTIFACTS = ROOT / ".experiments" / "artifacts"
EXPERIMENTS = ROOT / ".experiments" / "experiments.jsonl"

#: The engine's initial capital. Every producer in this record starts from
#: one million, so the first bar's return is recoverable from the equity
#: curve: ``equity[0] / INITIAL_CAPITAL - 1``.
INITIAL_CAPITAL = 1_000_000.0

#: The four nested keys of the `metrics` block.
NESTED_KEYS = ("ablations", "perturbation", "perturbation_min_ratio", "cross_validation")

#: Relative tolerance for a re-derivation. The measured residuals are 0 for
#: the re-executed families and at most 7e-14 for the equity-reconstructed
#: ones; the tolerance leaves two orders of magnitude of head-room.
TOLERANCE = 1e-9


# ---------------------------------------------------------------------------
# 1. The record
# ---------------------------------------------------------------------------
def _producer_names() -> dict[str, str]:
    """Map every committed experiment id to the producer that wrote it."""
    names: dict[str, str] = {}
    for line in EXPERIMENTS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:  # pragma: no cover - defensive
            continue
        metadata = record.get("metadata") or {}
        experiment_id = metadata.get("experiment_id")
        if experiment_id:
            names[experiment_id] = metadata.get("name")
    return names


PRODUCER_NAMES = _producer_names()


def _nested_summaries() -> dict[str, dict]:
    """The summaries that publish at least one nested block, and the block."""
    out: dict[str, dict] = {}
    for path in sorted(ARTIFACTS.glob("*/summary.json")):
        summary = json.loads(path.read_text())
        metrics = summary.get("metrics") or {}
        blocks = {key: metrics[key] for key in NESTED_KEYS if key in metrics}
        if "perturbation" in summary:
            blocks["top_level_perturbation"] = summary["perturbation"]
        if blocks:
            out[path.parent.name] = {"path": path, "summary": summary, "blocks": blocks}
    return out


NESTED = _nested_summaries()


#: The producer families that publish a nested block, and the shape each one
#: publishes. ``h9`` is the four-key block, ``h10`` the five-key block and
#: ``oos_metrics`` the seven-key block wrapped in an ``oos_metrics`` object.
ABLATION_SHAPES = {
    "h9_intraday_tsmom_ctexits_v2": "h9",
    "h10_intraday_tsmom_pfopt": "h10",
    "h21_futures_tsmom_multicontract": "h10",
    "h22_futures_tsmom_voltarget": "h10",
    "h23_crypto_futures_tsmom": "h10",
    "h25_futures_tsmom_pfmargin": "h10",
    "h16_factor_timing": "oos_metrics",
    "h17_vrp": "oos_metrics",
    "h19_volume_predictive": "oos_metrics",
    "h20_signed_volume": "oos_metrics",
}

#: The H9 family names its ablation artifacts after the *variant*, not after
#: the published ablation key: the published ``raw_hourly_no_exits`` ablation
#: is committed as ``ablations_raw_hourly_equity.parquet``. The mapping is
#: pinned here so the contract does not depend on a name coincidence.
ABLATION_ARTIFACT_ALIASES = {
    "raw_hourly_no_exits": "ablations_raw_hourly_equity",
}


def _shape(experiment_id: str) -> str:
    return ABLATION_SHAPES[PRODUCER_NAMES[experiment_id]]


# ---------------------------------------------------------------------------
# 2. The reconstruction primitives
# ---------------------------------------------------------------------------
def _reconstruct_returns(equity: pd.Series, initial_capital: float = INITIAL_CAPITAL) -> pd.Series:
    """Recover the engine's net return series from its equity curve.

    The engine computes ``equity = (1 + net_returns).cumprod() * capital``,
    so the first bar's return is ``equity[0] / capital - 1`` and every later
    bar's return is the ratio of two consecutive equity values. The ratios
    are exact up to one ulp per bar; the accumulated error of the cumprod
    cancels in the ratio.
    """
    values = equity.astype(float)
    returns = values / values.shift(1) - 1.0
    returns.iloc[0] = values.iloc[0] / initial_capital - 1.0
    return returns


def _sharpe(returns: pd.Series, ddof: int = 0) -> float:
    """The producers' Sharpe: mean / std * sqrt(252), with the std's ddof
    chosen by the caller (``0`` = population, the convention every nested
    block uses)."""
    array = returns.to_numpy(dtype=float)
    if array.size == 0:
        return 0.0
    if array.std(ddof=ddof) <= 1e-15:
        return 0.0
    return float(array.mean() / array.std(ddof=ddof) * np.sqrt(252))


def _period_metrics(returns: pd.Series) -> dict:
    """The producers' ``_period_metrics`` block (without the trade count)."""
    series = returns.dropna()
    cumulative = (1.0 + series).cumprod()
    drawdown = float((cumulative / cumulative.cummax() - 1.0).min()) if len(cumulative) > 0 else 0.0
    gross_profit = float(series[series > 0].sum())
    gross_loss = float(abs(series[series < 0].sum()))
    return {
        "sharpe": _sharpe(series),
        "max_drawdown": drawdown,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "n_periods": int(len(series)),
    }


def _fractional_splits(index: pd.Index) -> tuple[pd.Series, pd.Series]:
    """The H9/H10/H21/H22/H23/H25 split rule: the last 20 % of the bars are
    the Test window, the 25 % before them the Val window, and the OOS window
    is the two together."""
    count = len(index)
    train_end = index[int(count * 0.55)]
    val_end = index[int(count * 0.8)]
    val_mask = (index > train_end) & (index <= val_end)
    test_mask = index > val_end
    return val_mask | test_mask, test_mask


def _residual(published: float, rederived: float) -> float:
    if published == rederived:
        return 0.0
    if not np.isfinite(published) or not np.isfinite(rederived):
        return float("inf")
    return abs(published - rederived) / max(abs(published), abs(rederived), 1e-300)


def _flatten(block, prefix: str = "") -> list[tuple[str, float]]:
    """Every *leaf* of a published block, with its path inside the block."""
    if not isinstance(block, dict):
        return [(prefix, block)]
    leaves: list[tuple[str, float]] = []
    for key, value in block.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            leaves.extend(_flatten(value, path))
        else:
            leaves.append((path, value))
    return leaves


# ---------------------------------------------------------------------------
# 3. The re-derivation table
# ---------------------------------------------------------------------------
@dataclass
class Leaf:
    """One published leaf value and what the record says about it."""

    experiment_id: str
    block: str
    path: str
    published: float
    rederived: float | None = None
    status: str = "rederived"
    reason: str = ""


@dataclass
class Table:
    leaves: list[Leaf] = field(default_factory=list)

    def add(self, **kwargs) -> None:
        self.leaves.append(Leaf(**kwargs))

    @property
    def rederived(self) -> list[Leaf]:
        return [leaf for leaf in self.leaves if leaf.status == "rederived"]

    @property
    def not_rederivable(self) -> list[Leaf]:
        return [leaf for leaf in self.leaves if leaf.status == "not_rederivable"]

    def for_experiment(self, experiment_id: str) -> list[Leaf]:
        return [leaf for leaf in self.leaves if leaf.experiment_id == experiment_id]


def _ablation_equity_path(directory: pathlib.Path, ablation: str) -> pathlib.Path | None:
    """The committed equity curve of one ablation, under either of the two
    naming conventions the record uses."""
    alias = ABLATION_ARTIFACT_ALIASES.get(ablation)
    candidates = []
    if alias is not None:
        candidates.append(directory / f"{alias}.parquet")
    candidates.append(directory / f"ablations__{ablation}__equity.parquet")
    candidates.append(directory / f"ablations_{ablation}_equity.parquet")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _ablation_derived_values(
    directory: pathlib.Path, ablation: str, shape: str, prices: pd.DataFrame
) -> dict[str, float]:
    """The four metrics an ablation's committed equity curve determines."""
    equity_path = _ablation_equity_path(directory, ablation)
    if equity_path is None:
        return {}
    equity = read_parquet_safe(equity_path)
    returns = _reconstruct_returns(equity[equity.columns[0]])
    oos_mask, test_mask = _fractional_splits(prices.index)
    oos = _period_metrics(returns[oos_mask])
    test = _period_metrics(returns[test_mask])
    full = _period_metrics(returns)
    if shape == "h9":
        return {
            "oos_sharpe": oos["sharpe"],
            "max_drawdown": oos["max_drawdown"],
            "profit_factor": full["profit_factor"],
        }
    return {
        "oos_sharpe": oos["sharpe"],
        "oos_profit_factor": oos["profit_factor"],
        "oos_max_drawdown": oos["max_drawdown"],
        "test_sharpe": test["sharpe"],
    }


def _rederive_from_equity(table: Table) -> None:
    """Route 1: the ablation's own committed equity curve."""
    for experiment_id, record in NESTED.items():
        ablations = record["blocks"].get("ablations")
        if not ablations:
            continue
        directory = record["path"].parent
        shape = _shape(experiment_id)
        prices_path = directory / "prices.parquet"
        if not prices_path.exists():
            continue
        prices = read_parquet_safe(prices_path)
        for ablation, published_block in ablations.items():
            if shape == "oos_metrics":
                continue
            derived = _ablation_derived_values(directory, ablation, shape, prices)
            for key, published in published_block.items():
                path = f"ablations.{ablation}.{key}"
                if key in derived:
                    table.add(
                        experiment_id=experiment_id,
                        block="ablations",
                        path=path,
                        published=published,
                        rederived=derived[key],
                    )
                else:
                    table.add(
                        experiment_id=experiment_id,
                        block="ablations",
                        path=path,
                        published=published,
                        status="not_rederivable",
                        reason=(
                            "the ablation's own trade log was never committed; the record "
                            "holds the ablation's equity curve but not its trades"
                        ),
                    )


def _rederive_from_inputs(table: Table) -> None:
    """Route 2: re-run the producers' own signal builders over the committed
    inputs. The re-execution is validated bit-for-bit against the committed
    equity artifact before any published value is checked."""
    from h55_rederivation import rederive_family

    for experiment_id, record in NESTED.items():
        ablations = record["blocks"].get("ablations")
        if not ablations:
            continue
        producer = PRODUCER_NAMES[experiment_id]
        if ABLATION_SHAPES[producer] != "oos_metrics":
            continue
        outcome = rederive_family(producer, record["path"].parent, record["summary"])
        for ablation, published_block in ablations.items():
            derived_block = outcome["ablations"].get(ablation) if outcome else None
            for suffix, published in _flatten(published_block):
                path = f"ablations.{ablation}.{suffix}"
                derived = None
                if derived_block is not None:
                    cursor = derived_block
                    for part in suffix.split("."):
                        cursor = cursor.get(part) if isinstance(cursor, dict) else None
                        if cursor is None:
                            break
                    derived = cursor if isinstance(cursor, (int, float)) else None
                if derived is None:
                    table.add(
                        experiment_id=experiment_id,
                        block="ablations",
                        path=path,
                        published=published,
                        status="not_rederivable",
                        reason=outcome_reason(producer),
                    )
                else:
                    table.add(
                        experiment_id=experiment_id,
                        block="ablations",
                        path=path,
                        published=published,
                        rederived=float(derived),
                    )


def outcome_reason(producer: str) -> str:
    """Why a family's block cannot be re-derived from the record."""
    if producer == "h20_signed_volume":
        return (
            "the daily OHLC panel the signal builder reads was never committed; "
            "the record holds the SPY close and volume only"
        )
    return "the family's inputs were never committed"


def _rederive_perturbation(table: Table) -> None:
    """The OAT +/-20 % perturbation blocks, inside `metrics` and at the top
    level of the summary."""
    from h55_rederivation import rederive_family

    for experiment_id, record in NESTED.items():
        for block_name in ("perturbation", "top_level_perturbation"):
            block = record["blocks"].get(block_name)
            if not block:
                continue
            producer = PRODUCER_NAMES[experiment_id]
            published_variants = block["variants"]
            published_ratio = block["min_perturbed_sharpe_ratio"]

            # The ratio is a function of the published variants and the
            # published base OOS Sharpe alone -- it re-derives in every
            # summary that publishes it.
            base = record["summary"]["metrics"].get("oos_sharpe")
            if base is not None and base > 0:
                derived_ratio = min(published_variants.values()) / base
            else:
                derived_ratio = 0.0
            table.add(
                experiment_id=experiment_id,
                block=block_name,
                path="min_perturbed_sharpe_ratio",
                published=published_ratio,
                rederived=derived_ratio,
            )

            outcome = rederive_family(producer, record["path"].parent, record["summary"])
            variants = outcome["perturbation"] if outcome else None
            for name, published in published_variants.items():
                if variants is None or name not in variants:
                    table.add(
                        experiment_id=experiment_id,
                        block=block_name,
                        path=f"variants.{name}",
                        published=published,
                        status="not_rederivable",
                        reason=outcome_reason(producer),
                    )
                else:
                    table.add(
                        experiment_id=experiment_id,
                        block=block_name,
                        path=f"variants.{name}",
                        published=published,
                        rederived=variants[name],
                    )


def _rederive_perturbation_min_ratio(table: Table) -> None:
    """The H23 family's standalone perturbation ratio."""
    for experiment_id, record in NESTED.items():
        if "perturbation_min_ratio" not in record["blocks"]:
            continue
        base = record["summary"]["metrics"].get("oos_sharpe")
        derived = 0.0 if base is None or base <= 0 else float("nan")
        table.add(
            experiment_id=experiment_id,
            block="perturbation_min_ratio",
            path="perturbation_min_ratio",
            published=record["blocks"]["perturbation_min_ratio"],
            rederived=derived,
        )


def _rederive_cross_validation(table: Table) -> None:
    """The cross-validation blocks: the QQQ/IWM closes were never committed."""
    for experiment_id, record in NESTED.items():
        block = record["blocks"].get("cross_validation")
        if not block:
            continue
        for symbol, values in block.items():
            for key, published in values.items():
                table.add(
                    experiment_id=experiment_id,
                    block="cross_validation",
                    path=f"cross_validation.{symbol}.{key}",
                    published=published,
                    status="not_rederivable",
                    reason=(
                        "the cross-validation closes (QQQ, IWM) were fetched at run "
                        "time and never committed"
                    ),
                )


def _build_table() -> Table:
    table = Table()
    _rederive_from_equity(table)
    _rederive_from_inputs(table)
    _rederive_perturbation(table)
    _rederive_perturbation_min_ratio(table)
    _rederive_cross_validation(table)
    return table


TABLE = _build_table()


# ---------------------------------------------------------------------------
# 4. The tests
# ---------------------------------------------------------------------------
class TestTheRecord:
    """The record is named before anything is checked against it."""

    def test_the_four_nested_keys_are_pinned(self):
        assert NESTED_KEYS == (
            "ablations",
            "perturbation",
            "perturbation_min_ratio",
            "cross_validation",
        )

    def test_the_summaries_that_publish_a_nested_block_are_pinned(self):
        counts = {
            key: sum(1 for record in NESTED.values() if key in record["blocks"])
            for key in NESTED_KEYS + ("top_level_perturbation",)
        }
        assert counts == {
            "ablations": 27,
            "perturbation": 7,
            "perturbation_min_ratio": 7,
            "cross_validation": 2,
            "top_level_perturbation": 5,
        }
        assert len(NESTED) == 27

    def test_the_published_leaf_count_is_pinned(self):
        assert len(TABLE.leaves) == 736

    def test_every_published_leaf_is_accounted_for(self):
        for experiment_id, record in NESTED.items():
            for key, block in record["blocks"].items():
                published = len(_flatten(block))
                accounted = sum(
                    1 for leaf in TABLE.for_experiment(experiment_id) if leaf.block == key
                )
                assert accounted == published, (experiment_id, key, accounted, published)

    def test_the_producer_families_are_pinned(self):
        families = sorted({PRODUCER_NAMES[eid] for eid in NESTED})
        assert families == [
            "h10_intraday_tsmom_pfopt",
            "h16_factor_timing",
            "h17_vrp",
            "h19_volume_predictive",
            "h20_signed_volume",
            "h21_futures_tsmom_multicontract",
            "h22_futures_tsmom_voltarget",
            "h23_crypto_futures_tsmom",
            "h25_futures_tsmom_pfmargin",
            "h9_intraday_tsmom_ctexits_v2",
        ]


class TestReDerivation:
    """Every leaf the record can carry is re-derived from the record."""

    def test_every_rederivable_leaf_agrees(self):
        failures = []
        for leaf in TABLE.rederived:
            residual = _residual(leaf.published, leaf.rederived)
            if not (residual <= TOLERANCE):
                failures.append((leaf.path, leaf.published, leaf.rederived, residual))
        assert not failures, failures[:10]

    def test_the_measured_residuals_are_recorded(self):
        residuals = [
            _residual(leaf.published, leaf.rederived)
            for leaf in TABLE.rederived
            if leaf.rederived is not None
        ]
        assert max(residuals) <= TOLERANCE
        assert min(residuals) == 0.0

    def test_the_rederivable_and_disclosed_counts_are_pinned(self):
        assert len(TABLE.rederived) == 610
        assert len(TABLE.not_rederivable) == 126

    def test_every_disclosed_leaf_names_its_reason(self):
        for leaf in TABLE.not_rederivable:
            assert leaf.reason, leaf.path
            assert leaf.rederived is None

    def test_the_ablation_trade_counts_are_the_disclosed_ones(self):
        disclosed = [
            leaf
            for leaf in TABLE.not_rederivable
            if leaf.block == "ablations"
            and leaf.path.endswith((".trades", ".oos_trades"))
            and ABLATION_SHAPES[PRODUCER_NAMES[leaf.experiment_id]] in ("h9", "h10")
        ]
        assert len(disclosed) == 86
        assert {leaf.experiment_id for leaf in disclosed} == {
            eid
            for eid, record in NESTED.items()
            if "ablations" in record["blocks"]
            and ABLATION_SHAPES[PRODUCER_NAMES[eid]] in ("h9", "h10")
        }

    def test_the_cross_validation_blocks_are_disclosed(self):
        disclosed = [leaf for leaf in TABLE.not_rederivable if leaf.block == "cross_validation"]
        assert len(disclosed) == 8
        assert {leaf.experiment_id for leaf in disclosed} == {
            "exp_2026-10-13T22-40-41-870350Z",
            "exp_2026-10-13T23-06-33-191710Z",
        }

    def test_the_h20_blocks_are_disclosed(self):
        disclosed = [
            leaf
            for leaf in TABLE.not_rederivable
            if leaf.experiment_id == "exp_2026-10-13T23-06-33-191710Z"
        ]
        assert len(disclosed) == 36  # 28 ablation leaves + 4 variants + 4 cross-val
        assert all("OHLC" in leaf.reason for leaf in disclosed if leaf.block == "ablations")

    def test_the_top_level_perturbation_blocks_re_derive(self):
        leaves = [leaf for leaf in TABLE.leaves if leaf.block == "top_level_perturbation"]
        assert len(leaves) == 25  # 5 summaries x (4 variants + the ratio)
        assert all(leaf.status == "rederived" for leaf in leaves)


class TestConventions:
    """The conventions the record hides are pinned, not assumed."""

    def test_the_h9_ablation_block_mixes_an_oos_and_a_whole_sample_window(self):
        checked = 0
        for experiment_id, record in NESTED.items():
            if _shape(experiment_id) != "h9":
                continue
            prices = read_parquet_safe(record["path"].parent / "prices.parquet")
            for ablation, published in record["blocks"]["ablations"].items():
                derived = _ablation_derived_values(record["path"].parent, ablation, "h9", prices)
                assert _residual(published["profit_factor"], derived["profit_factor"]) <= TOLERANCE
                assert _residual(published["max_drawdown"], derived["max_drawdown"]) <= TOLERANCE
                # the OOS-window profit factor is a *different* number
                oos_mask, _ = _fractional_splits(prices.index)
                equity = read_parquet_safe(_ablation_equity_path(record["path"].parent, ablation))
                window = _reconstruct_returns(equity[equity.columns[0]])[oos_mask]
                oos_profit_factor = _period_metrics(window)["profit_factor"]
                assert _residual(published["profit_factor"], oos_profit_factor) > 1e-6
                checked += 1
        assert checked == 6

    def test_the_h9_ablation_sharpe_is_on_the_population_standard_deviation(self):
        checked = 0
        for experiment_id, record in NESTED.items():
            if _shape(experiment_id) != "h9":
                continue
            prices = read_parquet_safe(record["path"].parent / "prices.parquet")
            oos_mask, _ = _fractional_splits(prices.index)
            for ablation, published in record["blocks"]["ablations"].items():
                path = _ablation_equity_path(record["path"].parent, ablation)
                equity = read_parquet_safe(path)
                window = _reconstruct_returns(equity[equity.columns[0]])[oos_mask]
                assert _residual(published["oos_sharpe"], _sharpe(window, ddof=0)) <= TOLERANCE
                assert _residual(published["oos_sharpe"], _sharpe(window, ddof=1)) > 1e-6
                checked += 1
        assert checked == 6

    def test_the_perturbation_ratio_is_the_fallback_when_the_base_sharpe_is_not_positive(self):
        checked = 0
        for experiment_id, record in NESTED.items():
            if "perturbation_min_ratio" not in record["blocks"]:
                continue
            base = record["summary"]["metrics"]["oos_sharpe"]
            assert base <= 0
            assert record["blocks"]["perturbation_min_ratio"] == 0.0
            checked += 1
        assert checked == 7

    def test_the_rebalance_anchor_is_pinned(self):
        from h55_rederivation import (
            ACTUAL_LAST_TRADING_DAY_REBALANCE,
            CALENDAR_MONTH_END_REBALANCE,
        )

        assert CALENDAR_MONTH_END_REBALANCE is not None
        assert ACTUAL_LAST_TRADING_DAY_REBALANCE is not None

    def test_the_h16_family_used_two_different_rebalance_anchors(self):
        """The anchor is identified from the committed equity curve, and the
        four H16 summaries split two-and-two across the two anchors."""
        from h55_rederivation import (
            ACTUAL_LAST_TRADING_DAY_REBALANCE,
            CALENDAR_MONTH_END_REBALANCE,
            rederive_family,
        )

        anchors = {}
        for experiment_id, record in NESTED.items():
            if PRODUCER_NAMES[experiment_id] != "h16_factor_timing":
                continue
            outcome = rederive_family(
                PRODUCER_NAMES[experiment_id],
                record["path"].parent,
                record["summary"],
            )
            assert outcome is not None
            anchors[experiment_id] = outcome["rebalance"]
        assert {
            name for name, anchor in anchors.items() if anchor is CALENDAR_MONTH_END_REBALANCE
        } == {
            "exp_2026-10-13T21-11-45-843908Z",
            "exp_2026-10-13T21-13-09-580962Z",
        }
        assert {
            name for name, anchor in anchors.items() if anchor is ACTUAL_LAST_TRADING_DAY_REBALANCE
        } == {
            "exp_2026-10-13T21-18-23-178134Z",
            "exp_2026-10-13T21-22-02-751156Z",
        }

    def test_the_first_h16_summary_published_one_family_block_three_times(self):
        experiment_id = "exp_2026-10-13T21-11-45-843908Z"
        block = NESTED[experiment_id]["blocks"]["ablations"]
        family_blocks = [
            json.dumps(block[name]["oos_metrics"], sort_keys=True)
            for name in ("family_value", "family_momentum", "family_quality")
        ]
        assert family_blocks[0] == family_blocks[1] == family_blocks[2]
        # the later H16 summaries publish three distinct blocks
        later = NESTED["exp_2026-10-13T21-13-09-580962Z"]["blocks"]["ablations"]
        later_blocks = [
            json.dumps(later[name]["oos_metrics"], sort_keys=True)
            for name in ("family_value", "family_momentum", "family_quality")
        ]
        assert len(set(later_blocks)) == 3


class TestNegativeControls:
    """The checks are behavioural, not API checks."""

    def test_the_sample_standard_deviation_breaks_the_ablation_sharpes(self):
        broke = 0
        degenerate = 0
        for experiment_id, record in NESTED.items():
            if _shape(experiment_id) not in ("h9", "h10"):
                continue
            prices = read_parquet_safe(record["path"].parent / "prices.parquet")
            oos_mask, _ = _fractional_splits(prices.index)
            for ablation, published in record["blocks"]["ablations"].items():
                path = _ablation_equity_path(record["path"].parent, ablation)
                if path is None:
                    continue
                equity = read_parquet_safe(path)
                window = _reconstruct_returns(equity[equity.columns[0]])[oos_mask]
                if _residual(published["oos_sharpe"], _sharpe(window, ddof=1)) > 1e-6:
                    broke += 1
                elif published["oos_sharpe"] == 0.0:
                    degenerate += 1
        assert broke == 78
        assert degenerate == 8

    def test_the_current_rebalance_anchor_fails_the_bit_for_bit_validation(self):
        from h55_rederivation import ACTUAL_LAST_TRADING_DAY_REBALANCE, rederive_family

        experiment_id = "exp_2026-10-13T21-11-45-843908Z"
        directory = NESTED[experiment_id]["path"].parent
        outcome = rederive_family(
            PRODUCER_NAMES[experiment_id],
            directory,
            NESTED[experiment_id]["summary"],
            monthly_rebalance=ACTUAL_LAST_TRADING_DAY_REBALANCE,
        )
        assert outcome is None

    def test_the_current_rebalance_anchor_breaks_the_published_variants(self):
        from h55_rederivation import ACTUAL_LAST_TRADING_DAY_REBALANCE, rederive_family

        experiment_id = "exp_2026-10-13T21-11-45-843908Z"
        directory = NESTED[experiment_id]["path"].parent
        published = NESTED[experiment_id]["blocks"]["perturbation"]["variants"]
        outcome = rederive_family(
            PRODUCER_NAMES[experiment_id],
            directory,
            NESTED[experiment_id]["summary"],
            monthly_rebalance=ACTUAL_LAST_TRADING_DAY_REBALANCE,
            require_match=False,
        )
        broken = 0
        for name, value in published.items():
            if _residual(value, outcome["perturbation"][name]) > 1e-6:
                broken += 1
        assert broken == len(published)

    def test_a_nudged_published_value_fails_the_residual_check(self):
        leaf = next(leaf for leaf in TABLE.rederived if leaf.rederived is not None)
        nudged = leaf.published * 1.001
        assert _residual(nudged, leaf.rederived) > TOLERANCE


class TestBlastRadius:
    """Nothing a gate reads moves."""

    def test_no_published_gate_reads_an_ablation_or_cross_validation_block(self):
        for experiment_id, record in NESTED.items():
            passes = record["summary"].get("passes")
            if not isinstance(passes, dict):
                continue
            assert not any("ablation" in key for key in passes)
            assert not any("cross" in key for key in passes)

    def test_the_perturbation_gate_reads_only_the_ratio(self):
        checked = 0
        without_values = []
        for experiment_id, record in NESTED.items():
            passes = record["summary"].get("passes")
            if not isinstance(passes, dict) or "perturbation" not in passes:
                continue
            ratio_leaves = [
                leaf
                for leaf in TABLE.for_experiment(experiment_id)
                if leaf.path in ("min_perturbed_sharpe_ratio", "perturbation_min_ratio")
            ]
            if not ratio_leaves:
                without_values.append(experiment_id)
                continue
            assert len(ratio_leaves) == 1
            assert ratio_leaves[0].status == "rederived"
            checked += 1
        assert checked == 19
        # Two H22 summaries publish the perturbation *gate* but not the
        # perturbation *values*: the gate is a published boolean whose
        # evidence was never published.
        assert sorted(without_values) == [
            "exp_2026-10-14T07-12-35-292010Z",
            "exp_2026-10-14T07-12-59-473353Z",
        ]

    def test_the_two_gate_only_summaries_really_publish_no_perturbation_values(self):
        for experiment_id in (
            "exp_2026-10-14T07-12-35-292010Z",
            "exp_2026-10-14T07-12-59-473353Z",
        ):
            summary = NESTED[experiment_id]["summary"]
            assert "perturbation" not in summary
            assert "perturbation_min_ratio" not in (summary.get("metrics") or {})
            assert summary["passes"]["perturbation"] is True
