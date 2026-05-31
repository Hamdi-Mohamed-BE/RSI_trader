from __future__ import annotations

import re


DEFAULT_BROKER_SYMBOL_SUFFIX = "-VIP"

BROKER_SUFFIXES = {
    "VIP",
    "STD",
    "STANDARD",
    "ECN",
    "RAW",
    "PRO",
    "MINI",
    "MICRO",
    "CRP",
    "CASH",
}

CRYPTO_MARKET_KEYS = {
    "BTCUSD",
    "ETHUSD",
    "SOLUSD",
    "XRPUSD",
    "ADAUSD",
    "BNBUSD",
    "LTCUSD",
    "BCHUSD",
    "DOTUSD",
    "TRXUSD",
    "XLMUSD",
    "UNIUSD",
}

CRYPTO_DEFAULT_LOTS = {
    "BTCUSD": 0.10,
    "ETHUSD": 1.00,
    "SOLUSD": 0.50,
    "XRPUSD": 0.10,
    "ADAUSD": 0.20,
    "BNBUSD": 0.30,
    "LTCUSD": 0.20,
    "BCHUSD": 0.20,
    "DOTUSD": 0.50,
    "TRXUSD": 0.05,
    "XLMUSD": 0.50,
    "UNIUSD": 0.50,
}

CRYPTO_ALIASES = {
    "BTCUSD": {"BTC", "BITCOIN", "BTCUSD"},
    "ETHUSD": {"ETH", "ETHEREUM", "ETHUSD"},
    "SOLUSD": {"SOL", "SOLANA", "SOLUSD"},
    "XRPUSD": {"XRP", "RIPPLE", "XRPUSD"},
    "ADAUSD": {"ADA", "CARDANO", "ADAUSD"},
    "BNBUSD": {"BNB", "BINANCECOIN", "BINANCE", "BNBUSD"},
    "LTCUSD": {"LTC", "LITECOIN", "LTCUSD"},
    "BCHUSD": {"BCH", "BITCOINCASH", "BCHUSD"},
    "DOTUSD": {"DOT", "POLKADOT", "DOTUSD"},
    "TRXUSD": {"TRX", "TRON", "TRXUSD"},
    "XLMUSD": {"XLM", "STELLAR", "XLMUSD"},
    "UNIUSD": {"UNI", "UNISWAP", "UNIUSD"},
}


def normalize_broker_symbol_suffix(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    upper = value.upper()
    if upper[0] in "-._":
        return upper
    return f"-{upper}"


def mt5_symbol_candidates(token: str, broker_suffix: str | None = None) -> list[str]:
    base = re.sub(r"[^A-Z0-9]", "", token.upper())
    if not base:
        return []
    if broker_suffix is None:
        suffix = normalize_broker_symbol_suffix(DEFAULT_BROKER_SYMBOL_SUFFIX)
    else:
        suffix = normalize_broker_symbol_suffix(broker_suffix)
    if not suffix:
        return [base]
    separator = suffix[0] if suffix[0] in "-._" else "-"
    tag = suffix[1:] if suffix[0] in "-._" else suffix
    if not tag:
        return [base]
    ordered = [f"{base}{separator}{tag}", f"{base}{tag}", base]
    seen: set[str] = set()
    candidates: list[str] = []
    for item in ordered:
        key = item.upper()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(item)
    return candidates


def preferred_broker_symbol(
    symbol: str,
    broker_suffix: str | None = None,
    *,
    append_suffix: bool = True,
) -> str:
    base = market_key(symbol)
    if not append_suffix:
        return base
    candidates = mt5_symbol_candidates(base, broker_suffix)
    return candidates[0] if candidates else symbol


def market_key(symbol: str) -> str:
    """Return a stable market key while preserving real broker symbols elsewhere."""
    value = re.sub(r"\s+", "", symbol.strip().upper())
    while True:
        match = re.search(r"([._-])([A-Z0-9]+)$", value)
        if not match or match.group(2) not in BROKER_SUFFIXES:
            return value
        value = value[: match.start()]


def same_market(left: str, right: str) -> bool:
    return market_key(left) == market_key(right)


def crypto_aliases_for(key: str) -> set[str]:
    return set(CRYPTO_ALIASES.get(market_key(key), set()))


def find_symbol_config(symbols: list, token: str):
    stripped = token.strip()
    if stripped:
        for item in symbols:
            for name in (item.demo_symbol, item.live_symbol, item.symbol, item.name):
                if name and name.strip() == stripped:
                    return item

    key = market_key(token)
    for item in symbols:
        if item.key == key or market_key(item.symbol) == key or same_market(item.symbol, token):
            return item
        for name in (item.demo_symbol, item.live_symbol):
            if name and market_key(name) == key:
                return item
    return None


def resolve_trade_symbol(
    symbol: str,
    config,
    *,
    is_demo: bool,
    account_suffix: str = "",
    append_suffix: bool = True,
) -> str:
    """Pick the MT5 symbol string for an account (demo vs live name from settings)."""
    symbol_cfg = find_symbol_config(config.symbols, symbol)
    if symbol_cfg is not None:
        chosen = symbol_cfg.demo_symbol if is_demo else symbol_cfg.live_symbol
        return (chosen.strip() or symbol_cfg.symbol.strip())
    if not append_suffix:
        return market_key(symbol)
    suffix = account_suffix or getattr(config.mt5, "broker_symbol_suffix", DEFAULT_BROKER_SYMBOL_SUFFIX)
    return preferred_broker_symbol(symbol, suffix, append_suffix=True)


def asset_group(symbol: str, name: str = "") -> str:
    key = market_key(symbol)
    label = name.strip().upper()
    symbol_upper = symbol.strip().upper()
    if key in CRYPTO_MARKET_KEYS:
        return "crypto"
    if key in {"XAUUSD", "XAGUSD"} or "GOLD" in label or "SILVER" in label:
        return "metals"
    if "OIL" in symbol_upper or "OIL" in label or symbol_upper.startswith("CL"):
        return "commodities"
    if re.fullmatch(r"[A-Z]{6}", key):
        return "forex"
    return "other"
