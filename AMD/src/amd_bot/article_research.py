from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import itertools
import json
from pathlib import Path

import pandas as pd

from .article_engine import ArticleParams, backtest_article_model
from .config import load_config
from .engine import Trade, metrics
from .mt5_data import connection, discover_symbols, load_m1, symbol_metadata


UTC = timezone.utc


def _score(row: dict[str, object], minimum_trades: int) -> float:
    trades = int(row["trades"])
    if trades < minimum_trades:
        return -1e9 + trades
    pf = min(float(row["profit_factor"]), 5.0)
    net = float(row["net_r"])
    dd = max(float(row["max_drawdown_pct"]), 1.0)
    return pf * 2.0 + net / max(trades, 1) * 3.0 - dd / 20.0


def _monthly(trades: list[Trade], risk_pct: float) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    groups: dict[str, list[Trade]] = {}
    for trade in trades:
        month = trade.session_date[:7]
        groups.setdefault(month, []).append(trade)
    for month, values in sorted(groups.items()):
        row = metrics(month, values, 1000.0, risk_pct)
        row["month"] = month
        rows.append(row)
    return pd.DataFrame(rows)


def _before(trades: list[Trade], boundary: datetime) -> list[Trade]:
    return [
        trade
        for trade in trades
        if pd.Timestamp(trade.entry_time) < pd.Timestamp(boundary)
    ]


def _from(trades: list[Trade], boundary: datetime) -> list[Trade]:
    return [
        trade
        for trade in trades
        if pd.Timestamp(trade.entry_time) >= pd.Timestamp(boundary)
    ]


