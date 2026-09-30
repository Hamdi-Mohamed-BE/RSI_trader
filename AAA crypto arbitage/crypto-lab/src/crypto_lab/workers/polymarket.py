"""Model D workers: arbitrage scanner and wallet tracker."""

from __future__ import annotations

from crypto_lab.container import Container
from crypto_lab.domain.bots import BotMode
from crypto_lab.domain.polymarket.arbitrage import ScanConfig
from crypto_lab.infrastructure.http import JsonHttpClient
from crypto_lab.infrastructure.polymarket.clients import ClobBooks, DataApiWallets, GammaCatalog
from crypto_lab.services.polymarket.scanner import ScannerService, ScannerSettings
from crypto_lab.services.polymarket.settlement import settle_baskets
from crypto_lab.services.polymarket.wallet_tracker import WalletTrackerService, WalletTrackerSettings
from crypto_lab.workers.base import BotWorker


class PolyScannerWorker(BotWorker):
    slug = "poly-scanner"
    interval_s = 30.0

    def __init__(self, container: Container, settings: ScannerSettings | None = None) -> None:
        super().__init__(container)
        self._catalog, self._books = GammaCatalog(), ClobBooks()
        self._resolution = JsonHttpClient("https://gamma-api.polymarket.com", rate_per_second=3)
        settings = settings or ScannerSettings(
            paper_bankroll_usdc=container.settings.paper_balance_usdc,
            scan=ScanConfig(max_capital_usdc=container.settings.paper_trade_limit_usdc),
        )
        self._service = ScannerService(self._catalog, self._books, container.session_factory, settings=settings)

    async def run_cycle(self, mode: BotMode) -> str:
        if mode is BotMode.PAPER:
            await settle_baskets(self.container, self._resolution)
        r = await self._service.run_once(mode)
        return (
            f"events={r.events} markets={r.markets} books={r.books} stale={r.stale_books} "
            f"opps={r.opportunities} new={r.new_opportunities} paper_filled={r.paper_filled} "
            f"paper_missed={r.paper_missed} {r.duration_ms}ms"
        )

    async def aclose(self) -> None:
        await self._catalog.aclose()
        await self._books.aclose()
        await self._resolution.aclose()


class PolyWalletWorker(BotWorker):
    slug = "poly-wallets"
    interval_s = 3600.0

    def __init__(self, container: Container, settings: WalletTrackerSettings | None = None) -> None:
        super().__init__(container)
        self._source = DataApiWallets()
        self._service = WalletTrackerService(self._source, container.session_factory, settings)

    async def run_cycle(self, mode: BotMode) -> str:
        r = await self._service.run_once()
        return (
            f"leaderboard={r.leaderboard_wallets} refreshed={r.wallets_refreshed} new_trades={r.new_trades} "
            f"errors={r.errors}"
        )

    async def aclose(self) -> None:
        await self._source.aclose()
