from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

from .config import REPORTS_DIR, load_config
from .mt5_client import MT5Client, TIMEFRAME_MINUTES
from .session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, as_aware, date_in_timezone


SUITE_REPORT_DIR = REPORTS_DIR / "strategy_suite"
SUITE_REPORT_DIR.mkdir(parents=True, exist_ok=True)

FOREX = {"AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"}
DEFAULT_POINT_BY_SYMBOL = {
    "XAUUSD": 0.01,
    "XAGUSD": 0.001,
    "BTCUSD": 0.01,
    "US30": 0.1,
    "US300": 0.1,
}


@dataclass(frozen=True)
class SuiteBotConfig:
    bot_id: str
    name: str
    symbols: tuple[str, ...]
    timeframe: str
    risk_pct: float
    rr: float
    max_trades_per_day: int
    enabled: bool = True
    session: str = "00:00-23:59"
    notes: str = ""


@dataclass(frozen=True)
class SuiteSignal:
    bot: str
    symbol: str
    timeframe: str
    opened_at: datetime
    start_index: int
    direction: str
    entry: float
    stop_loss: float
    final_rr: float
    setup_score: int
    reason: str
    spread_price: float
    spread_points: float
    atr: float


@dataclass
class SuiteTrade:
    bot: str
    symbol: str
    timeframe: str
    month: str
    opened_at: str
    closed_at: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    exit_price: float
    result: str
    r_multiple: float
    setup_score: int
    spread_r: float
    spread_points: float
    atr: float
    reason: str


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if value in {"US30_10M", "US30-10M", "US30_10"}:
        return "US30"
    return value


