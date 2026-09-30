"""Payment watcher with mocked TronGrid / BSC JSON-RPC responses. No network access."""

from datetime import timedelta

from app.store import db, orders, payments, settings
from app.store.chain import BscClient, TronClient
from store_helpers import (OTHER_TRON, T0, TEST_BSC, bep20_log, bsc_fetch, configure, fresh_db, make_order,
                           tron_fetch, trc20_row)

NOW = T0 + timedelta(minutes=10)


def order_row(conn, created):
    return orders.get(conn, created.order_id)


def test_trc20_exact_amount_with_enough_confirmations_confirms_order(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn, trc20_confirmations=20)
        created = make_order(conn)
        units = int(order_row(conn, created)["amount_units"])
        calls = []
        tron = TronClient(fetch=tron_fetch([trc20_row("tx-ok", units)], tx_blocks={"tx-ok": 980}, now_block=1000, calls=calls))
        summary = payments.scan_once(conn, now=NOW, tron=tron)
        order = order_row(conn, created)
        assert order["status"] == "paid" and order["tx_hash"] == "tx-ok" and order["confirmations"] == 21
        assert order["paid_by"] == "chain:TRC20"
        assert summary["statuses"] == {"matched": 1}
        assert conn.execute("SELECT COUNT(*) FROM licenses WHERE order_id = ?", (created.order_id,)).fetchone()[0] == 1
        url = calls[0][1]
        assert "only_to=true" in url and settings.USDT_CONTRACTS["TRC20"] in url and settings.get(conn, "trc20_address") in url
        # a second scan of the same transfer changes nothing
        payments.scan_once(conn, now=NOW, tron=TronClient(fetch=tron_fetch([trc20_row("tx-ok", units)], tx_blocks={"tx-ok": 980}, now_block=1001)))
        assert conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0] == 1


def test_trc20_waits_for_confirmations_then_confirms(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn, trc20_confirmations=20)
        created = make_order(conn)
        units = int(order_row(conn, created)["amount_units"])
        payments.scan_once(conn, now=NOW, tron=TronClient(fetch=tron_fetch([trc20_row("tx-slow", units)], tx_blocks={"tx-slow": 995}, now_block=1000)))
        order = order_row(conn, created)
        assert order["status"] == "pending" and order["tx_hash"] == "tx-slow" and order["confirmations"] == 6
        status = conn.execute("SELECT status FROM chain_transfers WHERE tx_hash='tx-slow'").fetchone()["status"]
        assert status == "pending_conf"
        payments.scan_once(conn, now=NOW + timedelta(minutes=1), tron=TronClient(fetch=tron_fetch([trc20_row("tx-slow", units)], tx_blocks={"tx-slow": 995}, now_block=1014)))
        assert order_row(conn, created)["status"] == "paid"


def test_trc20_wrong_token_wrong_amount_wrong_recipient_and_failed_tx_do_not_confirm(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn, trc20_confirmations=1)
        created = make_order(conn)
        units = int(order_row(conn, created)["amount_units"])
        rows = [
            trc20_row("tx-token", units, token="TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"),  # not USDT
            trc20_row("tx-amount", units - 10_000),  # 0.01 USDT short
            trc20_row("tx-other-to", units, to=OTHER_TRON),
            trc20_row("tx-failed", units),
        ]
        tron = TronClient(fetch=tron_fetch(rows, tx_blocks={"tx-failed": 900}, now_block=1000, failed={"tx-failed"}))
        summary = payments.scan_once(conn, now=NOW, tron=tron)
        assert order_row(conn, created)["status"] == "pending"
        assert summary["statuses"] == {"ignored": 2, "unmatched": 1, "failed": 1}
        statuses = {row["tx_hash"]: row["status"] for row in conn.execute("SELECT tx_hash, status FROM chain_transfers")}
        assert statuses == {"tx-token": "ignored", "tx-amount": "unmatched", "tx-failed": "failed"}


