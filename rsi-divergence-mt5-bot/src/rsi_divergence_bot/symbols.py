from __future__ import annotations

import re


DEFAULT_BROKER_SYMBOL_SUFFIX = "-VIP"

BROKER_SUFFIXES = {
    "M",
    "C",
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


def signal_copy_broker_symbols(token: str) -> tuple[str, str, str]:
    """Config table key plus demo (-VIP) and live (-STD) broker names for signal auto-register."""
    base = market_key(token)
    if not base:
        base = re.sub(r"[^A-Z0-9]", "", token.strip().upper())
    return base, f"{base}-VIP", f"{base}-STD"


def token_mt5_symbol_candidates(token: str, broker_suffix: str | None = None) -> list[str]:
    """MT5 names to try for a signal token — never includes unrelated symbols from settings."""
    base, demo_name, live_name = signal_copy_broker_symbols(token)
    ordered = [demo_name, live_name, base]
    if broker_suffix is not None:
        ordered.extend(mt5_symbol_candidates(token, broker_suffix))
    else:
        ordered.extend(mt5_symbol_candidates(token, "-VIP"))
        ordered.extend(mt5_symbol_candidates(token, "-STD"))
        ordered.append(base)
    seen: set[str] = set()
    candidates: list[str] = []
    for item in ordered:
        key = item.upper()
        if not key or key in seen:
            continue
        if market_key(item) != base:
            continue
        seen.add(key)
        candidates.append(item)
    return candidates


def first_available_mt5_symbol(client, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if client.symbol_info(candidate) is None or client.tick(candidate) is None:
            continue
        return candidate
    return None


def discover_mt5_symbol(client, token: str, candidates: list[str] | None = None) -> str | None:
    direct = first_available_mt5_symbol(client, candidates or [])
    if direct is not None:
        return direct
    if not hasattr(client, "symbols"):
        return None

    requested = re.sub(r"[^A-Z0-9]", "", market_key(token).upper())
    if not requested:
        return None
    scored: list[tuple[int, int, str]] = []
    try:
        broker_symbols = client.symbols() or []
    except Exception:  # noqa: BLE001
        return None
    for item in broker_symbols:
        if isinstance(item, dict):
            name = str(item.get("name") or "")
        else:
            name = str(getattr(item, "name", item))
        normalized = re.sub(r"[^A-Z0-9]", "", name.upper())
        if normalized == requested:
            score = 110
        elif normalized.startswith(requested):
            score = 96
        elif normalized.endswith(requested):
            score = 82
        elif len(requested) >= 4 and requested in normalized:
            score = 68
        else:
            continue
        scored.append((-score, len(name), name))

    for _score, _length, name in sorted(scored):
        try:
            tick = client.tick(name)
            info = client.symbol_info(name)
        except Exception:  # noqa: BLE001
            continue
        if info is None or tick is None:
            continue
        if isinstance(tick, dict):
            bid = float(tick.get("bid", 0.0) or 0.0)
            ask = float(tick.get("ask", 0.0) or 0.0)
        else:
            bid = float(getattr(tick, "bid", 0.0) or 0.0)
            ask = float(getattr(tick, "ask", 0.0) or 0.0)
        if bid > 0 and ask > 0:
            return name
    return None


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
        if match and match.group(2) in BROKER_SUFFIXES:
            value = value[: match.start()]
            continue
        attached = next(
            (
                suffix
                for suffix in sorted(BROKER_SUFFIXES, key=len, reverse=True)
                if len(suffix) > 1 and value.endswith(suffix) and len(value) - len(suffix) >= 3
            ),
            None,
        )
        if attached:
            value = value[: -len(attached)]
            continue
        if value.endswith(("M", "C")):
            candidate = value[:-1]
            if re.fullmatch(r"[A-Z]{6}|[A-Z]{2,5}\d{2,3}", candidate):
                value = candidate
                continue
        return value


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


def settings_mt5_symbol(symbol_cfg, *, is_demo: bool) -> str:
    """Broker symbol from Settings (demo_symbol / live_symbol), else config table key."""
    chosen = symbol_cfg.demo_symbol if is_demo else symbol_cfg.live_symbol
    return (chosen.strip() or symbol_cfg.symbol.strip())


def settings_mt5_symbol_from_config(symbol_cfg, config) -> str:
    return settings_mt5_symbol(symbol_cfg, is_demo=bool(config.mt5.is_demo))


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
        return settings_mt5_symbol(symbol_cfg, is_demo=is_demo)
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
