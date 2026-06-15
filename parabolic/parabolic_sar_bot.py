from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5


TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
}

FILLING_MODES = [
    mt5.ORDER_FILLING_RETURN,
    mt5.ORDER_FILLING_IOC,
    mt5.ORDER_FILLING_FOK,
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def as_dict(value: Any) -> dict[str, Any]:
    return value._asdict() if hasattr(value, "_asdict") else dict(value or {})


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    temp_path.replace(path)


def rates_to_dicts(rates) -> list[dict[str, float]]:
    if rates is None:
        return []
    return [
        {key: (int(value) if key == "time" else float(value)) for key, value in zip(rates.dtype.names, row)}
        for row in rates
    ]


def parabolic_sar(candles: list[dict[str, float]], start: float, increment: float, maximum: float) -> list[float | None]:
    """Standard PSAR calculation for completed OHLC candles."""
    count = len(candles)
    values: list[float | None] = [None] * count
    if count < 3:
        return values

    long_trend = candles[1]["close"] >= candles[0]["close"]
    extreme = candles[1]["high"] if long_trend else candles[1]["low"]
    sar = candles[0]["low"] if long_trend else candles[0]["high"]
    accel = start
    values[1] = sar

    for index in range(2, count):
        prev_sar = sar
        sar = prev_sar + accel * (extreme - prev_sar)
        if long_trend:
            sar = min(sar, candles[index - 1]["low"], candles[index - 2]["low"])
            if candles[index]["low"] < sar:
                long_trend = False
                sar = extreme
                extreme = candles[index]["low"]
                accel = start
            elif candles[index]["high"] > extreme:
                extreme = candles[index]["high"]
                accel = min(accel + increment, maximum)
        else:
            sar = max(sar, candles[index - 1]["high"], candles[index - 2]["high"])
            if candles[index]["high"] > sar:
                long_trend = True
                sar = extreme
                extreme = candles[index]["high"]
                accel = start
            elif candles[index]["low"] < extreme:
                extreme = candles[index]["low"]
                accel = min(accel + increment, maximum)
        values[index] = sar
    return values


class ParabolicSarBot:
    def __init__(self, root: Path, config: dict[str, Any], live_override: bool | None = None) -> None:
        self.root = root
        self.config = config
        self.state_path = root / config.get("state_file", "state/parabolic_sar_state.json")
        self.state = load_json(self.state_path) if self.state_path.exists() else {"symbols": {}, "trades": {}}
        if live_override is not None:
            self.config.setdefault("execution", {})["mode"] = "live" if live_override else "dry_run"

    @property
    def live(self) -> bool:
        return str(self.config.get("execution", {}).get("mode", "live")).lower() == "live"

    @property
    def magic(self) -> int:
        return int(self.config.get("execution", {}).get("magic", 26061560))

    def connect(self) -> None:
        mt5_path = self.config.get("mt5_path")
        ok = mt5.initialize(path=mt5_path) if mt5_path else mt5.initialize()
        if not ok:
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    def shutdown(self) -> None:
        mt5.shutdown()

    def symbol_config(self, logical: str, entry: Any) -> tuple[list[str], float]:
        if isinstance(entry, dict):
            aliases = list(entry.get("aliases", [logical]))
            lot = float(entry.get("lot", 0.01))
        else:
            aliases = list(entry if isinstance(entry, list) else [logical])
            lot = float(self.config.get("lots", {}).get(logical, 0.01))
        return aliases, lot

    def resolve_symbol(self, logical: str, aliases: list[str]) -> str | None:
        names = [symbol.name for symbol in (mt5.symbols_get() or [])]
        upper_to_name = {name.upper(): name for name in names}
        for alias in aliases:
            found = upper_to_name.get(alias.upper())
            if found:
                mt5.symbol_select(found, True)
                return found
        candidates = [name for name in names if name.upper().startswith(logical.upper())]
        candidates.sort(key=lambda name: (0 if "VIP" in name.upper() else 1, len(name), name))
        if candidates:
            mt5.symbol_select(candidates[0], True)
            return candidates[0]
        return None

    def closed_rates(self, symbol: str, timeframe: int, count: int) -> list[dict[str, float]]:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        candles = rates_to_dicts(rates)
        return candles[:-1] if len(candles) > 1 else []

    def psar_signal(self, logical: str, broker_symbol: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        strategy = self.config.get("strategy", {})
        timeframe_name = str(self.config.get("timeframe", "M5")).upper()
        timeframe = TIMEFRAMES.get(timeframe_name, mt5.TIMEFRAME_M5)
        candles = self.closed_rates(broker_symbol, timeframe, int(strategy.get("bars", 300)))
        if len(candles) < 50:
            return None, {"status": "insufficient_candles", "bars": len(candles)}

        start = float(strategy.get("start", 0.02))
        increment = float(strategy.get("increment", 0.02))
        maximum = float(strategy.get("maximum", 0.2))
        psar_values = parabolic_sar(candles, start, increment, maximum)
        if psar_values[-1] is None or psar_values[-2] is None:
            return None, {"status": "psar_unavailable"}

        directions = [1 if psar is not None and psar < candle["close"] else -1 for psar, candle in zip(psar_values, candles)]
        last_bar_time = int(candles[-1]["time"])
        prev_dir = int(directions[-2])
        current_dir = int(directions[-1])
        side = "BUY" if current_dir == 1 and prev_dir == -1 else "SELL" if current_dir == -1 and prev_dir == 1 else None

        state = self.state.setdefault("symbols", {}).setdefault(logical, {})
        if not state:
            state.update({"last_bar_time": last_bar_time, "last_dir": current_dir, "updated_at": utc_now()})
            if strategy.get("bootstrap_no_trade", True):
                return None, {"status": "bootstrapped", "dir": current_dir, "bar_time": last_bar_time}

        if state.get("last_signal_bar_time") == last_bar_time:
            return None, {"status": "signal_already_processed", "dir": current_dir, "bar_time": last_bar_time}

        if side is None:
            state.update({"last_bar_time": last_bar_time, "last_dir": current_dir, "updated_at": utc_now()})
            return None, {"status": "no_flip", "dir": current_dir, "bar_time": last_bar_time}

        info = mt5.symbol_info(broker_symbol)
        tick = mt5.symbol_info_tick(broker_symbol)
        if not info or not tick:
            return None, {"status": "symbol_info_unavailable"}

        entry = float(tick.ask if side == "BUY" else tick.bid)
        psar = float(psar_values[-1])
        sl = psar if bool(strategy.get("use_psar_as_sl", True)) else 0.0
        if side == "BUY" and sl >= entry:
            return None, {"status": "invalid_buy_sl", "entry": round(entry, info.digits), "psar": round(psar, info.digits)}
        if side == "SELL" and sl <= entry:
            return None, {"status": "invalid_sell_sl", "entry": round(entry, info.digits), "psar": round(psar, info.digits)}

        signal = {
            "logical_symbol": logical,
            "broker_symbol": broker_symbol,
            "side": side,
            "bar_time": last_bar_time,
            "entry": round(entry, info.digits),
            "sl": round(sl, info.digits) if sl else 0.0,
            "psar": round(psar, info.digits),
            "dir": current_dir,
            "timeframe": timeframe_name,
        }
        state.update({
            "last_bar_time": last_bar_time,
            "last_dir": current_dir,
            "last_signal_bar_time": last_bar_time,
            "updated_at": utc_now(),
        })
        return signal, {"status": "signal", "side": side, "bar_time": last_bar_time}

    def bot_position(self, position: Any) -> bool:
        data = as_dict(position)
        comment = str(data.get("comment", "")).lower()
        configured_comment = str(self.config.get("execution", {}).get("open_comment", "parabolic")).lower()
        return (
            int(data.get("magic", 0) or 0) == self.magic
            or comment.startswith("psar")
            or comment.startswith("parabolic")
            or bool(configured_comment and comment.startswith(configured_comment))
        )

    def symbol_positions(self, symbol: str) -> list[Any]:
        positions = list(mt5.positions_get(symbol=symbol) or [])
        if self.config.get("execution", {}).get("manage_all_symbol_positions", False):
            return positions
        return [position for position in positions if self.bot_position(position)]

    def normalize_lot(self, symbol: str, requested: float) -> tuple[float | None, dict[str, Any]]:
        info = mt5.symbol_info(symbol)
        if not info:
            return None, {"error": "symbol_info_missing"}
        step = float(info.volume_step or 0.01)
        min_lot = float(info.volume_min or step)
        max_lot = float(info.volume_max or requested)
        lot = math.floor(float(requested) / step) * step
        lot = min(lot, max_lot)
        lot = round(lot, 4)
        if lot < min_lot:
            return None, {"error": "lot_below_min", "requested": requested, "min_lot": min_lot, "step": step}
        return lot, {"requested": requested, "lot": lot, "min_lot": min_lot, "max_lot": max_lot, "step": step}

    def send_with_filling_modes(self, request_base: dict[str, Any]) -> dict[str, Any]:
        if not self.live:
            return {"ok": True, "dry_run": True, "request": request_base}
        last_error: dict[str, Any] | None = None
        for filling in FILLING_MODES:
            request = dict(request_base)
            request["type_filling"] = filling
            check = mt5.order_check(request)
            check_data = as_dict(check) if check else {"retcode": None, "comment": "no check result"}
            if check_data.get("retcode") != 0:
                last_error = {"stage": "check", "retcode": check_data.get("retcode"), "comment": check_data.get("comment"), "filling": filling}
                continue
            result = mt5.order_send(request)
            result_data = as_dict(result) if result else {"retcode": None, "comment": "no send result"}
            if result_data.get("retcode") in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
                return {
                    "ok": True,
                    "order": result_data.get("order"),
                    "deal": result_data.get("deal"),
                    "retcode": result_data.get("retcode"),
                    "comment": result_data.get("comment"),
                    "request": request,
                }
            last_error = {"stage": "send", "retcode": result_data.get("retcode"), "comment": result_data.get("comment"), "filling": filling}
        return {"ok": False, "error": last_error or "unknown_order_error", "request": request_base}

    def close_position(self, position: Any) -> dict[str, Any]:
        data = as_dict(position)
        symbol = data["symbol"]
        side = "BUY" if int(data["type"]) == mt5.POSITION_TYPE_BUY else "SELL"
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"ok": False, "ticket": int(data["ticket"]), "error": "tick_unavailable"}
        close_type = mt5.ORDER_TYPE_SELL if side == "BUY" else mt5.ORDER_TYPE_BUY
        price = float(tick.bid if side == "BUY" else tick.ask)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(data["volume"]),
            "type": close_type,
            "position": int(data["ticket"]),
            "price": price,
            "deviation": int(self.config.get("execution", {}).get("deviation_points", 30)),
            "magic": self.magic,
            "comment": str(self.config.get("execution", {}).get("close_comment", "parabolic close"))[:31],
        }
        result = self.send_with_filling_modes(request)
        result["ticket"] = int(data["ticket"])
        result["closed_side"] = side
        return result

    def open_position(self, signal: dict[str, Any], lot: float) -> dict[str, Any]:
        order_type = mt5.ORDER_TYPE_BUY if signal["side"] == "BUY" else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal["broker_symbol"],
            "volume": lot,
            "type": order_type,
            "price": signal["entry"],
            "deviation": int(self.config.get("execution", {}).get("deviation_points", 30)),
            "magic": self.magic,
            "comment": str(self.config.get("execution", {}).get("open_comment", "parabolic"))[:31],
        }
        if signal.get("sl", 0.0):
            request["sl"] = float(signal["sl"])
        return self.send_with_filling_modes(request)

    def execute_signal(self, signal: dict[str, Any], requested_lot: float) -> dict[str, Any]:
        symbol = signal["broker_symbol"]
        desired_side = signal["side"]
        positions = self.symbol_positions(symbol)
        same_side = []
        opposite = []
        for position in positions:
            data = as_dict(position)
            side = "BUY" if int(data["type"]) == mt5.POSITION_TYPE_BUY else "SELL"
            (same_side if side == desired_side else opposite).append(position)

        close_results = []
        for position in opposite:
            close_results.append(self.close_position(position))
        if close_results and not all(result.get("ok") for result in close_results):
            return {"ok": False, "stage": "close_opposite", "close_results": close_results}

        if same_side and not self.config.get("execution", {}).get("open_if_same_side_exists", False):
            return {"ok": True, "skipped": "same_side_position_exists", "close_results": close_results}

        lot, lot_info = self.normalize_lot(symbol, requested_lot)
        if lot is None:
            return {"ok": False, "stage": "lot", "lot_info": lot_info, "close_results": close_results}
        open_result = self.open_position(signal, lot)
        return {"ok": open_result.get("ok", False), "lot": lot, "lot_info": lot_info, "close_results": close_results, "open_result": open_result}

    def run_once(self, write_state: bool = True) -> dict[str, Any]:
        self.connect()
        try:
            account = mt5.account_info()
            terminal = mt5.terminal_info()
            if not account or not terminal:
                raise RuntimeError("MT5 account/terminal info unavailable")

            output: dict[str, Any] = {
                "time_utc": utc_now(),
                "mode": self.config.get("execution", {}).get("mode", "live"),
                "timeframe": self.config.get("timeframe", "M5"),
                "account": {
                    "login": int(account.login),
                    "balance": round(float(account.balance), 2),
                    "equity": round(float(account.equity), 2),
                    "free_margin": round(float(account.margin_free), 2),
                    "trade_allowed": bool(account.trade_allowed),
                    "terminal_trade_allowed": bool(terminal.trade_allowed),
                },
                "symbols": [],
                "signals": [],
                "orders": [],
            }
            can_trade = bool(account.trade_allowed) and bool(terminal.trade_allowed)
            for logical, entry in self.config.get("symbols", {}).items():
                aliases, requested_lot = self.symbol_config(logical, entry)
                broker_symbol = self.resolve_symbol(logical, aliases)
                row: dict[str, Any] = {"logical": logical, "broker": broker_symbol, "requested_lot": requested_lot}
                if not broker_symbol:
                    row["status"] = "symbol_not_found"
                    output["symbols"].append(row)
                    continue
                signal, note = self.psar_signal(logical, broker_symbol)
                row.update(note)
                if signal is None:
                    output["symbols"].append(row)
                    continue
                output["signals"].append(signal)
                if not can_trade:
                    row["status"] = "signal_skipped_trade_not_allowed"
                    output["symbols"].append(row)
                    continue
                result = self.execute_signal(signal, requested_lot)
                row["execution"] = result
                output["orders"].append({"logical": logical, "broker": broker_symbol, "signal": signal, "result": result})
                output["symbols"].append(row)
            if write_state:
                save_json(self.state_path, self.state)
            return output
        finally:
            self.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MT5 Parabolic SAR flip bot.")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--loop", action="store_true", help="Keep scanning on poll_seconds")
    parser.add_argument("--live", action="store_true", help="Override config and allow real orders")
    parser.add_argument("--dry-run", action="store_true", help="Override config and prevent real orders")
    parser.add_argument("--no-state-write", action="store_true", help="Do not save state after this run")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = load_json(config_path)
    live_override = True if args.live else False if args.dry_run else None
    bot = ParabolicSarBot(root, config, live_override=live_override)
    if args.loop:
        while True:
            print(json.dumps(bot.run_once(write_state=not args.no_state_write), indent=2))
            time.sleep(int(config.get("poll_seconds", 30)))
    else:
        print(json.dumps(bot.run_once(write_state=not args.no_state_write), indent=2))


if __name__ == "__main__":
    main()
