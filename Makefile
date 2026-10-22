# FinWise ML Platform — Development Commands
# Usage: make <target>

.PHONY: help dev backend frontend test lint format security migrate seed docker-up docker-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === Development ===

dev: ## Start backend + frontend in parallel
	$(MAKE) -j2 backend frontend

backend: ## Start Flask backend server
	cd backend && python app_v2_secure.py

frontend: ## Start Next.js frontend dev server
	cd frontend && npm run dev

# === Testing ===

test: ## Run all tests with coverage
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-unit: ## Run only unit tests
	cd backend && python -m pytest tests/ -v -m unit

test-integration: ## Run only integration tests
	cd backend && python -m pytest tests/ -v -m integration

# === Code Quality ===

lint: ## Run all linters
	cd backend && python -m ruff check .
	cd frontend && npm run lint

format: ## Auto-format code
	cd backend && python -m black .
	cd backend && python -m ruff check --fix .

security: ## Run security scans
	cd backend && python -m bandit -r . -ll
	cd backend && safety check

typecheck: ## Run type checking
	cd backend && python -m mypy app/
	cd frontend && npx tsc --noEmit

# === Database ===

migrate: ## Run database migrations
	cd backend && python -m alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	cd backend && python -m alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Rollback last migration
	cd backend && python -m alembic downgrade -1

# === Docker ===

docker-up: ## Start production Docker stack
	docker-compose -f docker-compose.production.yml up -d

docker-down: ## Stop Docker stack
	docker-compose -f docker-compose.production.yml down

docker-dev: ## Start local development Docker stack
	docker-compose -f docker-compose.local.yml up -d

docker-logs: ## View Docker logs
	docker-compose -f docker-compose.production.yml logs -f

# === Fairness ===

fairness-check: ## Run fairness analysis
	cd backend && python -m scripts.run_fairness_check

# === Cleanup ===

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage
	rm -rf frontend/.next frontend/out

# === Installation ===

install: ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

install-dev: ## Install development dependencies
	cd backend && pip install -r requirements-dev.txt
	cd frontend && npm install
