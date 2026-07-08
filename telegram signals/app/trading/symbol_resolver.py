import MetaTrader5 as mt5
from typing import Optional, Dict, List, Tuple
from app.trading.mt5_client import mt5_client
from app.trading.lot_config import canonical_symbol
from app.core.logging import logger

DEFAULT_ALIAS_MAP = {
    "GOLD": ["XAUUSD", "XAUUSDm", "XAUUSD-STD", "XAUUSD.raw", "GOLD"],
    "SILVER": ["XAGUSD", "XAGUSDm", "SILVER"],
    "BTC": ["BTCUSD", "BTCUSDm", "BTCUSD-STD", "BTCUSD.raw", "BTC"],
    "US30": ["US30", "DJ30", "DJI", "US30.cash", "US30m", "US30-STD"],
    "NAS100": ["NAS100", "USTEC", "US100", "NAS100.cash", "NAS100m", "NAS100-STD"]
}

# Suffixes to trim for comparison
SUFFIXES = ["M", "C", ".M", ".C", ".RAW", ".PRO", "-STD", "_STD", "-VIP", "_VIP"]

class SymbolResolver:
    def __init__(self):
        self._cache: Dict[str, str] = {}

    def _normalize(self, symbol: str) -> str:
        """Normalizes a symbol by making uppercase and stripping common suffixes/punctuation."""
        return canonical_symbol(symbol)

    def resolve(self, requested_symbol: str) -> Tuple[Optional[str], float]:
        """
        Resolves a raw input symbol (e.g. USDCAD) to a broker-specific symbol (e.g. USDCADm).
        Returns: (broker_symbol, confidence_score)
        """
        req_upper = requested_symbol.upper()
        
        # 1. Check cache first
        if req_upper in self._cache:
            return self._cache[req_upper], 1.0

        # Ensure MT5 is connected
        if not mt5_client.connect():
            logger.warning("MT5 not connected, returning raw symbol.")
            return req_upper, 0.5

        # Fetch all symbols from MT5
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            logger.warning("Failed to retrieve symbols from MT5, returning raw symbol.")
            return req_upper, 0.5

        broker_symbols = [s.name for s in all_symbols]
        
        # 2. Try exact match first
        for s in broker_symbols:
            if s.upper() == req_upper:
                self._cache[req_upper] = s
                # Make sure it's visible
                mt5_client.select_symbol(s, True)
                return s, 1.0

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
            # Check which alias matches a broker symbol
            for s in broker_symbols:
                for alias in aliases:
                    if s.upper() == alias.upper() or self._normalize(s) == self._normalize(alias):
                        self._cache[req_upper] = s
                        mt5_client.select_symbol(s, True)
                        return s, 0.95

        # 4. Try normalized comparison
        req_norm = self._normalize(req_upper)
        for s in broker_symbols:
            if self._normalize(s) == req_norm:
                self._cache[req_upper] = s
                mt5_client.select_symbol(s, True)
                return s, 0.90

        # 5. Fuzzy match prefix / suffix containment
        # Example: Input is EURUSD, broker has "EURUSD.micro"
        for s in broker_symbols:
            s_upper = s.upper()
            if req_upper in s_upper or s_upper in req_upper:
                self._cache[req_upper] = s
                mt5_client.select_symbol(s, True)
                return s, 0.80

        # fallback: return requested in upper case
        return req_upper, 0.3

    def clear_cache(self):
        self._cache.clear()

# Global symbol resolver
symbol_resolver = SymbolResolver()
