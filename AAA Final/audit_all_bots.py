from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import MetaTrader5 as mt5
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parent
SUCCESS_CHECKS = {0, int(mt5.TRADE_RETCODE_DONE), int(mt5.TRADE_RETCODE_PLACED)}


def enabled(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def available_symbols() -> list[object]:
    symbols = mt5.symbols_get()
    if symbols is None:
        raise RuntimeError(f"Cannot read MT5 symbols: {mt5.last_error()}")
    return [
        item
        for item in symbols
        if int(item.trade_mode) != int(mt5.SYMBOL_TRADE_MODE_DISABLED)
    ]


def symbol_score(canonical: str, item: object) -> tuple[int, int, int, int] | None:
    name = str(item.name).upper()
    description = str(getattr(item, "description", "")).upper()
    key = canonical.upper()
    if key == "US100":
        aliases = ("NAS100", "USTEC", "NDX", "NASDAQ", "US100")
        match = max((len(alias) for alias in aliases if alias in name), default=0)
        if not match:
            return None
    else:
        match = len(key) if key in name else 0
        if not match and key == "XAUUSD" and "GOLD" in description:
            match = 3
        if not match:
            return None
    tick = mt5.symbol_info_tick(item.name)
    tick_time = int(getattr(tick, "time", 0) or 0)
    return (match, int(bool(item.visible)), tick_time, -len(name))


def discover(canonical: str, symbols: list[object]) -> str:
    choices = [
        (score, item.name)
        for item in symbols
        if (score := symbol_score(canonical, item)) is not None
    ]
    if not choices:
        raise RuntimeError(f"No broker symbol found for {canonical}")
    symbol = max(choices, key=lambda row: row[0])[1]
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Cannot select {symbol}: {mt5.last_error()}")
    return symbol


def market_modes(info: object) -> tuple[int, ...]:
    flags = int(getattr(info, "filling_mode", 0))
    modes: list[int] = []
    if flags & 1:
        modes.append(int(mt5.ORDER_FILLING_FOK))
    if flags & 2:
        modes.append(int(mt5.ORDER_FILLING_IOC))
    for fallback in (
        int(mt5.ORDER_FILLING_FOK),
        int(mt5.ORDER_FILLING_IOC),
        int(mt5.ORDER_FILLING_RETURN),
    ):
        if fallback not in modes:
            modes.append(fallback)
    return tuple(modes)


def accepted(request: dict[str, object], modes: tuple[int, ...]) -> int | None:
    for mode in modes:
        candidate = dict(request)
        candidate["type_filling"] = mode
        result = mt5.order_check(candidate)
        if result is not None and int(result.retcode) in SUCCESS_CHECKS:
            return mode
    return None


def order_preflight(symbol: str) -> tuple[bool, str]:
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        return False, "symbol details or tick unavailable"
    point = float(info.point)
    digits = int(info.digits)
    distance = max(
        (int(info.trade_stops_level) + 20) * point,
        max(abs(float(tick.ask)), 1.0) * 0.001,
    )
    volume = float(info.volume_min)
    ask = float(tick.ask)
    bid = float(tick.bid)
    common = {
        "volume": volume,
        "symbol": symbol,
        "magic": 999002,
        "comment": "PREFLIGHT_NO_SEND",
        "type_time": mt5.ORDER_TIME_GTC,
    }
    market = {
        **common,
        "action": mt5.TRADE_ACTION_DEAL,
        "type": mt5.ORDER_TYPE_BUY,
        "price": round(ask, digits),
        "sl": round(ask - distance, digits),
        "tp": round(ask + distance, digits),
        "deviation": 50,
    }
    market_mode = accepted(market, market_modes(info))
    if market_mode is None:
        return False, "market order rejected by order_check"

    pending_specs = (
        ("BUY_LIMIT", mt5.ORDER_TYPE_BUY_LIMIT, ask - distance, ask - 2 * distance, ask),
        ("SELL_LIMIT", mt5.ORDER_TYPE_SELL_LIMIT, bid + distance, bid + 2 * distance, bid),
        ("BUY_STOP", mt5.ORDER_TYPE_BUY_STOP, ask + distance, ask, ask + 2 * distance),
        ("SELL_STOP", mt5.ORDER_TYPE_SELL_STOP, bid - distance, bid, bid - 2 * distance),
    )
    rejected: list[str] = []
    for label, order_type, price, stop, target in pending_specs:
        request = {
            **common,
            "action": mt5.TRADE_ACTION_PENDING,
            "type": order_type,
            "price": round(price, digits),
            "sl": round(stop, digits),
            "tp": round(target, digits),
        }
        if accepted(request, (int(mt5.ORDER_FILLING_RETURN),)) is None:
            rejected.append(label)
    if rejected:
        return False, "pending rejected: " + ", ".join(rejected)
    return True, f"market fill={market_mode}; four pending types accepted"


def bot_definitions() -> list[tuple[str, Path, list[str], int]]:
    asia_env = dotenv_values(ROOT / "asia breakout" / ".env")
    basket_path = ROOT / "asia breakout" / str(
        asia_env.get("SYMBOL_CONFIG_PATH", "configs/core4_basket.json")
    )
    basket = json.loads(basket_path.read_text(encoding="utf-8"))
    asia_symbols = list(basket.keys())
    return [
        ("AMD", ROOT / "AMD" / ".env", ["XAUUSD"], 300730),
        ("Asia Breakout", ROOT / "asia breakout" / ".env", asia_symbols, 290729),
        ("DmC", ROOT / "DmC" / ".env", ["US100"], 1082601),
        ("EMA3", ROOT / "EMA3" / ".env", ["XAUUSD"], 3082026),
        ("US100 Weakness", ROOT / "US100 weekness" / ".env", ["US100"], 310731),
    ]


def main() -> int:
    print("ALL BOT PREFLIGHT (order_check only; no orders are submitted)")
    if not mt5.initialize():
        print(f"FAIL MT5 initialization: {mt5.last_error()}")
        return 1
    failures = 0
    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            print("FAIL connected account or terminal unavailable")
            return 1
        print(
            f"Account {account.login} | {account.server} | balance "
            f"${account.balance:,.2f} | equity ${account.equity:,.2f} | "
            f"free margin ${account.margin_free:,.2f} | leverage 1:{account.leverage}"
        )
        print(
            f"Trading permissions: terminal={bool(terminal.trade_allowed)} "
            f"account={bool(account.trade_allowed)}"
        )
        if not bool(terminal.trade_allowed) or not bool(account.trade_allowed):
            failures += 1

        catalogue = available_symbols()
        usage: dict[str, list[str]] = defaultdict(list)
        magics: dict[int, str] = {}
        resolved: dict[str, str] = {}
        for bot, env_path, canonicals, fallback_magic in bot_definitions():
            env = dotenv_values(env_path)
            magic = int(env.get("MAGIC", env.get("MAGIC_NUMBER", fallback_magic)))
            live = enabled(env.get("ENABLE_TRADING", env.get("LIVE_TRADING")))
            dry = enabled(env.get("DRY_RUN", "false"))
            duplicate = magic in magics
            if duplicate:
                failures += 1
            else:
                magics[magic] = bot
            print(
                f"\n{bot}: {'LIVE-ENABLED' if live and not dry else 'SAFE/DRY'} "
                f"magic={magic}{' DUPLICATE' if duplicate else ''}"
            )
            for canonical in canonicals:
                try:
                    symbol = resolved.get(canonical)
                    if symbol is None:
                        symbol = discover(canonical, catalogue)
                        resolved[canonical] = symbol
                    usage[canonical].append(bot)
                    ok, detail = order_preflight(symbol)
                    print(
                        f"  {'PASS' if ok else 'FAIL'} {canonical} -> "
                        f"{symbol}: {detail}"
                    )
                    failures += int(not ok)
                except Exception as exc:
                    failures += 1
                    print(f"  FAIL {canonical}: {exc}")

        print("\nCross-bot symbol ownership:")
        for canonical, bots in usage.items():
            label = "OVERLAP" if len(bots) > 1 else "single owner"
            print(f"  {canonical}: {', '.join(bots)} ({label})")

        positions = mt5.positions_get() or ()
        orders = mt5.orders_get() or ()
        known_magics = set(magics)
        owned_positions = [p for p in positions if int(p.magic) in known_magics]
        owned_orders = [o for o in orders if int(o.magic) in known_magics]
        foreign_positions = [p for p in positions if int(p.magic) not in known_magics]
        print(
            f"\nState: bot positions={len(owned_positions)}, bot pending="
            f"{len(owned_orders)}, external/manual positions={len(foreign_positions)}"
        )
        print(f"Checked at {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC")
        print("RESULT:", "PASS" if failures == 0 else f"FAIL ({failures} issue(s))")
        return 0 if failures == 0 else 1
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
