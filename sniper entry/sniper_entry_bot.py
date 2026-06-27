from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, time as datetime_time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


def parse_hhmm(value: str, default: str = "00:00") -> datetime_time:
    raw = str(value or default).strip() or default
    try:
        hour, minute = raw.split(":", 1)
        return datetime_time(hour=int(hour), minute=int(minute))
    except (TypeError, ValueError):
        hour, minute = default.split(":", 1)
        return datetime_time(hour=int(hour), minute=int(minute))


class NewYorkFallbackZone(tzinfo):
    """Small Windows-safe fallback when Python's IANA tzdata is unavailable."""

    @staticmethod
    def _nth_weekday(year: int, month: int, weekday: int, n: int) -> int:
        first = datetime(year, month, 1)
        return 1 + ((weekday - first.weekday()) % 7) + (n - 1) * 7

    @classmethod
    def _transition_utc(cls, year: int) -> tuple[datetime, datetime]:
        dst_start_day = cls._nth_weekday(year, 3, 6, 2)
        dst_end_day = cls._nth_weekday(year, 11, 6, 1)
        return datetime(year, 3, dst_start_day, 7), datetime(year, 11, dst_end_day, 6)

    @classmethod
    def _transition_local(cls, year: int) -> tuple[datetime, datetime]:
        dst_start_day = cls._nth_weekday(year, 3, 6, 2)
        dst_end_day = cls._nth_weekday(year, 11, 6, 1)
        return datetime(year, 3, dst_start_day, 2), datetime(year, 11, dst_end_day, 2)

    def _is_dst_local(self, dt: datetime | None) -> bool:
        if dt is None:
            return False
        value = dt.replace(tzinfo=None)
        start, end = self._transition_local(value.year)
        return start <= value < end

    def utcoffset(self, dt: datetime | None) -> timedelta:
        return timedelta(hours=-4 if self._is_dst_local(dt) else -5)

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(hours=1 if self._is_dst_local(dt) else 0)

    def tzname(self, dt: datetime | None) -> str:
        return "EDT" if self._is_dst_local(dt) else "EST"

    def fromutc(self, dt: datetime) -> datetime:
        if dt.tzinfo is not self:
            raise ValueError("fromutc: dt.tzinfo is not self")
        value = dt.replace(tzinfo=None)
        start, end = self._transition_utc(value.year)
        offset = timedelta(hours=-4 if start <= value < end else -5)
        return (value + offset).replace(tzinfo=self)


def safe_zone(name: str | None, default: str = "America/New_York") -> tzinfo:
    selected = (name or default).strip() or default
    try:
        return ZoneInfo(selected)
    except ZoneInfoNotFoundError:
        pass
    try:
        return ZoneInfo(default)
    except ZoneInfoNotFoundError:
        if selected in {"America/New_York", "US/Eastern"} or default in {"America/New_York", "US/Eastern"}:
            return NewYorkFallbackZone()
        if selected.upper() == "UTC" or default.upper() == "UTC":
            return timezone.utc
        return timezone.utc


def minutes_of_day(value: datetime_time) -> int:
    return value.hour * 60 + value.minute


