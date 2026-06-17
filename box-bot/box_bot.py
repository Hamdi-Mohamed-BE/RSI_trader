from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
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


@dataclass
class BoxLevels:
    logical_symbol: str
    broker_symbol: str
    box_time: int
    high: float
    low: float
    mid: float
    range: float
    atr: float
    spread: float
    buffer: float


@dataclass
class TradePlan:
    trade_id: str
    logical_symbol: str
    broker_symbol: str
    setup: str
    side: str
    box_time: int
    signal_bar_time: int
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    risk: float
    final_rr: float
    lot: float
    reason: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mt5_as_dict(value: Any) -> dict[str, Any]:
    return value._asdict() if hasattr(value, "_asdict") else dict(value or {})


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    tmp.replace(path)


def rates_to_dicts(rates) -> list[dict[str, float]]:
    if rates is None:
        return []
    return [
        {key: (int(value) if key == "time" else float(value)) for key, value in zip(rates.dtype.names, row)}
        for row in rates
    ]


def atr(candles: list[dict[str, float]], period: int = 14) -> float | None:
    if len(candles) <= period:
        return None
    true_ranges: list[float] = []
    for index in range(1, len(candles)):
        high = candles[index]["high"]
        low = candles[index]["low"]
        prev_close = candles[index - 1]["close"]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if len(true_ranges) < period:
        return None
    value = sum(true_ranges[:period]) / period
    for true_range in true_ranges[period:]:
        value = (value * (period - 1) + true_range) / period
    return value


def round_to_digits(value: float, digits: int) -> float:
    return round(float(value), int(digits))


def price_crossed(side: str, price: float, level: float) -> bool:
    return price >= level if side == "BUY" else price <= level


