from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from crypto_lab.domain.bots import BotMode
from crypto_lab.domain.polymarket.wallets import WalletTrade
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.paper_models import PaperPosition
from crypto_lab.infrastructure.db.polymarket_models import PmPaperTrade, PmWallet
from crypto_lab.infrastructure.db.session import unit_of_work
from crypto_lab.services.paper import portfolio
from crypto_lab.services.polymarket.settlement import settle_baskets
from crypto_lab.workers import available_workers
from crypto_lab.workers.cex import CexWorker
from crypto_lab.workers.copy import CopyWorker
from crypto_lab.workers.solana import SolanaWorker
from tests.integration.test_shared_paper import prepare
from tests.polymarket_factories import FakeBooks, book

D = Decimal


async def test_cex_seeds_only_once_and_rotates_only_owned_inventory(container, monkeypatch):
    await prepare(container)
    worker = CexWorker(container)
    worker.rules = {v: (D("0.00001"), D("0.00001"), D(5)) for v in ("OKX", "Binance")}
    snapshot = {
        "OKX": {"asks": [["80000", "1"]], "bids": [["79990", "1"]]},
        "Binance": {"asks": [["80000", "1"]], "bids": [["79990", "1"]]},
    }

    async def books():
        return snapshot

    monkeypatch.setattr(worker, "books", books)
    assert "inventory funded" in await worker.run_cycle(BotMode.PAPER)
    assert "No qualifying trade" in await worker.run_cycle(BotMode.PAPER)
    snapshot["OKX"]["bids"] = [["83000", "1"]]
    assert "rotated" in await worker.run_cycle(BotMode.PAPER)
    async with container.session_factory() as s:
        rows = list(await s.scalars(select(PaperPosition)))
        assert len(rows) == 2
        assert rows[0].closed_at and rows[1].closed_at is None
        assert rows[1].venue == "Binance" and rows[1].quantity == rows[0].quantity
        p = await portfolio(s)
        assert p.cash + p.locked == 100 + p.realized
        assert all(r.capital <= 10 for r in rows)
    await worker.aclose()


class CopyData:
    def __init__(self, trades):
        self.rows = trades

    async def trades(self, wallet, *, max_rows):
        return self.rows

    async def aclose(self):
        pass


async def test_copy_is_forward_only_fee_capped_and_exits_on_source_sale(container, monkeypatch):
    await prepare(container)
    wallet = "0x" + "1" * 40
    async with unit_of_work(container.session_factory) as s:
        s.add(PmWallet(address=wallet, tracked=True))
    worker = CopyWorker(container)
    await worker.selection()
    trade = WalletTrade(
        wallet, "tx1", "token", "cond", "BUY", D(100), D("0.5"), "Y", 0, "Test market", "slug", "event", utcnow()
    )
    await worker.data.aclose()
    worker.data = CopyData([replace(trade, at=utcnow() - timedelta(hours=1))])
    await worker.books.aclose()
    worker.books = FakeBooks({"token": book("token", asks=[("0.5", "100")], bids=[("0.49", "100")])})

    async def market(condition, token):
        return {
            "conditionId": condition,
            "feesEnabled": True,
            "feeSchedule": {"rate": "0.07"},
            "acceptingOrders": True,
            "orderMinSize": "5",
        }

    monkeypatch.setattr(worker, "market", market)
    assert "0 recent source" in await worker.run_cycle(BotMode.PAPER)
    assert await worker.positions() == []
    worker.data.rows = [trade]
    assert "paper buy filled" in await worker.run_cycle(BotMode.PAPER)
    row = (await worker.positions())[0]
    assert 0 < row.capital <= 10
    await worker.run_cycle(BotMode.PAPER)
    assert len(await worker.positions()) == 1
    worker.data.rows = [replace(trade, tx_hash="tx2", side="SELL", at=utcnow())]
    await worker.run_cycle(BotMode.PAPER)
    assert await worker.positions() == []
    async with container.session_factory() as s:
        assert (await portfolio(s)).realized < 0  # spread and fees aren't hidden
    await worker.data.aclose()
    await worker.gamma.aclose()


class JupiterFake:
    def __init__(self):
        self.paths = []

    async def get(self, path, **params):
        self.paths.append(path)
        if path == "/tokens/v2/search":
            if params["query"] != "BONK":
                return []
            return [
                {
                    "id": "mint",
                    "symbol": "BONK",
                    "decimals": 6,
                    "isVerified": True,
                    "tags": ["meme"],
                    "audit": {
                        "mintAuthorityDisabled": True,
                        "freezeAuthorityDisabled": True,
                        "topHoldersPercentage": 20,
                    },
                    "liquidity": 300000,
                    "firstPool": {"createdAt": (utcnow() - timedelta(days=30)).isoformat()},
                    "updatedAt": utcnow().isoformat(),
                    "stats1h": {"priceChange": 3, "buyVolume": 50000, "sellVolume": 20000},
                    "stats5m": {"priceChange": 1},
                }
            ]
        return {
            "inputMint": params["inputMint"],
            "outputMint": params["outputMint"],
            "inAmount": params["amount"],
            "outAmount": params["amount"],
            "routePlan": [{}],
            "priceImpactPct": "0.0001",
        }

    async def aclose(self):
        pass


async def test_solana_quotes_only_and_shared_entry_exit_costs(container):
    await prepare(container)
    worker = SolanaWorker(container)
    await worker.http.aclose()
    fake = JupiterFake()
    worker.http = fake
    assert "Paper entry BONK" in await worker.run_cycle(BotMode.PAPER)
    row = (await worker.positions())[0]
    assert row.capital == 10
    async with unit_of_work(container.session_factory) as s:
        held = await s.get(PaperPosition, row.id)
        held.opened_at = utcnow() - timedelta(hours=2)
    assert "holding limit" in await worker.run_cycle(BotMode.PAPER)
    assert not await worker.positions()
    async with container.session_factory() as s:
        assert (await portfolio(s)).cash < 100
    assert set(fake.paths) == {"/tokens/v2/search", "/swap/v2/order"}
    await worker.aclose()


async def test_pending_basket_settles_once_after_explicit_resolution(container):
    await prepare(container)
    async with unit_of_work(container.session_factory) as s:
        s.add(
            PmPaperTrade(
                source="scanner",
                status="open",
                kind="neg_risk_basket_buy",
                fingerprint="basket",
                event_id="e",
                title="test",
                shares=D(10),
                capital=D(9),
                payout=D(10),
                fees=D(0),
                detected_edge=D(1),
                legs=[
                    {"token_id": "a", "shares": "10", "side": "buy"},
                    {"token_id": "b", "shares": "10", "side": "buy"},
                ],
            )
        )

    class Gamma:
        resolved = False

        async def get(self, path, **params):
            return [
                {
                    "closed": True,
                    "umaResolutionStatus": "resolved" if self.resolved else "proposed",
                    "clobTokenIds": '["a", "b"]',
                    "outcomePrices": '["1", "0"]',
                }
            ]

    gamma = Gamma()
    assert await settle_baskets(container, gamma) == 0
    gamma.resolved = True
    assert await settle_baskets(container, gamma) == 1
    assert await settle_baskets(container, gamma) == 0
    async with container.session_factory() as s:
        assert (await portfolio(s)).cash == 101


def test_all_five_workers_registered():
    assert available_workers() == ["cex-arb", "poly-copy", "poly-scanner", "poly-wallets", "sol-rotation"]
