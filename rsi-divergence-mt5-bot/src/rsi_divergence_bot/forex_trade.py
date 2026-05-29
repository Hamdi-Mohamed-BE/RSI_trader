from __future__ import annotations

from hashlib import sha1

import pandas as pd

from .config import AppConfig, ForexTradeConfig, RiskConfig, SymbolConfig
from .indicators import ema, rsi
from .mt5_client import MT5Client
from .sessions import in_allowed_session, session_name
from .strategy import Signal
from .trade_geometry import invalid_market_geometry


def _normalize_symbol_token(value: str) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    return raw.split("-")[0].split(".")[0]


def symbol_allowed(symbol_cfg: SymbolConfig, cfg: ForexTradeConfig) -> bool:
    if not cfg.symbol_keys:
        return True
    allowed = {_normalize_symbol_token(item) for item in cfg.symbol_keys if str(item).strip()}
    if not allowed:
        return True
    candidates = {
        _normalize_symbol_token(symbol_cfg.key),
        _normalize_symbol_token(symbol_cfg.name),
        _normalize_symbol_token(symbol_cfg.symbol),
    }
    return bool(allowed & candidates)


def prepare_frame(df: pd.DataFrame, cfg: ForexTradeConfig) -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    out["rsi"] = rsi(out["close"], cfg.rsi_period)
    if cfg.use_trend_filter:
        out["trend_ema"] = ema(out["close"], cfg.trend_ema_period)
    return out


def _trend_allows(frame: pd.DataFrame, index: int, side: str, cfg: ForexTradeConfig) -> bool:
    if not cfg.use_trend_filter:
        return True
    row = frame.iloc[index]
    if pd.isna(row.get("trend_ema")):
        return False
    close = float(row.close)
    trend = float(row.trend_ema)
    if side == "buy":
        return close > trend
    return close < trend


def _long_condition(frame: pd.DataFrame, index: int, cfg: ForexTradeConfig) -> bool:
    if index < 1:
        return False
    latest = frame.iloc[index]
    previous = frame.iloc[index - 1]
    if pd.isna(latest["rsi"]) or pd.isna(previous["rsi"]):
        return False
    rsi_val = float(latest["rsi"])
    prev_rsi = float(previous["rsi"])
    crossed = prev_rsi >= cfg.rsi_long_entry and rsi_val < cfg.rsi_long_entry
    if not crossed:
        return False
    return _trend_allows(frame, index, "buy", cfg)


def _short_condition(frame: pd.DataFrame, index: int, cfg: ForexTradeConfig) -> bool:
    if index < 1:
        return False
    latest = frame.iloc[index]
    previous = frame.iloc[index - 1]
    if pd.isna(latest["rsi"]) or pd.isna(previous["rsi"]):
        return False
    rsi_val = float(latest["rsi"])
    prev_rsi = float(previous["rsi"])
    crossed = prev_rsi <= cfg.rsi_short_entry and rsi_val > cfg.rsi_short_entry
    if not crossed:
        return False
    return _trend_allows(frame, index, "sell", cfg)


def _price_levels(entry: float, side: str, cfg: ForexTradeConfig) -> tuple[float, float]:
    if side == "buy":
        sl = entry * (1.0 - cfg.stop_loss_pct)
        tp = entry * (1.0 + cfg.take_profit_pct)
    else:
        sl = entry * (1.0 + cfg.stop_loss_pct)
        tp = entry * (1.0 - cfg.take_profit_pct)
    return sl, tp


def _make_signal(
    frame: pd.DataFrame,
    index: int,
    side: str,
    symbol_cfg: SymbolConfig,
    cfg: ForexTradeConfig,
    risk_cfg: RiskConfig | None,
) -> Signal | None:
    row = frame.iloc[index]
    time_value = row.time.to_pydatetime() if hasattr(row.time, "to_pydatetime") else row.time
    if risk_cfg and not in_allowed_session(time_value, symbol_cfg.sessions):
        return None

    entry = float(row.close)
    sl, tp = _price_levels(entry, side, cfg)
    tps = [tp]
    risk_distance = abs(entry - sl)
    if risk_distance <= 0 or invalid_market_geometry(side, entry, sl, tps):
        return None

    setup_key = f"forex_trade:{symbol_cfg.key}:{side}:{time_value.isoformat()}"
    return Signal(
        setup_id=sha1(setup_key.encode("utf-8")).hexdigest()[:8],
        symbol=symbol_cfg.symbol,
        market_key=symbol_cfg.key,
        name=symbol_cfg.name,
        side=side,
        time=time_value,
        entry=entry,
        sl=sl,
        tps=tps,
        lot_per_leg=symbol_cfg.lot_per_leg,
        risk_distance=risk_distance,
        session=session_name(time_value),
        reason=(
            f"forex_trade {side} RSI mean-reversion "
            f"(entry<{cfg.rsi_long_entry:.0f}|>{cfg.rsi_short_entry:.0f}, "
            f"exit {cfg.rsi_long_exit:.0f}/{cfg.rsi_short_exit:.0f})"
        ),
        algorithm="forex_trade",
        ema_slow_len=cfg.trend_ema_period if cfg.use_trend_filter else None,
    )


def generate_signals(
    df: pd.DataFrame,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig | None,
    cfg: ForexTradeConfig,
) -> list[Signal]:
    if not symbol_allowed(symbol_cfg, cfg):
        return []
    frame = prepare_frame(df, cfg)
    warmup = max(cfg.rsi_period, cfg.trend_ema_period if cfg.use_trend_filter else 0) + 5
    signals: list[Signal] = []
    for index in range(warmup, len(frame)):
        if _long_condition(frame, index, cfg):
            signal = _make_signal(frame, index, "buy", symbol_cfg, cfg, risk_cfg)
            if signal is not None:
                signals.append(signal)
                continue
        if _short_condition(frame, index, cfg):
            signal = _make_signal(frame, index, "sell", symbol_cfg, cfg, risk_cfg)
            if signal is not None:
                signals.append(signal)
    return signals


