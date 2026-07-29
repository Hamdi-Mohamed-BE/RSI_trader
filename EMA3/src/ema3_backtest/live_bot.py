from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import time
from typing import Iterable

import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv


UTC = timezone.utc


def canonical(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def env_bool(name: str, default: bool) -> bool:
    import os

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class LiveConfig:
    symbol_hint: str
    pivot_distance: int
    max_same_direction_legs: int
    fixed_lot: float
    live_trading: bool
    close_on_opposite: bool
    entry_window_minutes: int
    poll_seconds: int
    history_bars: int
    deviation_points: int
    max_tick_age_seconds: int
    magic: int
    comment: str
    state_file: Path
    log_file: Path

    @classmethod
    def from_env(cls) -> "LiveConfig":
        import os

        load_dotenv()
        return cls(
            symbol_hint=os.getenv("GOLD_SYMBOL_HINT", "AUTO").strip(),
            pivot_distance=int(os.getenv("PIVOT_DISTANCE", "6")),
            max_same_direction_legs=int(
                os.getenv("MAX_SAME_DIRECTION_LEGS", "1")
            ),
            fixed_lot=float(os.getenv("FIXED_LOT", "0.10")),
            live_trading=env_bool("LIVE_TRADING", False),
            close_on_opposite=env_bool("CLOSE_ON_OPPOSITE", True),
            entry_window_minutes=int(os.getenv("ENTRY_WINDOW_MINUTES", "10")),
            poll_seconds=int(os.getenv("POLL_SECONDS", "15")),
            history_bars=int(os.getenv("HISTORY_BARS", "100")),
            deviation_points=int(os.getenv("DEVIATION_POINTS", "50")),
            max_tick_age_seconds=int(os.getenv("MAX_TICK_AGE_SECONDS", "120")),
            magic=int(os.getenv("MAGIC_NUMBER", "3082026")),
            comment=os.getenv("ORDER_COMMENT", "EMA3_H4_PIVOT")[:31],
            state_file=Path(os.getenv("STATE_FILE", "runtime/state.json")),
            log_file=Path(os.getenv("LOG_FILE", "logs/ema3-live.log")),
        )

    def validate(self) -> None:
        if self.pivot_distance < 1:
            raise ValueError("PIVOT_DISTANCE must be at least 1")
        if self.max_same_direction_legs < 1:
            raise ValueError("MAX_SAME_DIRECTION_LEGS must be at least 1")
        if self.fixed_lot <= 0:
            raise ValueError("FIXED_LOT must be positive")
        if self.history_bars < self.pivot_distance * 2 + 3:
            raise ValueError("HISTORY_BARS is too small for the pivot distance")
        if self.entry_window_minutes < 1:
            raise ValueError("ENTRY_WINDOW_MINUTES must be positive")


def gold_symbol_score(item: object, hint: str) -> tuple[int, int, int, int, str]:
    name = str(getattr(item, "name", ""))
    description = str(getattr(item, "description", ""))
    path = str(getattr(item, "path", ""))
    normalized = canonical(name)
    requested = canonical(hint)
    text = canonical(f"{name} {description} {path}")
    exact_hint = requested not in {"", "AUTO"} and normalized == requested
    starts_hint = (
        requested not in {"", "AUTO"} and normalized.startswith(requested)
    )
    is_xauusd = normalized == "XAUUSD" or normalized.startswith("XAUUSD")
    is_gold_name = normalized == "GOLD" or normalized.startswith("GOLD")
    describes_gold = "GOLD" in text or "XAU" in text
    if not any((exact_hint, starts_hint, is_xauusd, is_gold_name, describes_gold)):
        return (-10_000, 0, 0, 0, name)
    trade_mode = int(getattr(item, "trade_mode", 0))
    disabled = trade_mode == int(mt5.SYMBOL_TRADE_MODE_DISABLED)
    visible = bool(getattr(item, "visible", False))
    base = (
        1_000 if exact_hint else
        900 if is_xauusd else
        800 if is_gold_name else
        700 if starts_hint else
        500
    )
    return (
        base,
        0 if disabled else 1,
        1 if visible else 0,
        -len(name),
        name,
    )


def choose_gold_symbol(symbols: Iterable[object], hint: str = "AUTO") -> str:
    ranked = sorted(
        ((gold_symbol_score(item, hint), item) for item in symbols),
        key=lambda row: row[0],
        reverse=True,
    )
    if not ranked or ranked[0][0][0] < 0:
        raise RuntimeError(
            "No broker gold symbol found. Set GOLD_SYMBOL_HINT to its name."
        )
    return str(getattr(ranked[0][1], "name"))


def discover_gold_symbol(hint: str) -> str:
    symbols = mt5.symbols_get()
    if not symbols:
        raise RuntimeError(f"MT5 symbol catalogue unavailable: {mt5.last_error()}")
    symbol = choose_gold_symbol(symbols, hint)
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
    info = mt5.symbol_info(symbol)
    if info is None or int(info.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_DISABLED):
        raise RuntimeError(f"Discovered gold symbol {symbol} is not tradable")
    return symbol


def latest_h4_frame(symbol: str, bars: int) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, bars)
    if rates is None or len(rates) < 3:
        raise RuntimeError(f"No H4 data for {symbol}: {mt5.last_error()}")
    frame = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame


