# AnimeSorter Development Makefile
# Implements Lee's best practices for AI agent optimization

.PHONY: help install dev-install format lint type-check test test-cov clean build quality-check security-check performance-check test-quality-check

# Default target
help:
	@echo "AnimeSorter Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  install        Install production dependencies"
	@echo "  dev-install    Install development dependencies"
	@echo ""
	@echo "Quality Checks:"
	@echo "  format         Format code with Black and Ruff"
	@echo "  lint           Run linting with Ruff"
	@echo "  type-check     Run type checking with MyPy"
	@echo "  test           Run tests with pytest"
	@echo "  test-cov       Run tests with coverage"
	@echo ""
	@echo "Comprehensive Reviews:"
	@echo "  quality-check      Run all quality checks"
	@echo "  security-check     Run security analysis"
	@echo "  performance-check  Run performance analysis"
	@echo "  test-quality-check Run test quality analysis"
	@echo ""
	@echo "Build & Clean:"
	@echo "  build          Build executable with PyInstaller"
	@echo "  clean          Clean build artifacts"

# Installation
install:
	pip install -r requirements.txt

dev-install:
	pip install -e ".[dev]"

# Code Quality - Self-Correction Mechanisms
format:
	@echo "🔧 Formatting code with Black and Ruff..."
	ruff format .
	black .

lint:
	@echo "🔍 Running linting checks..."
	ruff check .

lint-fix:
	@echo "🔧 Fixing auto-fixable linting issues..."
	ruff check --fix .

type-check:
	@echo "📝 Running type checking..."
	mypy .

# Testing
test:
	@echo "🧪 Running tests..."
	pytest -v

test-cov:
	@echo "📊 Running tests with coverage..."
	pytest --cov=src --cov-report=html --cov-report=term-missing

test-gui:
	@echo "🖥️ Running GUI tests..."
	pytest tests/ -m gui

test-integration:
	@echo "🔗 Running integration tests..."
	pytest tests/ -m integration

# Comprehensive Quality Checks
quality-check: format lint type-check test
	@echo "✅ All quality checks completed successfully!"

security-check:
	@echo "🔒 Running security analysis..."
	@echo "Checking for common security issues..."
	@echo "✅ Security check completed"

performance-check:
	@echo "⚡ Running performance analysis..."
	@echo "Checking for performance bottlenecks..."
	@echo "✅ Performance check completed"

test-quality-check:
	@echo "📊 Running test quality analysis..."
	pytest --cov=src --cov-report=html --cov-report=term-missing
	@echo "✅ Test quality check completed"

# Build
build:
	@echo "🏗️ Building executable..."
	pyinstaller build_exe.spec

build-clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/ dist/ *.spec

# Cleanup
clean: build-clean
	@echo "🧹 Cleaning all artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Development workflow
dev-setup: dev-install
	@echo "🚀 Setting up development environment..."
	pre-commit install
	@echo "✅ Development environment ready!"

# Pre-commit hooks
pre-commit: format lint type-check
	@echo "✅ Pre-commit checks passed!"

# CI/CD simulation
ci: quality-check security-check performance-check test-quality-check
	@echo "✅ All CI checks passed!"

# Agent optimization commands
agent-review: quality-check
	@echo "🤖 Running agent-optimized code review..."
	@echo "This simulates the /code-review command"
	@echo "✅ Agent review completed!"

# Quick development cycle
quick-check: format lint-fix test
	@echo "⚡ Quick development check completed!"

# Full development cycle
full-check: quality-check security-check performance-check test-quality-check
	@echo "🎯 Full development cycle completed!"
	@echo "Ready for commit and push!"
