import os
from datetime import datetime
import MetaTrader5 as mt5
from typing import Optional, Dict, Any, List, Tuple
from app.core.logging import orders_logger, logger


def _order_filling_from_symbol_info(info: Dict[str, Any]) -> int:
    filling_mode = int(info.get("filling_mode") or info.get("type_filling") or 0)
    if filling_mode & 1:
        return mt5.ORDER_FILLING_FOK
    if filling_mode & 2:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN

class MT5Client:
    def __init__(self):
        self._connected = False

    def connect(self) -> bool:
        """Initializes connection to MetaTrader 5."""
        if self._connected:
            # Check if still active
            if mt5.terminal_info() is not None:
                return True
            else:
                self._connected = False
                
        orders_logger.info("Initializing MetaTrader 5 connection...")
        
        # Initialize MT5
        # If credentials aren't passed, MT5 uses the currently logged in terminal.
        # This matches the goal: "places the trade on the currently active MetaTrader 5 account."
        initialized = mt5.initialize()
        
        if not initialized:
            error_code = mt5.last_error()
            orders_logger.error(f"MetaTrader 5 initialization failed. Error code: {error_code}")
            self._connected = False
            return False
            
        self._connected = True
        orders_logger.info("MetaTrader 5 connection established.")
        
        # Print account info
        acc_info = mt5.account_info()
        if acc_info:
            orders_logger.info(f"Connected to Account: {acc_info.login}, Server: {acc_info.server}, Equity: {acc_info.equity}")
            
        return True

    def disconnect(self):
        """Shutdown MetaTrader 5 connection."""
        if self._connected:
            mt5.shutdown()
            self._connected = False
            orders_logger.info("MetaTrader 5 connection closed.")

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Retrieves currently connected account information."""
        if not self.connect():
            return None
        info = mt5.account_info()
        if info is None:
            return None
        return info._asdict()

    def get_trading_permissions(self) -> Dict[str, Any]:
        """Returns terminal/account trading permissions with a user-facing diagnosis."""
        if not self.connect():
            return {
                "ok": False,
                "message": "MetaTrader 5 is not connected.",
                "terminal_connected": False,
            }
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        terminal_connected = bool(terminal and terminal.connected)
        terminal_trade_allowed = bool(terminal and terminal.trade_allowed)
        trade_api_disabled = bool(terminal and terminal.tradeapi_disabled)
        account_trade_allowed = bool(account and account.trade_allowed)
        account_expert_allowed = bool(account and account.trade_expert)
        ok = (
            terminal_connected
            and terminal_trade_allowed
            and not trade_api_disabled
            and account_trade_allowed
            and account_expert_allowed
        )
        reasons = []
        if not terminal_connected:
            reasons.append("terminal is disconnected")
        if not terminal_trade_allowed:
            reasons.append("AutoTrading/Algo Trading is disabled in the MT5 terminal")
        if trade_api_disabled:
            reasons.append("Python trading API access is disabled")
        if not account_trade_allowed:
            reasons.append("the account does not allow trading")
        if not account_expert_allowed:
            reasons.append("expert trading is disabled for the account")
        return {
            "ok": ok,
            "message": "Trading is enabled." if ok else "; ".join(reasons) + ".",
            "terminal_connected": terminal_connected,
            "terminal_trade_allowed": terminal_trade_allowed,
            "trade_api_disabled": trade_api_disabled,
            "account_trade_allowed": account_trade_allowed,
            "account_expert_allowed": account_expert_allowed,
        }

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieves specifications for a symbol."""
        if not self.connect():
            return None
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        return info._asdict()

    def get_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieves current tick data (ask/bid) for a symbol."""
        if not self.connect():
            return None
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.warning(f"symbol_info_tick returned None for {symbol}: {mt5.last_error()}")
            return None
        return tick._asdict()

    def calculate_order_profit(
        self,
        symbol: str,
        side: str,
        lot: float,
        entry_price: float,
        exit_price: float,
    ) -> Optional[float]:
        """Uses MT5's native profit engine to estimate P/L for a hypothetical trade."""
        if not self.connect():
            return None
        self.select_symbol(symbol, True)
        order_type = mt5.ORDER_TYPE_BUY if str(side).lower() == "buy" else mt5.ORDER_TYPE_SELL
        profit = mt5.order_calc_profit(
            order_type,
            symbol,
            float(lot),
            float(entry_price),
            float(exit_price),
        )
        if profit is None:
            logger.warning(f"order_calc_profit returned None for {symbol}: {mt5.last_error()}")
            return None
        return float(profit)

    def select_symbol(self, symbol: str, select: bool = True) -> bool:
        """Selects a symbol in Market Watch."""
        if not self.connect():
            return False
        return mt5.symbol_select(symbol, select)

    def check_order(self, request: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Checks margin and parameters for a trade request before sending."""
        if not self.connect():
            return False, None, "MT5 terminal not connected"
            
        # Run order check
        check_result = mt5.order_check(request)
        if check_result is None:
            error_code = mt5.last_error()
            return False, None, f"order_check returned None. Error: {error_code}"
            
        result_dict = check_result._asdict()
        
        # check_result.retcode == 0 indicates success
        if check_result.retcode != 0:
            return False, result_dict, check_result.comment
            
        return True, result_dict, None

    def send_order(self, request: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Sends a trade request to the MT5 execution server."""
        if not self.connect():
            return False, None, "MT5 terminal not connected"
            
        orders_logger.info(f"Sending order request: {request}")
        
        result = mt5.order_send(request)
        if result is None:
            error_code = mt5.last_error()
            orders_logger.error(f"order_send returned None. Error code: {error_code}")
            return False, None, f"order_send failed: {error_code}"
            
        result_dict = result._asdict()
        orders_logger.info(f"order_send result: {result_dict}")
        
        success_codes = {mt5.TRADE_RETCODE_DONE}
        if hasattr(mt5, "TRADE_RETCODE_DONE_PARTIAL"):
            success_codes.add(mt5.TRADE_RETCODE_DONE_PARTIAL)
        if result.retcode not in success_codes:
            if result.retcode == 10027:
                error = "AutoTrading is disabled in the MT5 terminal. Enable Algo Trading, then reprocess the signal."
            elif result.retcode == 10026:
                error = "Automated trading is disabled by the broker/server."
            else:
                error = f"Trade rejected: {result.comment} (code {result.retcode})"
            return False, result_dict, error
            
        return True, result_dict, None

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves active trading positions."""
        if not self.connect():
            return []
            
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
            
        if positions is None:
            return []
            
        return [pos._asdict() for pos in positions]

    def get_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves active pending orders."""
        if not self.connect():
            return []
            
        if symbol:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()
            
        if orders is None:
            return []
            
        return [ord._asdict() for ord in orders]

    def get_history_deals(self, date_from: datetime, date_to: datetime) -> List[Dict[str, Any]]:
        """Retrieves account deal history for a date range."""
        if not self.connect():
            return []

        deals = mt5.history_deals_get(date_from, date_to)
        if deals is None:
            return []
        return [deal._asdict() for deal in deals]

    def modify_position(self, ticket: int, stop_loss: float, take_profit: float) -> Tuple[bool, Optional[str]]:
        """Modifies the SL and TP values for an active position."""
        if not self.connect():
            return False, "MT5 terminal not connected"
            
        # Get position details
        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            return False, f"Position with ticket {ticket} not found"
            
        position = positions[0]
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": position.symbol,
            "sl": float(stop_loss),
            "tp": float(take_profit)
        }
        
        success, result, error = self.send_order(request)
        return success, error

    def close_partial_position(self, ticket: int, volume: float, comment: str = "TG TP2 partial") -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Closes part of an active position by sending the opposite deal against the ticket."""
        if not self.connect():
            return False, None, "MT5 terminal not connected"

        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            return False, None, f"Position with ticket {ticket} not found"

        position = positions[0]
        info = mt5.symbol_info(position.symbol)
        tick = mt5.symbol_info_tick(position.symbol)
        if info is None or tick is None:
            return False, None, f"Missing symbol info/tick for {position.symbol}"

        info_dict = info._asdict()
        digits = int(info_dict.get("digits") or 5)
        volume_step = float(info_dict.get("volume_step") or 0.01)
        volume_min = float(info_dict.get("volume_min") or volume_step)
        position_volume = float(position.volume)
        close_volume = min(float(volume), position_volume)

        if close_volume < volume_min:
            return False, None, f"Partial close volume {close_volume:g} is below broker minimum {volume_min:g}"

        steps = int(close_volume / volume_step)
        close_volume = round(steps * volume_step, 8)
        if close_volume < volume_min:
            return False, None, f"Normalized partial close volume is below broker minimum {volume_min:g}"

        is_buy = position.type == mt5.POSITION_TYPE_BUY
        close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
        price = tick.bid if is_buy else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": position.symbol,
            "volume": close_volume,
            "type": close_type,
            "price": round(float(price), digits),
            "deviation": 20,
            "magic": int(position.magic or 0),
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _order_filling_from_symbol_info(info_dict),
        }

        return self.send_order(request)

    def close_position(self, ticket: int, comment: str = "TG daily limit close") -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Closes an active position completely."""
        if not self.connect():
            return False, None, "MT5 terminal not connected"

        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            return False, None, f"Position with ticket {ticket} not found"

        return self.close_partial_position(ticket, float(positions[0].volume), comment=comment)

    def cancel_order(self, ticket: int, comment: str = "TG daily limit cancel") -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Cancels a pending order by ticket."""
        if not self.connect():
            return False, None, "MT5 terminal not connected"

        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": int(ticket),
            "comment": comment[:31],
        }
        return self.send_order(request)

# Global MT5 client
mt5_client = MT5Client()

