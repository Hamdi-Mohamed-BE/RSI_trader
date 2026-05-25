from __future__ import annotations

import re
from dataclasses import dataclass

from .config import AppConfig, SymbolConfig
from .mt5_client import MT5Client
from .symbols import crypto_aliases_for, market_key
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


def parse_manual_trade(text: str, config: AppConfig) -> ManualTradePlan:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Paste a trade signal first.")

    side: str | None = None
    symbol_token: str | None = None
    entry_hint: float | None = None
    sl: float | None = None
    tps: list[float] = []
    lot: float | None = None

    for line in lines:
        clean = line.replace("@", " ").replace(":", " ").replace("=", " ")
        upper = clean.upper()
        word_tokens = re.findall(r"[A-Z][A-Z0-9-]*", upper)
        tokens = re.findall(r"[A-Z][A-Z0-9-]*|[-+]?\d+(?:\.\d+)?", upper)
        numbers = [float(item) for item in re.findall(r"[-+]?\d+(?:\.\d+)?", clean)]

        if "BUY" in word_tokens or "SELL" in word_tokens:
            side = "buy" if "BUY" in word_tokens else "sell"
            side_index = word_tokens.index("BUY") if "BUY" in word_tokens else word_tokens.index("SELL")
            candidates = list(reversed(word_tokens[:side_index])) + word_tokens[side_index + 1 :]
            ignored = {"BUY", "SELL", "NOW", "ENTRY", "ENTERY", "SIGNAL"}
            symbol_token = next((token for token in candidates if token not in ignored), symbol_token)
            if numbers:
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
            tps.append(numbers[-1])
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

    return ManualTradePlan(
        symbol=symbol_cfg.symbol,
        side=side,
        lot=lot,
        sl=float(sl),
        tps=[float(tp) for tp in tps],
        entry_hint=entry_hint,
    )


def resolve_symbol(token: str, config: AppConfig) -> SymbolConfig | None:
    target = _norm_symbol(token)
    aliases: dict[str, SymbolConfig] = {}
    for item in config.symbols:
        values = {
            item.symbol,
            item.key,
            market_key(item.symbol),
            item.name,
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
