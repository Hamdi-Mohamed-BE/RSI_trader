from __future__ import annotations

import re

from .models import TradeSignal


SIDE_PATTERN = re.compile(r"\b(BUY|SELL)\b", re.IGNORECASE)
SYMBOL_BEFORE_SIDE = re.compile(r"\b([A-Z]{3,12})\s+(?:BUY|SELL)\b", re.IGNORECASE)
SYMBOL_AFTER_SIDE = re.compile(r"\b(?:BUY|SELL)\s+([A-Z]{3,12})\b", re.IGNORECASE)
SL_PATTERN = re.compile(
    r"\b(?:SL|S\s*/\s*L|STOP\s*LOSS|STOPLOSS|STOPOSS)\s*(?:@|:|=)?\s*([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
TP_PATTERN = re.compile(
    r"\b(?:TP\s*\d*|TAKE\s*PROFIT\s*\d*)\s*(?:@|:|=)?\s*([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
ENTRY_PATTERN = re.compile(
    r"\b(?:ENTRY|ENTER|LIMIT|STOP)\s*(?:@|:|=)?\s*([0-9]+(?:\.[0-9]+)?)(?:\s*(?:-|TO)\s*([0-9]+(?:\.[0-9]+)?))?",
    re.IGNORECASE,
)
SIDE_PRICE_PATTERN = re.compile(
    r"\b(?:BUY|SELL)\s+(?:NOW\s+)?(?:@|:|=)?\s*([0-9]+(?:\.[0-9]+)?)(?:\s*(?:-|TO)\s*([0-9]+(?:\.[0-9]+)?))?",
    re.IGNORECASE,
)

IGNORED_SYMBOL_WORDS = {
    "NOW", "LIMIT", "STOP", "MARKET", "SIGNAL", "ENTRY", "ZONE", "GOLDEN",
}


def parse_signal(text: str, aliases: dict[str, str] | None = None) -> TradeSignal | None:
    cleaned = _clean(text)
    side_match = SIDE_PATTERN.search(cleaned)
    if side_match is None:
        return None
    side = side_match.group(1).upper()
    symbol = _symbol(cleaned, aliases or {})
    if symbol is None:
        return None
    sl_match = SL_PATTERN.search(cleaned)
    take_profits = tuple(float(value) for value in TP_PATTERN.findall(cleaned))
    if sl_match is None or not take_profits:
        return None

    entry_match = ENTRY_PATTERN.search(cleaned) or SIDE_PRICE_PATTERN.search(cleaned)
    entry_low = float(entry_match.group(1)) if entry_match else None
    entry_high = float(entry_match.group(2)) if entry_match and entry_match.group(2) else entry_low
    market = bool(re.search(r"\b(?:BUY|SELL)\s+NOW\b|\bMARKET\b", cleaned, re.IGNORECASE))
    if entry_low is None:
        market = True

    ordered_targets = sorted(set(take_profits), reverse=side == "SELL")
    signal = TradeSignal(
        symbol=symbol,
        side=side,
        entry_low=min(entry_low, entry_high) if entry_low is not None and entry_high is not None else None,
        entry_high=max(entry_low, entry_high) if entry_low is not None and entry_high is not None else None,
        stop_loss=float(sl_match.group(1)),
        take_profits=tuple(ordered_targets),
        market=market,
        raw_text=text.strip(),
    )
    return signal if valid_geometry(signal) else None


def valid_geometry(signal: TradeSignal) -> bool:
    reference = None
    if signal.entry_low is not None and signal.entry_high is not None:
        reference = (signal.entry_low + signal.entry_high) / 2.0
    if reference is None:
        return True
    if signal.side == "BUY":
        return signal.stop_loss < reference and all(target > reference for target in signal.take_profits)
    return signal.stop_loss > reference and all(target < reference for target in signal.take_profits)


def _symbol(text: str, aliases: dict[str, str]) -> str | None:
    for pattern in (SYMBOL_BEFORE_SIDE, SYMBOL_AFTER_SIDE):
        match = pattern.search(text)
        if not match:
            continue
        token = match.group(1).upper().replace("/", "")
        if token not in IGNORED_SYMBOL_WORDS:
            return aliases.get(token, token)
    for alias, canonical in aliases.items():
        if re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE):
            return canonical
    return None


def _clean(text: str) -> str:
    return re.sub(r"[\u200b-\u200f\ufeff]", "", text).replace(",", " ")

