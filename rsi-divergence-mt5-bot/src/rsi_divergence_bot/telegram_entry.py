from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

OrderKind = Literal["market", "buy_limit", "sell_limit", "buy_stop", "sell_stop"]


@dataclass(frozen=True)
class EntryZone:
    low: float
    high: float

    @classmethod
    def from_prices(cls, first: float, second: float) -> EntryZone:
        a = float(first)
        b = _expand_entry_shorthand(a, float(second))
        low, high = sorted((a, b))
        return cls(low=low, high=high)

    @classmethod
    def single(cls, price: float) -> EntryZone:
        value = float(price)
        return cls(low=value, high=value)


@dataclass(frozen=True)
class TelegramExecutionDecision:
    order_kind: OrderKind
    side: str
    entry_price: float
    current_bid: float
    current_ask: float
    zone_low: float | None
    zone_high: float | None
    reason: str


def _expand_entry_shorthand(leading: float, trailing: float) -> float:
    """Expand shorthand like 4540/35 -> 4535; keep full pairs like 4394/4397."""
    if trailing >= leading * 0.5:
        return trailing
    leading_text = f"{leading:g}"
    trailing_text = f"{int(trailing):g}"
    if len(trailing_text) < len(leading_text):
        return float(leading_text[: -len(trailing_text)] + trailing_text)
    return trailing


_ENTRY_RANGE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*[_/\-–—]\s*(\d+(?:\.\d+)?)",
)


def extract_entry_zone_from_line(line: str) -> EntryZone | None:
    match = _ENTRY_RANGE_RE.search(line)
    if match:
        return EntryZone.from_prices(float(match.group(1)), float(match.group(2)))
    if not re.search(r"\b(BUY|SELL)\b", line, re.IGNORECASE):
        return None
    numbers = [float(item) for item in re.findall(r"(\d+(?:\.\d+)?)", line)]
    if len(numbers) >= 2:
        return EntryZone.from_prices(numbers[-2], numbers[-1])
    if len(numbers) == 1:
        return EntryZone.single(numbers[0])
    return None


def extract_entry_zone_from_text(text: str) -> EntryZone | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()
        if not re.search(r"\b(BUY|SELL)\b", upper):
            continue
        zone = extract_entry_zone_from_line(line)
        if zone is not None:
            return zone
    return None


def resolve_telegram_execution(
    side: str,
    *,
    bid: float,
    ask: float,
    zone: EntryZone | None = None,
    explicit_entry: float | None = None,
    pending_action: str | None = None,
    force_market: bool = False,
) -> TelegramExecutionDecision:
    side = side.lower()
    if side not in {"buy", "sell"}:
        raise ValueError(f"unsupported side {side}")

    zone_low = zone.low if zone else None
    zone_high = zone.high if zone else None

    if force_market:
        live = ask if side == "buy" else bid
        zone_note = ""
        if zone is not None:
            zone_note = f" (entry zone {zone.low:.5f}-{zone.high:.5f} ignored)"
        return TelegramExecutionDecision(
            order_kind="market",
            side=side,
            entry_price=live,
            current_bid=bid,
            current_ask=ask,
            zone_low=zone_low,
            zone_high=zone_high,
            reason=(
                f"Signal under max age — market {side} at live "
                f"{'ask' if side == 'buy' else 'bid'} {live:.5f}{zone_note}"
            ),
        )

    if pending_action and pending_action not in {"buy", "sell", "none"}:
        entry = float(explicit_entry or 0.0)
        if entry <= 0 and zone is not None:
            entry = zone.high if side == "buy" else zone.low
        if entry <= 0:
            raise ValueError(f"{pending_action} requires an entry price")
        return TelegramExecutionDecision(
            order_kind=pending_action,  # type: ignore[arg-type]
            side=side,
            entry_price=entry,
            current_bid=bid,
            current_ask=ask,
            zone_low=zone_low,
            zone_high=zone_high,
            reason=f"Signal requests {pending_action} at {entry:.5f}",
        )

    if zone is None and explicit_entry is not None:
        zone = EntryZone.single(explicit_entry)
        zone_low = zone.low
        zone_high = zone.high

    if zone is None:
        live = ask if side == "buy" else bid
        return TelegramExecutionDecision(
            order_kind="market",
            side=side,
            entry_price=live,
            current_bid=bid,
            current_ask=ask,
            zone_low=None,
            zone_high=None,
            reason=f"No entry zone — market {side} at live {'ask' if side == 'buy' else 'bid'} {live:.5f}",
        )

    if side == "buy":
        if zone.low <= ask <= zone.high:
            return TelegramExecutionDecision(
                order_kind="market",
                side="buy",
                entry_price=ask,
                current_bid=bid,
                current_ask=ask,
                zone_low=zone_low,
                zone_high=zone_high,
                reason=(
                    f"Live ask {ask:.5f} is inside entry zone {zone.low:.5f}-{zone.high:.5f} — market buy"
                ),
            )
        if ask > zone.high:
            return TelegramExecutionDecision(
                order_kind="buy_limit",
                side="buy",
                entry_price=zone.high,
                current_bid=bid,
                current_ask=ask,
                zone_low=zone_low,
                zone_high=zone_high,
                reason=(
                    f"Live ask {ask:.5f} is above entry zone top {zone.high:.5f} "
                    f"— buy limit pre-order at {zone.high:.5f}"
                ),
            )
        return TelegramExecutionDecision(
            order_kind="market",
            side="buy",
            entry_price=ask,
            current_bid=bid,
            current_ask=ask,
            zone_low=zone_low,
            zone_high=zone_high,
            reason=(
                f"Live ask {ask:.5f} is below entry zone {zone.low:.5f}-{zone.high:.5f} "
                f"— market buy at better price"
            ),
        )

    if zone.low <= bid <= zone.high:
        return TelegramExecutionDecision(
            order_kind="market",
            side="sell",
            entry_price=bid,
            current_bid=bid,
            current_ask=ask,
            zone_low=zone_low,
            zone_high=zone_high,
            reason=(
                f"Live bid {bid:.5f} is inside entry zone {zone.low:.5f}-{zone.high:.5f} — market sell"
            ),
        )
    if bid < zone.low:
        return TelegramExecutionDecision(
            order_kind="sell_limit",
            side="sell",
            entry_price=zone.low,
            current_bid=bid,
            current_ask=ask,
            zone_low=zone_low,
            zone_high=zone_high,
            reason=(
                f"Live bid {bid:.5f} is below entry zone bottom {zone.low:.5f} "
                f"— sell limit pre-order at {zone.low:.5f}"
            ),
        )
    return TelegramExecutionDecision(
        order_kind="market",
        side="sell",
        entry_price=bid,
        current_bid=bid,
        current_ask=ask,
        zone_low=zone_low,
        zone_high=zone_high,
        reason=(
            f"Live bid {bid:.5f} is above entry zone {zone.low:.5f}-{zone.high:.5f} "
            f"— market sell at better price"
        ),
    )
