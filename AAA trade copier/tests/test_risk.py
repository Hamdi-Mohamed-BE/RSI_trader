from decimal import Decimal
from uuid import uuid4

import pytest

from trade_copier.domain.enums import RiskMode
from trade_copier.domain.messages import AccountSnapshot, ContractSpec
from trade_copier.models import RiskProfile
from trade_copier.services.risk import RiskCalculator, RiskRejectedError


def snapshot(*, equity: str = "10000", minimum: str = "0.01") -> AccountSnapshot:
    return AccountSnapshot(
        account_id=uuid4(),
        equity=Decimal(equity),
        free_margin=Decimal(equity),
        contract=ContractSpec(
            symbol="XAUUSD",
            tick_size=Decimal("0.01"),
            tick_value=Decimal("1"),
            volume_min=Decimal(minimum),
            volume_max=Decimal("100"),
            volume_step=Decimal("0.01"),
        ),
    )


def profile() -> RiskProfile:
    return RiskProfile(
        name="test",
        mode=RiskMode.STOP_PERCENT.value,
        risk_percent=Decimal("1"),
        max_risk_per_trade_percent=Decimal("1"),
    )


def test_stop_risk_calculates_follower_volume() -> None:
    decision = RiskCalculator().calculate_volume(
        snapshot=snapshot(),
        profile=profile(),
        master_volume=Decimal("1"),
        master_equity=Decimal("100000"),
        entry_price=Decimal("2400"),
        stop_loss=Decimal("2390"),
    )
    assert decision.volume == Decimal("0.10")
    assert decision.cash_risk == Decimal("100.00")


def test_volume_is_floored_not_rounded_up() -> None:
    decision = RiskCalculator().calculate_volume(
        snapshot=snapshot(equity="12345"),
        profile=profile(),
        master_volume=Decimal("1"),
        master_equity=Decimal("100000"),
        entry_price=Decimal("2400"),
        stop_loss=Decimal("2390"),
    )
    assert decision.volume == Decimal("0.12")
    assert decision.cash_risk == Decimal("120.00")


def test_minimum_volume_that_exceeds_risk_is_rejected() -> None:
    with pytest.raises(RiskRejectedError, match="Minimum broker volume"):
        RiskCalculator().calculate_volume(
            snapshot=snapshot(equity="100", minimum="0.10"),
            profile=profile(),
            master_volume=Decimal("1"),
            master_equity=Decimal("100000"),
            entry_price=Decimal("2400"),
            stop_loss=Decimal("2390"),
        )
