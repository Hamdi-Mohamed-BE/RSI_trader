from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json

import pandas as pd

from .article_engine import ArticleParams, backtest_article_model
from .config import load_config
from .engine import Trade, metrics
from .mt5_data import connection, discover_symbols, load_m1, symbol_metadata


UTC = timezone.utc


def _split_three(
    trades: list[Trade],
    train_end: datetime,
    validation_end: datetime,
) -> tuple[list[Trade], list[Trade], list[Trade]]:
    train: list[Trade] = []
    validation: list[Trade] = []
    test: list[Trade] = []
    train_marker = pd.Timestamp(train_end)
    validation_marker = pd.Timestamp(validation_end)
    for trade in trades:
        entry = pd.Timestamp(trade.entry_time)
        if entry < train_marker:
            train.append(trade)
        elif entry < validation_marker:
            validation.append(trade)
        else:
            test.append(trade)
    return train, validation, test


def _score(
    train: dict[str, object],
    validation: dict[str, object],
) -> float:
    if (
        int(train["trades"]) < 20
        or int(validation["trades"]) < 8
        or float(train["profit_factor"]) < 1.0
        or float(validation["profit_factor"]) < 1.0
    ):
        return -1e6 + int(train["trades"]) + int(validation["trades"])
    stable_pf = min(
        float(train["profit_factor"]),
        float(validation["profit_factor"]),
        3.0,
    )
    selection_trades = int(train["trades"]) + int(validation["trades"])
    selection_net = float(train["net_r"]) + float(validation["net_r"])
    frequency = min(selection_trades, 80) / 80.0
    net = selection_net / max(selection_trades, 1)
    drawdown_penalty = max(
        float(train["max_drawdown_pct"]),
        float(validation["max_drawdown_pct"]),
    ) / 15.0
    return stable_pf * 3.0 + frequency + net * 2.0 - drawdown_penalty


def _candidate_set() -> list[tuple[ArticleParams, float, float]]:
    baseline = ArticleParams(
        enable_fade=True,
        enable_distribution=True,
        trade_london=True,
        trade_new_york=False,
        max_trades_per_day=1,
        fade_rr=1.5,
        distribution_rr=1.5,
        sweep_min_fraction=0.02,
        sweep_max_fraction=0.60,
        breakout_fraction=0.03,
        retest_tolerance_fraction=0.04,
        stop_buffer_fraction=0.03,
        volume_factor=0.0,
        use_regime_filter=True,
    )
    candidates: list[tuple[ArticleParams, float, float]] = []
    management = (
        (0.30, 0.15),
        (0.50, 0.15),
        (0.75, 0.15),
        (1.00, 0.15),
        (0.50, 0.00),
    )

    def add(params: ArticleParams) -> None:
        for trigger, lock in management:
            candidates.append((params, trigger, lock))

    for rr in (1.0, 1.5, 2.0, 3.0):
        add(replace(baseline, fade_rr=rr, distribution_rr=rr))
    for enabled in ("fade", "distribution"):
        add(
            replace(
                baseline,
                enable_fade=enabled == "fade",
                enable_distribution=enabled == "distribution",
            )
        )
    for value in (0.0, 0.05, 0.10):
        add(replace(baseline, sweep_min_fraction=value))
    for value in (0.35, 0.50, 0.80):
        add(replace(baseline, sweep_max_fraction=value))
    for value in (0.00, 0.06, 0.10):
        add(replace(baseline, breakout_fraction=value))
    for value in (0.02, 0.06, 0.10):
        add(replace(baseline, retest_tolerance_fraction=value))
    for value in (0.02, 0.05, 0.08, 0.12):
        add(replace(baseline, stop_buffer_fraction=value))
    for value in (0.8, 1.0, 1.2):
        add(replace(baseline, volume_factor=value))
    unique: dict[str, tuple[ArticleParams, float, float]] = {}
    for params, trigger, lock in candidates:
        key = json.dumps(
            {
                "params": asdict(params),
                "lock_trigger_r": trigger,
                "lock_profit_r": lock,
            },
            sort_keys=True,
        )
        unique[key] = (params, trigger, lock)
    return list(unique.values())


def main() -> None:
    base_config = replace(load_config(), risk_pct=3.0)
    end = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = end - timedelta(days=365)
    train_end = start + (end - start) * 0.60
    validation_end = start + (end - start) * 0.80
    report_dir = base_config.root / "reports" / "article_research"
    report_dir.mkdir(parents=True, exist_ok=True)
    with connection():
        symbol = discover_symbols(("XAUUSD",))["XAUUSD"]
        point = float(symbol_metadata(symbol)["point"])
        frame = load_m1(
            symbol,
            start - timedelta(days=45),
            end,
            base_config.root / "data",
            False,
        )
    rows: list[dict[str, object]] = []
    candidate_set = _candidate_set()
    for idx, (params, trigger, lock) in enumerate(candidate_set, 1):
        config = replace(
            base_config,
            lock_trigger_r=trigger,
            lock_profit_r=lock,
        )
        trades = backtest_article_model(
            frame, symbol, point, config, params, start, end
        )
        train_trades, validation_trades, test_trades = _split_three(
            trades,
            train_end,
            validation_end,
        )
        full = metrics(symbol, trades, 1000.0, config.risk_pct)
        train = metrics(
            symbol, train_trades, 1000.0, config.risk_pct
        )
        validation = metrics(
            symbol, validation_trades, 1000.0, config.risk_pct
        )
        test = metrics(
            symbol, test_trades, 1000.0, config.risk_pct
        )
        rows.append(
            {
                "params": json.dumps(asdict(params), sort_keys=True),
                "lock_trigger_r": trigger,
                "lock_profit_r": lock,
                "full_trades": full["trades"],
                "full_wr": full["win_rate_pct"],
                "full_pf": full["profit_factor"],
                "full_net_r": full["net_r"],
                "full_return": full["return_pct"],
                "full_dd": full["max_drawdown_pct"],
                "train_trades": train["trades"],
                "train_pf": train["profit_factor"],
                "train_net_r": train["net_r"],
                "validation_trades": validation["trades"],
                "validation_pf": validation["profit_factor"],
                "validation_net_r": validation["net_r"],
                "test_trades": test["trades"],
                "test_wr": test["win_rate_pct"],
                "test_pf": test["profit_factor"],
                "test_net_r": test["net_r"],
                "test_return": test["return_pct"],
                "test_dd": test["max_drawdown_pct"],
                "score": _score(train, validation),
            }
        )
        if idx % 20 == 0:
            print(f"Robust search {idx}/{len(candidate_set)}", flush=True)
    result = pd.DataFrame(rows).sort_values("score", ascending=False)
    result.to_csv(report_dir / "robust_search.csv", index=False)
    winner = result.iloc[0].to_dict()
    (report_dir / "robust_winner.json").write_text(
        json.dumps(
            {
                "period": {
                    "start": start.isoformat(),
                    "train_end": train_end.isoformat(),
                    "validation_end": validation_end.isoformat(),
                    "end": end.isoformat(),
                },
                "risk_pct": base_config.risk_pct,
                "winner": winner,
                "selection_note": (
                    "Score used train and validation only. The final 20% "
                    "test segment was not used to select parameters."
                ),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(result.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
