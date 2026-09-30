"""Forward-only Polymarket wallet-copy experiment, not replayed leaderboard profits."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any

from sqlalchemy import select

from crypto_lab.container import Container
from crypto_lab.domain.bots import BotMode
from crypto_lab.domain.polymarket.wallets import WalletTrade
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.paper_models import PaperPosition
from crypto_lab.infrastructure.db.polymarket_models import PmWallet
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.infrastructure.http import JsonHttpClient
from crypto_lab.infrastructure.polymarket.clients import ClobBooks, DataApiWallets
from crypto_lab.infrastructure.polymarket.mappers import fee_schedule
from crypto_lab.services.paper import lock_portfolio, save_state, state
from crypto_lab.workers.research import ResearchWorker

D = Decimal


def resolved_price(raw: dict[str, Any], token: str) -> Decimal | None:
    if not raw.get("closed") or raw.get("umaResolutionStatus") != "resolved":
        return None
    ids = raw.get("clobTokenIds", [])
    prices = raw.get("outcomePrices", [])
    ids = json.loads(ids) if isinstance(ids, str) else ids
    prices = json.loads(prices) if isinstance(prices, str) else prices
    if token not in ids or len(ids) != len(prices):
        return None
    values: list[Decimal] = [D(str(p)) for p in prices]
    if sum(values) != 1 or any(p not in {D(0), D(1)} for p in values):
        return None
    return values[int(ids.index(token))]


class CopyWorker(ResearchWorker):
    slug = "poly-copy"

    def __init__(self, container: Container) -> None:
        super().__init__(container)
        self.data, self.books = DataApiWallets(), ClobBooks()
        self.gamma = JsonHttpClient("https://gamma-api.polymarket.com", rate_per_second=3)

    async def selection(self) -> dict[str, Any]:
        async with unit_of_work(self.container.session_factory) as s:
            await lock_portfolio(s)
            selected = await state(s, "copy-selection")
            if selected:
                return selected
            wallets = list(await s.scalars(select(PmWallet).order_by(PmWallet.leaderboard_rank)))
            tracked = [w for w in wallets if w.tracked]
            # Freeze the first selection; later trades only. No hindsight reselection.
            candidates = tracked or [
                w
                for w in wallets
                if w.leaderboard_rank
                and w.stats.get("closed_positions", 0) >= 50
                and w.stats.get("style") == "directional"
            ]
            if not candidates:
                return {}
            selected = {
                "wallets": [w.address for w in candidates[:3]],
                "since": utcnow().isoformat(),
                "selection": "watchlist"
                if tracked
                else "automatic top-ranked directional wallets with >=50 closed positions (exploratory)",
            }
            await save_state(s, "copy-selection", selected)
            return selected

    async def market(self, condition: str, token: str) -> dict[str, Any]:
        rows = await self.gamma.get("/markets", condition_ids=condition)
        for row in rows:
            tokens = row.get("clobTokenIds", [])
            tokens = json.loads(tokens) if isinstance(tokens, str) else tokens
            if row.get("conditionId") == condition and token in tokens:
                if "feesEnabled" not in row:
                    raise ValueError("Market fee metadata missing")
                return dict(row)
        raise ValueError("Matching market metadata unavailable")

    async def manage(self, row: PaperPosition, sells: set[tuple[str, str]], mode: BotMode) -> None:
        token = row.detail["asset"]
        raw = await self.market(row.detail["condition"], token)
        payout = resolved_price(raw, token)
        if payout is not None:
            await self.mark_or_exit(
                row, row.quantity * payout, "confirmed market resolution" if mode is BotMode.PAPER else ""
            )
            return
        book = (await self.books.books([token])).get(token)
        fill = book.sell(row.quantity) if book else None
        if fill is None:
            return  # retain capital and mark as stale, never invent a zero fill
        proceeds = max(D(0), fill.notional - fee_schedule(raw).taker_fee(fill))
        ret = proceeds / row.capital - 1
        reason = ""
        if (row.detail["wallet"], token) in sells:
            reason = "source wallet sold (full follower exit)"
        elif ret <= D("-0.30"):
            reason = "30% loss trigger"
        elif ret >= D("0.50"):
            reason = "50% profit trigger"
        elif utcnow() - row.opened_at > timedelta(hours=24):
            reason = "24-hour holding limit"
        await self.mark_or_exit(row, proceeds, reason if mode is BotMode.PAPER else "")

    async def copy_buy(self, trade: WalletTrade) -> str:
        raw = await self.market(trade.condition_id, trade.asset)
        if raw.get("closed") or not raw.get("acceptingOrders"):
            return "market not accepting orders"
        await asyncio.sleep(2)
        book = (await self.books.books([trade.asset])).get(trade.asset)
        if not book or not book.best_ask or trade.price <= 0:
            return "missing executable asks"
        if abs(book.best_ask / trade.price - 1) > D("0.02"):
            return "copy price moved more than 2% from source"
        fee = fee_schedule(raw)
        cap = self.container.settings.paper_trade_limit_usdc
        # Upper-bound per-share fee, then depth walk and recheck actual all-in cost.
        qty = min(trade.size, cap / (book.best_ask + fee.rate + D("0.001"))).quantize(D("0.01"), rounding=ROUND_DOWN)
        if qty < max(book.min_order_size, D(str(raw.get("orderMinSize", 5)))):
            return "minimum share size does not fit 10 USDC"
        fill = book.buy(qty)
        if not fill or abs(fill.average_price / trade.price - 1) > D("0.02"):
            return "depth/slippage exceeds copy limit"
        key = hashlib.sha256(
            f"{trade.wallet}:{trade.tx_hash}:{trade.asset}:{trade.side}:{trade.size}".encode()
        ).hexdigest()
        row = PaperPosition(
            bot=self.slug,
            key="copy-" + key,
            symbol=trade.title[:160],
            venue="Polymarket",
            quantity=qty,
            capital=fill.notional + fee.taker_fee(fill),
            detail={
                "asset": trade.asset,
                "wallet": trade.wallet,
                "condition": trade.condition_id,
                "source_at": trade.at.isoformat(),
                "source_price": str(trade.price),
                "execution": "2s delay, live ask depth, 2% price deviation limit",
            },
        )
        return await self.enter(row) or "paper buy filled"

    async def run_cycle(self, mode: BotMode) -> str:
        chosen = await self.selection()
        if not chosen:
            return "Waiting for wallet tracker data or a watchlisted wallet. No paper entries."
        start = datetime.fromisoformat(chosen["since"])
        fresh: list[WalletTrade] = []
        for wallet in chosen["wallets"]:
            trades = await self.data.trades(wallet, max_rows=100)
            fresh.extend(
                t
                for t in trades
                if max(start, utcnow() - timedelta(minutes=3)) < t.at <= utcnow() and t.wallet == wallet
            )
        positions = await self.positions()
        sells = {(t.wallet, t.asset) for t in fresh if t.side == "SELL"}
        for row in positions:
            await self.manage(row, sells, mode)
        if mode is not BotMode.PAPER:
            return f"Shadow: {len(chosen['wallets'])} frozen wallets; {len(fresh)} recent source trades; no entries."
        held = {p.detail["asset"] for p in positions}
        results: list[str] = []
        for t in sorted(fresh, key=lambda t: t.at):
            if t.side != "BUY" or t.asset in held or (t.wallet, t.asset) in sells or len(held) >= 3:
                continue
            result = await self.copy_buy(t)
            results.append(result)
            if result == "paper buy filled":
                held.add(t.asset)
        return (
            f"Following {len(chosen['wallets'])} frozen wallets; {len(fresh)} recent source trades; "
            f"{len(held)} open assets. "
            + ("; ".join(results[-4:]) or "Waiting for a new qualifying buy; no historical trades replayed.")
        )

    async def aclose(self) -> None:
        await self.data.aclose()
        await self.books.aclose()
        await self.gamma.aclose()
