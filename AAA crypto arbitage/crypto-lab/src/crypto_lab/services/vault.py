"""Credential vault: encrypt-on-write, masked reads, decrypt only for workers.

The web layer only ever receives :class:`CredentialView` objects, which cannot contain secret values.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.domain.credentials import CredentialEnvironment, ProviderRegistry, ProviderSpec
from crypto_lab.domain.errors import NotFoundError, ValidationError
from crypto_lab.infrastructure.db.base import utcnow
from crypto_lab.infrastructure.db.models import ApiCredential
from crypto_lab.infrastructure.db.repositories import CredentialRepository
from crypto_lab.security.crypto import AesGcmCipher, EncryptedBlob
from crypto_lab.services.audit import Actor, AuditService

HINT_CHARS = 4


@dataclass(frozen=True, slots=True)
class CredentialView:
    """Safe, display-only representation of a stored credential."""

    id: str
    provider: ProviderSpec
    label: str
    environment: CredentialEnvironment
    public_fields: dict[str, str]
    hint: str
    enabled: bool
    created_at: datetime
    rotated_at: datetime | None
    last_test_at: datetime | None
    last_test_ok: bool | None
    last_test_message: str


def _hint(secret_values: dict[str, str], spec: ProviderSpec) -> str:
    first = next((secret_values[f.name] for f in spec.secret_fields if f.name in secret_values), "")
    return f"…{first[-HINT_CHARS:]}" if len(first) > HINT_CHARS * 2 else "…"


class CredentialVault:
    def __init__(self, session: AsyncSession, cipher: AesGcmCipher, providers: ProviderRegistry) -> None:
        self._repo = CredentialRepository(session)
        self._audit = AuditService(session)
        self._cipher = cipher
        self._providers = providers

    @staticmethod
    def _aad(credential_id: str, provider: str) -> bytes:
        return f"credential:{credential_id}:{provider}".encode()

    def _view(self, row: ApiCredential) -> CredentialView:
        return CredentialView(
            id=row.id,
            provider=self._providers.get(row.provider),
            label=row.label,
            environment=CredentialEnvironment(row.environment),
            public_fields=dict(row.public_fields),
            hint=row.hint,
            enabled=row.enabled,
            created_at=row.created_at,
            rotated_at=row.rotated_at,
            last_test_at=row.last_test_at,
            last_test_ok=row.last_test_ok,
            last_test_message=row.last_test_message,
        )

    def _seal(self, row: ApiCredential, spec: ProviderSpec, cleaned: dict[str, str]) -> None:
        secrets_only = {f.name: cleaned[f.name] for f in spec.secret_fields if f.name in cleaned}
        blob = self._cipher.encrypt(json.dumps(secrets_only).encode("utf-8"), self._aad(row.id, row.provider))
        row.secret_nonce, row.secret_ciphertext = blob.nonce, blob.ciphertext
        row.public_fields = {f.name: cleaned[f.name] for f in spec.public_fields if f.name in cleaned}
        row.hint = _hint(secrets_only, spec)

    async def list(self) -> Sequence[CredentialView]:
        return [self._view(row) for row in await self._repo.list()]

    async def get(self, credential_id: str) -> CredentialView:
        return self._view(await self._require(credential_id))

    async def _require(self, credential_id: str) -> ApiCredential:
        row = await self._repo.get(credential_id)
        if row is None:
            raise NotFoundError("Credential not found.")
        return row

    async def create(
        self, provider_slug: str, label: str, environment: str, values: dict[str, str], actor: Actor
    ) -> CredentialView:
        spec = self._providers.get(provider_slug)
        env = self._parse_env(environment)
        label = self._clean_label(label, spec)
        cleaned = spec.validate(values, env)
        # The id is assigned up front because it is bound into the ciphertext's associated data.
        row = ApiCredential(
            id=str(uuid.uuid4()),
            provider=spec.slug,
            label=label,
            environment=env.value,
            secret_nonce=b"",
            secret_ciphertext=b"",
        )
        self._seal(row, spec, cleaned)
        await self._repo.add(row)
        await self._audit.record(
            actor, "credential.created", row.id, provider=spec.slug, environment=env.value, label=label
        )
        return self._view(row)

    async def rotate(self, credential_id: str, values: dict[str, str], actor: Actor) -> CredentialView:
        row = await self._require(credential_id)
        spec = self._providers.get(row.provider)
        cleaned = spec.validate(values, CredentialEnvironment(row.environment))
        self._seal(row, spec, cleaned)
        row.rotated_at = utcnow()
        row.last_test_at = row.last_test_ok = None
        row.last_test_message = ""
        await self._audit.record(actor, "credential.rotated", row.id, provider=row.provider)
        return self._view(row)

    async def set_enabled(self, credential_id: str, enabled: bool, actor: Actor) -> None:
        row = await self._require(credential_id)
        row.enabled = enabled
        await self._audit.record(
            actor, "credential.enabled" if enabled else "credential.disabled", row.id, provider=row.provider
        )

    async def delete(self, credential_id: str, actor: Actor) -> None:
        row = await self._require(credential_id)
        await self._repo.delete(row)
        await self._audit.record(actor, "credential.deleted", credential_id, provider=row.provider, label=row.label)

    async def reveal_for_worker(self, credential_id: str) -> dict[str, str]:
        """Decrypt all fields for a worker process. Never call this from a web route."""
        row = await self._require(credential_id)
        blob = EncryptedBlob(row.secret_nonce, row.secret_ciphertext)
        secrets_only: dict[str, str] = json.loads(self._cipher.decrypt(blob, self._aad(row.id, row.provider)))
        return {**row.public_fields, **secrets_only}

    @staticmethod
    def _parse_env(environment: str) -> CredentialEnvironment:
        try:
            return CredentialEnvironment(environment)
        except ValueError as exc:
            raise ValidationError("Unknown environment.") from exc

    @staticmethod
    def _clean_label(label: str, spec: ProviderSpec) -> str:
        label = label.strip() or spec.name
        if len(label) > 80:
            raise ValidationError("Label must be at most 80 characters.")
        return label
