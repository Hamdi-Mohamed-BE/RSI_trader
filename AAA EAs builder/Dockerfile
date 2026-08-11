FROM node:22-alpine AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY assets ./assets
COPY apps ./apps
COPY templates ./templates
COPY scripts/build-frontend.mjs ./scripts/build-frontend.mjs
RUN npm run assets:build

FROM python:3.13-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY --chown=app:app . .
COPY --from=frontend --chown=app:app /app/static/css/app.css /app/static/css/app.css
COPY --from=frontend --chown=app:app /app/static/js/app.js /app/static/js/app.js
COPY --from=frontend --chown=app:app /app/static/vendor /app/static/vendor

RUN mkdir -p /app/storage/files /app/staticfiles \
    && chown -R app:app /app/storage /app/staticfiles \
    && uv run python manage.py collectstatic --noinput --settings=config.settings.development

USER app
EXPOSE 8000
CMD ["uv", "run", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120"]
