.PHONY: help install start stop clean init test logs

# Default target
help:
	@echo "Game Master V3 - Development Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  install     - Install Python dependencies in virtual environment"
	@echo "  start       - Start all services with Docker Compose"
	@echo "  stop        - Stop all services"
	@echo "  clean       - Stop services and remove volumes"
	@echo "  init        - Initialize databases with sample data"
	@echo "  test        - Run tests"
	@echo "  logs        - Show logs from all services"
	@echo "  api         - Start only the API service (for development)"
	@echo "  api-direct  - Start API with direct uvicorn (better Ctrl+C handling)"
	@echo "  api-env     - Start API with explicit .env loading"
	@echo "  kill-api    - Force stop any running API processes on port 8000"
	@echo "  restart-api - Restart the API service (kill + start)"
	@echo "  shell       - Open shell in the API container"
	@echo "  activate    - Show how to activate virtual environment"
	@echo "  demo-ai     - Run AI features demo (requires OpenAI API key)"
	@echo "  test-api    - Run only API tests"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-fast   - Run tests with fail-fast and last-failed"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint        - Run all linting checks"
	@echo "  format      - Format code with black and isort"
	@echo "  type-check  - Run mypy type checking"

# Install Python dependencies
install:
	python3 -m venv venv || true
	./venv/bin/pip install --upgrade pip setuptools wheel
	./venv/bin/pip install -r requirements.txt

# Start all services
start:
	docker-compose -f docker/docker-compose.yml up -d
	@echo "Services starting... Check logs with 'make logs'"
	@echo "API will be available at http://localhost:8000"
	@echo "Neo4j Browser: http://localhost:7474 (neo4j/gamemaster123)"
	@echo "Qdrant Dashboard: http://localhost:6333/dashboard"
	@echo "Grafana: http://localhost:3000 (admin/admin)"

# Stop all services
stop:
	docker-compose -f docker/docker-compose.yml down

# Clean everything (including volumes)
clean:
	docker-compose -f docker/docker-compose.yml down -v
	docker system prune -f

# Initialize databases
init:
	@echo "Waiting for databases to be ready..."
	sleep 10
	@if [ -f .env ]; then \
		export $$(grep -v '^#' .env | xargs) && PYTHONPATH=. ./venv/bin/python scripts/init_databases.py; \
	else \
		PYTHONPATH=. ./venv/bin/python scripts/init_databases.py; \
	fi

# Run the FastAPI application locally (for development)
api:
	@if [ -f .env ]; then \
		echo "Loading environment variables from .env file..."; \
		export $$(grep -v '^#' .env | xargs) && cd src && PYTHONPATH=.. ../venv/bin/python main.py; \
	else \
		echo "No .env file found, running with system environment..."; \
		cd src && PYTHONPATH=.. ../venv/bin/python main.py; \
	fi

# Alternative API start with direct uvicorn (better signal handling)
api-direct:
	@if [ -f .env ]; then \
		echo "Loading environment variables from .env file..."; \
		export $$(grep -v '^#' .env | xargs) && cd src && PYTHONPATH=.. ../venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info; \
	else \
		echo "No .env file found, running with system environment..."; \
		cd src && PYTHONPATH=.. ../venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info; \
	fi

# Start API with python-dotenv for explicit .env loading
api-env:
	cd src && PYTHONPATH=.. ../venv/bin/python -c "from dotenv import load_dotenv; load_dotenv('../.env'); import main"

# Force stop any running API processes
kill-api:
	@echo "Stopping any running API processes on port 8000..."
	@if lsof -i :8000 > /dev/null 2>&1; then \
		echo "Found processes on port 8000, killing them..."; \
		lsof -ti :8000 | xargs kill -9; \
		echo "✅ Processes stopped"; \
	else \
		echo "No processes found on port 8000"; \
	fi

# Restart API service (kill existing + start new)
restart-api: kill-api
	@echo "Starting API server..."
	@sleep 2
	$(MAKE) api

# Test Commands
test:
	PYTHONPATH=src ./venv/bin/pytest src/tests/ -v

test-unit:
	PYTHONPATH=src ./venv/bin/pytest src/tests/ -v -m "unit"

test-integration:
	PYTHONPATH=src ./venv/bin/pytest src/tests/ -v -m "integration"

test-api:
	PYTHONPATH=src ./venv/bin/pytest src/tests/ -v -m "api"

test-coverage:
	PYTHONPATH=src ./venv/bin/pytest src/tests/ --cov=src --cov-report=html --cov-report=term-missing

test-fast:
	PYTHONPATH=src ./venv/bin/pytest src/tests/ -v -x --ff

test-parallel:
	PYTHONPATH=src ./venv/bin/pytest src/tests/ -v -n auto

# Show logs
logs:
	docker-compose -f docker/docker-compose.yml logs -f

# Show logs for specific service
logs-%:
	docker-compose -f docker/docker-compose.yml logs -f $*

# Open shell in container
shell:
	docker-compose -f docker/docker-compose.yml exec gamemaster-api bash

# Development workflow - start everything and initialize
dev: start
	@echo "Waiting for services to start..."
	sleep 15
	$(MAKE) init
	@echo ""
	@echo "🚀 Game Master V3 is ready!"
	@echo "   API: http://localhost:8000"
	@echo "   Docs: http://localhost:8000/docs"
	@echo "   Health: http://localhost:8000/health"

# Full reset - clean and restart everything
reset: clean start
	sleep 15
	$(MAKE) init

# Status check
status:
	docker-compose -f docker/docker-compose.yml ps

# Show how to activate virtual environment
activate:
	@echo "To activate the virtual environment, run:"
	@echo "  source venv/bin/activate"
	@echo ""
	@echo "To deactivate, run:"
	@echo "  deactivate"

# Run AI features demo
demo-ai:
	@echo "Running AI features demo..."
	@echo "Note: Requires OPENAI_API_KEY environment variable"
	@if [ -f .env ]; then \
		export $$(grep -v '^#' .env | xargs) && PYTHONPATH=. ./venv/bin/python example_ai_usage.py; \
	else \
		PYTHONPATH=. ./venv/bin/python example_ai_usage.py; \
	fi

# Code Quality Commands
format:
	./venv/bin/black src/
	./venv/bin/isort src/

lint:
	./venv/bin/flake8 src/
	./venv/bin/black --check src/
	./venv/bin/isort --check-only src/

type-check:
	./venv/bin/mypy src/ --ignore-missing-imports

quality: format lint type-check

# Pre-commit setup
pre-commit-install:
	./venv/bin/pre-commit install

pre-commit-run:
	./venv/bin/pre-commit run --all-files

# CI/CD simulation
ci: install quality test-coverage
	@echo "✅ All CI checks passed!"