"""Polymarket HTTP adapters against a mocked transport (request shapes, pagination, mapping)."""

import json
from decimal import Decimal

import httpx

from crypto_lab.infrastructure.polymarket.clients import ClobBooks, DataApiWallets, GammaCatalog


def _market(cid: str) -> dict[str, object]:
    return {
        "conditionId": cid,
        "question": cid,
        "slug": cid,
        "active": True,
        "closed": False,
        "enableOrderBook": True,
        "clobTokenIds": json.dumps([f"{cid}-y", f"{cid}-n"]),
        "outcomes": json.dumps(["Yes", "No"]),
        "feesEnabled": False,
    }


async def test_gamma_stops_at_volume_floor_and_skips_empty_events() -> None:
    seen: list[dict[str, str]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        return httpx.Response(
            200,
            json=[
                {"id": "1", "title": "big", "volume24hr": 9000, "markets": [_market("a")]},
                {"id": "2", "title": "no markets", "volume24hr": 8000, "markets": []},
                {"id": "3", "title": "small", "volume24hr": 10, "markets": [_market("b")]},
            ],
        )

    catalog = GammaCatalog(transport=httpx.MockTransport(handle))
    events = await catalog.active_events(max_events=10, min_volume_24h=100)
    await catalog.aclose()
    assert [e.event_id for e in events] == ["1"]
    assert seen[0]["order"] == "volume24hr" and seen[0]["closed"] == "false"


async def test_clob_books_batches_unique_tokens() -> None:
    bodies: list[list[dict[str, str]]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        return httpx.Response(
            200,
            json=[
                {"asset_id": b["token_id"], "timestamp": "1", "bids": [], "asks": [{"price": "0.5", "size": "1"}]}
                for b in body
            ],
        )

    books = ClobBooks(transport=httpx.MockTransport(handle), batch_size=2)
    result = await books.books(["t1", "t2", "t1", "t3"])
    await books.aclose()
    assert [len(b) for b in bodies] == [2, 1]
    assert sorted(result) == ["t1", "t2", "t3"] and result["t3"].best_ask == Decimal("0.5")


async def test_data_api_paginates_until_a_short_page() -> None:
    offsets: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/leaderboard":
            offset = int(request.url.params["offset"])
            offsets.append(str(offset))
            size = 50 if offset == 0 else 3
            return httpx.Response(
                200,
                json=[
                    {"rank": str(offset + i + 1), "proxyWallet": f"0x{offset + i:040x}", "pnl": 1, "vol": 2}
                    for i in range(size)
                ],
            )
        if request.url.path == "/closed-positions":
            return httpx.Response(200, json=[{"asset": "a", "proxyWallet": "0xw", "realizedPnl": "5"}])
        return httpx.Response(200, json=[{"asset": "a", "proxyWallet": "0xw", "timestamp": 1790000000, "side": "BUY"}])

    api = DataApiWallets(transport=httpx.MockTransport(handle))
    leaders = await api.leaderboard(period="month", order_by="pnl", limit=60)
    closed = await api.closed_positions("0xw", max_rows=10)
    trades = await api.trades("0xw", max_rows=10)
    await api.aclose()
    assert len(leaders) == 53 and offsets == ["0", "50"]
    assert closed[0].realized_pnl == Decimal(5) and trades[0].side == "BUY"
