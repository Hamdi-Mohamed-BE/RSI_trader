import MetaTrader5 as mt5
from typing import Optional, Dict, Tuple
from app.trading.mt5_client import mt5_client
from app.trading.lot_config import canonical_symbol
from app.core.logging import logger

DEFAULT_ALIAS_MAP = {
    "GOLD": ["XAUUSD", "XAUUSDm", "XAUUSD-STD", "XAUUSD.raw", "GOLD", "XAAUSD"],
    "XAAUSD": ["XAUUSD", "XAUUSDm", "XAUUSD-STD", "XAUUSD.raw", "GOLD"],
    "SILVER": ["XAGUSD", "XAGUSDm", "SILVER"],
    "BTC": ["BTCUSD", "BTCUSDm", "BTCUSD-STD", "BTCUSD.raw", "BTC"],
    "US30": ["US30", "DJ30", "DJI", "US30.cash", "US30m", "US30-STD"],
    "NAS100": ["NAS100", "USTEC", "US100", "NAS100.cash", "NAS100m", "NAS100-STD"]
}

class SymbolResolver:
    def __init__(self):
        self._cache: Dict[str, str] = {}

    def _normalize(self, symbol: str) -> str:
        """Normalizes a symbol by making uppercase and stripping common suffixes/punctuation."""
        return canonical_symbol(symbol)

    def _allows_opening(self, symbol_obj) -> bool:
        trade_mode = getattr(symbol_obj, "trade_mode", None)
        if isinstance(trade_mode, int):
            # 0 = disabled, 3 = close only. Both cannot open new market/pending trades.
            return trade_mode not in {0, 3}
        return True

    def _symbol_is_openable(self, symbol_name: str) -> bool:
        info = mt5.symbol_info(symbol_name)
        if info is None:
            return True
        return self._allows_opening(info)

    def _remember(self, requested_symbol: str, broker_symbol: str, confidence: float) -> Tuple[str, float]:
        self._cache[requested_symbol.upper()] = broker_symbol
        mt5_client.select_symbol(broker_symbol, True)
        return broker_symbol, confidence

    def resolve(self, requested_symbol: str) -> Tuple[Optional[str], float]:
        """
        Resolves a raw input symbol (e.g. USDCAD) to a broker-specific symbol (e.g. USDCADm).
        Returns: (broker_symbol, confidence_score)
        """
        req_upper = requested_symbol.upper()
        
        # 1. Check cache first
        if req_upper in self._cache:
            cached = self._cache[req_upper]
            if self._symbol_is_openable(cached):
                return cached, 1.0
            logger.warning(f"Cached symbol {cached} for {req_upper} is close-only/disabled. Re-resolving.")
            self._cache.pop(req_upper, None)

        # Ensure MT5 is connected
        if not mt5_client.connect():
            logger.warning("MT5 not connected, returning raw symbol.")
            return req_upper, 0.5

        # Fetch all symbols from MT5
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            logger.warning("Failed to retrieve symbols from MT5, returning raw symbol.")
            return req_upper, 0.5

        broker_symbols = list(all_symbols)
        
        # 2. Try exact match first
        for s in broker_symbols:
            if s.name.upper() == req_upper and self._allows_opening(s):
                return self._remember(req_upper, s.name, 1.0)

        # 3. Check alias mapping
        aliases = []
        # Check direct match in alias map
        if req_upper in DEFAULT_ALIAS_MAP:
            aliases = DEFAULT_ALIAS_MAP[req_upper]
        else:
            # Check if requested matches any list entry (reverse lookup)
            for k, val_list in DEFAULT_ALIAS_MAP.items():
                if req_upper in val_list:
                    aliases = val_list
                    break
        
        if aliases:
            # Follow alias priority first. This prevents broker symbols like a close-only
            # stock named "GOLD" from beating the intended gold spot symbol "XAUUSD".
            for alias in aliases:
                alias_norm = self._normalize(alias)
                for s in broker_symbols:
                    if not self._allows_opening(s):
                        continue
                    if s.name.upper() == alias.upper() or self._normalize(s.name) == alias_norm:
                        return self._remember(req_upper, s.name, 0.95)

        # 4. Try normalized comparison
        req_norm = self._normalize(req_upper)
        for s in broker_symbols:
            if self._allows_opening(s) and self._normalize(s.name) == req_norm:
                return self._remember(req_upper, s.name, 0.90)

        # 5. Fuzzy match prefix / suffix containment
        # Example: Input is EURUSD, broker has "EURUSD.micro"
        for s in broker_symbols:
            if not self._allows_opening(s):
                continue
            s_upper = s.name.upper()
            if req_upper in s_upper or s_upper in req_upper:
                return self._remember(req_upper, s.name, 0.80)

        # fallback: return requested in upper case
        return req_upper, 0.3

    def clear_cache(self):
        self._cache.clear()

# Global symbol resolver
symbol_resolver = SymbolResolver()
