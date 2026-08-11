from datetime import UTC, datetime

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AdminUser
from ..schemas import AdminCreate
from .audit import record_audit

password_hash = PasswordHash.recommended()


def create_admin(session: Session, data: AdminCreate) -> AdminUser:
    normalized_email = data.email.strip().lower()
    existing = session.scalar(select(AdminUser).where(AdminUser.email == normalized_email))
    if existing:
        raise ValueError("An administrator with this email already exists.")

    user = AdminUser(
        email=normalized_email,
        display_name=data.display_name.strip(),
        password_hash=password_hash.hash(data.password),
    )
    session.add(user)
    record_audit(
        session,
        actor=normalized_email,
        action="admin.created",
        target_type="admin_user",
        message="Local administrator created.",
    )
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> AdminUser | None:
    user = session.scalar(select(AdminUser).where(AdminUser.email == email.strip().lower()))
    if not user or not user.is_active:
        return None
    if not password_hash.verify(password, user.password_hash):
        return None
    user.last_login_at = datetime.now(UTC)
    session.commit()
    return user


def bootstrap_admin(session: Session, settings: Settings) -> AdminUser | None:
    normalized_email = settings.admin_email.strip().lower()
    existing = session.scalar(select(AdminUser).where(AdminUser.email == normalized_email))
    if existing or not settings.admin_password:
        return existing
    return create_admin(
        session,
        AdminCreate(
            email=settings.admin_email,
            password=settings.admin_password,
            display_name="AAA Administrator",
        ),
    )
