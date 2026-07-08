import os
import MetaTrader5 as mt5
from typing import Optional, Dict, Any, List, Tuple
from app.core.logging import orders_logger, logger

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
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return tick._asdict()

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
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, result_dict, f"Trade rejected: {result.comment} (code {result.retcode})"
            
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

# Global MT5 client
mt5_client = MT5Client()

