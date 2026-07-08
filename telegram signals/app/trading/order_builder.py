import MetaTrader5 as mt5
from typing import Dict, Any, Optional
from app.trading.mt5_client import mt5_client
from app.core.logging import logger

MAGIC_NUMBER = 878701  # Copier's unique magic number identifier

class OrderBuilder:
    @staticmethod
    def get_filling_type(symbol_info: Dict[str, Any]) -> int:
        """Determines the appropriate execution filling mode for a symbol."""
        filling_mode = int(symbol_info.get("filling_mode") or symbol_info.get("type_filling") or 0)
        
        # Check against bitmask options in MT5
        # FOK = Fill Or Kill (FOK)
        # IOC = Immediate Or Cancel (IOC)
        # RETURN = Return remaining volume
        if filling_mode & 1:
            return mt5.ORDER_FILLING_FOK
        elif filling_mode & 2:
            return mt5.ORDER_FILLING_IOC
        else:
            # Fallback/Default for most brokers
            return mt5.ORDER_FILLING_RETURN

    @staticmethod
    def build_request(
        symbol: str,
        side: str,
        order_type: str,
        lot: float,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        pending_type: Optional[str] = None,
        deviation: int = 20,
        comment: str = "TG Copier"
    ) -> Dict[str, Any]:
        """
        Builds the raw MT5 trade request dictionary.
        """
        symbol_info = mt5_client.get_symbol_info(symbol)
        if not symbol_info:
            raise ValueError(f"Symbol {symbol} info could not be retrieved from MT5.")

        filling = OrderBuilder.get_filling_type(symbol_info)
        
        request = {
            "symbol": symbol,
            "volume": float(lot),
            "magic": MAGIC_NUMBER,
            "deviation": deviation,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling
        }

        # Determine type & action
        if order_type == "market":
            request["action"] = mt5.TRADE_ACTION_DEAL
            
            # Fetch current prices for execution
            tick = mt5_client.get_tick(symbol)
            if not tick:
                raise ValueError(f"Could not retrieve tick prices for {symbol}.")
                
            if side == "buy":
                request["type"] = mt5.ORDER_TYPE_BUY
                request["price"] = tick["ask"]
            elif side == "sell":
                request["type"] = mt5.ORDER_TYPE_SELL
                request["price"] = tick["bid"]
            else:
                raise ValueError(f"Invalid side: {side}")
        elif order_type == "pending":
            request["action"] = mt5.TRADE_ACTION_PENDING
            request["type_filling"] = mt5.ORDER_FILLING_RETURN
            if not entry_price or entry_price <= 0:
                raise ValueError("Entry price is required for pending orders.")
                
            request["price"] = float(entry_price)
            
            if pending_type == "buy_limit":
                request["type"] = mt5.ORDER_TYPE_BUY_LIMIT
            elif pending_type == "sell_limit":
                request["type"] = mt5.ORDER_TYPE_SELL_LIMIT
            elif pending_type == "buy_stop":
                request["type"] = mt5.ORDER_TYPE_BUY_STOP
            elif pending_type == "sell_stop":
                request["type"] = mt5.ORDER_TYPE_SELL_STOP
            else:
                raise ValueError(f"Invalid pending type: {pending_type}")
        else:
            raise ValueError(f"Invalid order type: {order_type}")

        # Set optional SL / TP (which must be float values)
        if stop_loss:
            request["sl"] = float(stop_loss)
        if take_profit:
            request["tp"] = float(take_profit)

        return request
