from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import MetaTrader5 as mt5


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "mt5-live.json"
EXAMPLE_PATH = ROOT / "config" / "mt5-live.example.json"


def stop(message: str, code: int = 2) -> None:
    print(f"\nBLOCKED: {message}")
    print("No order was sent.")
    mt5.shutdown()
    raise SystemExit(code)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        stop(
            f"Create {CONFIG_PATH.name} by copying {EXAMPLE_PATH.name}, then set the real futures symbol."
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def is_tradable(symbol_info) -> bool:
    return symbol_info is not None and int(symbol_info.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_FULL)


def main() -> None:
    config = load_config()
    terminal_path = str(config.get("terminal_path", "")).strip()
    connected = mt5.initialize(path=terminal_path) if terminal_path else mt5.initialize()
    if not connected:
        stop(f"MT5 connection failed: {mt5.last_error()}")

    account = mt5.account_info()
    terminal = mt5.terminal_info()
    if account is None or terminal is None:
        stop(f"MT5 did not return account information: {mt5.last_error()}")

    risk_percent = float(config.get("risk_percent", 1.0))
    if abs(risk_percent - 1.0) > 1e-9:
        stop("This runner is locked to exactly 1.0% account-equity risk per complete basis trade.")
    risk_usd = float(account.equity) * risk_percent / 100.0

    spot_symbol = str(config.get("spot_symbol", "")).strip()
    futures_symbol = str(config.get("futures_symbol", "")).strip()
    spot = mt5.symbol_info(spot_symbol) if spot_symbol else None
    future = mt5.symbol_info(futures_symbol) if futures_symbol else None

    print("BTC BASIS LIVE READINESS")
    print("------------------------")
    print(f"Account: {account.login} / {account.server}")
    print(f"Equity: ${account.equity:,.2f}")
    print(f"Risk cap: {risk_percent:.2f}% = ${risk_usd:,.2f} per complete two-leg trade")
    print(f"Spot leg: {spot_symbol or '(not configured)'}")
    print(f"CME futures leg: {futures_symbol or '(not configured)'}")
    print(f"Databento key: {'present' if os.getenv('DATABENTO_API_KEY') else 'missing'}")

    if not is_tradable(spot):
        stop(f"spot symbol '{spot_symbol}' is missing or not fully tradable on this MT5 account")
    if not futures_symbol:
        stop("no CME BTC/MBT futures symbol is configured")
    if not is_tradable(future):
        path = getattr(future, "path", "not found") if future is not None else "not found"
        stop(f"futures symbol '{futures_symbol}' is unavailable or disabled (path: {path})")
    if futures_symbol.upper() == spot_symbol.upper():
        stop("the spot and futures legs cannot be the same broker symbol")
    if "FUT" not in str(future.path).upper() and "CME" not in str(future.path).upper():
        stop(f"'{futures_symbol}' does not identify itself as an exchange futures product ({future.path})")
    if not os.getenv("DATABENTO_API_KEY"):
        stop("DATABENTO_API_KEY is missing; the CME signal feed cannot start")
    if not bool(config.get("live_trading", False)):
        stop("live_trading is false; this is the safe default")

    stop(
        "market prerequisites passed, but order sending remains intentionally disabled because the post-May-2026 maintenance-window strategy has not been validated",
        code=3,
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        mt5.shutdown()
