from __future__ import annotations

import csv
import itertools
import json
import math
import os
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
REPORT_JSON = BASE_DIR / "news_pulse_backtest_report.json"
REPORT_CSV = BASE_DIR / "news_pulse_event_results.csv"
CALENDAR_ZONE = ZoneInfo("Asia/Jakarta")
UTC = timezone.utc


@dataclass(frozen=True)
class NewsEvent:
    local_time: str
    currency: str
    symbol: str
    name: str

    @property
    def time_utc(self) -> datetime:
        local = datetime.strptime(self.local_time, "%Y-%m-%d %H:%M").replace(
            tzinfo=CALENDAR_ZONE
        )
        return local.astimezone(UTC)


@dataclass(frozen=True)
class StrategyConfig:
    offset_pips: float
    offset_atr: float
    spread_multiple: float
    sl_buffer_pips: float
    sl_buffer_atr: float
    expiry_minutes: int
    hold_minutes: int
    trail_start_r: float
    trail_distance_r: float
    slippage_spreads: float
    mt5_history_offset_hours: float


@dataclass
class EventResult:
    local_time: str
    utc_time: str
    currency: str
    event: str
    symbol: str
    broker_symbol: str
    outcome: str
    direction: str
    setup_high: float
    setup_low: float
    entry: float
    stop_loss: float
    exit_price: float
    exit_reason: str
    exit_time_utc: str
    offset_pips: float
    atr_pips: float
    spread_pips: float
    risk_pips: float
    max_favorable_pips: float
    max_adverse_pips: float
    max_lot_1_200: float
    pnl_usd: float
    return_pct: float
    r_multiple: float
    note: str = ""


# Release times are Forex Factory display times in Asia/Jakarta (UTC+7).
# Same-time release clusters are one event because one OCO straddle covers them.
EVENTS = [
    NewsEvent("2026-05-29 06:30", "JPY", "EURJPY", "Tokyo core CPI"),
    NewsEvent("2026-05-29 19:30", "CAD", "USDCAD", "Canada GDP"),
    NewsEvent("2026-06-01 21:00", "USD", "EURUSD", "ISM manufacturing PMI"),
    NewsEvent("2026-06-02 19:00", "EUR", "EURUSD", "Euro-area flash CPI"),
    NewsEvent("2026-06-05 19:30", "USD", "EURUSD", "US payrolls / unemployment"),
    NewsEvent("2026-06-05 19:30", "CAD", "USDCAD", "Canada employment"),
    NewsEvent("2026-06-10 19:30", "USD", "EURUSD", "US CPI"),
    NewsEvent("2026-06-10 20:45", "CAD", "USDCAD", "Bank of Canada decision"),
    NewsEvent("2026-06-11 19:15", "EUR", "EURUSD", "ECB decision"),
    NewsEvent("2026-06-11 19:30", "USD", "EURUSD", "US PPI"),
    NewsEvent("2026-06-16 10:19", "JPY", "EURJPY", "Bank of Japan decision"),
    NewsEvent("2026-06-16 11:30", "AUD", "EURAUD", "RBA decision"),
    NewsEvent("2026-06-17 19:30", "USD", "EURUSD", "US retail sales"),
    NewsEvent("2026-06-18 01:00", "USD", "EURUSD", "FOMC decision"),
    NewsEvent("2026-06-19 06:30", "JPY", "EURJPY", "Japan national core CPI"),
    NewsEvent("2026-06-19 19:30", "CAD", "USDCAD", "Canada retail sales"),
    NewsEvent("2026-06-22 19:30", "CAD", "USDCAD", "Canada CPI"),
    NewsEvent("2026-06-24 08:30", "AUD", "EURAUD", "Australia CPI"),
    NewsEvent("2026-06-25 08:30", "AUD", "EURAUD", "Australia employment"),
    NewsEvent("2026-06-25 19:30", "USD", "EURUSD", "US core PCE / GDP / durables"),
    NewsEvent("2026-06-26 06:30", "JPY", "EURJPY", "Tokyo core CPI"),
    NewsEvent("2026-06-30 19:30", "CAD", "USDCAD", "Canada GDP"),
    NewsEvent("2026-07-01 16:00", "EUR", "EURUSD", "Euro-area flash CPI"),
    NewsEvent("2026-07-01 19:15", "USD", "EURUSD", "ADP employment"),
    NewsEvent("2026-07-01 21:00", "USD", "EURUSD", "ISM manufacturing PMI"),
    NewsEvent("2026-07-02 19:30", "USD", "EURUSD", "US payrolls / unemployment"),
    NewsEvent("2026-07-06 21:00", "USD", "EURUSD", "ISM services PMI"),
    NewsEvent("2026-07-10 19:30", "CAD", "USDCAD", "Canada employment"),
    NewsEvent("2026-07-14 19:30", "USD", "EURUSD", "US CPI"),
    NewsEvent("2026-07-15 19:30", "USD", "EURUSD", "US PPI"),
    NewsEvent("2026-07-15 20:45", "CAD", "USDCAD", "Bank of Canada decision"),
    NewsEvent("2026-07-16 19:30", "USD", "EURUSD", "US retail sales"),
    NewsEvent("2026-07-20 19:30", "CAD", "USDCAD", "Canada CPI"),
    NewsEvent("2026-07-23 08:30", "AUD", "EURAUD", "Australia employment"),
    NewsEvent("2026-07-23 19:15", "EUR", "EURUSD", "ECB decision"),
    NewsEvent("2026-07-23 19:30", "CAD", "USDCAD", "Canada retail sales"),
    NewsEvent("2026-07-29 08:30", "AUD", "EURAUD", "Australia CPI"),
]


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def env_float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    return float(value) if value else default


