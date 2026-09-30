"""License issue / activation check / revoke / account binding, plus the MQL5 license gate structure."""

import hashlib
import hmac
import re
from datetime import timedelta
from pathlib import Path

import pytest

from app.store import builds, db, licenses, orders
from app.store.deliverables import deliverable_for, sellable_products
from store_helpers import T0, FakeProduct, configure, fresh_db, make_order

MANIFEST = {
    "builds": {
        "calyx-orb-test-ea-00000001": {"products": ["orb-a", "orb-b"], "compiled": True},
        "calyx-other-ea-00000002": {"products": ["other"], "compiled": True},
    },
    "products": {
        "orb-a": {"build_id": "calyx-orb-test-ea-00000001", "magic": 111},
        "orb-b": {"build_id": "calyx-orb-test-ea-00000001", "magic": 222},
        "other": {"build_id": "calyx-other-ea-00000002", "magic": 333},
    },
}
BUILD = "calyx-orb-test-ea-00000001"
SECRET = b"test-license-secret-000000000000000000000000"


@pytest.fixture()
def paid_license(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn)
        created = make_order(conn, [FakeProduct("orb-a", "ORB A", 449)])
        orders.mark_paid(conn, created.order_id, paid_by="admin:test", note="test payment")
        lic = conn.execute("SELECT * FROM licenses WHERE order_id = ?", (created.order_id,)).fetchone()
    return lic


def request(key, login="5550001", mode="real", magic=111, build=BUILD, server="Broker-Live", product="orb-a", nonce="ab" * 16):
    return {"key": key, "login": login, "trade_mode": mode, "magic": magic, "build": build, "server": server,
            "product": product, "nonce": nonce}


def check(payload, when=T0):
    with db.connect() as conn:
        return licenses.check(conn, payload, ip="203.0.113.9", now=when, manifest=MANIFEST, secret_key=SECRET)


def test_keys_are_unique_and_well_formed():
    keys = {licenses.generate_key() for _ in range(500)}
    assert len(keys) == 500
    assert all(licenses.KEY_RE.match(key) for key in keys)


