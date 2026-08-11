FROM node:24-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY assets ./assets
COPY src/trade_copier/templates ./src/trade_copier/templates
RUN npm run build

FROM python:3.13-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.11.9 /uv /uvx /bin/
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev
COPY src ./src
COPY --from=assets /app/src/trade_copier/static/css/app.css ./src/trade_copier/static/css/app.css
RUN mkdir -p /app/storage
ENV PATH="/app/.venv/bin:$PATH"
CMD ["aaa-trade-copier-web"]
