"""Owner-editable store settings (admin panel) with validation and defaults."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from . import config
from .db import iso, utcnow

NETWORKS = ("TRC20", "BEP20")

# Public token contracts (USDT). These are not owner secrets; they identify the token.
USDT_CONTRACTS = {
    "TRC20": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
    "BEP20": "0x55d398326f99059fF775485246999027B3197955",
}
USDT_DECIMALS = {"TRC20": 6, "BEP20": 18}
NETWORK_LABELS = {
    "TRC20": "Tron (TRC20)",
    "BEP20": "BNB Smart Chain (BEP20)",
}


@dataclass(frozen=True)
class SettingSpec:
    key: str
    label: str
    kind: str  # str | int | url | trc20 | bep20 | secret
    default: Any
    minimum: int | None = None
    maximum: int | None = None
    help: str = ""
    internal: bool = False


SPECS: tuple[SettingSpec, ...] = (
    SettingSpec("trc20_address", "TRC20 deposit address (Binance, USDT on Tron)", "trc20", "",
                help="Copy it from Binance → Deposit → USDT → network TRX Tron (TRC20). Leave empty to disable TRC20."),
    SettingSpec("bep20_address", "BEP20 deposit address (Binance, USDT on BNB Smart Chain)", "bep20", "",
                help="Copy it from Binance → Deposit → USDT → network BNB Smart Chain (BEP20). Leave empty to disable BEP20."),
    SettingSpec("trc20_confirmations", "TRC20 confirmations required", "int", 20, 1, 500),
    SettingSpec("bep20_confirmations", "BEP20 confirmations required", "int", 15, 1, 500),
    SettingSpec("order_expiry_minutes", "Order expiry (minutes)", "int", 60, 10, 1440),
    SettingSpec("late_payment_minutes", "Late-payment acceptance window after expiry (minutes)", "int", 30, 0, 1440,
                help="A transfer that arrives this long after expiry still confirms the order automatically."),
    SettingSpec("activation_url", "License activation URL (compiled into store builds)", "url",
                config.DEFAULT_ACTIVATION_URL,
                help="Changing this requires rebuilding the store EX5 files; buyers must allow its origin in MT5."),
    SettingSpec("trongrid_url", "TronGrid API base URL", "url", "https://api.trongrid.io"),
    SettingSpec("trongrid_api_key", "TronGrid API key (optional)", "secret", "",
                help="Optional TRON-PRO-API-KEY for higher public rate limits."),
    SettingSpec("bsc_rpc_url", "BSC JSON-RPC URL", "url", "https://bsc-dataseed.bnbchain.org",
                help="Must support eth_getLogs. Alternatives: https://bsc-rpc.publicnode.com"),
    SettingSpec("bsc_log_chunk", "BSC eth_getLogs block range per request", "int", 1000, 10, 50000),
    SettingSpec("bsc_max_lookback", "BSC maximum blocks scanned back on start", "int", 20000, 100, 500000),
    SettingSpec("watcher_interval_seconds", "Payment watcher interval (seconds)", "int", 30, 10, 3600),
    SettingSpec("bsc_cursor", "Last scanned BSC block", "int", 0, internal=True),
)
SPEC_BY_KEY = {spec.key: spec for spec in SPECS}

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58decode(value: str) -> bytes:
    number = 0
    for char in value:
        index = _B58.find(char)
        if index < 0:
            raise ValueError("invalid base58 character")
        number = number * 58 + index
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    pad = len(value) - len(value.lstrip("1"))
    return b"\x00" * pad + raw


def valid_trc20_address(value: str) -> bool:
    if not re.fullmatch(r"T[1-9A-HJ-NP-Za-km-z]{33}", value or ""):
        return False
    try:
        raw = _b58decode(value)
    except ValueError:
        return False
    if len(raw) != 25 or raw[0] != 0x41:
        return False
    checksum = hashlib.sha256(hashlib.sha256(raw[:21]).digest()).digest()[:4]
    return checksum == raw[21:]


def valid_bep20_address(value: str) -> bool:
    return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", value or "")) and int(value, 16) != 0


def validate(key: str, raw: str) -> Any:
    spec = SPEC_BY_KEY[key]
    value = (raw or "").strip()
    if spec.kind == "int":
        if not re.fullmatch(r"\d{1,9}", value):
            raise ValueError(f"{spec.label}: enter a whole number.")
        number = int(value)
        if spec.minimum is not None and number < spec.minimum:
            raise ValueError(f"{spec.label}: minimum is {spec.minimum}.")
        if spec.maximum is not None and number > spec.maximum:
            raise ValueError(f"{spec.label}: maximum is {spec.maximum}.")
        return number
    if spec.kind == "url":
        parsed = urlparse(value)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc or any(c in value for c in " \"'<>"):
            raise ValueError(f"{spec.label}: enter a full http(s) URL.")
        return value.rstrip("/") if key != "activation_url" else value
    if spec.kind == "trc20":
        if value and not valid_trc20_address(value):
            raise ValueError("TRC20 address is not a valid Tron address (checksum failed).")
        return value
    if spec.kind == "bep20":
        if value and not valid_bep20_address(value):
            raise ValueError("BEP20 address must be 0x followed by 40 hexadecimal characters.")
        return value
    if spec.kind == "secret":
        if value and not re.fullmatch(r"[A-Za-z0-9-]{8,80}", value):
            raise ValueError(f"{spec.label}: unexpected characters.")
        return value
    if len(value) > 500:
        raise ValueError(f"{spec.label}: too long.")
    return value


def get_all(conn: sqlite3.Connection) -> dict[str, Any]:
    stored = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM settings")}
    values: dict[str, Any] = {}
    for spec in SPECS:
        raw = stored.get(spec.key)
        if raw is None:
            values[spec.key] = spec.default
        elif spec.kind == "int":
            values[spec.key] = int(raw)
        else:
            values[spec.key] = raw
    return values


def get(conn: sqlite3.Connection, key: str) -> Any:
    return get_all(conn)[key]


def set_value(conn: sqlite3.Connection, key: str, value: Any) -> None:
    if key not in SPEC_BY_KEY:
        raise KeyError(key)
    conn.execute(
        "INSERT INTO settings(key, value, updated_at) VALUES (?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, str(value), iso(utcnow())),
    )


def deposit_address(values: dict[str, Any], network: str) -> str:
    return str(values.get(f"{network.lower()}_address") or "")


def enabled_networks(values: dict[str, Any]) -> list[str]:
    return [network for network in NETWORKS if deposit_address(values, network)]


def activation_origin(values: dict[str, Any]) -> str:
    parsed = urlparse(str(values.get("activation_url") or config.DEFAULT_ACTIVATION_URL))
    return f"{parsed.scheme}://{parsed.netloc}"
