import re
from typing import Optional, List, Tuple
from sqlmodel import Session
from app.llm.schemas import SignalParseSchema
from app.llm.gemini_client import gemini_client
from app.core.logging import logger
from app.core.config import settings

# Regex patterns for deterministic parsing
SYMBOL_PATTERN = re.compile(r"\b([A-Z]{6}|XAUUSD|XAGUSD|GOLD|SILVER|BTCUSD|BTC|ETHUSD|ETH|US30|DJ30|DJI|NAS100|USTEC|US100|SP500|SPX500|GER30|DE30|UK100)\b", re.IGNORECASE)

SL_PATTERN = re.compile(r"(?:sl|stop\s*loss|stoploss)\b\s*[@:=]?\s*([0-9.]+)", re.IGNORECASE)
TP_PATTERN = re.compile(r"(?:tp|take\s*profit|target|tp\d+)\b\s*[@:=]?\s*([0-9.]+)", re.IGNORECASE)

# Pending entry pattern — matches "@ 2355.50", "entry 2355.50", "price: 1.3500", etc.
ENTRY_PATTERN = re.compile(r"(?:entry|entries|at|price|limit|stop)\s*[@:=]?\s*([0-9.]+)", re.IGNORECASE)
# Standalone @ with a price (e.g., "SELL LIMIT GOLD @ 2355.50")
AT_PRICE_PATTERN = re.compile(r"@\s*([0-9.]+)", re.IGNORECASE)

def parse_determinist(text: str) -> Optional[SignalParseSchema]:
    """
    Attempts to deterministically parse a signal message.
    Returns a SignalParseSchema if the basic parameters (Symbol, Side, SL, TP) are found.
    Otherwise returns None.
    """
    text_clean = text.strip()
    text_lines = text_clean.split("\n")
    
    # 1. Match symbol
    sym_match = SYMBOL_PATTERN.search(text_clean)
    if not sym_match:
        return None
    symbol = sym_match.group(1).upper()
    
    # 2. Match side & order type
    side = None
    order_type = "market"
    pending_type = None
    
    text_lower = text_clean.lower()
    
    # Determine buy vs sell
    if "buy" in text_lower:
        side = "buy"
    elif "sell" in text_lower:
        side = "sell"
    else:
        return None
        
    # Determine pending type — match explicit phrases to avoid false positives
    # e.g., "stoploss" should NOT trigger pending "stop" order detection
    if re.search(r'\b(?:buy|sell)\s+limit\b', text_lower):
        order_type = "pending"
        pending_type = f"{side}_limit"
    elif re.search(r'\b(?:buy|sell)\s+stop\b', text_lower):
        order_type = "pending"
        pending_type = f"{side}_stop"
            
    # 3. Match SL
    sl_match = SL_PATTERN.search(text_clean)
    if not sl_match:
        return None
    stop_loss = float(sl_match.group(1))
    
    # 4. Match TPs
    tps = []
    for line in text_lines:
        for match in TP_PATTERN.finditer(line):
            tps.append(float(match.group(1)))
            
    if not tps:
        return None
        
    # Sort TPs relative to direction (ascending for buy, descending for sell)
    # or just keep in order parsed
    tps = sorted(list(set(tps)))
    if side == "sell":
        tps = sorted(tps, reverse=True)
        
    final_tp = tps[-1]
    break_even_trigger_tp = tps[0] if len(tps) > 0 else None
    
    # 5. Entry price for pending
    entry_price = None
    if order_type == "pending":
        entry_match = ENTRY_PATTERN.search(text_clean)
        if entry_match:
            entry_price = float(entry_match.group(1))
        else:
            # Fallback: look for standalone "@" prices that aren't already SL or TP
            known_values = set(tps + [stop_loss])
            for at_match in AT_PRICE_PATTERN.finditer(text_clean):
                candidate = float(at_match.group(1))
                if candidate not in known_values:
                    entry_price = candidate
                    break
        
        if entry_price is None:
            # If it's pending but we can't find entry price, deterministic fails
            return None
            
    return SignalParseSchema(
        is_signal=True,
        confidence=0.95,
        ignore_reason=None,
        message_type="signal",
        symbol_raw=symbol,
        side=side,
        order_type=order_type,
        pending_type=pending_type,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profits=tps,
        final_take_profit=final_tp,
        break_even_trigger_tp=break_even_trigger_tp,
        risk_warnings=[],
        parser_notes=["Parsed deterministically via regex."]
    )

