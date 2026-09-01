from __future__ import annotations

import re
import sys

import MetaTrader5 as mt5


def normalized(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", name.upper())


def gold_score(symbol) -> int | None:
    name = normalized(symbol.name)
    if "XAUUSD" not in name and not name.startswith("GOLD"):
        return None

    score = 0
    if symbol.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
        score += 1000
    if symbol.visible:
        score += 500
    if symbol.select:
        score += 100
    if name == "XAUUSD":
        score += 40
    elif name.startswith("XAUUSD"):
        score += 35
    elif name.endswith("XAUUSD"):
        score += 30
    elif "XAUUSD" in name:
        score += 25
    elif name == "GOLD":
        score += 20
    elif name.startswith("GOLD"):
        score += 15
    return score


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    terminal = sys.argv[1]
    if not mt5.initialize(path=terminal):
        return 3
    try:
        candidates = []
        for symbol in mt5.symbols_get() or ():
            score = gold_score(symbol)
            if score is not None:
                candidates.append((score, symbol.name))
        if not candidates:
            return 4
        candidates.sort(key=lambda item: (-item[0], len(item[1]), item[1].upper()))
        print(candidates[0][1])
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