def test_first_activation_binds_live_account_and_signature_verifies(paid_license):
    status, body = check(request(paid_license["license_key"]))
    assert status == 200 and body["allowed"] is True and body["code"] == "activated"
    message = f"{body['nonce']}|{paid_license['license_key']}|5550001|{BUILD}|1|activated|{body['ts']}"
    build_secret = hmac.new(SECRET, f"calyx-build:{BUILD}".encode(), hashlib.sha256).hexdigest()
    assert body["sig"] == hmac.new(build_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    assert body["nonce"] == "ab" * 16 and '"' not in body["message"]
    with db.connect() as conn:
        lic = licenses.get(conn, paid_license["id"])
        assert (lic["live_login"], lic["live_server"], lic["activations"]) == ("5550001", "Broker-Live", 1)
        logged = conn.execute("SELECT * FROM license_checks").fetchall()
        assert len(logged) == 1 and logged[0]["allowed"] == 1 and logged[0]["key_hint"].startswith("CLX-")
    status, body = check(request(paid_license["license_key"]))
    assert body["allowed"] is True and body["code"] == "ok"


def test_one_live_and_one_demo_account(paid_license):
    key = paid_license["license_key"]
    assert check(request(key))[1]["allowed"]
    assert check(request(key, login="7770001", mode="demo", server="Broker-Demo"))[1]["code"] == "activated"
    assert check(request(key, login="5550002"))[1]["code"] == "live_limit"
    assert check(request(key, login="7770002", mode="contest", server="Broker-Demo"))[1]["code"] == "demo_limit"
    assert check(request(key, server="Other-Live"))[1]["code"] == "server_mismatch"


def test_accounts_entered_at_checkout_are_enforced(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn)
        created = make_order(conn, [FakeProduct("orb-a", "ORB A", 449)], live_login="9990001")
        orders.mark_paid(conn, created.order_id, paid_by="admin:test", note="test payment")
        key = conn.execute("SELECT license_key FROM licenses").fetchone()[0]
    assert check(request(key, login="5550001"))[1]["code"] == "live_limit"
    assert check(request(key, login="9990001"))[1]["code"] == "activated"  # server recorded on first activation


def test_revoke_unrevoke_reset_and_expiry(paid_license):
    key, lic_id = paid_license["license_key"], paid_license["id"]
    assert check(request(key))[1]["allowed"]
    with db.connect() as conn:
        licenses.revoke(conn, lic_id, "admin:test", "chargeback")
    assert check(request(key))[1]["code"] == "revoked"
    with db.connect() as conn:
        licenses.unrevoke(conn, lic_id, "admin:test")
        licenses.reset_accounts(conn, lic_id, "admin:test", "live")
    assert check(request(key, login="5550009", server="New-Live"))[1]["code"] == "activated"
    with db.connect() as conn:
        licenses.set_expiry(conn, lic_id, "admin:test", T0 + timedelta(days=1))
    assert check(request(key, login="5550009", server="New-Live"), when=T0 + timedelta(days=2))[1]["code"] == "expired"
    with db.connect() as conn:
        licenses.set_expiry(conn, lic_id, "admin:test", None)  # back to perpetual
        with pytest.raises(licenses.LicenseError, match="perpetual"):
            licenses.extend(conn, lic_id, "admin:test", 30, target="expiry")
        licenses.extend(conn, lic_id, "admin:test", 30, target="updates")
        assert licenses.get(conn, lic_id)["expires_at"] is None


def test_product_build_and_magic_binding(paid_license):
    key = paid_license["license_key"]
    assert check(request(key, magic=222))[1]["code"] == "magic_mismatch"  # sibling product's SET on the shared EX5
    assert check(request(key, build="calyx-other-ea-00000002", magic=333))[1]["code"] == "product_mismatch"
    assert check(request(key, build="calyx-unknown-ea-1"))[1]["code"] == "build_unknown"
    assert check(request(key, product="orb-b"))[1]["code"] == "product_mismatch"
    assert check(request("CLX-AAAAA-BBBBB-CCCCC-DDDDD"))[1]["code"] == "unknown_key"


def test_unpaid_order_and_bad_requests(tmp_path, monkeypatch):
    fresh_db(tmp_path, monkeypatch)
    with db.connect() as conn:
        configure(conn)
        created = make_order(conn, [FakeProduct("orb-a", "ORB A", 449)])
        orders.mark_paid(conn, created.order_id, paid_by="admin:test", note="test payment")
        key = conn.execute("SELECT license_key FROM licenses").fetchone()[0]
        conn.execute("UPDATE orders SET status='cancelled'")
    assert check(request(key))[1]["code"] == "order_unpaid"
    assert check(request(key, login="abc"))[0] == 400
    assert check(request(key, nonce="short"))[0] == 400
    assert check(request(key, mode="live"))[0] == 400
    assert check("not a dict")[0] == 400


def test_buyer_can_edit_accounts_until_activated(paid_license):
    lic_id = paid_license["id"]
    with db.connect() as conn:
        licenses.set_accounts(conn, lic_id, "1234567", "7654321", actor="buyer")
    assert check(request(paid_license["license_key"], login="1234567"))[1]["allowed"]
    with db.connect() as conn:
        with pytest.raises(licenses.LicenseError, match="already activated"):
            licenses.set_accounts(conn, lic_id, "2222222", None, actor="buyer")
        licenses.set_accounts(conn, lic_id, "2222222", None, actor="admin:test")  # the owner may
        assert licenses.get(conn, lic_id)["live_server"] is None


def test_every_catalogue_product_has_a_magic_that_identifies_it_within_its_ex5():
    seen: dict[str, set[int]] = {}
    for product in sellable_products():
        item = deliverable_for(product)
        assert item.magic is not None, product.label
        assert item.set_path.is_file() and item.expert_path.is_file() and item.source_path.is_file(), product.label
        magics = seen.setdefault(str(item.expert_path), set())
        assert item.magic not in magics, f"{product.label}: magic shared with a sibling product"
        magics.add(item.magic)


def test_wrapper_gates_callbacks_and_bypasses_the_tester():
    code = "input long InpMagic=5;\nint OnInit(){return 0;}\nvoid OnTick(){}\nvoid OnDeinit(const int r){}\n"
    plan = builds.BuildPlan("calyx-demo-ea-12345678", "Calyx Demo EA", Path("x.ex5"), Path("x.mq5"))
    text, present = builds.wrapper_source(plan, "src_x.mqh", code, "InpMagic", "https://calyx.duckdns.org/api/license/check", "f" * 64)
    assert present["OnTick"] and present["OnDeinit"] and not present["OnTimer"]
    assert text.index('#include "CalyxLicense.mqh"') < text.index("#define OnInit Store_StrategyInit") < text.index('#include "src/src_x.mqh"')
    assert "#undef OnInit" in text and "long CalyxStoreMagic() { return (long)InpMagic; }" in text
    assert "if(CalyxIsTester())\n      return Store_StrategyInit();" in text
    assert "Store_StrategyTimer" not in text.split("#undef OnDeinit")[1]  # no call to a missing callback
    with pytest.raises(RuntimeError, match="magic input"):
        builds.wrapper_source(plan, "src_x.mqh", code, "InpMagicNumber", "https://x/api", "f" * 64)


def test_license_module_rules():
    text = (Path(builds.__file__).parent / "mql" / "CalyxLicense.mqh").read_text(encoding="utf-8")
    assert re.search(r"#define CALYX_RECHECK_SECONDS\s+86400\b", text)
    assert re.search(r"#define CALYX_GRACE_SECONDS\s+259200\b", text)  # 72 h offline grace
    assert "MQLInfoInteger(MQL_TESTER)" in text and "MQLInfoInteger(MQL_OPTIMIZATION)" in text
    assert "ExpertRemove();" in text and "NO LONGER MANAGED" in text
    assert "input string InpCalyxLicenseKey" in text
    assert "GlobalVariableSet(name + \"_t\"" in text and "CalyxStateSignature" in text
    assert "WebRequest(\"POST\", CALYX_LICENSE_URL" in text


def test_build_secret_is_derived_and_not_stored():
    first = builds.build_secret("calyx-x-1", SECRET)
    assert first == builds.build_secret("calyx-x-1", SECRET) != builds.build_secret("calyx-x-2", SECRET)
    manifest = builds.load_manifest()
    if manifest.get("builds"):
        assert first not in Path(builds.builds_root() / "manifest.json").read_text(encoding="utf-8")