def suite_bot_configs() -> dict[str, SuiteBotConfig]:
    load_config()
    return {
        "grid": SuiteBotConfig(
            bot_id="grid",
            name="Grid Range Bot",
            symbols=_csv_env("GRID_SYMBOLS", ("AUDUSD", "USDCAD", "NZDUSD", "GBPUSD")),
            timeframe=os.getenv("GRID_TIMEFRAME", "M15").strip().upper() or "M15",
            risk_pct=_float_env("GRID_RISK_PCT", 2.0),
            rr=_float_env("GRID_RR", 1.4),
            max_trades_per_day=_int_env("GRID_MAX_TRADES_PER_DAY", 3),
            enabled=_bool_env("GRID_ENABLED", True),
            session=os.getenv("GRID_ALLOWED_SESSIONS", "19:00-02:00"),
            notes="Trades range bounces only when ADX is low and price is near an outer Bollinger grid.",
        ),
        "trend": SuiteBotConfig(
            bot_id="trend",
            name="Trend Following Bot",
            symbols=_csv_env("TREND_SYMBOLS", ("BTCUSD", "XAUUSD", "US30", "GBPJPY")),
            timeframe=os.getenv("TREND_TIMEFRAME", "H1").strip().upper() or "H1",
            risk_pct=_float_env("TREND_RISK_PCT", 5.0),
            rr=_float_env("TREND_RR", 3.0),
            max_trades_per_day=_int_env("TREND_MAX_TRADES_PER_DAY", 3),
            enabled=_bool_env("TREND_ENABLED", True),
            session=os.getenv("TREND_ALLOWED_SESSIONS", "08:00-17:00"),
            notes="Uses EMA trend alignment, ADX strength, and breakout confirmation.",
        ),
        "mean_reversion": SuiteBotConfig(
            bot_id="mean_reversion",
            name="Mean Reversion Bot",
            symbols=_csv_env("MEANREV_SYMBOLS", ("AUDUSD", "USDCAD", "NZDUSD", "GBPUSD", "XAUUSD")),
            timeframe=os.getenv("MEANREV_TIMEFRAME", "M15").strip().upper() or "M15",
            risk_pct=_float_env("MEANREV_RISK_PCT", 3.0),
            rr=_float_env("MEANREV_RR", 2.0),
            max_trades_per_day=_int_env("MEANREV_MAX_TRADES_PER_DAY", 3),
            enabled=_bool_env("MEANREV_ENABLED", True),
            session=os.getenv("MEANREV_ALLOWED_SESSIONS", "19:00-02:00"),
            notes="Trades RSI/Bollinger overextensions back toward the mean.",
        ),
        "dca": SuiteBotConfig(
            bot_id="dca",
            name="DCA Dip Bot",
            symbols=_csv_env("DCA_SYMBOLS", ("BTCUSD", "XAUUSD")),
            timeframe=os.getenv("DCA_TIMEFRAME", "H4").strip().upper() or "H4",
            risk_pct=_float_env("DCA_RISK_PCT", 1.0),
            rr=_float_env("DCA_RR", 1.8),
            max_trades_per_day=_int_env("DCA_MAX_TRADES_PER_DAY", 1),
            enabled=_bool_env("DCA_ENABLED", True),
            session=os.getenv("DCA_ALLOWED_SESSIONS", "00:00-23:59"),
            notes="Long-only dip accumulation with a protective stop and mean target.",
        ),
        "news": SuiteBotConfig(
            bot_id="news",
            name="News Pulse Bot",
            symbols=_csv_env("NEWS_SYMBOLS", ("XAUUSD", "XAGUSD", "BTCUSD", "US30")),
            timeframe=os.getenv("NEWS_TIMEFRAME", "M1").strip().upper() or "M1",
            risk_pct=_float_env("NEWS_RISK_PCT", 3.0),
            rr=_float_env("NEWS_RR", 2.0),
            max_trades_per_day=_int_env("NEWS_MAX_TRADES_PER_DAY", 3),
            enabled=_bool_env("NEWS_ENABLED", True),
            session=os.getenv("NEWS_ALLOWED_SESSIONS", "08:00-15:00"),
            notes="Pre-news breakout straddle. OpenAI bias is optional when news text/API key is configured.",
        ),
        "arbitrage": SuiteBotConfig(
            bot_id="arbitrage",
            name="Arbitrage Framework",
            symbols=_csv_env("ARBITRAGE_SYMBOLS", ("BTCUSD",)),
            timeframe=os.getenv("ARBITRAGE_TIMEFRAME", "M1").strip().upper() or "M1",
            risk_pct=_float_env("ARBITRAGE_RISK_PCT", 1.0),
            rr=_float_env("ARBITRAGE_RR", 1.0),
            max_trades_per_day=_int_env("ARBITRAGE_MAX_TRADES_PER_DAY", 0),
            enabled=_bool_env("ARBITRAGE_ENABLED", False),
            session="00:00-23:59",
            notes="Disabled until at least two independent price feeds are configured.",
        ),
    }


def is_forex_symbol(symbol: str) -> bool:
    symbol = normalize_symbol(symbol)
    return len(symbol) == 6 and symbol[:3] in FOREX and symbol[3:] in FOREX


def infer_point(symbol: str) -> float:
    symbol = normalize_symbol(symbol)
    if symbol in DEFAULT_POINT_BY_SYMBOL:
        return DEFAULT_POINT_BY_SYMBOL[symbol]
    if symbol.endswith("JPY") and is_forex_symbol(symbol):
        return 0.001
    if is_forex_symbol(symbol):
        return 0.00001
    return 0.01


def normalize_candles(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    df["time"] = pd.to_datetime(df["time"])
    for column in ("open", "high", "low", "close"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if "spread" not in df.columns:
        df["spread"] = 0.0
    df["spread"] = pd.to_numeric(df["spread"], errors="coerce").fillna(0.0)
    return df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"].astype(float)
    high = out["high"].astype(float)
    low = out["low"].astype(float)
    previous = close.shift(1)
    tr = pd.concat([(high - low), (high - previous).abs(), (low - previous).abs()], axis=1).max(axis=1)
    out["atr"] = tr.rolling(14).mean()
    out["ema20"] = close.ewm(span=20, adjust=False).mean()
    out["ema50"] = close.ewm(span=50, adjust=False).mean()
    out["ema100"] = close.ewm(span=100, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    out["bb_mid"] = mid
    out["bb_upper"] = mid + 2 * std
    out["bb_lower"] = mid - 2 * std
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, math.nan)
    out["rsi"] = 100 - (100 / (1 + rs))
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr = out["atr"].replace(0, math.nan)
    plus_di = 100 * plus_dm.rolling(14).sum() / atr
    minus_di = 100 * minus_dm.rolling(14).sum() / atr
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, math.nan)).fillna(0.0)
    out["adx"] = dx.rolling(14).mean()
    out["range_high_20"] = high.rolling(20).max()
    out["range_low_20"] = low.rolling(20).min()
    return out


