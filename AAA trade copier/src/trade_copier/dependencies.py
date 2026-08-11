from collections.abc import Generator

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from .models import AdminUser


def request_session(request: Request) -> Generator[Session]:
    session_factory = request.app.state.session_factory
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()


def current_user(request: Request, session: Session) -> AdminUser | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = session.get(AdminUser, user_id)
    if user is None or not user.is_active:
        request.session.clear()
        return None
    return user


def require_user(request: Request, session: Session) -> AdminUser:
    user = current_user(request, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user
