"""Bot run modes and the policy that guards transitions between them.

The policy is a chain of small guard objects (Chain of Responsibility / Specification). Each guard either passes or
raises :class:`ModeTransitionError` with a human-readable reason. LIVE is deliberately hard to reach.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from crypto_lab.domain.errors import ModeTransitionError


class BotMode(StrEnum):
    OFF = "off"
    SHADOW = "shadow"  # compute signals on live data, record only
    PAPER = "paper"  # simulated fills and a paper ledger
    LIVE = "live"  # real orders

    @property
    def is_trading(self) -> bool:
        return self is BotMode.LIVE


ALLOWED_TRANSITIONS: dict[BotMode, frozenset[BotMode]] = {
    BotMode.OFF: frozenset({BotMode.SHADOW, BotMode.PAPER}),
    BotMode.SHADOW: frozenset({BotMode.OFF, BotMode.PAPER}),
    BotMode.PAPER: frozenset({BotMode.OFF, BotMode.SHADOW, BotMode.LIVE}),
    BotMode.LIVE: frozenset({BotMode.OFF, BotMode.PAPER}),
}


@dataclass(frozen=True, slots=True)
class TransitionRequest:
    """Everything a guard may need to judge a mode change."""

    bot_slug: str
    current: BotMode
    target: BotMode
    gate_passed: bool
    live_trading_enabled: bool
    confirmation_text: str = ""
    two_factor_verified: bool = False


class TransitionGuard(Protocol):
    def check(self, request: TransitionRequest) -> None:
        """Raise :class:`ModeTransitionError` if the request must be refused."""


class AllowedEdgeGuard:
    def check(self, request: TransitionRequest) -> None:
        if request.target == request.current:
            raise ModeTransitionError(f"Bot is already in {request.current.value.upper()} mode.")
        if request.target not in ALLOWED_TRANSITIONS[request.current]:
            raise ModeTransitionError(
                f"{request.current.value.upper()} -> {request.target.value.upper()} is not allowed; "
                "go through PAPER first."
            )


class LiveOnlyGuard:
    """Base for guards that only apply when entering LIVE."""

    def check(self, request: TransitionRequest) -> None:
        if request.target is BotMode.LIVE:
            self.check_live(request)

    def check_live(self, request: TransitionRequest) -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class LiveFeatureFlagGuard(LiveOnlyGuard):
    def check_live(self, request: TransitionRequest) -> None:
        if not request.live_trading_enabled:
            raise ModeTransitionError("Live trading is disabled in configuration (CRYPTOLAB_LIVE_TRADING_ENABLED).")


class GatePassedGuard(LiveOnlyGuard):
    def check_live(self, request: TransitionRequest) -> None:
        if not request.gate_passed:
            raise ModeTransitionError("This bot has not passed its paper-trading gate.")


class TypedConfirmationGuard(LiveOnlyGuard):
    def check_live(self, request: TransitionRequest) -> None:
        if request.confirmation_text.strip() != request.bot_slug:
            raise ModeTransitionError(f"Type the bot id '{request.bot_slug}' to confirm LIVE mode.")


class TwoFactorGuard(LiveOnlyGuard):
    def check_live(self, request: TransitionRequest) -> None:
        if not request.two_factor_verified:
            raise ModeTransitionError("A valid two-factor code is required for LIVE mode.")


@dataclass(frozen=True, slots=True)
class ModeTransitionPolicy:
    guards: Sequence[TransitionGuard]

    def check(self, request: TransitionRequest) -> None:
        for guard in self.guards:
            guard.check(request)


DEFAULT_POLICY = ModeTransitionPolicy(
    guards=(AllowedEdgeGuard(), LiveFeatureFlagGuard(), GatePassedGuard(), TypedConfirmationGuard(), TwoFactorGuard())
)


@dataclass(frozen=True, slots=True)
class BotDefinition:
    """A bot that the lab knows about (seeded into the database)."""

    slug: str
    name: str
    model: str
    description: str


DEFAULT_BOTS: tuple[BotDefinition, ...] = (
    BotDefinition(
        "poly-scanner",
        "Polymarket arbitrage scanner",
        "D",
        "Fee-aware YES+NO and multi-outcome scanner on recorded order books.",
    ),
    BotDefinition(
        "poly-wallets",
        "Polymarket wallet tracker",
        "D",
        "Leaderboard ingest, wallet trade history and descriptive stats (read-only).",
    ),
    BotDefinition(
        "poly-copy",
        "Polymarket wallet copy engine",
        "D",
        "Mirrors selected wallets with delay, deviation and size limits.",
    ),
    BotDefinition("cex-arb", "CEX spot arbitrage", "A/B", "Cross-exchange BTC spot arbitrage and lead-lag research."),
    BotDefinition("sol-rotation", "Solana meme rotation", "E", "Rug-filtered momentum rotation using Jupiter quotes."),
)