def parse_sessions(value: str) -> list[tuple[int, int]]:
    sessions: list[tuple[int, int]] = []
    for chunk in value.split(","):
        label = chunk.strip()
        if not label or "-" not in label:
            continue
        start, end = label.split("-", 1)
        try:
            start_h, start_m = [int(part) for part in start.strip().split(":", 1)]
            end_h, end_m = [int(part) for part in end.strip().split(":", 1)]
        except ValueError:
            continue
        sessions.append((start_h * 60 + start_m, end_h * 60 + end_m))
    return sessions


def in_sessions(value: datetime, session_text: str, data_timezone: str, session_timezone: str) -> bool:
    sessions = parse_sessions(session_text)
    if not sessions:
        return True
    local = as_aware(value, data_timezone).astimezone(as_aware(datetime.now(), session_timezone).tzinfo)
    minutes = local.hour * 60 + local.minute
    for start, end in sessions:
        if start <= end and start <= minutes <= end:
            return True
        if start > end and (minutes >= start or minutes <= end):
            return True
    return False


def spread_price_for(row: pd.Series, symbol: str) -> tuple[float, float]:
    points = max(0.0, float(row.get("spread") or 0.0))
    price = points * infer_point(symbol) * max(0.0, _float_env("BACKTEST_SPREAD_MULTIPLIER", 1.0))
    return price, points


def adjusted_score(base: int, risk: float, spread_price: float) -> int:
    if risk <= 0:
        return 0
    spread_r = spread_price / risk
    penalty = int(round(spread_r * 100))
    return max(1, min(100, base - penalty))


def price_at_r(entry: float, risk: float, direction: str, r_value: float) -> float:
    return entry + risk * r_value if direction == "BUY" else entry - risk * r_value


