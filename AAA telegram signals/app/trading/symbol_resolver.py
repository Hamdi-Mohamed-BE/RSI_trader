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
    "US30": ["DJCUSD.c", "DJCUSD", "US30", "DJ30", "DJI", "US30.cash", "US30m", "US30-STD", "DOW"],
    "DJ30": ["DJCUSD.c", "DJCUSD", "US30", "DJ30", "DJI", "US30.cash", "US30m", "US30-STD", "DOW"],
    "DJI": ["DJCUSD.c", "DJCUSD", "US30", "DJ30", "DJI", "US30.cash", "US30m", "US30-STD", "DOW"],
    "DOW": ["DJCUSD.c", "DJCUSD", "US30", "DJ30", "DJI", "US30.cash", "US30m", "US30-STD", "DOW"],
    "US100": ["NACUSD.c", "NACUSD", "US100", "NAS100", "USTEC", "USTEC100", "NDX", "NAS100.cash", "NAS100m", "NAS100-STD"],
    "NAS100": ["NACUSD.c", "NACUSD", "US100", "NAS100", "USTEC", "USTEC100", "NDX", "NAS100.cash", "NAS100m", "NAS100-STD"],
    "USTEC": ["NACUSD.c", "NACUSD", "US100", "NAS100", "USTEC", "USTEC100", "NDX", "NAS100.cash", "NAS100m", "NAS100-STD"],
    "USTEC100": ["NACUSD.c", "NACUSD", "US100", "NAS100", "USTEC", "USTEC100", "NDX", "NAS100.cash", "NAS100m", "NAS100-STD"],
    "NDX": ["NACUSD.c", "NACUSD", "US100", "NAS100", "USTEC", "USTEC100", "NDX", "NAS100.cash", "NAS100m", "NAS100-STD"],
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

    def _aliases_for(self, requested_symbol: str) -> list[str]:
        if requested_symbol in DEFAULT_ALIAS_MAP:
            return DEFAULT_ALIAS_MAP[requested_symbol]
        for key, values in DEFAULT_ALIAS_MAP.items():
            if requested_symbol in values or self._normalize(requested_symbol) == self._normalize(key):
                return values
        return []

    def _resolve_aliases(self, req_upper: str, broker_symbols: list) -> Tuple[Optional[str], float]:
        aliases = self._aliases_for(req_upper)
        if not aliases:
            return None, 0.0

        # Follow alias priority first. This prevents broker stock symbols like DOW
        # or GOLD from beating the intended CFD/spot symbol.
        for alias in aliases:
            alias_norm = self._normalize(alias)
            for s in broker_symbols:
                if not self._allows_opening(s):
                    continue
                if s.name.upper() == alias.upper() or self._normalize(s.name) == alias_norm:
                    return self._remember(req_upper, s.name, 0.98)
        return None, 0.0

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

        # 2. Resolve known aliases before exact broker symbols. This matters for
        # index names: "DOW" is a stock on many brokers, while Telegram channels
        # usually mean US30/Dow index.
        alias_symbol, alias_confidence = self._resolve_aliases(req_upper, broker_symbols)
        if alias_symbol:
            return alias_symbol, alias_confidence
        
        # 3. Try exact match
        for s in broker_symbols:
            if s.name.upper() == req_upper and self._allows_opening(s):
                return self._remember(req_upper, s.name, 1.0)

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
