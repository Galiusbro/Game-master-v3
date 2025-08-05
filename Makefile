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
	PYTHONPATH=. ./venv/bin/python scripts/init_databases.py

# Run the FastAPI application locally (for development)
api:
	cd src && PYTHONPATH=.. ../venv/bin/python main.py

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
	PYTHONPATH=. ./venv/bin/python example_ai_usage.py

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