def signal_at_closed_index(
    df: pd.DataFrame,
    end_index: int,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig | None,
    cfg: ForexTradeConfig,
) -> Signal | None:
    if end_index < 0 or end_index >= len(df):
        return None
    closed = df.iloc[: end_index + 1]
    signals = generate_signals(closed, symbol_cfg, risk_cfg, cfg)
    if not signals:
        return None
    latest = signals[-1]
    row_time = closed.iloc[-1]["time"]
    if hasattr(row_time, "to_pydatetime"):
        row_time = row_time.to_pydatetime()
    return latest if latest.time == row_time else None


def latest_closed_signal(
    df: pd.DataFrame,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig | None,
    cfg: ForexTradeConfig,
) -> Signal | None:
    if len(df) < 2:
        return None
    closed = df.iloc[:-1]
    return signal_at_closed_index(closed, len(closed) - 1, symbol_cfg, risk_cfg, cfg)


def latest_closed_rsi(df: pd.DataFrame, cfg: ForexTradeConfig) -> float | None:
    if len(df) < cfg.rsi_period + 2:
        return None
    closed = df.iloc[:-1]
    frame = prepare_frame(closed, cfg)
    value = frame.iloc[-1]["rsi"]
    if pd.isna(value):
        return None
    return float(value)


def spread_points(client: MT5Client, symbol: str) -> float:
    info = client.symbol_info(symbol)
    point = float(getattr(info, "point", 0.0) or 0.00001)
    return client.spread_price(symbol) / point


def spread_ok(client: MT5Client, symbol: str, cfg: ForexTradeConfig) -> tuple[bool, str]:
    if not cfg.use_spread_filter:
        return True, ""
    points = spread_points(client, symbol)
    if points > cfg.max_spread_points:
        return False, f"spread {points:.1f} points exceeds max {cfg.max_spread_points:.1f}"
    return True, ""


def resolve_lot_size(
    client: MT5Client,
    symbol: str,
    risk_distance: float,
    cfg: ForexTradeConfig,
    *,
    fallback_lot: float,
) -> float:
    if not cfg.use_risk_based_lot or risk_distance <= 0:
        return client.normalize_volume(symbol, fallback_lot)

    account = client.account()
    equity = float(getattr(account, "equity", 0.0) or getattr(account, "balance", 0.0) or 0.0)
    if equity <= 0:
        return client.normalize_volume(symbol, fallback_lot)

    risk_amount = equity * cfg.risk_per_trade
    loss_per_lot = client.money_for_distance(symbol, 1.0, risk_distance)
    if loss_per_lot <= 0:
        return client.normalize_volume(symbol, fallback_lot)

    lots = risk_amount / loss_per_lot
    return client.normalize_volume(symbol, lots)


def with_lot(signal: Signal, lot_per_leg: float) -> Signal:
    return Signal(
        setup_id=signal.setup_id,
        symbol=signal.symbol,
        market_key=signal.market_key,
        name=signal.name,
        side=signal.side,
        time=signal.time,
        entry=signal.entry,
        sl=signal.sl,
        tps=list(signal.tps),
        lot_per_leg=lot_per_leg,
        risk_distance=signal.risk_distance,
        session=signal.session,
        reason=signal.reason,
        algorithm=signal.algorithm,
        trail_atr_mult=signal.trail_atr_mult,
        ema_fast_len=signal.ema_fast_len,
        ema_slow_len=signal.ema_slow_len,
        atr_at_entry=signal.atr_at_entry,
    )


def _field(obj, name: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def manage_rsi_exits(
    client: MT5Client,
    config: AppConfig,
    logger,
    *,
    is_demo: bool,
) -> int:
    if config.bot.signal_algorithm != "forex_trade":
        return 0
    if config.bot.dry_run:
        return 0

    from .config import trade_symbol_for_account

    cfg = config.bot.forex_trade
    closed = 0
    positions = client.positions() or []
    for pos in positions:
        if int(_field(pos, "magic", 0) or 0) != config.bot.magic:
            continue
        symbol = str(_field(pos, "symbol", ""))
        if not symbol:
            continue
        matching = next(
            (
                item
                for item in config.enabled_symbols
                if trade_symbol_for_account(item, is_demo=is_demo) == symbol
                and symbol_allowed(item, cfg)
            ),
            None,
        )
        if matching is None:
            continue

        df = client.rates(symbol, cfg.timeframe, max(cfg.bars, cfg.rsi_period + 20))
        rsi_val = latest_closed_rsi(df, cfg)
        if rsi_val is None:
            continue

        is_buy = int(_field(pos, "type", 0) or 0) == 0
        should_close = (is_buy and rsi_val >= cfg.rsi_long_exit) or (
            not is_buy and rsi_val <= cfg.rsi_short_exit
        )
        if not should_close:
            continue

        ticket = int(_field(pos, "ticket"))
        result = client.close_position(ticket, symbol)
        closed += 1
        logger.info(
            "FOREX TRADE RSI EXIT %s ticket=%s side=%s rsi=%.2f ret=%s",
            symbol,
            ticket,
            "buy" if is_buy else "sell",
            rsi_val,
            _field(result, "retcode"),
        )
    return closed
