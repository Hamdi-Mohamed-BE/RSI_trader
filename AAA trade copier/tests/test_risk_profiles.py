from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.models import Account, RiskProfile
from trade_copier.services.risk_profiles import (
    DEFAULT_RISK_PROFILE_NAME,
    LEGACY_DEFAULT_RISK_PROFILE_NAME,
    ensure_default_risk_profile,
)


def test_default_profile_is_one_percent_with_daily_caps_disabled(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        follower = Account(
            display_name="Unassigned follower",
            login="800001",
            broker_server="Broker-Demo",
            role="follower",
            state="active",
        )
        master = Account(
            display_name="Unassigned master",
            login="800002",
            broker_server="Broker-Demo",
            role="master_candidate",
            state="active",
        )
        session.add_all([follower, master])
        session.commit()

        profile = ensure_default_risk_profile(session, actor="test")

        assert profile.name == DEFAULT_RISK_PROFILE_NAME
        assert profile.mode == "stop_percent"
        assert profile.risk_percent == Decimal("1")
        assert profile.max_risk_per_trade_percent == Decimal("1")
        assert profile.max_daily_loss_percent == Decimal("0")
        assert profile.max_daily_profit_percent == Decimal("0")
        assert profile.reject_without_stop is False
        assert follower.risk_profile_id == profile.id
        assert master.risk_profile_id is None
        assert (
            session.scalar(select(RiskProfile).where(RiskProfile.name == DEFAULT_RISK_PROFILE_NAME))
            is profile
        )


def test_legacy_exact_copy_assignment_is_migrated_to_hybrid_default(
    client: TestClient,
    session_factory: sessionmaker[Session],
) -> None:
    del client
    with session_factory() as session:
        legacy = RiskProfile(name=LEGACY_DEFAULT_RISK_PROFILE_NAME, mode="stop_percent")
        session.add(legacy)
        session.flush()
        follower = Account(
            display_name="Legacy follower",
            login="810001",
            broker_server="Broker-Demo",
            role="follower",
            state="active",
            risk_profile_id=legacy.id,
        )
        session.add(follower)
        session.commit()

        profile = ensure_default_risk_profile(session, actor="test")

        assert profile.name == DEFAULT_RISK_PROFILE_NAME
        assert profile.mode == "stop_percent"
        assert profile.reject_without_stop is False
        assert follower.risk_profile_id == profile.id
        assert follower.risk_profile_id != legacy.id
