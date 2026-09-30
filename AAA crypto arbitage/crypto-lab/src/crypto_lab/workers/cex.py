"""Two-venue BTC/USDC spot inventory rotation. No naked short or instant transfer assumptions."""

from __future__ import annotations

import asyncio
from decimal import ROUND_DOWN, Decimal
from typing import Any

from crypto_lab.container import Container
from crypto_lab.domain.bots import BotMode
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.paper_models import PaperPosition
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.infrastructure.http import JsonHttpClient
from crypto_lab.services.paper import close_position, lock_portfolio, open_position, portfolio
from crypto_lab.workers.research import ResearchWorker

D = Decimal
FEE = D("0.002")  # conservative assumed taker fee per venue; not a user's account fee tier
SLIP = D("0.0005")


def quote(levels: list[list[Any]], quantity: Decimal) -> Decimal | None:
    remaining, total = quantity, D(0)
    for level in levels:
        price, size = D(str(level[0])), D(str(level[1]))
        if price <= 0 or size <= 0 or not price.is_finite() or not size.is_finite():
            continue
        take = min(remaining, size)
        total += take * price
        remaining -= take
        if remaining <= 0:
            return total
    return None


class CexWorker(ResearchWorker):
    slug = "cex-arb"

    def __init__(self, container: Container) -> None:
        super().__init__(container)
        self.binance = JsonHttpClient("https://api.binance.com", rate_per_second=2)
        self.okx = JsonHttpClient("https://www.okx.com", rate_per_second=2)
        self.rules: dict[str, tuple[Decimal, Decimal, Decimal]] = {}

    async def books(self) -> dict[str, dict[str, Any]]:
        b, o = await asyncio.gather(
            self.binance.get("/api/v3/depth", symbol="BTCUSDC", limit=20),
            self.okx.get("/api/v5/market/books", instId="BTC-USDC", sz=20),
        )
        if o.get("code") != "0" or not o.get("data"):
            raise ValueError("OKX BTC/USDC book unavailable")
        if abs(int(utcnow().timestamp() * 1000) - int(o["data"][0]["ts"])) > 15000:
            raise ValueError("OKX book is stale; not filling")
        return {"Binance": b, "OKX": o["data"][0]}

    async def load_rules(self) -> None:
        b, o = await asyncio.gather(
            self.binance.get("/api/v3/exchangeInfo", symbol="BTCUSDC"),
            self.okx.get("/api/v5/public/instruments", instType="SPOT", instId="BTC-USDC"),
        )
        symbol = b["symbols"][0]
        filters = {f["filterType"]: f for f in symbol["filters"]}
        lot = filters["LOT_SIZE"]
        notional = filters.get("NOTIONAL", filters.get("MIN_NOTIONAL"))
        item = o["data"][0]
        if symbol["status"] != "TRADING" or item["state"] != "live" or not notional:
            raise ValueError("BTC/USDC is not tradeable with known minimums")
        self.rules = {
            "Binance": (D(lot["stepSize"]), D(lot["minQty"]), D(notional["minNotional"])),
            "OKX": (D(item["lotSz"]), D(item["minSz"]), D(0)),
        }

    def valid_size(self, qty: Decimal, notional: Decimal, venue: str) -> bool:
        step, minimum, min_cost = self.rules[venue]
        return qty >= minimum and notional >= min_cost and qty % step == 0

    async def run_cycle(self, mode: BotMode) -> str:
        if not self.rules:
            await self.load_rules()
        books = await self.books()
        positions = await self.positions()
        cap = self.container.settings.paper_trade_limit_usdc
        if not positions:
            # Seed at most one small spot inventory lot; label its directional exposure explicitly.
            step = max(r[0] for r in self.rules.values())
            price = D(books["OKX"]["asks"][0][0])
            qty = ((cap * D("0.90") / (price * (1 + FEE + SLIP))) / step).to_integral_value(rounding=ROUND_DOWN) * step
            cost = quote(books["OKX"]["asks"], qty)
            if cost is None or not all(self.valid_size(qty, cost, venue) for venue in self.rules):
                return "Waiting: venue minimums cannot fit the 10 USDC inventory allocation."
            if mode is BotMode.SHADOW:
                return "Shadow: BTC/USDC books available. Paper would seed spot inventory (directional exposure)."
            row = PaperPosition(
                bot=self.slug,
                key="cex-inventory-" + utcnow().isoformat(),
                symbol="BTC/USDC inventory",
                venue="OKX",
                quantity=qty,
                capital=cost * (1 + FEE + SLIP),
                detail={"strategy": "inventory rotation", "fee_per_leg": str(FEE), "slippage_per_leg": str(SLIP)},
            )
            return (
                await self.enter(row)
                or "Paper BTC inventory funded on OKX; this has BTC price exposure, not realized arbitrage profit."
            )
        row = positions[0]
        sell_venue, buy_venue = row.venue, "Binance" if row.venue == "OKX" else "OKX"
        sell = quote(books[sell_venue]["bids"], row.quantity)
        buy = quote(books[buy_venue]["asks"], row.quantity)
        if sell is None or buy is None:
            return "Waiting: insufficient book depth."
        proceeds, cost = sell * (1 - FEE - SLIP), buy * (1 + FEE + SLIP)
        await self.mark_or_exit(row, proceeds)
        edge = proceeds - cost
        if mode is not BotMode.PAPER or edge < D("0.01"):
            return (
                f"Scanning BTC/USDC; inventory at {sell_venue}; net rotation edge {edge:+.4f} USDC "
                "(fees/slippage included). No qualifying trade."
            )
        await asyncio.sleep(1.5)
        books = await self.books()
        sell, buy = quote(books[sell_venue]["bids"], row.quantity), quote(books[buy_venue]["asks"], row.quantity)
        if (
            sell is None
            or buy is None
            or not all(self.valid_size(row.quantity, n, v) for n, v in ((sell, sell_venue), (buy, buy_venue)))
        ):
            return "Skipped: depth or venue minimum changed after latency."
        proceeds, cost = sell * (1 - FEE - SLIP), buy * (1 + FEE + SLIP)
        if proceeds - cost < D("0.01") or cost > cap:
            return "Skipped: edge disappeared or replacement lot exceeds 10 USDC."
        async with unit_of_work(self.container.session_factory) as s:
            await lock_portfolio(s)
            balance = await portfolio(s)
            if cost > balance.cash:
                return "Skipped: insufficient shared cash to pre-fund the buy leg."
            replacement = PaperPosition(
                bot=self.slug,
                key=f"cex-rotate-{row.id}",
                symbol=row.symbol,
                venue=buy_venue,
                quantity=row.quantity,
                capital=cost,
                detail={**row.detail, "rotation_edge": str(proceeds - cost)},
            )
            note = await open_position(s, replacement)
            if note:
                return note
            if not await close_position(s, row.id, proceeds, "inventory rotated; P/L includes BTC price movement"):
                raise ValueError("Inventory changed before atomic rotation")
        return f"Paper inventory rotated {sell_venue} → {buy_venue}; matched edge {proceeds - cost:.4f} USDC."

    async def aclose(self) -> None:
        await self.binance.aclose()
        await self.okx.aclose()
