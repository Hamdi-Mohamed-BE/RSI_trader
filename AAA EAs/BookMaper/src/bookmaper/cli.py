from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date
from typing import Any

from .active_eas import evaluate_regime_filter
from .backtest import RegimeEAConfig, optimize_on_training, simulate_regime_ea
from .config import (
    ARTIFACT_ROOT,
    ASSETS,
    TEST_END,
    TEST_START,
    TRAIN_SCORE_START,
    ensure_directories,
)
from .data import fetch_yahoo
from .regime import current_snapshot
from .reporting import (
    artifact_paths,
    plot_active_filter,
    plot_standalone,
    write_active_csv,
    write_equity_csv,
    write_full_report,
    write_json,
    write_standalone_summary_csv,
)


PUBLIC_ASSETS = ("xau", "us100", "btc", "eth")
FILTER_ASSETS = PUBLIC_ASSETS + ("us30",)


def _plain_standalone(results: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, result in results.items():
        payload[key] = {
            name: value
            for name, value in result.items()
            if name not in {"literal", "optimized"}
        }
        for variant in ("literal", "optimized"):
            payload[key][variant] = {
                "config": result[variant]["config"],
                "period": result[variant]["period"],
                "metrics": result[variant]["metrics"],
                "trades": result[variant]["trades"],
                "equity": [
                    {"date": when.isoformat(), "equity": round(float(value), 4)}
                    for when, value in result[variant]["equity"].items()
                ],
            }
    return payload


def _plain_active(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "baseline": {
            "metrics": result["baseline"]["metrics"],
            "equity": [
                {"time": when.isoformat(), "balance": round(float(value), 4)}
                for when, value in result["baseline"]["equity"].items()
            ],
        },
        "filtered": {
            "metrics": result["filtered"]["metrics"],
            "equity": [
                {"time": when.isoformat(), "balance": round(float(value), 4)}
                for when, value in result["filtered"]["equity"].items()
            ],
        },
        "by_ea": result["by_ea"],
        "audits": result["audits"],
        "decisions": result["decisions"],
    }


def run_all(*, refresh: bool) -> dict[str, Any]:
    ensure_directories()
    paths = artifact_paths()
    market = {key: fetch_yahoo(ASSETS[key], refresh=refresh) for key in FILTER_ASSETS}
    selected: dict[str, dict[str, Any]] = {}
    standalone: dict[str, Any] = {}
    literal_config = RegimeEAConfig()
    cached_signals = None
    cached_standalone = None
    if not refresh and paths["signals"].is_file() and paths["standalone_json"].is_file():
        cached_signals = json.loads(paths["signals"].read_text(encoding="utf-8"))
        cached_standalone = json.loads(paths["standalone_json"].read_text(encoding="utf-8"))

    for key in FILTER_ASSETS:
        asset = ASSETS[key]
        if cached_signals is not None:
            best = RegimeEAConfig(**cached_signals["selected_configs"][key])
            prior = cached_standalone.get(key, {}) if cached_standalone else {}
            training_metrics = prior.get("training_metrics", {})
            top_training = prior.get("top_training_candidates", [])
        else:
            best, training_metrics, top_training = optimize_on_training(
                market[key],
                start=TRAIN_SCORE_START,
                end="2025-08-10",
                roundtrip_cost_bps=asset.roundtrip_cost_bps,
            )
        selected[key] = asdict(best)
        if key not in PUBLIC_ASSETS:
            continue
        literal = simulate_regime_ea(
            market[key],
            literal_config,
            start=TEST_START,
            end=TEST_END,
            roundtrip_cost_bps=asset.roundtrip_cost_bps,
        )
        optimized = simulate_regime_ea(
            market[key],
            best,
            start=TEST_START,
            end=TEST_END,
            roundtrip_cost_bps=asset.roundtrip_cost_bps,
        )
        standalone[key] = {
            "label": asset.label,
            "ticker": asset.ticker,
            "data_source": "Yahoo Finance daily adjusted OHLCV research proxy",
            "roundtrip_cost_bps": asset.roundtrip_cost_bps,
            "training_period": {"start": TRAIN_SCORE_START, "end": "2025-08-10"},
            "training_metrics": training_metrics,
            "top_training_candidates": top_training,
            "literal": literal,
            "optimized": optimized,
        }

    active = evaluate_regime_filter(market, selected)
    snapshots = {
        key: (
            current_snapshot(
                market[key]["Close"],
                window=int(selected[key]["window"]),
                threshold=float(selected[key]["threshold"]),
            )
            | {"market_data_through": market[key].index[-1].date().isoformat()}
        )
        for key in FILTER_ASSETS
    }
    write_json(paths["standalone_json"], _plain_standalone(standalone))
    write_json(paths["active_json"], _plain_active(active))
    write_json(
        paths["signals"],
        {
            "as_of": date.today().isoformat(),
            "selected_configs": selected,
            "signals": snapshots,
        },
    )
    write_json(
        paths["locked_settings"],
        {
            "selection_period": {"start": TRAIN_SCORE_START, "end": "2025-08-10"},
            "locked_test_period": {"start": TEST_START, "end": TEST_END},
            "selected_configs": selected,
        },
    )
    write_standalone_summary_csv(standalone, paths["standalone_csv"])
    write_equity_csv(standalone, paths["standalone_equity_csv"])
    write_active_csv(active, paths["active_csv"])
    plot_standalone(standalone, paths["standalone_graph"])
    plot_active_filter(active, paths["active_graph"])
    write_full_report(standalone, active, snapshots, paths["report"])
    return {
        "standalone": {key: value["optimized"]["metrics"] for key, value in standalone.items()},
        "active_baseline": active["baseline"]["metrics"],
        "active_filtered": active["filtered"]["metrics"],
        "artifacts": {key: str(value) for key, value in paths.items()},
    }


def run_signals(*, refresh: bool) -> dict[str, Any]:
    paths = artifact_paths()
    if not paths["signals"].is_file():
        return run_all(refresh=refresh)
    stored = json.loads(paths["signals"].read_text(encoding="utf-8"))
    configs = stored["selected_configs"]
    snapshots: dict[str, Any] = {}
    for key in FILTER_ASSETS:
        frame = fetch_yahoo(ASSETS[key], refresh=refresh)
        snapshots[key] = current_snapshot(
            frame["Close"],
            window=int(configs[key]["window"]),
            threshold=float(configs[key]["threshold"]),
        ) | {"market_data_through": frame.index[-1].date().isoformat()}
    payload = {"as_of": date.today().isoformat(), "selected_configs": configs, "signals": snapshots}
    write_json(paths["signals"], payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Markov regime EA research runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("all", "download evidence, optimize on training data and run locked tests"),
        ("signals", "refresh current regime probabilities using locked settings"),
    ):
        child = subparsers.add_parser(command, help=help_text)
        child.add_argument("--refresh", action="store_true", help="force a fresh market-data download")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_all(refresh=args.refresh) if args.command == "all" else run_signals(refresh=args.refresh)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
