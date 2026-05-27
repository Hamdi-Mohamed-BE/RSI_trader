from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from .config import MT5Config
from .mt5_algo_trading import ensure_algo_trading
from .symbols import CRYPTO_MARKET_KEYS
from .timeframes import TIMEFRAME_MINUTES, mt5_timeframe_value, timeframe_seconds, validate_timeframe
from .trade_geometry import invalid_market_geometry, invalid_pending_geometry

try:
    import MetaTrader5 as _native_mt5
except ImportError:  # pragma: no cover
    _native_mt5 = None

try:
    import rpyc
    from rpyc.utils.classic import obtain
except ImportError:  # pragma: no cover
    rpyc = None

    def obtain(value):
        return value


_MT5_LOCK = threading.RLock()
_THREAD_LOCAL = threading.local()
_COMMON_24H_SYMBOLS = tuple(sorted(CRYPTO_MARKET_KEYS))


def _thread_ready(connection_key: str) -> bool:
    return getattr(_THREAD_LOCAL, "ready", False) and getattr(_THREAD_LOCAL, "path", None) == connection_key


def _set_thread_ready(connection_key: str, ready: bool) -> None:
    _THREAD_LOCAL.ready = ready
    _THREAD_LOCAL.path = connection_key if ready else None


def _utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _rates_frame(rates, *, time_offset_seconds: int = 0) -> pd.DataFrame:
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    if time_offset_seconds:
        df["time"] = df["time"] - pd.to_timedelta(time_offset_seconds, unit="s")
    return df


def _timeframe_seconds(timeframe: str) -> int:
    return timeframe_seconds(timeframe)


def _floor_timestamp(dt: datetime, timeframe: str) -> datetime:
    seconds = _timeframe_seconds(timeframe)
    unix = int(dt.timestamp())
    return datetime.fromtimestamp(unix - (unix % seconds), tz=timezone.utc)


def _detect_server_time_offset_seconds(rates, timeframe: str) -> int | None:
    if rates is None or len(rates) == 0:
        return None
    raw_last = datetime.fromtimestamp(int(rates[-1]["time"]), tz=timezone.utc)
    expected_last = _floor_timestamp(datetime.now(timezone.utc), timeframe)
    rounded_hours = round((raw_last - expected_last).total_seconds() / 3600)
    candidate = int(rounded_hours * 3600)
    if abs(candidate) > 14 * 3600:
        return None
    corrected_delta = abs((raw_last - timedelta(seconds=candidate) - expected_last).total_seconds())
    if corrected_delta <= max(_timeframe_seconds(timeframe) * 2, 120):
        return candidate
    return None


