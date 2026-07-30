from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json

import pandas as pd

from .article_engine import ArticleParams, backtest_article_model
from .config import load_config
from .engine import metrics
from .mt5_data import connection, discover_symbols, load_m1, symbol_metadata


UTC = timezone.utc


def main() -> None:
    config = load_config()
    end = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    start = end - timedelta(days=365)
    split = start + (end - start) * 0.80
    report_dir = config.root / "reports" / "article_research"
    candidates = pd.read_csv(report_dir / "coarse_search.csv").head(15)
    with connection():
        symbol = discover_symbols(("XAUUSD",))["XAUUSD"]
        point = float(symbol_metadata(symbol)["point"])
        frame = load_m1(
            symbol,
            start - timedelta(days=45),
            end,
            config.root / "data",
            False,
        )
    rows: list[dict[str, object]] = []
    for idx, params_json in enumerate(candidates["params"], 1):
        params = ArticleParams(**json.loads(params_json))
        trades = backtest_article_model(
            frame, symbol, point, config, params, start, end
        )
        selection = [
            trade
            for trade in trades
            if pd.Timestamp(trade.entry_time) < pd.Timestamp(split)
        ]
        holdout = [
            trade
            for trade in trades
            if pd.Timestamp(trade.entry_time) >= pd.Timestamp(split)
        ]
        full_metrics = metrics(
            symbol, trades, 1000.0, config.risk_pct
        )
        selection_metrics = metrics(
            symbol, selection, 1000.0, config.risk_pct
        )
        holdout_metrics = metrics(
            symbol, holdout, 1000.0, config.risk_pct
        )
        rows.append(
            {
                "params": json.dumps(asdict(params), sort_keys=True),
                "full_trades": full_metrics["trades"],
                "full_wr": full_metrics["win_rate_pct"],
                "full_pf": full_metrics["profit_factor"],
                "full_net_r": full_metrics["net_r"],
                "full_dd": full_metrics["max_drawdown_pct"],
                "selection_trades": selection_metrics["trades"],
                "selection_pf": selection_metrics["profit_factor"],
                "selection_net_r": selection_metrics["net_r"],
                "holdout_trades": holdout_metrics["trades"],
                "holdout_wr": holdout_metrics["win_rate_pct"],
                "holdout_pf": holdout_metrics["profit_factor"],
                "holdout_net_r": holdout_metrics["net_r"],
                "holdout_dd": holdout_metrics["max_drawdown_pct"],
            }
        )
        print(f"Validated {idx}/{len(candidates)}", flush=True)
    result = pd.DataFrame(rows).sort_values(
        ["holdout_pf", "holdout_net_r"], ascending=False
    )
    result.to_csv(report_dir / "coarse_holdout_actual_management.csv", index=False)
    print(result.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
