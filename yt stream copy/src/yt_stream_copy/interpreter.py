from __future__ import annotations

import re
from collections import deque
from typing import Any

SYMBOLS = {
    "gold": "XAUUSD", "xau": "XAUUSD", "xauusd": "XAUUSD", "gc": "XAUUSD",
    "nasdaq": "US100", "nq": "US100", "us100": "US100", "ustec": "US100",
    "silver": "XAGUSD", "xag": "XAGUSD", "bitcoin": "BTCUSD", "btc": "BTCUSD",
    "eurusd": "EURUSD", "gbpusd": "GBPUSD", "gbpjpy": "GBPJPY",
}
SIDE_PATTERNS = {
    "buy": re.compile(r"\b(buy|buying|bought|long|going long)\b", re.I),
    "sell": re.compile(r"\b(sell|selling|sold|short|going short)\b", re.I),
}
ENTRY_WORDS = re.compile(
    r"\b(i(?:'m| am) (?:in|buying|selling|long|short)|i(?:'m| am) (?:gonna|going to) try to (?:buy|sell)|"
    r"press(?:ed|ing)? (?:buy|sell)|we(?:'re| are) in|entered|filled|just bought|just sold|"
    r"position is open|opened (?:a |the )?(?:trade|position))\b", re.I,
)
HYPOTHETICAL_WORDS = re.compile(
    r"\b(might|maybe|consider|could|would|if price|if we|looking for|interested in|"
    r"want to see|potential(?:ly)?|not in|don't enter|do not enter)\b", re.I,
)
IDEA_WORDS = re.compile(r"\b(might|maybe|consider|looking for|interested in|want to see|potential)\b", re.I)
# Bare phrases such as "closed above VWAP" are market commentary, not trade exits.
EXIT_WORDS = re.compile(
    r"\b(i(?:'m| am) out|we(?:'re| are) out|i closed (?:it|the trade|the position)|"
    r"we closed (?:it|the trade|the position)|close (?:it|the trade|the position|my position)|"
    r"took profit|take profit (?:was )?hit|stopped out|stop(?: loss)? (?:was )?hit|"
    r"exited (?:the trade|the position)|position is closed)\b", re.I,
)


def _symbol(text: str) -> str | None:
    lower = text.lower()
    return next((value for key, value in SYMBOLS.items() if re.search(rf"\b{re.escape(key)}\b", lower)), None)


def _side(text: str) -> str | None:
    return next((name for name, pattern in SIDE_PATTERNS.items() if pattern.search(text)), None)


def _number_after(text: str, labels: str) -> float | None:
    match = re.search(rf"(?:{labels})\s*(?:is\s+)?(?:at|to|:)?\s*([$]?\d[\d,]*(?:\.\d+)?)", text, re.I)
    if not match:
        return None
    return float(match.group(1).replace("$", "").replace(",", ""))


def interpret(text: str, channel: str = "Unknown") -> dict[str, Any] | None:
    """Stateless compatibility parser used by tests and manual transcript injection."""
    return ContextInterpreter(channel).feed(text)


class ContextInterpreter:
    """Interpret fragmented speech while remembering recently discussed symbol and side."""

    def __init__(self, channel: str = "Unknown") -> None:
        self.channel = channel
        self.recent: deque[str] = deque(maxlen=40)
        self.last_symbol: str | None = None
        self.pending_side: str | None = None

    def reset(self, channel: str) -> None:
        self.channel = channel
        self.recent.clear()
        self.last_symbol = None
        self.pending_side = None

    def feed(self, text: str) -> dict[str, Any] | None:
        clean = " ".join(text.split())
        if not clean:
            return None
        current_symbol = _symbol(clean)
        current_side = _side(clean)
        if current_symbol:
            self.last_symbol = current_symbol
        if current_side:
            self.pending_side = current_side
        symbol = current_symbol or self.last_symbol
        side = current_side or self.pending_side
        self.recent.append(clean)

        if EXIT_WORDS.search(clean):
            return {
                "status": "exit_reported", "symbol": symbol, "side": side, "confidence": 0.90,
                "reason": "Explicit spoken position exit detected.", "evidence": [clean],
                "mt5_comment": f"Stream {self.channel}"[:31],
            }

        entry_language = bool(ENTRY_WORDS.search(clean))
        hypothetical = bool(HYPOTHETICAL_WORDS.search(clean))
        direct_action = bool(re.search(
            r"\b(press(?:ed|ing)? (?:buy|sell)|we(?:'re| are) in|just bought|just sold|"
            r"i(?:'m| am) (?:gonna|going to) try to (?:buy|sell)|i(?:'m| am) (?:buying|selling|long|short))\b",
            clean, re.I,
        ))
        confirmed = entry_language and (direct_action or not hypothetical)
        if not side:
            return None
        if not symbol and not confirmed:
            return None

        entry = _number_after(clean, r"entry|entered|filled|bought|sold|press(?:ed)? (?:buy|sell)")
        stop_loss = _number_after(clean, r"stop(?: loss)?|sl")
        take_profit = _number_after(clean, r"take profit|target|tp")
        completeness = sum(value is not None for value in (entry, stop_loss, take_profit))

        if completeness and symbol and not confirmed and not current_side:
            return {
                "status": "level_update", "symbol": symbol, "side": side,
                "entry": entry, "stop_loss": stop_loss, "take_profit": take_profit,
                "confidence": min(0.94, 0.76 + completeness * 0.06),
                "reason": "A labelled trade level was stated after the entry.",
                "evidence": [clean], "mt5_comment": f"Stream {self.channel}"[:31],
            }

        if confirmed:
            return {
                "status": "confirmed_entry", "symbol": symbol, "side": side,
                "entry": entry, "stop_loss": stop_loss, "take_profit": take_profit,
                "confidence": min(0.98, 0.86 + completeness * 0.04),
                "reason": "Explicit spoken entry action detected across the live context.",
                "evidence": [clean], "mt5_comment": f"Stream {self.channel}"[:31],
            }
        if symbol and (current_side or IDEA_WORDS.search(clean)):
            return {
                "status": "watching", "symbol": symbol, "side": side,
                "entry": entry, "stop_loss": stop_loss, "take_profit": take_profit,
                "confidence": min(0.75, 0.48 + completeness * 0.05),
                "reason": "Trade idea mentioned without an explicit entry action.",
                "evidence": [clean], "mt5_comment": f"Stream {self.channel}"[:31],
            }
        return None
