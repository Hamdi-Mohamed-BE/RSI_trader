from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .config import Settings, get_settings
from .database import SessionLocal, create_schema, engine
from .routers import api, auth, web
from .services.auth import bootstrap_admin
from .services.demo_cleanup import remove_legacy_demo_seed
from .services.mt5_discovery import detect_and_import_running_accounts
from .services.risk_profiles import ensure_default_risk_profile

PACKAGE_DIR = Path(__file__).resolve().parent


def create_app(
    *,
    settings: Settings | None = None,
    active_engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    selected_engine = active_engine or engine
    selected_factory = session_factory or SessionLocal

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        create_schema(selected_engine)
        with selected_factory() as session:
            bootstrap_admin(session, active_settings)
            remove_legacy_demo_seed(session)
            ensure_default_risk_profile(session, actor="startup")
            if active_settings.auto_detect_mt5 and active_settings.app_env != "test":
                detect_and_import_running_accounts(session, actor="startup")
        yield

    application = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        docs_url="/api/docs" if active_settings.app_env != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.engine = selected_engine
    application.state.session_factory = selected_factory
    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        SessionMiddleware,
        secret_key=active_settings.app_secret_key,
        session_cookie="aaa_trade_copier_session",
        same_site="strict",
        https_only=active_settings.app_env == "production",
        max_age=60 * 60 * 12,
    )
    application.mount(
        "/static",
        StaticFiles(directory=PACKAGE_DIR / "static"),
        name="static",
    )
    application.include_router(auth.router)
    application.include_router(web.router)
    application.include_router(api.router)
    return application


app = create_app()
