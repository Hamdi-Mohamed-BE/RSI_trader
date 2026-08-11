from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.responses import Response

from ..dependencies import request_session
from ..security import validate_csrf
from ..services.auth import authenticate
from ..templating import page_context, templates

router = APIRouter()


@router.get("/login", name="login")
def login_page(request: Request) -> Response:
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", page_context(request))


@router.post("/login", name="login-submit")
def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
) -> Response:
    validate_csrf(request, csrf)
    user = authenticate(session, email, password)
    if user is None:
        return templates.TemplateResponse(
            request,
            "login.html",
            page_context(request, error="Email or password is incorrect."),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", name="logout")
def logout(request: Request, csrf: Annotated[str, Form()]) -> Response:
    validate_csrf(request, csrf)
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
