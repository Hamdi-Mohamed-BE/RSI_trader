import math
from typing import Dict, Any, Tuple, Optional
from app.trading.mt5_client import mt5_client
from app.core.logging import logger

class RiskCalculator:
    @staticmethod
    def estimate_loss(
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        lot: float,
    ) -> Optional[float]:
        profit = mt5_client.calculate_order_profit(
            symbol=symbol,
            side=side,
            lot=lot,
            entry_price=entry_price,
            exit_price=stop_loss,
        )
        if profit is None:
            return None
        return abs(float(profit))

    @staticmethod
    def calculate_lot(
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        risk_mode: str = "fixed_lot",
        fixed_lot: float = 0.01,
        risk_percent: float = 1.0,
        risk_usd_cap: float = 10.0,
        use_equity_instead_of_balance: bool = True,
        allow_min_lot_if_risk_too_small: bool = True,
        max_lot_limit: Optional[float] = None
    ) -> Tuple[float, Optional[str]]:
        """
        Calculates position size (lot) based on risk parameters, symbol parameters, and entry/SL distance.
        Returns: (calculated_lot, warning_message)
        """
        # If risk mode is fixed_lot, it's trivial, but we still need to normalize it
        # to the broker specs.
        
        # 1. Fetch broker symbol parameters
        symbol_info = mt5_client.get_symbol_info(symbol)
        acc_info = mt5_client.get_account_info()
        
        # Fallbacks if MT5 is unavailable
        tick_size = 0.00001
        tick_value = 1.0
        volume_min = 0.01
        volume_max = 500.0
        volume_step = 0.01
        
        if symbol_info:
            tick_size = symbol_info.get("trade_tick_size") or tick_size
            tick_value = symbol_info.get("trade_tick_value") or tick_value
            volume_min = symbol_info.get("volume_min") or volume_min
            volume_max = symbol_info.get("volume_max") or volume_max
            volume_step = symbol_info.get("volume_step") or volume_step
            
        risk_amount: Optional[float] = None
        risk_per_lot_source = "fixed lot"

        if risk_mode == "fixed_lot":
            lot = fixed_lot
            warning = None
        else:
            # Requires Stop Loss
            if not stop_loss or stop_loss <= 0:
                logger.error(f"Cannot calculate lot size without a valid stop loss. SL={stop_loss}")
                raise ValueError("Stop loss is required for percentage risk or USD cap modes.")
                
            price_distance = abs(entry_price - stop_loss)
            if price_distance <= 0:
                raise ValueError("Stop loss must be different from entry price.")
                
            # Account value calculation
            account_val = 1000.0  # default fallback
            if acc_info:
                if use_equity_instead_of_balance:
                    account_val = acc_info.get("equity") or account_val
                else:
                    account_val = acc_info.get("balance") or account_val
                    
            if risk_mode == "risk_percent":
                risk_amount = account_val * (risk_percent / 100.0)
            elif risk_mode == "risk_usd_cap":
                risk_amount = risk_usd_cap
            else:
                logger.warning(f"Unknown risk mode: {risk_mode}. Defaulting to fixed lot.")
                return fixed_lot, None

            mt5_risk_per_lot = RiskCalculator.estimate_loss(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                lot=1.0,
            )
            if mt5_risk_per_lot and mt5_risk_per_lot > 0:
                risk_per_lot = mt5_risk_per_lot
                risk_per_lot_source = "MT5 order_calc_profit"
            else:
                # Fallback: risk_per_lot = (price_distance / tick_size) * tick_value.
                # MT5's native profit engine is preferred because broker tick values are
                # often misleading for metals, crypto, indices, and custom CFDs.
                risk_per_lot = (price_distance / tick_size) * tick_value
                risk_per_lot_source = "tick value fallback"
            if risk_per_lot <= 0:
                raise ValueError("Calculated risk per lot is zero or negative. Check symbol tick value/size.")
                
            lot = risk_amount / risk_per_lot
            logger.info(
                f"Raw calculated lot: {lot:.5f} "
                f"(Risk Amt: {risk_amount:.2f}, Risk/Lot: {risk_per_lot:.2f}, source={risk_per_lot_source})"
            )
            warning = None

        # 2. Normalization steps
        # Step sizing normalization
        # Let's align lot to volume_step
        if risk_mode in {"risk_percent", "risk_usd_cap"}:
            steps = math.floor((lot / volume_step) + 1e-9)
        else:
            steps = round(lot / volume_step)
        normalized_lot = steps * volume_step
        
        # Round to decimal points matching volume_step precision (e.g. 0.01 step -> 2 decimals)
        decimals = max(0, -int(math.floor(math.log10(volume_step))))
        normalized_lot = round(normalized_lot, decimals)
        
        # Upper limits
        if max_lot_limit:
            normalized_lot = min(normalized_lot, max_lot_limit)
        normalized_lot = min(normalized_lot, volume_max)
        
        # Lower limits and warnings
        if normalized_lot < volume_min:
            if allow_min_lot_if_risk_too_small:
                min_lot_risk = None
                if risk_mode in {"risk_percent", "risk_usd_cap"}:
                    min_lot_risk = RiskCalculator.estimate_loss(
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        lot=volume_min,
                    )
                if (
                    risk_mode in {"risk_percent", "risk_usd_cap"}
                    and risk_amount is not None
                    and min_lot_risk is not None
                    and min_lot_risk > risk_amount
                ):
                    normalized_lot = 0.0
                    warning = (
                        f"Broker minimum lot {volume_min} would risk {min_lot_risk:.2f}, "
                        f"above configured cap {risk_amount:.2f}. Position sizing skipped."
                    )
                else:
                    warning = f"Calculated lot {lot:.4f} is below broker minimum {volume_min}. Using broker minimum lot."
                    normalized_lot = volume_min
            else:
                # Lot size is zero/too small, don't trade
                normalized_lot = 0.0
                warning = f"Calculated lot {lot:.4f} is below broker minimum {volume_min}. Position sizing skipped."

        if risk_mode in {"risk_percent", "risk_usd_cap"} and normalized_lot > 0 and risk_amount is not None:
            actual_risk = RiskCalculator.estimate_loss(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                stop_loss=stop_loss,
                lot=normalized_lot,
            )
            if actual_risk is not None and actual_risk > risk_amount + 0.01:
                warning = (
                    f"Normalized lot {normalized_lot} would risk {actual_risk:.2f}, "
                    f"above configured cap {risk_amount:.2f}. Position sizing skipped."
                )
                normalized_lot = 0.0
                
        return normalized_lot, warning
