.PHONY: help build up down restart logs clean test test-unit test-property test-scenarios shell db-shell format lint

help:
	@echo "Granzion Lab - Available Commands"
	@echo "=================================="
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View logs (all services)"
	@echo "  make clean          - Remove all containers and volumes"
	@echo ""
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests"
	@echo "  make test-property  - Run property tests"
	@echo "  make test-scenarios - Run scenario tests"
	@echo ""
	@echo "  make shell          - Open shell in app container"
	@echo "  make db-shell       - Open PostgreSQL shell"
	@echo ""
	@echo "  make format         - Format code with black"
	@echo "  make lint           - Lint code with ruff"

build:
	docker compose build

up:
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Granzion Lab is starting!"
	@echo "  TUI: http://localhost:8000"
	@echo "  API: http://localhost:8001"
	@echo "  Keycloak: http://localhost:8080"
	@echo "  PuppyGraph: http://localhost:8082"

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

clean:
	docker compose down -v
	rm -rf logs/*.log

test:
	docker compose exec granzion-lab pytest tests/ -v

test-unit:
	docker compose exec granzion-lab pytest tests/unit/ -v

test-property:
	docker compose exec granzion-lab pytest tests/property/ -v

test-scenarios:
	docker compose exec granzion-lab pytest tests/scenarios/ -v

shell:
	docker compose exec granzion-lab /bin/bash

db-shell:
	docker compose exec postgres psql -U granzion -d granzion_lab

format:
	docker compose exec granzion-lab black src/ tests/

lint:
	docker compose exec granzion-lab ruff check src/ tests/
