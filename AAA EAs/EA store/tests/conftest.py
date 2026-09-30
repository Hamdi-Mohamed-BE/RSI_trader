"""Test isolation for the store: temporary database/secrets, no payment watcher, no MT5."""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="calyx-store-tests-")
# Forced (not setdefault): tests must never touch the real store database or secrets.
os.environ["CALYX_STORE_DB"] = os.path.join(_TMP, "store.sqlite3")
os.environ["CALYX_STORE_SECRETS_FILE"] = os.path.join(_TMP, "store-secrets.json")
os.environ["CALYX_STORE_WATCHER"] = "0"
os.environ["CALYX_COOKIE_SECURE"] = "0"
os.environ.setdefault("EA_STORE_DISABLE_MT5", "1")
