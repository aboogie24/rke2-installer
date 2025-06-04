.PHONY: help test test-unit test-e2e test-integration test-performance lint format coverage clean install-dev setup-test-env

# Default target
help:
	@echo "Available targets:"
	@echo "  setup-test-env     - Set up test environment"
	@echo "  install-dev        - Install development dependencies"
	@echo "  test               - Run all tests"
	@echo "  test-unit          - Run unit tests only"
	@echo "  test-e2e           - Run end-to-end tests"
	@echo "  test-integration   - Run integration tests (requires Docker)"
	@echo "  test-performance   - Run performance tests"
	@echo "  lint               - Run code linting"
	@echo "  format             - Format code"
	@echo "  coverage           - Generate test coverage report"
	@echo "  clean              - Clean up test artifacts"

# Variables
PYTHON := python3
PIP := pip3
PYTEST := pytest
PYTEST_ARGS := -v --tb=short
COVERAGE_MIN := 80

# Setup test environment
setup-test-env:
	@echo "Setting up test environment..."
	$(PYTHON) -m venv venv-test
	./venv-test/bin/pip install --upgrade pip
	./venv-test/bin/pip install -r requirements-test.txt
	@echo "Test environment ready. Activate with: source venv-test/bin/activate"

# Install development dependencies
install-dev:
	$(PIP) install -r requirements-test.txt
	$(PIP) install -e .

# Run all tests
test: 
	@echo "Running all tests..."
	PYTHONPATH=. $(PYTEST) $(PYTEST_ARGS) tests/

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	PYTHONPATH=. $(PYTEST) $(PYTEST_ARGS) tests/unit/ \
		--cov=deploy \
		--cov=main \
		--cov-report=term-missing \
		--junit-xml=test-results/unit-tests.xml

# Run end-to-end tests
test-e2e:
	@echo "Running end-to-end tests..."
	PYTHONPATH=. $(PYTEST) $(PYTEST_ARGS) tests/e2e/ \
		--junit-xml=test-results/e2e-tests.xml

# Run integration tests (requires Docker)
test-integration:
	@echo "Running integration tests..."
	@which docker > /dev/null || (echo "Docker is required for integration tests" && exit 1)
	$(PYTEST) $(PYTEST_ARGS) tests/e2e/ -m integration \
		--junit-xml=test-results/integration-tests.xml

# Run performance tests
test-performance:
	@echo "Running performance tests..."
	$(PYTEST) $(PYTEST_ARGS) tests/e2e/ -m slow \
		--junit-xml=test-results/performance-tests.xml

# Run specific test file
test-file:
	@if [ -z "$(FILE)" ]; then echo "Usage: make test-file FILE=path/to/test_file.py"; exit 1; fi
	$(PYTEST) $(PYTEST_ARGS) $(FILE)

# Lint code
lint:
	@echo "Running code linting..."
	flake8 main.py deploy/ tests/ --max-line-length=120 --ignore=E501,W503
	pylint main.py deploy/ --disable=C0103,R0903,R0913,W0613
	mypy main.py deploy/ --ignore-missing-imports

# Format code
format:
	@echo "Formatting code..."
	black main.py deploy/ tests/ --line-length=120
	isort main.py deploy/ tests/ --profile black

# Generate coverage report
coverage:
	@echo "Generating coverage report..."
	$(PYTEST) tests/ --cov=deploy --cov=main \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-report=term-missing \
		--cov-fail-under=$(COVERAGE_MIN)
	@echo "Coverage report generated in htmlcov/"

# Clean up test artifacts
clean:
	@echo "Cleaning up test artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf test-results/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	rm -rf venv-test/

# Create test results directory
test-results:
	mkdir -p test-results

# Run tests with specific markers
test-smoke: test-results
	@echo "Running smoke tests..."
	$(PYTEST) $(PYTEST_ARGS) tests/ -m "not slow and not integration" \
		--junit-xml=test-results/smoke-tests.xml

# Run tests for CI/CD
test-ci: test-results
	@echo "Running CI tests..."
	$(PYTEST) tests/unit/ tests/e2e/ \
		--cov=deploy --cov=main \
		--cov-report=xml:coverage.xml \
		--junit-xml=test-results/ci-tests.xml \
		-m "not slow and not integration" \
		--maxfail=5

# Watch tests (requires pytest-watch)
test-watch:
	ptw tests/ -- $(PYTEST_ARGS)