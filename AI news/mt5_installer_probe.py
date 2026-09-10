from __future__ import annotations

import argparse
import json
from pathlib import Path

import MetaTrader5 as mt5


def compact(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def symbol_score(name: str) -> tuple[int, int, str]:
    normalized = compact(name)
    if normalized == "XAUUSD":
        return 0, len(name), name
    if normalized.startswith("XAUUSD"):
        return 10, len(name), name
    if normalized == "GOLD":
        return 20, len(name), name
    if normalized.startswith("GOLD"):
        return 30, len(name), name
    return 1000, len(name), name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True)
    args = parser.parse_args()

    terminal = Path(args.terminal).resolve()
    if not terminal.exists():
        raise SystemExit(f"Terminal does not exist: {terminal}")
    if not mt5.initialize(path=str(terminal)):
        raise SystemExit(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        terminal_info = mt5.terminal_info()
        account = mt5.account_info()
        symbols = mt5.symbols_get() or ()
        if terminal_info is None or account is None:
            raise SystemExit("MT5 is not connected to an account.")
        candidates = sorted(
            (
                item
                for item in symbols
                if symbol_score(item.name)[0] < 1000
                and int(item.trade_mode) != int(mt5.SYMBOL_TRADE_MODE_DISABLED)
            ),
            key=lambda item: symbol_score(item.name),
        )
        selected = None
        for candidate in candidates:
            if mt5.symbol_select(candidate.name, True):
                tick = mt5.symbol_info_tick(candidate.name)
                if tick is not None and float(tick.bid) > 0 and float(tick.ask) > 0:
                    selected = candidate.name
                    break
        if selected is None:
            raise SystemExit("No tradable XAUUSD/GOLD broker symbol was found.")
        trade_mode_names = {
            int(mt5.ACCOUNT_TRADE_MODE_DEMO): "DEMO",
            int(mt5.ACCOUNT_TRADE_MODE_CONTEST): "CONTEST",
            int(mt5.ACCOUNT_TRADE_MODE_REAL): "REAL",
        }
        print(
            json.dumps(
                {
                    "terminal_exe": str(terminal),
                    "terminal_path": terminal_info.path,
                    "data_path": terminal_info.data_path,
                    "commondata_path": terminal_info.commondata_path,
                    "server": account.server,
                    "login": int(account.login),
                    "account_trade_mode": trade_mode_names.get(
                        int(account.trade_mode), f"UNKNOWN_{int(account.trade_mode)}"
                    ),
                    "trade_allowed": bool(terminal_info.trade_allowed),
                    "symbol": selected,
                    "candidates": [item.name for item in candidates],
                },
                separators=(",", ":"),
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
