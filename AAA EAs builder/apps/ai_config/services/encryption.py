import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class SecretDecryptionError(ValueError):
    pass


def _resolve_key() -> bytes:
    configured_key = settings.MODEL_CONFIG_ENCRYPTION_KEY.strip()
    if configured_key:
        try:
            key = configured_key.encode("ascii")
            Fernet(key)
            return key
        except (ValueError, UnicodeEncodeError) as exc:
            raise ImproperlyConfigured(
                "MODEL_CONFIG_ENCRYPTION_KEY must be a valid Fernet key."
            ) from exc

    if settings.DEBUG:
        logger.warning("Using a development-only derived model credential encryption key.")
        digest = hashlib.sha256(f"{settings.SECRET_KEY}:model-config".encode()).digest()
        return base64.urlsafe_b64encode(digest)

    raise ImproperlyConfigured("MODEL_CONFIG_ENCRYPTION_KEY is required outside development.")


def encrypt_secret(value: str) -> str:
    if not value:
        raise ValueError("Cannot encrypt an empty secret.")
    return Fernet(_resolve_key()).encrypt(value.encode()).decode("ascii")


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    try:
        return Fernet(_resolve_key()).decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise SecretDecryptionError("The stored credential could not be decrypted.") from exc


def secret_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]
