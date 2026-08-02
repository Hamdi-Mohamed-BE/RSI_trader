from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pandas as pd

from .article_engine import backtest_article_model, params_from_config
from .config import load_config
from .engine import metrics
from .mt5_data import connection, discover_symbols, load_m1, symbol_metadata


UTC = timezone.utc


def run(days: int = 365, refresh: bool = False) -> None:
    base = replace(
        load_config(),
        risk_pct=0.5,
        max_target_rr=1.7,
        article_fade_rr=1.7,
        article_distribution_rr=1.7,
    )
    end = datetime.now(UTC).replace(second=0, microsecond=0)
    start = end - timedelta(days=days)
    report_dir = base.root / "reports" / "risk_progression_1_7r"
    report_dir.mkdir(parents=True, exist_ok=True)

    with connection() as account:
        symbol = discover_symbols(("XAUUSD",))["XAUUSD"]
        point = float(symbol_metadata(symbol)["point"])
        frame = load_m1(
            symbol,
            start - timedelta(days=70),
            end,
            base.root / "data" / "risk_study",
            refresh,
        )
        print(
            f"Account {account.login} {account.server} | {symbol} | "
            f"{start.isoformat()} to {end.isoformat()}",
            flush=True,
        )

    trade_sets: dict[str, list] = {}
    for trailing in (False, True):
        config = replace(base, trailing_enabled=trailing)
        trades = backtest_article_model(
            frame,
            symbol,
            point,
            config,
            params_from_config(config),
            start,
            end,
        )
        trade_sets["trailing" if trailing else "fixed"] = trades

    rows: list[dict[str, object]] = []
    for progression in (False, True):
        for management in ("fixed", "trailing"):
            trades = trade_sets[management]
            row = metrics(
                symbol,
                trades,
                base.starting_balance,
                base.risk_pct,
                progression_enabled=progression,
                progression_multiplier=1.6,
                progression_max_pct=None,
            )
            row["scenario"] = (
                ("progression" if progression else "flat")
                + "_"
                + management
            )
            rows.append(row)
            pd.DataFrame([trade.to_dict() for trade in trades]).to_csv(
                report_dir / f"{row['scenario']}_trades.csv", index=False
            )

    summary = pd.DataFrame(rows)
    summary.to_csv(report_dir / "scenarios.csv", index=False)
    (report_dir / "summary.json").write_text(
        json.dumps(
            {
                "symbol": symbol,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "base_risk_pct": 0.5,
                "loss_multiplier": 1.6,
                "research_progression_cap": None,
                "max_target_r": 1.7,
                "trailing": {"start_r": 1.0, "distance_r": 0.5},
                "scenarios": rows,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    columns = [
        "scenario",
        "trades",
        "win_rate_pct",
        "profit_factor",
        "ending_balance",
        "return_pct",
        "max_drawdown_pct",
        "max_risk_used_pct",
    ]
    display = summary[columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "|" + "|".join("---" for _ in columns) + "|"
    body = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in display.itertuples(index=False, name=None)
    ]
    table = "\n".join([header, separator, *body])
    (report_dir / "REPORT.md").write_text(
        "# AMD risk progression / 1.7R study\n\n"
        f"Period: {start.isoformat()} to {end.isoformat()}  \n"
        f"Broker symbol: `{symbol}`  \n"
        "Starting balance: $1,000; base risk: 0.5%; progression: 1.6x "
        "after loss and reset after win; research progression uncapped.\n\n"
        + table
        + "\n\nTrailing starts at +1R, follows by 0.5R, and retains the 1.7R hard TP.\n",
        encoding="utf-8",
    )
    print(table)
    print(f"Saved: {report_dir}")


if __name__ == "__main__":
    run()
