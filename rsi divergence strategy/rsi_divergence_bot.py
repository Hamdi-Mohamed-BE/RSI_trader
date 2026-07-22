from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import MetaTrader5 as mt5
import numpy as np


TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
}


@dataclass(frozen=True)
class SymbolConfig:
    symbol: str
    timeframe: str
    pivot_len: int
    atr_sl_mult: float
    confirmation: str
    rr: tuple[float, float, float]
    session: str = "ALL"


@dataclass
class TradeIdea:
    symbol: str
    broker_symbol: str
    timeframe: str
    side: str
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    tp1: float
    tp2: float
    tp3: float
    r_multiple: float
    pnl: float
    balance_after: float
    exit_reason: str
    bars_held: int
    pivot_rsi: float
    previous_rsi: float
    risk_points: float
    lot: float = 0.0
    target_risk: float = 0.0
    actual_risk: float = 0.0
    risk_mode: str = "RISK_PERCENT"


DEFAULT_CONFIGS: dict[str, SymbolConfig] = {
    "XAUUSD": SymbolConfig("XAUUSD", "M5", 3, 2.0, "EMA", (1.0, 1.5, 3.0), "LONDON"),
    "XAGUSD": SymbolConfig("XAGUSD", "M1", 5, 1.5, "OFF", (1.0, 1.5, 2.0), "ALL"),
    "BTCUSD": SymbolConfig("BTCUSD", "M1", 3, 1.2, "EMA", (1.0, 1.5, 2.0), "NY_OPEN"),
    "ETHUSD": SymbolConfig("ETHUSD", "M1", 3, 1.2, "EMA", (1.0, 1.5, 2.0), "NY_OPEN"),
    "EURUSD": SymbolConfig("EURUSD", "M15", 3, 2.0, "TREND", (1.0, 1.5, 3.0), "ALL"),
    "GBPUSD": SymbolConfig("GBPUSD", "M15", 3, 2.0, "RSI_EXTREME", (1.0, 1.5, 2.0), "ALL"),
    "USDJPY": SymbolConfig("USDJPY", "M1", 3, 2.0, "TREND", (1.0, 2.0, 3.0), "NY_LATE"),
    "AUDUSD": SymbolConfig("AUDUSD", "M1", 3, 2.0, "TREND", (1.0, 1.5, 3.0), "NY_LATE"),
    "USDCAD": SymbolConfig("USDCAD", "M5", 3, 2.0, "OFF", (1.0, 1.5, 2.0), "NY_OPEN"),
    "EURGBP": SymbolConfig("EURGBP", "M1", 3, 2.0, "TREND", (1.0, 2.0, 3.0), "LONDON"),
    "AUDCAD": SymbolConfig("AUDCAD", "M1", 7, 1.5, "RSI_EXTREME", (1.0, 2.0, 3.0), "ALL"),
    "GBPCHF": SymbolConfig("GBPCHF", "M5", 7, 2.0, "OFF", (1.0, 2.0, 3.0), "NY_LATE"),
    "US30": SymbolConfig("US30", "M5", 3, 2.0, "EMA", (1.0, 1.5, 2.0), "NY_OPEN"),
    "US100": SymbolConfig("US100", "M5", 3, 2.0, "EMA", (1.0, 1.5, 2.0), "NY_OPEN"),
}


OPTIMIZED_CONFIG_PATH = Path(__file__).resolve().parent / "optimized_configs.json"
ENV_PATH = Path(__file__).resolve().parent / ".env"
LIVE_STATE_PATH = Path(__file__).resolve().parent / "runtime" / "live_state.json"


