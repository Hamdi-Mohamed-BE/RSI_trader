FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY config.docker.example.yaml ./config.docker.example.yaml
COPY docker/bot-entrypoint.sh /usr/local/bin/bot-entrypoint

RUN chmod +x /usr/local/bin/bot-entrypoint \
    && uv sync --frozen --no-dev

EXPOSE 8787

CMD ["bot-entrypoint"]
