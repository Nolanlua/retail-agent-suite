SHELL := /bin/bash
.PHONY: bootstrap up down seed test lint

bootstrap:
	uv sync --all-packages

up:
	docker compose -f deploy/docker-compose.yml up -d postgres redis qdrant opensearch neo4j

down:
	docker compose -f deploy/docker-compose.yml down -v

seed:
	uv run python scripts/seed_wiki.py

test:
	uv run pytest

lint:
	uv run ruff check .