def simulate_trade(df: pd.DataFrame, signal: SuiteSignal, max_bars: int, partial_fraction: float = 0.5) -> SuiteTrade | None:
    direction = signal.direction.upper()
    risk = abs(signal.entry - signal.stop_loss)
    if risk <= 0:
        return None
    end_index = min(len(df) - 1, signal.start_index + max(1, max_bars))
    path = df.iloc[signal.start_index : end_index + 1]
    if path.empty:
        return None

    spread_r = signal.spread_price / risk
    current_sl_r = -1.0
    stage = 0
    remaining = 1.0
    realized_r = -spread_r
    exit_price = float(path.iloc[-1]["close"])
    closed_at = pd.Timestamp(path.iloc[-1]["time"]).to_pydatetime()
    result = "timeout"
    final_tp = price_at_r(signal.entry, risk, direction, signal.final_rr)

    for _, row in path.iterrows():
        high = float(row["high"])
        low = float(row["low"])
        happened_at = pd.Timestamp(row["time"]).to_pydatetime()
        current_sl = price_at_r(signal.entry, risk, direction, current_sl_r)
        if direction == "BUY":
            if low <= current_sl:
                exit_price = current_sl
                closed_at = happened_at
                result = "loss" if current_sl_r < -0.05 else "trail_stop"
                realized_r += remaining * current_sl_r
                break
            if high >= final_tp:
                exit_price = final_tp
                closed_at = happened_at
                result = "win"
                realized_r += remaining * signal.final_rr
                break
            while stage < int(math.floor(signal.final_rr)) and high >= price_at_r(signal.entry, risk, direction, stage + 1):
                stage += 1
                if stage == 1 and partial_fraction > 0:
                    close_fraction = min(partial_fraction, remaining)
                    realized_r += close_fraction
                    remaining -= close_fraction
                    current_sl_r = max(current_sl_r, 0.0)
                elif stage >= 2:
                    current_sl_r = max(current_sl_r, float(stage - 1))
        else:
            if high >= current_sl:
                exit_price = current_sl
                closed_at = happened_at
                result = "loss" if current_sl_r < -0.05 else "trail_stop"
                realized_r += remaining * current_sl_r
                break
            if low <= final_tp:
                exit_price = final_tp
                closed_at = happened_at
                result = "win"
                realized_r += remaining * signal.final_rr
                break
            while stage < int(math.floor(signal.final_rr)) and low <= price_at_r(signal.entry, risk, direction, stage + 1):
                stage += 1
                if stage == 1 and partial_fraction > 0:
                    close_fraction = min(partial_fraction, remaining)
                    realized_r += close_fraction
                    remaining -= close_fraction
                    current_sl_r = max(current_sl_r, 0.0)
                elif stage >= 2:
                    current_sl_r = max(current_sl_r, float(stage - 1))
    else:
        raw_r = (exit_price - signal.entry) / risk if direction == "BUY" else (signal.entry - exit_price) / risk
        realized_r += remaining * raw_r

    return SuiteTrade(
        bot=signal.bot,
        symbol=signal.symbol,
        timeframe=signal.timeframe,
        month=signal.opened_at.strftime("%Y-%m"),
        opened_at=signal.opened_at.isoformat(sep=" ", timespec="seconds"),
        closed_at=closed_at.isoformat(sep=" ", timespec="seconds"),
        direction=direction,
        entry=round(signal.entry, 6),
        stop_loss=round(signal.stop_loss, 6),
        take_profit=round(final_tp, 6),
        exit_price=round(exit_price, 6),
        result=result,
        r_multiple=round(float(realized_r), 4),
        setup_score=signal.setup_score,
        spread_r=round(float(spread_r), 4),
        spread_points=round(float(signal.spread_points), 2),
        atr=round(float(signal.atr), 6),
        reason=signal.reason,
    )


def _signal_from_row(
    bot: str,
    symbol: str,
    timeframe: str,
    index: int,
    row: pd.Series,
    direction: str,
    stop_distance: float,
    rr: float,
    base_score: int,
    reason: str,
) -> SuiteSignal | None:
    if stop_distance <= 0:
        return None
    entry = float(row["close"])
    stop = entry - stop_distance if direction == "BUY" else entry + stop_distance
    spread_price, spread_points = spread_price_for(row, symbol)
    score = adjusted_score(base_score, stop_distance, spread_price)
    max_spread_r = _float_env("SUITE_MAX_SPREAD_R", 0.18)
    if max_spread_r > 0 and spread_price / stop_distance > max_spread_r:
        return None
    return SuiteSignal(
        bot=bot,
        symbol=symbol,
        timeframe=timeframe,
        opened_at=pd.Timestamp(row["time"]).to_pydatetime(),
        start_index=index,
        direction=direction,
        entry=entry,
        stop_loss=stop,
        final_rr=rr,
        setup_score=score,
        reason=reason,
        spread_price=spread_price,
        spread_points=spread_points,
        atr=float(row.get("atr") or 0.0),
    )


def generate_grid_signals(df: pd.DataFrame, symbol: str, config: SuiteBotConfig) -> list[SuiteSignal]:
    signals: list[SuiteSignal] = []
    for index in range(80, len(df)):
        row = df.iloc[index]
        atr = float(row.get("atr") or 0.0)
        if atr <= 0 or float(row.get("adx") or 100) > _float_env("GRID_MAX_ADX", 18.0):
            continue
        close = float(row["close"])
        lower = float(row.get("bb_lower") or math.nan)
        upper = float(row.get("bb_upper") or math.nan)
        if not math.isfinite(lower) or not math.isfinite(upper):
            continue
        if close <= lower:
            signal = _signal_from_row("Grid", symbol, config.timeframe, index, row, "BUY", atr * 1.35, config.rr, 88, "Range grid buy at lower Bollinger band.")
        elif close >= upper:
            signal = _signal_from_row("Grid", symbol, config.timeframe, index, row, "SELL", atr * 1.35, config.rr, 88, "Range grid sell at upper Bollinger band.")
        else:
            signal = None
        if signal:
            signals.append(signal)
    return signals


