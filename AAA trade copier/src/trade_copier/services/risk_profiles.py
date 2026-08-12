from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.enums import AccountRole, RiskMode
from ..models import Account, RiskProfile
from .audit import record_audit

DEFAULT_RISK_PROFILE_NAME = "Automatic 1% per trade"
LEGACY_DEFAULT_RISK_PROFILE_NAME = "Exact master copy"


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
    legacy_profile = session.scalar(
        select(RiskProfile).where(RiskProfile.name == LEGACY_DEFAULT_RISK_PROFILE_NAME)
    )
    migrated = False
    if profile is None and legacy_profile is not None:
        profile = legacy_profile
        profile.name = DEFAULT_RISK_PROFILE_NAME
        migrated = True
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
    profile.reject_without_stop = False
    profile.enabled = True

    if legacy_profile is not None and legacy_profile.id != profile.id:
        legacy_accounts = session.scalars(
            select(Account).where(Account.risk_profile_id == legacy_profile.id)
        ).all()
        for account in legacy_accounts:
            account.risk_profile_id = profile.id
            session.add(account)
        migrated = migrated or bool(legacy_accounts)

    if created or migrated:
        record_audit(
            session,
            actor=actor,
            action=(
                "risk_profile.default_created"
                if created
                else "risk_profile.default_migrated"
            ),
            target_type="risk_profile",
            target_id=profile.id,
            message=(
                "Configured 1% stop-risk sizing with exact master lots when no SL exists."
            ),
            details={
                "volume_mode_with_stop": "one_percent_stop_risk",
                "volume_mode_without_stop": "exact_master_lots",
                "daily_loss_cap": "disabled",
                "daily_profit_cap": "disabled",
                "stop_loss_required": False,
                "legacy_profile_id": (
                    legacy_profile.id
                    if legacy_profile is not None and legacy_profile.id != profile.id
                    else ""
                ),
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
                    f"Assigned automatic hybrid risk to {len(assigned_accounts)} "
                    "follower account(s)."
                ),
                details={"account_ids": assigned_accounts},
            )

    session.commit()
    session.refresh(profile)
    return profile
