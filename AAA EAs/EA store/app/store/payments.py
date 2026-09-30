"""Payment watcher: match incoming USDT transfers to open orders and confirm them.

An order is confirmed automatically only when a transfer

* is USDT (the network's official contract) sent **to** the configured deposit address,
* carries **exactly** the order's unique amount,
* was included in a block between order creation (−10 min clock tolerance) and
  expiry + the late-payment window, and
* has at least the configured number of confirmations.

Everything else (other amounts, other networks, failed transactions) is recorded
as an unmatched transfer for the owner to review in the admin panel, who can
still mark an order paid manually with a note.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any

from . import config, orders
from .chain import BscClient, ChainError, TronClient, Transfer
from .db import connect, iso, parse_iso, utcnow
from .settings import NETWORKS, USDT_CONTRACTS, USDT_DECIMALS, deposit_address, get_all, set_value

log = logging.getLogger("calyx.store.payments")
CLOCK_TOLERANCE = timedelta(minutes=10)
BSC_SECONDS_PER_BLOCK = 0.75  # conservative (short) estimate → scans slightly more blocks, never fewer
MAX_BSC_CHUNKS_PER_SCAN = 25


def awaiting_orders(conn: sqlite3.Connection, now: datetime, late_minutes: int) -> list[sqlite3.Row]:
    cutoff = iso(now - timedelta(minutes=late_minutes) - CLOCK_TOLERANCE)
    return list(conn.execute(
        "SELECT * FROM orders WHERE status = 'pending' OR (status = 'expired' AND expires_at >= ?) ORDER BY created_at",
        (cutoff,),
    ))


def _upsert_transfer(conn: sqlite3.Connection, t: Transfer, status: str, order_id: int | None, note: str | None,
                     now: datetime) -> None:
    conn.execute(
        """INSERT INTO chain_transfers(network, tx_hash, log_index, from_addr, to_addr, token, amount_units, block_number,
               block_time, confirmations, order_id, status, note, seen_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(network, tx_hash, log_index) DO UPDATE SET
               block_number = COALESCE(excluded.block_number, block_number),
               block_time = COALESCE(excluded.block_time, block_time),
               confirmations = excluded.confirmations, order_id = COALESCE(excluded.order_id, order_id),
               status = excluded.status, note = excluded.note""",
        (t.network, t.tx_hash, t.log_index, t.from_addr, t.to_addr, t.token, str(t.amount_units), t.block_number,
         iso(t.block_time), t.confirmations, order_id, status, note, iso(now)),
    )


def _existing(conn: sqlite3.Connection, t: Transfer) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM chain_transfers WHERE network = ? AND tx_hash = ? AND log_index = ?",
                        (t.network, t.tx_hash, t.log_index)).fetchone()


def _same_address(network: str, a: str, b: str) -> bool:
    return a.lower() == b.lower() if network == "BEP20" else a == b


def _wrong_network_note(conn: sqlite3.Connection, t: Transfer) -> str | None:
    scale = 10 ** (USDT_DECIMALS[t.network] - 2)
    if t.amount_units % scale:
        return None
    cents = t.amount_units // scale
    other = conn.execute(
        "SELECT public_id, network FROM orders WHERE amount_cents = ? AND network != ? AND status IN ('pending','expired') "
        "ORDER BY created_at DESC LIMIT 1", (cents, t.network)).fetchone()
    if other:
        return (f"Amount {orders.format_amount(cents)} matches order {other['public_id']}, which expects {other['network']}. "
                "Buyer may have used the wrong network - review and mark paid manually if appropriate.")
    return None


def process_transfer(conn: sqlite3.Connection, t: Transfer, values: dict[str, Any], now: datetime,
                     client: TronClient | BscClient) -> str:
    """Record one observed transfer; confirm its order when every rule holds. Returns the transfer status."""
    address = deposit_address(values, t.network)
    if not address or not _same_address(t.network, t.to_addr, address):
        return "ignored"
    if not _same_address(t.network, t.token, USDT_CONTRACTS[t.network]):
        _upsert_transfer(conn, t, "ignored", None, "Not the USDT contract for this network.", now)
        return "ignored"
    existing = _existing(conn, t)
    if existing is not None and existing["status"] in {"matched", "failed"}:
        return existing["status"]
    candidates = list(conn.execute(
        "SELECT * FROM orders WHERE network = ? AND amount_units = ? AND status IN ('pending','expired') "
        "AND (tx_hash IS NULL OR tx_hash = ?) ORDER BY created_at",
        (t.network, str(t.amount_units), t.tx_hash),
    ))
    if not candidates:
        _upsert_transfer(conn, t, "unmatched", None, _wrong_network_note(conn, t) or "No open order with this exact amount.", now)
        return "unmatched"
    if isinstance(client, TronClient) and t.block_number is None:
        client.confirm(t)
    if isinstance(client, BscClient) and t.block_time is None and t.block_number is not None:
        t.block_time = client.block_time(t.block_number)
    if not t.success:
        _upsert_transfer(conn, t, "failed", None, "Transaction failed on chain.", now)
        return "failed"
    when = t.block_time or now
    late = timedelta(minutes=int(values["late_payment_minutes"]))
    order = next((row for row in candidates
                  if parse_iso(row["created_at"]) - CLOCK_TOLERANCE <= when <= parse_iso(row["expires_at"]) + late), None)
    if order is None:
        _upsert_transfer(conn, t, "unmatched", None,
                         "Exact amount of an order, but sent outside its payment window - review manually.", now)
        return "unmatched"
    required = int(values[f"{t.network.lower()}_confirmations"])
    if t.block_number is None or t.confirmations < required:
        orders.record_detection(conn, order["id"], t.tx_hash, t.from_addr, t.block_number, t.confirmations)
        _upsert_transfer(conn, t, "pending_conf", order["id"], f"{t.confirmations}/{required} confirmations", now)
        return "pending_conf"
    orders.mark_paid(conn, order["id"], paid_by=f"chain:{t.network}", tx_hash=t.tx_hash, tx_from=t.from_addr,
                     tx_block=t.block_number, confirmations=t.confirmations, paid_units=str(t.amount_units), now=now)
    _upsert_transfer(conn, t, "matched", order["id"], f"{t.confirmations} confirmations", now)
    return "matched"


def scan_once(conn: sqlite3.Connection, *, now: datetime | None = None, tron: TronClient | None = None,
              bsc: BscClient | None = None) -> dict[str, Any]:
    now = now or utcnow()
    values = get_all(conn)
    orders.expire_orders(conn, now)
    waiting = awaiting_orders(conn, now, int(values["late_payment_minutes"]))
    summary: dict[str, Any] = {"at": iso(now), "waiting": len(waiting), "statuses": {}, "errors": []}
    by_network = {network: [row for row in waiting if row["network"] == network] for network in NETWORKS}

    def tally(status: str) -> None:
        summary["statuses"][status] = summary["statuses"].get(status, 0) + 1

    tron_address = deposit_address(values, "TRC20")
    if by_network["TRC20"] and tron_address:
        client = tron or TronClient(values["trongrid_url"], values["trongrid_api_key"])
        oldest = min(parse_iso(row["created_at"]) for row in by_network["TRC20"]) - CLOCK_TOLERANCE
        try:
            for transfer in client.incoming(tron_address, int(oldest.timestamp() * 1000)):
                tally(process_transfer(conn, transfer, values, now, client))
        except ChainError as exc:
            summary["errors"].append(f"TRC20: {exc}")

    bsc_address = deposit_address(values, "BEP20")
    pending_bsc = list(conn.execute("SELECT * FROM chain_transfers WHERE network = 'BEP20' AND status = 'pending_conf'"))
    if bsc_address and (by_network["BEP20"] or pending_bsc):
        client = bsc or BscClient(values["bsc_rpc_url"])
        try:
            latest = client.latest_block()
            cursor = int(values["bsc_cursor"] or 0)
            lookback = int(values["bsc_max_lookback"])
            if by_network["BEP20"]:
                oldest = min(parse_iso(row["created_at"]) for row in by_network["BEP20"]) - CLOCK_TOLERANCE
                estimate = int((now - oldest).total_seconds() / BSC_SECONDS_PER_BLOCK) + 200
                start = max(cursor + 1, latest - min(lookback, estimate))
                chunk = int(values["bsc_log_chunk"])
                chunks = 0
                while start <= latest and chunks < MAX_BSC_CHUNKS_PER_SCAN:
                    end = min(latest, start + chunk - 1)
                    for transfer in client.incoming(bsc_address, start, end):
                        tally(process_transfer(conn, transfer, values, now, client))
                    set_value(conn, "bsc_cursor", end)
                    start = end + 1
                    chunks += 1
            for row in pending_bsc:
                transfer = Transfer("BEP20", row["tx_hash"], int(row["log_index"]), row["from_addr"] or "", row["to_addr"],
                                    row["token"], int(row["amount_units"]), row["block_number"], parse_iso(row["block_time"]),
                                    max(0, latest - int(row["block_number"] or latest) + 1))
                tally(process_transfer(conn, transfer, values, now, client))
        except ChainError as exc:
            summary["errors"].append(f"BEP20: {exc}")
    return summary


class PaymentWatcher:
    """Background thread running ``scan_once`` every ``watcher_interval_seconds``."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_summary: dict[str, Any] | None = None
        self.last_error: str | None = None
        self.last_run: str | None = None

    def start(self) -> None:
        if self._thread is not None or not config.watcher_enabled():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="calyx-payment-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop.is_set():
            interval = 30
            try:
                with connect() as conn:
                    interval = int(get_all(conn)["watcher_interval_seconds"])
                    self.last_summary = scan_once(conn)
                    self.last_error = "; ".join(self.last_summary["errors"]) or None
            except Exception as exc:  # keep the thread alive; surface the error in the admin panel
                log.exception("payment watcher scan failed")
                self.last_error = f"{type(exc).__name__}: {exc}"
            self.last_run = iso(utcnow())
            self._stop.wait(max(10, interval))


watcher = PaymentWatcher()