def generate_trend_signals(df: pd.DataFrame, symbol: str, config: SuiteBotConfig) -> list[SuiteSignal]:
    signals: list[SuiteSignal] = []
    for index in range(220, len(df)):
        row = df.iloc[index]
        previous = df.iloc[index - 1]
        atr = float(row.get("atr") or 0.0)
        if atr <= 0 or float(row.get("adx") or 0.0) < _float_env("TREND_MIN_ADX", 22.0):
            continue
        close = float(row["close"])
        if close > float(row["ema50"]) > float(row["ema200"]) and close >= float(previous.get("range_high_20") or close + 1):
            signal = _signal_from_row("Trend", symbol, config.timeframe, index, row, "BUY", atr * 1.5, config.rr, 91, "EMA trend aligned with ADX breakout.")
        elif close < float(row["ema50"]) < float(row["ema200"]) and close <= float(previous.get("range_low_20") or close - 1):
            signal = _signal_from_row("Trend", symbol, config.timeframe, index, row, "SELL", atr * 1.5, config.rr, 91, "EMA trend aligned with ADX breakdown.")
        else:
            signal = None
        if signal:
            signals.append(signal)
    return signals


def generate_mean_reversion_signals(df: pd.DataFrame, symbol: str, config: SuiteBotConfig) -> list[SuiteSignal]:
    signals: list[SuiteSignal] = []
    for index in range(80, len(df)):
        row = df.iloc[index]
        atr = float(row.get("atr") or 0.0)
        rsi = float(row.get("rsi") or 50.0)
        close = float(row["close"])
        lower = float(row.get("bb_lower") or math.nan)
        upper = float(row.get("bb_upper") or math.nan)
        adx = float(row.get("adx") or 0.0)
        if atr <= 0 or not math.isfinite(lower) or not math.isfinite(upper) or adx > _float_env("MEANREV_MAX_ADX", 24.0):
            continue
        if rsi <= _float_env("MEANREV_RSI_BUY", 28.0) and close <= lower:
            signal = _signal_from_row("MeanReversion", symbol, config.timeframe, index, row, "BUY", atr * 1.25, config.rr, 90, "Oversold RSI plus lower Bollinger extension.")
        elif rsi >= _float_env("MEANREV_RSI_SELL", 72.0) and close >= upper:
            signal = _signal_from_row("MeanReversion", symbol, config.timeframe, index, row, "SELL", atr * 1.25, config.rr, 90, "Overbought RSI plus upper Bollinger extension.")
        else:
            signal = None
        if signal:
            signals.append(signal)
    return signals


def generate_dca_signals(df: pd.DataFrame, symbol: str, config: SuiteBotConfig) -> list[SuiteSignal]:
    signals: list[SuiteSignal] = []
    for index in range(220, len(df)):
        row = df.iloc[index]
        atr = float(row.get("atr") or 0.0)
        close = float(row["close"])
        ema100 = float(row.get("ema100") or close)
        ema200 = float(row.get("ema200") or close)
        rsi = float(row.get("rsi") or 50.0)
        if atr <= 0:
            continue
        if ema100 > ema200 and close < ema100 - atr * _float_env("DCA_DIP_ATR", 1.0) and rsi < _float_env("DCA_MAX_RSI", 45.0):
            signal = _signal_from_row("DCA", symbol, config.timeframe, index, row, "BUY", atr * 2.4, config.rr, 86, "Trend-up dip accumulation entry.")
            if signal:
                signals.append(signal)
    return signals


def _news_event_minutes() -> tuple[str, ...]:
    value = os.getenv("NEWS_EVENT_TIMES", "08:30,10:00,14:00")
    return tuple(item.strip() for item in value.split(",") if item.strip())


