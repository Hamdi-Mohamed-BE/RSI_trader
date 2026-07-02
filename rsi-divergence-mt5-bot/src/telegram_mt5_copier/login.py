import asyncio

from .settings import load_settings


async def login() -> None:
    settings = load_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise SystemExit("Set TELEGRAM_API_ID and TELEGRAM_API_HASH on the Settings page first.")
    from telethon import TelegramClient

    settings.session_file.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(
        str(settings.session_file),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    await client.start(phone=settings.telegram_phone or None)
    me = await client.get_me()
    print(f"Telegram user API authorized as {getattr(me, 'username', None) or me.id}.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(login())
