from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import math
from typing import Any

import numpy as np
import pandas as pd


try:
    import MetaTrader5 as mt5
except Exception:  # pragma: no cover - depends on local terminal/package.
    mt5 = None


TIMEFRAME_MINUTES: dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
    "W1": 10080,
}


def _mt5_timeframe(timeframe: str) -> Any:
    if mt5 is None:
        return None
    return {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
    }.get(timeframe)


class MT5Client:
    """Thin and safe MetaTrader 5 adapter.

    This class never places live trades unless a caller explicitly calls a live
    order method and passes live_trading=True. The current app uses it for data.
    """

    def __init__(self) -> None:
        self._connected = False

    @property
    def package_available(self) -> bool:
        return mt5 is not None

    def connect(self) -> bool:
        if mt5 is None:
            return False
        if self._connected:
            return True
        self._connected = bool(mt5.initialize())
        return self._connected

    def shutdown(self) -> None:
        if mt5 is not None and self._connected:
            mt5.shutdown()
        self._connected = False

    def terminal_status(self) -> dict[str, Any]:
        if mt5 is None:
            return {"available": False, "connected": False, "message": "MetaTrader5 package is not installed."}
        connected = self.connect()
        info = mt5.terminal_info() if connected else None
        return {
            "available": True,
            "connected": connected,
            "message": "MT5 connected." if connected else "MT5 package is installed but terminal is not connected.",
            "terminal": info._asdict() if info else None,
        }

    def account_info(self) -> dict[str, Any] | None:
        if mt5 is None or not self.connect():
            return None
        info = mt5.account_info()
        return info._asdict() if info else None

    def resolve_symbol(self, symbol: str) -> str | None:
        if not self.connect():
            return None
        exact = mt5.symbol_info(symbol)
        if exact is not None:
            return symbol

        candidates = list(mt5.symbols_get(f"*{symbol}*") or [])
        preferred = {
            "XAUUSD": ("XAUUSD", "GOLD"),
            "XAGUSD": ("XAGUSD", "SILVER"),
            "BTCUSD": ("BTCUSD", "BITCOIN"),
            "EURUSD": ("EURUSD", "EURO"),
            "USDJPY": ("USDJPY", "YEN"),
            "GBPUSD": ("GBPUSD", "POUND"),
            "USDCAD": ("USDCAD", "CANADIAN"),
            "USDAUD": ("USDAUD", "AUD"),
            "AUDUSD": ("AUDUSD", "AUSSIE", "AUSTRALIAN"),
            "NZDUSD": ("NZDUSD", "KIWI", "NEW ZEALAND"),
            "EURGBP": ("EURGBP", "EURO", "POUND"),
            "EURJPY": ("EURJPY", "EURO", "YEN"),
            "GBPJPY": ("GBPJPY", "POUND", "YEN"),
            "US30": ("US30", "DJ30", "DOW", "WALL STREET"),
            "US300": ("US300", "USA300", "US 300"),
        }.get(symbol, (symbol,))
        filtered = [
            item
            for item in candidates
            if any(token.upper() in item.name.upper() or token.upper() in item.description.upper() for token in preferred)
        ]
        pool = filtered or candidates
        if not pool:
            return None
        pool.sort(key=lambda item: (not item.visible, len(item.name), item.name))
        return pool[0].name

    def symbol_info(self, symbol: str) -> dict[str, Any] | None:
        if not self.connect():
            return None
        resolved = self.resolve_symbol(symbol)
        if not resolved:
            return None
        info = mt5.symbol_info(resolved)
        if info is None:
            return None
        if not info.visible:
            mt5.symbol_select(resolved, True)
            info = mt5.symbol_info(resolved)
        return info._asdict() if info else None

    def current_quote(self, symbol: str) -> dict[str, float] | None:
        if not self.connect():
            return None
        resolved = self.resolve_symbol(symbol)
        if not resolved:
            return None
        tick = mt5.symbol_info_tick(resolved)
        if tick is None:
            return None
        info = mt5.symbol_info(resolved)
        point = float(getattr(info, "point", 0.0) or 0.0) if info else 0.0
        digits = int(getattr(info, "digits", 5) or 5) if info else 5
        if point <= 0:
            point = 10 ** -digits
        bid = float(tick.bid)
        ask = float(tick.ask)
        spread = max(0.0, ask - bid)
        return {
            "bid": bid,
            "ask": ask,
            "last": float(tick.last),
            "spread": spread,
            "spread_points": spread / point if point > 0 else 0.0,
            "point": point,
            "digits": float(digits),
        }

    def normalize_lot(self, symbol: str, lot: float) -> float:
        info = self.symbol_info(symbol)
        if not info:
            return round(max(lot, 0.01), 2)
        min_lot = float(info.get("volume_min") or 0.01)
        max_lot = float(info.get("volume_max") or lot)
        step = float(info.get("volume_step") or 0.01)
        clipped = min(max(lot, min_lot), max_lot)
        steps = round((clipped - min_lot) / step)
        return round(min_lot + steps * step, 4)

    def lot_constraints(self, symbol: str) -> dict[str, float]:
        info = self.symbol_info(symbol)
        if not info:
            return {"min": 0.01, "max": 100.0, "step": 0.01}
        return {
            "min": float(info.get("volume_min") or 0.01),
            "max": float(info.get("volume_max") or 100.0),
            "step": float(info.get("volume_step") or 0.01),
        }

    def normalize_lot_down(self, symbol: str, lot: float) -> float:
        constraints = self.lot_constraints(symbol)
        min_lot = constraints["min"]
        max_lot = constraints["max"]
        step = constraints["step"]
        if lot < min_lot:
            return 0.0
        clipped = min(lot, max_lot)
        steps = math.floor((clipped - min_lot + 1e-12) / step)
        normalized = min_lot + steps * step
        return round(max(min_lot, min(normalized, max_lot)), 4)

    def contract_size(self, symbol: str) -> float:
        info = self.symbol_info(symbol)
        if info and info.get("trade_contract_size"):
            return float(info["trade_contract_size"])
        return {
            "XAUUSD": 100.0,
            "XAGUSD": 5000.0,
            "BTCUSD": 1.0,
            "EURUSD": 100000.0,
            "USDJPY": 100000.0,
            "GBPUSD": 100000.0,
            "USDCAD": 100000.0,
            "USDAUD": 100000.0,
            "AUDUSD": 100000.0,
            "NZDUSD": 100000.0,
            "EURGBP": 100000.0,
            "EURJPY": 100000.0,
            "GBPJPY": 100000.0,
            "US30": 1.0,
            "US300": 1.0,
        }.get(symbol, 1.0)

    def normalize_price(self, symbol: str, price: float) -> float:
        info = self.symbol_info(symbol)
        digits = int(info.get("digits") or 5) if info else 5
        return round(float(price), digits)

    @staticmethod
    def order_comment(signal: dict[str, Any], live_trading: bool = False) -> str:
        grade = str(signal.get("setup_grade") or "A+").replace(" ", "")[:4]
        timeframe = str(signal.get("timeframe") or "").upper()[:5]
        try:
            score = f"S{int(round(float(signal.get('setup_score'))))}"
        except (TypeError, ValueError):
            score = "SNA"
        parts = ["LTA", grade, score]
        if timeframe:
            parts.append(timeframe)
        if not live_trading:
            parts.append("prep")
        return " ".join(parts)[:31]

    def spread_check(
        self,
        signal: dict[str, Any],
        max_spread_risk_percent: float = 15.0,
        max_spread_points: float = 0.0,
        quote: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        symbol = str(signal.get("symbol") or "")
        direction = str(signal.get("direction") or "").upper()
        stop_loss = float(signal.get("stop_loss") or 0.0)
        quote = quote or self.current_quote(symbol)
        if direction not in {"BUY", "SELL"}:
            return {"ok": False, "message": "Signal direction must be BUY or SELL for spread check.", "symbol": symbol}
        if not quote:
            return {"ok": False, "message": "Live bid/ask quote is unavailable, so spread cannot be checked.", "symbol": symbol}

        entry_price = float(quote["ask"] if direction == "BUY" else quote["bid"])
        spread = float(quote.get("spread") or max(0.0, float(quote["ask"]) - float(quote["bid"])))
        spread_points = float(quote.get("spread_points") or 0.0)
        risk_distance = abs(entry_price - stop_loss)
        if entry_price <= 0 or stop_loss <= 0 or risk_distance <= 0:
            return {
                "ok": False,
                "message": "Entry or stop loss is invalid for spread check.",
                "symbol": symbol,
                "direction": direction,
                "quote": quote,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
            }

        spread_risk_percent = (spread / risk_distance) * 100
        reasons: list[str] = []
        if max_spread_risk_percent > 0 and spread_risk_percent > max_spread_risk_percent:
            reasons.append(
                f"Spread is {spread_risk_percent:.2f}% of stop distance, above max {max_spread_risk_percent:.2f}%."
            )
        if max_spread_points > 0 and spread_points > max_spread_points:
            reasons.append(f"Spread is {spread_points:.1f} points, above max {max_spread_points:.1f}.")

        return {
            "ok": not reasons,
            "message": "Spread accepted." if not reasons else "Spread is too wide for this setup.",
            "symbol": symbol,
            "direction": direction,
            "quote": quote,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "spread": spread,
            "spread_points": spread_points,
            "risk_distance": risk_distance,
            "spread_risk_percent": spread_risk_percent,
            "max_spread_risk_percent": max_spread_risk_percent,
            "max_spread_points": max_spread_points,
            "reasons": reasons,
        }

    def estimate_trade_risk(
        self,
        symbol: str,
        direction: str,
        lot: float,
        entry_price: float,
        stop_loss: float,
    ) -> dict[str, Any]:
        if lot <= 0 or entry_price <= 0 or stop_loss <= 0 or entry_price == stop_loss:
            return {"ok": False, "risk": 0.0, "method": "invalid_inputs"}

        resolved = self.resolve_symbol(symbol) or symbol
        direction = direction.upper()
        if mt5 is not None and self.connect():
            order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
            profit = mt5.order_calc_profit(order_type, resolved, float(lot), float(entry_price), float(stop_loss))
            if profit is not None:
                return {
                    "ok": True,
                    "risk": abs(float(profit)),
                    "method": "mt5_order_calc_profit",
                    "broker_symbol": resolved,
                }

        risk = abs(float(entry_price) - float(stop_loss)) * self.contract_size(symbol) * float(lot)
        return {
            "ok": risk > 0,
            "risk": risk,
            "method": "contract_size_fallback",
            "broker_symbol": resolved,
        }

    def risk_based_lot(
        self,
        signal: dict[str, Any],
        risk_percent: float,
        fallback_balance: float | None = None,
        require_account_balance: bool = False,
        quote: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        raw_symbol = str(signal.get("symbol") or "")
        direction = str(signal.get("direction") or "").upper()
        stop_loss = float(signal.get("stop_loss") or 0.0)
        signal_entry = float(signal.get("entry") or 0.0)
        resolved = self.resolve_symbol(raw_symbol) or raw_symbol
        if direction not in {"BUY", "SELL"}:
            return {
                "ok": False,
                "message": "Signal direction must be BUY or SELL for risk-based lot sizing.",
                "risk_percent": risk_percent,
                "symbol": raw_symbol,
                "broker_symbol": resolved,
            }

        account = self.account_info()
        balance = float(account.get("balance") or 0.0) if account else 0.0
        balance_source = "mt5_account_balance"
        if balance <= 0:
            if require_account_balance:
                return {
                    "ok": False,
                    "message": "Account balance is unavailable, so risk-based live lot sizing is blocked.",
                    "risk_percent": risk_percent,
                    "symbol": raw_symbol,
                    "broker_symbol": resolved,
                }
            balance = float(fallback_balance or 0.0)
            balance_source = "fallback_balance"

        if risk_percent <= 0 or balance <= 0:
            return {
                "ok": False,
                "message": "Risk percent or balance is zero.",
                "risk_percent": risk_percent,
                "balance": balance,
                "balance_source": balance_source,
                "symbol": raw_symbol,
                "broker_symbol": resolved,
            }

        quote = quote or self.current_quote(raw_symbol)
        entry_price = signal_entry
        entry_source = "signal_entry"
        if quote and direction in {"BUY", "SELL"}:
            entry_price = float(quote["ask"] if direction == "BUY" else quote["bid"])
            entry_source = "current_quote"

        if entry_price <= 0 or stop_loss <= 0 or entry_price == stop_loss:
            return {
                "ok": False,
                "message": "Entry or stop loss is invalid for risk-based lot sizing.",
                "risk_percent": risk_percent,
                "balance": balance,
                "balance_source": balance_source,
                "symbol": raw_symbol,
                "broker_symbol": resolved,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
            }

        risk_budget = balance * (risk_percent / 100)
        per_lot = self.estimate_trade_risk(raw_symbol, direction, 1.0, entry_price, stop_loss)
        risk_per_lot = float(per_lot.get("risk") or 0.0)
        if not per_lot.get("ok") or risk_per_lot <= 0:
            return {
                "ok": False,
                "message": "Could not estimate risk per 1.0 lot.",
                "risk_percent": risk_percent,
                "balance": balance,
                "balance_source": balance_source,
                "symbol": raw_symbol,
                "broker_symbol": resolved,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "risk_budget": risk_budget,
                "per_lot": per_lot,
            }

        raw_lot = risk_budget / risk_per_lot
        constraints = self.lot_constraints(raw_symbol)
        lot = self.normalize_lot_down(raw_symbol, raw_lot)
        if lot <= 0:
            min_lot_risk = self.estimate_trade_risk(raw_symbol, direction, constraints["min"], entry_price, stop_loss)
            return {
                "ok": False,
                "message": "Risk budget is below broker minimum lot risk; trade blocked instead of rounding up.",
                "risk_percent": risk_percent,
                "balance": balance,
                "balance_source": balance_source,
                "symbol": raw_symbol,
                "broker_symbol": resolved,
                "entry_price": entry_price,
                "entry_source": entry_source,
                "stop_loss": stop_loss,
                "risk_budget": risk_budget,
                "raw_lot": raw_lot,
                "lot_constraints": constraints,
                "min_lot_risk": min_lot_risk,
            }

        estimated = self.estimate_trade_risk(raw_symbol, direction, lot, entry_price, stop_loss)
        step = constraints["step"]
        while estimated.get("ok") and float(estimated.get("risk") or 0.0) > risk_budget * 1.001 and lot > constraints["min"]:
            lot = round(lot - step, 4)
            estimated = self.estimate_trade_risk(raw_symbol, direction, lot, entry_price, stop_loss)

        final_risk = float(estimated.get("risk") or 0.0)
        if not estimated.get("ok") or final_risk <= 0:
            return {
                "ok": False,
                "message": "Could not estimate final normalized lot risk.",
                "risk_percent": risk_percent,
                "balance": balance,
                "balance_source": balance_source,
                "symbol": raw_symbol,
                "broker_symbol": resolved,
                "entry_price": entry_price,
                "entry_source": entry_source,
                "stop_loss": stop_loss,
                "risk_budget": risk_budget,
                "raw_lot": raw_lot,
                "lot": lot,
                "estimated": estimated,
                "lot_constraints": constraints,
            }
        if final_risk > risk_budget * 1.001:
            return {
                "ok": False,
                "message": "Broker-normalized lot still exceeds the risk budget; trade blocked.",
                "risk_percent": risk_percent,
                "balance": balance,
                "balance_source": balance_source,
                "symbol": raw_symbol,
                "broker_symbol": resolved,
                "entry_price": entry_price,
                "entry_source": entry_source,
                "stop_loss": stop_loss,
                "risk_budget": risk_budget,
                "raw_lot": raw_lot,
                "lot": lot,
                "estimated_risk": final_risk,
                "risk_method": estimated.get("method"),
                "lot_constraints": constraints,
            }

        return {
            "ok": bool(estimated.get("ok")),
            "message": "Risk-based lot calculated.",
            "risk_percent": risk_percent,
            "balance": balance,
            "balance_source": balance_source,
            "symbol": raw_symbol,
            "broker_symbol": resolved,
            "direction": direction,
            "entry_price": entry_price,
            "entry_source": entry_source,
            "stop_loss": stop_loss,
            "quote": quote,
            "spread": float(quote.get("spread") or 0.0) if quote else None,
            "spread_points": float(quote.get("spread_points") or 0.0) if quote else None,
            "risk_budget": risk_budget,
            "risk_per_1_lot": risk_per_lot,
            "raw_lot": raw_lot,
            "lot": lot,
            "estimated_risk": final_risk,
            "risk_method": estimated.get("method"),
            "lot_constraints": constraints,
        }

    def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        max_bars: int = 50000,
    ) -> pd.DataFrame | None:
        if not self.connect():
            return None
        resolved = self.resolve_symbol(symbol)
        if not resolved:
            return None
        tf = _mt5_timeframe(timeframe)
        if tf is None:
            return None
        rates = mt5.copy_rates_range(resolved, tf, start, end)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.rename(columns={"tick_volume": "volume"})
        if "volume" not in df.columns:
            df["volume"] = 1.0
        df = df[["time", "open", "high", "low", "close", "volume", "spread"]].copy()
        return df.tail(max_bars).reset_index(drop=True)

    def prepare_order(self, signal: dict[str, Any], lot: float, live_trading: bool = False) -> dict[str, Any]:
        resolved = self.resolve_symbol(signal["symbol"]) or signal["symbol"]
        return {
            "live_trading": bool(live_trading),
            "symbol": signal["symbol"],
            "broker_symbol": resolved,
            "direction": signal["direction"],
            "lot": self.normalize_lot(signal["symbol"], lot),
            "timeframe": signal.get("timeframe"),
            "setup_score": signal.get("setup_score"),
            "setup_grade": signal.get("setup_grade"),
            "entry_model": signal.get("entry_model"),
            "entry": signal["entry"],
            "stop_loss": signal["stop_loss"],
            "take_profit": signal["take_profit"],
            "tp1": signal.get("tp1"),
            "tp2": signal.get("tp2"),
            "tp3": signal.get("tp3"),
            "tp4": signal.get("tp4"),
            "tp5": signal.get("tp5"),
            "comment": self.order_comment(signal, live_trading=live_trading),
        }

    def open_positions(self, symbol: str | None = None, magic: int | None = None) -> list[dict[str, Any]]:
        if mt5 is None or not self.connect():
            return []
        resolved = self.resolve_symbol(symbol) if symbol else None
        raw_positions = mt5.positions_get(symbol=resolved) if resolved else mt5.positions_get()
        positions = [position._asdict() for position in (raw_positions or [])]
        if magic is not None:
            positions = [position for position in positions if int(position.get("magic") or 0) == int(magic)]
        return positions

    def closed_position_deal(self, position_ticket: int, lookback_days: int = 14) -> dict[str, Any]:
        if mt5 is None or not self.connect():
            return {"found": False, "message": "MT5 is not connected."}

        raw_deals = None
        try:
            raw_deals = mt5.history_deals_get(position=int(position_ticket))
        except TypeError:
            raw_deals = None

        if raw_deals is None:
            end = datetime.now()
            start = end - timedelta(days=lookback_days)
            raw_deals = mt5.history_deals_get(start, end)

        deals = []
        for deal in raw_deals or []:
            payload = deal._asdict()
            position_id = int(payload.get("position_id") or payload.get("position") or 0)
            if position_id == int(position_ticket):
                deals.append(payload)

        if not deals:
            return {"found": False, "message": f"No history deal found for position {position_ticket}."}

        close_entries = {
            getattr(mt5, "DEAL_ENTRY_OUT", 1),
            getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
            getattr(mt5, "DEAL_ENTRY_INOUT", 2),
        }
        closing_deals = [deal for deal in deals if int(deal.get("entry", -1)) in close_entries]
        closing_deals.sort(key=lambda deal: (int(deal.get("time_msc") or 0), int(deal.get("time") or 0)))
        closing_deal = closing_deals[-1] if closing_deals else deals[-1]

        reason = int(closing_deal.get("reason") or -1)
        reason_name = {
            getattr(mt5, "DEAL_REASON_SL", 4): "SL",
            getattr(mt5, "DEAL_REASON_TP", 5): "TP",
        }.get(reason, "OTHER")
        profit = sum(
            float(deal.get("profit") or 0.0) + float(deal.get("commission") or 0.0) + float(deal.get("swap") or 0.0)
            for deal in closing_deals or [closing_deal]
        )

        return {
            "found": True,
            "position_ticket": int(position_ticket),
            "closing_deal": closing_deal,
            "exit_reason": reason_name,
            "exit_reason_code": reason,
            "exit_price": float(closing_deal.get("price") or 0.0),
            "profit": profit,
            "closed_at": datetime.fromtimestamp(int(closing_deal.get("time") or 0)).isoformat(timespec="seconds")
            if closing_deal.get("time")
            else None,
            "deals": deals,
        }

    def place_order(self, order: dict[str, Any]) -> dict[str, Any]:
        if not order.get("live_trading"):
            return {"placed": False, "message": "Live trading is disabled."}
        if mt5 is None or not self.connect():
            return {"placed": False, "message": "MT5 is not connected."}
        if not all(order.get(key) is not None for key in ("symbol", "direction", "lot", "stop_loss", "take_profit")):
            return {"placed": False, "message": "Order is missing symbol, direction, lot, SL, or TP."}

        symbol = order.get("broker_symbol") or self.resolve_symbol(order["symbol"])
        if not symbol:
            return {"placed": False, "message": "Broker symbol could not be resolved."}

        info = mt5.symbol_info(symbol)
        if info is None:
            return {"placed": False, "message": f"Symbol info unavailable for {symbol}."}
        if not info.visible:
            mt5.symbol_select(symbol, True)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"placed": False, "message": f"No live tick for {symbol}."}

        direction = str(order["direction"]).upper()
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        price = float(tick.ask if direction == "BUY" else tick.bid)
        point = float(getattr(info, "point", 0.0) or 0.0)
        digits = int(getattr(info, "digits", 5) or 5)
        if point <= 0:
            point = 10 ** -digits
        spread = max(0.0, float(tick.ask) - float(tick.bid))
        spread_points = spread / point if point > 0 else 0.0
        spread_limits = order.get("spread_limits") or {}
        if spread_limits:
            check = self.spread_check(
                {
                    "symbol": order["symbol"],
                    "direction": direction,
                    "stop_loss": order["stop_loss"],
                },
                max_spread_risk_percent=float(spread_limits.get("max_spread_risk_percent") or 0.0),
                max_spread_points=float(spread_limits.get("max_spread_points") or 0.0),
                quote={
                    "bid": float(tick.bid),
                    "ask": float(tick.ask),
                    "last": float(tick.last),
                    "spread": spread,
                    "spread_points": spread_points,
                    "point": point,
                    "digits": float(digits),
                },
            )
            if not check.get("ok"):
                return {
                    "placed": False,
                    "message": "MT5 send blocked because spread widened before execution.",
                    "spread_check": check,
                }
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(order["lot"]),
            "type": order_type,
            "price": price,
            "sl": float(order["stop_loss"]),
            "tp": float(order["take_profit"]),
            "deviation": 20,
            "magic": 27032024,
            "comment": str(order.get("comment") or "LTA A+ automation")[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            return {"placed": False, "message": "MT5 order_send returned no result.", "request": request}
        payload = result._asdict()
        return {
            "placed": payload.get("retcode") == mt5.TRADE_RETCODE_DONE,
            "message": payload.get("comment", ""),
            "request": request,
            "quote": {
                "bid": float(tick.bid),
                "ask": float(tick.ask),
                "last": float(tick.last),
                "spread": spread,
                "spread_points": spread_points,
                "point": point,
            },
            "result": payload,
        }

    def modify_position_sl_tp(
        self,
        ticket: int,
        symbol: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict[str, Any]:
        if mt5 is None or not self.connect():
            return {"modified": False, "message": "MT5 is not connected."}

        resolved = self.resolve_symbol(symbol) or symbol
        request: dict[str, Any] = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(ticket),
            "symbol": resolved,
        }
        if stop_loss is not None:
            request["sl"] = self.normalize_price(resolved, float(stop_loss))
        if take_profit is not None:
            request["tp"] = self.normalize_price(resolved, float(take_profit))

        result = mt5.order_send(request)
        if result is None:
            return {"modified": False, "message": "MT5 order_send returned no result.", "request": request}
        payload = result._asdict()
        return {
            "modified": payload.get("retcode") == mt5.TRADE_RETCODE_DONE,
            "message": payload.get("comment", ""),
            "request": request,
            "result": payload,
        }


def generate_demo_candles(symbol: str, timeframe: str, start: datetime, end: datetime, max_bars: int = 8000) -> pd.DataFrame:
    """Generate deterministic candles so the UI can run before MT5 is installed.

    Demo data is clearly labeled by the backtester and should not be used as a
    performance claim.
    """

    minutes = TIMEFRAME_MINUTES.get(timeframe, 15)
    total_minutes = max(int((end - start).total_seconds() // 60), minutes)
    bars = max(100, min(total_minutes // minutes, max_bars))
    end = min(end, start + timedelta(minutes=bars * minutes))
    times = pd.date_range(start=start, end=end, freq=f"{minutes}min", inclusive="left")
    if len(times) < 100:
        times = pd.date_range(start=start, periods=100, freq=f"{minutes}min")

    seed = int(hashlib.sha256(f"{symbol}-{timeframe}-{start.date()}-{end.date()}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    base = {
        "XAUUSD": 2350.0,
        "XAGUSD": 30.0,
        "BTCUSD": 65000.0,
        "EURUSD": 1.08,
        "USDJPY": 157.0,
        "GBPUSD": 1.27,
        "USDCAD": 1.37,
        "USDAUD": 1.50,
        "AUDUSD": 0.66,
        "NZDUSD": 0.61,
        "EURGBP": 0.85,
        "EURJPY": 170.0,
        "GBPJPY": 200.0,
        "US30": 39000.0,
        "US300": 18000.0,
    }.get(symbol, 100.0)
    volatility = {
        "XAUUSD": 1.8,
        "XAGUSD": 0.04,
        "BTCUSD": 120.0,
        "EURUSD": 0.0011,
        "USDJPY": 0.12,
        "GBPUSD": 0.0014,
        "USDCAD": 0.0012,
        "USDAUD": 0.0014,
        "AUDUSD": 0.0012,
        "NZDUSD": 0.0012,
        "EURGBP": 0.0010,
        "EURJPY": 0.16,
        "GBPJPY": 0.22,
        "US30": 75.0,
        "US300": 45.0,
    }.get(symbol, 1.0)

    drift = np.sin(np.linspace(0, 10, len(times))) * volatility * 0.12
    shocks = rng.normal(0, volatility, len(times))
    close = base + np.cumsum(shocks * 0.22 + drift)
    open_ = np.r_[close[0], close[:-1]]
    body_high = np.maximum(open_, close)
    body_low = np.minimum(open_, close)
    wick = np.abs(rng.normal(volatility * 0.55, volatility * 0.2, len(times)))
    high = body_high + wick
    low = body_low - wick
    volume = rng.integers(100, 1200, len(times)).astype(float)

    # Add a few deliberate liquidity sweeps so the research UI has something to inspect.
    for idx in range(120, len(times), 240):
        low[idx] -= volatility * 4
        close[idx] = max(open_[idx], close[idx]) + volatility * 1.5
        high[idx + 1 : min(idx + 4, len(times))] += volatility * 2
        volume[idx] *= 2.5

    return pd.DataFrame(
        {
            "time": times,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "spread": np.full(len(times), 0.0),
        }
    ).reset_index(drop=True)
