import uvicorn

from yt_stream_copy.config import settings


if __name__ == "__main__":
    uvicorn.run("yt_stream_copy.app:app", host=settings.host, port=settings.port, reload=False)

