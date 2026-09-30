"""Shared helpers for the direct-checkout tests (fake products, chain mocks, test addresses)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.store import db, orders, pricing, settings

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
T0 = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


@dataclass
class FakeProduct:
    slug: str
    label: str
    price: int


def tron_address(seed: int) -> str:
    """A syntactically valid (checksummed) Tron address for tests only."""
    body = b"\x41" + hashlib.sha256(f"calyx-test-{seed}".encode()).digest()[:20]
    raw = body + hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4]
    number = int.from_bytes(raw, "big")
    out = ""
    while number:
        number, rem = divmod(number, 58)
        out = B58[rem] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\x00"))) + out


TEST_TRON = tron_address(1)
OTHER_TRON = tron_address(2)
TEST_BSC = "0x" + "ab" * 20


def fresh_db(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "store.sqlite3"
    monkeypatch.setenv("CALYX_STORE_DB", str(path))
    db.init_db(path)
    return path


def configure(conn, **overrides: Any) -> dict[str, Any]:
    values = {"trc20_address": TEST_TRON, "bep20_address": TEST_BSC} | overrides
    for key, value in values.items():
        settings.set_value(conn, key, value)
    return settings.get_all(conn)


def make_order(conn, products=None, *, network="TRC20", now=T0, email="buyer@example.com", **kw):
    products = products or [FakeProduct("alpha", "Alpha", 449)]
    values = settings.get_all(conn)
    quote = pricing.quote(products)
    return orders.create_order(conn, quote, email=email, network=network, values=values, now=now, **kw)


def tron_fetch(transfers: list[dict[str, Any]], *, tx_blocks: dict[str, int] | None = None, now_block: int = 1000,
               failed: set[str] | None = None, calls: list | None = None):
    tx_blocks = tx_blocks or {}
    failed = failed or set()

    def fetch(method: str, url: str, body, headers):
        if calls is not None:
            calls.append((method, url, body))
        if "/transactions/trc20" in url:
            return {"success": True, "data": transfers, "meta": {}}
        if url.endswith("/wallet/getnowblock"):
            return {"block_header": {"raw_data": {"number": now_block}}}
        if url.endswith("/wallet/gettransactioninfobyid"):
            txid = body["value"]
            if txid not in tx_blocks:
                return {}
            info = {"id": txid, "blockNumber": tx_blocks[txid], "receipt": {"result": "SUCCESS"}}
            if txid in failed:
                info["receipt"] = {"result": "REVERT"}
                info["result"] = "FAILED"
            return info
        raise AssertionError(url)

    return fetch


def trc20_row(txid: str, units: int, *, to: str = TEST_TRON, token: str = settings.USDT_CONTRACTS["TRC20"],
              when: datetime = T0 + timedelta(minutes=5)) -> dict[str, Any]:
    return {"transaction_id": txid, "token_info": {"address": token, "decimals": 6, "symbol": "USDT"},
            "block_timestamp": int(when.timestamp() * 1000), "from": OTHER_TRON, "to": to, "type": "Transfer",
            "value": str(units)}


def bsc_fetch(logs: list[dict[str, Any]], *, latest: int, block_times: dict[int, datetime], calls: list | None = None):
    def fetch(method: str, url: str, body, headers):
        if calls is not None:
            calls.append(body)
        rpc = body["method"]
        if rpc == "eth_blockNumber":
            return {"jsonrpc": "2.0", "id": body["id"], "result": hex(latest)}
        if rpc == "eth_getLogs":
            params = body["params"][0]
            lo, hi = int(params["fromBlock"], 16), int(params["toBlock"], 16)
            chosen = [log for log in logs if lo <= int(log["blockNumber"], 16) <= hi
                      and log["address"].lower() == params["address"].lower()]
            return {"jsonrpc": "2.0", "id": body["id"], "result": chosen}
        if rpc == "eth_getBlockByNumber":
            number = int(body["params"][0], 16)
            return {"jsonrpc": "2.0", "id": body["id"], "result": {"timestamp": hex(int(block_times[number].timestamp()))}}
        raise AssertionError(rpc)

    return fetch


def bep20_log(txid: str, units: int, block: int, *, to: str = TEST_BSC,
              token: str = settings.USDT_CONTRACTS["BEP20"], removed: bool = False) -> dict[str, Any]:
    from app.store.chain import TRANSFER_TOPIC

    return {"address": token, "topics": [TRANSFER_TOPIC, "0x" + "0" * 24 + "cd" * 20, "0x" + "0" * 24 + to[2:].lower()],
            "data": hex(units), "blockNumber": hex(block), "transactionHash": txid, "logIndex": "0x1", "removed": removed}
