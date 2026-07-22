import os
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "storage" / "selenium_telegram_profile"
DEFAULT_URL = "https://web.telegram.org/k/"


def main() -> None:
    load_dotenv(BASE_DIR / ".env")

    telegram_url = (
        os.getenv("TELEGRAM_SELENIUM_URL")
        or os.getenv("TELEGRAM_CHAT_LINK")
        or DEFAULT_URL
    ).strip()
    if telegram_url.startswith("-") or telegram_url.isdigit():
        telegram_url = DEFAULT_URL

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)
    driver.get(telegram_url)

    print("=" * 70)
    print("Telegram Web opened with Selenium.")
    print(f"URL: {telegram_url}")
    print(f"Saved browser session folder: {PROFILE_DIR}")
    print("Log in or scan QR once. The session should stay in this profile.")
    print("Press Enter here when you want this launcher to exit.")
    print("=" * 70)
    input()


if __name__ == "__main__":
    main()
