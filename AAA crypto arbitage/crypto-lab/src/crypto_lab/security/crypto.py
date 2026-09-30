"""Authenticated encryption for stored credentials.

* :class:`AesGcmCipher` encrypts with AES-256-GCM. Associated data binds each ciphertext to its record, so a ciphertext
  copied onto another row fails to decrypt.
* The 32-byte master key is resolved by a chain of :class:`MasterKeyProvider` strategies
  (environment -> OS keyring -> development key file).
"""

from __future__ import annotations

import base64
import binascii
import logging
import os
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import keyring
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from keyring.errors import KeyringError

logger = logging.getLogger(__name__)

KEY_BYTES = 32
NONCE_BYTES = 12


class CryptoError(Exception):
    """Decryption failed or no master key could be resolved. Message never contains key material."""


@dataclass(frozen=True, slots=True)
class EncryptedBlob:
    nonce: bytes
    ciphertext: bytes


class AesGcmCipher:
    def __init__(self, key: bytes) -> None:
        if len(key) != KEY_BYTES:
            raise CryptoError("Master key must be exactly 32 bytes.")
        self._aead = AESGCM(key)

    def encrypt(self, plaintext: bytes, associated_data: bytes) -> EncryptedBlob:
        nonce = secrets.token_bytes(NONCE_BYTES)
        return EncryptedBlob(nonce=nonce, ciphertext=self._aead.encrypt(nonce, plaintext, associated_data))

    def decrypt(self, blob: EncryptedBlob, associated_data: bytes) -> bytes:
        try:
            return self._aead.decrypt(blob.nonce, blob.ciphertext, associated_data)
        except InvalidTag as exc:
            raise CryptoError("Credential could not be decrypted (wrong key or tampered record).") from exc


def encode_key(key: bytes) -> str:
    return base64.urlsafe_b64encode(key).decode("ascii")


def decode_key(value: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.strip().encode("ascii"))
    except (binascii.Error, ValueError) as exc:
        raise CryptoError("Master key is not valid base64.") from exc
    if len(key) != KEY_BYTES:
        raise CryptoError("Master key must decode to 32 bytes.")
    return key


def generate_key() -> bytes:
    return secrets.token_bytes(KEY_BYTES)


class MasterKeyProvider(Protocol):
    name: str

    def load(self) -> bytes | None:
        """Return the key, or ``None`` if this source has no key."""


@dataclass(slots=True)
class StaticKeyProvider:
    """Key supplied directly (environment variable or tests)."""

    value: str | None
    name: str = "environment"

    def load(self) -> bytes | None:
        return decode_key(self.value) if self.value else None


@dataclass(slots=True)
class KeyringKeyProvider:
    """Key stored in the OS credential store (Windows Credential Manager, macOS Keychain, Secret Service)."""

    service: str
    username: str = "master-key"
    name: str = "os-keyring"

    def load(self) -> bytes | None:
        try:
            value = keyring.get_password(self.service, self.username)
        except KeyringError:
            logger.warning("OS keyring unavailable; skipping.")
            return None
        return decode_key(value) if value else None


@dataclass(slots=True)
class DevFileKeyProvider:
    """Development fallback: a git-ignored key file created on first use. Never use in production."""

    path: Path
    create_if_missing: bool = True
    name: str = "dev-key-file"

    def load(self) -> bytes | None:
        if self.path.exists():
            return decode_key(self.path.read_text(encoding="ascii"))
        if not self.create_if_missing:
            return None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        key = generate_key()
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as handle:
            handle.write(encode_key(key))
        logger.warning(
            "Created development master key file at %s (git-ignored). Use env/keyring in production.", self.path
        )
        return key


@dataclass(slots=True)
class ChainedKeyProvider:
    providers: Sequence[MasterKeyProvider]
    name: str = "chain"

    def load(self) -> bytes | None:
        for provider in self.providers:
            key = provider.load()
            if key is not None:
                logger.info("Vault master key loaded from %s.", provider.name)
                return key
        return None

    def require(self) -> bytes:
        key = self.load()
        if key is None:
            raise CryptoError("No vault master key found. Set CRYPTOLAB_MASTER_KEY or store one in the OS keyring.")
        return key