class BoxBot:
    def __init__(self, root: Path, config: dict[str, Any], live_override: bool | None = None) -> None:
        self.root = root
        self.config = config
        self.state_path = root / config.get("state_file", "state/box_bot_state.json")
        self.state = load_json(self.state_path) if self.state_path.exists() else {"symbols": {}, "trades": {}}
        if live_override is not None:
            self.config.setdefault("execution", {})["mode"] = "live" if live_override else "dry_run"

    @property
    def live(self) -> bool:
        return str(self.config.get("execution", {}).get("mode", "dry_run")).lower() == "live"

    @property
    def magic(self) -> int:
        return int(self.config.get("execution", {}).get("magic", 26061740))

    @property
    def comment_prefix(self) -> str:
        return str(self.config.get("execution", {}).get("comment", "boxbot"))[:16]

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
            lot = 0.01
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

    def closed_rates(self, symbol: str, timeframe_name: str, count: int) -> list[dict[str, float]]:
        timeframe = TIMEFRAMES.get(timeframe_name.upper())
        if timeframe is None:
            raise ValueError(f"Unsupported timeframe: {timeframe_name}")
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        candles = rates_to_dicts(rates)
        return candles[:-1] if len(candles) > 1 else []

    def current_tick_prices(self, symbol: str) -> tuple[float, float] | None:
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return None
        return float(tick.bid), float(tick.ask)

    def box_levels(self, logical: str, broker_symbol: str) -> tuple[BoxLevels | None, dict[str, Any]]:
        strategy = self.config.get("strategy", {})
        box_tf = str(self.config.get("box_timeframe", "H4")).upper()
        exec_tf = str(self.config.get("execution_timeframe", "M5")).upper()
        h4_candles = self.closed_rates(broker_symbol, box_tf, 4)
        if len(h4_candles) < 1:
            return None, {"status": "insufficient_h4_candles", "bars": len(h4_candles)}
        box = h4_candles[-1]
        m5_candles = self.closed_rates(broker_symbol, exec_tf, int(strategy.get("atr_period", 14)) + 30)
        atr_value = atr(m5_candles, int(strategy.get("atr_period", 14)))
        tick_prices = self.current_tick_prices(broker_symbol)
        info = mt5.symbol_info(broker_symbol)
        if atr_value is None or not tick_prices or not info:
            return None, {"status": "market_data_unavailable"}
        bid, ask = tick_prices
        spread = abs(ask - bid)
        if atr_value <= 0:
            return None, {"status": "invalid_atr", "atr": atr_value}
        max_spread_ratio = float(strategy.get("max_spread_atr_ratio", 0.35))
        if spread / atr_value > max_spread_ratio:
            return None, {"status": "spread_too_wide", "spread": spread, "atr": atr_value}
        box_high = float(box["high"])
        box_low = float(box["low"])
        box_range = box_high - box_low
        if box_range <= float(info.point or 0.0):
            return None, {"status": "invalid_box_range", "range": box_range}
        stop_buffer = max(
            atr_value * float(strategy.get("stop_buffer_atr", 0.1)),
            spread * float(strategy.get("stop_buffer_spread_mult", 2.0)),
            float(info.point or 0.0) * max(float(info.trade_stops_level or 0.0), 1.0),
        )
        return (
            BoxLevels(
                logical_symbol=logical,
                broker_symbol=broker_symbol,
                box_time=int(box["time"]),
                high=box_high,
                low=box_low,
                mid=(box_high + box_low) / 2.0,
                range=box_range,
                atr=atr_value,
                spread=spread,
                buffer=stop_buffer,
            ),
            {"status": "box"},
        )

    def symbol_state(self, logical: str) -> dict[str, Any]:
        return self.state.setdefault("symbols", {}).setdefault(logical, {})

    def reset_box_state_if_needed(self, logical: str, box: BoxLevels) -> None:
        symbol_state = self.symbol_state(logical)
        if symbol_state.get("box_time") != box.box_time:
            symbol_state.clear()
            symbol_state.update(
                {
                    "box_time": box.box_time,
                    "box_high": box.high,
                    "box_low": box.low,
                    "breakout": None,
                    "updated_at": utc_now(),
                }
            )

    def detect_breakout(self, box: BoxLevels, candle: dict[str, float]) -> str | None:
        strategy = self.config.get("strategy", {})
        breakout_buffer = max(box.atr * float(strategy.get("breakout_close_buffer_atr", 0.1)), box.buffer)
        close = float(candle["close"])
        if close > box.high + breakout_buffer:
            return "UP"
        if close < box.low - breakout_buffer:
            return "DOWN"
        return None

    def build_range_plan(
        self,
        logical: str,
        box: BoxLevels,
        candle: dict[str, float],
        lot: float,
    ) -> tuple[TradePlan | None, dict[str, Any]]:
        strategy = self.config.get("strategy", {})
        info = mt5.symbol_info(box.broker_symbol)
        tick_prices = self.current_tick_prices(box.broker_symbol)
        if not info or not tick_prices:
            return None, {"status": "symbol_info_unavailable"}
        bid, ask = tick_prices
        edge_zone = box.range * float(strategy.get("edge_zone_pct", 0.15))
        require_rejection = bool(strategy.get("require_rejection_candle", True))

        side: str | None = None
        reason = ""
        if float(candle["high"]) >= box.high - edge_zone and float(candle["close"]) <= box.high - box.buffer:
            if not require_rejection or float(candle["close"]) < float(candle["open"]):
                side = "SELL"
                reason = "range_rejection_from_h4_high"
        if float(candle["low"]) <= box.low + edge_zone and float(candle["close"]) >= box.low + box.buffer:
            if not require_rejection or float(candle["close"]) > float(candle["open"]):
                side = "BUY"
                reason = "range_rejection_from_h4_low"

        if side is None:
            return None, {"status": "no_edge_rejection"}

        entry = ask if side == "BUY" else bid
        target = box.high if side == "BUY" else box.low
        reward = (target - entry) if side == "BUY" else (entry - target)
        if reward <= 0:
            return None, {"status": "entry_past_target", "side": side, "entry": entry, "target": target}

        final_rr = float(strategy.get("final_rr", 3.0))
        risk = reward / final_rr
        min_stop = max(float(info.point or 0.0) * max(float(info.trade_stops_level or 0.0), 1.0), box.spread * 2.0)
        if risk < min_stop:
            return None, {"status": "risk_below_broker_min_stop", "risk": risk, "min_stop": min_stop}

        if side == "BUY":
            sl = entry - risk
            if sl > box.low - box.buffer:
                return None, {
                    "status": "sl_not_below_box_low",
                    "entry": round_to_digits(entry, info.digits),
                    "sl": round_to_digits(sl, info.digits),
                    "required_below": round_to_digits(box.low - box.buffer, info.digits),
                }
            tp1 = entry + risk
            tp2 = entry + risk * 2.0
            tp3 = target
        else:
            sl = entry + risk
            if sl < box.high + box.buffer:
                return None, {
                    "status": "sl_not_above_box_high",
                    "entry": round_to_digits(entry, info.digits),
                    "sl": round_to_digits(sl, info.digits),
                    "required_above": round_to_digits(box.high + box.buffer, info.digits),
                }
            tp1 = entry - risk
            tp2 = entry - risk * 2.0
            tp3 = target

        actual_rr = reward / abs(entry - sl)
        if actual_rr < float(strategy.get("min_final_rr", 2.9)):
            return None, {"status": "rr_too_low", "rr": actual_rr}

        return self.make_plan(logical, box, candle, lot, "range", side, entry, sl, tp1, tp2, tp3, risk, actual_rr, reason), {
            "status": "range_plan"
        }

    def build_breakout_retest_plan(
        self,
        logical: str,
        box: BoxLevels,
        candle: dict[str, float],
        lot: float,
        direction: str,
    ) -> tuple[TradePlan | None, dict[str, Any]]:
        strategy = self.config.get("strategy", {})
        info = mt5.symbol_info(box.broker_symbol)
        tick_prices = self.current_tick_prices(box.broker_symbol)
        if not info or not tick_prices:
            return None, {"status": "symbol_info_unavailable"}
        bid, ask = tick_prices
        tolerance = max(box.atr * float(strategy.get("breakout_retest_tolerance_atr", 0.2)), box.buffer)

        if direction == "UP":
            touched_edge = float(candle["low"]) <= box.high + tolerance
            rejected = float(candle["close"]) > box.high and float(candle["close"]) > float(candle["open"])
            if not (touched_edge and rejected):
                return None, {"status": "waiting_for_bullish_retest"}
            side = "BUY"
            entry = ask
            sl = min(box.high, float(candle["low"])) - box.buffer
            reason = "breakout_up_retest_buy"
        else:
            touched_edge = float(candle["high"]) >= box.low - tolerance
            rejected = float(candle["close"]) < box.low and float(candle["close"]) < float(candle["open"])
            if not (touched_edge and rejected):
                return None, {"status": "waiting_for_bearish_retest"}
            side = "SELL"
            entry = bid
            sl = max(box.low, float(candle["high"])) + box.buffer
            reason = "breakout_down_retest_sell"

        risk = abs(entry - sl)
        if risk <= 0:
            return None, {"status": "invalid_breakout_risk", "entry": entry, "sl": sl}
        if risk > box.atr * float(strategy.get("max_breakout_stop_atr", 1.6)):
            return None, {"status": "breakout_stop_too_wide", "risk": risk, "atr": box.atr}

        if side == "BUY":
            tp1 = entry + risk
            tp2 = entry + risk * 2.0
            tp3 = entry + risk * 3.0
        else:
            tp1 = entry - risk
            tp2 = entry - risk * 2.0
            tp3 = entry - risk * 3.0

        return self.make_plan(logical, box, candle, lot, "breakout_retest", side, entry, sl, tp1, tp2, tp3, risk, 3.0, reason), {
            "status": "breakout_retest_plan"
        }

    def make_plan(
        self,
        logical: str,
        box: BoxLevels,
        candle: dict[str, float],
        lot: float,
        setup: str,
        side: str,
        entry: float,
        sl: float,
        tp1: float,
        tp2: float,
        tp3: float,
        risk: float,
        final_rr: float,
        reason: str,
    ) -> TradePlan:
        info = mt5.symbol_info(box.broker_symbol)
        digits = int(info.digits if info else 2)
        signal_bar_time = int(candle["time"])
        trade_id = f"{logical}-{box.box_time}-{signal_bar_time}-{setup}-{side}".replace(" ", "_")
        return TradePlan(
            trade_id=trade_id,
            logical_symbol=logical,
            broker_symbol=box.broker_symbol,
            setup=setup,
            side=side,
            box_time=box.box_time,
            signal_bar_time=signal_bar_time,
            entry=round_to_digits(entry, digits),
            sl=round_to_digits(sl, digits),
            tp1=round_to_digits(tp1, digits),
            tp2=round_to_digits(tp2, digits),
            tp3=round_to_digits(tp3, digits),
            risk=round_to_digits(risk, digits),
            final_rr=round(final_rr, 2),
            lot=lot,
            reason=reason,
        )

    def scan_symbol(self, logical: str, entry: Any) -> dict[str, Any]:
        aliases, requested_lot = self.symbol_config(logical, entry)
        broker_symbol = self.resolve_symbol(logical, aliases)
        if not broker_symbol:
            return {"symbol": logical, "status": "symbol_not_found", "aliases": aliases}

        box, box_status = self.box_levels(logical, broker_symbol)
        if box is None:
            return {"symbol": logical, "broker_symbol": broker_symbol, **box_status}
        self.reset_box_state_if_needed(logical, box)
        symbol_state = self.symbol_state(logical)

        exec_tf = str(self.config.get("execution_timeframe", "M5")).upper()
        m5_candles = self.closed_rates(broker_symbol, exec_tf, 80)
        if len(m5_candles) < 3:
            return {"symbol": logical, "broker_symbol": broker_symbol, "status": "insufficient_m5_candles"}
        candle = m5_candles[-1]
        signal_bar_time = int(candle["time"])

        if not symbol_state.get("bootstrapped") and self.config.get("strategy", {}).get("bootstrap_no_trade", True):
            symbol_state.update({"bootstrapped": True, "last_seen_bar_time": signal_bar_time, "updated_at": utc_now()})
            return {
                "symbol": logical,
                "broker_symbol": broker_symbol,
                "status": "bootstrapped_no_trade",
                "box_high": box.high,
                "box_low": box.low,
            }

        if symbol_state.get("last_signal_bar_time") == signal_bar_time:
            return {"symbol": logical, "broker_symbol": broker_symbol, "status": "signal_bar_already_processed"}

        breakout = self.detect_breakout(box, candle)
        if breakout:
            if symbol_state.get("breakout") != breakout:
                symbol_state.update(
                    {
                        "breakout": breakout,
                        "breakout_bar_time": signal_bar_time,
                        "updated_at": utc_now(),
                    }
                )
                return {
                    "symbol": logical,
                    "broker_symbol": broker_symbol,
                    "status": "breakout_detected_waiting_retest",
                    "breakout": breakout,
                }

        plan: TradePlan | None = None
        details: dict[str, Any]
        active_breakout = symbol_state.get("breakout")
        if active_breakout and self.config.get("strategy", {}).get("breakout_trade_mode", "retest") == "retest":
            plan, details = self.build_breakout_retest_plan(logical, box, candle, requested_lot, str(active_breakout))
        else:
            plan, details = self.build_range_plan(logical, box, candle, requested_lot)

        if plan is None:
            symbol_state.update({"last_seen_bar_time": signal_bar_time, "updated_at": utc_now()})
            return {"symbol": logical, "broker_symbol": broker_symbol, "box_high": box.high, "box_low": box.low, **details}

        symbol_state.update({"last_signal_bar_time": signal_bar_time, "updated_at": utc_now()})
        execution = self.execute_plan(plan)
        return {"symbol": logical, "broker_symbol": broker_symbol, "status": "planned", "plan": asdict(plan), "execution": execution}

    def bot_position(self, position: Any) -> bool:
        data = mt5_as_dict(position)
        comment = str(data.get("comment", ""))
        return int(data.get("magic", 0)) == self.magic or comment.startswith(self.comment_prefix)

    def symbol_positions(self, symbol: str) -> list[Any]:
        positions = list(mt5.positions_get(symbol=symbol) or [])
        return [position for position in positions if self.bot_position(position)]

    def normalize_lot(self, symbol: str, requested: float) -> tuple[float | None, dict[str, Any]]:
        info = mt5.symbol_info(symbol)
        if not info:
            return None, {"error": "symbol_info_missing"}
        step = float(info.volume_step or 0.01)
        min_lot = float(info.volume_min or step)
        max_lot = float(info.volume_max or requested)
        lot = math.floor(float(requested) / step) * step
        lot = round(lot, 8)
        if lot < min_lot:
            return None, {"error": "lot_below_min", "requested": requested, "min_lot": min_lot, "step": step}
        lot = min(lot, max_lot)
        return lot, {"requested": requested, "lot": lot, "min_lot": min_lot, "max_lot": max_lot, "step": step}

    def send_with_filling_modes(self, request_base: dict[str, Any]) -> dict[str, Any]:
        if not self.live:
            return {"ok": True, "dry_run": True, "request": request_base}
        last_error: dict[str, Any] | None = None
        for filling in FILLING_MODES:
            request = dict(request_base)
            request["type_filling"] = filling
            check = mt5.order_check(request)
            check_data = mt5_as_dict(check) if check else {"retcode": None, "comment": "no check result"}
            if check_data.get("retcode") != 0:
                last_error = {
                    "stage": "check",
                    "retcode": check_data.get("retcode"),
                    "comment": check_data.get("comment"),
                    "filling": filling,
                }
                continue
            result = mt5.order_send(request)
            result_data = mt5_as_dict(result) if result else {"retcode": None, "comment": "no send result"}
            if result_data.get("retcode") in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
                return {
                    "ok": True,
                    "order": result_data.get("order"),
                    "deal": result_data.get("deal"),
                    "retcode": result_data.get("retcode"),
                    "comment": result_data.get("comment"),
                    "request": request,
                }
            last_error = {
                "stage": "send",
                "retcode": result_data.get("retcode"),
                "comment": result_data.get("comment"),
                "filling": filling,
            }
        return {"ok": False, "error": last_error or "unknown_order_error", "request": request_base}

    def execute_plan(self, plan: TradePlan) -> dict[str, Any]:
        if self.config.get("execution", {}).get("skip_if_symbol_has_bot_positions", True):
            open_positions = self.symbol_positions(plan.broker_symbol)
            if open_positions:
                return {"ok": False, "status": "symbol_has_existing_bot_positions", "count": len(open_positions)}

        lot, lot_info = self.normalize_lot(plan.broker_symbol, plan.lot)
        if lot is None:
            return {"ok": False, "status": "lot_invalid", **lot_info}

        tick_prices = self.current_tick_prices(plan.broker_symbol)
        if not tick_prices:
            return {"ok": False, "status": "tick_unavailable"}
        bid, ask = tick_prices
        order_type = mt5.ORDER_TYPE_BUY if plan.side == "BUY" else mt5.ORDER_TYPE_SELL
        price = ask if plan.side == "BUY" else bid
        tps = [plan.tp1, plan.tp2, plan.tp3]
        results = []
        for index, tp in enumerate(tps, start=1):
            comment = f"{self.comment_prefix} {plan.setup[:4]} L{index}"[:31]
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": plan.broker_symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "sl": plan.sl,
                "tp": tp,
                "deviation": int(self.config.get("execution", {}).get("deviation_points", 30)),
                "magic": self.magic,
                "comment": comment,
            }
            result = self.send_with_filling_modes(request)
            result["leg"] = index
            result["tp"] = tp
            results.append(result)

        self.state.setdefault("trades", {})[plan.trade_id] = {
            "active": True,
            "created_at": utc_now(),
            "plan": asdict(plan),
            "legs": [
                {
                    "leg": result["leg"],
                    "ticket": result.get("order"),
                    "deal": result.get("deal"),
                    "tp": result["tp"],
                    "dry_run": bool(result.get("dry_run", False)),
                }
                for result in results
            ],
            "tp1_hit": False,
            "be_moved": False,
        }
        return {"ok": all(bool(result.get("ok")) for result in results), "lot": lot, "lot_info": lot_info, "legs": results}

    def modify_position_sl(self, position: Any, sl: float, tp: float) -> dict[str, Any]:
        data = mt5_as_dict(position)
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": data["symbol"],
            "position": int(data["ticket"]),
            "sl": sl,
            "tp": tp,
            "magic": self.magic,
            "comment": f"{self.comment_prefix} BE"[:31],
        }
        if not self.live:
            return {"ok": True, "dry_run": True, "request": request}
        result = mt5.order_send(request)
        result_data = mt5_as_dict(result) if result else {"retcode": None, "comment": "no send result"}
        return {
            "ok": result_data.get("retcode") in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED),
            "retcode": result_data.get("retcode"),
            "comment": result_data.get("comment"),
            "request": request,
        }

    def manage_open_trades(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if not self.config.get("execution", {}).get("move_sl_to_entry_at_tp1", True):
            return events

        for trade_id, trade in list(self.state.setdefault("trades", {}).items()):
            if not trade.get("active"):
                continue
            plan = trade.get("plan", {})
            symbol = str(plan.get("broker_symbol"))
            side = str(plan.get("side"))
            positions = self.symbol_positions(symbol)
            open_by_ticket = {int(mt5_as_dict(position)["ticket"]): position for position in positions}
            known_tickets = [int(leg["ticket"]) for leg in trade.get("legs", []) if leg.get("ticket")]
            open_known = [ticket for ticket in known_tickets if ticket in open_by_ticket]
            if known_tickets and not open_known:
                trade["active"] = False
                trade["closed_at"] = utc_now()
                events.append({"trade_id": trade_id, "status": "all_legs_closed"})
                continue

            tick_prices = self.current_tick_prices(symbol)
            if not tick_prices:
                continue
            bid, ask = tick_prices
            current = bid if side == "BUY" else ask
            tp1 = float(plan["tp1"])
            tp1_ticket = next((int(leg["ticket"]) for leg in trade.get("legs", []) if leg.get("leg") == 1 and leg.get("ticket")), None)
            tp1_closed = bool(tp1_ticket and tp1_ticket not in open_by_ticket)
            tp1_hit = bool(trade.get("tp1_hit")) or tp1_closed or price_crossed(side, current, tp1)
            if not tp1_hit:
                continue
            trade["tp1_hit"] = True
            if trade.get("be_moved"):
                continue

            info = mt5.symbol_info(symbol)
            if not info:
                continue
            offset_points = float(self.config.get("execution", {}).get("break_even_offset_points", 0))
            point = float(info.point or 0.0)
            entry = float(plan["entry"])
            be = entry + offset_points * point if side == "BUY" else entry - offset_points * point
            be = round_to_digits(be, int(info.digits))
            moves = []
            for leg in trade.get("legs", []):
                if int(leg.get("leg", 0)) <= 1 or not leg.get("ticket"):
                    continue
                ticket = int(leg["ticket"])
                position = open_by_ticket.get(ticket)
                if not position:
                    continue
                data = mt5_as_dict(position)
                old_sl = float(data.get("sl", 0.0))
                tp = float(data.get("tp", leg.get("tp", 0.0)))
                should_move = old_sl == 0.0 or (side == "BUY" and old_sl < be) or (side == "SELL" and old_sl > be)
                if should_move:
                    moves.append({"ticket": ticket, "result": self.modify_position_sl(position, be, tp)})
            trade["be_moved"] = True
            trade["be_moved_at"] = utc_now()
            trade["be_price"] = be
            events.append({"trade_id": trade_id, "status": "moved_remaining_legs_to_be", "moves": moves})
        return events

    def run_cycle(self) -> dict[str, Any]:
        output: dict[str, Any] = {"time": utc_now(), "mode": "live" if self.live else "dry_run", "management": [], "symbols": []}
        output["management"] = self.manage_open_trades()
        for logical, entry in self.config.get("symbols", {}).items():
            try:
                output["symbols"].append(self.scan_symbol(logical, entry))
            except Exception as exc:
                output["symbols"].append({"symbol": logical, "status": "error", "error": repr(exc)})
        save_json(self.state_path, self.state)
        return output


def print_result(result: dict[str, Any]) -> None:
    print(json.dumps(result, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="H4 box fade/breakout MT5 bot.")
    parser.add_argument("--config", default="config.json", help="Config JSON path.")
    parser.add_argument("--once", action="store_true", help="Run one scan cycle.")
    parser.add_argument("--loop", action="store_true", help="Keep scanning.")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run mode.")
    parser.add_argument("--live", action="store_true", help="Force live trading mode.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = load_json(config_path)
    live_override = True if args.live else False if args.dry_run else None
    bot = BoxBot(root, config, live_override=live_override)

    bot.connect()
    try:
        if args.loop:
            while True:
                print_result(bot.run_cycle())
                time.sleep(float(config.get("poll_seconds", 10)))
        else:
            print_result(bot.run_cycle())
    finally:
        bot.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