def generate_news_signals(df: pd.DataFrame, symbol: str, config: SuiteBotConfig) -> list[SuiteSignal]:
    signals: list[SuiteSignal] = []
    if config.timeframe not in {"M1", "M5"}:
        return signals
    session_tz = os.getenv("NEWS_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE)
    data_tz = os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE)
    event_times = set(_news_event_minutes())
    lookback = max(3, _int_env("NEWS_PRE_RANGE_BARS", 3))
    for index in range(max(30, lookback + 1), len(df)):
        row = df.iloc[index]
        happened_at = pd.Timestamp(row["time"]).to_pydatetime()
        local = as_aware(happened_at, data_tz).astimezone(as_aware(datetime.now(), session_tz).tzinfo)
        if local.strftime("%H:%M") not in event_times:
            continue
        prior = df.iloc[index - lookback : index]
        if prior.empty:
            continue
        high = float(prior["high"].max())
        low = float(prior["low"].min())
        width = high - low
        atr = float(row.get("atr") or 0.0)
        if atr <= 0 or width <= 0:
            continue
        # Backtestable version of the news bot uses an OCO straddle. The live bot can bias one side with OpenAI.
        current_high = float(row["high"])
        current_low = float(row["low"])
        if current_high >= high and current_low <= low:
            continue
        if current_high >= high:
            signal = _signal_from_row("NewsPulse", symbol, config.timeframe, index, row, "BUY", max(width, atr * 0.8), config.rr, 92, f"News straddle buy pulse around {local.strftime('%H:%M')} NY.")
        elif current_low <= low:
            signal = _signal_from_row("NewsPulse", symbol, config.timeframe, index, row, "SELL", max(width, atr * 0.8), config.rr, 92, f"News straddle sell pulse around {local.strftime('%H:%M')} NY.")
        else:
            signal = None
        if signal:
            signals.append(signal)
    return signals


SIGNAL_GENERATORS = {
    "grid": generate_grid_signals,
    "trend": generate_trend_signals,
    "mean_reversion": generate_mean_reversion_signals,
    "dca": generate_dca_signals,
    "news": generate_news_signals,
}


def generate_signals_for_bot(df: pd.DataFrame, symbol: str, config: SuiteBotConfig) -> list[SuiteSignal]:
    generator = SIGNAL_GENERATORS.get(config.bot_id)
    if generator is None:
        return []
    return generator(df, symbol, config)


def select_trades(trades: list[SuiteTrade], max_per_day: int) -> list[SuiteTrade]:
    selected: list[SuiteTrade] = []
    counts: dict[tuple[str, str], int] = {}
    open_until: dict[tuple[str, str], datetime] = {}
    ranked = sorted(trades, key=lambda item: (item.opened_at, -item.setup_score, -item.r_multiple, item.symbol))
    for trade in ranked:
        opened = datetime.fromisoformat(trade.opened_at)
        closed = datetime.fromisoformat(trade.closed_at)
        day = opened.date().isoformat()
        key = (trade.bot, day)
        sym_key = (trade.bot, trade.symbol)
        if max_per_day > 0 and counts.get(key, 0) >= max_per_day:
            continue
        if open_until.get(sym_key, datetime.min) > opened:
            continue
        selected.append(trade)
        counts[key] = counts.get(key, 0) + 1
        open_until[sym_key] = closed
    return selected