def test_payment_outside_window_is_left_for_manual_review(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        values = configure(conn, trc20_confirmations=1, late_payment_minutes=30)
        created = make_order(conn)
        units = int(order_row(conn, created)["amount_units"])
        too_early = trc20_row("tx-early", units, when=T0 - timedelta(hours=2))
        payments.scan_once(conn, now=NOW, tron=TronClient(fetch=tron_fetch([too_early], tx_blocks={"tx-early": 10}, now_block=1000)))
        assert order_row(conn, created)["status"] == "pending"
        note = conn.execute("SELECT note FROM chain_transfers WHERE tx_hash='tx-early'").fetchone()["note"]
        assert "outside its payment window" in note
        # late but within the late-payment window: accepted even though the order already expired
        late_time = T0 + timedelta(minutes=values["order_expiry_minutes"] + 20)
        late = trc20_row("tx-late", units, when=late_time)
        payments.scan_once(conn, now=late_time + timedelta(minutes=2),
                           tron=TronClient(fetch=tron_fetch([late], tx_blocks={"tx-late": 999}, now_block=1000)))
        assert order_row(conn, created)["status"] == "paid"


def test_wrong_network_payment_is_flagged_not_confirmed(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn, trc20_confirmations=1)
        created = make_order(conn, network="BEP20")
        cents = order_row(conn, created)["amount_cents"]
        other = make_order(conn, network="TRC20")  # keeps the TRC20 watcher active
        tron_units = cents * 10**4
        payments.scan_once(conn, now=NOW, tron=TronClient(fetch=tron_fetch([trc20_row("tx-wrong-net", tron_units)], tx_blocks={"tx-wrong-net": 999}, now_block=1000)),
                           bsc=BscClient(fetch=bsc_fetch([], latest=5000, block_times={})))
        assert order_row(conn, created)["status"] == "pending"
        assert order_row(conn, other)["status"] == "pending"
        row = conn.execute("SELECT status, note FROM chain_transfers WHERE tx_hash='tx-wrong-net'").fetchone()
        assert row["status"] == "unmatched" and "wrong network" in row["note"] and "BEP20" in row["note"]


def test_bep20_logs_confirm_after_required_blocks(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn, bep20_confirmations=15, bsc_log_chunk=100)
        created = make_order(conn, network="BEP20")
        units = int(order_row(conn, created)["amount_units"])
        logs = [
            bep20_log("0xaaa", units, 4990),
            bep20_log("0xremoved", units, 4991, removed=True),
            bep20_log("0xnotusdt", units, 4992, token="0x" + "11" * 20),
        ]
        times = {4990: T0 + timedelta(minutes=4)}
        calls = []
        summary = payments.scan_once(conn, now=NOW, bsc=BscClient(fetch=bsc_fetch(logs, latest=5000, block_times=times, calls=calls)))
        assert summary["statuses"] == {"pending_conf": 1}
        order = order_row(conn, created)
        assert order["status"] == "pending" and order["tx_hash"] == "0xaaa" and order["confirmations"] == 11
        get_logs = [c for c in calls if c["method"] == "eth_getLogs"]
        topics = get_logs[0]["params"][0]["topics"]
        assert topics[2].endswith(TEST_BSC[2:].lower()) and topics[1] is None
        assert settings.get(conn, "bsc_cursor") == 5000
        # later scan: only new blocks are requested, the stored transfer is re-evaluated
        calls.clear()
        payments.scan_once(conn, now=NOW + timedelta(seconds=10), bsc=BscClient(fetch=bsc_fetch(logs, latest=5010, block_times=times, calls=calls)))
        requested = [int(c["params"][0]["fromBlock"], 16) for c in calls if c["method"] == "eth_getLogs"]
        assert requested == [5001]
        order = order_row(conn, created)
        assert order["status"] == "paid" and order["confirmations"] == 21 and order["paid_units"] == str(units)


def test_bep20_wrong_amount_is_unmatched(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn, bep20_confirmations=1)
        created = make_order(conn, network="BEP20")
        units = int(order_row(conn, created)["amount_units"])
        logs = [bep20_log("0xbbb", units + 10**16, 4990)]  # 0.01 USDT too much
        payments.scan_once(conn, now=NOW, bsc=BscClient(fetch=bsc_fetch(logs, latest=5000, block_times={})))
        assert order_row(conn, created)["status"] == "pending"
        assert conn.execute("SELECT status FROM chain_transfers WHERE tx_hash='0xbbb'").fetchone()["status"] == "unmatched"


def test_watcher_does_nothing_without_open_orders_or_addresses(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)

    def explode(*_args):
        raise AssertionError("no network call expected")

    with db.connect() as conn:
        configure(conn)
        summary = payments.scan_once(conn, now=NOW, tron=TronClient(fetch=explode), bsc=BscClient(fetch=explode))
        assert summary["waiting"] == 0
        make_order(conn)
        make_order(conn, network="BEP20")
        configure(conn, trc20_address="", bep20_address="")  # addresses removed after checkout
        summary = payments.scan_once(conn, now=NOW, tron=TronClient(fetch=explode), bsc=BscClient(fetch=explode))
        assert summary["waiting"] == 2 and summary["errors"] == []