def run(days: int = 365, refresh: bool = False) -> None:
    config = load_config()
    config = replace(config, risk_pct=1.0)
    end = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = end - timedelta(days=days)
    split1 = start + (end - start) * 0.60
    split2 = start + (end - start) * 0.80
    report_dir = config.root / "reports" / "article_research"
    report_dir.mkdir(parents=True, exist_ok=True)
    with connection() as account:
        symbol = discover_symbols(("XAUUSD",))["XAUUSD"]
        point = float(symbol_metadata(symbol)["point"])
        frame = load_m1(
            symbol,
            start - timedelta(days=45),
            end,
            config.root / "data",
            refresh,
        )
        print(
            f"Account {account.login} {account.server} | {symbol} | "
            f"{start.date()} to {end.date()}",
            flush=True,
        )

    coarse: list[ArticleParams] = []
    for setup, sessions, rr, regime in itertools.product(
        ("fade", "distribution", "both"),
        ("london", "new_york", "both"),
        (1.5, 2.0, 3.0),
        (False, True),
    ):
        coarse.append(
            ArticleParams(
                enable_fade=setup in {"fade", "both"},
                enable_distribution=setup in {"distribution", "both"},
                trade_london=sessions in {"london", "both"},
                trade_new_york=sessions in {"new_york", "both"},
                fade_rr=rr,
                distribution_rr=rr,
                use_regime_filter=regime,
            )
        )
    coarse_rows: list[dict[str, object]] = []
    for idx, params in enumerate(coarse, 1):
        trades = backtest_article_model(
            frame, symbol, point, config, params, start, split1
        )
        row = metrics(symbol, trades, 1000.0, config.risk_pct)
        row["params"] = json.dumps(asdict(params), sort_keys=True)
        row["score"] = _score(row, minimum_trades=18)
        coarse_rows.append(row)
        if idx % 18 == 0:
            print(f"Coarse search {idx}/{len(coarse)}", flush=True)
    coarse_df = pd.DataFrame(coarse_rows).sort_values("score", ascending=False)
    coarse_df.to_csv(report_dir / "coarse_search.csv", index=False)
    seeds = [
        ArticleParams(**json.loads(value))
        for value in coarse_df.head(2)["params"]
    ]

    refined: list[ArticleParams] = []
    seen: set[str] = set()
    for seed in seeds:
        for (
            sweep_min,
            sweep_max,
            breakout,
            retest,
            stop_buffer,
            volume_factor,
            lock_trigger,
        ) in itertools.product(
            (0.00, 0.03),
            (0.50,),
            (0.00, 0.03, 0.06),
            (0.03, 0.06),
            (0.03, 0.07),
            (0.0, 1.0),
            (0.5,),
        ):
            params = replace(
                seed,
                sweep_min_fraction=sweep_min,
                sweep_max_fraction=sweep_max,
                breakout_fraction=breakout,
                retest_tolerance_fraction=retest,
                stop_buffer_fraction=stop_buffer,
                volume_factor=volume_factor,
            )
            key = json.dumps(asdict(params), sort_keys=True)
            if key not in seen:
                seen.add(key)
                refined.append(params)
    refined_rows: list[dict[str, object]] = []
    research_config = replace(config, lock_trigger_r=0.5, lock_profit_r=0.0)
    for idx, params in enumerate(refined, 1):
        selection_trades = backtest_article_model(
            frame, symbol, point, research_config, params, start, split2
        )
        train_trades = _before(selection_trades, split1)
        valid_trades = _from(selection_trades, split1)
        train = metrics(symbol, train_trades, 1000.0, config.risk_pct)
        valid = metrics(symbol, valid_trades, 1000.0, config.risk_pct)
        row = {
            "params": json.dumps(asdict(params), sort_keys=True),
            "train_trades": train["trades"],
            "train_wr": train["win_rate_pct"],
            "train_pf": train["profit_factor"],
            "train_net_r": train["net_r"],
            "train_dd": train["max_drawdown_pct"],
            "valid_trades": valid["trades"],
            "valid_wr": valid["win_rate_pct"],
            "valid_pf": valid["profit_factor"],
            "valid_net_r": valid["net_r"],
            "valid_dd": valid["max_drawdown_pct"],
            "score": (
                _score(train, minimum_trades=18)
                + _score(valid, minimum_trades=5) * 2.0
            ),
        }
        refined_rows.append(row)
        if idx % 20 == 0:
            print(
                f"Refined search {idx}/{len(refined)}",
                flush=True,
            )
    refined_df = pd.DataFrame(refined_rows).sort_values(
        "score", ascending=False
    )
    refined_df.to_csv(report_dir / "refined_search.csv", index=False)

    final_rows: list[dict[str, object]] = []
    for params_json in refined_df.head(20)["params"]:
        params = ArticleParams(**json.loads(params_json))
        train_trades = backtest_article_model(
            frame, symbol, point, research_config, params, start, split2
        )
        test_trades = backtest_article_model(
            frame, symbol, point, research_config, params, split2, end
        )
        train = metrics(symbol, train_trades, 1000.0, config.risk_pct)
        test = metrics(symbol, test_trades, 1000.0, config.risk_pct)
        final_rows.append(
            {
                "params": params_json,
                "train_trades": train["trades"],
                "train_wr": train["win_rate_pct"],
                "train_pf": train["profit_factor"],
                "train_net_r": train["net_r"],
                "train_dd": train["max_drawdown_pct"],
                "test_trades": test["trades"],
                "test_wr": test["win_rate_pct"],
                "test_pf": test["profit_factor"],
                "test_net_r": test["net_r"],
                "test_dd": test["max_drawdown_pct"],
                "score": _score(test, minimum_trades=5),
            }
        )
    final_df = pd.DataFrame(final_rows).sort_values("score", ascending=False)
    final_df.to_csv(report_dir / "holdout_results.csv", index=False)
    winner = ArticleParams(**json.loads(final_df.iloc[0]["params"]))
    full_trades = backtest_article_model(
        frame, symbol, point, research_config, winner, start, end
    )
    full = metrics(symbol, full_trades, 1000.0, config.risk_pct)
    pd.DataFrame([trade.to_dict() for trade in full_trades]).to_csv(
        report_dir / "winner_trades.csv", index=False
    )
    _monthly(full_trades, config.risk_pct).to_csv(
        report_dir / "winner_monthly.csv", index=False
    )
    result = {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "split": {
            "selection_end": split2.isoformat(),
            "holdout_start": split2.isoformat(),
        },
        "symbol": symbol,
        "risk_pct_for_comparison": config.risk_pct,
        "winner": asdict(winner),
        "full_sample": full,
        "holdout": final_df.iloc[0].to_dict(),
    }
    (report_dir / "winner.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    run()
