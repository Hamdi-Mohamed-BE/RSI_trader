import json
from pathlib import Path
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from datetime import datetime

from app.db.database import get_db
from app.db.models import TelegramMessage, LLMParseResult
from app.db.repositories import (
    TelegramMessageRepository,
    OrderAttemptRepository,
    ManagedTradeRepository,
    SystemEventRepository
)
from app.services.settings_service import SettingsService
from app.trading.mt5_client import mt5_client
from app.trading.order_builder import MAGIC_NUMBER
from app.core.config import settings
from app.telegram.poller import telegram_poller

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
TELEGRAM_MEDIA_DIR = Path("app/static/telegram_media")
TELEGRAM_MEDIA_URL_PREFIX = "/static/telegram_media"


def _existing_media_url_for_message(message_id: int) -> str | None:
    matches = sorted(TELEGRAM_MEDIA_DIR.glob(f"*_{message_id}.*"))
    if not matches:
        return None
    return f"{TELEGRAM_MEDIA_URL_PREFIX}/{matches[0].name}"

@router.get("/", response_class=HTMLResponse)
async def view_dashboard(request: Request, db: Session = Depends(get_db)):
    # 1. Fetch settings
    copier_enabled = SettingsService.get(db, "copier_enabled")
    max_daily = int(SettingsService.get(db, "max_trades_per_day") or 0)
    
    # 2. Get MT5 Status
    mt5_connected = mt5_client.connect()
    account_info = mt5_client.get_account_info() if mt5_connected else None
    
    account_login = account_info.get("login") if account_info else None
    account_server = account_info.get("server") if account_info else None
    balance = account_info.get("balance") if account_info else 0.0
    equity = account_info.get("equity") if account_info else 0.0

    # 3. Get active MT5 positions opened by this copier
    raw_positions = mt5_client.get_positions() if mt5_connected else []
    copier_positions = []
    
    for pos in raw_positions:
        if pos.get("magic") == MAGIC_NUMBER:
            ticket = pos.get("ticket")
            db_trade = ManagedTradeRepository.get_by_ticket(db, ticket)
            
            copier_positions.append({
                "ticket": ticket,
                "symbol": pos.get("symbol"),
                "side": pos.get("type"),
                "volume": pos.get("volume"),
                "price_open": pos.get("price_open"),
                "price_current": pos.get("price_current"),
                "sl": pos.get("sl"),
                "tp": pos.get("tp"),
                "be_done": db_trade.break_even_done if db_trade else False,
                "db_id": db_trade.id if db_trade else 0
            })
            
    # 4. Counts and recent tables
    recent_msgs = TelegramMessageRepository.get_recent(db, limit=10)
    total_messages = db.exec(select(func.count()).select_from(TelegramMessage)).one()
    
    last_polled_time = None
    if recent_msgs:
        last_polled_time = recent_msgs[0].message_date.strftime('%Y-%m-%d %H:%M:%S')
        
    daily_count = OrderAttemptRepository.get_trades_count_for_day(db, datetime.utcnow().strftime("%Y-%m-%d"))
    events = SystemEventRepository.get_recent(db, limit=10)

    context = {
        "active_page": "dashboard",
        "copier_enabled": copier_enabled,
        "mt5_connected": mt5_connected,
        "account_login": account_login,
        "account_server": account_server,
        "balance": balance,
        "equity": equity,
        "daily_trades_count": daily_count,
        "max_daily": max_daily,
        "total_messages_count": total_messages,
        "last_polled_time": last_polled_time,
        "active_trades": copier_positions,
        "recent_messages": recent_msgs,
        "system_events": events
    }
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)

