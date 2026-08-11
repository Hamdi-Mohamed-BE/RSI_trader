from decimal import Decimal
from typing import Annotated
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from starlette.responses import Response

from ..dependencies import request_session, require_user
from ..domain.enums import AccountRole, AccountState, JobStatus, OrderType, RiskMode, Side
from ..models import (
    Account,
    AdminUser,
    AuditEvent,
    CopyJob,
    CopyTestResult,
    CopyTestRun,
    RiskProfile,
    SourceTradeEvent,
    SymbolMapping,
)
from ..schemas import (
    AccountCreate,
    AccountUpdate,
    CopyTestInput,
    RiskProfileCreate,
    SymbolMappingCreate,
)
from ..security import validate_csrf
from ..services.accounts import (
    create_account,
    delete_account,
    ensure_system_state,
    replace_account_credential,
    select_master,
    set_global_pause,
    update_account,
)
from ..services.audit import record_audit
from ..services.copy_test import CopyTestRunner
from ..services.copy_test_execution import CopyTestExecutionRunner
from ..services.credentials import build_credential_vault
from ..services.demo_orders import DemoOrderExecutor
from ..services.mt5_discovery import detect_and_import_running_accounts
from ..services.terminals import TerminalManager
from ..templating import page_context, templates

router = APIRouter()


def _user(request: Request, session: Session) -> AdminUser:
    return require_user(request, session)


def _terminal_manager(request: Request) -> TerminalManager:
    settings = request.app.state.settings
    vault = build_credential_vault(settings.storage_dir / "vault")
    return TerminalManager(
        instances_root=settings.mt5_instances_dir,
        vault=vault,
        default_template_path=settings.mt5_template_path,
    )


@router.get("/", name="dashboard")
def dashboard(request: Request, session: Annotated[Session, Depends(request_session)]) -> Response:
    user = _user(request, session)
    state = ensure_system_state(session)
    accounts = session.scalars(select(Account).order_by(Account.display_name)).all()
    master = next((account for account in accounts if account.is_master), None)
    recent_jobs = session.scalars(
        select(CopyJob)
        .options(
            selectinload(CopyJob.follower_account),
            selectinload(CopyJob.source_event),
        )
        .order_by(CopyJob.created_at.desc())
        .limit(8)
    ).all()
    job_total = session.scalar(select(func.count(CopyJob.id))) or 0
    filled_total = (
        session.scalar(
            select(func.count(CopyJob.id)).where(CopyJob.status == JobStatus.FILLED.value)
        )
        or 0
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        page_context(
            request,
            user=user,
            state=state,
            accounts=accounts,
            master=master,
            recent_jobs=recent_jobs,
            job_total=job_total,
            filled_total=filled_total,
            healthy_count=sum(account.health == "healthy" for account in accounts),
        ),
    )


