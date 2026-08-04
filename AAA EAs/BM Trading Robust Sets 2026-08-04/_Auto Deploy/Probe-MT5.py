"""Read the active MT5 terminal, account and broker symbol catalog as JSON."""

from __future__ import annotations

import argparse
import json
import sys

import MetaTrader5 as mt5


def emit(payload: dict, exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
    raise SystemExit(exit_code)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True)
    args = parser.parse_args()

    if not mt5.initialize(path=args.terminal, timeout=60_000):
        code, message = mt5.last_error()
        emit({"ok": False, "error": f"MT5 initialize failed ({code}): {message}"}, 2)

    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None:
            code, message = mt5.last_error()
            emit({"ok": False, "error": f"Could not read terminal info ({code}): {message}"}, 3)
        if account is None:
            code, message = mt5.last_error()
            emit(
                {
                    "ok": False,
                    "error": (
                        "No logged-in account was found in this MT5 installation. "
                        f"MT5 error ({code}): {message}"
                    ),
                },
                4,
            )

        symbols = mt5.symbols_get()
        if symbols is None:
            code, message = mt5.last_error()
            emit({"ok": False, "error": f"Could not read broker symbols ({code}): {message}"}, 5)

        account_dict = account._asdict()
        terminal_dict = terminal._asdict()
        emit(
            {
                "ok": True,
                "terminal": {
                    "name": terminal_dict.get("name", ""),
                    "company": terminal_dict.get("company", ""),
                    "path": terminal_dict.get("path", ""),
                    "data_path": terminal_dict.get("data_path", ""),
                    "connected": bool(terminal_dict.get("connected", False)),
                    "trade_allowed": bool(terminal_dict.get("trade_allowed", False)),
                },
                "account": {
                    "login": str(account_dict.get("login", "")),
                    "server": account_dict.get("server", ""),
                    "company": account_dict.get("company", ""),
                    "currency": account_dict.get("currency", ""),
                    "balance": float(account_dict.get("balance", 0.0)),
                    "equity": float(account_dict.get("equity", 0.0)),
                    "trade_allowed": bool(account_dict.get("trade_allowed", False)),
                    "trade_expert": bool(account_dict.get("trade_expert", False)),
                    "trade_mode": int(account_dict.get("trade_mode", -1)),
                },
                "symbols": [
                    {
                        "name": item.name,
                        "path": item.path,
                        "visible": bool(item.visible),
                        "select": bool(item.select),
                        "trade_mode": int(item.trade_mode),
                        "volume_min": float(item.volume_min),
                        "volume_max": float(item.volume_max),
                        "volume_step": float(item.volume_step),
                    }
                    for item in symbols
                ],
            }
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
