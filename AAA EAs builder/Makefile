.DEFAULT_GOAL := help

.PHONY: help install assets css css-watch dev worker test test-cov lint format typecheck check migrate migration superuser seed sync-ai docker-up docker-down docker-logs docker-test clean

help:
	@echo "AAA EAs Builder commands"
	@echo "  make install       Install Python and frontend dependencies"
	@echo "  make dev           Start the Django development server"
	@echo "  make worker        Start the Celery worker"
	@echo "  make css-watch     Watch and rebuild Tailwind CSS"
	@echo "  make check         Run lint, Django checks, and tests"
	@echo "  make sync-ai       Sync the default Gemini gateway and model"
	@echo "  make docker-up     Build and start the Docker stack"

install:
	uv sync
	npm ci

assets:
	npm run assets:build

css:
	npm run css:build

css-watch:
	npm run css:watch

dev: sync-ai
	uv run python manage.py runserver

worker:
	uv run celery -A config worker --loglevel=INFO

test:
	uv run pytest

test-cov:
	uv run pytest --cov --cov-report=term-missing

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy apps config

check: lint typecheck
	uv run python manage.py check
	uv run pytest

migrate:
	uv run python manage.py migrate

migration:
	uv run python manage.py makemigrations

superuser:
	uv run python manage.py createsuperuser

seed:
	uv run python manage.py seed_demo

sync-ai:
	uv run python manage.py sync_llm_config

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f web worker

docker-test:
	docker compose run --rm web uv run pytest

clean:
	uv run python -c "from pathlib import Path; [p.unlink() for p in Path('.').rglob('*.pyc') if p.is_file()]"
