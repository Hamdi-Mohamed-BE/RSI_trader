from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from datetime import datetime
import json

from app.db.database import get_db
from app.db.repositories import (
    TelegramMessageRepository,
    ManagedTradeRepository,
    SystemEventRepository,
    OrderAttemptRepository
)
from app.services.copier_service import copier_service
from app.services.settings_service import SettingsService
from app.trading.mt5_client import mt5_client
from app.trading.trade_manager import TradeManager

router = APIRouter(prefix="/api")

@router.post("/copier/start")
async def start_copier(db: Session = Depends(get_db)):
    """Starts the copier polling process."""
    permissions = mt5_client.get_trading_permissions()
    if not permissions.get("ok"):
        SettingsService.set(db, "copier_enabled", False)
        SystemEventRepository.log(
            db,
            "error",
            "mt5",
            f"Copier start blocked: {permissions['message']}",
            permissions,
        )
        return {
            "status": "error",
            "message": permissions["message"],
            "trading_permissions": permissions,
        }
    SettingsService.set(db, "copier_enabled", True)
    if not copier_service.is_running():
        copier_service.start()
    SystemEventRepository.log(db, "info", "system", "Copier background polling resumed by user.")
    return {"status": "success", "message": "Copier service started"}

@router.post("/copier/stop")
async def stop_copier(db: Session = Depends(get_db)):
    """Stops the copier polling process."""
    SettingsService.set(db, "copier_enabled", False)
    # We keep the thread alive but it will skip processing because copier_enabled is False.
    # Alternatively we can call copier_service.stop().
    # Keeping the background thread running is safer so it handles health checks, etc.
    SystemEventRepository.log(db, "info", "system", "Copier background polling paused by user.")
    return {"status": "success", "message": "Copier service stopped"}

@router.get("/status")
async def get_status(db: Session = Depends(get_db)):
    mt5_connected = mt5_client.connect()
    copier_enabled = SettingsService.get(db, "copier_enabled")
    
    return {
        "copier_enabled": copier_enabled,
        "copier_loop_running": copier_service.is_running(),
        "mt5_connected": mt5_connected,
        "account_info": mt5_client.get_account_info() if mt5_connected else None,
        "trading_permissions": mt5_client.get_trading_permissions() if mt5_connected else None,
    }

@router.get("/messages")
async def get_messages(db: Session = Depends(get_db)):
    return TelegramMessageRepository.get_recent(db, limit=20)

@router.get("/trades")
async def get_trades(db: Session = Depends(get_db)):
    return ManagedTradeRepository.get_recent(db, limit=20)

@router.post("/messages/{id}/reprocess")
async def reprocess_message(id: int, db: Session = Depends(get_db)):
    """Forces reprocessing of a specific message ID."""
    from app.db.models import TelegramMessage
    from sqlmodel import select
    
    msg = db.get(TelegramMessage, id)
    if not msg:
        raise HTTPException(status_code=404, detail="Telegram message not found")

    # Reset message state
    msg.ignored = False
    msg.ignore_reason = None
    msg.processed = False
    TelegramMessageRepository.save(db, msg)

    # Trigger process pipeline directly
    try:
        await copier_service._process_message(db, msg)
        SystemEventRepository.log(
            db,
            level="success",
            source="system",
            message=f"Reprocessed message ID {msg.message_id} successfully."
        )
        return {"status": "success", "message": "Message successfully reprocessed."}
    except Exception as e:
        SystemEventRepository.log(
            db,
            level="error",
            source="system",
            message=f"Reprocessing message ID {msg.message_id} failed: {str(e)}"
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trades/{id}/move-break-even")
async def force_trade_break_even(id: int, db: Session = Depends(get_db)):
    """Forces immediate break-even update for a trade."""
    from app.db.models import ManagedTrade
    trade = db.get(ManagedTrade, id)
    if not trade:
        raise HTTPException(status_code=404, detail="Managed trade not found")

    if trade.status != "active":
        raise HTTPException(status_code=400, detail="Trade is not currently active")

    # Fetch symbol specs
    sym_info = mt5_client.get_symbol_info(trade.broker_symbol)
    point = sym_info.get("point") if sym_info else 0.00001
    
    # Calculate new SL using dynamic offset points
    offset_pts = int(SettingsService.get(db, "break_even_offset_points") or 0)
    offset_price = offset_pts * point
    
    side = trade.side.lower()
    if side == "buy":
        new_sl = trade.entry_price + offset_price
    else:
        new_sl = trade.entry_price - offset_price

    digits = sym_info.get("digits") if sym_info else 5
    new_sl = round(new_sl, digits)
    
    success, error = mt5_client.modify_position(trade.mt5_ticket, stop_loss=new_sl, take_profit=trade.final_take_profit)
    if success:
        trade.stop_loss_current = new_sl
        trade.break_even_done = True
        trade.updated_at = datetime.utcnow()
        ManagedTradeRepository.save(db, trade)
        
        SystemEventRepository.log(
            db,
            level="success",
            source="trading",
            message=f"Manually moved trade {trade.mt5_ticket} to break-even at {new_sl}."
        )
        return {"status": "success", "message": "SL moved to break-even."}
    else:
        SystemEventRepository.log(
            db,
            level="error",
            source="trading",
            message=f"Manual break-even failed for trade {trade.mt5_ticket}: {error}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to modify SL: {error}")