@router.get("/messages", response_class=HTMLResponse)
async def view_messages(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=5, le=100),
    reloaded: int = Query(0, ge=0),
    created: int = Query(0, ge=0),
    media_updated: int = Query(0, ge=0),
):
    copier_enabled = SettingsService.get(db, "copier_enabled")
    
    # Show the full current-day message list instead of hiding older same-day posts.
    today = datetime.now()
    total_messages = TelegramMessageRepository.count_for_day(db, today)
    total_pages = max(1, (total_messages + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    recent_msgs = TelegramMessageRepository.get_for_day(db, today, limit=per_page, offset=offset)
    
    messages_data = []
    for msg in recent_msgs:
        media_url = msg.media_url or _existing_media_url_for_message(msg.message_id)
        if media_url and msg.media_url != media_url:
            msg.media_url = media_url
            TelegramMessageRepository.save(db, msg)

        # Get cached LLM parsing result from DB
        parsed_stmt = select(LLMParseResult).where(LLMParseResult.telegram_message_db_id == msg.id)
        parsed_db = db.exec(parsed_stmt).first()
        
        parsed_json_pretty = ""
        parsed_json_preview = ""
        parsed_json_has_more = False
        if parsed_db:
            try:
                parsed_obj = json.loads(parsed_db.normalized_json)
                parsed_json_pretty = json.dumps(parsed_obj, indent=2, ensure_ascii=False)
            except Exception:
                parsed_json_pretty = parsed_db.normalized_json or parsed_db.raw_response_json or ""
            preview_limit = 300
            parsed_json_has_more = len(parsed_json_pretty) > preview_limit
            parsed_json_preview = (
                parsed_json_pretty[:preview_limit].rstrip() + "\n..."
                if parsed_json_has_more
                else parsed_json_pretty
            )
                
        messages_data.append({
            "msg": msg,
            "media_url": media_url,
            "parsed": parsed_db,
            "parsed_json_pretty": parsed_json_pretty,
            "parsed_json_preview": parsed_json_preview,
            "parsed_json_has_more": parsed_json_has_more,
        })

    context = {
        "active_page": "messages",
        "copier_enabled": copier_enabled,
        "messages": messages_data,
        "message_count": total_messages,
        "message_day_label": today.strftime("%Y-%m-%d"),
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": max(1, page - 1),
        "next_page": min(total_pages, page + 1),
        "reload_notice": {
            "scanned": reloaded,
            "created": created,
            "media_updated": media_updated,
        } if reloaded else None,
    }
    return templates.TemplateResponse(request=request, name="messages.html", context=context)

@router.post("/messages/reload")
async def reload_messages_from_telegram(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Form(120),
    per_page: int = Form(25),
):
    limit = max(20, min(int(limit or 120), 300))
    per_page = max(5, min(int(per_page or 25), 100))
    result = await telegram_poller.refresh_recent_messages(db, limit=limit)
    SystemEventRepository.log(
        db,
        "info",
        "telegram",
        f"Manual Telegram reload scanned {result.get('scanned', 0)} messages, created {result.get('created', 0)}, media backfilled {result.get('media_updated', 0)}.",
    )
    return RedirectResponse(
        url=(
            "/messages"
            f"?per_page={per_page}"
            f"&reloaded={result.get('scanned', 0)}"
            f"&created={result.get('created', 0)}"
            f"&media_updated={result.get('media_updated', 0)}"
        ),
        status_code=303,
    )

@router.get("/trades", response_class=HTMLResponse)
async def view_trades(request: Request, db: Session = Depends(get_db)):
    copier_enabled = SettingsService.get(db, "copier_enabled")
    attempts = OrderAttemptRepository.get_recent(db, limit=50)
    
    context = {
        "active_page": "trades",
        "copier_enabled": copier_enabled,
        "attempts": attempts
    }
    return templates.TemplateResponse(request=request, name="trades.html", context=context)

@router.get("/settings", response_class=HTMLResponse)
async def view_settings_form(request: Request, db: Session = Depends(get_db)):
    copier_enabled = SettingsService.get(db, "copier_enabled")
    all_settings = SettingsService.get_all(db)
    
    context = {
        "active_page": "settings",
        "copier_enabled": copier_enabled,
        "settings": all_settings
    }
    return templates.TemplateResponse(request=request, name="settings.html", context=context)

@router.post("/settings")
async def save_settings_form(
    request: Request,
    db: Session = Depends(get_db),
    telegram_mode: str = Form("bot"),
    telegram_api_id: int = Form(...),
    telegram_api_hash: str = Form(...),
    telegram_bot_token: str = Form(""),
    telegram_chat_link: str = Form(...),
    telegram_read_mode: str = Form("api"),
    telegram_browser_headless: bool = Form(False),
    gemini_api_key: str = Form(...),
    gemini_model: str = Form("gemini-2.5-flash"),
    risk_mode: str = Form("fixed_lot"),
    fixed_lot: float = Form(0.01),
    symbol_lots: str = Form(""),
    risk_percent: float = Form(1.0),
    risk_usd_cap: float = Form(10.0),
    use_equity_instead_of_balance: bool = Form(False),
    allow_min_lot_if_risk_too_small: bool = Form(False),
    poll_interval_seconds: int = Form(10),
    min_llm_confidence: float = Form(0.80),
    max_spread_points: str = Form(""),
    max_trades_per_day: int = Form(0),
    daily_win_goal_usd: float = Form(500.0),
    daily_loss_limit_usd: float = Form(500.0),
    stale_signal_max_age_minutes: int = Form(5),
    stale_signal_max_entry_distance_points: int = Form(50),
    allow_reply_signals: bool = Form(False),
    allow_no_sl: bool = Form(False),
    move_to_break_even_enabled: bool = Form(False),
    break_even_offset_points: int = Form(0)
):
    # Save settings to DB
    SettingsService.set(db, "telegram_mode", telegram_mode if telegram_mode in {"bot", "user"} else "bot")
    SettingsService.set(db, "telegram_api_id", telegram_api_id)
    SettingsService.set(db, "telegram_api_hash", telegram_api_hash)
    SettingsService.set(db, "telegram_bot_token", telegram_bot_token)
    SettingsService.set(db, "telegram_chat_link", telegram_chat_link)
    SettingsService.set(db, "telegram_read_mode", telegram_read_mode if telegram_read_mode in {"api", "browser"} else "api")
    SettingsService.set(db, "telegram_browser_headless", telegram_browser_headless)
    SettingsService.set(db, "gemini_api_key", gemini_api_key)
    SettingsService.set(db, "gemini_model", gemini_model)
    SettingsService.set(db, "risk_mode", risk_mode)
    SettingsService.set(db, "fixed_lot", fixed_lot)
    SettingsService.set(db, "symbol_lots", symbol_lots)
    SettingsService.set(db, "risk_percent", risk_percent)
    SettingsService.set(db, "risk_usd_cap", risk_usd_cap)
    SettingsService.set(db, "use_equity_instead_of_balance", use_equity_instead_of_balance)
    SettingsService.set(db, "allow_min_lot_if_risk_too_small", allow_min_lot_if_risk_too_small)
    SettingsService.set(db, "poll_interval_seconds", poll_interval_seconds)
    SettingsService.set(db, "min_llm_confidence", min_llm_confidence)
    SettingsService.set(db, "max_trades_per_day", max_trades_per_day)
    SettingsService.set(db, "daily_win_goal_usd", daily_win_goal_usd)
    SettingsService.set(db, "daily_loss_limit_usd", daily_loss_limit_usd)
    SettingsService.set(db, "stale_signal_max_age_minutes", stale_signal_max_age_minutes)
    SettingsService.set(db, "stale_signal_max_entry_distance_points", stale_signal_max_entry_distance_points)
    SettingsService.set(db, "allow_reply_signals", allow_reply_signals)
    SettingsService.set(db, "allow_no_sl", allow_no_sl)
    SettingsService.set(db, "move_to_break_even_enabled", move_to_break_even_enabled)
    SettingsService.set(db, "break_even_offset_points", break_even_offset_points)
    
    if max_spread_points.strip().isdigit():
        SettingsService.set(db, "max_spread_points", int(max_spread_points))
    else:
        SettingsService.set(db, "max_spread_points", None)

    SystemEventRepository.log(db, "info", "settings", "System settings successfully updated by user.")
    return RedirectResponse(url="/settings", status_code=303)
