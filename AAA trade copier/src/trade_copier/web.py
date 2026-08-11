import uvicorn

from .config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "trade_copier.app:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    main()
