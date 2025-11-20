SHELL := /bin/bash

.PHONY: dev-up dev-down logs test lint fmt

DEV ?= 1

dev-up:
	docker compose up --build -d

dev-down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

# Backend tests + linters
lint:
	docker compose exec api ruff check . || true
	docker compose exec api mypy app || true
	docker compose exec frontend npm run lint || true

fmt:
	docker compose exec api ruff check --fix . || true
	docker compose exec frontend npm run format || true

test:
	docker compose exec api pytest -q || true
