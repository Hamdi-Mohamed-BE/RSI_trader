from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Direction, EntryType, ParseOutcome, Signal

PRICE_RE = r"\d[\d,]*(?:\.\d+)?"
SYMBOL_RE = r"[A-Z]{2,10}\d{0,5}"

HEADER_PATTERNS = [
    re.compile(
        rf"\b(?P<symbol>{SYMBOL_RE})\s+"
        rf"(?P<direction>BUY|SELL)\s*"
        rf"(?P<kind>NOW|MARKET|LIMIT|STOP)?\s*"
        rf"(?:@|AT|ENTRY)?\s*(?P<entry>{PRICE_RE})?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<direction>BUY|SELL)\s+"
        rf"(?P<symbol>{SYMBOL_RE})\s*"
        rf"(?P<kind>NOW|MARKET|LIMIT|STOP)?\s*"
        rf"(?:@|AT|ENTRY)?\s*(?P<entry>{PRICE_RE})?",
        re.IGNORECASE,
    ),
]

SL_PATTERNS = [
    re.compile(
        rf"\b(?:SL|S/L|STOP\s*LOSS|STOPLOSS)\b\s*(?:@|:|-|=)?\s*(?P<price>{PRICE_RE})",
        re.IGNORECASE,
    ),
]

TP_PATTERN = re.compile(
    rf"\b(?:TP|TP\s*\d+|TAKE\s*PROFIT|TARGET)\s*\d*\b\s*"
    rf"(?:@|:|-|=)?\s*(?P<price>{PRICE_RE})",
    re.IGNORECASE,
)

ENTRY_PATTERN = re.compile(
    rf"\b(?:ENTRY|ENTRIES|OPEN\s*PRICE)\b\s*(?:@|:|-|=)?\s*(?P<price>{PRICE_RE})",
    re.IGNORECASE,
)

PROMO_MARKERS = (
    "JOIN VIP",
    "VIP COMMUNITY",
    "PREMIUM",
    "SUBSCRIBE",
    "T.ME/",
    "HTTPS://",
    "HTTP://",
)


def _to_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    return float(value.replace(",", "").strip())


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _has_forward_marker(text: str) -> bool:
    upper = text.upper()
    return "FORWARDED FROM" in upper or upper.startswith("FORWARDED")


def _looks_promotional_without_signal(text: str) -> bool:
    upper = text.upper()
    if any(marker in upper for marker in PROMO_MARKERS):
        return not any(pattern.search(text) for pattern in HEADER_PATTERNS)
    return False


class SignalParser:
    def __init__(self, max_age_seconds: int = 180) -> None:
        self.max_age_seconds = max_age_seconds

    def parse(
        self,
        text: str | None,
        *,
        source_id: str,
        message_id: int,
        created_at: datetime | None,
        forwarded: bool = False,
        now: datetime | None = None,
    ) -> ParseOutcome:
        if not text or not text.strip():
            return ParseOutcome(None, "empty message")

        if forwarded or _has_forward_marker(text):
            return ParseOutcome(None, "forwarded message")

        created = _to_utc(created_at)
        current = _to_utc(now)
        age = (current - created).total_seconds()
        if age > self.max_age_seconds:
            return ParseOutcome(None, f"message older than {self.max_age_seconds}s")

        if _looks_promotional_without_signal(text):
            return ParseOutcome(None, "promotional message")

        header = self._find_header(text)
        if not header:
            return ParseOutcome(None, "no trade header")

        stop_loss = self._find_stop_loss(text)
        if stop_loss is None:
            return ParseOutcome(None, "missing stop loss")

        take_profits = self._find_take_profits(text)
        if not take_profits:
            return ParseOutcome(None, "missing take profit")

        symbol, direction, entry_type, entry_price = header
        if entry_price is None:
            entry_price = self._find_entry_price(text)

        if entry_type is EntryType.MARKET and entry_price is None:
            resolved_entry_type = EntryType.MARKET
        elif entry_type is EntryType.MARKET and entry_price is not None:
            resolved_entry_type = EntryType.MARKET
        elif entry_type in {EntryType.LIMIT, EntryType.STOP}:
            resolved_entry_type = entry_type
        else:
            resolved_entry_type = EntryType.AUTO

        return ParseOutcome(
            Signal(
                source_id=source_id,
                message_id=message_id,
                created_at=created,
                symbol=symbol,
                direction=direction,
                entry_type=resolved_entry_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profits=tuple(take_profits),
                raw_text=text,
            )
        )

    def _find_header(
        self, text: str
    ) -> tuple[str, Direction, EntryType, float | None] | None:
        for line in _lines(text):
            for pattern in HEADER_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                symbol = match.group("symbol").upper()
                direction = Direction(match.group("direction").upper())
                raw_kind = match.group("kind")
                kind = raw_kind.upper() if raw_kind else ""
                entry = _number(match.group("entry"))

                if kind in {"NOW", "MARKET"}:
                    entry_type = EntryType.MARKET
                elif kind == "LIMIT":
                    entry_type = EntryType.LIMIT
                elif kind == "STOP":
                    entry_type = EntryType.STOP
                elif entry is not None:
                    entry_type = EntryType.AUTO
                else:
                    entry_type = EntryType.MARKET

                return symbol, direction, entry_type, entry
        return None

    def _find_stop_loss(self, text: str) -> float | None:
        for pattern in SL_PATTERNS:
            match = pattern.search(text)
            if match:
                return _number(match.group("price"))
        return None

    def _find_take_profits(self, text: str) -> list[float]:
        values: list[float] = []
        for match in TP_PATTERN.finditer(text):
            value = _number(match.group("price"))
            if value is not None:
                values.append(value)
        return values

    def _find_entry_price(self, text: str) -> float | None:
        match = ENTRY_PATTERN.search(text)
        if not match:
            return None
        return _number(match.group("price"))
