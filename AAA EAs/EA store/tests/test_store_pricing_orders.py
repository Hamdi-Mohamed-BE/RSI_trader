"""Store pricing (40% off, buy-3-get-1-free), unique amounts and order expiry."""

from datetime import timedelta

import pytest

from app.catalog import get_sellable_catalog
from app.store import db, orders, pricing
from store_helpers import T0, FakeProduct, configure, fresh_db, make_order


def products(*prices):
    return [FakeProduct(f"p{i}", f"Bot {i}", price) for i, price in enumerate(prices)]


def test_every_bot_is_forty_percent_below_list_price():
    assert pricing.discounted_cents(449) == 26940
    assert pricing.discounted_cents(149) == 8940
    assert pricing.discounted_cents(549) == 32940
    assert pricing.package_sale_cents() == 119400  # $1,990 package -> $1,194
    for product in get_sellable_catalog():
        assert pricing.sale_cents(product) * 10 == product.price * 100 * 6  # exact 60%, integer cents


def test_pack_rule_makes_cheapest_of_every_four_free():
    three = pricing.quote(products(449, 149, 349))
    assert three.free_count == 0 and three.total_cents == three.sale_total_cents
    four = pricing.quote(products(449, 149, 349, 249))
    free = [line for line in four.lines if line.free]
    assert [line.list_cents for line in free] == [14900]
    assert four.total_cents == (26940 + 20940 + 14940)
    assert four.pack_discount_cents == 8940
    eight = pricing.quote(products(449, 449, 449, 449, 149, 179, 199, 229))
    assert sorted(line.list_cents for line in eight.lines if line.free) == [14900, 17900]  # the two cheapest overall
    assert eight.free_count == 2
    assert eight.discount_cents == eight.pack_discount_cents
    seven = pricing.quote(products(*(300,) * 7))
    assert seven.free_count == 1 and seven.next_free_in == 1


def test_duplicate_products_are_charged_once():
    duplicate = [FakeProduct("same", "Same", 449), FakeProduct("same", "Same", 449)]
    assert pricing.quote(duplicate).count == 1


def test_complete_portfolio_price_applies_only_when_cart_has_everything_and_is_cheaper():
    catalog = get_sellable_catalog()
    everything = pricing.quote(catalog, [p.slug for p in catalog])
    pack_total = pricing.quote(catalog).total_cents
    assert everything.package_applied is (pricing.package_sale_cents() < pack_total)
    assert everything.total_cents == min(pack_total, pricing.package_sale_cents())
    assert sum(line.charged_cents for line in everything.lines) == everything.total_cents
    partial = pricing.quote(catalog[:-1], [p.slug for p in catalog])
    assert not partial.package_applied
    cheap = products(1, 1, 1)
    assert not pricing.quote(cheap, [p.slug for p in cheap]).package_applied  # pack total already lower


def test_unique_amounts_among_open_orders(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn)
        created = [make_order(conn) for _ in range(3)]
        rows = [orders.get(conn, c.order_id) for c in created]
        assert [row["offset_cents"] for row in rows] == [1, 2, 3]
        assert len({row["amount_cents"] for row in rows}) == 3
        assert rows[0]["amount_cents"] == 26941
        assert rows[0]["amount_units"] == str(26941 * 10**4)  # TRC20 USDT has 6 decimals
        bep = make_order(conn, network="BEP20")
        assert orders.get(conn, bep.order_id)["amount_units"] == str(26944 * 10**16)  # 18 decimals, globally unique


def test_offsets_are_reused_only_after_the_late_payment_window(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        values = configure(conn)
        first = make_order(conn)
        later = T0 + timedelta(minutes=values["order_expiry_minutes"] + 1)
        orders.expire_orders(conn, later)
        assert orders.get(conn, first.order_id)["status"] == "expired"
        second = make_order(conn, now=later)
        assert orders.get(conn, second.order_id)["offset_cents"] == 2  # expired order still inside late window
        much_later = T0 + timedelta(minutes=values["order_expiry_minutes"] + values["late_payment_minutes"] + 30)
        orders.expire_orders(conn, much_later)
        third = make_order(conn, now=much_later)
        assert orders.get(conn, third.order_id)["offset_cents"] == 1


def test_offsets_exhaust_cleanly(tmp_path, monkeypatch):
    with pytest.raises(orders.OrderError):
        orders.choose_offset(1000, {1000 + i for i in range(1, 100)})


def test_order_expiry_and_validation(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn, order_expiry_minutes=60)
        created = make_order(conn, live_login="12345678", demo_login="87654321")
        order = orders.get(conn, created.order_id)
        assert order["expires_at"] == db.iso(T0 + timedelta(minutes=60))
        assert orders.refresh_status(conn, order, T0 + timedelta(minutes=59))["status"] == "pending"
        assert orders.refresh_status(conn, order, T0 + timedelta(minutes=61))["status"] == "expired"
        assert orders.get_by_token(conn, created.token)["id"] == created.order_id
        assert order["token_hash"] != created.token  # only the hash is stored
        with pytest.raises(orders.OrderError):
            make_order(conn, email="not-an-email")
        with pytest.raises(orders.OrderError):
            make_order(conn, live_login="12ab")
        with pytest.raises(orders.OrderError):
            make_order(conn, live_login="1234567", demo_login="1234567")


def test_checkout_refuses_unconfigured_network(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn, trc20_address="", bep20_address="")
        with pytest.raises(orders.OrderError, match="not configured"):
            make_order(conn)


def test_mark_paid_issues_one_license_per_bot_and_is_idempotent(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn)
        created = make_order(conn, products(449, 149, 349, 249), live_login="5550001")
        assert orders.mark_paid(conn, created.order_id, paid_by="admin:test", note="manual test")
        assert not orders.mark_paid(conn, created.order_id, paid_by="admin:test", note="again")
        rows = list(conn.execute("SELECT * FROM licenses WHERE order_id = ?", (created.order_id,)))
        assert len(rows) == 4
        assert all(row["live_login"] == "5550001" for row in rows)
        assert len({row["license_key"] for row in rows}) == 4
        items = orders.items(conn, created.order_id)
        assert sum(item["free"] for item in items) == 1
        assert [item["label"] for item in items if item["free"]] == ["Bot 1"]
