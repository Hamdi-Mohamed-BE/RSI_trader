from pathlib import Path
from getpass import getpass
import asyncio
import os
from telethon import TelegramClient
from telethon.errors import (
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession
from app.core.config import settings
from app.core.logging import telegram_logger

# Store sessions inside storage/sessions
SESSION_DIR = Path("storage/sessions")
SESSION_DIR.mkdir(parents=True, exist_ok=True)
QR_PATH = SESSION_DIR / "telegram_login_qr.png"

class TelegramClientWrapper:
    def __init__(self):
        self.client: TelegramClient | None = None
        self._fingerprint: tuple | None = None
        
    async def get_client(
        self,
        api_id: int | None = None,
        api_hash: str | None = None,
        bot_token: str | None = None,
        mode: str | None = None,
        session_string: str | None = None,
    ) -> TelegramClient:
        """Returns initialized TelegramClient, authenticating if necessary."""
        api_id = int(api_id or settings.TELEGRAM_API_ID)
        api_hash = api_hash or settings.TELEGRAM_API_HASH
        bot_token = bot_token if bot_token is not None else settings.TELEGRAM_BOT_TOKEN
        mode = (mode or settings.TELEGRAM_MODE or "bot").strip().lower()
        session_string = session_string if session_string is not None else settings.TELEGRAM_SESSION_STRING
        fingerprint = (api_id, api_hash, bot_token if mode == "bot" else session_string, mode)

        if self.client is not None and self.client.is_connected() and self._fingerprint == fingerprint:
            return self.client

        if self.client is not None:
            await self.disconnect()
            
        telegram_logger.info(f"Initializing Telethon client in {mode.upper()} mode...")
        session = (
            StringSession(session_string)
            if mode == "user" and session_string
            else str(SESSION_DIR / ("copier_user_session" if mode == "user" else "copier_bot_session"))
        )
        self.client = TelegramClient(
            session,
            api_id,
            api_hash,
        )
        self._fingerprint = fingerprint
        
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            if mode == "bot":
                telegram_logger.info("Bot is not authorized. Logging in using token...")
                if not bot_token:
                    raise ValueError("TELEGRAM_BOT_TOKEN is missing in config.")
                await self.client.start(bot_token=bot_token)
                telegram_logger.info("Bot authentication successful.")
            elif mode == "user":
                telegram_logger.info("User session is not authorized. Complete the login prompts in this window.")
                await self._login_user_interactive(self.client)
                telegram_logger.info("User authentication successful.")
            else:
                raise ValueError("TELEGRAM_MODE must be 'bot' or 'user'.")
        else:
            telegram_logger.info(f"{mode.title()} session is already authorized.")
            
        return self.client

    async def disconnect(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            telegram_logger.info("Disconnected Telegram client.")
            self.client = None
            self._fingerprint = None

    async def _login_user_interactive(self, client: TelegramClient) -> None:
        """Interactive Telegram user login. QR is tried first; phone-code remains as fallback."""
        if await self._try_qr_login(client):
            return

        print("QR login was not completed. Falling back to phone code login.")
        await self._login_user_by_phone_code(client)

    async def _try_qr_login(self, client: TelegramClient) -> bool:
        try:
            import qrcode
        except Exception as exc:
            telegram_logger.warning(f"QR package is not available; falling back to phone code login: {exc}")
            return False

        for attempt in range(1, 3):
            qr_login = await client.qr_login()
            img = qrcode.make(qr_login.url)
            img.save(QR_PATH)

            print("")
            print("Telegram QR login is ready.")
            print(f"Open this QR image and scan it from Telegram mobile: {QR_PATH.resolve()}")
            print("Telegram app: Settings > Devices > Link Desktop Device.")
            print("Waiting for QR scan...")
            telegram_logger.info(f"Telegram QR login image generated at {QR_PATH.resolve()} (attempt {attempt}/2).")

            try:
                os.startfile(QR_PATH)
            except Exception:
                pass

            try:
                await qr_login.wait(timeout=60)
                return True
            except asyncio.TimeoutError:
                telegram_logger.warning("Telegram QR login expired before it was scanned.")
                print("QR expired before scan. Creating a fresh QR...")
            except SessionPasswordNeededError:
                password = getpass("Telegram 2FA password: ")
                await client.sign_in(password=password)
                return True
            except Exception as exc:
                telegram_logger.warning(f"Telegram QR login failed: {exc}")
                print(f"QR login failed: {exc}")
                return False

        return False

    async def _login_user_by_phone_code(self, client: TelegramClient) -> None:
        """Phone-code login that preserves phone_code_hash across retries."""
        while True:
            phone = input("Please enter your phone number with country code, e.g. +216...: ").strip()
            if phone:
                break

        sent_code = await client.send_code_request(phone)
        phone_code_hash = sent_code.phone_code_hash

        while True:
            code = input("Please enter the code you received: ").strip().replace(" ", "")
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
                return
            except PhoneCodeInvalidError:
                telegram_logger.warning("Invalid Telegram code. Check the latest code and try again.")
                print("Invalid code. Please enter the newest Telegram code exactly as received.")
            except PhoneCodeExpiredError:
                telegram_logger.warning("Telegram code expired. Requesting a fresh code.")
                print("Code expired. Sending a fresh code now...")
                sent_code = await client.send_code_request(phone, force_sms=False)
                phone_code_hash = sent_code.phone_code_hash
            except SessionPasswordNeededError:
                password = getpass("Telegram 2FA password: ")
                await client.sign_in(password=password)
                return

# Global client wrapper instance
telegram_client_wrapper = TelegramClientWrapper()
