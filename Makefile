# Self-Constrained-Control Development Makefile
# Usage: make [target]
# Run `make help` for available commands

.PHONY: help install fmt lint type test build clean all

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Install package with dev dependencies
	python -m pip install -e ".[dev]"

fmt: ## Format code with ruff
	ruff format .

lint: ## Lint code with ruff (with auto-fix)
	ruff check --fix .

type: ## Run mypy type checking on src/
	mypy src

test: ## Run tests with pytest and coverage
	pytest --cov=self_constrained_control --cov-fail-under=65

build: ## Build distribution package
	python -m build

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage

all: fmt lint type test ## Run all quality checks (format, lint, type, test)
	@echo "All checks passed!"

pre-commit: ## Run pre-commit on all files
	pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	pre-commit install
