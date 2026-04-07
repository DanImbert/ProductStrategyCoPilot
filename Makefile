.PHONY: help check-python install dev run test lint format clean benchmark benchmark-local regression docker-build docker-run

PYTHON ?= python3
PIP := $(PYTHON) -m pip

help:
	@echo "Product Strategy Copilot - Available commands:"
	@echo "  make install       - Install runtime dependencies"
	@echo "  make dev           - Install with dev dependencies"
	@echo "  make run           - Run the API server locally"
	@echo "  make test          - Run tests with coverage"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo "  make benchmark     - Run the 10-case benchmark in zero-cost mock mode"
	@echo "  make benchmark-local - Run the benchmark against a free local OpenAI-compatible model"
	@echo "  make regression   - Run the fixed prompt regression suite"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run Docker container"

check-python:
	@$(PYTHON) -c "import sys; raise SystemExit('Python 3.10+ is required for this project.') if sys.version_info < (3, 10) else None"

install: check-python
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements.txt

dev: check-python
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -r requirements-dev.txt

run: check-python
	$(PYTHON) -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test: check-python
	$(PYTHON) -m pytest tests/ -v --cov=src --cov-report=term-missing

lint: check-python
	$(PYTHON) -m ruff check src/ tests/
	$(PYTHON) -m mypy src/

format: check-python
	$(PYTHON) -m black src/ tests/ scripts/

benchmark: check-python
	$(PYTHON) -m scripts.benchmark --provider mock

benchmark-local: check-python
	$(PYTHON) -m scripts.benchmark --provider local

regression: check-python
	$(PYTHON) -m scripts.prompt_regression --provider mock

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info

docker-build:
	docker build -t product-strategy-copilot:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env product-strategy-copilot:latest
