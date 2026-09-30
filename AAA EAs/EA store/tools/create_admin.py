"""Create a Calyx store admin user (password is prompted, never passed on the command line).

    uv run python tools/create_admin.py                # asks for username and password
    uv run python tools/create_admin.py --username owner
    uv run python tools/create_admin.py --username owner --reset   # set a new password

The password is stored only as an scrypt hash in data/store.sqlite3 (or
CALYX_STORE_DB). Enable two-factor authentication afterwards in /admin/security.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EA_STORE_DISABLE_MT5", "1")

from app.store import admin_auth, config, db, security  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or reset a Calyx store admin user.")
    parser.add_argument("--username", default="")
    parser.add_argument("--reset", action="store_true", help="set a new password for an existing user")
    args = parser.parse_args()
    username = args.username or input("Admin username: ").strip()
    if not admin_auth.USERNAME_RE.match(username):
        print("Username: 3-40 letters, digits, dot, dash or underscore.")
        return 2
    password = getpass.getpass(f"Password for {username} (min {security.MIN_PASSWORD_LENGTH} characters): ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match.")
        return 2
    if len(password) < security.MIN_PASSWORD_LENGTH:
        print(f"Password must be at least {security.MIN_PASSWORD_LENGTH} characters.")
        return 2
    with db.connect() as conn:
        existing = conn.execute("SELECT id FROM admins WHERE username = ?", (username,)).fetchone()
        try:
            if existing and args.reset:
                admin_auth.set_password(conn, int(existing["id"]), password, "cli")
                print(f"Password updated for {username}; existing sessions were signed out.")
            elif existing:
                print(f"{username} already exists. Use --reset to set a new password.")
                return 1
            else:
                admin_auth.create_admin(conn, username, password)
                print(f"Admin user {username} created in {config.db_path()}.")
        except (ValueError, admin_auth.AuthError) as exc:
            print(exc)
            return 2
    print("Next: sign in at /admin/login, enable 2FA in Security and enter the deposit addresses in Settings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
