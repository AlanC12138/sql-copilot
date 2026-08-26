# SQL Copilot — Common Commands
# Run `make help` to see all available commands.

.PHONY: help start stop seed dev test eval seed-bench eval-bench

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

start: ## Start Postgres instances (demo DB on 5432, app DB on 5433)
	docker compose up -d postgres app_db

stop: ## Stop all Postgres instances
	docker compose stop postgres app_db

seed: ## Seed the demo dataset and read-only role
	cd backend && poetry run python scripts/seed_demo_db.py

dev: ## Run the backend locally with hot reload
	cd backend && poetry run uvicorn app.main:app --reload

test: ## Run backend unit tests
	cd backend && poetry run pytest

eval: ## Run the NL->SQL benchmark against the live agent
	cd backend && poetry run python scripts/run_eval.py

seed-bench: ## Seed the 220-table noisy benchmark database
	cd backend && poetry run python scripts/seed_bench_db.py

eval-bench: ## Run the benchmark against the noisy 220-table schema (schema-discovery stress test)
	cd backend && poetry run python scripts/run_eval.py --target bench

.DEFAULT_GOAL := help
