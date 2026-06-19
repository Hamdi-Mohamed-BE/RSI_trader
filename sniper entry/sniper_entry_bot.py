from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
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
class Signal:
    logical_symbol: str
    broker_symbol: str
    side: str
    bar_time: int
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    tp4: float
    tp5: float
    risk_unit: float
    bull_pct: float
    bear_pct: float
    bias: str
    atr: float
    spread: float


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def as_dict(value: Any) -> dict[str, Any]:
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


def ema_series(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = []
    ema_value: float | None = None
    weight = 2.0 / (period + 1)
    for value in values:
        ema_value = value if ema_value is None else value * weight + ema_value * (1 - weight)
        out.append(ema_value)
    return out


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi_series(values: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return out
    gains = []
    losses = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0)
        loss = max(-change, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[index] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return out


def atr_series(candles: list[dict[str, float]], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(candles)
    if len(candles) <= period:
        return out
    true_ranges = [0.0]
    for index in range(1, len(candles)):
        high = candles[index]["high"]
        low = candles[index]["low"]
        prev_close = candles[index - 1]["close"]
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    atr_value = sum(true_ranges[1 : period + 1]) / period
    out[period] = atr_value
    for index in range(period + 1, len(candles)):
        atr_value = (atr_value * (period - 1) + true_ranges[index]) / period
        out[index] = atr_value
    return out


def macd_values(values: list[float]) -> tuple[list[float | None], list[float | None]]:
    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)
    macd_line: list[float | None] = [
        (fast - slow) if fast is not None and slow is not None else None for fast, slow in zip(ema12, ema26)
    ]
    compact = [value for value in macd_line if value is not None]
    compact_signal = ema_series(compact, 9)
    signal_line: list[float | None] = []
    compact_index = 0
    for value in macd_line:
        if value is None:
            signal_line.append(None)
        else:
            signal_line.append(compact_signal[compact_index])
            compact_index += 1
    return macd_line, signal_line


def adx_series(candles: list[dict[str, float]], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(candles)
    if len(candles) <= period * 2:
        return out
    tr = [0.0]
    plus_dm = [0.0]
    minus_dm = [0.0]
    for index in range(1, len(candles)):
        up_move = candles[index]["high"] - candles[index - 1]["high"]
        down_move = candles[index - 1]["low"] - candles[index]["low"]
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        tr.append(
            max(
                candles[index]["high"] - candles[index]["low"],
                abs(candles[index]["high"] - candles[index - 1]["close"]),
                abs(candles[index]["low"] - candles[index - 1]["close"]),
            )
        )
    tr_smooth = sum(tr[1 : period + 1])
    plus_smooth = sum(plus_dm[1 : period + 1])
    minus_smooth = sum(minus_dm[1 : period + 1])
    dx_values: list[float | None] = [None] * len(candles)
    for index in range(period, len(candles)):
        if index > period:
            tr_smooth = tr_smooth - (tr_smooth / period) + tr[index]
            plus_smooth = plus_smooth - (plus_smooth / period) + plus_dm[index]
            minus_smooth = minus_smooth - (minus_smooth / period) + minus_dm[index]
        if tr_smooth == 0:
            dx_values[index] = 0.0
            continue
        plus_di = 100.0 * plus_smooth / tr_smooth
        minus_di = 100.0 * minus_smooth / tr_smooth
        denom = plus_di + minus_di
        dx_values[index] = 0.0 if denom == 0 else 100.0 * abs(plus_di - minus_di) / denom
    first_adx_index = period * 2
    first_dx = [value for value in dx_values[period : first_adx_index + 1] if value is not None]
    if len(first_dx) < period:
        return out
    adx_value = sum(first_dx[-period:]) / period
    out[first_adx_index] = adx_value
    for index in range(first_adx_index + 1, len(candles)):
        if dx_values[index] is not None:
            adx_value = (adx_value * (period - 1) + dx_values[index]) / period
            out[index] = adx_value
    return out


def session_vwap(candles: list[dict[str, float]], index: int) -> float | None:
    if index < 0 or index >= len(candles):
        return None
    target_date = datetime.fromtimestamp(candles[index]["time"], timezone.utc).date()
    pv_sum = 0.0
    volume_sum = 0.0
    for candle in candles:
        candle_date = datetime.fromtimestamp(candle["time"], timezone.utc).date()
        if candle_date != target_date:
            continue
        typical = (candle["high"] + candle["low"] + candle["close"]) / 3.0
        volume = max(candle.get("tick_volume", 0.0), 1.0)
        pv_sum += typical * volume
        volume_sum += volume
        if candle["time"] == candles[index]["time"]:
            break
    return pv_sum / volume_sum if volume_sum else None


def reconstruct_signal_state(ema9: list[float | None], ema21: list[float | None], end_index: int) -> int:
    state = 0
    for index in range(1, max(1, end_index + 1)):
        if None in (ema9[index - 1], ema21[index - 1], ema9[index], ema21[index]):
            continue
        cross_up = ema9[index - 1] <= ema21[index - 1] and ema9[index] > ema21[index]
        cross_down = ema9[index - 1] >= ema21[index - 1] and ema9[index] < ema21[index]
        if cross_up and state <= 0:
            state = 1
        elif cross_down and state >= 0:
            state = -1
    return state


class SniperBot:
    def __init__(self, root: Path, config: dict[str, Any], live_override: bool | None = None) -> None:
        self.root = root
        self.config = config
        self.state_path = root / config.get("state_file", "state/sniper_state.json")
        self.state = load_json(self.state_path) if self.state_path.exists() else {"symbols": {}, "trades": {}}
        if live_override is not None:
            self.config.setdefault("execution", {})["mode"] = "live" if live_override else "dry_run"

    @property
    def live(self) -> bool:
        return self.config.get("execution", {}).get("mode", "live").lower() == "live"

    def connect(self) -> None:
        mt5_path = self.config.get("mt5_path")
        ok = mt5.initialize(path=mt5_path) if mt5_path else mt5.initialize()
        if not ok:
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    def shutdown(self) -> None:
        mt5.shutdown()

    def resolve_symbol(self, logical: str, aliases: list[str]) -> str | None:
        names = [symbol.name for symbol in (mt5.symbols_get() or [])]
        candidates: list[str] = []
        for alias in aliases:
            if alias in names and alias not in candidates:
                candidates.append(alias)
        for alias in aliases:
            upper = alias.upper()
            for name in names:
                if name.upper().startswith(upper) and name not in candidates:
                    candidates.append(name)
        best_name = None
        best_score = -1
        for name in candidates:
            mt5.symbol_select(name, True)
            time.sleep(0.05)
            info = mt5.symbol_info(name)
            tick = mt5.symbol_info_tick(name)
            if not info:
                continue
            score = 0
            if getattr(info, "trade_mode", 0) == mt5.SYMBOL_TRADE_MODE_FULL:
                score += 100
            if tick and tick.bid and tick.ask:
                score += 20
            if getattr(info, "visible", False):
                score += 5
            if "VIP" in name.upper():
                score += 3
            if score > best_score:
                best_name = name
                best_score = score
        if best_name:
            mt5.symbol_select(best_name, True)
        return best_name

    def get_closed_rates(self, symbol: str, timeframe: int, count: int = 300) -> list[dict[str, float]]:
        raw = rates_to_dicts(mt5.copy_rates_from_pos(symbol, timeframe, 0, count))
        return raw[:-1] if len(raw) > 1 else raw

    def duplicate_exposure(self, broker_symbol: str) -> list[dict[str, Any]]:
        if not self.config.get("execution", {}).get("skip_if_any_symbol_exposure", True):
            return []
        found: list[dict[str, Any]] = []
        for position in mt5.positions_get(symbol=broker_symbol) or []:
            data = as_dict(position)
            found.append({"kind": "position", "ticket": int(data["ticket"]), "side": "BUY" if int(data["type"]) == mt5.POSITION_TYPE_BUY else "SELL", "volume": float(data["volume"])})
        for order in mt5.orders_get(symbol=broker_symbol) or []:
            data = as_dict(order)
            found.append({"kind": "order", "ticket": int(data["ticket"]), "type": int(data["type"]), "volume": float(data["volume_current"])})
        return found

    def analyze(self, logical: str, broker_symbol: str) -> tuple[Signal | None, dict[str, Any]]:
        timeframe_name = self.config.get("timeframe", "H4")
        timeframe = TIMEFRAMES[timeframe_name]
        candles = self.get_closed_rates(broker_symbol, timeframe)
        five_minute = self.get_closed_rates(broker_symbol, mt5.TIMEFRAME_M5)
        if len(candles) < 80 or len(five_minute) < 30:
            return None, {"status": "not_enough_data", "bars": len(candles), "m5_bars": len(five_minute)}

        closes = [candle["close"] for candle in candles]
        volumes = [candle.get("tick_volume", 0.0) for candle in candles]
        ema9 = ema_series(closes, 9)
        ema21 = ema_series(closes, 21)
        atr14 = atr_series(candles, 14)
        rsi14 = rsi_series(closes, 14)
        rsi5m = rsi_series([candle["close"] for candle in five_minute], 14)[-1]
        macd_line, macd_signal = macd_values(closes)
        adx = adx_series(candles, 14)
        index = len(candles) - 1
        prev = index - 1
        if any(value is None for value in (ema9[prev], ema21[prev], ema9[index], ema21[index], atr14[index], rsi14[index], rsi5m, macd_line[index], macd_signal[index], adx[index])):
            return None, {"status": "indicators_not_ready"}

        tick = mt5.symbol_info_tick(broker_symbol)
        info = mt5.symbol_info(broker_symbol)
        if not tick or not info:
            return None, {"status": "no_tick"}

        spread = float(tick.ask - tick.bid)
        vwap = session_vwap(candles, index)
        vol_avg = sma(volumes, 20)
        close = closes[index]
        open_price = candles[index]["open"]

        bull_score = 0
        bull_score += 1 if vwap is not None and close > vwap else 0
        bull_score += 1 if rsi14[index] > 50 else 0
        bull_score += 1 if macd_line[index] > macd_signal[index] else 0
        bull_score += 1 if ema9[index] > ema21[index] else 0
        bull_score += 1 if adx[index] > 25 and close > ema9[index] else 0
        bull_score += 1 if vol_avg and volumes[index] > vol_avg and close > open_price else 0
        bull_score += 1 if rsi5m > 50 else 0
        bear_score = 0
        bear_score += 1 if vwap is not None and close < vwap else 0
        bear_score += 1 if rsi14[index] < 50 else 0
        bear_score += 1 if macd_line[index] < macd_signal[index] else 0
        bear_score += 1 if ema9[index] < ema21[index] else 0
        bear_score += 1 if adx[index] > 25 and close < ema9[index] else 0
        bear_score += 1 if vol_avg and volumes[index] > vol_avg and close < open_price else 0
        bear_score += 1 if rsi5m < 50 else 0
        bull_pct = bull_score / 7.0 * 100.0
        bear_pct = bear_score / 7.0 * 100.0
        bias = "STRONG BULL" if bull_pct - bear_pct >= 40 else "STRONG BEAR" if bear_pct - bull_pct >= 40 else "MILD BULL" if bull_pct > bear_pct else "MILD BEAR"

        spread_ratio = spread / atr14[index] if atr14[index] else 999.0
        max_spread_ratio = float(self.config.get("strategy", {}).get("max_spread_atr_ratio", 0.35))
        if spread_ratio > max_spread_ratio:
            return None, {
                "status": "spread_wide",
                "spread": round(spread, info.digits),
                "atr": round(float(atr14[index]), info.digits),
                "spread_atr": round(spread_ratio, 2),
                "bias": bias,
            }

        state_before = reconstruct_signal_state(ema9, ema21, prev)
        saved = self.state.setdefault("symbols", {}).get(logical)
        if saved:
            state_before = int(saved.get("signal_state", state_before))
        bar_time = int(candles[index]["time"])
        if saved and int(saved.get("last_bar_time", 0)) >= bar_time:
            return None, {"status": "already_processed", "bar_time": bar_time, "bias": bias, "bull_pct": round(bull_pct), "bear_pct": round(bear_pct)}

        cross_up = ema9[prev] <= ema21[prev] and ema9[index] > ema21[index]
        cross_down = ema9[prev] >= ema21[prev] and ema9[index] < ema21[index]
        trigger_buy = cross_up and state_before <= 0
        trigger_sell = cross_down and state_before >= 0
        state_after = 1 if trigger_buy else -1 if trigger_sell else state_before

        age_minutes = (datetime.now(timezone.utc).timestamp() - bar_time) / 60.0
        max_age = float(self.config.get("strategy", {}).get("max_signal_age_minutes", 25))
        if age_minutes > max_age:
            self.update_symbol_state(logical, bar_time, state_after)
            return None, {"status": "stale_bar", "age_minutes": round(age_minutes, 1), "bias": bias}

        if not saved and self.config.get("strategy", {}).get("bootstrap_no_trade", True):
            self.update_symbol_state(logical, bar_time, state_after)
            return None, {"status": "bootstrapped_no_trade", "bar_time": bar_time, "signal_state": state_after, "bias": bias}

        if not (trigger_buy or trigger_sell):
            self.update_symbol_state(logical, bar_time, state_after)
            return None, {"status": "no_cross", "bias": bias, "bull_pct": round(bull_pct), "bear_pct": round(bear_pct)}

        side = "BUY" if trigger_buy else "SELL"
        risk_unit = float(atr14[index]) * float(self.config.get("strategy", {}).get("atr_multiplier", 1.5))
        entry = float(tick.ask if side == "BUY" else tick.bid)
        if side == "BUY":
            sl = entry - risk_unit
            tp1, tp2, tp3, tp4, tp5 = [entry + risk_unit * multiple for multiple in (1, 2, 3, 4, 5)]
        else:
            sl = entry + risk_unit
            tp1, tp2, tp3, tp4, tp5 = [entry - risk_unit * multiple for multiple in (1, 2, 3, 4, 5)]

        signal = Signal(
            logical_symbol=logical,
            broker_symbol=broker_symbol,
            side=side,
            bar_time=bar_time,
            entry=round(entry, info.digits),
            sl=round(sl, info.digits),
            tp1=round(tp1, info.digits),
            tp2=round(tp2, info.digits),
            tp3=round(tp3, info.digits),
            tp4=round(tp4, info.digits),
            tp5=round(tp5, info.digits),
            risk_unit=risk_unit,
            bull_pct=bull_pct,
            bear_pct=bear_pct,
            bias=bias,
            atr=float(atr14[index]),
            spread=spread,
        )
        self.update_symbol_state(logical, bar_time, state_after)
        return signal, {"status": "signal", "side": side, "bias": bias, "bull_pct": round(bull_pct), "bear_pct": round(bear_pct)}

    def update_symbol_state(self, logical: str, bar_time: int, signal_state: int) -> None:
        self.state.setdefault("symbols", {})[logical] = {
            "last_bar_time": int(bar_time),
            "signal_state": int(signal_state),
            "updated_at": utc_now(),
        }

    def calc_lot(self, signal: Signal, balance: float) -> tuple[float | None, dict[str, Any]]:
        info = mt5.symbol_info(signal.broker_symbol)
        if not info:
            return None, {"error": "risk_unavailable"}
        risk_cfg = self.config.get("risk", {})
        risk_pct = float(risk_cfg.get("balance_risk_pct", 5.0))
        if balance <= 0 or risk_pct <= 0:
            return None, {"error": "risk_budget_invalid", "balance": round(balance, 2), "balance_risk_pct": risk_pct}

        cap = balance * risk_pct / 100.0
        order_type = mt5.ORDER_TYPE_BUY if signal.side == "BUY" else mt5.ORDER_TYPE_SELL
        risk_calc = mt5.order_calc_profit(order_type, signal.broker_symbol, 1.0, signal.entry, signal.sl)
        risk_per_lot = abs(float(risk_calc or 0.0))
        risk_method = "mt5_order_calc_profit"
        if risk_per_lot <= 0:
            if not info.trade_tick_size or not info.trade_tick_value:
                return None, {"error": "risk_unavailable", "balance": round(balance, 2), "balance_risk_pct": risk_pct}
            distance = abs(signal.entry - signal.sl)
            risk_per_lot = distance / info.trade_tick_size * info.trade_tick_value
            risk_method = "tick_value_fallback"
        if risk_per_lot <= 0:
            return None, {"error": "risk_per_lot_zero"}
        step = float(info.volume_step or 0.01)
        min_lot = float(info.volume_min or step)
        max_lot = float(info.volume_max or 100.0)
        raw = cap / risk_per_lot
        lot = math.floor(raw / step) * step
        lot = round(min(max_lot, lot), 4)
        if lot < min_lot:
            min_risk = risk_per_lot * min_lot
            return None, {
                "error": "min_lot_exceeds_cap",
                "risk_model": "balance_percent",
                "balance": round(balance, 2),
                "balance_risk_pct": risk_pct,
                "risk_cap": round(cap, 2),
                "min_lot": min_lot,
                "min_lot_risk": round(min_risk, 2),
                "risk_method": risk_method,
            }
        risk = risk_per_lot * lot
        return lot, {
            "risk_model": "balance_percent",
            "balance": round(balance, 2),
            "balance_risk_pct": risk_pct,
            "risk_cap": round(cap, 2),
            "risk_per_lot": round(risk_per_lot, 2),
            "dollar_risk": round(risk, 2),
            "risk_pct": round(risk / balance * 100.0, 2) if balance else None,
            "risk_method": risk_method,
        }

    def manage_positions(self) -> list[dict[str, Any]]:
        if not self.config.get("execution", {}).get("manage_virtual_targets", True):
            return []
        magic = int(self.config.get("execution", {}).get("magic", 26061515))
        actions: list[dict[str, Any]] = []
        for position in mt5.positions_get() or []:
            data = as_dict(position)
            if int(data.get("magic", 0) or 0) != magic and not str(data.get("comment", "")).startswith("SNIP"):
                continue
            symbol = data["symbol"]
            side = "BUY" if int(data["type"]) == mt5.POSITION_TYPE_BUY else "SELL"
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if not info or not tick:
                continue
            entry = float(data["price_open"])
            old_sl = float(data.get("sl") or 0)
            tp = float(data.get("tp") or 0)
            if old_sl <= 0 or tp <= 0:
                actions.append({"ticket": int(data["ticket"]), "action": "review", "reason": "missing_sl_tp"})
                continue
            final_distance = abs(tp - entry)
            risk_unit = final_distance / 5.0
            tp1 = entry + risk_unit if side == "BUY" else entry - risk_unit
            tp2 = entry + 2 * risk_unit if side == "BUY" else entry - 2 * risk_unit
            price = float(tick.bid if side == "BUY" else tick.ask)
            spread = float(tick.ask - tick.bid)
            buffer = max(spread * 1.5, (info.point or 0.01) * 10)
            desired_sl = None
            reason = None
            if side == "BUY":
                if price >= tp2 and self.config.get("execution", {}).get("move_sl_to_tp1_at_tp2", True):
                    desired_sl = tp1
                    reason = "tp2_lock_tp1"
                elif price >= tp1 and self.config.get("execution", {}).get("move_sl_to_entry_at_tp1", True):
                    desired_sl = entry + buffer
                    reason = "tp1_lock_entry"
                if desired_sl is not None and desired_sl <= old_sl:
                    desired_sl = None
            else:
                if price <= tp2 and self.config.get("execution", {}).get("move_sl_to_tp1_at_tp2", True):
                    desired_sl = tp1
                    reason = "tp2_lock_tp1"
                elif price <= tp1 and self.config.get("execution", {}).get("move_sl_to_entry_at_tp1", True):
                    desired_sl = entry - buffer
                    reason = "tp1_lock_entry"
                if desired_sl is not None and desired_sl >= old_sl:
                    desired_sl = None
            if desired_sl is None:
                continue
            new_sl = round(desired_sl, info.digits)
            request = {"action": mt5.TRADE_ACTION_SLTP, "position": int(data["ticket"]), "symbol": symbol, "sl": new_sl, "tp": tp}
            if not self.live:
                actions.append({"ticket": int(data["ticket"]), "action": "dry_manage_sl", "old_sl": old_sl, "new_sl": new_sl, "reason": reason})
                continue
            result = mt5.order_send(request)
            result_data = as_dict(result) if result else {"retcode": None, "comment": "no result"}
            actions.append({"ticket": int(data["ticket"]), "action": "modify_sl", "old_sl": old_sl, "new_sl": new_sl, "reason": reason, "retcode": result_data.get("retcode"), "comment": result_data.get("comment")})
        return actions

    def place_signal(self, signal: Signal, lot: float) -> dict[str, Any]:
        info = mt5.symbol_info(signal.broker_symbol)
        if not info:
            return {"ok": False, "error": "symbol_info_missing"}
        order_type = mt5.ORDER_TYPE_BUY if signal.side == "BUY" else mt5.ORDER_TYPE_SELL
        tp = signal.tp5
        request_base = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.broker_symbol,
            "volume": lot,
            "type": order_type,
            "price": signal.entry,
            "sl": signal.sl,
            "tp": tp,
            "deviation": int(self.config.get("execution", {}).get("deviation_points", 30)),
            "magic": int(self.config.get("execution", {}).get("magic", 26061515)),
            "comment": f"SNIP {signal.logical_symbol[:5]} {signal.side[0]} {self.config.get('timeframe', 'H4')}"[:31],
        }
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
                return {"ok": True, "order": result_data.get("order"), "deal": result_data.get("deal"), "retcode": result_data.get("retcode"), "comment": result_data.get("comment"), "request": request}
            last_error = {"stage": "send", "retcode": result_data.get("retcode"), "comment": result_data.get("comment"), "filling": filling}
        return {"ok": False, "error": last_error or "unknown_order_error", "request": request_base}

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
                "account": {
                    "login": int(account.login),
                    "balance": round(float(account.balance), 2),
                    "equity": round(float(account.equity), 2),
                    "free_margin": round(float(account.margin_free), 2),
                    "trade_allowed": bool(account.trade_allowed),
                    "terminal_trade_allowed": bool(terminal.trade_allowed),
                },
                "management_actions": self.manage_positions(),
                "symbols": [],
                "signals": [],
                "orders": [],
            }
            can_trade = bool(account.trade_allowed) and bool(terminal.trade_allowed)
            for logical, aliases in self.config.get("symbols", {}).items():
                broker_symbol = self.resolve_symbol(logical, aliases)
                row: dict[str, Any] = {"logical": logical, "broker": broker_symbol}
                if not broker_symbol:
                    row["status"] = "symbol_not_found"
                    output["symbols"].append(row)
                    continue
                duplicates = self.duplicate_exposure(broker_symbol)
                signal, note = self.analyze(logical, broker_symbol)
                row.update(note)
                row["duplicates"] = duplicates
                if signal is None:
                    output["symbols"].append(row)
                    continue
                output["signals"].append(signal.__dict__)
                if duplicates:
                    row["status"] = "signal_skipped_duplicate_exposure"
                    output["symbols"].append(row)
                    continue
                lot, risk = self.calc_lot(signal, float(account.balance))
                row["risk"] = risk
                if lot is None:
                    row["status"] = "signal_skipped_risk"
                    output["symbols"].append(row)
                    continue
                if not can_trade:
                    row["status"] = "signal_skipped_trade_not_allowed"
                    output["symbols"].append(row)
                    continue
                order_result = self.place_signal(signal, lot)
                row["lot"] = lot
                row["order_result"] = order_result
                output["orders"].append({"logical": logical, "broker": broker_symbol, "side": signal.side, "lot": lot, "risk": risk, "result": order_result})
                output["symbols"].append(row)
            if write_state:
                save_json(self.state_path, self.state)
            return output
        finally:
            self.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MT5 bot for the KhanSaab Sniper EMA-cross strategy.")
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
    bot = SniperBot(root, config, live_override=live_override)
    if args.loop:
        while True:
            result = bot.run_once(write_state=not args.no_state_write)
            print(json.dumps(result, indent=2))
            time.sleep(int(config.get("poll_seconds", 60)))
    else:
        result = bot.run_once(write_state=not args.no_state_write)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