def summarize_trades(trades: list[SuiteTrade], starting_balance: float, risk_pct: float) -> tuple[dict[str, Any], pd.DataFrame]:
    balance = float(starting_balance)
    peak = balance
    max_drawdown = 0.0
    rows: list[dict[str, Any]] = []
    for trade in sorted(trades, key=lambda item: (item.opened_at, item.bot, item.symbol)):
        risk_amount = balance * risk_pct / 100.0
        pnl = risk_amount * trade.r_multiple
        before = balance
        balance = max(0.0, balance + pnl)
        peak = max(peak, balance)
        max_drawdown = max(max_drawdown, (peak - balance) / peak if peak > 0 else 0.0)
        row = asdict(trade)
        row.update({"balance_before": round(before, 2), "risk_amount": round(risk_amount, 2), "pnl": round(pnl, 2), "balance_after": round(balance, 2)})
        rows.append(row)
    wins = sum(1 for item in trades if item.r_multiple > 0)
    losses = sum(1 for item in trades if item.r_multiple < 0)
    summary = {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(balance, 2),
        "net_profit": round(balance - starting_balance, 2),
        "return_pct": round((balance / starting_balance - 1) * 100, 2) if starting_balance else 0.0,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades) * 100, 2) if trades else 0.0,
        "net_r": round(sum(float(item.r_multiple) for item in trades), 2),
        "avg_spread_r": round(sum(float(item.spread_r) for item in trades) / len(trades), 4) if trades else 0.0,
        "max_drawdown_pct": round(max_drawdown * 100, 2),
    }
    return summary, pd.DataFrame(rows)


