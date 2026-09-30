"""Composition root: builds long-lived singletons once and hands out per-session services."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from crypto_lab.config import Settings
from crypto_lab.domain.bots import DEFAULT_POLICY, ModeTransitionPolicy
from crypto_lab.domain.credentials import DEFAULT_PROVIDERS, ProviderRegistry
from crypto_lab.infrastructure.db.session import create_engine, create_session_factory
from crypto_lab.security.crypto import (
    AesGcmCipher,
    ChainedKeyProvider,
    DevFileKeyProvider,
    KeyringKeyProvider,
    MasterKeyProvider,
    StaticKeyProvider,
)
from crypto_lab.security.passwords import PasswordHasher
from crypto_lab.security.ratelimit import SlidingWindowRateLimiter
from crypto_lab.services.auth import AuthService
from crypto_lab.services.bots import BotService
from crypto_lab.services.vault import CredentialVault


def build_key_provider(settings: Settings) -> ChainedKeyProvider:
    providers: list[MasterKeyProvider] = [
        StaticKeyProvider(settings.master_key),
        KeyringKeyProvider(settings.master_key_keyring_service),
    ]
    if settings.allow_dev_key_file and settings.environment != "production":
        providers.append(DevFileKeyProvider(settings.dev_key_file))
    return ChainedKeyProvider(providers)


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    cipher: AesGcmCipher
    hasher: PasswordHasher = field(default_factory=PasswordHasher)
    providers: ProviderRegistry = field(default_factory=lambda: DEFAULT_PROVIDERS)
    policy: ModeTransitionPolicy = field(default_factory=lambda: DEFAULT_POLICY)
    login_limiter: SlidingWindowRateLimiter = field(init=False)

    def __post_init__(self) -> None:
        self.login_limiter = SlidingWindowRateLimiter(self.settings.login_rate_per_minute, 60.0)

    @classmethod
    def build(cls, settings: Settings, key_provider: ChainedKeyProvider | None = None) -> Container:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        engine = create_engine(settings.resolved_database_url)
        key = (key_provider or build_key_provider(settings)).require()
        return cls(
            settings=settings, engine=engine, session_factory=create_session_factory(engine), cipher=AesGcmCipher(key)
        )

    # Per-session service factories (Factory Method).
    def auth(self, session: AsyncSession) -> AuthService:
        return AuthService(session, self.settings, self.hasher, self.cipher)

    def vault(self, session: AsyncSession) -> CredentialVault:
        return CredentialVault(session, self.cipher, self.providers)

    def bots(self, session: AsyncSession) -> BotService:
        return BotService(session, self.policy, self.settings.live_trading_enabled)

    async def dispose(self) -> None:
        await self.engine.dispose()
