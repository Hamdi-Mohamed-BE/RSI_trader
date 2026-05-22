from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from bs4 import BeautifulSoup, NavigableString, Tag

_SKIP_BUBBLE_CLASSES = frozenset({"is-date", "service", "is-fake", "sticky-date", "centered"})
_NOISE_SELECTORS = (
    ".time",
    ".reactions",
    ".reply-markup",
    ".attachment",
    ".media-container",
    ".audio-element",
    ".document-container",
    ".reaction",
    ".message-status",
    ".message-time",
    ".bubble-tail",
    ".avatar",
    ".colored-name",
)
_TEXT_CLASS_HINTS = (
    "translatable-message",
    "message",
    "text-content",
    "message-content",
    "bubble-content",
    "bubble-content-wrapper",
)


@dataclass(frozen=True)
class ParsedChatMessage:
    key: str
    text: str
    timestamp: float | None = None
    source: str = "html"


@dataclass(frozen=True)
class ParseDiagnostics:
    bubble_count: int = 0
    message_count: int = 0
    mid_count: int = 0
    html_length: int = 0
    source: str = ""


def _class_set(tag: Tag) -> set[str]:
    classes = tag.get("class") or []
    return set(classes)


def _is_skippable_bubble(tag: Tag) -> bool:
    return bool(_class_set(tag) & _SKIP_BUBBLE_CLASSES)