def _field(obj, name: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class MT5BridgeBackend:
    def __init__(self, host: str, port: int, timeout: int):
        if rpyc is None:
            raise RuntimeError("rpyc is not installed. Run `uv sync` first.")
        self._host = host
        self._port = port
        self._timeout = timeout
        self._conn = None
        self._mt5 = None

    def _connect(self):
        if self._conn is not None and self._mt5 is not None:
            return self._mt5
        self._conn = rpyc.classic.connect(self._host, self._port)
        self._conn._config["sync_request_timeout"] = self._timeout
        self._conn.execute("import MetaTrader5 as mt5")
        self._conn.execute("import datetime")
        self._mt5 = self._conn.modules.MetaTrader5
        return self._mt5

    def __getattr__(self, name: str):
        return obtain(getattr(self._connect(), name))

    def _eval_plain(self, expression: str):
        return obtain(self._conn.eval(expression))

    def initialize(self, *args, **kwargs):
        return obtain(self._connect().initialize(*args, **kwargs))

    def shutdown(self):
        if self._mt5 is None:
            return None
        result = obtain(self._mt5.shutdown())
        self._conn = None
        self._mt5 = None
        return result

    def last_error(self):
        return obtain(self._connect().last_error())

    def account_info(self):
        self._connect()
        return self._eval_plain("mt5.account_info()._asdict() if mt5.account_info() is not None else None")

    def symbol_select(self, *args, **kwargs):
        return obtain(self._connect().symbol_select(*args, **kwargs))

    def symbol_info(self, *args, **kwargs):
        self._connect()
        symbol = args[0] if args else kwargs.get("symbol")
        return self._eval_plain(f"mt5.symbol_info({symbol!r})._asdict() if mt5.symbol_info({symbol!r}) is not None else None")

    def symbol_info_tick(self, *args, **kwargs):
        self._connect()
        symbol = args[0] if args else kwargs.get("symbol")
        return self._eval_plain(
            f"mt5.symbol_info_tick({symbol!r})._asdict() if mt5.symbol_info_tick({symbol!r}) is not None else None"
        )

    def positions_get(self, *args, **kwargs):
        self._connect()
        if args:
            code = f"mt5.positions_get(*{args!r}, **{kwargs!r})"
        else:
            code = f"mt5.positions_get(**{kwargs!r})"
        return self._eval_plain(f"[item._asdict() for item in ({code} or [])]")

    def history_deals_get(self, *args, **kwargs):
        self._connect()
        from_ts = args[0] if len(args) > 0 else kwargs.get("date_from")
        to_ts = args[1] if len(args) > 1 else kwargs.get("date_to")
        code = (
            "mt5.history_deals_get("
            f"datetime.datetime.fromtimestamp({from_ts.timestamp()!r}), "
            f"datetime.datetime.fromtimestamp({to_ts.timestamp()!r})"
            ")"
        )
        return self._eval_plain(f"[item._asdict() for item in ({code} or [])]")

    def copy_rates_from_pos(self, *args, **kwargs):
        return obtain(self._connect().copy_rates_from_pos(*args, **kwargs))

    def order_send(self, *args, **kwargs):
        self._connect()
        request = args[0] if args else kwargs.get("request")
        self._conn.execute(f"__rsi_order_request = {request!r}")
        result = self._eval_plain(
            "(lambda res: None if res is None else "
            "{key: (value._asdict() if hasattr(value, '_asdict') else value) "
            "for key, value in res._asdict().items()})(mt5.order_send(__rsi_order_request))"
        )
        return PlainObject(result or {})


class PlainObject:
    def __init__(self, values: dict):
        self._values = values
        for key, value in values.items():
            setattr(self, key, value)

    def _asdict(self) -> dict:
        return dict(self._values)

    def __repr__(self) -> str:
        return repr(self._values)


class MT5Client:
    def __init__(self, mt5_config: MT5Config | str):
        if isinstance(mt5_config, str):
            mt5_config = MT5Config(path=mt5_config)
        self.config = mt5_config
        self.mt5 = self._load_backend()
        self.connection_key = (
            f"bridge:{self.config.host}:{self.config.port}"
            if self.config.mode == "linux_bridge"
            else f"native:{self.config.path}"
        )
        self._time_offset_seconds: int | None = None

    def _load_backend(self):
        if self.config.mode == "linux_bridge":
            if rpyc is None:
                raise RuntimeError("rpyc is not installed. Run `uv sync` first.")
            return MT5BridgeBackend(self.config.host, self.config.port, self.config.timeout)
        if _native_mt5 is None:
            raise RuntimeError("MetaTrader5 package is not installed. Run `uv sync` first.")
        return _native_mt5

    def _initialize_kwargs(self, *, include_login: bool = True) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if include_login:
            if self.config.login is not None:
                kwargs["login"] = int(self.config.login)
            if self.config.password:
                kwargs["password"] = self.config.password
            if self.config.server:
                kwargs["server"] = self.config.server
        if self.config.timeout:
            kwargs["timeout"] = int(self.config.timeout)
        return kwargs

    def _connection_key_for(self, mt5_config: MT5Config | None = None) -> str:
        cfg = mt5_config or self.config
        if cfg.mode == "linux_bridge":
            return f"bridge:{cfg.host}:{cfg.port}"
        return f"native:{cfg.path or ''}"

    def initialize_terminal(self) -> None:
        """Connect to the MT5 terminal without selecting a trading account."""
        with _MT5_LOCK:
            if _thread_ready(self.connection_key):
                if self.mt5.account_info() is not None:
                    return
                self.mt5.shutdown()
                _set_thread_ready(self.connection_key, False)

            kwargs = self._initialize_kwargs(include_login=False)
            if self.config.mode == "native_windows" and self.config.path:
                ok = self.mt5.initialize(path=self.config.path, **kwargs)
            else:
                ok = self.mt5.initialize(**kwargs)
            if not ok:
                raise RuntimeError(f"MT5 initialize failed: {self.mt5.last_error()}")
            _set_thread_ready(self.connection_key, True)
            ensure_algo_trading(self, config=self.config)

    def login_account(self, login: int, password: str, server: str) -> None:
        self.initialize_terminal()
        with _MT5_LOCK:
            ok = self.mt5.login(int(login), password=str(password), server=str(server))
            if not ok:
                raise RuntimeError(f"MT5 login failed: {self.mt5.last_error()}")
            self.config.login = int(login)
            self.config.password = str(password)
            self.config.server = str(server)
            ensure_algo_trading(self, config=self.config)

    def switch_account(self, mt5_config: MT5Config) -> None:
        new_key = self._connection_key_for(mt5_config)
        path_changed = (mt5_config.path or "") != (self.config.path or "")
        if new_key != self.connection_key or path_changed:
            self.shutdown(force=True)
            self.config = mt5_config
            self.connection_key = new_key
            self._time_offset_seconds = None
        if mt5_config.login is None or not mt5_config.password or not mt5_config.server:
            raise RuntimeError("account login, password, and server are required")
        self.login_account(int(mt5_config.login), str(mt5_config.password), str(mt5_config.server))

    def initialize(self) -> None:
        with _MT5_LOCK:
            if _thread_ready(self.connection_key):
                if self.mt5.account_info() is not None:
                    return
                self.mt5.shutdown()
                _set_thread_ready(self.connection_key, False)

            kwargs = self._initialize_kwargs(include_login=True)
            if self.config.mode == "native_windows" and self.config.path:
                ok = self.mt5.initialize(path=self.config.path, **kwargs)
            else:
                ok = self.mt5.initialize(**kwargs)
            if not ok:
                raise RuntimeError(f"MT5 initialize failed: {self.mt5.last_error()}")
            _set_thread_ready(self.connection_key, True)
            ensure_algo_trading(self, config=self.config)

    def _rates_time_offset(self, symbol: str, timeframe: str, rates) -> int:
        detected = _detect_server_time_offset_seconds(rates, timeframe)
        if detected is not None:
            self._time_offset_seconds = detected
            return detected
        if self._time_offset_seconds is not None:
            return self._time_offset_seconds

        tf = mt5_timeframe_value(self.mt5, "M1")
        for probe_symbol in _COMMON_24H_SYMBOLS:
            try:
                if not self.mt5.symbol_select(probe_symbol, True):
                    continue
                probe = self.mt5.copy_rates_from_pos(probe_symbol, tf, 0, 5)
                detected = _detect_server_time_offset_seconds(probe, "M1")
                if detected is not None:
                    self._time_offset_seconds = detected
                    return detected
            except Exception:  # noqa: BLE001
                continue

        self._time_offset_seconds = 0
        return 0

    def shutdown(self, *, force: bool = False) -> None:
        if not force:
            return
        with _MT5_LOCK:
            if _thread_ready(self.connection_key):
                self.mt5.shutdown()
            _set_thread_ready(self.connection_key, False)

    def connection_status(self) -> dict:
        try:
            self.initialize()
            info = self.mt5.account_info()
            if info is None:
                return {"connected": False, "error": str(self.mt5.last_error())}
            return {
                "connected": True,
                "login": _field(info, "login"),
                "server": _field(info, "server"),
                "balance": round(float(_field(info, "balance", 0.0)), 2),
            }
        except Exception as exc:  # noqa: BLE001
            return {"connected": False, "error": str(exc)}

    def account(self):
        self.initialize()
        with _MT5_LOCK:
            return self.mt5.account_info()

    def symbol_info(self, symbol: str):
        self.initialize()
        with _MT5_LOCK:
            self.mt5.symbol_select(symbol, True)
            return self.mt5.symbol_info(symbol)

    def tick(self, symbol: str):
        self.initialize()
        with _MT5_LOCK:
            self.mt5.symbol_select(symbol, True)
            return self.mt5.symbol_info_tick(symbol)

    def positions(self, symbol: str | None = None):
        self.initialize()
        with _MT5_LOCK:
            return self.mt5.positions_get(symbol=symbol) if symbol else self.mt5.positions_get()

    def account_snapshot(self) -> dict:
        info = self.account()
        if info is None:
            raise RuntimeError(f"Account info unavailable: {self.mt5.last_error()}")
        return {
            "login": _field(info, "login"),
            "server": _field(info, "server"),
            "name": _field(info, "name"),
            "currency": _field(info, "currency"),
            "balance": round(float(_field(info, "balance", 0.0)), 2),
            "equity": round(float(_field(info, "equity", 0.0)), 2),
            "margin": round(float(_field(info, "margin", 0.0)), 2),
            "free_margin": round(float(_field(info, "margin_free", 0.0)), 2),
            "floating_pnl": round(float(_field(info, "profit", 0.0)), 2),
            "margin_level": round(float(_field(info, "margin_level")), 2) if _field(info, "margin_level") else None,
        }

    def open_positions(self, bot_magic: int | None = None) -> list[dict]:
        positions = self.positions() or []
        rows: list[dict] = []
        for pos in positions:
            side = "buy" if _field(pos, "type") == self.mt5.ORDER_TYPE_BUY else "sell"
            rows.append(
                {
                    "ticket": int(_field(pos, "ticket", 0)),
                    "symbol": _field(pos, "symbol"),
                    "side": side,
                    "volume": float(_field(pos, "volume", 0.0)),
                    "price_open": float(_field(pos, "price_open", 0.0)),
                    "price_current": float(_field(pos, "price_current", 0.0)),
                    "sl": float(_field(pos, "sl", 0.0)),
                    "tp": float(_field(pos, "tp", 0.0)),
                    "profit": round(float(_field(pos, "profit", 0.0)), 2),
                    "swap": round(float(_field(pos, "swap", 0.0)), 2),
                    "magic": int(_field(pos, "magic", 0)),
                    "comment": _field(pos, "comment", ""),
                    "time": datetime.fromtimestamp(int(_field(pos, "time", 0)), tz=timezone.utc).isoformat(),
                    "is_bot": bot_magic is not None and int(_field(pos, "magic", 0)) == bot_magic,
                }
            )
        rows.sort(key=lambda item: item["time"], reverse=True)
        return rows

    def recent_deals(self, hours: int = 24, limit: int = 50) -> list[dict]:
        self.initialize()
        with _MT5_LOCK:
            utc_to = datetime.now(timezone.utc).replace(tzinfo=None)
            utc_from = (datetime.now(timezone.utc) - timedelta(hours=hours)).replace(tzinfo=None)
            deals = self.mt5.history_deals_get(utc_from, utc_to)
            if deals is None:
                return []

            rows: list[dict] = []
            for deal in sorted(deals, key=lambda item: _field(item, "time", 0), reverse=True)[:limit]:
                if _field(deal, "type") == self.mt5.DEAL_TYPE_BUY:
                    side = "buy"
                elif _field(deal, "type") == self.mt5.DEAL_TYPE_SELL:
                    side = "sell"
                else:
                    side = str(_field(deal, "type"))
                rows.append(
                    {
                        "ticket": int(_field(deal, "ticket", 0)),
                        "order": int(_field(deal, "order", 0)),
                        "symbol": _field(deal, "symbol"),
                        "side": side,
                        "volume": float(_field(deal, "volume", 0.0)),
                        "price": float(_field(deal, "price", 0.0)),
                        "profit": round(float(_field(deal, "profit", 0.0)), 2),
                        "commission": round(float(_field(deal, "commission", 0.0)), 2),
                        "swap": round(float(_field(deal, "swap", 0.0)), 2),
                        "magic": int(_field(deal, "magic", 0)),
                        "comment": _field(deal, "comment", ""),
                        "time": datetime.fromtimestamp(int(_field(deal, "time", 0)), tz=timezone.utc).isoformat(),
                    }
                )
            return rows

    def deals_range(self, start: datetime, end: datetime) -> list[dict]:
        self.initialize()
        with _MT5_LOCK:
            utc_from = _utc_naive(start)
            utc_to = _utc_naive(end)
            deals = self.mt5.history_deals_get(utc_from, utc_to)
            if deals is None:
                return []

            buy_type = self._mt5_const("DEAL_TYPE_BUY", 0)
            sell_type = self._mt5_const("DEAL_TYPE_SELL", 1)
            rows: list[dict] = []
            for deal in sorted(deals, key=lambda item: _field(item, "time", 0)):
                deal_type = int(_field(deal, "type", -1))
                if deal_type == buy_type:
                    side = "buy"
                elif deal_type == sell_type:
                    side = "sell"
                else:
                    side = str(deal_type)
                rows.append(
                    {
                        "ticket": int(_field(deal, "ticket", 0)),
                        "order": int(_field(deal, "order", 0)),
                        "position_id": int(_field(deal, "position_id", 0)),
                        "symbol": _field(deal, "symbol"),
                        "side": side,
                        "type": deal_type,
                        "entry": int(_field(deal, "entry", 0)),
                        "reason": int(_field(deal, "reason", 0)),
                        "volume": float(_field(deal, "volume", 0.0)),
                        "price": float(_field(deal, "price", 0.0)),
                        "profit": round(float(_field(deal, "profit", 0.0)), 2),
                        "commission": round(float(_field(deal, "commission", 0.0)), 2),
                        "swap": round(float(_field(deal, "swap", 0.0)), 2),
                        "fee": round(float(_field(deal, "fee", 0.0)), 2),
                        "magic": int(_field(deal, "magic", 0)),
                        "comment": _field(deal, "comment", ""),
                        "time": datetime.fromtimestamp(int(_field(deal, "time", 0)), tz=timezone.utc).isoformat(),
                        "time_unix": int(_field(deal, "time", 0)),
                    }
                )
            return rows

    def realized_pnl_since(self, start: datetime) -> float:
        self.initialize()
        with _MT5_LOCK:
            utc_from = _utc_naive(start)
            utc_to = datetime.now(timezone.utc).replace(tzinfo=None)
            deals = self.mt5.history_deals_get(utc_from, utc_to)
            if deals is None:
                return 0.0

            total = 0.0
            for deal in deals:
                if _field(deal, "type") not in {self.mt5.DEAL_TYPE_BUY, self.mt5.DEAL_TYPE_SELL}:
                    continue
                total += float(_field(deal, "profit", 0.0)) + float(_field(deal, "commission", 0.0)) + float(_field(deal, "swap", 0.0))
            return round(total, 2)

    def live_snapshot(self, bot_magic: int) -> dict:
        payload: dict = {
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "bot_magic": bot_magic,
            "connected": False,
            "account": None,
            "positions": [],
            "deals": [],
            "error": None,
        }
        try:
            self.initialize()
            payload["account"] = self.account_snapshot()
            payload["connected"] = True
        except Exception as exc:  # noqa: BLE001
            payload["error"] = str(exc)
            return payload

        try:
            payload["positions"] = self.open_positions(bot_magic)
        except Exception as exc:  # noqa: BLE001
            payload["error"] = f"Positions unavailable: {exc}"

        try:
            payload["deals"] = self.recent_deals()
        except Exception:  # noqa: BLE001
            pass

        return payload

    def rates(self, symbol: str, timeframe: str, count: int = 500) -> pd.DataFrame:
        timeframe = validate_timeframe(timeframe)
        self.initialize()
        with _MT5_LOCK:
            if not self.mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Could not select symbol {symbol}: {self.mt5.last_error()}")
            tf = mt5_timeframe_value(self.mt5, timeframe)
            rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"No rates for {symbol} {timeframe}: {self.mt5.last_error()}")
            offset = self._rates_time_offset(symbol, timeframe, rates)
            return _rates_frame(rates, time_offset_seconds=offset)

    def rates_range(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame:
        timeframe = validate_timeframe(timeframe)

        self.initialize()
        with _MT5_LOCK:
            if not self.mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Could not select symbol {symbol}: {self.mt5.last_error()}")

            info = self.mt5.symbol_info(symbol)
            if info is None:
                raise RuntimeError(f"Symbol not found in MT5: {symbol}")

            start_naive = _utc_naive(start)
            end_naive = _utc_naive(end)
            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            if end_naive > now_naive:
                end_naive = now_naive
            if start_naive >= end_naive:
                raise ValueError(f"Invalid date range for {symbol}: start must be before end")

            tf = mt5_timeframe_value(self.mt5, timeframe)
            start_utc = pd.Timestamp(start_naive, tz="UTC")
            end_utc = pd.Timestamp(end_naive, tz="UTC")

            minutes = TIMEFRAME_MINUTES[timeframe]
            bars_needed = int((now_naive - start_naive).total_seconds() / 60 / minutes) + 20
            bars_needed = min(max(bars_needed, 50), 100_000)

            batch = self.mt5.copy_rates_from_pos(symbol, tf, 0, bars_needed)
            if batch is None or len(batch) == 0:
                raise RuntimeError(f"No rates for {symbol} {timeframe}: {self.mt5.last_error()}")

            offset = self._rates_time_offset(symbol, timeframe, batch)
            df = _rates_frame(batch, time_offset_seconds=offset)
            df = df[(df["time"] >= start_utc) & (df["time"] <= end_utc)].reset_index(drop=True)
            if df.empty and bars_needed < 200_000:
                batch = self.mt5.copy_rates_from_pos(symbol, tf, 0, min(bars_needed * 2, 200_000))
                if batch is not None and len(batch) > 0:
                    offset = self._rates_time_offset(symbol, timeframe, batch)
                    df = _rates_frame(batch, time_offset_seconds=offset)
                    df = df[(df["time"] >= start_utc) & (df["time"] <= end_utc)].reset_index(drop=True)

            if df.empty:
                raise RuntimeError(
                    f"No bars in range for {symbol} {timeframe} between {start_naive} and {end_naive}"
                )
            return df

    def money_for_distance(self, symbol: str, volume: float, price_distance: float) -> float:
        info = self.symbol_info(symbol)
        tick_size = _field(info, "trade_tick_size") or _field(info, "point") or 0.00001
        tick_value = _field(info, "trade_tick_value") or _field(info, "trade_tick_value_profit") or 1.0
        return price_distance / tick_size * tick_value * volume

    def spread_price(self, symbol: str) -> float:
        self.initialize()
        with _MT5_LOCK:
            if not self.mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Could not select symbol {symbol}: {self.mt5.last_error()}")
            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                raise RuntimeError(f"No tick for {symbol}: {self.mt5.last_error()}")
            return float(_field(tick, "ask", 0.0) - _field(tick, "bid", 0.0))

    def normalize_volume(self, symbol: str, volume: float) -> float:
        info = self.symbol_info(symbol)
        step = float(_field(info, "volume_step") or 0.01)
        min_vol = float(_field(info, "volume_min") or step)
        max_vol = float(_field(info, "volume_max") or volume)
        steps = round(volume / step)
        normalized = max(min_vol, min(max_vol, steps * step))
        return round(normalized, 8)

    def normalize_price(self, symbol: str, price: float) -> float:
        info = self.symbol_info(symbol)
        return round(price, int(_field(info, "digits", 5)))

    def _filling_modes(self, symbol: str) -> list[int]:
        info = self.symbol_info(symbol)
        filling = int(_field(info, "filling_mode", 0))
        symbol_fok = self._mt5_const("SYMBOL_FILLING_FOK", 1)
        symbol_ioc = self._mt5_const("SYMBOL_FILLING_IOC", 2)
        symbol_return = self._mt5_const("SYMBOL_FILLING_RETURN", 4)
        order_fok = self._mt5_const("ORDER_FILLING_FOK", 0)
        order_ioc = self._mt5_const("ORDER_FILLING_IOC", 1)
        order_return = self._mt5_const("ORDER_FILLING_RETURN", 2)
        modes: list[int] = []
        if filling & symbol_ioc:
            modes.append(order_ioc)
        if filling & symbol_fok:
            modes.append(order_fok)
        if filling & symbol_return:
            modes.append(order_return)
        return modes or [order_ioc, order_fok, order_return]

    def _mt5_const(self, name: str, default: int) -> int:
        try:
            return int(getattr(self.mt5, name))
        except Exception:  # noqa: BLE001
            return int(default)

    TRADE_PLACED = 10008
    TRADE_DONE = 10009

    def send_market(self, symbol: str, side: str, volume: float, sl: float, tp: float, magic: int, comment: str):
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise ValueError(f"Unsupported market side: {side}")
        self.initialize()
        with _MT5_LOCK:
            if not self.mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Could not select symbol {symbol}: {self.mt5.last_error()}")
            info = self.mt5.symbol_info(symbol)
            tick = self.mt5.symbol_info_tick(symbol)
            if info is None or tick is None:
                raise RuntimeError(f"No symbol/tick for {symbol}: {self.mt5.last_error()}")

            order_type = self.mt5.ORDER_TYPE_BUY if side == "buy" else self.mt5.ORDER_TYPE_SELL
            price = float(_field(tick, "ask") if side == "buy" else _field(tick, "bid"))
            norm_volume = self.normalize_volume(symbol, volume)
            norm_sl = self.normalize_price(symbol, sl)
            norm_tp = self.normalize_price(symbol, tp)

            geometry_error = invalid_market_geometry(side, price, norm_sl, [norm_tp], label="live price")
            if geometry_error:
                raise ValueError(f"{symbol} {geometry_error}")

            stops_level = int(_field(info, "trade_stops_level", 0) or 0)
            point = float(_field(info, "point") or 0.00001)
            min_stop = stops_level * point
            if min_stop > 0:
                if side == "buy":
                    if price - norm_sl < min_stop:
                        norm_sl = self.normalize_price(symbol, price - min_stop)
                    if norm_tp - price < min_stop:
                        norm_tp = self.normalize_price(symbol, price + min_stop)
                else:
                    if norm_sl - price < min_stop:
                        norm_sl = self.normalize_price(symbol, price + min_stop)
                    if price - norm_tp < min_stop:
                        norm_tp = self.normalize_price(symbol, price - min_stop)

            geometry_error = invalid_market_geometry(side, price, norm_sl, [norm_tp], label="live price")
            if geometry_error:
                raise ValueError(f"{symbol} {geometry_error}")

            last_result = None
            for filling in self._filling_modes(symbol):
                request = {
                    "action": self.mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": norm_volume,
                    "type": order_type,
                    "price": price,
                    "sl": norm_sl,
                    "tp": norm_tp,
                    "deviation": 100,
                    "magic": magic,
                    "comment": comment[:31],
                    "type_filling": filling,
                }
                last_result = self.mt5.order_send(request)
                retcode = getattr(last_result, "retcode", None)
                if retcode == self.TRADE_DONE:
                    return last_result
            return last_result

    def send_market_bare(self, symbol: str, side: str, volume: float, magic: int, comment: str):
        """Market order without stop loss or take profit (manual close only)."""
        side = side.lower()
        if side not in {"buy", "sell"}:
            raise ValueError(f"Unsupported market side: {side}")
        self.initialize()
        with _MT5_LOCK:
            if not self.mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Could not select symbol {symbol}: {self.mt5.last_error()}")
            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                raise RuntimeError(f"No symbol/tick for {symbol}: {self.mt5.last_error()}")

            order_type = self.mt5.ORDER_TYPE_BUY if side == "buy" else self.mt5.ORDER_TYPE_SELL
            price = float(_field(tick, "ask") if side == "buy" else _field(tick, "bid"))
            norm_volume = self.normalize_volume(symbol, volume)

            last_result = None
            for filling in self._filling_modes(symbol):
                request = {
                    "action": self.mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": norm_volume,
                    "type": order_type,
                    "price": price,
                    "sl": 0.0,
                    "tp": 0.0,
                    "deviation": 100,
                    "magic": magic,
                    "comment": comment[:31],
                    "type_filling": filling,
                }
                last_result = self.mt5.order_send(request)
                retcode = getattr(last_result, "retcode", None)
                if retcode == self.TRADE_DONE:
                    return last_result
            return last_result

    def send_pending(
        self,
        symbol: str,
        order_kind: str,
        volume: float,
        entry: float,
        sl: float,
        tp: float,
        magic: int,
        comment: str,
    ):
        order_kind = order_kind.lower()
        self.initialize()
        with _MT5_LOCK:
            if not self.mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Could not select symbol {symbol}: {self.mt5.last_error()}")
            info = self.mt5.symbol_info(symbol)
            tick = self.mt5.symbol_info_tick(symbol)
            if info is None or tick is None:
                raise RuntimeError(f"No symbol/tick for {symbol}: {self.mt5.last_error()}")

            order_type_map = {
                "buy_limit": self.mt5.ORDER_TYPE_BUY_LIMIT,
                "sell_limit": self.mt5.ORDER_TYPE_SELL_LIMIT,
                "buy_stop": self.mt5.ORDER_TYPE_BUY_STOP,
                "sell_stop": self.mt5.ORDER_TYPE_SELL_STOP,
            }
            if order_kind not in order_type_map:
                raise ValueError(f"Unsupported pending order kind: {order_kind}")

            norm_volume = self.normalize_volume(symbol, volume)
            norm_entry = self.normalize_price(symbol, entry)
            norm_sl = self.normalize_price(symbol, sl)
            norm_tp = self.normalize_price(symbol, tp)
            side = "buy" if order_kind.startswith("buy") else "sell"
            geometry_error = invalid_market_geometry(side, norm_entry, norm_sl, [norm_tp], label="pending entry")
            if geometry_error:
                raise ValueError(f"{symbol} {order_kind} {geometry_error}")
            pending_error = invalid_pending_geometry(
                order_kind,
                float(_field(tick, "bid", 0.0) or 0.0),
                float(_field(tick, "ask", 0.0) or 0.0),
                norm_entry,
            )
            if pending_error:
                raise ValueError(f"{symbol} {pending_error}")
            request = {
                "action": self.mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": norm_volume,
                "type": order_type_map[order_kind],
                "price": norm_entry,
                "sl": norm_sl,
                "tp": norm_tp,
                "deviation": 100,
                "magic": magic,
                "comment": comment[:31],
                "type_time": self._mt5_const("ORDER_TIME_GTC", 0),
            }
            result = self.mt5.order_send(request)
            return result

    def update_position_sl(self, ticket: int, symbol: str, sl: float, tp: float):
        self.initialize()
        with _MT5_LOCK:
            request = {
                "action": self.mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": sl,
                "tp": tp,
            }
            return self.mt5.order_send(request)

    def close_position(self, ticket: int, symbol: str):
        self.initialize()
        with _MT5_LOCK:
            positions = self.mt5.positions_get(ticket=ticket)
            if not positions:
                return None
            pos = positions[0]
            pos_volume = float(_field(pos, "volume", 0.0) or 0.0)
            if pos_volume <= 0:
                return None
        return self.close_position_partial(ticket, symbol, pos_volume)

    def close_position_partial(self, ticket: int, symbol: str, volume: float):
        self.initialize()
        with _MT5_LOCK:
            positions = self.mt5.positions_get(ticket=ticket)
            if not positions:
                raise RuntimeError(f"Position {ticket} not found for {symbol}")
            pos = positions[0]
            pos_type = int(_field(pos, "type", 0))
            pos_volume = float(_field(pos, "volume", 0.0) or 0.0)
            close_volume = self.normalize_volume(symbol, min(float(volume), pos_volume))
            if close_volume <= 0:
                return None

            tick = self.mt5.symbol_info_tick(symbol)
            if tick is None:
                raise RuntimeError(f"No tick for {symbol}: {self.mt5.last_error()}")

            buy_type = self._mt5_const("ORDER_TYPE_BUY", 0)
            order_type = (
                self._mt5_const("ORDER_TYPE_SELL", 1)
                if pos_type == buy_type
                else self._mt5_const("ORDER_TYPE_BUY", 0)
            )
            price = float(
                _field(tick, "bid") if order_type == self._mt5_const("ORDER_TYPE_SELL", 1) else _field(tick, "ask")
            )

            last_result = None
            for filling in self._filling_modes(symbol):
                request = {
                    "action": self.mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "position": ticket,
                    "volume": close_volume,
                    "type": order_type,
                    "price": price,
                    "deviation": 100,
                    "magic": int(_field(pos, "magic", 0) or 0),
                    "comment": str(_field(pos, "comment", "partial TP"))[:31],
                    "type_filling": filling,
                }
                last_result = self.mt5.order_send(request)
                retcode = getattr(last_result, "retcode", None)
                if retcode == self.TRADE_DONE:
                    return last_result
            return last_result
