import uvicorn

from .settings import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "telegram_mt5_copier.web:app",
        host=settings.web_host,
        port=settings.web_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