def load_env_file(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def config_from_dict(payload: dict) -> SymbolConfig:
    return SymbolConfig(
        symbol=str(payload["symbol"]).upper(),
        timeframe=str(payload["timeframe"]).upper(),
        pivot_len=int(payload["pivot_len"]),
        atr_sl_mult=float(payload["atr_sl_mult"]),
        confirmation=str(payload["confirmation"]).upper(),
        rr=tuple(float(v) for v in payload["rr"]),
        session=str(payload.get("session", "ALL")).upper(),
    )


def load_optimized_configs() -> dict[str, SymbolConfig]:
    if not OPTIMIZED_CONFIG_PATH.exists():
        return {}
    payload = json.loads(OPTIMIZED_CONFIG_PATH.read_text(encoding="utf-8"))
    configs: dict[str, SymbolConfig] = {}
    for symbol, item in payload.get("configs", {}).items():
        configs[symbol.upper()] = config_from_dict(item)
    return configs


def load_optimized_max_trades() -> dict[str, int]:
    if not OPTIMIZED_CONFIG_PATH.exists():
        return {}
    payload = json.loads(OPTIMIZED_CONFIG_PATH.read_text(encoding="utf-8"))
    limits: dict[str, int] = {}
    for symbol, item in payload.get("configs", {}).items():
        limits[symbol.upper()] = int(item.get("max_trades_per_symbol_day", 3))
    return limits


def load_live_state() -> dict:
    if not LIVE_STATE_PATH.exists():
        return {"signals": {}}
    try:
        return json.loads(LIVE_STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"signals": {}}


def save_live_state(state: dict) -> None:
    LIVE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIVE_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def parse_state_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def successful_live_records(state: dict, symbol: str | None = None) -> list[dict]:
    records: list[dict] = []
    for item in state.get("signals", {}).values():
        if symbol and str(item.get("symbol", "")).upper() != symbol.upper():
            continue
        if item.get("tickets"):
            records.append(item)
    return records


def live_ideas_count_for_day(state: dict, symbol: str, day: datetime) -> int:
    day_key = day.astimezone(timezone.utc).date()
    count = 0
    for item in successful_live_records(state, symbol):
        placed_at = parse_state_datetime(item.get("placed_at"))
        if placed_at and placed_at.date() == day_key:
            count += 1
    return count


def last_live_idea_time(state: dict, symbol: str) -> datetime | None:
    times = [
        placed_at
        for item in successful_live_records(state, symbol)
        if (placed_at := parse_state_datetime(item.get("placed_at"))) is not None
    ]
    return max(times) if times else None


def clean_symbol(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def resolve_symbol(wanted: str) -> str | None:
    if mt5.symbol_info(wanted):
        mt5.symbol_select(wanted, True)
        return wanted

    wanted_clean = clean_symbol(wanted)
    all_symbols = mt5.symbols_get()
    if not all_symbols:
        return None

    exact = [s.name for s in all_symbols if clean_symbol(s.name) == wanted_clean]
    starts = [s.name for s in all_symbols if clean_symbol(s.name).startswith(wanted_clean)]
    contains = [s.name for s in all_symbols if wanted_clean in clean_symbol(s.name)]
    aliases = []
    if wanted_clean == "US30":
        aliases = [s.name for s in all_symbols if "US30" in clean_symbol(s.name) or "DJ30" in clean_symbol(s.name) or "DOW" in clean_symbol(s.name)]
    if wanted_clean == "US100":
        aliases = [s.name for s in all_symbols if "US100" in clean_symbol(s.name) or "NAS" in clean_symbol(s.name) or "USTEC" in clean_symbol(s.name)]

    for name in exact + starts + aliases + contains:
        if mt5.symbol_select(name, True):
            return name
    return None


def rates_to_arrays(rates: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "time": np.array([datetime.fromtimestamp(int(t), tz=timezone.utc) for t in rates["time"]], dtype=object),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
        "tick_volume": rates["tick_volume"].astype(float),
        "spread": rates["spread"].astype(float),
    }


def ema(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(values), np.nan)
    if len(values) == 0:
        return out
    alpha = 2.0 / (period + 1.0)
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = values[i] * alpha + out[i - 1] * (1.0 - alpha)
    return out


def rsi(values: np.ndarray, period: int = 14) -> np.ndarray:
    out = np.full(len(values), np.nan)
    if len(values) <= period:
        return out
    gains = np.zeros(len(values))
    losses = np.zeros(len(values))
    diff = np.diff(values)
    gains[1:] = np.maximum(diff, 0.0)
    losses[1:] = np.maximum(-diff, 0.0)
    avg_gain = np.mean(gains[1 : period + 1])
    avg_loss = np.mean(losses[1 : period + 1])
    out[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def atr(data: dict[str, np.ndarray], period: int = 14) -> np.ndarray:
    high = data["high"]
    low = data["low"]
    close = data["close"]
    out = np.full(len(close), np.nan)
    tr = np.zeros(len(close))
    for i in range(len(close)):
        prev = close[i - 1] if i > 0 else close[i]
        tr[i] = max(high[i] - low[i], abs(high[i] - prev), abs(low[i] - prev))
    if len(close) <= period:
        return out
    out[period] = np.mean(tr[1 : period + 1])
    for i in range(period + 1, len(close)):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def is_pivot_low(lows: np.ndarray, index: int, strength: int) -> bool:
    if index - strength < 0 or index + strength >= len(lows):
        return False
    return lows[index] <= np.nanmin(lows[index - strength : index + strength + 1])


def is_pivot_high(highs: np.ndarray, index: int, strength: int) -> bool:
    if index - strength < 0 or index + strength >= len(highs):
        return False
    return highs[index] >= np.nanmax(highs[index - strength : index + strength + 1])


def session_ok(session: str, dt: datetime) -> bool:
    # MT5 timestamps are treated as UTC. These windows are intentionally broad.
    hour = dt.hour + dt.minute / 60.0
    if session == "ALL":
        return True
    if session == "LONDON":
        return 7.0 <= hour <= 12.0
    if session == "NY_OPEN":
        return 13.0 <= hour <= 17.0
    if session == "NY_LATE":
        return 17.0 <= hour <= 21.0
    return True


def normalize_lot(symbol: str, lot: float, *, round_down: bool = True) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        return round(max(0.0, lot), 2)
    min_lot = float(info.volume_min or 0.01)
    max_lot = float(info.volume_max or 100.0)
    step = float(info.volume_step or 0.01)
    lot = max(min_lot, min(max_lot, lot))
    if step > 0:
        units = lot / step
        units = math.floor(units + 1e-9) if round_down else round(units)
        lot = units * step
    decimals = max(0, int(round(-math.log10(step)))) if 0 < step < 1 else 2
    return round(max(min_lot, min(max_lot, lot)), decimals)


def money_per_lot_at_risk(symbol: str, risk_points: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.0
    tick_size = float(info.trade_tick_size or info.point or 0.0)
    tick_value = float(info.trade_tick_value or 0.0)
    if tick_size <= 0 or tick_value <= 0 or risk_points <= 0:
        return 0.0
    return (risk_points / tick_size) * tick_value


def calculate_position_size(
    symbol: str,
    balance: float,
    risk_points: float,
    risk_mode: str,
    risk_percent: float,
    fixed_lot: float,
    risk_usd_cap: float,
    risk_usd_offset: float,
) -> dict:
    mode = risk_mode.upper()
    money_per_lot = money_per_lot_at_risk(symbol, risk_points)
    if money_per_lot <= 0:
        fallback = balance * risk_percent / 100.0
        return {
            "mode": mode,
            "lot": 0.0,
            "target_risk": round(fallback, 2),
            "actual_risk": round(fallback, 2),
            "money_per_lot": 0.0,
        }

    if mode == "FIXED_LOT":
        lot = normalize_lot(symbol, fixed_lot, round_down=False)
        actual_risk = lot * money_per_lot
        return {
            "mode": mode,
            "lot": lot,
            "target_risk": round(actual_risk, 2),
            "actual_risk": round(actual_risk, 2),
            "money_per_lot": round(money_per_lot, 4),
        }

    if mode == "USD_RISK_CAP":
        target_risk = max(0.0, risk_usd_cap - risk_usd_offset)
    else:
        mode = "RISK_PERCENT"
        target_risk = balance * risk_percent / 100.0

    raw_lot = target_risk / money_per_lot if money_per_lot > 0 else 0.0
    lot = normalize_lot(symbol, raw_lot, round_down=True)
    actual_risk = lot * money_per_lot

    info = mt5.symbol_info(symbol)
    min_lot = float(info.volume_min or 0.01) if info else 0.01
    step = float(info.volume_step or 0.01) if info else 0.01
    while lot > min_lot and actual_risk > target_risk and step > 0:
        lot = normalize_lot(symbol, lot - step, round_down=True)
        actual_risk = lot * money_per_lot

    return {
        "mode": mode,
        "lot": lot,
        "target_risk": round(target_risk, 2),
        "actual_risk": round(actual_risk, 2),
        "money_per_lot": round(money_per_lot, 4),
    }


def live_signal_age_minutes(config: SymbolConfig, fallback: int) -> int:
    if config.timeframe == "M1":
        return fallback
    if config.timeframe == "M5":
        return max(fallback, 20)
    return max(fallback, 45)


def get_live_rates(broker_symbol: str, timeframe: str, lookback_days: int) -> dict[str, np.ndarray] | None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)
    rates = mt5.copy_rates_range(broker_symbol, TIMEFRAMES[timeframe], start, end)
    if rates is None or len(rates) < 250:
        return None
    return rates_to_arrays(rates)


def latest_live_signal(data: dict[str, np.ndarray], config: SymbolConfig, max_age_minutes: int) -> dict | None:
    signals = build_signals(data, config)
    if not signals:
        return None
    now = datetime.now(timezone.utc)
    fresh = [
        signal
        for signal in signals
        if 0 <= (now - signal["entry_time"]).total_seconds() <= max_age_minutes * 60
    ]
    return fresh[-1] if fresh else None


def current_entry_price(broker_symbol: str, side: str) -> float | None:
    tick = mt5.symbol_info_tick(broker_symbol)
    if tick is None:
        return None
    return float(tick.ask if side == "BUY" else tick.bid)


def spread_ok(broker_symbol: str, max_spread_points: int) -> tuple[bool, str]:
    info = mt5.symbol_info(broker_symbol)
    tick = mt5.symbol_info_tick(broker_symbol)
    if info is None or tick is None:
        return False, "missing symbol info/tick"
    spread_points = int(round((float(tick.ask) - float(tick.bid)) / float(info.point or 0.00001)))
    if spread_points > max_spread_points:
        return False, f"spread {spread_points} > {max_spread_points} points"
    return True, f"spread {spread_points} points"


def has_same_side_position(broker_symbol: str, side: str, magic: int) -> bool:
    positions = mt5.positions_get(symbol=broker_symbol)
    if not positions:
        return False
    wanted_type = mt5.POSITION_TYPE_BUY if side == "BUY" else mt5.POSITION_TYPE_SELL
    for position in positions:
        if int(position.magic) == magic and int(position.type) == wanted_type:
            return True
    return False


def has_any_position(broker_symbol: str, magic: int) -> bool:
    positions = mt5.positions_get(symbol=broker_symbol)
    if not positions:
        return False
    return any(int(position.magic) == magic for position in positions)


def send_market_leg(
    broker_symbol: str,
    side: str,
    lot: float,
    stop: float,
    take_profit: float,
    magic: int,
    deviation: int,
    comment: str,
) -> tuple[bool, str, int | None]:
    tick = mt5.symbol_info_tick(broker_symbol)
    if tick is None:
        return False, "missing tick", None
    order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
    price = float(tick.ask if side == "BUY" else tick.bid)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": broker_symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": stop,
        "tp": take_profit,
        "deviation": deviation,
        "magic": magic,
        "comment": comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        return False, f"order_send returned None: {mt5.last_error()}", None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"{result.retcode} {result.comment}", int(getattr(result, "order", 0) or 0)
    return True, result.comment, int(result.order or result.deal or 0)


def place_live_signal(
    symbol: str,
    broker_symbol: str,
    config: SymbolConfig,
    signal: dict,
    args: argparse.Namespace,
    state: dict,
    max_daily_ideas: int,
) -> str:
    side = signal["side"]
    signal_key = f"{symbol}:{side}:{signal['signal_time'].isoformat()}:{config.timeframe}"
    if signal_key in state.get("signals", {}):
        return f"skip duplicate {signal_key}"

    now = datetime.now(timezone.utc)
    ideas_today = live_ideas_count_for_day(state, symbol, now)
    if max_daily_ideas > 0 and ideas_today >= max_daily_ideas:
        return f"blocked {symbol} daily idea cap {ideas_today}/{max_daily_ideas}"

    last_placed = last_live_idea_time(state, symbol)
    if args.symbol_cooldown_minutes > 0 and last_placed:
        minutes_since = (now - last_placed).total_seconds() / 60.0
        if minutes_since < args.symbol_cooldown_minutes:
            return (
                f"blocked {symbol} cooldown {minutes_since:.0f}/"
                f"{args.symbol_cooldown_minutes} minutes since last idea"
            )

    if args.live_one_position_per_symbol and has_any_position(broker_symbol, args.magic):
        return f"skip existing RSI position for {broker_symbol}"

    if args.live_one_position_per_side and has_same_side_position(broker_symbol, side, args.magic):
        return f"skip existing {side} position for {broker_symbol}"

    ok, spread_reason = spread_ok(broker_symbol, args.max_spread_points)
    if not ok:
        return f"blocked {spread_reason}"

    live_entry = current_entry_price(broker_symbol, side)
    if live_entry is None:
        return "blocked missing live price"

    stop = float(signal["stop"])
    risk = live_entry - stop if side == "BUY" else stop - live_entry
    if risk <= 0:
        return f"blocked invalid live risk entry={live_entry:.6f} stop={stop:.6f}"

    original_risk = abs(float(signal["entry"]) - stop)
    drift = abs(live_entry - float(signal["entry"]))
    max_drift = original_risk * args.max_entry_drift_r
    if original_risk > 0 and drift > max_drift:
        return f"blocked price drift {drift:.6f} > {max_drift:.6f}"

    if side == "BUY":
        take_profits = [live_entry + risk * config.rr[0], live_entry + risk * config.rr[1], live_entry + risk * config.rr[2]]
    else:
        take_profits = [live_entry - risk * config.rr[0], live_entry - risk * config.rr[1], live_entry - risk * config.rr[2]]

    sizing = calculate_position_size(
        broker_symbol,
        float(mt5.account_info().equity if mt5.account_info() else args.balance),
        risk,
        args.risk_mode,
        args.risk,
        args.fixed_lot,
        args.risk_usd_cap,
        args.risk_usd_offset,
    )
    total_lot = float(sizing["lot"])
    leg_lot = normalize_lot(broker_symbol, total_lot / 3.0, round_down=True)
    info = mt5.symbol_info(broker_symbol)
    min_lot = float(info.volume_min or 0.01) if info else 0.01
    if leg_lot < min_lot:
        leg_lot = min_lot

    if not args.live_trading:
        return (
            f"paper {side} {broker_symbol} {config.timeframe} lot={leg_lot}x3 "
            f"entry={live_entry:.6f} sl={stop:.6f} tp={','.join(f'{tp:.6f}' for tp in take_profits)} "
            f"risk_target=${sizing['target_risk']} actual~${sizing['actual_risk']}"
        )

    tickets: list[int] = []
    errors: list[str] = []
    for index, tp in enumerate(take_profits, start=1):
        comment = f"RSIDIV {symbol} L{index}"
        placed, message, ticket = send_market_leg(
            broker_symbol,
            side,
            leg_lot,
            stop,
            float(tp),
            args.magic,
            args.deviation_points,
            comment,
        )
        if placed and ticket:
            tickets.append(ticket)
        else:
            errors.append(f"L{index}: {message}")

    state.setdefault("signals", {})[signal_key] = {
        "placed_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "broker_symbol": broker_symbol,
        "side": side,
        "timeframe": config.timeframe,
        "tickets": tickets,
        "errors": errors,
        "entry": live_entry,
        "stop": stop,
        "take_profits": take_profits,
        "lot_per_leg": leg_lot,
        "sizing": sizing,
    }
    save_live_state(state)
    if errors:
        return f"partial/failed {side} {broker_symbol} tickets={tickets} errors={errors}"
    return f"placed {side} {broker_symbol} {config.timeframe} tickets={tickets} lot={leg_lot}x3"


def confirmation_passes(
    data: dict[str, np.ndarray],
    side: str,
    pivot_index: int,
    check_index: int,
    mode: str,
    ema20: np.ndarray,
    ema50: np.ndarray,
    rsi_values: np.ndarray,
) -> bool:
    close = data["close"]
    high = data["high"]
    low = data["low"]
    if check_index <= pivot_index or check_index >= len(close):
        return False

    if mode == "OFF":
        return True

    recent_high = np.nanmax(high[pivot_index:check_index])
    recent_low = np.nanmin(low[pivot_index:check_index])
    if side == "BUY":
        ema_reclaim = close[check_index] > ema20[check_index]
        micro_break = close[check_index] > recent_high
        if mode == "EMA":
            return ema_reclaim or micro_break
        if mode == "TREND":
            return ema_reclaim and (close[check_index] > ema50[check_index] or ema20[check_index] >= ema20[check_index - 3])
        if mode == "RSI_EXTREME":
            return np.nanmin(rsi_values[max(0, pivot_index - 3) : pivot_index + 2]) <= 42.0 and (ema_reclaim or micro_break)
    else:
        ema_reject = close[check_index] < ema20[check_index]
        micro_break = close[check_index] < recent_low
        if mode == "EMA":
            return ema_reject or micro_break
        if mode == "TREND":
            return ema_reject and (close[check_index] < ema50[check_index] or ema20[check_index] <= ema20[check_index - 3])
        if mode == "RSI_EXTREME":
            return np.nanmax(rsi_values[max(0, pivot_index - 3) : pivot_index + 2]) >= 58.0 and (ema_reject or micro_break)
    return False


def build_signals(data: dict[str, np.ndarray], config: SymbolConfig) -> list[dict]:
    close = data["close"]
    high = data["high"]
    low = data["low"]
    times = data["time"]
    rsi14 = rsi(close, 14)
    atr14 = atr(data, 14)
    ema20 = ema(close, 20)
    ema50 = ema(close, 50)

    signals: list[dict] = []
    last_low: tuple[int, float, float] | None = None
    last_high: tuple[int, float, float] | None = None
    pivot_len = config.pivot_len
    weak_equal_atr = 0.18
    min_rsi_delta = 1.5
    max_confirm_bars = max(3, pivot_len * 3)
    max_risk_atr = 6.0

    for confirm_i in range(max(60, pivot_len * 2 + 20), len(close) - 2):
        p = confirm_i - pivot_len
        if not np.isfinite(rsi14[p]) or not np.isfinite(atr14[p]) or atr14[p] <= 0:
            continue

        if is_pivot_low(low, p, pivot_len):
            if last_low is not None:
                prev_i, prev_price, prev_rsi = last_low
                price_condition = low[p] <= prev_price + atr14[p] * weak_equal_atr
                rsi_condition = rsi14[p] >= prev_rsi + min_rsi_delta
                if price_condition and rsi_condition:
                    signal = find_entry_signal(data, config, "BUY", p, confirm_i, max_confirm_bars, ema20, ema50, rsi14, atr14, prev_rsi)
                    if signal:
                        signals.append(signal)
            last_low = (p, low[p], rsi14[p])

        if is_pivot_high(high, p, pivot_len):
            if last_high is not None:
                prev_i, prev_price, prev_rsi = last_high
                price_condition = high[p] >= prev_price - atr14[p] * weak_equal_atr
                rsi_condition = rsi14[p] <= prev_rsi - min_rsi_delta
                if price_condition and rsi_condition:
                    signal = find_entry_signal(data, config, "SELL", p, confirm_i, max_confirm_bars, ema20, ema50, rsi14, atr14, prev_rsi)
                    if signal:
                        risk_points = abs(signal["entry"] - signal["stop"])
                        if risk_points <= max_risk_atr * atr14[signal["entry_index"]]:
                            signals.append(signal)
            last_high = (p, high[p], rsi14[p])

    deduped: list[dict] = []
    last_entry_i = -9999
    for signal in sorted(signals, key=lambda item: item["entry_index"]):
        if signal["entry_index"] - last_entry_i >= pivot_len:
            deduped.append(signal)
            last_entry_i = signal["entry_index"]
    return deduped


def find_entry_signal(
    data: dict[str, np.ndarray],
    config: SymbolConfig,
    side: str,
    pivot_index: int,
    confirm_index: int,
    max_confirm_bars: int,
    ema20: np.ndarray,
    ema50: np.ndarray,
    rsi14: np.ndarray,
    atr14: np.ndarray,
    previous_rsi: float,
) -> dict | None:
    close = data["close"]
    high = data["high"]
    low = data["low"]
    open_ = data["open"]
    times = data["time"]
    for check_i in range(confirm_index, min(len(close) - 1, confirm_index + max_confirm_bars) + 1):
        if not session_ok(config.session, times[check_i]):
            continue
        if confirmation_passes(data, side, pivot_index, check_i, config.confirmation, ema20, ema50, rsi14):
            entry_i = check_i + 1
            if entry_i >= len(close):
                return None
            entry = float(open_[entry_i])
            atr_value = float(atr14[pivot_index])
            if side == "BUY":
                stop = float(low[pivot_index] - config.atr_sl_mult * atr_value)
                risk = entry - stop
                if risk <= 0:
                    return None
                tp1 = entry + risk * config.rr[0]
                tp2 = entry + risk * config.rr[1]
                tp3 = entry + risk * config.rr[2]
            else:
                stop = float(high[pivot_index] + config.atr_sl_mult * atr_value)
                risk = stop - entry
                if risk <= 0:
                    return None
                tp1 = entry - risk * config.rr[0]
                tp2 = entry - risk * config.rr[1]
                tp3 = entry - risk * config.rr[2]
            return {
                "side": side,
                "pivot_index": pivot_index,
                "confirm_index": check_i,
                "entry_index": entry_i,
                "signal_time": times[pivot_index],
                "entry_time": times[entry_i],
                "entry": entry,
                "stop": stop,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "pivot_rsi": float(rsi14[pivot_index]),
                "previous_rsi": float(previous_rsi),
            }
    return None


def simulate_signal(data: dict[str, np.ndarray], signal: dict, timeout_bars: int = 120) -> dict:
    side = signal["side"]
    entry_i = signal["entry_index"]
    entry = signal["entry"]
    initial_stop = signal["stop"]
    tp1, tp2, tp3 = signal["tp1"], signal["tp2"], signal["tp3"]
    risk = abs(entry - initial_stop)
    legs = [
        {"leg": 1, "target": tp1, "target_r": 1.0, "stop": initial_stop, "open": True},
        {"leg": 2, "target": tp2, "target_r": 1.5, "stop": initial_stop, "open": True},
        {"leg": 3, "target": tp3, "target_r": 3.0, "stop": initial_stop, "open": True},
    ]
    # Keep true target R from the configured prices, not only the common defaults.
    if risk > 0:
        for leg in legs:
            leg["target_r"] = abs(leg["target"] - entry) / risk

    realized_r = 0.0
    exit_reason = "end_of_data"
    exit_i = len(data["close"]) - 1
    last_price = float(data["close"][-1])

    for i in range(entry_i + 1, min(len(data["close"]), entry_i + timeout_bars + 1)):
        bar_high = float(data["high"][i])
        bar_low = float(data["low"][i])
        bar_close = float(data["close"][i])

        open_legs = [leg for leg in legs if leg["open"]]
        stopped = []
        for leg in open_legs:
            stop_hit = bar_low <= leg["stop"] if side == "BUY" else bar_high >= leg["stop"]
            if stop_hit:
                stopped.append(leg)

        if stopped:
            for leg in stopped:
                leg["open"] = False
                if risk <= 0:
                    leg_r = 0.0
                elif side == "BUY":
                    leg_r = (leg["stop"] - entry) / risk
                else:
                    leg_r = (entry - leg["stop"]) / risk
                realized_r += leg_r / 3.0
            if not any(leg["open"] for leg in legs):
                exit_reason = "stop"
                exit_i = i
                last_price = stopped[-1]["stop"]
                break

        target_hits = []
        for leg in [leg for leg in legs if leg["open"]]:
            target_hit = bar_high >= leg["target"] if side == "BUY" else bar_low <= leg["target"]
            if target_hit:
                target_hits.append(leg)

        hit_numbers = {leg["leg"] for leg in target_hits}
        for leg in target_hits:
            leg["open"] = False
            realized_r += float(leg["target_r"]) / 3.0

        if 1 in hit_numbers:
            for leg in legs:
                if leg["open"] and leg["leg"] in {2, 3}:
                    leg["stop"] = entry
        if 2 in hit_numbers:
            for leg in legs:
                if leg["open"] and leg["leg"] == 3:
                    leg["stop"] = tp1

        if not any(leg["open"] for leg in legs):
            exit_reason = "tp3" if 3 in hit_numbers else "target"
            exit_i = i
            last_price = tp3 if 3 in hit_numbers else bar_close
            break

        if i - entry_i >= timeout_bars:
            exit_reason = "timeout"
            exit_i = i
            last_price = bar_close
            for leg in [leg for leg in legs if leg["open"]]:
                if risk <= 0:
                    leg_r = 0.0
                elif side == "BUY":
                    leg_r = (bar_close - entry) / risk
                else:
                    leg_r = (entry - bar_close) / risk
                realized_r += max(-1.0, min(float(leg["target_r"]), leg_r)) / 3.0
                leg["open"] = False
            break

    if any(leg["open"] for leg in legs):
        for leg in [leg for leg in legs if leg["open"]]:
            if risk <= 0:
                leg_r = 0.0
            elif side == "BUY":
                leg_r = (last_price - entry) / risk
            else:
                leg_r = (entry - last_price) / risk
            realized_r += max(-1.0, min(float(leg["target_r"]), leg_r)) / 3.0
            leg["open"] = False

    return {
        "exit_index": exit_i,
        "exit_time": data["time"][exit_i],
        "exit_reason": exit_reason,
        "r_multiple": float(realized_r),
        "risk_points": float(risk),
    }


def backtest_symbol(
    display_symbol: str,
    broker_symbol: str,
    config: SymbolConfig,
    days: int,
    start_balance: float,
    risk_percent: float,
    max_trades_per_day: int,
    risk_mode: str,
    fixed_lot: float,
    risk_usd_cap: float,
    risk_usd_offset: float,
) -> tuple[list[TradeIdea], dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days + 10)
    rates = mt5.copy_rates_range(broker_symbol, TIMEFRAMES[config.timeframe], start, end)
    if rates is None or len(rates) < 250:
        return [], {"symbol": display_symbol, "broker_symbol": broker_symbol, "error": f"not enough MT5 candles ({0 if rates is None else len(rates)})"}

    data = rates_to_arrays(rates)
    cutoff = end - timedelta(days=days)
    signals = [s for s in build_signals(data, config) if s["entry_time"] >= cutoff]

    balance = start_balance
    peak = balance
    max_dd = 0.0
    trades: list[TradeIdea] = []
    next_free_index = -1
    day_counts: dict[str, int] = {}
    for signal in sorted(signals, key=lambda item: item["entry_index"]):
        if signal["entry_index"] <= next_free_index:
            continue
        day_key = signal["entry_time"].date().isoformat()
        if max_trades_per_day > 0 and day_counts.get(day_key, 0) >= max_trades_per_day:
            continue
        result = simulate_signal(data, signal)
        sizing = calculate_position_size(
            broker_symbol,
            balance,
            float(result["risk_points"]),
            risk_mode,
            risk_percent,
            fixed_lot,
            risk_usd_cap,
            risk_usd_offset,
        )
        risk_money = float(sizing["actual_risk"])
        pnl = risk_money * result["r_multiple"]
        balance += pnl
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
        next_free_index = int(result["exit_index"])
        day_counts[day_key] = day_counts.get(day_key, 0) + 1
        trades.append(
            TradeIdea(
                symbol=display_symbol,
                broker_symbol=broker_symbol,
                timeframe=config.timeframe,
                side=signal["side"],
                signal_time=signal["signal_time"].isoformat(),
                entry_time=signal["entry_time"].isoformat(),
                exit_time=result["exit_time"].isoformat(),
                entry=round(signal["entry"], 6),
                stop=round(signal["stop"], 6),
                tp1=round(signal["tp1"], 6),
                tp2=round(signal["tp2"], 6),
                tp3=round(signal["tp3"], 6),
                r_multiple=round(result["r_multiple"], 4),
                pnl=round(pnl, 2),
                balance_after=round(balance, 2),
                exit_reason=result["exit_reason"],
                bars_held=int(result["exit_index"] - signal["entry_index"]),
                pivot_rsi=round(signal["pivot_rsi"], 2),
                previous_rsi=round(signal["previous_rsi"], 2),
                risk_points=round(result["risk_points"], 6),
                lot=float(sizing["lot"]),
                target_risk=float(sizing["target_risk"]),
                actual_risk=float(sizing["actual_risk"]),
                risk_mode=str(sizing["mode"]),
            )
        )

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    stats = {
        "symbol": display_symbol,
        "broker_symbol": broker_symbol,
        "timeframe": config.timeframe,
        "confirmation": config.confirmation,
        "pivot_len": config.pivot_len,
        "atr_sl_mult": config.atr_sl_mult,
        "rr": "/".join(str(x) for x in config.rr),
        "session": config.session,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100.0, 2) if trades else 0.0,
        "start_balance": round(start_balance, 2),
        "final_balance": round(balance, 2),
        "profit": round(balance - start_balance, 2),
        "return_pct": round((balance - start_balance) / start_balance * 100.0, 2) if start_balance else 0.0,
        "max_drawdown_pct": round(max_dd, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0),
        "avg_r": round(sum(t.r_multiple for t in trades) / len(trades), 3) if trades else 0.0,
        "avg_lot": round(sum(t.lot for t in trades) / len(trades), 3) if trades else 0.0,
        "avg_actual_risk": round(sum(t.actual_risk for t in trades) / len(trades), 2) if trades else 0.0,
        "max_trades_per_day": max_trades_per_day,
        "risk_mode": risk_mode,
        "fixed_lot": fixed_lot,
        "risk_usd_cap": risk_usd_cap,
        "risk_usd_offset": risk_usd_offset,
    }
    return trades, stats


def combined_equity_curve(
    trades: Iterable[TradeIdea],
    start_balance: float,
    risk_percent: float,
    risk_mode: str = "RISK_PERCENT",
) -> tuple[dict, list[dict]]:
    balance = start_balance
    peak = balance
    max_dd = 0.0
    ordered = sorted(trades, key=lambda t: t.entry_time)
    points: list[dict] = [{"time": "", "balance": round(balance, 2), "drawdown_pct": 0.0, "symbol": "START", "r_multiple": 0.0}]
    for trade in ordered:
        if risk_mode.upper() == "RISK_PERCENT":
            pnl = balance * risk_percent / 100.0 * trade.r_multiple
        else:
            pnl = float(trade.actual_risk) * trade.r_multiple
        balance += pnl
        peak = max(peak, balance)
        drawdown = (peak - balance) / peak * 100.0 if peak > 0 else 0.0
        if peak > 0:
            max_dd = max(max_dd, drawdown)
        points.append(
            {
                "time": trade.entry_time,
                "balance": round(balance, 2),
                "drawdown_pct": round(drawdown, 2),
                "symbol": trade.symbol,
                "r_multiple": trade.r_multiple,
            }
        )
    wins = [t for t in ordered if t.r_multiple > 0]
    summary = {
        "trades": len(ordered),
        "win_rate": round(len(wins) / len(ordered) * 100.0, 2) if ordered else 0.0,
        "start_balance": round(start_balance, 2),
        "final_balance": round(balance, 2),
        "profit": round(balance - start_balance, 2),
        "return_pct": round((balance - start_balance) / start_balance * 100.0, 2) if start_balance else 0.0,
        "max_drawdown_pct": round(max_dd, 2),
    }
    return summary, points


def combined_equity(
    trades: Iterable[TradeIdea],
    start_balance: float,
    risk_percent: float,
    risk_mode: str = "RISK_PERCENT",
) -> dict:
    summary, _ = combined_equity_curve(trades, start_balance, risk_percent, risk_mode)
    return summary


def save_equity_outputs(report_dir: Path, points: list[dict]) -> None:
    with (report_dir / "equity_curve.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time", "balance", "drawdown_pct", "symbol", "r_multiple"])
        writer.writeheader()
        writer.writerows(points)

    width, height = 1100, 420
    pad_l, pad_r, pad_t, pad_b = 64, 24, 28, 48
    balances = [float(p["balance"]) for p in points] or [0.0]
    min_balance = min(balances)
    max_balance = max(balances)
    if math.isclose(min_balance, max_balance):
        min_balance -= 1.0
        max_balance += 1.0
    span = max_balance - min_balance

    def xy(index: int, balance: float) -> tuple[float, float]:
        x = pad_l + (width - pad_l - pad_r) * (index / max(1, len(points) - 1))
        y = pad_t + (height - pad_t - pad_b) * (1.0 - (balance - min_balance) / span)
        return x, y

    coords = [xy(i, float(point["balance"])) for i, point in enumerate(points)]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"{pad_l},{height-pad_b} " + polyline + f" {width-pad_r},{height-pad_b}"
    grid = []
    labels = []
    for step in range(5):
        ratio = step / 4
        value = min_balance + span * (1.0 - ratio)
        y = pad_t + (height - pad_t - pad_b) * ratio
        grid.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width-pad_r}" y2="{y:.1f}" stroke="#253044" stroke-width="1"/>')
        labels.append(f'<text x="12" y="{y+4:.1f}" fill="#94a3b8" font-size="12">${value:,.0f}</text>')

    title = f"Equity Curve: ${balances[0]:,.2f} to ${balances[-1]:,.2f}"
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#080d18"/>
  <text x="{pad_l}" y="20" fill="#f8fafc" font-size="16" font-family="Arial">{title}</text>
  {''.join(grid)}
  {''.join(labels)}
  <polygon points="{area}" fill="#10b981" opacity="0.16"/>
  <polyline points="{polyline}" fill="none" stroke="#22c55e" stroke-width="3"/>
  <line x1="{pad_l}" y1="{height-pad_b}" x2="{width-pad_r}" y2="{height-pad_b}" stroke="#334155"/>
  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{height-pad_b}" stroke="#334155"/>
  <text x="{pad_l}" y="{height-16}" fill="#94a3b8" font-size="12" font-family="Arial">start</text>
  <text x="{width-pad_r-34}" y="{height-16}" fill="#94a3b8" font-size="12" font-family="Arial">end</text>
