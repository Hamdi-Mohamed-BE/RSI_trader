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


def preferred_broker_symbol(symbol: str, broker_suffix: str | None = None) -> str:
    base = market_key(symbol)
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
