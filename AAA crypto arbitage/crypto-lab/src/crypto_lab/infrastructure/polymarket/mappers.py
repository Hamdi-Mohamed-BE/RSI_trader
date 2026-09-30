"""Anti-corruption layer: translate raw Polymarket JSON into domain objects.

Polymarket encodes some list fields as JSON strings (``outcomes``, ``clobTokenIds``) and numbers as strings. All of
that is handled here so the domain never sees API quirks. Malformed rows are skipped, not guessed.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from crypto_lab.domain.polymarket.fees import NO_FEES, FeeSchedule
from crypto_lab.domain.polymarket.market import Event, Market, OutcomeToken
from crypto_lab.domain.polymarket.orderbook import OrderBook, PriceLevel
from crypto_lab.domain.polymarket.wallets import ClosedPosition, LeaderboardEntry, WalletTrade

logger = logging.getLogger(__name__)

# Fallback taker rates by fee type (Polymarket fee docs, checked 2026-09-29) when a market omits ``feeSchedule``.
FALLBACK_RATE_BY_FEE_TYPE: tuple[tuple[str, Decimal], ...] = (
    ("crypto", Decimal("0.07")),
    ("sports", Decimal("0.05")),
    ("economics", Decimal("0.05")),
    ("culture", Decimal("0.05")),
    ("weather", Decimal("0.05")),
    ("general", Decimal("0.05")),
    ("politics", Decimal("0.04")),
    ("finance", Decimal("0.04")),
    ("tech", Decimal("0.04")),
    ("mentions", Decimal("0.04")),
    ("geopolitic", Decimal(0)),
)
UNKNOWN_FEE_RATE = Decimal("0.07")  # most conservative published rate


def dec(value: Any, default: Decimal = Decimal(0)) -> Decimal:
    if value is None or value == "":
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), UTC)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(text[:10])
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.startswith("["):
        return [str(v) for v in json.loads(value)]
    return []


def fee_schedule(raw: Mapping[str, Any]) -> FeeSchedule:
    if not raw.get("feesEnabled"):
        return NO_FEES
    schedule = raw.get("feeSchedule")
    if isinstance(schedule, Mapping) and schedule.get("rate") is not None:
        return FeeSchedule(
            rate=dec(schedule["rate"]),
            exponent=int(schedule.get("exponent", 1)),
            taker_only=bool(schedule.get("takerOnly", True)),
        )
    fee_type = str(raw.get("feeType") or "").lower()
    rate = next((r for key, r in FALLBACK_RATE_BY_FEE_TYPE if key in fee_type), UNKNOWN_FEE_RATE)
    return FeeSchedule(rate=rate)


def market_from_gamma(raw: Mapping[str, Any], event_id: str = "") -> Market | None:
    token_ids, outcomes = _json_list(raw.get("clobTokenIds")), _json_list(raw.get("outcomes"))
    if len(token_ids) != 2 or len(outcomes) != 2 or not raw.get("conditionId"):
        return None
    return Market(
        condition_id=str(raw["conditionId"]),
        question=str(raw.get("question") or ""),
        slug=str(raw.get("slug") or ""),
        tokens=tuple(OutcomeToken(t, o) for t, o in zip(token_ids, outcomes, strict=True)),
        event_id=event_id,
        neg_risk=bool(raw.get("negRisk")),
        fees=fee_schedule(raw),
        fee_type=str(raw.get("feeType") or ""),
        tick_size=dec(raw.get("orderPriceMinTickSize"), Decimal("0.01")),
        min_order_size=dec(raw.get("orderMinSize"), Decimal(5)),
        end_date=parse_dt(raw.get("endDate")),
        volume_24h=dec(raw.get("volume24hr")),
        liquidity=dec(raw.get("liquidityNum") or raw.get("liquidity")),
        accepting_orders=bool(raw.get("acceptingOrders", True)),
        group_item_title=str(raw.get("groupItemTitle") or ""),
    )


def _tradeable(raw: Mapping[str, Any]) -> bool:
    return bool(raw.get("active")) and not raw.get("closed") and bool(raw.get("enableOrderBook"))


def event_from_gamma(raw: Mapping[str, Any]) -> Event | None:
    event_id = str(raw.get("id") or "")
    if not event_id:
        return None
    markets = tuple(
        m for m in (market_from_gamma(r, event_id) for r in raw.get("markets") or [] if _tradeable(r)) if m is not None
    )
    return Event(
        event_id=event_id,
        slug=str(raw.get("slug") or ""),
        title=str(raw.get("title") or ""),
        markets=markets,
        neg_risk=bool(raw.get("negRisk") or raw.get("enableNegRisk")),
        neg_risk_augmented=bool(raw.get("negRiskAugmented")),
        end_date=parse_dt(raw.get("endDate")),
        volume_24h=dec(raw.get("volume24hr")),
        tags=tuple(str(t.get("label")) for t in raw.get("tags") or [] if isinstance(t, Mapping) and t.get("label")),
    )


def book_from_clob(raw: Mapping[str, Any], received_ms: int = 0) -> OrderBook | None:
    token_id = str(raw.get("asset_id") or "")
    if not token_id:
        return None
    return OrderBook.build(
        token_id,
        _levels(raw, "bids"),
        _levels(raw, "asks"),
        int(dec(raw.get("timestamp"))),
        tick_size=dec(raw.get("tick_size"), Decimal("0.01")),
        min_order_size=dec(raw.get("min_order_size"), Decimal(5)),
        received_ms=received_ms,
    )


def _levels(raw: Mapping[str, Any], side: str) -> list[PriceLevel]:
    rows = raw.get(side) or []
    return [PriceLevel(dec(lv.get("price")), dec(lv.get("size"))) for lv in rows if isinstance(lv, Mapping)]


def leaderboard_entry(raw: Mapping[str, Any]) -> LeaderboardEntry | None:
    wallet = str(raw.get("proxyWallet") or "").lower()
    if not wallet:
        return None
    return LeaderboardEntry(
        rank=int(dec(raw.get("rank"))),
        wallet=wallet,
        user_name=str(raw.get("userName") or ""),
        pnl=dec(raw.get("pnl")),
        volume=dec(raw.get("vol")),
    )


def wallet_trade(raw: Mapping[str, Any]) -> WalletTrade | None:
    at = parse_dt(raw.get("timestamp"))
    if at is None or not raw.get("asset"):
        return None
    return WalletTrade(
        wallet=str(raw.get("proxyWallet") or "").lower(),
        tx_hash=str(raw.get("transactionHash") or ""),
        asset=str(raw["asset"]),
        condition_id=str(raw.get("conditionId") or ""),
        side=str(raw.get("side") or ""),
        size=dec(raw.get("size")),
        price=dec(raw.get("price")),
        outcome=str(raw.get("outcome") or ""),
        outcome_index=int(dec(raw.get("outcomeIndex"))),
        title=str(raw.get("title") or ""),
        slug=str(raw.get("slug") or ""),
        event_slug=str(raw.get("eventSlug") or ""),
        at=at,
    )


def closed_position(raw: Mapping[str, Any]) -> ClosedPosition | None:
    if not raw.get("asset"):
        return None
    return ClosedPosition(
        wallet=str(raw.get("proxyWallet") or "").lower(),
        asset=str(raw["asset"]),
        condition_id=str(raw.get("conditionId") or ""),
        avg_price=dec(raw.get("avgPrice")),
        total_bought=dec(raw.get("totalBought")),
        realized_pnl=dec(raw.get("realizedPnl")),
        cur_price=dec(raw.get("curPrice")),
        outcome=str(raw.get("outcome") or ""),
        title=str(raw.get("title") or ""),
        slug=str(raw.get("slug") or ""),
        event_slug=str(raw.get("eventSlug") or ""),
        closed_at=parse_dt(raw.get("timestamp")),
    )
