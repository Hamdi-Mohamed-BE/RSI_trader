from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path

import pandas as pd

from .backtest import _stats, run_backtest
from .config import load_config
from .mt5_adapter import connection, discover_symbol, load_or_fetch_m1, symbol_metadata


def _max_progression_risk(trades, base: float, multiplier: float) -> float:
    by_day: dict[str, float] = {}
    for trade in trades:
        by_day[trade.ny_date] = by_day.get(trade.ny_date, 0.0) + (
            trade.r_multiple * trade.risk_share
        )
    streak = 0
    highest = base
    for key in sorted(by_day):
        highest = max(highest, base * multiplier**streak)
        if by_day[key] < -1e-9:
            streak += 1
        elif by_day[key] > 1e-9:
            streak = 0
    return highest


def main() -> int:
    project = Path.cwd().resolve()
    config = load_config(project)
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=config.history_days)
    with connection():
        symbol = discover_symbol(config.canonical_symbol)
        metadata = symbol_metadata(symbol)
        frame = load_or_fetch_m1(symbol, start, now, config.cache_dir, refresh=True)

    output = config.reports_dir / "risk_progression_1_7r"
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for trailing in (False, True):
        scenario_config = config.with_parameters(
            risk_pct=0.5,
            target_rr=1.7,
            max_target_rr=1.7,
            trailing_enabled=trailing,
            risk_progression_enabled=False,
        )
        result = run_backtest(
            frame,
            symbol,
            scenario_config,
            point=float(metadata["point"]),
            initial_balance=10_000.0,
        )
        for progression in (False, True):
            stats = _stats(
                list(result.trades),
                0.5,
                10_000.0,
                progression_enabled=progression,
                progression_multiplier=1.6,
                progression_max_pct=None,
            )
            row = asdict(stats)
            row.update(
                {
                    "scenario": (
                        f"{'progression' if progression else 'flat'}_"
                        f"{'trailing' if trailing else 'fixed'}"
                    ),
                    "base_risk_pct": 0.5,
                    "risk_multiplier": 1.6 if progression else 1.0,
                    "max_risk_used_pct": (
                        _max_progression_risk(result.trades, 0.5, 1.6)
                        if progression
                        else 0.5
                    ),
                    "target_cap_r": 1.7,
                    "trailing_enabled": trailing,
                    "start": result.start.isoformat(),
                    "end": result.end.isoformat(),
                    "symbol": symbol,
                }
            )
            if math.isinf(float(row["profit_factor"])):
                row["profit_factor"] = "inf"
            rows.append(row)

    table = pd.DataFrame(rows)
    table.to_csv(output / "scenarios.csv", index=False)
    (output / "scenarios.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    lines = [
        "# US100 risk progression / 1.7R study",
        "",
        f"Data: `{rows[0]['start']}` to `{rows[0]['end']}` on `{symbol}`.",
        "Base risk 0.5%; progression is uncapped 1.6^loss-streak for research.",
        "",
        "| Scenario | Ideas | Win rate | PF | Ending | Max DD | Max risk used |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        pf = row["profit_factor"]
        pf_text = str(pf) if isinstance(pf, str) else f"{float(pf):.2f}"
        lines.append(
            f"| {row['scenario']} | {row['trades']} | {row['win_rate']:.2f}% | "
            f"{pf_text} | ${row['ending_balance']:.2f} | "
            f"{row['max_drawdown_pct']:.2f}% | {row['max_risk_used_pct']:.2f}% |"
        )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(table[["scenario", "trades", "win_rate", "profit_factor", "ending_balance", "max_drawdown_pct", "max_risk_used_pct"]].to_string(index=False))
    print(f"\nSaved {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
