SHELL := /bin/bash
.PHONY: bootstrap data features up down test lint

bootstrap:
	uv sync --all-packages

data:
	uv run python data/generate_retail.py

features:
	uv run python scripts/seed_features.py

up:
	docker compose -f deploy/docker-compose.yml up -d mysql order-service

down:
	docker compose -f deploy/docker-compose.yml down -v

test:
	uv run pytest

lint:
	uv run ruff check .
