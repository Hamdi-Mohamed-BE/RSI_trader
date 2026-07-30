from __future__ import annotations

import logging
import re
from typing import Iterable

import MetaTrader5 as mt5

from .models import Candidate, SymbolSpec

LOG = logging.getLogger("us100.symbols")


def normalize(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _spec(info: object) -> SymbolSpec:
    return SymbolSpec(
        name=str(info.name),
        description=str(info.description or ""),
        path=str(info.path or ""),
        digits=int(info.digits),
        point=float(info.point),
        tick_size=float(info.trade_tick_size or info.point),
        tick_value=float(info.trade_tick_value),
        contract_size=float(info.trade_contract_size),
        volume_min=float(info.volume_min),
        volume_max=float(info.volume_max),
        volume_step=float(info.volume_step),
        stops_level_points=int(info.trade_stops_level),
        freeze_level_points=int(info.trade_freeze_level),
        spread_points=int(info.spread),
        trade_mode=int(info.trade_mode),
        filling_mode=int(info.filling_mode),
        visible=bool(info.visible),
    )


def rank_symbols(symbols: Iterable[object], aliases: tuple[str, ...]) -> list[Candidate]:
    results: list[Candidate] = []
    normalized_aliases = tuple(normalize(a) for a in aliases)
    for info in symbols:
        name = normalize(str(info.name))
        description = normalize(str(info.description or ""))
        path = normalize(str(info.path or ""))
        score = 0.0
        reasons: list[str] = []
        for alias in normalized_aliases:
            if name == alias:
                score = max(score, 100.0)
                reasons.append(f"exact alias {alias}")
            elif name.startswith(alias) or name.endswith(alias):
                score = max(score, 85.0)
                reasons.append(f"broker prefix/suffix around {alias}")
            elif alias in name:
                score = max(score, 75.0)
                reasons.append(f"alias {alias} in symbol")
        if "USTECH100" in description or (
            "USTECH" in description and ("100" in description or "INDEX" in description)
        ):
            score = max(score, 96.0)
            reasons.append("description identifies US Tech 100 index")
        elif "NASDAQ100" in description or "NASDAQINDEX" in description:
            score = max(score, 94.0)
            reasons.append("description identifies Nasdaq 100")
        elif "NASDAQ" in description and "FUTURE" in description:
            score = max(score, 72.0)
            reasons.append("Nasdaq future")
        if score == 0:
            continue
        tradable = int(info.trade_mode) != int(mt5.SYMBOL_TRADE_MODE_DISABLED)
        if tradable:
            score += 8
            reasons.append("tradable")
        if bool(info.visible):
            score += 3
            reasons.append("visible")
        if "CASHINDICES" in path or "CASHINDEX" in path:
            score += 12
            reasons.append("cash-index path")
        if "CFDSHARES" in path or "SHARES" in path:
            score -= 45
            reasons.append("penalty: equity/share, not index")
        if "FUTURE" in description or "FUTURES" in path:
            score -= 8
            reasons.append("penalty: expiring future")
        if float(info.trade_tick_size or 0) > 0 and float(info.volume_step or 0) > 0:
            score += 2
            reasons.append("complete broker specifications")
        results.append(
            Candidate(
                symbol=str(info.name),
                description=str(info.description or ""),
                score=score,
                reasons=tuple(dict.fromkeys(reasons)),
                tradable=tradable,
                visible=bool(info.visible),
            )
        )
    return sorted(results, key=lambda c: (-c.score, len(c.symbol), c.symbol))


def discover_us100(
    aliases: tuple[str, ...], override: str = "", ambiguity_margin: float = 5.0
) -> tuple[SymbolSpec, list[Candidate]]:
    symbols = mt5.symbols_get()
    if symbols is None:
        raise RuntimeError(f"Unable to retrieve MT5 symbols: {mt5.last_error()}")
    if override:
        info = mt5.symbol_info(override)
        if info is None:
            raise RuntimeError(f"Configured US100_SYMBOL={override!r} does not exist")
        if int(info.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_DISABLED):
            raise RuntimeError(f"Configured symbol {override} is not tradable")
        if not mt5.symbol_select(override, True):
            raise RuntimeError(f"Could not select {override}: {mt5.last_error()}")
        return _spec(info), [
            Candidate(override, str(info.description or ""), 999, ("manual override",), True, True)
        ]
    ranked = rank_symbols(symbols, aliases)
    if not ranked:
        raise RuntimeError("No US100/Nasdaq-100 candidate was found")
    best = ranked[0]
    if not best.tradable:
        raise RuntimeError(f"Best match {best.symbol} is not tradable")
    if len(ranked) > 1 and best.score - ranked[1].score < ambiguity_margin:
        raise RuntimeError(
            "Ambiguous US100 discovery: "
            + ", ".join(f"{c.symbol}={c.score:.1f}" for c in ranked[:3])
            + ". Set US100_SYMBOL explicitly."
        )
    if not mt5.symbol_select(best.symbol, True):
        raise RuntimeError(f"Could not select {best.symbol}: {mt5.last_error()}")
    info = mt5.symbol_info(best.symbol)
    if info is None:
        raise RuntimeError(f"Could not read selected symbol {best.symbol}")
    LOG.info(
        "Selected %s (%s), score %.1f: %s",
        best.symbol,
        best.description,
        best.score,
        "; ".join(best.reasons),
    )
    return _spec(info), ranked