def _parse_timestamp(tag: Tag) -> float | None:
    raw = tag.get("data-timestamp")
    if raw:
        try:
            parsed = float(raw)
            if parsed > 0:
                return parsed / 1000.0 if parsed > 1e12 else parsed
        except (TypeError, ValueError):
            pass

    parent = tag.find_parent(attrs={"data-timestamp": True})
    if parent is not None:
        raw = parent.get("data-timestamp")
        if raw:
            try:
                parsed = float(raw)
                if parsed > 0:
                    return parsed / 1000.0 if parsed > 1e12 else parsed
            except (TypeError, ValueError):
                pass

    for time_tag in tag.select(".time, .message-time, time, .time-inner"):
        title = time_tag.get("title") or time_tag.get("datetime") or ""
        if not title:
            continue
        for fmt in (
            "%d.%m.%Y, %H:%M:%S",
            "%d.%m.%Y, %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                dt = datetime.strptime(title.strip(), fmt).replace(tzinfo=timezone.utc)
                return dt.timestamp()
            except ValueError:
                continue
        try:
            normalized = title.replace(".", "-", 2) if title.count(".") >= 2 else title
            dt = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except ValueError:
            continue
    return None


def _node_text(node: Tag | NavigableString | None) -> str:
    if node is None:
        return ""
    if isinstance(node, NavigableString):
        return str(node).strip()
    return node.get_text("\n", strip=True)


def _extract_text_from_bubble(bubble: Tag) -> str:
    for hint in _TEXT_CLASS_HINTS:
        for node in bubble.select(f".{hint}"):
            text = _node_text(node)
            if text:
                return _normalize_text(text)

    clone = BeautifulSoup(str(bubble), "html.parser")
    root = clone.find(True)
    if root is None:
        return ""
    for selector in _NOISE_SELECTORS:
        for node in root.select(selector):
            node.decompose()
    return _normalize_text(root.get_text("\n", strip=True))


def _normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _message_key(tag: Tag) -> str:
    for attr in ("data-mid", "data-message-id"):
        value = tag.get(attr)
        if value:
            return str(value)
    nested = tag.select_one("[data-mid], [data-message-id]")
    if nested is not None:
        return str(nested.get("data-mid") or nested.get("data-message-id") or "")
    return ""


def _collect_bubbles(soup: BeautifulSoup) -> list[Tag]:
    bubbles: list[Tag] = []
    seen: set[int] = set()

    def add(tag: Tag) -> None:
        ident = id(tag)
        if ident in seen:
            return
        seen.add(ident)
        bubbles.append(tag)

    for tag in soup.select(".bubble"):
        if not _is_skippable_bubble(tag):
            add(tag)

    if not bubbles:
        for tag in soup.select(".Message, .message-list-item, [data-message-id]"):
            add(tag)

    if not bubbles:
        for tag in soup.select(".message"):
            host = tag.find_parent(class_=lambda value: value and "bubble" in value.split())
            add(host or tag)

    return bubbles


_AD_WORD_RE = re.compile(
    r"\b("
    r"ad|ads|advert|adverts|advertise|advertised|advertisement|advertising|advertiser|"
    r"promo|promotion|promotional|sponsored|sponsor"
    r")\b",
    re.IGNORECASE,
)
_ADD_WORD_RE = re.compile(r"\b(add|added|adding|addon|add-on)\b", re.IGNORECASE)
_AD_TAG_RE = re.compile(r"(?:#|\[|\()ad(?:s)?(?:\]|\)|\b)", re.IGNORECASE)
_AD_PREFIX_RE = re.compile(r"^ad[\s:.\-]", re.IGNORECASE)
_PREVIEW_SELECTORS = (
    ".dialog-subtitle",
    ".dialog-subtitle-span-last-message",
    ".dialog-subtitle-span",
    ".row-subtitle",
    ".subtitle",
    ".last-message",
    ".user-last-message",
)


def looks_like_ad(text: str) -> bool:
    cleaned = _normalize_text(text)
    if not cleaned:
        return False
    if _AD_PREFIX_RE.match(cleaned):
        return True
    if _AD_TAG_RE.search(cleaned):
        return True
    if _AD_WORD_RE.search(cleaned):
        return True
    if _ADD_WORD_RE.search(cleaned):
        upper = cleaned.upper()
        if re.search(r"\b(BUY|SELL)\b", upper) and re.search(r"\b(SL|TP|STOP)\b", upper):
            return False
        return True
    return False


def _hash_variants(channel_hash: str) -> set[str]:
    target = str(channel_hash or "").strip().lstrip("#")
    variants = {target} if target else set()
    if target.startswith("-100"):
        variants.add(target[4:])
    elif target.startswith("-") and target[1:].isdigit():
        variants.add(f"-100{target[1:]}")
    return {item for item in variants if item}


def _row_matches_channel(row: Tag, channel_hash: str, channel_name: str) -> bool:
    variants = _hash_variants(channel_hash)
    peer = str(row.get("data-peer-id") or "")
    if peer and any(peer == variant or peer.endswith(variant) or variant in peer for variant in variants):
        return True
    link = row.select_one("a[href]")
    href = str(link.get("href") or "") if link is not None else ""
    if href and any(f"#{variant}" in href or variant in href for variant in variants):
        return True
    title_el = row.select_one(".peer-title, .dialog-title, .user-title, .title, .name")
    title = _node_text(title_el).lower()
    wanted = channel_name.strip().lower()
    if wanted and (wanted in title or title in wanted):
        return True
    return False


def _extract_preview_text(row: Tag) -> str:
    for selector in _PREVIEW_SELECTORS:
        node = row.select_one(selector)
        text = _normalize_text(_node_text(node))
        if text:
            return text
    return _normalize_text(row.get_text("\n", strip=True))


def parse_chatlist_preview(
    html: str,
    *,
    channel_hash: str,
    channel_name: str,
    source: str = "chatlist-preview",
) -> ParsedChatMessage | None:
    soup = BeautifulSoup(html or "", "html.parser")
    for row in soup.select(".chatlist-chat, .chatlist .chat, .chatlist-chat-padding"):
        if not _row_matches_channel(row, channel_hash, channel_name):
            continue
        text = _extract_preview_text(row)
        if not text or len(text) > 2500:
            continue
        peer = str(row.get("data-peer-id") or channel_hash or channel_name)
        return ParsedChatMessage(key=f"preview:{peer}", text=text, timestamp=None, source=source)
    return None


def pick_latest_non_ad(messages: list[ParsedChatMessage]) -> tuple[ParsedChatMessage | None, bool]:
    skipped_ad = False
    for message in reversed(messages):
        if looks_like_ad(message.text):
            skipped_ad = True
            continue
        return message, skipped_ad
    return None, skipped_ad


def parse_all_messages(html: str, *, source: str = "html") -> tuple[list[ParsedChatMessage], ParseDiagnostics]:
    soup = BeautifulSoup(html or "", "html.parser")
    diagnostics = ParseDiagnostics(
        bubble_count=len(soup.select(".bubble")),
        message_count=len(soup.select(".message")),
        mid_count=len(soup.select("[data-mid], [data-message-id]")),
        html_length=len(html or ""),
        source=source,
    )

    candidates: list[ParsedChatMessage] = []
    for bubble in _collect_bubbles(soup):
        key = _message_key(bubble)
        if not key:
            continue
        text = _extract_text_from_bubble(bubble)
        if not text or len(text) > 2500:
            continue
        candidates.append(
            ParsedChatMessage(
                key=key,
                text=text,
                timestamp=_parse_timestamp(bubble),
                source=source,
            )
        )
    return candidates, diagnostics


def parse_latest_message(
    html: str,
    *,
    source: str = "html",
    skip_ads: bool = False,
) -> tuple[ParsedChatMessage | None, ParseDiagnostics]:
    candidates, diagnostics = parse_all_messages(html, source=source)
    if not candidates:
        return None, diagnostics

    if skip_ads:
        for message in reversed(candidates):
            if not looks_like_ad(message.text):
                return message, diagnostics
        return None, diagnostics

    return candidates[-1], diagnostics
