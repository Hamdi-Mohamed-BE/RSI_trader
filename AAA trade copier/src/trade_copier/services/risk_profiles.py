from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.enums import AccountRole, RiskMode
from ..models import Account, RiskProfile
from .audit import record_audit

DEFAULT_RISK_PROFILE_NAME = "Automatic 1% per trade"


def ensure_default_risk_profile(
    session: Session,
    *,
    actor: str = "system",
    assign_missing: bool = True,
) -> RiskProfile:
    """Create the system default and assign it only where no policy was chosen."""
    profile = session.scalar(
        select(RiskProfile).where(RiskProfile.name == DEFAULT_RISK_PROFILE_NAME)
    )
    created = profile is None
    if profile is None:
        profile = RiskProfile(name=DEFAULT_RISK_PROFILE_NAME)
        session.add(profile)
        session.flush()

    profile.mode = RiskMode.STOP_PERCENT.value
    profile.risk_percent = Decimal("1")
    profile.fixed_cash_risk = None
    profile.fixed_lots = None
    profile.max_risk_per_trade_percent = Decimal("1")
    profile.max_total_open_risk_percent = Decimal("100")
    profile.max_daily_loss_percent = Decimal("0")
    profile.max_daily_profit_percent = Decimal("0")
    profile.max_spread_points = 10_000
    profile.max_slippage_points = 30
    profile.max_open_positions = 1_000
    profile.reject_without_stop = True
    profile.enabled = True

    if created:
        record_audit(
            session,
            actor=actor,
            action="risk_profile.default_created",
            target_type="risk_profile",
            target_id=profile.id,
            message="Created the automatic 1% risk profile with daily caps disabled.",
            details={
                "risk_percent": "1",
                "daily_loss_cap": "disabled",
                "daily_profit_cap": "disabled",
            },
        )

    assigned_accounts: list[str] = []
    if assign_missing:
        accounts = session.scalars(
            select(Account).where(
                Account.role == AccountRole.FOLLOWER.value,
                Account.risk_profile_id.is_(None),
            )
        ).all()
        for account in accounts:
            account.risk_profile_id = profile.id
            assigned_accounts.append(account.id)
        if assigned_accounts:
            record_audit(
                session,
                actor=actor,
                action="risk_profile.default_assigned",
                target_type="risk_profile",
                target_id=profile.id,
                message=(
                    f"Assigned the automatic 1% profile to {len(assigned_accounts)} "
                    "follower account(s)."
                ),
                details={"account_ids": assigned_accounts},
            )

    session.commit()
    session.refresh(profile)
    return profile