def session_contains(now_local: datetime, start: str, end: str) -> bool:
    current = now_local.hour * 60 + now_local.minute
    start_minutes = minutes_of_day(parse_hhmm(start, "00:00"))
    end_minutes = minutes_of_day(parse_hhmm(end, "23:59"))
    if end_minutes <= start_minutes:
        return current >= start_minutes or current <= end_minutes
    return start_minutes <= current <= end_minutes


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

    def guardrail_config(self) -> dict[str, Any]:
        return self.config.get("guardrails", {}) or {}

    def session_gate(self, now_utc: datetime | None = None) -> tuple[bool, list[str], dict[str, Any]]:
        guardrails = self.guardrail_config()
        if not guardrails.get("enabled", True):
            return True, [], {"enabled": False}
        timezone_name = str(guardrails.get("timezone", "America/New_York"))
        zone = safe_zone(timezone_name)
        now_local = (now_utc or datetime.now(timezone.utc)).astimezone(zone)
        reasons: list[str] = []
        weekdays = [str(item).strip().lower()[:3] for item in guardrails.get("allowed_weekdays", [])]
        if weekdays and now_local.strftime("%a").lower()[:3] not in weekdays:
            reasons.append(f"weekday_block:{now_local.strftime('%a')}")
        sessions = guardrails.get("sessions", [])
        session_hits = []
        if sessions:
            for session in sessions:
                if session_contains(now_local, str(session.get("start", "00:00")), str(session.get("end", "23:59"))):
                    session_hits.append(str(session.get("name", "session")))
            if not session_hits:
                reasons.append("outside_allowed_session")
        return not reasons, reasons, {
            "timezone": timezone_name,
            "local_time": now_local.replace(microsecond=0).isoformat(),
            "session_hits": session_hits,
        }

    def bot_deals_since(self, start: datetime, end: datetime | None = None) -> list[dict[str, Any]]:
        end = end or datetime.now(timezone.utc)
        magic = int(self.config.get("execution", {}).get("magic", 26061515))
        rows: list[dict[str, Any]] = []
        for deal in mt5.history_deals_get(start, end) or []:
            data = as_dict(deal)
            comment = str(data.get("comment", ""))
            if int(data.get("magic", 0) or 0) == magic or comment.startswith("SNIP"):
                rows.append(data)
        return rows

    def bot_closed_trades(self, days: int = 30) -> list[dict[str, Any]]:
        start = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
        grouped: dict[str, dict[str, Any]] = {}
        close_entries = {
            getattr(mt5, "DEAL_ENTRY_OUT", 1),
            getattr(mt5, "DEAL_ENTRY_INOUT", 2),
            getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
        }
        for deal in self.bot_deals_since(start):
            entry_type = int(deal.get("entry", -1) or -1)
            if entry_type not in close_entries:
                continue
            position_id = str(deal.get("position_id") or deal.get("position") or deal.get("ticket"))
            item = grouped.setdefault(
                position_id,
                {
                    "position_id": position_id,
                    "symbol": str(deal.get("symbol", "")),
                    "time": int(deal.get("time", 0) or 0),
                    "profit": 0.0,
                },
            )
            item["time"] = max(int(item.get("time", 0) or 0), int(deal.get("time", 0) or 0))
            item["profit"] = float(item.get("profit", 0.0)) + float(deal.get("profit", 0.0) or 0.0)
            item["profit"] += float(deal.get("swap", 0.0) or 0.0) + float(deal.get("commission", 0.0) or 0.0)
        return sorted(grouped.values(), key=lambda item: int(item.get("time", 0) or 0))

    def daily_metrics(self, account: Any) -> dict[str, Any]:
        guardrails = self.guardrail_config()
        timezone_name = str(guardrails.get("timezone", "America/New_York"))
        zone = safe_zone(timezone_name)
        now_local = datetime.now(timezone.utc).astimezone(zone)
        day_start = datetime.combine(now_local.date(), datetime_time.min, tzinfo=zone).astimezone(timezone.utc)
        deals = self.bot_deals_since(day_start)
        entry_types = {getattr(mt5, "DEAL_ENTRY_IN", 0), getattr(mt5, "DEAL_ENTRY_INOUT", 2)}
        trades_today = {
            str(deal.get("position_id") or deal.get("position") or deal.get("ticket"))
            for deal in deals
            if int(deal.get("entry", -1) or -1) in entry_types
        }
        daily_pnl = sum(
            float(deal.get("profit", 0.0) or 0.0)
            + float(deal.get("swap", 0.0) or 0.0)
            + float(deal.get("commission", 0.0) or 0.0)
            for deal in deals
        )
        risk_state = self.state.setdefault("risk_state", {})
        equity = float(getattr(account, "equity", 0.0) or 0.0)
        previous_peak = float(risk_state.get("equity_peak", equity) or equity)
        peak = max(previous_peak, equity)
        risk_state["equity_peak"] = peak
        risk_state["updated_at"] = utc_now()
        drawdown_pct = ((peak - equity) / peak * 100.0) if peak > 0 else 0.0
        closed = self.bot_closed_trades(guardrails.get("loss_streak_lookback_days", 30))
        loss_streak = 0
        for trade in reversed(closed):
            if float(trade.get("profit", 0.0) or 0.0) < 0:
                loss_streak += 1
            elif float(trade.get("profit", 0.0) or 0.0) > 0:
                break
        return {
            "timezone": timezone_name,
            "day": now_local.date().isoformat(),
            "daily_pnl": round(daily_pnl, 2),
            "trades_today": len(trades_today),
            "loss_streak": loss_streak,
            "equity_peak": round(peak, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "recent_closed": closed[-10:],
        }

    def risk_gate(self, signal: Signal, account: Any, metrics: dict[str, Any]) -> tuple[bool, list[str]]:
        guardrails = self.guardrail_config()
        if not guardrails.get("enabled", True):
            return True, []
        reasons: list[str] = []
        max_trades = int(guardrails.get("max_trades_per_day", 0) or 0)
        if max_trades > 0 and int(metrics.get("trades_today", 0)) >= max_trades:
            reasons.append("max_trades_per_day")
        max_daily_loss_pct = float(guardrails.get("max_daily_loss_pct", 0.0) or 0.0)
        balance = float(getattr(account, "balance", 0.0) or 0.0)
        if max_daily_loss_pct > 0 and float(metrics.get("daily_pnl", 0.0) or 0.0) <= -(balance * max_daily_loss_pct / 100.0):
            reasons.append("max_daily_loss")
        max_drawdown_pct = float(guardrails.get("max_total_drawdown_pct", 0.0) or 0.0)
        if max_drawdown_pct > 0 and float(metrics.get("drawdown_pct", 0.0) or 0.0) >= max_drawdown_pct:
            reasons.append("max_total_drawdown")
        max_losses = int(guardrails.get("max_consecutive_losses", 0) or 0)
        if max_losses > 0 and int(metrics.get("loss_streak", 0) or 0) >= max_losses:
            reasons.append("max_consecutive_losses")

        cooldown_minutes = int(guardrails.get("symbol_loss_cooldown_minutes", 0) or 0)
        if cooldown_minutes > 0:
            cutoff = datetime.now(timezone.utc).timestamp() - cooldown_minutes * 60
            for trade in reversed(metrics.get("recent_closed", [])):
                if str(trade.get("symbol", "")).upper() != signal.broker_symbol.upper():
                    continue
                if float(trade.get("profit", 0.0) or 0.0) < 0 and int(trade.get("time", 0) or 0) >= cutoff:
                    reasons.append("symbol_loss_cooldown")
                break
        return not reasons, reasons

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
        strategy_cfg = self.config.get("strategy", {})
        min_adx = float(strategy_cfg.get("min_adx", 0.0) or 0.0)
        if min_adx > 0 and float(adx[index]) < min_adx:
            self.update_symbol_state(logical, bar_time, state_after)
            return None, {
                "status": "weak_trend_adx",
                "side": side,
                "adx": round(float(adx[index]), 2),
                "min_adx": min_adx,
                "bias": bias,
            }
        if strategy_cfg.get("require_bias_alignment", True):
            edge = float(strategy_cfg.get("min_bias_edge_pct", 15.0) or 0.0)
            bias_edge = bull_pct - bear_pct if side == "BUY" else bear_pct - bull_pct
            if bias_edge < edge:
                self.update_symbol_state(logical, bar_time, state_after)
                return None, {
                    "status": "bias_not_aligned",
                    "side": side,
                    "bias": bias,
                    "bull_pct": round(bull_pct),
                    "bear_pct": round(bear_pct),
                    "required_edge": edge,
                }
        dynamic_cfg = strategy_cfg.get("dynamic_stop", {}) or {}
        base_atr_multiplier = float(dynamic_cfg.get("base_atr", strategy_cfg.get("atr_multiplier", 1.5)))
        activity_factor = 1.0
        volatility_ratio = 1.0
        volume_ratio = 1.0
        if dynamic_cfg.get("enabled", True):
            atr_lookback = max(20, int(dynamic_cfg.get("volatility_lookback", 50) or 50))
            historical_atr = [float(value) for value in atr14[max(0, index - atr_lookback) : index] if value]
            baseline_atr = sorted(historical_atr)[len(historical_atr) // 2] if historical_atr else float(atr14[index])
            volatility_ratio = float(atr14[index]) / max(baseline_atr, 1e-12)
            volume_lookback = max(10, int(dynamic_cfg.get("volume_lookback", 30) or 30))
            historical_volume = sorted(float(value) for value in volumes[max(0, index - volume_lookback) : index] if value > 0)
            baseline_volume = historical_volume[len(historical_volume) // 2] if historical_volume else max(float(volumes[index]), 1.0)
            volume_ratio = float(volumes[index]) / max(baseline_volume, 1.0)
            boost = max(0.0, volatility_ratio - 1.0) * 0.55 + max(0.0, volume_ratio - 1.0) * 0.20
            if (
                volatility_ratio >= float(dynamic_cfg.get("high_volatility_ratio", 1.2))
                and volume_ratio >= float(dynamic_cfg.get("high_volume_ratio", 1.35))
            ):
                boost += 0.15
            activity_factor = min(float(dynamic_cfg.get("max_widen_factor", 2.5)), 1.0 + boost)
        atr_multiple = min(float(dynamic_cfg.get("max_atr", 3.5)), base_atr_multiplier * activity_factor)
        risk_unit = float(atr14[index]) * atr_multiple
        broker_minimum_stop = max(
            float(getattr(info, "trade_stops_level", 0) or 0) * float(info.point or 0.0),
            float(getattr(info, "trade_freeze_level", 0) or 0) * float(info.point or 0.0),
            spread * 1.25,
        )
        risk_unit = max(risk_unit, broker_minimum_stop)
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
        return signal, {
            "status": "signal",
            "side": side,
            "bias": bias,
            "bull_pct": round(bull_pct),
            "bear_pct": round(bear_pct),
            "dynamic_stop": {
                "atr_multiple": round(atr_multiple, 3),
                "activity_factor": round(activity_factor, 3),
                "volatility_ratio": round(volatility_ratio, 3),
                "volume_ratio": round(volume_ratio, 3),
            },
        }

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

    @staticmethod
    def normalize_volume_down(info: Any, volume: float) -> float:
        min_lot = float(getattr(info, "volume_min", 0.01) or 0.01)
        max_lot = float(getattr(info, "volume_max", 100.0) or 100.0)
        step = float(getattr(info, "volume_step", 0.01) or 0.01)
        if volume < min_lot:
            return 0.0
        clipped = min(float(volume), max_lot)
        steps = math.floor((clipped - min_lot + 1e-12) / step)
        normalized = min_lot + steps * step
        return round(max(min_lot, min(normalized, max_lot)), 4)

    def close_partial_position(
        self,
        data: dict[str, Any],
        symbol: str,
        side: str,
        info: Any,
        tick: Any,
        close_percent: float,
    ) -> dict[str, Any]:
        ticket = int(data["ticket"])
        current_volume = float(data.get("volume") or 0.0)
        close_percent = max(0.0, min(100.0, float(close_percent or 0.0)))
        min_lot = float(getattr(info, "volume_min", 0.01) or 0.01)
        target_volume = current_volume * (close_percent / 100.0)
        close_volume = self.normalize_volume_down(info, target_volume)

        if close_volume <= 0:
            return {
                "closed": False,
                "permanent_skip": True,
                "message": "Partial close volume is below broker minimum lot.",
                "ticket": ticket,
                "current_volume": current_volume,
                "target_volume": target_volume,
                "minimum_lot": min_lot,
            }

        remaining_volume = round(current_volume - close_volume, 8)
        if 0 < remaining_volume < min_lot:
            close_volume = self.normalize_volume_down(info, current_volume - min_lot)
            remaining_volume = round(current_volume - close_volume, 8)
        if close_volume <= 0 or close_volume >= current_volume or remaining_volume < min_lot:
            return {
                "closed": False,
                "permanent_skip": True,
                "message": "Broker minimum lot does not allow a safe partial close.",
                "ticket": ticket,
                "current_volume": current_volume,
                "target_volume": target_volume,
                "minimum_lot": min_lot,
            }

        order_type = mt5.ORDER_TYPE_SELL if side == "BUY" else mt5.ORDER_TYPE_BUY
        price = float(tick.bid if side == "BUY" else tick.ask)
        request_base = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": close_volume,
            "type": order_type,
            "price": price,
            "deviation": int(self.config.get("execution", {}).get("deviation_points", 30)),
            "comment": f"SNIP TP1 {close_percent:g}%"[:31],
        }
        if not self.live:
            return {"closed": False, "dry_run": True, "request": request_base}

        last_error: dict[str, Any] | None = None
        for filling in FILLING_MODES:
            request = dict(request_base)
            request["type_filling"] = filling
            result = mt5.order_send(request)
            result_data = as_dict(result) if result else {"retcode": None, "comment": "no send result"}
            if result_data.get("retcode") in (
                mt5.TRADE_RETCODE_DONE,
                getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010),
                mt5.TRADE_RETCODE_PLACED,
            ):
                return {
                    "closed": True,
                    "ticket": ticket,
                    "closed_volume": close_volume,
                    "remaining_volume": remaining_volume,
                    "close_percent": close_percent,
                    "retcode": result_data.get("retcode"),
                    "comment": result_data.get("comment"),
                    "request": request,
                    "result": result_data,
                }
            last_error = {
                "stage": "send",
                "retcode": result_data.get("retcode"),
                "comment": result_data.get("comment"),
                "filling": filling,
            }
        return {"closed": False, "error": last_error or "unknown_partial_close_error", "request": request_base}

    def close_position_full(
        self,
        data: dict[str, Any],
        symbol: str,
        side: str,
        tick: Any,
    ) -> dict[str, Any]:
        request_base = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": int(data["ticket"]),
            "symbol": symbol,
            "volume": float(data.get("volume") or 0.0),
            "type": mt5.ORDER_TYPE_SELL if side == "BUY" else mt5.ORDER_TYPE_BUY,
            "price": float(tick.bid if side == "BUY" else tick.ask),
            "deviation": int(self.config.get("execution", {}).get("deviation_points", 30)),
            "comment": "SNIP setup invalidated",
            "type_time": mt5.ORDER_TIME_GTC,
        }
        if not self.live:
            return {"closed": False, "dry_run": True, "request": request_base}
        last_error: dict[str, Any] | None = None
        for filling in FILLING_MODES:
            request = {**request_base, "type_filling": filling}
            result = mt5.order_send(request)
            result_data = as_dict(result) if result else {"retcode": None, "comment": "no result"}
            if result_data.get("retcode") in {
                mt5.TRADE_RETCODE_DONE,
                getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010),
            }:
                return {"closed": True, "request": request, "result": result_data}
            last_error = {
                "retcode": result_data.get("retcode"),
                "comment": result_data.get("comment"),
                "filling": filling,
            }
        return {"closed": False, "error": last_error or "unknown_close_error", "request": request_base}

    def smart_exit_check(
        self,
        data: dict[str, Any],
        symbol: str,
        side: str,
        tick: Any,
    ) -> dict[str, Any] | None:
        cfg = self.config.get("execution", {}).get("smart_exit", {}) or {}
        if not cfg.get("enabled", True):
            return None
        timeframe_name = str(cfg.get("timeframe", "M15")).upper()
        timeframe = TIMEFRAMES.get(timeframe_name, mt5.TIMEFRAME_M15)
        min_bars_open = max(1, int(cfg.get("min_bars_open", 2) or 2))
        timeframe_minutes = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240}.get(timeframe_name, 15)
        opened_at = int(data.get("time") or 0)
        if opened_at and time.time() - opened_at < timeframe_minutes * min_bars_open * 60:
            return None
        candles = self.get_closed_rates(symbol, timeframe, max(60, int(cfg.get("lookback_bars", 100) or 100)))
        if len(candles) < 35:
            return None
        closes = [float(candle["close"]) for candle in candles]
        ema_fast = ema_series(closes, max(2, int(cfg.get("ema_fast", 9) or 9)))
        ema_slow = ema_series(closes, max(3, int(cfg.get("ema_slow", 21) or 21)))
        atr_values = atr_series(candles, max(2, int(cfg.get("atr_period", 14) or 14)))
        atr = float(atr_values[-1] or 0.0)
        if atr <= 0 or ema_fast[-1] is None or ema_slow[-1] is None:
            return None
        entry = float(data.get("price_open") or 0.0)
        latest = candles[-1]
        last_two_closes = closes[-2:]
        structure_lookback = max(3, int(cfg.get("structure_lookback", 8) or 8))
        previous_structure = candles[-structure_lookback - 1 : -1]
        volume_history = sorted(float(candle.get("tick_volume", 1.0) or 1.0) for candle in candles[-31:-1])
        baseline_volume = volume_history[len(volume_history) // 2] if volume_history else 1.0
        volume_ratio = float(latest.get("tick_volume", 1.0) or 1.0) / max(baseline_volume, 1.0)
        adverse_atr = float(cfg.get("adverse_entry_atr", 0.25) or 0.25)
        body_atr = float(cfg.get("momentum_body_atr", 0.65) or 0.65)
        body = abs(float(latest["close"]) - float(latest["open"]))
        if side == "BUY":
            trend_reversal = bool(ema_fast[-1] < ema_slow[-1] and all(value < float(ema_fast[-1]) for value in last_two_closes))
            failed_entry = all(value < entry - atr * adverse_atr for value in last_two_closes)
            adverse_momentum = float(latest["close"]) < float(latest["open"]) and body >= atr * body_atr
            structure_break = float(latest["close"]) < min(float(candle["low"]) for candle in previous_structure)
        else:
            trend_reversal = bool(ema_fast[-1] > ema_slow[-1] and all(value > float(ema_fast[-1]) for value in last_two_closes))
            failed_entry = all(value > entry + atr * adverse_atr for value in last_two_closes)
            adverse_momentum = float(latest["close"]) > float(latest["open"]) and body >= atr * body_atr
            structure_break = float(latest["close"]) > max(float(candle["high"]) for candle in previous_structure)
        score = 0
        reasons: list[str] = []
        for confirmed, weight, reason in (
            (trend_reversal, 1, "ema_trend_reversed"),
            (failed_entry, 1, "two_closes_failed_entry"),
            (adverse_momentum and volume_ratio >= float(cfg.get("momentum_volume_ratio", 1.3)), 1, "high_volume_adverse_momentum"),
            (structure_break, 2, "adverse_structure_break"),
        ):
            if confirmed:
                score += weight
                reasons.append(reason)
        profit = float(data.get("profit") or 0.0)
        required = max(1, int(cfg.get("profit_confirmations", 1) if profit > 0 else cfg.get("loss_confirmations", 2)))
        if score < required:
            return None
        result = self.close_position_full(data, symbol, side, tick)
        return {
            "action": "smart_invalidation_exit",
            "score": score,
            "required": required,
            "reasons": reasons,
            "profit": profit,
            "atr": atr,
            "volume_ratio": round(volume_ratio, 3),
            "result": result,
        }

    def manage_positions(self) -> list[dict[str, Any]]:
        if not self.config.get("execution", {}).get("manage_virtual_targets", True):
            return []
        magic = int(self.config.get("execution", {}).get("magic", 26061515))
        actions: list[dict[str, Any]] = []
        managed_positions = self.state.setdefault("managed_positions", {})
        for position in mt5.positions_get() or []:
            data = as_dict(position)
            if int(data.get("magic", 0) or 0) != magic and not str(data.get("comment", "")).startswith("SNIP"):
                continue
            ticket = str(int(data["ticket"]))
            position_state = managed_positions.setdefault(ticket, {})
            symbol = data["symbol"]
            side = "BUY" if int(data["type"]) == mt5.POSITION_TYPE_BUY else "SELL"
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if not info or not tick:
                continue
            smart_exit = self.smart_exit_check(data, symbol, side, tick)
            if smart_exit is not None:
                actions.append({"ticket": int(data["ticket"]), **smart_exit})
                if smart_exit.get("result", {}).get("closed") or smart_exit.get("result", {}).get("dry_run"):
                    continue
            entry = float(data["price_open"])
            old_sl = float(data.get("sl") or 0)
            tp = float(data.get("tp") or 0)
            if old_sl <= 0 or tp <= 0:
                actions.append({"ticket": int(data["ticket"]), "action": "review", "reason": "missing_sl_tp"})
                continue
            final_distance = abs(tp - entry)
            target_name = str(self.config.get("execution", {}).get("broker_tp", "TP5")).upper()
            target_multiple = int(target_name.replace("TP", "")) if target_name.replace("TP", "").isdigit() else 5
            target_multiple = max(1, min(5, target_multiple))
            risk_unit = final_distance / float(target_multiple)
            tp1 = entry + risk_unit if side == "BUY" else entry - risk_unit
            tp2 = entry + 2 * risk_unit if side == "BUY" else entry - 2 * risk_unit
            price = float(tick.bid if side == "BUY" else tick.ask)
            spread = float(tick.ask - tick.bid)
            buffer = max(spread * 1.5, (info.point or 0.01) * 10)
            hit_tp1 = price >= tp1 if side == "BUY" else price <= tp1
            partial_enabled = self.config.get("execution", {}).get("partial_close_at_tp1", False)
            partial_pct = float(self.config.get("execution", {}).get("tp1_partial_close_pct", 0.0))
            if hit_tp1 and partial_enabled and partial_pct > 0 and not position_state.get("tp1_partial_done"):
                partial_result = self.close_partial_position(data, symbol, side, info, tick, partial_pct)
                actions.append(
                    {
                        "ticket": int(data["ticket"]),
                        "action": "tp1_partial_close",
                        "percent": partial_pct,
                        "result": partial_result,
                    }
                )
                if partial_result.get("closed") or partial_result.get("permanent_skip"):
                    position_state["tp1_partial_done"] = True
                    position_state["tp1_partial_status"] = "closed" if partial_result.get("closed") else "skipped"
                    position_state["tp1_partial_at"] = utc_now()
                    position_state["tp1_partial_closed_volume"] = partial_result.get("closed_volume")
                    position_state["tp1_partial_remaining_volume"] = partial_result.get("remaining_volume")
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
        target_name = str(self.config.get("execution", {}).get("broker_tp", "TP5")).lower()
        tp = getattr(signal, target_name, signal.tp5)
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
            session_ok, session_reasons, session_info = self.session_gate()
            daily_metrics = self.daily_metrics(account)
            output["guardrails"] = {
                "session_ok": session_ok,
                "session_reasons": session_reasons,
                "session": session_info,
                "daily": daily_metrics,
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
                if not session_ok:
                    row["status"] = "signal_skipped_session"
                    row["guardrail_reasons"] = session_reasons
                    output["symbols"].append(row)
                    continue
                risk_ok, risk_reasons = self.risk_gate(signal, account, daily_metrics)
                if not risk_ok:
                    row["status"] = "signal_skipped_guardrail"
                    row["guardrail_reasons"] = risk_reasons
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
