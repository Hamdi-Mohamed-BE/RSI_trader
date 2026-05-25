from __future__ import annotations

import argparse
import csv
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rsi_divergence_bot.backtest import optimize_symbol_timeframes
from rsi_divergence_bot.config import load_config
from rsi_divergence_bot.mt5_client import MT5Client
from rsi_divergence_bot.timeframes import SUPPORTED_TIMEFRAMES


def _utc_now_floor() -> datetime:
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)


def _parse_dt(value: str | None, default: datetime) -> datetime:
    if not value:
        return default
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fmt_money(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"${float(value):,.2f}"


def _fmt_pct(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}%"


def _candidate_label(candidate: dict) -> str:
    if candidate.get("error"):
        return "error"
    return (
        f"{_fmt_money(candidate.get('pnl', 0))} | "
        f"{int(candidate.get('trades', 0))}T/{int(candidate.get('position_legs', 0))}L | "
        f"{_fmt_pct(candidate.get('win_rate', 0))}"
    )


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def write_reports(result: dict, output_dir: Path) -> tuple[Path, Path]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    csv_path = output_dir / f"timeframe-performance-{timestamp}.csv"
    md_path = output_dir / f"timeframe-performance-{timestamp}.md"

    long_rows: list[dict] = []
    best_rows: list[list[str]] = []
    full_rows: list[list[str]] = []
    headers = ["symbol", "current", "best", *result["candidate_timeframes"]]

    for symbol_row in result["symbols"]:
        candidates = symbol_row["candidates"]
        best = symbol_row["best"] or {}
        viable = [item for item in candidates if not item.get("error") and item.get("trades", 0) > 0]
        top = sorted(
            viable,
            key=lambda item: (
                float(item.get("pnl", 0)),
                float(item.get("win_rate", 0)),
                int(item.get("trades", 0)),
                -float(item.get("max_drawdown", 0)),
            ),
            reverse=True,
        )[:3]
        top_text = "; ".join(
            f"{item['timeframe']} {_fmt_money(item.get('pnl', 0))} "
            f"{int(item.get('trades', 0))}T/{_fmt_pct(item.get('win_rate', 0))}"
            for item in top
        )
        best_rows.append(
            [
                symbol_row["symbol"],
                symbol_row["current_timeframe"],
                symbol_row["best_timeframe"],
                _fmt_money(best.get("pnl", 0)),
                str(int(best.get("trades", 0) or 0)),
                str(int(best.get("position_legs", 0) or 0)),
                _fmt_pct(best.get("win_rate", 0)),
                _fmt_money(best.get("max_drawdown", 0)),
                top_text or "no valid trades",
            ]
        )

        by_tf = {item["timeframe"]: item for item in candidates}
        full_rows.append(
            [
                symbol_row["symbol"],
                symbol_row["current_timeframe"],
                symbol_row["best_timeframe"],
                *[_candidate_label(by_tf.get(tf, {"error": "missing"})) for tf in result["candidate_timeframes"]],
            ]
        )

        for item in candidates:
            long_rows.append(
                {
                    "symbol": symbol_row["symbol"],
                    "name": symbol_row["name"],
                    "current_timeframe": symbol_row["current_timeframe"],
                    "best_timeframe": symbol_row["best_timeframe"],
                    "timeframe": item["timeframe"],
                    "bars": item.get("bars", 0),
                    "raw_signals": item.get("raw_signals", 0),
                    "trades": item.get("trades", 0),
                    "position_legs": item.get("position_legs", 0),
                    "wins": item.get("wins", 0),
                    "losses": item.get("losses", 0),
                    "win_rate": item.get("win_rate", 0),
                    "pnl": item.get("pnl", 0),
                    "max_drawdown": item.get("max_drawdown", 0),
                    "error": item.get("error") or "",
                }
            )

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(long_rows[0].keys()) if long_rows else [])
        writer.writeheader()
        writer.writerows(long_rows)

    md_parts = [
        "# Timeframe Performance",
        "",
        f"Start: `{result['start']}`",
        f"End: `{result['end']}`",
        f"Starting balance: `{_fmt_money(result['starting_balance'])}`",
        "",
        "Cell format in the full table: `PnL | closed trades / position legs | win rate`.",
        "",
        "## Best Timeframe Per Symbol",
        "",
        _markdown_table(
            ["Symbol", "Current TF", "Best TF", "PnL", "Trades", "Legs", "Win rate", "Max DD", "Top 3"],
            best_rows,
        ),
        "",
        "## Full Matrix",
        "",
        _markdown_table(headers, full_rows),
        "",
    ]
    md_path.write_text("\n".join(md_parts), encoding="utf-8")
    return csv_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export per-symbol timeframe performance using the app optimizer.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--balance", type=float, default=1000.0)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    project_dir = config_path.parent
    output_dir = project_dir / "runtime"
    output_dir.mkdir(parents=True, exist_ok=True)

    end = _parse_dt(args.end, _utc_now_floor())
    start = _parse_dt(args.start, end - timedelta(days=args.days))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logger = logging.getLogger("timeframe-report")

    config = load_config(config_path)
    client = MT5Client(config.mt5)
    try:
        logger.info(
            "Running timeframe performance report: symbols=%s timeframes=%s start=%s end=%s",
            len(config.enabled_symbols),
            len(SUPPORTED_TIMEFRAMES),
            start.isoformat(),
            end.isoformat(),
        )
        result = optimize_symbol_timeframes(
            client,
            config,
            start,
            end,
            starting_balance=args.balance,
            candidate_timeframes=list(SUPPORTED_TIMEFRAMES),
            logger=logger,
        )
        csv_path, md_path = write_reports(result, output_dir)
        logger.info("CSV report: %s", csv_path)
        logger.info("Markdown report: %s", md_path)
        print(str(md_path))
        print(str(csv_path))
    finally:
        client.shutdown(force=True)


if __name__ == "__main__":
    main()
