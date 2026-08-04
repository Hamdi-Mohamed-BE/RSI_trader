"""Read the active MT5 terminal, account and broker symbol catalog as JSON."""

from __future__ import annotations

import argparse
import json
import sys

import MetaTrader5 as mt5


TARGET_ALIASES = (
    "USDJPY",
    "XAUUSD",
    "GOLD",
    "US30",
    "DJ30",
    "WS30",
    "DJI30",
    "DOW30",
    "DOWJONES",
    "NDX100",
    "NAS100",
    "USTEC",
    "US100",
    "UT100",
    "NASDAQ100",
    "NQ100",
)


def normalize_symbol(name: str) -> str:
    return "".join(character for character in name.upper() if character.isalnum())


def is_target_symbol(name: str) -> bool:
    normalized = normalize_symbol(name)
    return any(alias in normalized for alias in TARGET_ALIASES)


def symbol_payload(original, account_currency: str) -> dict:
    item = original
    if is_target_symbol(original.name):
        # Some brokers return zero quotes and tick values for an otherwise tradable
        # index until Market Watch subscribes to it. Selecting it is read-only.
        mt5.symbol_select(original.name, True)
        refreshed = mt5.symbol_info(original.name)
        if refreshed is not None:
            item = refreshed

    tick = mt5.symbol_info_tick(item.name) if is_target_symbol(item.name) else None
    bid = max(float(item.bid), float(getattr(tick, "bid", 0.0)))
    ask = max(float(item.ask), float(getattr(tick, "ask", 0.0)))
    last = max(float(item.last), float(getattr(tick, "last", 0.0)))
    reference_price = max(
        bid,
        ask,
        last,
        float(item.session_price_open),
        float(item.session_price_settlement),
    )

    if is_target_symbol(item.name) and reference_price <= 0:
        for timeframe in (mt5.TIMEFRAME_M1, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_D1):
            rates = mt5.copy_rates_from_pos(item.name, timeframe, 0, 1)
            if rates is not None and len(rates):
                reference_price = float(rates[-1]["close"])
                if reference_price > 0:
                    break

    tick_size = abs(float(item.trade_tick_size)) or abs(float(item.point))
    tick_value = max(
        abs(float(item.trade_tick_value)),
        abs(float(item.trade_tick_value_loss)),
        abs(float(item.trade_tick_value_profit)),
    )

    if is_target_symbol(item.name) and tick_value <= 0 and reference_price > 0 and tick_size > 0:
        calculation_volume = max(float(item.volume_min), min(1.0, float(item.volume_max)))
        calculated_profit = mt5.order_calc_profit(
            mt5.ORDER_TYPE_BUY,
            item.name,
            calculation_volume,
            reference_price,
            reference_price + tick_size,
        )
        if calculated_profit is not None and calculation_volume > 0:
            tick_value = abs(float(calculated_profit)) / calculation_volume

    # Final deterministic fallback for USD-denominated index/metal/FX contracts.
    # For a one-tick movement, one lot changes by contract_size * tick_size
    # when the symbol profit currency already equals the account currency.
    if (
        is_target_symbol(item.name)
        and tick_value <= 0
        and tick_size > 0
        and float(item.trade_contract_size) > 0
        and str(item.currency_profit).upper() == account_currency.upper()
    ):
        tick_value = abs(float(item.trade_contract_size) * tick_size)

    return {
        "name": item.name,
        "path": item.path,
        "visible": bool(item.visible),
        "select": bool(item.select),
        "trade_mode": int(item.trade_mode),
        "volume_min": float(item.volume_min),
        "volume_max": float(item.volume_max),
        "volume_step": float(item.volume_step),
        "bid": bid,
        "ask": ask,
        "reference_price": reference_price,
        "trade_tick_size": tick_size,
        "trade_tick_value": tick_value,
        "trade_tick_value_loss": max(abs(float(item.trade_tick_value_loss)), tick_value),
        "trade_contract_size": float(item.trade_contract_size),
        "currency_profit": str(item.currency_profit),
    }


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
                "symbols": [symbol_payload(item, str(account_dict.get("currency", ""))) for item in symbols],
            }
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
