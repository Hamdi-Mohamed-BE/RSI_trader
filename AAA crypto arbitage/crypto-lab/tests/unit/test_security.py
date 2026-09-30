from pathlib import Path

import pyotp
import pytest

from crypto_lab.security import totp
from crypto_lab.security.crypto import (
    AesGcmCipher,
    ChainedKeyProvider,
    CryptoError,
    DevFileKeyProvider,
    EncryptedBlob,
    StaticKeyProvider,
    decode_key,
    encode_key,
    generate_key,
)
from crypto_lab.security.passwords import PasswordHasher
from crypto_lab.security.ratelimit import SlidingWindowRateLimiter


class TestAesGcmCipher:
    def test_round_trip_returns_plaintext(self) -> None:
        cipher = AesGcmCipher(generate_key())
        blob = cipher.encrypt(b"secret", b"row-1")
        assert cipher.decrypt(blob, b"row-1") == b"secret"

    def test_ciphertext_moved_to_another_row_fails(self) -> None:
        cipher = AesGcmCipher(generate_key())
        blob = cipher.encrypt(b"secret", b"row-1")
        with pytest.raises(CryptoError):
            cipher.decrypt(blob, b"row-2")

    def test_tampered_ciphertext_fails(self) -> None:
        cipher = AesGcmCipher(generate_key())
        blob = cipher.encrypt(b"secret", b"aad")
        tampered = EncryptedBlob(blob.nonce, bytes([blob.ciphertext[0] ^ 1]) + blob.ciphertext[1:])
        with pytest.raises(CryptoError):
            cipher.decrypt(tampered, b"aad")

    def test_wrong_key_fails(self) -> None:
        blob = AesGcmCipher(generate_key()).encrypt(b"secret", b"aad")
        with pytest.raises(CryptoError):
            AesGcmCipher(generate_key()).decrypt(blob, b"aad")

    def test_rejects_short_key(self) -> None:
        with pytest.raises(CryptoError):
            AesGcmCipher(b"short")

    def test_each_encryption_uses_a_fresh_nonce(self) -> None:
        cipher = AesGcmCipher(generate_key())
        assert cipher.encrypt(b"x", b"a").nonce != cipher.encrypt(b"x", b"a").nonce


class TestKeyProviders:
    def test_encode_decode_round_trip(self) -> None:
        key = generate_key()
        assert decode_key(encode_key(key)) == key

    def test_invalid_base64_is_rejected(self) -> None:
        with pytest.raises(CryptoError):
            decode_key("not base64 !!")

    def test_dev_file_is_created_once_and_reused(self, tmp_path: Path) -> None:
        provider = DevFileKeyProvider(tmp_path / "k" / "dev.key")
        first = provider.load()
        assert first is not None and len(first) == 32
        assert provider.load() == first

    def test_chain_uses_first_available_source(self, tmp_path: Path) -> None:
        env_key = generate_key()
        chain = ChainedKeyProvider(
            [StaticKeyProvider(None), StaticKeyProvider(encode_key(env_key)), DevFileKeyProvider(tmp_path / "dev.key")]
        )
        assert chain.require() == env_key
        assert not (tmp_path / "dev.key").exists()

    def test_chain_without_any_key_raises(self) -> None:
        with pytest.raises(CryptoError):
            ChainedKeyProvider([StaticKeyProvider(None)]).require()


class TestPasswords:
    def test_hash_verifies_only_the_right_password(self) -> None:
        hasher = PasswordHasher()
        h = hasher.hash("a-long-enough-password")
        assert hasher.verify(h, "a-long-enough-password") is True
        assert hasher.verify(h, "wrong-password-123") is False

    def test_short_password_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 12"):
            PasswordHasher().hash("short")

    def test_missing_hash_never_verifies(self) -> None:
        assert PasswordHasher().verify(None, "anything-at-all") is False


class TestTotp:
    def test_current_code_verifies_and_garbage_does_not(self) -> None:
        secret = totp.new_secret()
        assert totp.verify(secret, pyotp.TOTP(secret).now()) is True
        assert totp.verify(secret, "12ab56") is False
        assert totp.verify(secret, "") is False


class TestRateLimiter:
    def test_blocks_after_limit_until_window_passes(self) -> None:
        now = [0.0]
        limiter = SlidingWindowRateLimiter(2, 60, clock=lambda: now[0])
        assert limiter.allow("ip") and limiter.allow("ip")
        assert limiter.allow("ip") is False
        assert limiter.allow("other-ip") is True
        now[0] = 61
        assert limiter.allow("ip") is True
