.PHONY: setup web core admin test check css docker-up docker-down

setup:
	uv sync --extra dev
	npm install
	npm run build
	uv run aaa-trade-copier init-db
	uv run aaa-trade-copier seed-demo

web:
	uv run aaa-trade-copier-web

core:
	uv run aaa-trade-copier-core

admin:
	uv run aaa-trade-copier create-admin

test:
	uv run pytest -W error

check:
	uv run ruff check .
	uv run mypy src tests
	uv run pytest -W error

css:
	npm run build

docker-up:
	docker compose up --build

docker-down:
	docker compose down