@router.post("/system/pause", name="system-pause")
def pause_system(
    request: Request,
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
    reason: Annotated[str, Form()] = "Paused from dashboard",
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    set_global_pause(session, paused=True, reason=reason, actor=user.email)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/system/unpause", name="system-unpause")
def unpause_system(
    request: Request,
    csrf: Annotated[str, Form()],
    confirmation: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    if confirmation.strip().upper() != "ENABLE":
        return RedirectResponse("/?error=Type+ENABLE+to+unpause", status_code=303)
    set_global_pause(session, paused=False, reason="Enabled by administrator", actor=user.email)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/accounts", name="accounts")
def accounts_page(
    request: Request, session: Annotated[Session, Depends(request_session)]
) -> Response:
    user = _user(request, session)
    accounts = session.scalars(
        select(Account)
        .options(selectinload(Account.risk_profile), selectinload(Account.terminal))
        .order_by(Account.display_name)
    ).all()
    profiles = session.scalars(select(RiskProfile).order_by(RiskProfile.name)).all()
    return templates.TemplateResponse(
        request,
        "accounts/list.html",
        page_context(
            request,
            user=user,
            accounts=accounts,
            profiles=profiles,
            roles=list(AccountRole),
            states=list(AccountState),
            pipe_prefix=request.app.state.settings.follower_pipe_prefix,
        ),
    )


@router.post("/accounts", name="account-create")
def account_create(
    request: Request,
    display_name: Annotated[str, Form()],
    login: Annotated[str, Form()],
    broker_server: Annotated[str, Form()],
    role: Annotated[str, Form()],
    state: Annotated[str, Form()],
    trade_mode: Annotated[str, Form()],
    position_mode: Annotated[str, Form()],
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
    terminal_path: Annotated[str, Form()] = "",
    risk_profile_id: Annotated[str, Form()] = "",
    mt5_password: Annotated[str, Form()] = "",
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    try:
        data = AccountCreate(
            display_name=display_name,
            login=login,
            broker_server=broker_server,
            terminal_path=terminal_path,
            role=AccountRole(role),
            state=AccountState(state),
            trade_mode=trade_mode,
            position_mode=position_mode,
            risk_profile_id=risk_profile_id or None,
            password=mt5_password,
        )
        vault = build_credential_vault(request.app.state.settings.storage_dir / "vault")
        account = create_account(session, data, vault=vault, actor=user.email)
    except (ValidationError, ValueError, RuntimeError) as exc:
        return RedirectResponse(f"/accounts?error={exc!s}", status_code=303)
    if mt5_password:
        try:
            _terminal_manager(request).provision_and_connect(
                session,
                account,
                actor=user.email,
                template_path=terminal_path,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            return RedirectResponse(
                f"/accounts?error=Account+saved,+but+{exc!s}", status_code=303
            )
    return RedirectResponse("/accounts", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/accounts/discover", name="account-discover")
def account_discover(
    request: Request,
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    accounts = detect_and_import_running_accounts(session, actor=user.email)
    if not accounts:
        return RedirectResponse(
            "/accounts?error=No+running+and+logged-in+MT5+terminal+was+detected",
            status_code=303,
        )
    return RedirectResponse(
        f"/accounts?notice=Detected+{len(accounts)}+MT5+account(s)", status_code=303
    )


@router.post("/accounts/{account_id}/update", name="account-update")
def account_update(
    account_id: str,
    request: Request,
    display_name: Annotated[str, Form()],
    broker_server: Annotated[str, Form()],
    role: Annotated[str, Form()],
    state: Annotated[str, Form()],
    trade_mode: Annotated[str, Form()],
    position_mode: Annotated[str, Form()],
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
    terminal_path: Annotated[str, Form()] = "",
    risk_profile_id: Annotated[str, Form()] = "",
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    account = session.get(Account, account_id)
    if account is None:
        return RedirectResponse("/accounts?error=Account+not+found", status_code=303)
    try:
        data = AccountUpdate(
            display_name=display_name,
            broker_server=broker_server,
            terminal_path=terminal_path,
            role=AccountRole(role),
            state=AccountState(state),
            trade_mode=trade_mode,
            position_mode=position_mode,
            risk_profile_id=risk_profile_id or None,
        )
        update_account(session, account, data, actor=user.email)
    except (ValidationError, ValueError) as exc:
        return RedirectResponse(f"/accounts?error={exc!s}", status_code=303)
    return RedirectResponse("/accounts?notice=Account+updated", status_code=303)


@router.post("/accounts/{account_id}/delete", name="account-delete")
def account_delete(
    account_id: str,
    request: Request,
    csrf: Annotated[str, Form()],
    confirmation: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    if confirmation.strip().upper() != "DELETE":
        return RedirectResponse("/accounts?error=Type+DELETE+to+confirm", status_code=303)
    account = session.get(Account, account_id)
    if account is None:
        return RedirectResponse("/accounts?error=Account+not+found", status_code=303)
    vault = build_credential_vault(request.app.state.settings.storage_dir / "vault")
    try:
        delete_account(
            session,
            account,
            vault=vault,
            actor=user.email,
            instance_remover=_terminal_manager(request).remove_instance,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return RedirectResponse(f"/accounts?error={exc!s}", status_code=303)
    return RedirectResponse("/accounts?notice=Account+deleted", status_code=303)


@router.post("/accounts/{account_id}/terminal/start", name="account-terminal-start")
def account_terminal_start(
    account_id: str,
    request: Request,
    csrf: Annotated[str, Form()],
    confirmation: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    if confirmation.strip().upper() != "START":
        return RedirectResponse("/accounts?error=Type+START+to+confirm", status_code=303)
    account = session.get(Account, account_id)
    if account is None:
        return RedirectResponse("/accounts?error=Account+not+found", status_code=303)
    try:
        _terminal_manager(request).start(session, account, actor=user.email)
    except (OSError, RuntimeError, ValueError) as exc:
        return RedirectResponse(f"/accounts?error={exc!s}", status_code=303)
    return RedirectResponse(
        "/accounts?notice=Managed+MT5+started+and+logged+in",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/accounts/{account_id}/terminal/provision",
    name="account-terminal-provision",
)
def account_terminal_provision(
    account_id: str,
    request: Request,
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
    mt5_password: Annotated[str, Form()] = "",
    template_path: Annotated[str, Form()] = "",
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    account = session.get(Account, account_id)
    if account is None:
        return RedirectResponse("/accounts?error=Account+not+found", status_code=303)
    vault = build_credential_vault(request.app.state.settings.storage_dir / "vault")
    try:
        if mt5_password:
            replace_account_credential(
                session,
                account,
                mt5_password,
                vault=vault,
                actor=user.email,
            )
        if not account.credential_ref:
            raise ValueError("Enter the MT5 password so this instance can log in automatically.")
        _terminal_manager(request).provision_and_connect(
            session,
            account,
            actor=user.email,
            template_path=template_path,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return RedirectResponse(f"/accounts?error={exc!s}", status_code=303)
    return RedirectResponse(
        "/accounts?notice=Dedicated+MT5+instance+built+and+logged+in",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/accounts/{account_id}/master", name="account-master")
def account_master(
    account_id: str,
    request: Request,
    csrf: Annotated[str, Form()],
    confirmation: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    if confirmation.strip().upper() != "MASTER":
        return RedirectResponse("/accounts?error=Type+MASTER+to+confirm", status_code=303)
    try:
        select_master(session, account_id, actor=user.email)
    except ValueError as exc:
        return RedirectResponse(f"/accounts?error={exc!s}", status_code=303)
    return RedirectResponse("/accounts", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/copy-test", name="copy-test")
def copy_test_page(
    request: Request,
    session: Annotated[Session, Depends(request_session)],
) -> Response:
    user = _user(request, session)
    runs = session.scalars(
        select(CopyTestRun)
        .options(selectinload(CopyTestRun.results).selectinload(CopyTestResult.follower_account))
        .order_by(CopyTestRun.created_at.desc())
        .limit(20)
    ).all()
    return templates.TemplateResponse(
        request,
        "copy_test.html",
        page_context(
            request,
            user=user,
            runs=runs,
            sides=list(Side),
            order_types=list(OrderType),
        ),
    )


@router.post("/copy-test", name="copy-test-run")
def copy_test_run(
    request: Request,
    symbol: Annotated[str, Form()],
    side: Annotated[str, Form()],
    master_volume: Annotated[Decimal, Form()],
    entry_price: Annotated[Decimal, Form()],
    stop_loss: Annotated[Decimal, Form()],
    confirmation: Annotated[str, Form()],
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
    order_type: Annotated[str, Form()] = OrderType.MARKET.value,
    take_profit: Annotated[Decimal | None, Form()] = None,
    execute_demo: Annotated[bool, Form()] = False,
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    if confirmation.strip().upper() != "TEST":
        return RedirectResponse("/copy-test?error=Type+TEST+to+confirm", status_code=303)
    try:
        data = CopyTestInput(
            symbol=symbol,
            side=Side(side),
            order_type=OrderType(order_type),
            master_volume=master_volume,
            market_price=None,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            execute_demo=execute_demo,
        )
        if request.app.state.settings.auto_detect_mt5:
            detect_and_import_running_accounts(session, actor="copy-test-refresh")
        terminal_manager = _terminal_manager(request)
        terminal_manager.prepare_copy_test(
            session,
            data.symbol,
            actor="copy-test-auto-connect",
        )
        master = session.scalar(
            select(Account).where(
                Account.is_master.is_(True),
                Account.state == AccountState.ACTIVE.value,
            )
        )
        if master is None:
            raise ValueError("No active master MT5 account is configured.")
        quote = terminal_manager.current_quote(master, data.symbol)
        live_market_price = quote.ask if data.side is Side.BUY else quote.bid
        data = CopyTestInput.model_validate(
            {**data.model_dump(), "market_price": live_market_price}
        )
        run = CopyTestRunner().run(
            session,
            data,
            actor=user.email,
            master_broker_symbol=quote.symbol,
        )
        if run.execute_demo:
            settings = request.app.state.settings
            vault = build_credential_vault(settings.storage_dir / "vault")
            run = CopyTestExecutionRunner(DemoOrderExecutor(vault=vault)).execute(
                session,
                run,
                actor=user.email,
            )
    except ValidationError as exc:
        message = str(exc.errors()[0].get("msg", "Invalid Copy Test input."))
        message = message.removeprefix("Value error, ")
        return RedirectResponse(f"/copy-test?error={quote_plus(message)}", status_code=303)
    except ValueError as exc:
        return RedirectResponse(f"/copy-test?error={quote_plus(str(exc))}", status_code=303)
    notice = "Demo+order+test+finished" if run.execute_demo else "Readiness+test+finished"
    return RedirectResponse(f"/copy-test?notice={notice}&run={run.id}", status_code=303)


@router.get("/trades", name="trades")
def trades_page(
    request: Request, session: Annotated[Session, Depends(request_session)]
) -> Response:
    user = _user(request, session)
    events = session.scalars(
        select(SourceTradeEvent)
        .options(
            selectinload(SourceTradeEvent.jobs).selectinload(CopyJob.follower_account),
            selectinload(SourceTradeEvent.jobs).selectinload(CopyJob.acknowledgement),
        )
        .order_by(SourceTradeEvent.created_at.desc())
        .limit(100)
    ).all()
    return templates.TemplateResponse(
        request,
        "trades/list.html",
        page_context(request, user=user, events=events),
    )


@router.get("/configuration", name="configuration")
def configuration_page(
    request: Request, session: Annotated[Session, Depends(request_session)]
) -> Response:
    user = _user(request, session)
    profiles = session.scalars(select(RiskProfile).order_by(RiskProfile.name)).all()
    mappings = session.scalars(
        select(SymbolMapping)
        .options(selectinload(SymbolMapping.follower_account))
        .order_by(SymbolMapping.master_symbol)
    ).all()
    followers = session.scalars(
        select(Account)
        .where(Account.role == AccountRole.FOLLOWER.value)
        .order_by(Account.display_name)
    ).all()
    return templates.TemplateResponse(
        request,
        "configuration/index.html",
        page_context(
            request,
            user=user,
            profiles=profiles,
            mappings=mappings,
            followers=followers,
            risk_modes=list(RiskMode),
        ),
    )


@router.post("/configuration/risk-profiles", name="risk-profile-create")
def risk_profile_create(
    request: Request,
    name: Annotated[str, Form()],
    mode: Annotated[str, Form()],
    risk_percent: Annotated[Decimal, Form()],
    max_total_open_risk_percent: Annotated[Decimal, Form()],
    max_daily_loss_percent: Annotated[Decimal, Form()],
    max_spread_points: Annotated[int, Form()],
    max_slippage_points: Annotated[int, Form()],
    max_open_positions: Annotated[int, Form()],
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
    max_daily_profit_percent: Annotated[Decimal, Form()] = Decimal("0"),
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    try:
        data = RiskProfileCreate(
            name=name,
            mode=RiskMode(mode),
            risk_percent=risk_percent,
            max_total_open_risk_percent=max_total_open_risk_percent,
            max_daily_loss_percent=max_daily_loss_percent,
            max_daily_profit_percent=max_daily_profit_percent,
            max_spread_points=max_spread_points,
            max_slippage_points=max_slippage_points,
            max_open_positions=max_open_positions,
        )
    except ValidationError as exc:
        return RedirectResponse(f"/configuration?error={exc!s}", status_code=303)
    profile = RiskProfile(
        name=data.name,
        mode=data.mode.value,
        risk_percent=data.risk_percent,
        max_risk_per_trade_percent=data.risk_percent,
        max_total_open_risk_percent=data.max_total_open_risk_percent,
        max_daily_loss_percent=data.max_daily_loss_percent,
        max_daily_profit_percent=data.max_daily_profit_percent,
        max_spread_points=data.max_spread_points,
        max_slippage_points=data.max_slippage_points,
        max_open_positions=data.max_open_positions,
        reject_without_stop=data.reject_without_stop,
    )
    session.add(profile)
    record_audit(
        session,
        actor=user.email,
        action="risk_profile.created",
        target_type="risk_profile",
        target_id=profile.id,
        message=f"Risk profile {profile.name} was created.",
    )
    session.commit()
    return RedirectResponse("/configuration", status_code=303)


@router.post("/configuration/symbol-mappings", name="symbol-mapping-create")
def symbol_mapping_create(
    request: Request,
    follower_account_id: Annotated[str, Form()],
    master_symbol: Annotated[str, Form()],
    follower_symbol: Annotated[str, Form()],
    price_offset: Annotated[Decimal, Form()],
    csrf: Annotated[str, Form()],
    session: Annotated[Session, Depends(request_session)],
    preserve_relative_stops: Annotated[bool, Form()] = True,
) -> Response:
    user = _user(request, session)
    validate_csrf(request, csrf)
    try:
        data = SymbolMappingCreate(
            follower_account_id=follower_account_id,
            master_symbol=master_symbol.upper(),
            follower_symbol=follower_symbol.upper(),
            price_offset=price_offset,
            preserve_relative_stops=preserve_relative_stops,
        )
    except ValidationError as exc:
        return RedirectResponse(f"/configuration?error={exc!s}", status_code=303)
    mapping = SymbolMapping(**data.model_dump())
    session.add(mapping)
    record_audit(
        session,
        actor=user.email,
        action="symbol_mapping.created",
        target_type="symbol_mapping",
        target_id=mapping.id,
        message=f"Mapped {mapping.master_symbol} to {mapping.follower_symbol}.",
    )
    session.commit()
    return RedirectResponse("/configuration", status_code=303)


@router.get("/audit", name="audit")
def audit_page(request: Request, session: Annotated[Session, Depends(request_session)]) -> Response:
    user = _user(request, session)
    events = session.scalars(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(250)
    ).all()
    return templates.TemplateResponse(
        request,
        "audit.html",
        page_context(request, user=user, events=events),
    )
