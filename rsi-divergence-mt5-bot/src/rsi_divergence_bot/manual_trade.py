from __future__ import annotations

import re
from dataclasses import dataclass

from .config import AppConfig, SymbolConfig, trade_symbol_for_account
from .mt5_client import MT5Client
from .symbols import crypto_aliases_for, market_key, mt5_symbol_candidates, resolve_trade_symbol
from .telegram_entry import extract_entry_zone_from_line
from .trade_geometry import invalid_market_geometry


def _field(obj, name: str, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


@dataclass
class ManualTradePlan:
    symbol: str
    side: str
    lot: float
    sl: float
    tps: list[float]
    entry_hint: float | None = None
    entry_low: float | None = None
    entry_high: float | None = None


def parse_manual_trade(text: str, config: AppConfig) -> ManualTradePlan:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Paste a trade signal first.")

    side: str | None = None
    symbol_token: str | None = None
    entry_hint: float | None = None
    entry_low: float | None = None
    entry_high: float | None = None
    sl: float | None = None
    tps: list[float] = []
    lot: float | None = None

    for line in lines:
        clean = line.replace("@", " ").replace(":", " ").replace("=", " ")
        upper = clean.upper()
        word_tokens = re.findall(r"[A-Z][A-Z0-9-]*", upper)
        tokens = re.findall(r"[A-Z][A-Z0-9-]*|[-+]?\d+(?:\.\d+)?", upper)
        numbers = [float(item) for item in re.findall(r"[-+]?\d+(?:\.\d+)?", clean)]

        parsed_side, parsed_symbol = _extract_side_and_symbol(line)
        if parsed_side is not None:
            side = parsed_side
            if parsed_symbol:
                symbol_token = parsed_symbol
            zone = extract_entry_zone_from_line(line)
            if zone is not None:
                entry_low = zone.low
                entry_high = zone.high
                entry_hint = zone.high if side == "buy" else zone.low
            elif numbers:
                entry_hint = numbers[0]
            continue

        if any(token in tokens for token in ("SL", "STOP", "STOPLOSS", "LOSS")):
            if not numbers:
                raise ValueError(f"SL line has no price: {line}")
            sl = numbers[-1]
            continue

        if any(
            token.startswith("TP") or token.startswith("TARGET") or token.startswith("TAKEPROFIT")
            for token in tokens
        ):
            if not numbers:
                raise ValueError(f"TP line has no price: {line}")
            tps.extend(numbers)
            continue

        if "LOT" in tokens or "VOLUME" in tokens:
            if not numbers:
                raise ValueError(f"Lot line has no value: {line}")
            lot = numbers[-1]

    if side is None or symbol_token is None:
        raise ValueError("Could not find BUY or SELL with a symbol.")

    symbol_cfg = resolve_symbol(symbol_token, config)
    if symbol_cfg is None:
        raise ValueError(f"Unknown symbol: {symbol_token}")

    if sl is None:
        raise ValueError("Stop loss is required.")
    if not tps:
        raise ValueError("At least one TP is required.")
    if len(tps) > 8:
        raise ValueError("Use 8 TPs or fewer for one manual trade.")

    lot = float(lot if lot is not None else symbol_cfg.lot_per_leg)
    if lot <= 0:
        raise ValueError("Lot must be greater than zero.")

    mt5_symbol = trade_symbol_for_account(symbol_cfg, is_demo=config.mt5.is_demo)

    return ManualTradePlan(
        symbol=mt5_symbol,
        side=side,
        lot=lot,
        sl=float(sl),
        tps=[float(tp) for tp in tps],
        entry_hint=entry_hint,
        entry_low=entry_low,
        entry_high=entry_high,
    )


def _extract_side_and_symbol(line: str) -> tuple[str | None, str | None]:
    stripped = line.strip()
    match = re.match(r"(?i)^\s*([A-Za-z][A-Za-z0-9._-]+)\s+(BUY|SELL)\s*$", stripped)
    if match:
        return match.group(2).lower(), match.group(1)
    match = re.match(r"(?i)^\s*(BUY|SELL)\s+([A-Za-z][A-Za-z0-9._-]+)\s*$", stripped)
    if match:
        return match.group(1).lower(), match.group(2)
    match = re.match(
        r"(?i)^\s*([A-Za-z][A-Za-z0-9._-]+)\s+(BUY|SELL)(?:\s+NOW)?(?:\s+[\d./_\-–—]+)?",
        stripped,
    )
    if match:
        return match.group(2).lower(), match.group(1)
    match = re.match(
        r"(?i)^\s*(BUY|SELL)(?:\s+NOW)?\s+([A-Za-z][A-Za-z0-9._-]+)(?:\s+[\d./_\-–—]+)?",
        stripped,
    )
    if match:
        return match.group(1).lower(), match.group(2)
    return None, None


def resolve_symbol(token: str, config: AppConfig) -> SymbolConfig | None:
    stripped = token.strip()
    if stripped:
        for item in config.symbols:
            for name in (item.demo_symbol, item.live_symbol, item.symbol, item.name):
                if name and name.strip() == stripped:
                    return item

    target = _norm_symbol(token)
    aliases: dict[str, SymbolConfig] = {}
    for item in config.symbols:
        values = {
            item.symbol,
            item.key,
            market_key(item.symbol),
            item.name,
            item.demo_symbol,
            item.live_symbol,
        }
        if item.key == "XAUUSD" or "GOLD" in item.name.upper():
            values.update({"GOLD", "XAU", "XAUUSD"})
        if item.key == "XAGUSD" or "SILVER" in item.name.upper():
            values.update({"SILVER", "XAG", "XAGUSD"})
        values.update(crypto_aliases_for(item.key))
        if "OIL" in item.symbol.upper() or "OIL" in item.name.upper():
            values.update({"OIL", "CL", "CL-OIL"})

        for value in values:
            aliases[_norm_symbol(value)] = item

    return aliases.get(target)


def _auto_symbol_config(mt5_symbol: str, base_key: str, config: AppConfig) -> SymbolConfig:
    base = market_key(base_key) or base_key
    return SymbolConfig(
        symbol=base,
        name=base_key,
        demo_symbol=mt5_symbol,
        live_symbol=mt5_symbol,
        enabled=False,
        signal_active=True,
        lot_per_leg=config.risk.default_forex_lot,
        rr=[1.0, 1.5, 2.0],
    )


def resolve_symbol_for_telegram(
    token: str,
    config: AppConfig,
    client: MT5Client | None = None,
    *,
    auto_register: bool = True,
) -> tuple[SymbolConfig | None, bool]:
    existing = resolve_symbol(token, config)
    if existing is not None:
        return existing, False
    if client is None:
        return None, False

    base = _norm_symbol(token)
    suffix = config.mt5.broker_symbol_suffix if config.mt5.append_broker_symbol_suffix else ""
    candidates = list(mt5_symbol_candidates(token, suffix))
    for item in config.symbols:
        for name in (item.demo_symbol, item.live_symbol, item.symbol):
            key = _norm_symbol(name)
            if key and key not in candidates:
                candidates.append(key)
    for candidate in candidates:
        if client.symbol_info(candidate) is None or client.tick(candidate) is None:
            continue
        for item in config.symbols:
            names = {item.symbol, item.demo_symbol, item.live_symbol}
            if candidate in names or _norm_symbol(candidate) == _norm_symbol(item.symbol):
                return item, False
            if market_key(candidate) == item.key:
                return item, False
        cfg = _auto_symbol_config(candidate, base, config)
        if auto_register:
            config.symbols.append(cfg)
            return cfg, True
        return cfg, False
    return None, False


def execute_manual_trade(plan: ManualTradePlan, client: MT5Client, config: AppConfig, comment: str) -> dict:
    tick = client.tick(plan.symbol)
    if tick is None:
        raise ValueError(f"No live tick for {plan.symbol}.")
    entry = float(_field(tick, "ask") if plan.side == "buy" else _field(tick, "bid"))
    _validate_geometry(plan, entry)

    tickets: list[dict] = []
    failed: list[dict] = []
    for index, tp in enumerate(plan.tps, start=1):
        result = client.send_market(
            plan.symbol,
            plan.side,
            plan.lot,
            plan.sl,
            tp,
            config.bot.magic,
            f"{comment} TP{index}",
        )
        retcode = getattr(result, "retcode", None)
        order = int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0)
        row = {
            "tp_index": index,
            "tp": tp,
            "retcode": retcode,
            "order": order,
            "result": str(result),
        }
        if retcode == client.TRADE_DONE and order:
            tickets.append(row)
        else:
            failed.append(row)

    return {
        "symbol": plan.symbol,
        "side": plan.side,
        "lot": plan.lot,
        "entry": entry,
        "sl": plan.sl,
        "tps": plan.tps,
        "tickets": tickets,
        "failed": failed,
    }


def _validate_geometry(plan: ManualTradePlan, entry: float) -> None:
    label = "current ask" if plan.side == "buy" else "current bid"
    reason = invalid_market_geometry(plan.side, entry, plan.sl, plan.tps, label=label)
    if reason:
        raise ValueError(reason)


def _norm_symbol(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())