async def parse_signal(text: str, message_db_id: Optional[int] = None, session: Optional[Session] = None, dynamic_key: str | None = None, dynamic_model: str | None = None) -> SignalParseSchema:
    """
    Two-layer parser:
    1. Checks if a cached LLM parse result exists in the database.
    2. Runs regex deterministic parser.
    3. Runs Gemini validation/secondary parser.
    If Gemini succeeds, its parsed result is cached in the DB and returned.
    """
    # 1. Check cache in database if session & message_db_id are provided
    if session and message_db_id:
        from app.db.models import LLMParseResult
        from sqlmodel import select
        import json
        
        statement = select(LLMParseResult).where(LLMParseResult.telegram_message_db_id == message_db_id)
        cached = session.exec(statement).first()
        if cached:
            logger.info(f"Using cached parse result for message ID {message_db_id}")
            if cached.error:
                # If cached version was an error, we can try parsing again or re-raise
                logger.warning(f"Cached result was an error: {cached.error}. Re-parsing.")
            else:
                try:
                    parsed_data = json.loads(cached.normalized_json)
                    return SignalParseSchema(**parsed_data)
                except Exception as cache_err:
                    logger.error(f"Error reading cached JSON: {cache_err}")

    logger.info("Parsing signal message...")
    
    # Run deterministic parser
    det_result = None
    try:
        det_result = parse_determinist(text)
        if det_result:
            logger.info(f"Deterministic parser succeeded: {det_result.symbol_raw} {det_result.side}")
    except Exception as e:
        logger.warning(f"Deterministic parser failed with error: {e}")
        
    # Run Gemini parser
    try:
        gemini_result = await gemini_client.parse_message(text, dynamic_key, dynamic_model)
        logger.info(f"Gemini parser finished: is_signal={gemini_result.is_signal}, confidence={gemini_result.confidence}")
        
        # Merge notes if deterministic succeeded
        if det_result and gemini_result.is_signal:
            gemini_result.parser_notes.append("Deterministic parser also matched successfully.")
            
        # Cache successful Gemini result
        if session and message_db_id:
            try:
                from app.db.repositories import LLMParseResultRepository
                model_name = dynamic_model or settings.GEMINI_MODEL
                db_result = LLMParseResult(
                    telegram_message_db_id=message_db_id,
                    provider="gemini",
                    model=model_name,
                    raw_response_json=gemini_result.model_dump_json(),
                    normalized_json=gemini_result.model_dump_json(),
                    confidence=gemini_result.confidence,
                    is_signal=gemini_result.is_signal
                )
                LLMParseResultRepository.save(session, db_result)
                logger.info(f"Cached parse result for message ID {message_db_id}")
            except Exception as save_err:
                logger.error(f"Failed to cache parse result in DB: {save_err}")
                
        return gemini_result
    except Exception as e:
        logger.error(f"Gemini parser failed: {e}")
        
        # Cache the failure
        if session and message_db_id:
            try:
                from app.db.repositories import LLMParseResultRepository
                model_name = dynamic_model or settings.GEMINI_MODEL
                db_result = LLMParseResult(
                    telegram_message_db_id=message_db_id,
                    provider="gemini",
                    model=model_name,
                    raw_response_json="{}",
                    normalized_json="{}",
                    confidence=0.0,
                    is_signal=False,
                    error=str(e)
                )
                LLMParseResultRepository.save(session, db_result)
            except Exception:
                pass

        if det_result:
            logger.info("Falling back to deterministic parser result since Gemini failed.")
            det_result.parser_notes.append("Gemini parser failed, fell back to deterministic results.")
            
            # Save deterministic result to cache
            if session and message_db_id:
                try:
                    from app.db.repositories import LLMParseResultRepository
                    model_name = "deterministic"
                    db_result = LLMParseResult(
                        telegram_message_db_id=message_db_id,
                        provider="regex",
                        model=model_name,
                        raw_response_json=det_result.model_dump_json(),
                        normalized_json=det_result.model_dump_json(),
                        confidence=det_result.confidence,
                        is_signal=det_result.is_signal
                    )
                    LLMParseResultRepository.save(session, db_result)
                except Exception:
                    pass
                    
            return det_result
        else:
            # Re-raise error if we have no parser success
            raise
