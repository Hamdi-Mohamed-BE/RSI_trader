from __future__ import annotations

import json
import re
from typing import Any


CANONICAL_ALIASES = {
    "GOLD": "XAUUSD",
    "XAU": "XAUUSD",
    "XAAUSD": "XAUUSD",
    "SILVER": "XAGUSD",
    "XAG": "XAGUSD",
    "BTC": "BTCUSD",
    "BITCOIN": "BTCUSD",
    "ETH": "ETHUSD",
    "ETHEREUM": "ETHUSD",
    "US100": "US100",
    "NAS100": "US100",
    "USTEC": "US100",
    "USTEC100": "US100",
    "NDX": "US100",
    "US30": "US30",
    "DJ30": "US30",
    "DJI": "US30",
    "DOW": "US30",
}

BROKER_SUFFIXES = (
    ".RAW",
    ".PRO",
    ".MICRO",
    ".MINI",
    ".CASH",
    "-STD",
    "_STD",
    "-VIP",
    "_VIP",
    ".M",
    ".C",
    "M",
    "C",
)


def canonical_symbol(symbol: str | None) -> str:
    value = re.sub(r"[^A-Z0-9._-]", "", (symbol or "").upper().strip())
    compact = value.replace(".", "").replace("-", "").replace("_", "")
    if compact in CANONICAL_ALIASES:
        return CANONICAL_ALIASES[compact]
    for suffix in BROKER_SUFFIXES:
        if value.endswith(suffix) and len(value) > len(suffix) + 2:
            value = value[: -len(suffix)]
            break
    value = value.replace(".", "").replace("-", "").replace("_", "")
    return CANONICAL_ALIASES.get(value, value)


def parse_symbol_lots(value: Any) -> dict[str, float]:
    if isinstance(value, dict):
        raw_items = value.items()
    else:
        text = str(value or "").strip()
        if not text:
            return {}
        try:
            decoded = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            decoded = None
        if isinstance(decoded, dict):
            raw_items = decoded.items()
        else:
            entries = re.split(r"[\n,;]+", text)
            parsed_entries: list[tuple[str, str]] = []
            for entry in entries:
                parts = re.split(r"\s*[:=]\s*", entry.strip(), maxsplit=1)
                if len(parts) == 2:
                    parsed_entries.append((parts[0], parts[1]))
            raw_items = parsed_entries

    result: dict[str, float] = {}
    for raw_symbol, raw_lot in raw_items:
        symbol = canonical_symbol(str(raw_symbol))
        try:
            lot = float(raw_lot)
        except (TypeError, ValueError):
            continue
        if symbol and lot > 0:
            result[symbol] = lot
    return result


def fixed_lot_for_signal(
    symbol_raw: str,
    broker_symbol: str,
    default_lot: float,
    symbol_lots: Any,
) -> tuple[float, str]:
    overrides = parse_symbol_lots(symbol_lots)
    for candidate in (canonical_symbol(symbol_raw), canonical_symbol(broker_symbol)):
        if candidate in overrides:
            return overrides[candidate], f"symbol override ({candidate})"
    return float(default_lot), "default fixed lot"
