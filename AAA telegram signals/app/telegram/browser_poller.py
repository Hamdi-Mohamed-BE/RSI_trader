import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from sqlmodel import Session

from app.core.config import settings
from app.core.logging import telegram_logger
from app.db.models import TelegramMessage
from app.db.repositories import TelegramMessageRepository, SettingsRepository, SystemEventRepository
from app.telegram.filters import filter_message


BROWSER_STORAGE_DIR = Path("storage/browser_profile")
BROWSER_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DRIVER_STORAGE_DIR = Path("storage/webdrivers")
DRIVER_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class BrowserMessage:
    id: int
    text: str
    date: Optional[datetime] = None
    reply_to: object | None = None
    fwd_from: object | None = None


def normalize_telegram_web_url(chat_link: str) -> str:
    chat_link = (chat_link or "").strip()
    if not chat_link:
        return "https://web.telegram.org/k/"
    if chat_link.startswith("https://web.telegram.org/"):
        return chat_link
    if chat_link.startswith("https://t.me/"):
        return chat_link
    if chat_link.startswith("@"):
        return f"https://web.telegram.org/k/#{chat_link}"
    if chat_link.startswith("-100"):
        return f"https://web.telegram.org/k/#-{chat_link[4:]}"
    if chat_link.startswith("-"):
        return f"https://web.telegram.org/k/#{chat_link[1:]}"
    if chat_link.lstrip("-").isdigit():
        return f"https://web.telegram.org/k/#{chat_link}"
    return f"https://web.telegram.org/k/#{chat_link}"


class BrowserTelegramPoller:
    def __init__(self):
        self._driver = None
        self._loaded_url = None

    def poll_messages(self, session: Session) -> List[TelegramMessage]:
        chat_link = SettingsRepository.get(session, "telegram_chat_link", None) or settings.TELEGRAM_CHAT_LINK
        target_url = normalize_telegram_web_url(chat_link)
        try:
            driver = self._get_driver(session)
            if self._loaded_url != target_url:
                telegram_logger.info(f"Opening Telegram Web chat in browser mode: {target_url}")
                driver.get(target_url)
                self._loaded_url = target_url

            if self._looks_like_login_page(driver.page_source):
                telegram_logger.warning("Telegram Web is waiting for login. Complete login in the browser window.")
                SystemEventRepository.log(
                    session,
                    level="warning",
                    source="telegram_browser",
                    message="Telegram browser mode is waiting for login in the Selenium Chrome window.",
                )
                return []

            time.sleep(2)
            messages = self._extract_messages(driver.page_source)
            if not messages:
                telegram_logger.debug("Browser mode found no visible Telegram messages yet.")
                return []

            chat_id = self._stable_chat_id(chat_link or target_url)
            new_db_messages: List[TelegramMessage] = []
            allow_replies = bool(SettingsRepository.get(session, "allow_reply_signals", False))

            for msg in messages:
                existing = TelegramMessageRepository.get_by_telegram_id(session, chat_id, msg.id)
                if existing:
                    continue

                db_msg = TelegramMessage(
                    chat_id=chat_id,
                    message_id=msg.id,
                    message_date=msg.date or datetime.utcnow(),
                    raw_text=msg.text,
                    is_reply=False,
                    is_forwarded=False,
                    is_edited=False,
                )

                should_ignore, reason = filter_message(msg, allow_reply_signals=allow_replies)
                if should_ignore:
                    db_msg.ignored = True
                    db_msg.ignore_reason = reason
                    db_msg.processed = True
                    telegram_logger.info(f"Browser message {msg.id} ignored. Reason: {reason}")

                saved_msg = TelegramMessageRepository.save(session, db_msg)
                new_db_messages.append(saved_msg)

            return new_db_messages
        except Exception as exc:
            telegram_logger.error(f"Error polling Telegram Web browser messages: {exc}", exc_info=True)
            SystemEventRepository.log(
                session,
                level="error",
                source="telegram_browser",
                message=f"Browser polling failed: {exc}",
            )
            self._reset_driver()
            return []

    def _get_driver(self, session: Session):
        if self._driver is not None:
            try:
                _ = self._driver.current_url
                return self._driver
            except WebDriverException:
                self._driver = None

        options = Options()
        options.add_argument(f"--user-data-dir={BROWSER_STORAGE_DIR.resolve()}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--start-maximized")

        headless = bool(SettingsRepository.get(session, "telegram_browser_headless", False))
        if headless:
            options.add_argument("--headless=new")

        try:
            from webdriver_manager.chrome import ChromeDriverManager

            driver_path = ChromeDriverManager(path=str(DRIVER_STORAGE_DIR)).install()
            self._driver = webdriver.Chrome(service=Service(driver_path), options=options)
        except Exception as exc:
            telegram_logger.warning(f"webdriver-manager failed, falling back to Selenium Manager: {exc}")
            self._driver = webdriver.Chrome(options=options)

        return self._driver

    def _reset_driver(self):
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
        self._driver = None
        self._loaded_url = None

    @staticmethod
    def _looks_like_login_page(html: str) -> bool:
        text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True).casefold()
        login_markers = (
            "log in to telegram",
            "scan qr code",
            "your phone number",
            "country code",
            "telegram web",
        )
        return any(marker in text for marker in login_markers) and "message" not in text[:500]

    @staticmethod
    def _extract_messages(html: str) -> List[BrowserMessage]:
        soup = BeautifulSoup(html or "", "html.parser")
        nodes = soup.select(".message, .Message, [data-message-id], [id^='message-']")
        if not nodes:
            nodes = soup.select(".bubble, .text-content, [class*='message']")

        messages: List[BrowserMessage] = []
        seen = set()
        for index, node in enumerate(nodes[-80:], start=1):
            text = node.get_text("\n", strip=True)
            text = BrowserTelegramPoller._clean_message_text(text)
            if len(text) < 3 or text in seen:
                continue
            seen.add(text)

            raw_id = (
                node.get("data-message-id")
                or node.get("data-mid")
                or node.get("id")
                or ""
            )
            message_id = BrowserTelegramPoller._message_id_from_raw(raw_id, text, index)
            messages.append(BrowserMessage(id=message_id, text=text, date=datetime.utcnow()))

        messages.sort(key=lambda item: item.id)
        return messages

    @staticmethod
    def _clean_message_text(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text or "")
        text = re.sub(r"[ \t]+", " ", text)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        noise = {"edited", "views", "reply", "forward"}
        filtered = [line for line in lines if line.casefold() not in noise]
        return "\n".join(filtered).strip()

    @staticmethod
    def _message_id_from_raw(raw_id: str, text: str, fallback_index: int) -> int:
        match = re.search(r"(\d+)", raw_id or "")
        if match:
            return int(match.group(1))
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        return int(digest[:12], 16) + fallback_index

    @staticmethod
    def _stable_chat_id(chat_link: str) -> int:
        digest = hashlib.sha1((chat_link or "telegram-browser").encode("utf-8")).hexdigest()
        return -int(digest[:12], 16)


browser_telegram_poller = BrowserTelegramPoller()