def env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_float_list(name: str, default: list[float]) -> list[float]:
    value = os.getenv(name, "").strip()
    return [float(part.strip()) for part in value.split(",")] if value else default


def env_int_list(name: str, default: list[int]) -> list[int]:
    value = os.getenv(name, "").strip()
    return [int(part.strip()) for part in value.split(",")] if value else default


def clean_symbol(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def discover_symbol(wanted: str) -> str:
    wanted_clean = clean_symbol(wanted)
    direct = mt5.symbol_info(wanted)
    if direct and mt5.symbol_select(wanted, True):
        return wanted

    candidates: list[tuple[int, str]] = []
    for item in mt5.symbols_get() or []:
        name_clean = clean_symbol(item.name)
        score = 0
        if name_clean == wanted_clean:
            score = 100
        elif name_clean.startswith(wanted_clean):
            score = 90
        elif wanted_clean in name_clean:
            score = 70
        if score:
            candidates.append((score, item.name))

    for _, name in sorted(candidates, reverse=True):
        info = mt5.symbol_info(name)
        if info and int(info.trade_mode) not in {0, 3} and mt5.symbol_select(name, True):
            return name
    raise RuntimeError(f"Could not resolve broker symbol for {wanted}.")


def pip_size(info: Any) -> float:
    return float(info.point) * (10.0 if int(info.digits) in {3, 5} else 1.0)


def round_volume(value: float, info: Any) -> float:
    minimum = float(info.volume_min or 0.01)
    maximum = float(info.volume_max or value)
    step = float(info.volume_step or 0.01)
    if value < minimum:
        return 0.0
    steps = math.floor((min(value, maximum) - minimum) / step + 1e-9)
    return round(minimum + steps * step, 8)


def max_lot_at_leverage(
    symbol: str,
    balance: float,
    leverage: float,
    margin_use: float,
    eurusd_price: float,
) -> float:
    info = mt5.symbol_info(symbol)
    if info is None or balance <= 0:
        return 0.0
    base = str(info.currency_margin or info.currency_base).upper()
    base_to_usd = eurusd_price if base == "EUR" else 1.0
    margin_per_lot = float(info.trade_contract_size) * base_to_usd / leverage
    if margin_per_lot <= 0:
        return 0.0
    return round_volume(balance * margin_use / margin_per_lot, info)


def load_rates(symbol: str, start: datetime, end: datetime) -> list[dict[str, float]]:
    mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 2)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No M1 rates returned for {symbol}: {mt5.last_error()}")
    return [
        {
            "time": float(row["time"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "spread": float(row["spread"]),
        }
        for row in rates
    ]


def bar_index_before(rates: list[dict[str, float]], timestamp: float) -> int | None:
    low, high = 0, len(rates)
    while low < high:
        middle = (low + high) // 2
        if rates[middle]["time"] < timestamp:
            low = middle + 1
        else:
            high = middle
    return low - 1 if low else None


def average_true_range_pips(
    rates: list[dict[str, float]], index: int, pip: float, length: int = 14
) -> float:
    start = max(1, index - length + 1)
    values: list[float] = []
    for position in range(start, index + 1):
        row = rates[position]
        previous_close = rates[position - 1]["close"]
        true_range = max(
            row["high"] - row["low"],
            abs(row["high"] - previous_close),
            abs(row["low"] - previous_close),
        )
        values.append(true_range / pip)
    return mean(values) if values else 0.0


def historical_eurusd(
    eurusd_rates: list[dict[str, float]], timestamp: float
) -> float:
    index = bar_index_before(eurusd_rates, timestamp + 1)
    if index is None:
        raise RuntimeError("EURUSD conversion history does not cover the event.")
    return float(eurusd_rates[index]["close"])


def pnl_to_usd(
    raw_symbol: str,
    direction: str,
    entry: float,
    exit_price: float,
    lot: float,
    eurusd_price: float,
) -> float:
    signed_move = exit_price - entry if direction == "BUY" else entry - exit_price
    profit_currency_amount = signed_move * 100_000.0 * lot
    if raw_symbol == "EURUSD":
        return profit_currency_amount
    if raw_symbol == "EURAUD":
        audusd = eurusd_price / entry
        return profit_currency_amount * audusd
    if raw_symbol == "EURJPY":
        jpyusd = eurusd_price / entry
        return profit_currency_amount * jpyusd
    if raw_symbol == "USDCAD":
        return profit_currency_amount / entry
    raise ValueError(f"Unsupported symbol conversion: {raw_symbol}")


def simulate_event(
    event: NewsEvent,
    broker_symbol: str,
    rates: list[dict[str, float]],
    eurusd_rates: list[dict[str, float]],
    config: StrategyConfig,
    balance: float,
    leverage: float,
    margin_use: float,
) -> EventResult:
    info = mt5.symbol_info(broker_symbol)
    if info is None:
        raise RuntimeError(f"Missing symbol info for {broker_symbol}.")
    pip = pip_size(info)
    event_timestamp = event.time_utc.timestamp() + (
        config.mt5_history_offset_hours * 3600.0
    )
    setup_index = bar_index_before(rates, event_timestamp)
    if setup_index is None or setup_index < 14:
        return empty_result(event, broker_symbol, "NO_DATA", "No pre-event M1 candle.")

    setup = rates[setup_index]
    atr_pips = average_true_range_pips(rates, setup_index, pip)
    spread_pips = max(0.0, setup["spread"] * float(info.point) / pip)
    offset_pips = max(
        config.offset_pips,
        atr_pips * config.offset_atr,
        spread_pips * config.spread_multiple,
    )
    sl_buffer_pips = max(
        config.sl_buffer_pips, atr_pips * config.sl_buffer_atr
    )
    setup_spread = setup["spread"] * float(info.point)
    # MT5 candles are bid prices. Build the buy side from the ask range and the
    # sell side from the bid range so a wide news spread does not bias triggers.
    buy_entry = setup["high"] + setup_spread + offset_pips * pip
    sell_entry = setup["low"] - offset_pips * pip
    buy_stop = setup["low"] - sl_buffer_pips * pip
    sell_stop = setup["high"] + setup_spread + sl_buffer_pips * pip

    first_index = setup_index + 1
    expiry_timestamp = event_timestamp + config.expiry_minutes * 60
    trigger_index: int | None = None
    direction = ""
    fill = 0.0
    slippage_pips = spread_pips * config.slippage_spreads

    for index in range(first_index, len(rates)):
        row = rates[index]
        if row["time"] >= expiry_timestamp:
            break
        row_spread = row["spread"] * float(info.point)
        ask_high = row["high"] + row_spread
        ask_open = row["open"] + row_spread
        buy_hit = ask_high >= buy_entry
        sell_hit = row["low"] <= sell_entry
        if not buy_hit and not sell_hit:
            continue
        if buy_hit and sell_hit:
            direction = "SELL" if row["close"] >= row["open"] else "BUY"
        else:
            direction = "BUY" if buy_hit else "SELL"
        trigger_index = index
        if direction == "BUY":
            fill = max(buy_entry, ask_open) + slippage_pips * pip
        else:
            fill = min(sell_entry, row["open"]) - slippage_pips * pip
        break

    if trigger_index is None:
        return EventResult(
            event.local_time,
            event.time_utc.isoformat(),
            event.currency,
            event.name,
            event.symbol,
            broker_symbol,
            "NO_TRIGGER",
            "",
            setup["high"],
            setup["low"],
            0.0,
            0.0,
            0.0,
            "pending expired",
            "",
            offset_pips,
            atr_pips,
            spread_pips,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )

    stop = buy_stop if direction == "BUY" else sell_stop
    risk = fill - stop if direction == "BUY" else stop - fill
    if risk <= 0:
        return empty_result(event, broker_symbol, "INVALID", "Non-positive stop distance.")
    risk_pips = risk / pip
    current_stop = stop
    max_favorable = 0.0
    max_adverse = 0.0
    exit_price = 0.0
    exit_reason = "time exit"
    exit_timestamp = rates[trigger_index]["time"]
    horizon = event_timestamp + config.hold_minutes * 60

    for index in range(trigger_index, len(rates)):
        row = rates[index]
        if row["time"] > horizon:
            break
        row_spread = row["spread"] * float(info.point)
        if direction == "BUY":
            favorable = row["high"] - fill
            adverse = fill - row["low"]
            max_favorable = max(max_favorable, favorable)
            max_adverse = max(max_adverse, adverse)
            if row["low"] <= current_stop:
                exit_price = min(current_stop, row["open"])
                exit_reason = "stop/trail"
                exit_timestamp = row["time"]
                break
            if max_favorable >= config.trail_start_r * risk:
                current_stop = max(
                    current_stop,
                    row["high"] - config.trail_distance_r * risk,
                )
            exit_price = row["close"]
        else:
            favorable = fill - (row["low"] + row_spread)
            adverse = row["high"] + row_spread - fill
            max_favorable = max(max_favorable, favorable)
            max_adverse = max(max_adverse, adverse)
            if row["high"] + row_spread >= current_stop:
                exit_price = max(current_stop, row["open"] + row_spread)
                exit_reason = "stop/trail"
                exit_timestamp = row["time"]
                break
            if max_favorable >= config.trail_start_r * risk:
                current_stop = min(
                    current_stop,
                    row["low"] + row_spread + config.trail_distance_r * risk,
                )
            exit_price = row["close"] + row_spread
        exit_timestamp = row["time"]

    eurusd_price = historical_eurusd(eurusd_rates, event_timestamp)
    lot = max_lot_at_leverage(
        broker_symbol, balance, leverage, margin_use, eurusd_price
    )
    pnl = pnl_to_usd(event.symbol, direction, fill, exit_price, lot, eurusd_price)
    pnl = max(pnl, -balance)
    return_pct = pnl / balance * 100.0 if balance else 0.0
    r_multiple = (
        (exit_price - fill) / risk
        if direction == "BUY"
        else (fill - exit_price) / risk
    )
    if pnl > 0.005:
        outcome = "WIN"
    elif pnl < -0.005:
        outcome = "LOSS"
    else:
        outcome = "FLAT"

    return EventResult(
        event.local_time,
        event.time_utc.isoformat(),
        event.currency,
        event.name,
        event.symbol,
        broker_symbol,
        outcome,
        direction,
        setup["high"],
        setup["low"],
        fill,
        stop,
        exit_price,
        exit_reason,
        datetime.fromtimestamp(
            exit_timestamp - config.mt5_history_offset_hours * 3600.0, UTC
        ).isoformat(),
        offset_pips,
        atr_pips,
        spread_pips,
        risk_pips,
        max_favorable / pip,
        max_adverse / pip,
        lot,
        pnl,
        return_pct,
        r_multiple,
    )


def empty_result(
    event: NewsEvent, broker_symbol: str, outcome: str, note: str
) -> EventResult:
    return EventResult(
        event.local_time,
        event.time_utc.isoformat(),
        event.currency,
        event.name,
        event.symbol,
        broker_symbol,
        outcome,
        "",
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        "",
        "",
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        note,
    )


def summarize(results: list[EventResult]) -> dict[str, float | int | None]:
    traded = [item for item in results if item.outcome in {"WIN", "LOSS", "FLAT"}]
    wins = [item for item in traded if item.pnl_usd > 0]
    losses = [item for item in traded if item.pnl_usd < 0]
    gross_profit = sum(item.pnl_usd for item in wins)
    gross_loss = abs(sum(item.pnl_usd for item in losses))
    running = peak = drawdown = 0.0
    for item in traded:
        running += item.return_pct
        peak = max(peak, running)
        drawdown = max(drawdown, peak - running)
    return {
        "events": len(results),
        "triggered": len(traded),
        "wins": len(wins),
        "losses": len(losses),
        "no_trigger": sum(item.outcome == "NO_TRIGGER" for item in results),
        "win_rate_pct": round(len(wins) / len(traded) * 100.0, 2) if traded else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else None,
        "isolated_net_usd": round(sum(item.pnl_usd for item in traded), 2),
        "isolated_net_return_pct": round(sum(item.return_pct for item in traded), 2),
        "average_r": round(mean(item.r_multiple for item in traded), 3)
        if traded
        else 0.0,
        "additive_max_drawdown_pct": round(drawdown, 2),
    }


def sequential_summary(
    events: list[NewsEvent],
    mappings: dict[str, str],
    histories: dict[str, list[dict[str, float]]],
    eurusd_rates: list[dict[str, float]],
    config: StrategyConfig,
    start_balance: float,
    leverage: float,
    margin_use: float,
) -> dict[str, Any]:
    balance = start_balance
    peak = start_balance
    max_drawdown = 0.0
    wins = losses = triggered = skipped_overlap = 0
    last_exit: datetime | None = None

    for event in sorted(events, key=lambda item: item.time_utc):
        if last_exit is not None and event.time_utc < last_exit:
            skipped_overlap += 1
            continue
        result = simulate_event(
            event,
            mappings[event.symbol],
            histories[event.symbol],
            eurusd_rates,
            config,
            balance,
            leverage,
            margin_use,
        )
        if result.outcome not in {"WIN", "LOSS", "FLAT"}:
            continue
        triggered += 1
        wins += int(result.outcome == "WIN")
        losses += int(result.outcome == "LOSS")
        balance = max(0.0, balance + result.pnl_usd)
        peak = max(peak, balance)
        if peak:
            max_drawdown = max(max_drawdown, (peak - balance) / peak * 100.0)
        if result.exit_time_utc:
            last_exit = datetime.fromisoformat(result.exit_time_utc)
        if balance <= 0:
            break

    return {
        "start_balance_usd": round(start_balance, 2),
        "end_balance_usd": round(balance, 2),
        "return_pct": round((balance / start_balance - 1.0) * 100.0, 2),
        "triggered": triggered,
        "wins": wins,
        "losses": losses,
        "skipped_while_previous_trade_open": skipped_overlap,
        "max_drawdown_pct": round(max_drawdown, 2),
    }


def optimize(
    events: list[NewsEvent],
    mappings: dict[str, str],
    histories: dict[str, list[dict[str, float]]],
    eurusd_rates: list[dict[str, float]],
    base_config: StrategyConfig,
    balance: float,
    leverage: float,
    margin_use: float,
) -> tuple[StrategyConfig, list[dict[str, Any]]]:
    offsets = env_float_list("NEWS_OPT_OFFSET_PIPS", [1.0, 2.0, 3.0, 5.0])
    buffers = env_float_list("NEWS_OPT_SL_BUFFER_PIPS", [1.0, 2.0, 3.0, 5.0])
    expiries = env_int_list("NEWS_OPT_EXPIRY_MINUTES", [3, 5])
    trail_starts = env_float_list("NEWS_OPT_TRAIL_START_R", [1.0, 2.0, 3.0, 5.0])
    trail_distances = env_float_list(
        "NEWS_OPT_TRAIL_DISTANCE_R", [0.5, 1.0]
    )
    leaderboard: list[dict[str, Any]] = []

    for offset, buffer, expiry, trail_start, trail_distance in itertools.product(
        offsets, buffers, expiries, trail_starts, trail_distances
    ):
        config = replace(
            base_config,
            offset_pips=offset,
            sl_buffer_pips=buffer,
            expiry_minutes=expiry,
            trail_start_r=trail_start,
            trail_distance_r=trail_distance,
        )
        results = [
            simulate_event(
                event,
                mappings[event.symbol],
                histories[event.symbol],
                eurusd_rates,
                config,
                balance,
                leverage,
                margin_use,
            )
            for event in events
        ]
        stats = summarize(results)
        trigger_ratio = float(stats["triggered"]) / max(1, len(events))
        if trigger_ratio < 0.35:
            continue
        score = float(stats["isolated_net_return_pct"]) - (
            0.20 * float(stats["additive_max_drawdown_pct"])
        )
        leaderboard.append(
            {
                "score": round(score, 3),
                "config": asdict(config),
                "stats": stats,
            }
        )

    leaderboard.sort(
        key=lambda item: (
            float(item["score"]),
            float(item["stats"]["profit_factor"] or 999.0),
            float(item["stats"]["win_rate_pct"]),
        ),
        reverse=True,
    )
    if not leaderboard:
        return base_config, []
    return StrategyConfig(**leaderboard[0]["config"]), leaderboard[:10]


def write_csv(results: list[EventResult]) -> None:
    fields = list(asdict(results[0]).keys()) if results else []
    with REPORT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = asdict(result)
            for key, value in row.items():
                if isinstance(value, float):
                    row[key] = round(value, 5)
            writer.writerow(row)


def main() -> int:
    load_env()
    terminal_path = os.getenv(
        "MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe"
    )
    balance = env_float("NEWS_BACKTEST_START_BALANCE", 100.0)
    leverage = env_float("NEWS_BACKTEST_LEVERAGE", 200.0)
    margin_use = env_float("NEWS_MARGIN_USE_PCT", 100.0) / 100.0
    config = StrategyConfig(
        offset_pips=env_float("NEWS_OFFSET_PIPS", 2.0),
        offset_atr=env_float("NEWS_OFFSET_ATR", 0.25),
        spread_multiple=env_float("NEWS_SPREAD_MULTIPLE", 0.0),
        sl_buffer_pips=env_float("NEWS_SL_BUFFER_PIPS", 2.0),
        sl_buffer_atr=env_float("NEWS_SL_BUFFER_ATR", 0.25),
        expiry_minutes=env_int("NEWS_EXPIRY_MINUTES", 3),
        hold_minutes=env_int("NEWS_HOLD_MINUTES", 120),
        trail_start_r=env_float("NEWS_TRAIL_START_R", 3.0),
        trail_distance_r=env_float("NEWS_TRAIL_DISTANCE_R", 1.0),
        slippage_spreads=env_float("NEWS_SLIPPAGE_SPREADS", 0.5),
        mt5_history_offset_hours=env_float("NEWS_MT5_HISTORY_OFFSET_HOURS", 3.0),
    )

    if not mt5.initialize(path=terminal_path):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        mappings = {raw: discover_symbol(raw) for raw in sorted({e.symbol for e in EVENTS})}
        history_shift = timedelta(hours=config.mt5_history_offset_hours)
        start = min(event.time_utc for event in EVENTS) + history_shift - timedelta(hours=2)
        end = max(event.time_utc for event in EVENTS) + history_shift + timedelta(hours=3)
        histories = {
            raw: load_rates(broker, start, end) for raw, broker in mappings.items()
        }
        eurusd_rates = histories["EURUSD"]

        leaderboard: list[dict[str, Any]] = []
        if env_bool("NEWS_OPTIMIZE", True):
            config, leaderboard = optimize(
                EVENTS,
                mappings,
                histories,
                eurusd_rates,
                config,
                balance,
                leverage,
                margin_use,
            )

        results = [
            simulate_event(
                event,
                mappings[event.symbol],
                histories[event.symbol],
                eurusd_rates,
                config,
                balance,
                leverage,
                margin_use,
            )
            for event in EVENTS
        ]
        by_symbol = {
            symbol: summarize([item for item in results if item.symbol == symbol])
            for symbol in sorted(mappings)
        }
        sequential_by_symbol = {
            symbol: sequential_summary(
                [event for event in EVENTS if event.symbol == symbol],
                mappings,
                histories,
                eurusd_rates,
                config,
                balance,
                leverage,
                margin_use,
            )
            for symbol in sorted(mappings)
        }
        report = {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "source_account": {
                "login": int(account.login) if account else None,
                "server": str(account.server) if account else None,
                "actual_leverage_not_used": int(account.leverage) if account else None,
            },
            "assumptions": {
                "start_balance_per_event_usd": balance,
                "simulated_leverage": leverage,
                "margin_use_pct": margin_use * 100.0,
                "position_sizing": "maximum broker-normalized lot per isolated event",
                "pending_model": "OCO; opposite side cancelled after first trigger",
                "calendar_timezone": str(CALENDAR_ZONE),
                "mt5_history_offset_hours": config.mt5_history_offset_hours,
                "data_granularity": "MT5 M1 bid OHLC plus recorded spread",
            },
            "symbol_mapping": mappings,
            "best_config": asdict(config),
            "overall": summarize(results),
            "by_symbol": by_symbol,
            "sequential_by_symbol": sequential_by_symbol,
            "leaderboard": leaderboard,
            "events": [asdict(item) for item in results],
        }
        REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
        write_csv(results)

        print(f"MT5 account: {account.login if account else '?'} / {account.server if account else '?'}")
        print(f"Mappings: {mappings}")
        print(f"Best config: {asdict(config)}")
        print(f"Overall: {report['overall']}")
        for symbol, stats in by_symbol.items():
            print(f"{symbol}: {stats}")
        print(f"JSON report: {REPORT_JSON}")
        print(f"CSV events: {REPORT_CSV}")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
