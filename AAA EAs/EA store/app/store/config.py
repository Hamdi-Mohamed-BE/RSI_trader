"""Store configuration: paths, environment and local secrets.

Secrets are never hard-coded. They come from environment variables or a local
``.env`` file in the EA store root (gitignored). When neither provides them, a
random value is generated once and kept in ``data/store-secrets.json``
(gitignored) so a development server works out of the box. Production should
set the variables explicitly and keep the same values across restarts:

* ``CALYX_STORE_SECRET``   – signs session/CSRF cookies and download links.
* ``CALYX_LICENSE_SECRET`` – derives the per-build secret compiled into store
  builds and signs activation responses. Changing it requires rebuilding the
  store EX5 files (``tools/build_store_eas.py``).
"""

from __future__ import annotations

import json
import os
import secrets
from functools import lru_cache
from pathlib import Path
from threading import Lock

STORE_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = STORE_ROOT / "data"
BUILDS_ROOT = DATA_ROOT / "store-builds"
INSTALLER_TEMPLATE_ROOT = Path(__file__).resolve().parent / "installer"
MQL_TEMPLATE_ROOT = Path(__file__).resolve().parent / "mql"

DEFAULT_ACTIVATION_URL = "https://calyx.duckdns.org/api/license/check"
DEFAULT_SITE_ORIGIN = "https://calyx.duckdns.org"

_env_lock = Lock()
_env_loaded = False


def _load_dotenv() -> None:
    """Minimal .env reader (KEY=VALUE lines); existing environment wins."""
    global _env_loaded
    with _env_lock:
        if _env_loaded:
            return
        _env_loaded = True
        path = STORE_ROOT / ".env"
        if not path.is_file():
            return
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def env(name: str, default: str | None = None) -> str | None:
    _load_dotenv()
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def db_path() -> Path:
    return Path(env("CALYX_STORE_DB", str(DATA_ROOT / "store.sqlite3")))


def secrets_path() -> Path:
    return Path(env("CALYX_STORE_SECRETS_FILE", str(DATA_ROOT / "store-secrets.json")))


_secret_lock = Lock()


def _local_secret(name: str) -> str:
    with _secret_lock:
        path = secrets_path()
        data: dict[str, str] = {}
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
        if not data.get(name):
            data[name] = secrets.token_hex(32)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(tmp, path)
        return data[name]


@lru_cache(maxsize=None)
def secret(name: str) -> bytes:
    """Return a secret from the environment, else from the local secrets file."""
    value = env(name) or _local_secret(name)
    if len(value) < 32:
        raise RuntimeError(f"{name} must be at least 32 characters long.")
    return value.encode("utf-8")


def store_secret() -> bytes:
    return secret("CALYX_STORE_SECRET")


def license_secret() -> bytes:
    return secret("CALYX_LICENSE_SECRET")


def cookie_secure_mode() -> str:
    """'1' = always Secure, '0' = never, 'auto' = Secure when the request is HTTPS."""
    return (env("CALYX_COOKIE_SECURE", "auto") or "auto").lower()


def watcher_enabled() -> bool:
    return (env("CALYX_STORE_WATCHER", "1") or "1") not in {"0", "false", "no", "off"}


def trusted_proxies() -> set[str]:
    raw = env("CALYX_TRUSTED_PROXIES", "127.0.0.1,::1") or ""
    return {item.strip() for item in raw.split(",") if item.strip()}
