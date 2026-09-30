"""Read-only public blockchain clients for incoming USDT transfers.

* Tron (TRC20): TronGrid public REST
  ``/v1/accounts/{address}/transactions/trc20?only_to=true&contract_address=...``
  plus ``/wallet/gettransactioninfobyid`` and ``/wallet/getnowblock`` for confirmations.
* BNB Smart Chain (BEP20): public JSON-RPC ``eth_getLogs`` for the ERC-20
  ``Transfer`` topic filtered to the deposit address, ``eth_blockNumber`` and
  ``eth_getBlockByNumber`` for confirmations and block time.

The HTTP layer is injectable so tests use recorded/mocked responses. Nothing
here signs or sends transactions; it only reads public data.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .settings import USDT_CONTRACTS

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
USER_AGENT = "CalyxStorePaymentWatcher/1.0"

Fetch = Callable[[str, str, dict[str, Any] | None, dict[str, str]], Any]


class ChainError(RuntimeError):
    pass


def http_json(method: str, url: str, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None,
              timeout: float = 15.0) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", USER_AGENT)
    if data is not None:
        request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https endpoints
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        raise ChainError(f"{method} {urllib.parse.urlsplit(url).netloc}: {exc}") from exc


def default_fetch(method: str, url: str, body: dict[str, Any] | None, headers: dict[str, str]) -> Any:
    return http_json(method, url, body, headers)


@dataclass
class Transfer:
    network: str
    tx_hash: str
    log_index: int
    from_addr: str
    to_addr: str
    token: str
    amount_units: int
    block_number: int | None
    block_time: datetime | None
    confirmations: int = 0
    success: bool = True


class TronClient:
    network = "TRC20"

    def __init__(self, base_url: str = "https://api.trongrid.io", api_key: str = "", fetch: Fetch | None = None,
                 max_pages: int = 5):
        self.base = base_url.rstrip("/")
        self.headers = {"TRON-PRO-API-KEY": api_key} if api_key else {}
        self.fetch = fetch or default_fetch
        self.max_pages = max_pages
        self._latest: int | None = None

    def incoming(self, address: str, min_timestamp_ms: int) -> list[Transfer]:
        contract = USDT_CONTRACTS["TRC20"]
        params = {"only_to": "true", "contract_address": contract, "limit": "200",
                  "min_timestamp": str(max(0, int(min_timestamp_ms))), "order_by": "block_timestamp,asc"}
        transfers: list[Transfer] = []
        fingerprint = ""
        for _ in range(self.max_pages):
            query = dict(params)
            if fingerprint:
                query["fingerprint"] = fingerprint
            url = f"{self.base}/v1/accounts/{urllib.parse.quote(address)}/transactions/trc20?{urllib.parse.urlencode(query)}"
            payload = self.fetch("GET", url, None, self.headers)
            if not isinstance(payload, dict) or payload.get("success") is False:
                raise ChainError(f"TronGrid error: {str(payload)[:200]}")
            for row in payload.get("data") or []:
                token = (row.get("token_info") or {}).get("address", "")
                if row.get("type", "Transfer") != "Transfer":
                    continue
                try:
                    value = int(str(row.get("value", "0")))
                except ValueError:
                    continue
                stamp = row.get("block_timestamp")
                transfers.append(Transfer(
                    network="TRC20",
                    tx_hash=str(row.get("transaction_id", "")),
                    log_index=0,
                    from_addr=str(row.get("from", "")),
                    to_addr=str(row.get("to", "")),
                    token=str(token),
                    amount_units=value,
                    block_number=None,
                    block_time=datetime.fromtimestamp(int(stamp) / 1000, timezone.utc) if stamp else None,
                ))
            fingerprint = str((payload.get("meta") or {}).get("fingerprint") or "")
            if not fingerprint:
                break
        return transfers

    def latest_block(self) -> int:
        if self._latest is None:
            payload = self.fetch("POST", f"{self.base}/wallet/getnowblock", {}, self.headers)
            try:
                self._latest = int(payload["block_header"]["raw_data"]["number"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ChainError("TronGrid getnowblock: unexpected response") from exc
        return self._latest

    def confirm(self, transfer: Transfer) -> Transfer:
        payload = self.fetch("POST", f"{self.base}/wallet/gettransactioninfobyid", {"value": transfer.tx_hash}, self.headers)
        if not isinstance(payload, dict) or "blockNumber" not in payload:
            transfer.block_number, transfer.confirmations = None, 0  # not yet in a block
            return transfer
        transfer.block_number = int(payload["blockNumber"])
        receipt = payload.get("receipt") or {}
        transfer.success = payload.get("result", "SUCCESS") != "FAILED" and receipt.get("result", "SUCCESS") == "SUCCESS"
        transfer.confirmations = max(0, self.latest_block() - transfer.block_number + 1)
        return transfer


class BscClient:
    network = "BEP20"

    def __init__(self, rpc_url: str = "https://bsc-dataseed.bnbchain.org", fetch: Fetch | None = None):
        self.rpc_url = rpc_url
        self.fetch = fetch or default_fetch
        self._id = 0
        self._block_times: dict[int, datetime] = {}
        self._latest: int | None = None

    def _call(self, method: str, params: list[Any]) -> Any:
        self._id += 1
        payload = self.fetch("POST", self.rpc_url, {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}, {})
        if not isinstance(payload, dict):
            raise ChainError(f"{method}: unexpected response")
        if payload.get("error"):
            raise ChainError(f"{method}: {str(payload['error'])[:200]}")
        return payload.get("result")

    def latest_block(self) -> int:
        if self._latest is None:
            self._latest = int(self._call("eth_blockNumber", []), 16)
        return self._latest

    def block_time(self, number: int) -> datetime | None:
        if number not in self._block_times:
            block = self._call("eth_getBlockByNumber", [hex(number), False])
            if not block:
                return None
            self._block_times[number] = datetime.fromtimestamp(int(block["timestamp"], 16), timezone.utc)
        return self._block_times[number]

    def incoming(self, address: str, from_block: int, to_block: int) -> list[Transfer]:
        topic_to = "0x" + address.lower().removeprefix("0x").rjust(64, "0")
        logs = self._call("eth_getLogs", [{
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
            "address": USDT_CONTRACTS["BEP20"],
            "topics": [TRANSFER_TOPIC, None, topic_to],
        }]) or []
        latest = self.latest_block()
        transfers: list[Transfer] = []
        for log in logs:
            if log.get("removed"):
                continue
            topics = log.get("topics") or []
            if len(topics) < 3 or str(topics[0]).lower() != TRANSFER_TOPIC:
                continue
            number = int(log["blockNumber"], 16)
            transfers.append(Transfer(
                network="BEP20",
                tx_hash=str(log.get("transactionHash", "")).lower(),
                log_index=int(log.get("logIndex", "0x0"), 16),
                from_addr="0x" + str(topics[1])[-40:].lower(),
                to_addr="0x" + str(topics[2])[-40:].lower(),
                token=str(log.get("address", "")),
                amount_units=int(log.get("data") or "0x0", 16),
                block_number=number,
                block_time=None,
                confirmations=max(0, latest - number + 1),
            ))
        return transfers
