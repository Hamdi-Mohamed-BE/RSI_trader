import hashlib
import re


def normalize_signal_text(text: str | None) -> str:
    """Make Telegram signal text stable enough for duplicate detection."""
    if not text:
        return ""
    normalized = text.casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def signal_content_hash(text: str | None) -> str:
    normalized = normalize_signal_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
