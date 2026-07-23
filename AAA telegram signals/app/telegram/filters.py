import re
from typing import Tuple, Optional
from telethon.tl.types import Message
from app.core.config import settings

# Keywords to detect promotional/result posts
AD_KEYWORDS = [
    r"join", r"promo", r"referral", r"broker", r"discount", r"signup", r"register",
    r"vip channel", r"premium", r"signals pack", r"bonus", r"affiliate"
]

RESULT_KEYWORDS = [
    r"profit", r"pips secured", r"hit tp", r"tp hit", r"closed at profit",
    r"running \+", r"closed manual", r"running profit", r"won", r"win rate"
]

EDUCATION_KEYWORDS = [
    r"webinar", r"education", r"tutorial", r"course", r"learn how", r"analysis update",
    r"chart setup", r"technical analysis", r"market overview"
]


def looks_like_trade_signal(text: str) -> bool:
    """Detect strong signal shape before generic disclaimer/result filters."""
    text_lower = (text or "").lower()
    has_side = bool(re.search(r"\b(?:buy|sell|buying|selling)\b", text_lower))
    has_sl = bool(re.search(r"\b(?:sl|s/l|stop\s*loss|stoploss+|stop\s*oss|stoposs)\b", text_lower))
    has_tp = bool(re.search(r"\b(?:tp\s*\d*|take\s*profit|target)\b", text_lower))
    return has_side and has_sl and has_tp


def is_spam_or_promo(text: str) -> bool:
    """Helper to detect promotional or spam content."""
    text_lower = text.lower()
    for kw in AD_KEYWORDS:
        if re.search(kw, text_lower):
            return True
    return False

def is_result_message(text: str) -> bool:
    """Helper to check if message is a results report rather than a signal."""
    text_lower = text.lower()
    for kw in RESULT_KEYWORDS:
        if re.search(kw, text_lower):
            return True
    return False

def is_educational(text: str) -> bool:
    """Helper to check if message is an educational post."""
    text_lower = text.lower()
    for kw in EDUCATION_KEYWORDS:
        if re.search(kw, text_lower):
            return True
    return False

def filter_message(
    message: Message,
    allow_reply_signals: bool | None = None,
) -> Tuple[bool, Optional[str]]:
    """
    Evaluates a Telegram Message object and determines if it should be filtered out.
    Returns: (should_ignore: bool, ignore_reason: Optional[str])
    """
    # 1. Check if forwarded
    if message.fwd_from:
        return True, "forwarded"
        
    # 2. Check if reply
    allow_replies = settings.ALLOW_REPLY_SIGNALS if allow_reply_signals is None else allow_reply_signals
    if message.reply_to and not allow_replies:
        return True, "reply"
        
    # 3. Check for text presence
    text = message.text or ""
    if not text.strip():
        return True, "empty_text"

    # Real signal posts often include boilerplate like "not financial advice",
    # "profit", or "educational purposes". Let the parser decide when the
    # message clearly contains side + SL + TP.
    if looks_like_trade_signal(text):
        return False, None
        
    # 4. Check for ads/promos
    if is_spam_or_promo(text):
        return True, "ad"
        
    # 5. Check for trade results reports
    if is_result_message(text):
        return True, "result"
        
    # 6. Check for educational content
    if is_educational(text):
        return True, "education"
        
    # Simple check for intent: signal must contain a symbol or trade actions
    # We can do a lightweight check, or leave detailed check to the deterministic/LLM parser.
    # For now, let's keep it open to let the parser make the final call on is_signal.
    
    return False, None