def confirmed_signal(
    completed: pd.DataFrame, distance: int
) -> dict[str, object] | None:
    confirmation_idx = len(completed) - 1
    pivot_idx = confirmation_idx - distance
    if pivot_idx < distance:
        return None
    left = pivot_idx - distance
    right = pivot_idx + distance
    lows = completed.loc[left:right, "low"]
    highs = completed.loc[left:right, "high"]
    pivot_low = float(completed.at[pivot_idx, "low"])
    pivot_high = float(completed.at[pivot_idx, "high"])
    is_buy = (
        pivot_low == float(lows.min())
        and int((lows == pivot_low).sum()) == 1
    )
    is_sell = (
        pivot_high == float(highs.max())
        and int((highs == pivot_high).sum()) == 1
    )
    if is_buy == is_sell:
        return None
    side = "buy" if is_buy else "sell"
    pivot_time = completed.at[pivot_idx, "time"]
    confirmation_time = completed.at[confirmation_idx, "time"]
    return {
        "side": side,
        "pivot_time": pivot_time,
        "confirmation_time": confirmation_time,
        "signal_id": f"{side}:{pivot_time.isoformat()}:{confirmation_time.isoformat()}",
    }


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"processed_signals": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"processed_signals": []}


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)


def normalized_volume(symbol: str, requested: float) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"No symbol information for {symbol}")
    step = float(info.volume_step)
    minimum = float(info.volume_min)
    maximum = float(info.volume_max)
    volume = min(max(requested, minimum), maximum)
    if step > 0:
        volume = round(round(volume / step) * step, 8)
    return volume


def managed_positions(symbol: str, magic: int) -> list[object]:
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        raise RuntimeError(f"Could not read positions: {mt5.last_error()}")
    return [position for position in positions if int(position.magic) == magic]


def side_of_position(position: object) -> str:
    return "buy" if int(position.type) == int(mt5.POSITION_TYPE_BUY) else "sell"


def filling_modes() -> list[int]:
    return [
        int(mt5.ORDER_FILLING_RETURN),
        int(mt5.ORDER_FILLING_IOC),
        int(mt5.ORDER_FILLING_FOK),
    ]


def send_request(request: dict[str, object]) -> object:
    last_result = None
    for mode in filling_modes():
        attempt = dict(request)
        attempt["type_filling"] = mode
        result = mt5.order_send(attempt)
        last_result = result
        if result is not None and int(result.retcode) in {
            int(mt5.TRADE_RETCODE_DONE),
            int(mt5.TRADE_RETCODE_DONE_PARTIAL),
            int(mt5.TRADE_RETCODE_PLACED),
        }:
            return result
        if result is None or int(result.retcode) not in {
            int(mt5.TRADE_RETCODE_INVALID_FILL),
            int(mt5.TRADE_RETCODE_INVALID),
        }:
            break
    detail = mt5.last_error() if last_result is None else (
        last_result.retcode,
        last_result.comment,
    )
    raise RuntimeError(f"MT5 order failed: {detail}")


def close_position(
    symbol: str, position: object, config: LiveConfig, dry_run: bool
) -> None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No live tick for {symbol}")
    side = side_of_position(position)
    order_type = mt5.ORDER_TYPE_SELL if side == "buy" else mt5.ORDER_TYPE_BUY
    price = float(tick.bid) if side == "buy" else float(tick.ask)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "position": int(position.ticket),
        "volume": float(position.volume),
        "type": order_type,
        "price": price,
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": f"{config.comment}_EXIT"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }
    if dry_run:
        logging.info("DRY RUN close ticket=%s side=%s", position.ticket, side)
        return
    result = send_request(request)
    logging.info(
        "Closed ticket=%s retcode=%s deal=%s",
        position.ticket,
        result.retcode,
        result.deal,
    )


