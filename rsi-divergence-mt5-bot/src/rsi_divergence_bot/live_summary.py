from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from .mt5_client import MT5Client


SUMMARY_GROUPS = (
    ("rsi_bot", "RSI bot"),
    ("signal_bot", "Telegram signal bot"),
    ("other", "Other"),
)


def _parse_iso(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _net_pnl(deal: dict[str, Any]) -> float:
    return round(
        float(deal.get("profit", 0.0) or 0.0)
        + float(deal.get("commission", 0.0) or 0.0)
        + float(deal.get("swap", 0.0) or 0.0)
        + float(deal.get("fee", 0.0) or 0.0),
        2,
    )


def _comment_bucket(comment: str | None) -> str | None:
    value = str(comment or "").lower()
    if "rsi" in value:
        return "rsi_bot"
    if "signal" in value:
        return "signal_bot"
    return None


def _empty_bucket(key: str, label: str) -> dict:
    return {
        "key": key,
        "label": label,
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "breakeven": 0,
        "win_amount": 0.0,
        "loss_amount": 0.0,
        "net": 0.0,
        "win_rate": 0.0,
    }


def build_live_summary(client: MT5Client, start: datetime | str, end: datetime | str) -> dict:
    start_utc = _parse_iso(start)
    end_utc = _parse_iso(end)
    if start_utc >= end_utc:
        raise ValueError("Start must be before end")

    lookup_start = start_utc - timedelta(days=14)
    lookup_deals = client.deals_range(lookup_start, end_utc)
    bucket_by_position: dict[int, str] = {}

    for deal in lookup_deals:
        if deal.get("side") not in {"buy", "sell"}:
            continue
        position_id = int(deal.get("position_id") or deal.get("order") or deal.get("ticket") or 0)
        bucket = _comment_bucket(deal.get("comment"))
        if position_id and bucket:
            bucket_by_position[position_id] = bucket

    period_deals = [
        deal
        for deal in lookup_deals
        if start_utc <= _parse_iso(deal["time"]) <= end_utc and deal.get("side") in {"buy", "sell"}
    ]
    grouped: dict[int, dict] = {}
    for deal in period_deals:
        position_id = int(deal.get("position_id") or deal.get("order") or deal.get("ticket") or 0)
        key = position_id or int(deal.get("ticket") or 0)
        bucket = _comment_bucket(deal.get("comment")) or bucket_by_position.get(position_id, "other")
        row = grouped.setdefault(
            key,
            {
                "position_id": key,
                "bucket": bucket,
                "symbol": deal.get("symbol"),
                "side": deal.get("side"),
                "volume": 0.0,
                "entry_price": None,
                "exit_price": None,
                "opened_at": None,
                "closed_at": None,
                "comment": deal.get("comment") or "",
                "pnl": 0.0,
                "deal_count": 0,
            },
        )
        row["bucket"] = bucket if row["bucket"] == "other" else row["bucket"]
        row["symbol"] = row["symbol"] or deal.get("symbol")
        row["side"] = row["side"] or deal.get("side")
        row["volume"] = max(float(row["volume"] or 0.0), float(deal.get("volume") or 0.0))
        row["pnl"] = round(float(row["pnl"]) + _net_pnl(deal), 2)
        row["deal_count"] += 1

        deal_time = deal["time"]
        if row["opened_at"] is None or deal_time < row["opened_at"]:
            row["opened_at"] = deal_time
            row["entry_price"] = deal.get("price")
        if row["closed_at"] is None or deal_time > row["closed_at"]:
            row["closed_at"] = deal_time
            row["exit_price"] = deal.get("price")
        if deal.get("comment"):
            row["comment"] = deal.get("comment")

    summary = {key: _empty_bucket(key, label) for key, label in SUMMARY_GROUPS}
    trades = sorted(grouped.values(), key=lambda item: item["closed_at"] or item["opened_at"] or "", reverse=True)

    for trade in trades:
        bucket = trade.get("bucket") or "other"
        stats = summary.setdefault(bucket, _empty_bucket(bucket, bucket.replace("_", " ").title()))
        pnl = round(float(trade["pnl"]), 2)
        stats["trades"] += 1
        stats["net"] = round(float(stats["net"]) + pnl, 2)
        if pnl > 0:
            stats["wins"] += 1
            stats["win_amount"] = round(float(stats["win_amount"]) + pnl, 2)
        elif pnl < 0:
            stats["losses"] += 1
            stats["loss_amount"] = round(float(stats["loss_amount"]) + pnl, 2)
        else:
            stats["breakeven"] += 1

    for stats in summary.values():
        decided = int(stats["wins"]) + int(stats["losses"])
        stats["win_rate"] = round((int(stats["wins"]) / decided * 100) if decided else 0.0, 2)

    totals = _empty_bucket("overall", "Overall")
    for stats in summary.values():
        totals["trades"] += int(stats["trades"])
        totals["wins"] += int(stats["wins"])
        totals["losses"] += int(stats["losses"])
        totals["breakeven"] += int(stats["breakeven"])
        totals["win_amount"] = round(float(totals["win_amount"]) + float(stats["win_amount"]), 2)
        totals["loss_amount"] = round(float(totals["loss_amount"]) + float(stats["loss_amount"]), 2)
        totals["net"] = round(float(totals["net"]) + float(stats["net"]), 2)
    decided = int(totals["wins"]) + int(totals["losses"])
    totals["win_rate"] = round((int(totals["wins"]) / decided * 100) if decided else 0.0, 2)

    by_symbol: dict[str, dict] = defaultdict(lambda: {"trades": 0, "net": 0.0, "wins": 0, "losses": 0})
    for trade in trades:
        symbol = str(trade.get("symbol") or "Unknown")
        pnl = float(trade.get("pnl", 0.0) or 0.0)
        by_symbol[symbol]["trades"] += 1
        by_symbol[symbol]["net"] = round(float(by_symbol[symbol]["net"]) + pnl, 2)
        if pnl > 0:
            by_symbol[symbol]["wins"] += 1
        elif pnl < 0:
            by_symbol[symbol]["losses"] += 1

    return {
        "start": start_utc.isoformat(),
        "end": end_utc.isoformat(),
        "summary": list(summary.values()),
        "overall": totals,
        "by_symbol": [
            {"symbol": symbol, **stats}
            for symbol, stats in sorted(by_symbol.items(), key=lambda item: abs(float(item[1]["net"])), reverse=True)
        ],
        "trades": trades[:250],
    }
