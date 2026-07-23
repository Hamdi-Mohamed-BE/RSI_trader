import re
from typing import Optional, List, Tuple
from sqlmodel import Session
from app.llm.schemas import SignalParseSchema
from app.llm.gemini_client import gemini_client
from app.core.logging import logger
from app.core.config import settings

# Regex patterns for deterministic parsing. Symbol detection is intentionally
# context-based instead of a fixed whitelist; the broker resolver handles the
# final mapping to MT5 symbols such as XAUUSDm, US30m, USTECm, etc.
SYMBOL_TOKEN_PATTERN = re.compile(r"[#$*`_~\[]*([A-Z][A-Z0-9._/-]{1,15})[\]$*`_~]*", re.IGNORECASE)
SYMBOL_BEFORE_SIDE_PATTERN = re.compile(
    r"(?:^|[\s*_#])([A-Z][A-Z0-9._/-]{1,15})\s+(?:BUY(?:ING)?|SELL(?:ING)?)\b",
    re.IGNORECASE,
)
SYMBOL_AFTER_SIDE_PATTERN = re.compile(
    r"\b(?:BUY(?:ING)?|SELL(?:ING)?)(?:\s+(?:NOW|MARKET|LIMIT|STOP|ENTRY|ENTRIES|ZONE|AT))*\s+([A-Z][A-Z0-9._/-]{1,15})\b",
    re.IGNORECASE,
)

NON_SYMBOL_TOKENS = {
    "A",
    "ACTIVE",
    "AGAIN",
    "ALL",
    "AM",
    "AND",
    "AT",
    "BE",
    "BUY",
    "ENTRY",
    "ENTRIES",
    "FIRST",
    "FOR",
    "FROM",
    "HIT",
    "LIMIT",
    "LOSS",
    "MARKET",
    "NOW",
    "ORDER",
    "PRICE",
    "PROFIT",
    "SCALP",
    "SELL",
    "SELLING",
    "SETUP",
    "SIGNAL",
    "SL",
    "STOP",
    "STOPLOSS",
    "STOPLOSSS",
    "TAKE",
    "TARGET",
    "TP",
    "UPDATE",
    "ZONE",
}

SL_PATTERN = re.compile(r"(?:sl|s/l|stop\s*loss|stoploss+|stop\s*oss|stoposs)\b\s*[@:=]?\s*([0-9.]+)", re.IGNORECASE)
TP_PATTERN = re.compile(r"(?:tp\s*\d*|take\s*profit|target)\b\s*[@:=]?\s*([0-9.]+)", re.IGNORECASE)