</svg>'''
    (report_dir / "equity_curve.svg").write_text(svg, encoding="utf-8")


def save_report(base: Path, summary: dict, stats: list[dict], trades: list[TradeIdea], skipped: list[dict]) -> Path:
    report_dir = base / "reports" / datetime.now().strftime("%Y%m%d-%H%M%S")
    report_dir.mkdir(parents=True, exist_ok=True)
    _, equity_points = combined_equity_curve(
        trades,
        float(summary["start_balance"]),
        float(summary["risk_percent"]),
        str(summary.get("risk_mode", "RISK_PERCENT")),
    )
    save_equity_outputs(report_dir, equity_points)
    (report_dir / "report.json").write_text(
        json.dumps({"summary": summary, "symbols": stats, "skipped": skipped, "trades": [asdict(t) for t in trades]}, indent=2),
        encoding="utf-8",
    )
    with (report_dir / "symbol_stats.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stats[0].keys()) if stats else ["symbol"])
        writer.writeheader()
        writer.writerows(stats)
    with (report_dir / "trades.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = list(asdict(trades[0]).keys()) if trades else list(TradeIdea.__dataclass_fields__.keys())
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for trade in trades:
            writer.writerow(asdict(trade))
    lines = [
        "# RSI Divergence Backtest",
        "",
        f"- Run time: {datetime.now().isoformat(timespec='seconds')}",
        f"- Lookback days: {summary['days']}",
        f"- Starting balance: ${summary['start_balance']}",
        f"- Risk per trade idea: {summary['risk_percent']}%",
        f"- Sizing mode: {summary.get('risk_mode', 'RISK_PERCENT')}",
        f"- Combined result: ${summary['start_balance']} -> ${summary['combined']['final_balance']} ({summary['combined']['return_pct']}%)",
        f"- Combined trades: {summary['combined']['trades']}",
        f"- Combined win rate: {summary['combined']['win_rate']}%",
        f"- Combined max drawdown: {summary['combined']['max_drawdown_pct']}%",
        "",
        "![Equity Curve](equity_curve.svg)",
        "",
        "## Per Symbol",
        "",
        "| Symbol | Broker | TF | Mode | Trades | Win % | Return % | Final | DD % | PF | Avg R | Avg Lot | Avg Risk |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(stats, key=lambda item: item["return_pct"], reverse=True):
        lines.append(
            f"| {row['symbol']} | {row['broker_symbol']} | {row['timeframe']} | {row['confirmation']} | "
            f"{row['trades']} | {row['win_rate']} | {row['return_pct']} | ${row['final_balance']} | "
            f"{row['max_drawdown_pct']} | {row['profit_factor']} | {row['avg_r']} | {row.get('avg_lot', 0)} | ${row.get('avg_actual_risk', 0)} |"
        )
    if skipped:
        lines.extend(["", "## Skipped", ""])
        for item in skipped:
            lines.append(f"- {item['symbol']}: {item['reason']}")
    (report_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report_dir


def run_backtest(args: argparse.Namespace) -> int:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    configs = DEFAULT_CONFIGS
    max_trades_by_symbol: dict[str, int] = {}
    if args.use_optimized:
        optimized = load_optimized_configs()
        if optimized:
            configs = {**DEFAULT_CONFIGS, **optimized}
            max_trades_by_symbol = load_optimized_max_trades()
            print(f"Loaded optimized configs from {OPTIMIZED_CONFIG_PATH}")
        else:
            print("No optimized_configs.json found; using built-in defaults.")
    all_trades: list[TradeIdea] = []
    stats: list[dict] = []
    skipped: list[dict] = []
    try:
        for symbol in symbols:
            config = configs.get(symbol)
            if not config:
                skipped.append({"symbol": symbol, "reason": "no RSI-divergence config"})
                continue
            broker_symbol = resolve_symbol(symbol)
            if not broker_symbol:
                skipped.append({"symbol": symbol, "reason": "symbol not found in MT5"})
                continue
            symbol_max_trades = max_trades_by_symbol.get(symbol, args.max_trades_per_symbol_day)
            trades, row = backtest_symbol(
                symbol,
                broker_symbol,
                config,
                args.days,
                args.balance,
                args.risk,
                symbol_max_trades,
                args.risk_mode,
                args.fixed_lot,
                args.risk_usd_cap,
                args.risk_usd_offset,
            )
            if "error" in row:
                skipped.append({"symbol": symbol, "reason": row["error"]})
                continue
            all_trades.extend(trades)
            stats.append(row)
            print(
                f"{symbol:7s} {broker_symbol:14s} {row['timeframe']:3s} "
                f"trades={row['trades']:3d} win={row['win_rate']:5.1f}% "
                f"return={row['return_pct']:7.2f}% final=${row['final_balance']:8.2f}"
            )

        combined = combined_equity(all_trades, args.balance, args.risk, args.risk_mode)
        summary = {
            "days": args.days,
            "start_balance": args.balance,
            "risk_percent": args.risk,
            "risk_mode": args.risk_mode,
            "fixed_lot": args.fixed_lot,
            "risk_usd_cap": args.risk_usd_cap,
            "risk_usd_offset": args.risk_usd_offset,
            "max_trades_per_symbol_day": args.max_trades_per_symbol_day,
            "symbols": symbols,
            "combined": combined,
        }
        report_dir = save_report(Path(__file__).resolve().parent, summary, stats, all_trades, skipped)
        print("")
        print(f"COMBINED: ${args.balance:.2f} -> ${combined['final_balance']:.2f} "
              f"({combined['return_pct']:.2f}%), trades={combined['trades']}, "
              f"win={combined['win_rate']:.2f}%, DD={combined['max_drawdown_pct']:.2f}%")
        print(f"Report: {report_dir}")
        if skipped:
            print("Skipped:", "; ".join(f"{x['symbol']}={x['reason']}" for x in skipped))
        return 0
    finally:
        mt5.shutdown()


def is_demo_account() -> bool:
    account = mt5.account_info()
    if account is None:
        return False
    demo_constant = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    if demo_constant is not None and int(account.trade_mode) == int(demo_constant):
        return True
    text = f"{account.server} {getattr(account, 'company', '')}".lower()
    return "demo" in text or "trial" in text


def run_live_once(args: argparse.Namespace, configs: dict[str, SymbolConfig], max_trades_by_symbol: dict[str, int], state: dict) -> list[str]:
    messages: list[str] = []
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    for symbol in symbols:
        config = configs.get(symbol)
        if not config:
            messages.append(f"{symbol}: skipped no config")
            continue
        broker_symbol = resolve_symbol(symbol)
        if not broker_symbol:
            messages.append(f"{symbol}: skipped broker symbol not found")
            continue
        data = get_live_rates(broker_symbol, config.timeframe, args.live_lookback_days)
        if data is None:
            messages.append(f"{symbol}: skipped not enough {config.timeframe} candles")
            continue
        max_age = live_signal_age_minutes(config, args.live_max_signal_age_minutes)
        signal = latest_live_signal(data, config, max_age)
        if not signal:
            messages.append(f"{symbol}: no fresh {config.timeframe} signal")
            continue
        max_daily_ideas = max_trades_by_symbol.get(symbol, args.max_trades_per_symbol_day)
        messages.append(place_live_signal(symbol, broker_symbol, config, signal, args, state, max_daily_ideas))
    return messages


def run_live(args: argparse.Namespace) -> int:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError("MT5 account is not connected.")
        if args.require_demo and not is_demo_account():
            raise RuntimeError(f"Live bot blocked: account {account.login} on {account.server} does not look like a demo/trial account.")
        if args.live_trading and not mt5.terminal_info().trade_allowed:
            raise RuntimeError("Live trading is enabled in env, but MT5 Algo Trading is disabled.")

        optimized = load_optimized_configs() if args.use_optimized else {}
        configs = {**DEFAULT_CONFIGS, **optimized} if optimized else DEFAULT_CONFIGS
        max_trades_by_symbol = load_optimized_max_trades() if optimized else {}
        state = load_live_state()

        mode = "LIVE ORDERS" if args.live_trading else "PAPER SCAN"
        print(f"RSI divergence bot started in {mode} mode.")
        print(f"Account: {account.login} | {account.server} | equity={account.equity:.2f}")
        print(f"Symbols: {args.symbols}")
        print(f"Sizing: {args.risk_mode}, risk%={args.risk}, fixedLot={args.fixed_lot}, usdCap={args.risk_usd_cap}, offset={args.risk_usd_offset}")
        print(
            f"Overtrade guards: cooldown={args.symbol_cooldown_minutes}m, "
            f"default daily ideas/symbol={args.max_trades_per_symbol_day}, "
            f"onePositionPerSymbol={args.live_one_position_per_symbol}"
        )
        print("Press Ctrl+C to stop.")

        while True:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{stamp}] scan")
            for message in run_live_once(args, configs, max_trades_by_symbol, state):
                print(" ", message)
            if args.live_once:
                return 0
            time.sleep(max(5, args.scan_interval_seconds))
    finally:
        mt5.shutdown()


def parse_args() -> argparse.Namespace:
    load_env_file()
    parser = argparse.ArgumentParser(description="RSI divergence MT5 bot/backtester")
    parser.add_argument("--backtest", action="store_true", help="Run historical backtest")
    parser.add_argument("--live-loop", action="store_true", help="Run live MT5 scanner loop")
    parser.add_argument("--live-once", action="store_true", help="Run one live scan cycle and exit")
    parser.add_argument("--days", type=int, default=int(os.getenv("RSI_BACKTEST_DAYS", "60")))
    parser.add_argument("--balance", type=float, default=float(os.getenv("RSI_START_BALANCE", "300")))
    parser.add_argument("--risk", type=float, default=float(os.getenv("RSI_RISK_PERCENT", "4")))
    parser.add_argument("--risk-mode", choices=["RISK_PERCENT", "FIXED_LOT", "USD_RISK_CAP"], default=os.getenv("RSI_RISK_MODE", "RISK_PERCENT").upper())
    parser.add_argument("--fixed-lot", type=float, default=float(os.getenv("RSI_FIXED_LOT", "0.01")))
    parser.add_argument("--risk-usd-cap", type=float, default=float(os.getenv("RSI_RISK_USD_CAP", "12")))
    parser.add_argument("--risk-usd-offset", type=float, default=float(os.getenv("RSI_RISK_USD_OFFSET", "0.50")))
    parser.add_argument("--live-trading", action="store_true", default=os.getenv("RSI_LIVE_TRADING", "false").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--require-demo", action="store_true", default=os.getenv("RSI_REQUIRE_DEMO", "true").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--scan-interval-seconds", type=int, default=int(os.getenv("RSI_SCAN_INTERVAL_SECONDS", "60")))
    parser.add_argument("--live-lookback-days", type=int, default=int(os.getenv("RSI_LIVE_LOOKBACK_DAYS", "14")))
    parser.add_argument("--live-max-signal-age-minutes", type=int, default=int(os.getenv("RSI_LIVE_MAX_SIGNAL_AGE_MINUTES", "10")))
    parser.add_argument("--max-entry-drift-r", type=float, default=float(os.getenv("RSI_MAX_ENTRY_DRIFT_R", "0.35")))
    parser.add_argument("--magic", type=int, default=int(os.getenv("RSI_MAGIC", "7142026")))
    parser.add_argument("--max-spread-points", type=int, default=int(os.getenv("RSI_MAX_SPREAD_POINTS", "350")))
    parser.add_argument("--deviation-points", type=int, default=int(os.getenv("RSI_DEVIATION_POINTS", "30")))
    parser.add_argument("--live-one-position-per-side", action="store_true", default=os.getenv("RSI_LIVE_ONE_POSITION_PER_SIDE", "true").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--live-one-position-per-symbol", action="store_true", default=os.getenv("RSI_LIVE_ONE_POSITION_PER_SYMBOL", "true").lower() in {"1", "true", "yes", "on"})
    parser.add_argument("--max-trades-per-symbol-day", type=int, default=int(os.getenv("RSI_MAX_TRADES_PER_SYMBOL_DAY", "3")))
    parser.add_argument("--symbol-cooldown-minutes", type=int, default=int(os.getenv("RSI_SYMBOL_COOLDOWN_MINUTES", "120")))
    parser.add_argument("--use-optimized", action="store_true", default=os.getenv("RSI_USE_OPTIMIZED", "true").lower() in {"1", "true", "yes", "on"}, help="Use optimized_configs.json when present")
    parser.add_argument(
        "--symbols",
        default=os.getenv("RSI_SYMBOLS", "XAUUSD,XAGUSD,BTCUSD,ETHUSD,EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,EURGBP,AUDCAD,GBPCHF,US30,US100"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    if cli_args.live_loop or cli_args.live_once:
        raise SystemExit(run_live(cli_args))
    raise SystemExit(run_backtest(cli_args))
