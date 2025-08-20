# AnimeSorter Development Makefile
# Compatible with Unix-like systems (Linux, macOS)

.PHONY: help install test lint format type-check clean build dev docker-build docker-test docker-dev setup pre-commit security

# Default target
help: ## Show this help
	@echo "AnimeSorter Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Environment setup
setup: ## Set up development environment
	@echo "🔧 Setting up development environment..."
	python -m pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install
	@echo "✅ Development environment ready!"

install: ## Install package and dependencies
	@echo "📦 Installing package..."
	pip install -e ".[dev]"

# Code quality
lint: ## Run ruff linter
	@echo "🔍 Running ruff linter..."
	ruff check src/ tests/

lint-fix: ## Run ruff linter with fixes
	@echo "🔧 Running ruff linter with fixes..."
	ruff check src/ tests/ --fix

format: ## Format code with black
	@echo "🎨 Formatting code with black..."
	black src/ tests/

format-check: ## Check code formatting
	@echo "🎨 Checking code formatting..."
	black --check src/ tests/

type-check: ## Run mypy type checker
	@echo "🔍 Running mypy type checker..."
	mypy src/ --config-file=pyproject.toml

# Testing
test: ## Run tests
	@echo "🧪 Running tests..."
	pytest tests/ -v

test-cov: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	pytest tests/ \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-fail-under=70 \
		-v

test-fast: ## Run tests (excluding slow tests)
	@echo "⚡ Running fast tests..."
	pytest tests/ -v -m "not slow"

test-integration: ## Run integration tests
	@echo "🔗 Running integration tests..."
	pytest tests/ -v -m "integration"

# Security
security: ## Run security checks
	@echo "🔒 Running security checks..."
	bandit -r src/ -f json -o bandit-report.json || true
	safety check --json --output safety-report.json || true
	@echo "📄 Security reports generated: bandit-report.json, safety-report.json"

# Pre-commit
pre-commit: ## Run pre-commit hooks
	@echo "🪝 Running pre-commit hooks..."
	pre-commit run --all-files

# Build and packaging
build: ## Build package
	@echo "📦 Building package..."
	python -m build

build-exe: ## Build executable with PyInstaller
	@echo "🔨 Building executable..."
	pyinstaller --onefile \
		--windowed \
		--name "AnimeSorter" \
		--add-data "resources/*:resources" \
		--hidden-import PyQt5.QtWidgets \
		--hidden-import PyQt5.QtCore \
		--hidden-import PyQt5.QtGui \
		--hidden-import tmdbsimple \
		--hidden-import anitopy \
		--hidden-import guessit \
		src/main.py

# Development
dev: ## Run development server
	@echo "🚀 Starting development mode..."
	python -m src.main

debug: ## Run with debug logging
	@echo "🐛 Starting debug mode..."
	ANIMESORTER_LOG_LEVEL=DEBUG python -m src.main

# Docker
docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t animesorter:latest .

docker-build-dev: ## Build Docker development image
	@echo "🐳 Building Docker development image..."
	docker build --target builder -t animesorter:dev .

docker-test: ## Run tests in Docker
	@echo "🐳 Running tests in Docker..."
	docker-compose --profile test up --build --abort-on-container-exit

docker-dev: ## Start development environment in Docker
	@echo "🐳 Starting development environment in Docker..."
	docker-compose --profile dev up --build

docker-clean: ## Clean Docker images and containers
	@echo "🧹 Cleaning Docker resources..."
	docker-compose down -v
	docker system prune -f

# Cleanup
clean: ## Clean build artifacts
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true

clean-logs: ## Clean log files
	@echo "🧹 Cleaning log files..."
	rm -rf logs/
	rm -rf *.log

# All-in-one commands
check: lint format-check type-check ## Run all code quality checks
	@echo "✅ All code quality checks passed!"

test-all: test-cov security ## Run all tests and security checks
	@echo "✅ All tests and security checks completed!"

ci: check test-all ## Run CI pipeline locally
	@echo "✅ CI pipeline completed successfully!"

# Release
bump-version: ## Bump version (requires bump2version)
	@echo "📈 Bumping version..."
	bump2version patch

release: bump-version build ## Prepare release
	@echo "🚀 Release prepared! Remember to push tags and create GitHub release."

# Documentation
docs: ## Generate documentation (placeholder)
	@echo "📚 Documentation generation not yet implemented"

# Database/Cache cleanup (for future use)
clean-cache: ## Clean application cache
	@echo "🧹 Cleaning application cache..."
	rm -rf .cache/
	rm -rf ~/.cache/animesorter/ 2>/dev/null || true