def backtest_strategy_suite(
    start: date,
    end: date,
    starting_balance: float = 300.0,
    risk_pct: float = 5.0,
    bot_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    configs = suite_bot_configs()
    selected_configs = [configs[item] for item in (bot_ids or tuple(configs)) if item in configs and item != "arbitrage"]
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)
    client = MT5Client()
    status = client.terminal_status()
    all_trades: list[SuiteTrade] = []
    availability: list[dict[str, Any]] = []
    max_holding = {
        "grid": _int_env("GRID_MAX_HOLDING_BARS", 24),
        "trend": _int_env("TREND_MAX_HOLDING_BARS", 96),
        "mean_reversion": _int_env("MEANREV_MAX_HOLDING_BARS", 36),
        "dca": _int_env("DCA_MAX_HOLDING_BARS", 60),
        "news": _int_env("NEWS_MAX_HOLDING_BARS", 30),
    }
    for config in selected_configs:
        if not config.enabled:
            availability.append({"bot": config.bot_id, "status": "disabled"})
            continue
        for raw_symbol in config.symbols:
            symbol = normalize_symbol(raw_symbol)
            fetch_start = start_dt - timedelta(days=20)
            candles = client.fetch_candles(symbol, config.timeframe, fetch_start, end_dt, max_bars=80000)
            if candles is None or len(candles) < 250:
                availability.append({"bot": config.bot_id, "symbol": symbol, "timeframe": config.timeframe, "status": "no_history", "candles": 0 if candles is None else len(candles)})
                continue
            df = add_indicators(normalize_candles(candles))
            raw_signals = generate_signals_for_bot(df, symbol, config)
            filtered_signals = [
                signal
                for signal in raw_signals
                if start_dt <= signal.opened_at <= end_dt
                and in_sessions(signal.opened_at, config.session, os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE), os.getenv("MARKET_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE))
            ]
            trades = [
                trade
                for signal in filtered_signals
                for trade in [simulate_trade(df, signal, max_holding.get(config.bot_id, 48))]
                if trade is not None
            ]
            selected = select_trades(trades, config.max_trades_per_day)
            all_trades.extend(selected)
            availability.append(
                {
                    "bot": config.bot_id,
                    "symbol": symbol,
                    "timeframe": config.timeframe,
                    "status": "ok",
                    "candles": len(df),
                    "signals": len(filtered_signals),
                    "selected_trades": len(selected),
                }
            )
    client.shutdown()

    summary, trades_frame = summarize_trades(all_trades, starting_balance, risk_pct)
    by_bot: list[dict[str, Any]] = []
    by_symbol: list[dict[str, Any]] = []
    monthly: list[dict[str, Any]] = []
    if all_trades:
        for bot in sorted({item.bot for item in all_trades}):
            bot_trades = [item for item in all_trades if item.bot == bot]
            item, _ = summarize_trades(bot_trades, starting_balance, risk_pct)
            item["bot"] = bot
            by_bot.append(item)
        for key in sorted({(item.bot, item.symbol) for item in all_trades}):
            bot, symbol = key
            symbol_trades = [item for item in all_trades if item.bot == bot and item.symbol == symbol]
            item, _ = summarize_trades(symbol_trades, starting_balance, risk_pct)
            item.update({"bot": bot, "symbol": symbol})
            by_symbol.append(item)
        for key in sorted({(item.month, item.bot) for item in all_trades}):
            month, bot = key
            group = [item for item in all_trades if item.month == month and item.bot == bot]
            item, _ = summarize_trades(group, starting_balance, risk_pct)
            item.update({"month": month, "bot": bot})
            monthly.append(item)
    by_bot.sort(key=lambda item: float(item["ending_balance"]), reverse=True)
    by_symbol.sort(key=lambda item: float(item["ending_balance"]), reverse=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = SUITE_REPORT_DIR / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    trades_path = out_dir / "strategy_suite_trades.csv"
    bot_path = out_dir / "strategy_suite_by_bot.csv"
    symbol_path = out_dir / "strategy_suite_by_symbol.csv"
    monthly_path = out_dir / "strategy_suite_monthly.csv"
    report_path = out_dir / "strategy_suite_report.json"
    trades_frame.to_csv(trades_path, index=False)
    pd.DataFrame(by_bot).to_csv(bot_path, index=False)
    pd.DataFrame(by_symbol).to_csv(symbol_path, index=False)
    pd.DataFrame(monthly).to_csv(monthly_path, index=False)
    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "starting_balance": starting_balance,
        "risk_pct": risk_pct,
        "mt5_status": status,
        "spread_model": {
            "enabled": True,
            "description": "Each trade is charged one historical MT5 spread as an R-multiple cost.",
            "max_spread_r": _float_env("SUITE_MAX_SPREAD_R", 0.18),
            "spread_multiplier": _float_env("BACKTEST_SPREAD_MULTIPLIER", 1.0),
        },
        "summary": summary,
        "by_bot": by_bot,
        "by_symbol": by_symbol,
        "monthly": monthly,
        "availability": availability,
        "bot_configs": {key: asdict(value) for key, value in configs.items()},
        "paths": {
            "trades": str(trades_path),
            "by_bot": str(bot_path),
            "by_symbol": str(symbol_path),
            "monthly": str(monthly_path),
        },
    }
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["path"] = str(report_path)
    return report


def latest_suite_report() -> dict[str, Any] | None:
    reports = sorted(SUITE_REPORT_DIR.glob("*/strategy_suite_report.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not reports:
        return None
    return json.loads(reports[0].read_text(encoding="utf-8"))


def challenge_entry_candidates(start: date, end: date, symbols: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    configs = suite_bot_configs()
    allowed = ("trend", "mean_reversion", "news")
    report = backtest_strategy_suite(start, end, starting_balance=20.0, risk_pct=23.0, bot_ids=allowed)
    trades_path = Path(report["paths"]["trades"])
    if not trades_path.exists():
        return []
    frame = pd.read_csv(trades_path)
    if frame.empty:
        return []
    if symbols:
        normalized = {normalize_symbol(item) for item in symbols}
        frame = frame[frame["symbol"].map(normalize_symbol).isin(normalized)]
    frame = frame.sort_values(["setup_score", "r_multiple"], ascending=[False, False]).head(50)
    candidates: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        candidates.append(
            {
                "symbol": row["symbol"],
                "timeframe": row["timeframe"],
                "direction": row["direction"],
                "setup_grade": "A+",
                "setup_score": int(row["setup_score"]),
                "entry_model": f"20pip {row['bot']} suite entry",
                "execution_type": "MARKET",
                "entry": float(row["entry"]),
                "stop_loss": float(row["stop_loss"]),
                "take_profit": float(row["take_profit"]),
                "risk_reward": float(abs(float(row["take_profit"]) - float(row["entry"])) / max(abs(float(row["entry"]) - float(row["stop_loss"])), 1e-9)),
                "reasons": [str(row["reason"]), f"Spread-adjusted historical result: {float(row['r_multiple']):.2f}R."],
                "status": "allowed",
            }
        )
    return candidates
