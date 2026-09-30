"""Credential provider catalogue (Registry pattern).

Each external service the lab talks to is described once by a :class:`ProviderSpec`. The admin UI builds its forms
from these specs, and the vault uses them to decide which fields are secret. Adding a venue means registering a spec,
not editing templates or services.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum

from crypto_lab.domain.errors import NotFoundError, ValidationError


class CredentialEnvironment(StrEnum):
    """Where a credential is valid. LIVE credentials can move real money."""

    DATA = "data"  # read-only market/data access
    TESTNET = "testnet"
    DEMO = "demo"
    LIVE = "live"


class ProviderCategory(StrEnum):
    EXCHANGE = "exchange"
    PREDICTION_MARKET = "prediction_market"
    ONCHAIN_DATA = "onchain_data"
    NOTIFICATION = "notification"
    AI = "ai"


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One input of a credential form."""

    name: str
    label: str
    secret: bool = True
    multiline: bool = False
    required: bool = True


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Static description of a credential type."""

    slug: str
    name: str
    category: ProviderCategory
    fields: tuple[FieldSpec, ...]
    environments: tuple[CredentialEnvironment, ...]
    used_by: tuple[str, ...]
    docs_url: str
    notes: str = ""

    @property
    def secret_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(f for f in self.fields if f.secret)

    @property
    def public_fields(self) -> tuple[FieldSpec, ...]:
        return tuple(f for f in self.fields if not f.secret)

    def validate(self, values: dict[str, str], environment: CredentialEnvironment) -> dict[str, str]:
        """Return the cleaned field values or raise :class:`ValidationError`."""
        if environment not in self.environments:
            raise ValidationError(f"{self.name} does not support the '{environment}' environment.")
        cleaned: dict[str, str] = {}
        for spec in self.fields:
            value = values.get(spec.name, "").strip()
            if spec.required and not value:
                raise ValidationError(f"'{spec.label}' is required.")
            if value:
                cleaned[spec.name] = value
        return cleaned


@dataclass(slots=True)
class ProviderRegistry:
    """Lookup of provider specs by slug."""

    _providers: dict[str, ProviderSpec] = field(default_factory=dict)

    def register(self, spec: ProviderSpec) -> None:
        if spec.slug in self._providers:
            raise ValueError(f"Provider '{spec.slug}' is already registered.")
        self._providers[spec.slug] = spec

    def get(self, slug: str) -> ProviderSpec:
        try:
            return self._providers[slug]
        except KeyError as exc:
            raise NotFoundError(f"Unknown provider '{slug}'.") from exc

    def __iter__(self) -> Iterator[ProviderSpec]:
        return iter(sorted(self._providers.values(), key=lambda p: (p.category, p.name)))

    def __len__(self) -> int:
        return len(self._providers)


_E = CredentialEnvironment
_KEY = FieldSpec("api_key", "API key")
_SECRET = FieldSpec("api_secret", "API secret")


def _build_default_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    specs = (
        ProviderSpec(
            "binance",
            "Binance Spot",
            ProviderCategory.EXCHANGE,
            (_KEY, _SECRET),
            (_E.TESTNET, _E.LIVE),
            ("A", "B"),
            "https://developers.binance.com/docs/binance-spot-api-docs",
            "Create the key with withdrawals disabled and an IP whitelist.",
        ),
        ProviderSpec(
            "bybit",
            "Bybit Spot",
            ProviderCategory.EXCHANGE,
            (_KEY, _SECRET),
            (_E.TESTNET, _E.DEMO, _E.LIVE),
            ("A", "B"),
            "https://bybit-exchange.github.io/docs/v5/intro",
        ),
        ProviderSpec(
            "okx",
            "OKX Spot",
            ProviderCategory.EXCHANGE,
            (_KEY, _SECRET, FieldSpec("passphrase", "Passphrase")),
            (_E.DEMO, _E.LIVE),
            ("A", "B"),
            "https://www.okx.com/docs-v5/en/",
        ),
        ProviderSpec(
            "kraken",
            "Kraken Spot",
            ProviderCategory.EXCHANGE,
            (_KEY, FieldSpec("api_secret", "Private key")),
            (_E.LIVE,),
            ("A", "B"),
            "https://docs.kraken.com/api/",
        ),
        ProviderSpec(
            "polymarket",
            "Polymarket CLOB",
            ProviderCategory.PREDICTION_MARKET,
            (
                _KEY,
                _SECRET,
                FieldSpec("passphrase", "Passphrase"),
                FieldSpec("funder_address", "Funder / proxy wallet address", secret=False),
            ),
            (_E.LIVE,),
            ("D",),
            "https://docs.polymarket.com/",
            "Public market data needs no key. Trading creds are derived from a dedicated wallet.",
        ),
        ProviderSpec(
            "kalshi",
            "Kalshi",
            ProviderCategory.PREDICTION_MARKET,
            (
                FieldSpec("key_id", "API key ID", secret=False),
                FieldSpec("private_key_pem", "RSA private key (PEM)", multiline=True),
            ),
            (_E.DEMO, _E.LIVE),
            ("D",),
            "https://docs.kalshi.com/",
        ),
        ProviderSpec(
            "etherscan",
            "Etherscan API V2 (Polygon)",
            ProviderCategory.ONCHAIN_DATA,
            (_KEY,),
            (_E.DATA,),
            ("D",),
            "https://docs.etherscan.io/",
        ),
        ProviderSpec(
            "polygon_rpc",
            "Polygon RPC",
            ProviderCategory.ONCHAIN_DATA,
            (FieldSpec("rpc_url", "RPC URL (contains the key)"),),
            (_E.DATA,),
            ("D",),
            "https://docs.polygon.technology/",
        ),
        ProviderSpec(
            "helius",
            "Helius (Solana RPC)",
            ProviderCategory.ONCHAIN_DATA,
            (_KEY,),
            (_E.DATA,),
            ("E",),
            "https://www.helius.dev/docs",
        ),
        ProviderSpec(
            "jupiter",
            "Jupiter API",
            ProviderCategory.ONCHAIN_DATA,
            (_KEY,),
            (_E.DATA,),
            ("E",),
            "https://developers.jup.ag/",
        ),
        ProviderSpec(
            "birdeye",
            "Birdeye Data",
            ProviderCategory.ONCHAIN_DATA,
            (_KEY,),
            (_E.DATA,),
            ("E",),
            "https://docs.birdeye.so/",
        ),
        ProviderSpec(
            "telegram",
            "Telegram bot",
            ProviderCategory.NOTIFICATION,
            (FieldSpec("bot_token", "Bot token"), FieldSpec("chat_id", "Chat ID", secret=False)),
            (_E.LIVE,),
            ("A", "B", "D", "E"),
            "https://core.telegram.org/bots/api",
        ),
        ProviderSpec(
            "anthropic",
            "Anthropic (Claude)",
            ProviderCategory.AI,
            (_KEY,),
            (_E.DATA,),
            ("D",),
            "https://docs.anthropic.com/",
            "Optional research summaries only. Never used in the trade path.",
        ),
    )
    for spec in specs:
        registry.register(spec)
    return registry


DEFAULT_PROVIDERS = _build_default_registry()
