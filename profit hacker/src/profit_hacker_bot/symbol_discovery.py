from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


COMMON_ALIASES: dict[str, tuple[str, ...]] = {
    "NAS100": ("NAS100", "US100", "USTEC", "USTEC100", "NDX100", "NASDAQ100"),
    "US100": ("US100", "NAS100", "USTEC", "USTEC100", "NDX100", "NASDAQ100"),
    "SPX500": ("SPX500", "US500", "SP500", "S&P500"),
    "US500": ("US500", "SPX500", "SP500", "S&P500"),
    "US30": ("US30", "DJ30", "DOW30", "WS30"),
    "GER40": ("GER40", "DE40", "DAX40", "DAX"),
    "DE40": ("DE40", "GER40", "DAX40", "DAX"),
    "UK100": ("UK100", "FTSE100", "FTSE"),
    "JP225": ("JP225", "JPN225", "NIKKEI225", "NIKKEI"),
    "XAUUSD": ("XAUUSD", "GOLD"),
    "XAGUSD": ("XAGUSD", "SILVER"),
    "BTCUSD": ("BTCUSD", "BTC"),
    "ETHUSD": ("ETHUSD", "ETH"),
}


@dataclass(frozen=True)
class SymbolMatch:
    name: str
    score: int
    reason: str


def normalize_symbol(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def search_terms(telegram_symbol: str) -> tuple[str, ...]:
    normalized = normalize_symbol(telegram_symbol)
    aliases = COMMON_ALIASES.get(normalized, (normalized,))
    values: list[str] = []
    for alias in (normalized, *aliases):
        term = normalize_symbol(alias)
        if term and term not in values:
            values.append(term)
    return tuple(values)


def choose_best_symbol(
    telegram_symbol: str,
    broker_symbols: list[Any] | tuple[Any, ...],
    *,
    disabled_trade_mode: int | None = None,
) -> SymbolMatch | None:
    matches: list[SymbolMatch] = []
    for symbol in broker_symbols:
        name = str(getattr(symbol, "name", symbol))
        trade_mode = getattr(symbol, "trade_mode", None)
        if disabled_trade_mode is not None and trade_mode == disabled_trade_mode:
            continue
        match = score_symbol(telegram_symbol, name)
        if match:
            matches.append(match)

    if not matches:
        return None

    matches.sort(key=lambda item: (-item.score, len(item.name), item.name.upper()))
    return matches[0]


def score_symbol(telegram_symbol: str, broker_symbol: str) -> SymbolMatch | None:
    broker_normalized = normalize_symbol(broker_symbol)
    if not broker_normalized:
        return None

    best_score = 0
    best_reason = ""
    for index, term in enumerate(search_terms(telegram_symbol)):
        alias_penalty = 0 if index == 0 else 20
        score = _score_term(term, broker_normalized) - alias_penalty
        if score > best_score:
            best_score = score
            best_reason = f"matched {term}"

    if best_score < 60:
        return None
    return SymbolMatch(name=broker_symbol, score=best_score, reason=best_reason)


def _score_term(term: str, broker_normalized: str) -> int:
    if broker_normalized == term:
        return 110
    if broker_normalized.startswith(term):
        return 96
    if broker_normalized.endswith(term):
        return 82
    if len(term) >= 4 and term in broker_normalized:
        return 68
    return 0