# Pending entry pattern — matches "@ 2355.50", "entry 2355.50", "price: 1.3500", etc.
ENTRY_PATTERN = re.compile(r"(?:entry(?:\s*point)?|entries|at|price|limit|stop)\s*[@:=]?\s*([0-9.]+)", re.IGNORECASE)
# Standalone @ with a price (e.g., "SELL LIMIT GOLD @ 2355.50")
AT_PRICE_PATTERN = re.compile(r"@\s*([0-9.]+)", re.IGNORECASE)
ENTRY_RANGE_PATTERN = re.compile(
    r"(?:entry(?:\s*point)?|entries|at|price)\s*[@:=]?\s*"
    r"([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|—|to|â€“|â€”)\s*([0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
PENDING_RANGE_PATTERN = re.compile(
    r"\b(?P<side>buy|sell)\s+(?P<kind>limit|stop)\b[^\d\n]*"
    r"(?P<first>[0-9]+(?:\.[0-9]+)?)\s*(?:-|–|—|to)\s*"
    r"(?P<second>[0-9]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
PRICE_PATTERN = re.compile(r"(?<![A-Za-z])([0-9]+(?:\.[0-9]+)?)")


def clean_symbol_token(value: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9._/-]", "", (value or "").upper())
    return cleaned.strip("._-/")


def is_symbol_candidate(value: str) -> bool:
    token = clean_symbol_token(value)
    if not token or token in NON_SYMBOL_TOKENS:
        return False
    if token.startswith(("TP", "SL")) and token[2:].isdigit():
        return False
    if token.replace(".", "").isdigit():
        return False
    letters = sum(1 for char in token if char.isalpha())
    if letters < 2:
        return False
    return bool(re.search(r"[A-Z]", token))


def extract_symbol_raw(text: str) -> Optional[str]:
    text_upper = (text or "").upper()

    for pattern in (SYMBOL_BEFORE_SIDE_PATTERN, SYMBOL_AFTER_SIDE_PATTERN):
        for match in pattern.finditer(text_upper):
            candidate = clean_symbol_token(match.group(1))
            if is_symbol_candidate(candidate):
                return candidate

    for line in text_upper.splitlines():
        if not re.search(r"\b(?:BUY(?:ING)?|SELL(?:ING)?)\b", line):
            continue
        for match in SYMBOL_TOKEN_PATTERN.finditer(line):
            candidate = clean_symbol_token(match.group(1))
            if is_symbol_candidate(candidate):
                return candidate

    return None


def infer_symbol_from_price_context(text: str) -> Optional[str]:
    """
    Infer gold only for compact channel posts that omit the symbol but use
    XAU-style prices, for example: BUY LIMIT 4087 - 4085 SL 4082.
    """
    text_upper = (text or "").upper()
    if not re.search(r"\b(?:BUY(?:ING)?|SELL(?:ING)?)\b", text_upper):
        return None
    if not re.search(r"\b(?:SL|S/L|STOP\s*LOSS|STOPLOSS|STOPOSS|TP|TARGET)\b", text_upper):
        return None

    prices = [float(match.group(1)) for match in PRICE_PATTERN.finditer(text_upper)]
    trade_prices = [price for price in prices if 1000 <= price <= 10000]
    if len(trade_prices) >= 3 and len(trade_prices) == len(prices):
        return "XAUUSD"
    return None


def merge_deterministic_fields(
    primary: SignalParseSchema,
    deterministic: Optional[SignalParseSchema],
    raw_text: str = "",
) -> SignalParseSchema:
    """
    Keep the LLM response, but repair missing core trade fields from the
    deterministic parser. A signal with symbol_raw=None should never reach MT5.
    """
    repaired = primary.model_copy(deep=True)
    notes_added = False

    def fill(field: str, value):
        nonlocal notes_added
        if value in (None, "", []):
            return
        if getattr(repaired, field, None) in (None, "", []):
            setattr(repaired, field, value)
            notes_added = True

    if deterministic:
        fill("symbol_raw", deterministic.symbol_raw)
        fill("side", deterministic.side)
        fill("order_type", deterministic.order_type)
        fill("pending_type", deterministic.pending_type)
        fill("entry_price", deterministic.entry_price)
        fill("stop_loss", deterministic.stop_loss)
        if not repaired.take_profits:
            repaired.take_profits = list(deterministic.take_profits)
            notes_added = True
        fill("final_take_profit", deterministic.final_take_profit)
        fill("break_even_trigger_tp", deterministic.break_even_trigger_tp)
    elif repaired.is_signal and not repaired.symbol_raw:
        symbol = extract_symbol_raw(raw_text) or infer_symbol_from_price_context(raw_text)
        if symbol:
            repaired.symbol_raw = symbol
            notes_added = True

    if notes_added:
        repaired.parser_notes.append("Repaired missing fields from deterministic text parser.")
    return repaired

def parse_determinist(text: str) -> Optional[SignalParseSchema]:
    """
    Attempts to deterministically parse a signal message.
    Returns a SignalParseSchema if the basic parameters (Symbol, Side, SL, TP) are found.
    Otherwise returns None.
    """
    text_clean = text.strip()
    text_lines = text_clean.split("\n")
    
    # 1. Match symbol
    symbol = extract_symbol_raw(text_clean) or infer_symbol_from_price_context(text_clean)
    if not symbol:
        return None
    
    # 2. Match side & order type
    side = None
    order_type = "market"
    pending_type = None
    
    text_lower = text_clean.lower()
    
    # Determine buy vs sell
    if re.search(r"\bbuy(?:ing)?\b", text_lower):
        side = "buy"
    elif re.search(r"\bsell(?:ing)?\b", text_lower):
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
        if re.match(r"^\s*(?:tp\s*\d*|take\s*profit|target)\b", line, re.IGNORECASE):
            if re.match(r"^\s*tp\s*\d+\s*[@:=]?\s*(?:open|running|runner)\b", line, re.IGNORECASE):
                continue
            if re.match(r"^\s*tp\s*\d+\s*[@:=]", line, re.IGNORECASE):
                for match in TP_PATTERN.finditer(line):
                    tps.append(float(match.group(1)))
                continue
            line_numbers = [float(match.group(1)) for match in PRICE_PATTERN.finditer(line)]
            if line_numbers:
                tps.extend(line_numbers)
                continue
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
    
    # 5. Entry price, if provided
    entry_price = None
    entry_range_match = ENTRY_RANGE_PATTERN.search(text_clean)
    if entry_range_match:
        first = float(entry_range_match.group(1))
        second = float(entry_range_match.group(2))
        low = min(first, second)
        high = max(first, second)
        entry_price = low if side == "buy" else high

    if order_type == "pending":
        range_match = PENDING_RANGE_PATTERN.search(text_clean)
        if range_match:
            first = float(range_match.group("first"))
            second = float(range_match.group("second"))
            low = min(first, second)
            high = max(first, second)
            if pending_type == "buy_limit":
                entry_price = low
            elif pending_type == "sell_limit":
                entry_price = high
            elif pending_type == "buy_stop":
                entry_price = high
            elif pending_type == "sell_stop":
                entry_price = low

        entry_match = ENTRY_PATTERN.search(text_clean)
        if entry_price is None and entry_match:
            entry_price = float(entry_match.group(1))
        if entry_price is None:
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
    elif entry_price is None:
        entry_match = ENTRY_PATTERN.search(text_clean)
        if entry_match:
            entry_price = float(entry_match.group(1))
            
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
        from sqlmodel import select, desc
        import json
        
        statement = (
            select(LLMParseResult)
            .where(LLMParseResult.telegram_message_db_id == message_db_id)
            .order_by(desc(LLMParseResult.created_at))
        )
        cached = session.exec(statement).first()
        if cached:
            logger.info(f"Using cached parse result for message ID {message_db_id}")
            if cached.error:
                # If cached version was an error, we can try parsing again or re-raise
                logger.warning(f"Cached result was an error: {cached.error}. Re-parsing.")
            else:
                try:
                    parsed_data = json.loads(cached.normalized_json)
                    cached_result = SignalParseSchema(**parsed_data)
                    det_for_cache = parse_determinist(text)
                    repaired_result = merge_deterministic_fields(cached_result, det_for_cache, text)
                    if cached_result.model_dump() != repaired_result.model_dump():
                        cached.normalized_json = repaired_result.model_dump_json()
                        cached.raw_response_json = repaired_result.model_dump_json()
                        cached.confidence = repaired_result.confidence
                        cached.is_signal = repaired_result.is_signal
                        session.add(cached)
                        session.commit()
                        logger.warning(
                            f"Repaired cached parse result for message ID {message_db_id}: "
                            f"symbol={repaired_result.symbol_raw}"
                        )
                    return repaired_result
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
        gemini_result = merge_deterministic_fields(gemini_result, det_result, text)
            
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
