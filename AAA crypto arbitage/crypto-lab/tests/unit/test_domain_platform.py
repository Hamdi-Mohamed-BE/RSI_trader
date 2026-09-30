import pytest

from crypto_lab.domain.bots import DEFAULT_POLICY, BotMode, TransitionRequest
from crypto_lab.domain.credentials import DEFAULT_PROVIDERS, CredentialEnvironment
from crypto_lab.domain.errors import ModeTransitionError, NotFoundError, ValidationError


def _request(current: BotMode, target: BotMode, **overrides: object) -> TransitionRequest:
    base: dict[str, object] = {
        "bot_slug": "poly-scanner",
        "current": current,
        "target": target,
        "gate_passed": True,
        "live_trading_enabled": True,
        "confirmation_text": "poly-scanner",
        "two_factor_verified": True,
    }
    base.update(overrides)
    return TransitionRequest(**base)  # type: ignore[arg-type]


class TestModeTransitionPolicy:
    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (BotMode.OFF, BotMode.SHADOW),
            (BotMode.OFF, BotMode.PAPER),
            (BotMode.SHADOW, BotMode.PAPER),
            (BotMode.PAPER, BotMode.OFF),
            (BotMode.LIVE, BotMode.OFF),
            (BotMode.LIVE, BotMode.PAPER),
        ],
    )
    def test_allowed_non_live_edges_pass(self, current: BotMode, target: BotMode) -> None:
        DEFAULT_POLICY.check(_request(current, target))

    def test_live_must_go_through_paper(self) -> None:
        with pytest.raises(ModeTransitionError, match="through PAPER"):
            DEFAULT_POLICY.check(_request(BotMode.OFF, BotMode.LIVE))

    def test_same_mode_is_refused(self) -> None:
        with pytest.raises(ModeTransitionError, match="already"):
            DEFAULT_POLICY.check(_request(BotMode.PAPER, BotMode.PAPER))

    @pytest.mark.parametrize(
        ("override", "message"),
        [
            ({"live_trading_enabled": False}, "disabled in configuration"),
            ({"gate_passed": False}, "paper-trading gate"),
            ({"confirmation_text": "wrong"}, "Type the bot id"),
            ({"two_factor_verified": False}, "two-factor"),
        ],
    )
    def test_each_live_guard_blocks_on_its_own(self, override: dict[str, object], message: str) -> None:
        with pytest.raises(ModeTransitionError, match=message):
            DEFAULT_POLICY.check(_request(BotMode.PAPER, BotMode.LIVE, **override))

    def test_live_allowed_only_when_every_guard_passes(self) -> None:
        DEFAULT_POLICY.check(_request(BotMode.PAPER, BotMode.LIVE))


class TestProviderRegistry:
    def test_unknown_provider_raises_not_found(self) -> None:
        with pytest.raises(NotFoundError):
            DEFAULT_PROVIDERS.get("nope")

    def test_validate_requires_fields_and_supported_environment(self) -> None:
        spec = DEFAULT_PROVIDERS.get("binance")
        assert spec.validate({"api_key": " k ", "api_secret": "s"}, CredentialEnvironment.TESTNET) == {
            "api_key": "k",
            "api_secret": "s",
        }
        with pytest.raises(ValidationError, match="required"):
            spec.validate({"api_key": "k"}, CredentialEnvironment.LIVE)
        with pytest.raises(ValidationError, match="does not support"):
            spec.validate({"api_key": "k", "api_secret": "s"}, CredentialEnvironment.DEMO)

    def test_kalshi_key_id_is_public_and_pem_is_secret(self) -> None:
        spec = DEFAULT_PROVIDERS.get("kalshi")
        assert [f.name for f in spec.public_fields] == ["key_id"]
        assert [f.name for f in spec.secret_fields] == ["private_key_pem"]