def open_position(
    symbol: str, side: str, config: LiveConfig, dry_run: bool
) -> None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No live tick for {symbol}")
    volume = normalized_volume(symbol, config.fixed_lot)
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    price = float(tick.ask) if side == "buy" else float(tick.bid)
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": config.deviation_points,
        "magic": config.magic,
        "comment": config.comment,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    if dry_run:
        logging.info(
            "DRY RUN open side=%s symbol=%s volume=%.2f price=%s",
            side,
            symbol,
            volume,
            price,
        )
        return
    result = send_request(request)
    logging.info(
        "Opened %s %.2f %s retcode=%s order=%s deal=%s",
        side,
        volume,
        symbol,
        result.retcode,
        result.order,
        result.deal,
    )


def account_line() -> str:
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"No connected MT5 account: {mt5.last_error()}")
    return (
        f"Account {account.login} | {account.server} | {account.currency} | "
        f"balance {account.balance:,.2f} | equity {account.equity:,.2f} | "
        f"free margin {account.margin_free:,.2f} | leverage 1:{account.leverage}"
    )


def process_once(symbol: str, config: LiveConfig, state: dict[str, object]) -> None:
    frame = latest_h4_frame(symbol, config.history_bars)
    current = frame.iloc[-1]
    now = datetime.now(UTC)
    current_open = current["time"].to_pydatetime()
    bar_age_minutes = (now - current_open).total_seconds() / 60.0
    if not 0 <= bar_age_minutes < config.entry_window_minutes:
        logging.debug(
            "No entry: current H4 bar age %.1f min (window %d)",
            bar_age_minutes,
            config.entry_window_minutes,
        )
        return
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No live tick for {symbol}")
    tick_age = now.timestamp() - float(tick.time)
    if tick_age > config.max_tick_age_seconds:
        logging.warning("No entry: stale tick is %.0f seconds old", tick_age)
        return

    signal = confirmed_signal(frame.iloc[:-1].reset_index(drop=True), config.pivot_distance)
    if signal is None:
        logging.info("No newly confirmed pivot at %s", current_open.isoformat())
        return
    signal_id = str(signal["signal_id"])
    processed = list(state.get("processed_signals", []))
    if signal_id in processed:
        return

    side = str(signal["side"])
    positions = managed_positions(symbol, config.magic)
    opposite = [position for position in positions if side_of_position(position) != side]
    same_side = [position for position in positions if side_of_position(position) == side]
    logging.info(
        "Signal %s pivot=%s confirmation=%s managed=%d",
        side.upper(),
        signal["pivot_time"],
        signal["confirmation_time"],
        len(positions),
    )
    dry_run = not config.live_trading
    if opposite and config.close_on_opposite:
        for position in opposite:
            close_position(symbol, position, config, dry_run)
        same_side = []
    if len(same_side) < config.max_same_direction_legs:
        open_position(symbol, side, config, dry_run)
    else:
        logging.info(
            "Signal ignored: already at max %d %s leg(s)",
            config.max_same_direction_legs,
            side,
        )
    processed.append(signal_id)
    state["processed_signals"] = processed[-100:]
    state["last_signal"] = {
        "side": side,
        "pivot_time": signal["pivot_time"].isoformat(),
        "confirmation_time": signal["confirmation_time"].isoformat(),
        "signal_id": signal_id,
    }
    save_state(config.state_file, state)


def configure_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(path, encoding="utf-8"),
        ],
        force=True,
    )


def run(once: bool = False) -> None:
    config = LiveConfig.from_env()
    config.validate()
    configure_logging(config.log_file)
    if not mt5.initialize():
        raise RuntimeError(
            "Could not connect to the already-open MT5 terminal. "
            f"MT5 error: {mt5.last_error()}"
        )
    try:
        logging.info(account_line())
        symbol = discover_gold_symbol(config.symbol_hint)
        logging.info(
            "Gold discovered as %s | H4 | pivot=%d | lot=%.2f | max legs=%d | mode=%s",
            symbol,
            config.pivot_distance,
            config.fixed_lot,
            config.max_same_direction_legs,
            "LIVE" if config.live_trading else "DRY RUN",
        )
        state = load_state(config.state_file)
        while True:
            try:
                process_once(symbol, config, state)
            except Exception:
                logging.exception("Scan failed")
            if once:
                break
            time.sleep(config.poll_seconds)
    finally:
        mt5.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Live EMA3 H4 pivot reversal bot")
    parser.add_argument(
        "--once",
        action="store_true",
        help="perform one scan and exit",
    )
    arguments = parser.parse_args()
    run(once=arguments.once)


if __name__ == "__main__":
    main()
