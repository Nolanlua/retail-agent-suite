SHELL := /bin/bash
.PHONY: bootstrap infra-up infra-down test lint

bootstrap:
	uv sync --all-packages

infra-up:
	docker compose -f deploy/docker-compose.yml up -d postgres redis

infra-down:
	docker compose -f deploy/docker-compose.yml down -v

test:
	uv run pytest

lint:
	uv run ruff check .
