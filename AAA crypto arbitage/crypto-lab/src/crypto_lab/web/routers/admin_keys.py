"""Admin: API key vault. Secret values are write-only; responses only ever contain masked views."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response

from crypto_lab.domain.errors import DomainError
from crypto_lab.web.deps import AdminDep, ContainerDep, CsrfAdminDep, DbDep, actor_for
from crypto_lab.web.templating import render

router = APIRouter(prefix="/admin/keys", tags=["admin:keys"])


async def _form_values(request: Request) -> dict[str, str]:
    form = await request.form()
    return {k[len("field_") :]: str(v) for k, v in form.items() if k.startswith("field_") and isinstance(v, str)}


@router.get("")
async def list_keys(request: Request, container: ContainerDep, db: DbDep, admin: AdminDep) -> Response:
    credentials = await container.vault(db).list()
    return render(
        request, "admin/keys.html", {"credentials": credentials, "providers": list(container.providers)}, admin=admin
    )


@router.get("/new")
async def new_key_form(request: Request, container: ContainerDep, admin: AdminDep, provider: str) -> Response:
    spec = container.providers.get(provider)
    return render(request, "admin/key_form.html", {"spec": spec, "credential": None, "error": None}, admin=admin)


@router.post("")
async def create_key(
    request: Request,
    container: ContainerDep,
    db: DbDep,
    admin: CsrfAdminDep,
    provider: Annotated[str, Form()],
    environment: Annotated[str, Form()],
    label: Annotated[str, Form(max_length=80)] = "",
) -> Response:
    spec = container.providers.get(provider)
    try:
        await container.vault(db).create(
            provider, label, environment, await _form_values(request), actor_for(admin, request)
        )
    except DomainError as exc:
        return render(
            request,
            "admin/key_form.html",
            {"spec": spec, "credential": None, "error": str(exc)},
            admin=admin,
            status_code=422,
        )
    await db.commit()
    return RedirectResponse("/admin/keys?flash=saved", status_code=303)


@router.get("/{credential_id}/rotate")
async def rotate_form(
    request: Request, credential_id: str, container: ContainerDep, db: DbDep, admin: AdminDep
) -> Response:
    view = await container.vault(db).get(credential_id)
    return render(
        request, "admin/key_form.html", {"spec": view.provider, "credential": view, "error": None}, admin=admin
    )


@router.post("/{credential_id}/rotate")
async def rotate_key(
    request: Request, credential_id: str, container: ContainerDep, db: DbDep, admin: CsrfAdminDep
) -> Response:
    vault = container.vault(db)
    try:
        await vault.rotate(credential_id, await _form_values(request), actor_for(admin, request))
    except DomainError as exc:
        view = await vault.get(credential_id)
        return render(
            request,
            "admin/key_form.html",
            {"spec": view.provider, "credential": view, "error": str(exc)},
            admin=admin,
            status_code=422,
        )
    await db.commit()
    return RedirectResponse("/admin/keys?flash=rotated", status_code=303)


@router.post("/{credential_id}/toggle")
async def toggle_key(
    request: Request,
    credential_id: str,
    container: ContainerDep,
    db: DbDep,
    admin: CsrfAdminDep,
    enabled: Annotated[bool, Form()],
) -> Response:
    await container.vault(db).set_enabled(credential_id, enabled, actor_for(admin, request))
    await db.commit()
    return RedirectResponse(f"/admin/keys?flash={'enabled' if enabled else 'disabled'}", status_code=303)


@router.post("/{credential_id}/delete")
async def delete_key(
    request: Request, credential_id: str, container: ContainerDep, db: DbDep, admin: CsrfAdminDep
) -> Response:
    await container.vault(db).delete(credential_id, actor_for(admin, request))
    await db.commit()
    return RedirectResponse("/admin/keys?flash=deleted", status_code=303)
