"""Small paper-only meme momentum basket using public token checks and executable quote estimates."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any

from crypto_lab.container import Container
from crypto_lab.domain.bots import BotMode
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.paper_models import PaperPosition
from crypto_lab.infrastructure.http import JsonHttpClient
from crypto_lab.infrastructure.polymarket.mappers import parse_dt
from crypto_lab.workers.research import ResearchWorker

D = Decimal
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
NETWORK_COST = D("0.01")  # modeled USDC allowance per swap, not a measured on-chain fee
HAIRCUT = D("0.995")  # 50 bps adverse-fill allowance in addition to quote-included fees


def eligible(token: dict[str, Any]) -> bool:
    audit = token.get("audit") or {}
    pool_at = parse_dt((token.get("firstPool") or {}).get("createdAt"))
    updated = parse_dt(token.get("updatedAt"))
    now = utcnow()
    return bool(
        token.get("isVerified")
        and "meme" in token.get("tags", [])
        and audit.get("mintAuthorityDisabled") is True
        and audit.get("freezeAuthorityDisabled") is True
        and 0 <= float(audit.get("topHoldersPercentage", 101)) <= 35
        and float(token.get("liquidity", 0)) >= 250000
        and pool_at
        and pool_at < now - timedelta(days=7)
        and updated
        and now - timedelta(minutes=5) < updated <= now + timedelta(seconds=30)
    )


class SolanaWorker(ResearchWorker):
    slug = "sol-rotation"
    interval_s = 60

    def __init__(self, container: Container) -> None:
        super().__init__(container)
        self.http = JsonHttpClient("https://api.jup.ag", rate_per_second=0.5, max_retries=2)

    async def swap_quote(self, source: str, target: str, amount: int) -> int:
        q = await self.http.get("/swap/v2/order", inputMint=source, outputMint=target, amount=str(amount))
        if q.get("inputMint") != source or q.get("outputMint") != target or int(q.get("inAmount", 0)) != amount:
            raise ValueError("Jupiter returned an incompatible quote")
        if abs(D(str(q.get("priceImpactPct", "1")))) > D("0.01") or not q.get("routePlan"):
            raise ValueError("Quote failed the 1% price impact / route check")
        output = int(min(D(q["outAmount"]), D(q.get("otherAmountThreshold") or q["outAmount"])) * HAIRCUT)
        if output <= 0:
            raise ValueError("No positive executable quote")
        return output

    async def run_cycle(self, mode: BotMode) -> str:
        positions = await self.positions()
        if positions:
            row = positions[0]
            proceeds = max(
                D(0), D(await self.swap_quote(row.detail["mint"], USDC, int(row.quantity))) / 1000000 - NETWORK_COST
            )
            ret = proceeds / row.capital - 1
            reason = ""
            if ret <= D("-0.10"):
                reason = "10% exit trigger (quote-based, not a guaranteed loss limit)"
            elif ret >= D("0.15"):
                reason = "15% profit trigger"
            elif utcnow() - row.opened_at >= timedelta(hours=1):
                reason = "one-hour holding limit"
            await self.mark_or_exit(row, proceeds, reason if mode is BotMode.PAPER else "")
            return f"{row.symbol}: quote-based net value {proceeds:.4f} USDC; {reason or 'holding'}."
        candidates: list[dict[str, Any]] = []
        for symbol in ("BONK", "WIF", "POPCAT"):
            rows = await self.http.get("/tokens/v2/search", query=symbol)
            verified = [t for t in rows if str(t.get("symbol", "")).upper() == symbol and eligible(t)]
            if verified:
                candidates.append(max(verified, key=lambda t: float(t.get("liquidity", 0))))
        ranked = []
        for t in candidates:
            hour, minute = t.get("stats1h", {}), t.get("stats5m", {})
            if (
                float(hour.get("priceChange", 0)) >= 2
                and float(minute.get("priceChange", 0)) > 0
                and float(hour.get("buyVolume", 0)) + float(hour.get("sellVolume", 0)) >= 50000
            ):
                ranked.append(t)
        if not ranked:
            return (
                f"Scanned BONK/WIF/POPCAT; {len(candidates)} passed basic token checks; "
                "none passed +2% hourly / positive 5-minute momentum. Waiting."
            )
        token = max(ranked, key=lambda t: float(t["stats1h"]["priceChange"]))
        if mode is BotMode.SHADOW:
            return f"Shadow candidate {token['symbol']}; no paper funds committed."
        amount = int(
            ((self.container.settings.paper_trade_limit_usdc - NETWORK_COST) * 1000000).to_integral_value(
                rounding=ROUND_DOWN
            )
        )
        await self.swap_quote(USDC, token["id"], amount)
        await asyncio.sleep(2)
        output = await self.swap_quote(USDC, token["id"], amount)
        # Require a reverse route before buying; illiquid or unsellable tokens are rejected.
        reverse = D(await self.swap_quote(token["id"], USDC, output)) / 1000000 - NETWORK_COST
        capital = D(amount) / 1000000 + NETWORK_COST
        if reverse < capital * D("0.95"):
            return "Skipped: round-trip quote loss exceeds 5%."
        row = PaperPosition(
            bot=self.slug,
            key=f"sol-{token['id']}-{int(utcnow().timestamp() // 1800)}",
            symbol=token["symbol"],
            venue="Jupiter quote",
            quantity=D(output),
            capital=capital,
            mark=reverse,
            mark_at=utcnow(),
            detail={
                "mint": token["id"],
                "decimals": token["decimals"],
                "entry_quote_haircut": str(HAIRCUT),
                "network_cost_per_swap": str(NETWORK_COST),
                "checks": "verified, authorities disabled, top holders <=35%, liquidity >=250k, pool >=7d",
            },
        )
        return (
            await self.enter(row) or f"Paper entry {token['symbol']}: {capital:.2f} USDC including modeled entry cost."
        )

    async def aclose(self) -> None:
        await self.http.aclose()
