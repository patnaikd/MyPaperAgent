.PHONY: help install dev-install sync test test-cov lint format type-check clean init-db drop-db run

help:  ## Show this help message
	@echo "MyPaperAgent - Development Commands (using uv)"
	@echo "================================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies with uv
	uv pip install -e .

dev-install:  ## Install development dependencies with uv
	uv pip install -e ".[dev]"

sync:  ## Sync dependencies from pyproject.toml (recommended)
	uv sync --all-extras

lock:  ## Update uv.lock file
	uv lock

test:  ## Run tests
	uv run pytest

test-cov:  ## Run tests with coverage report
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html tests/

test-fast:  ## Run fast tests only (skip slow/integration tests)
	uv run pytest -m "not slow"

lint:  ## Run linting checks
	uv run ruff check src/ tests/

format:  ## Format code with black
	uv run black src/ tests/

format-check:  ## Check code formatting without making changes
	uv run black --check src/ tests/

type-check:  ## Run type checking with mypy
	uv run mypy src/

check-all: format-check lint type-check  ## Run all code quality checks

init-db:  ## Initialize the database
	uv run python -m src.utils.database init

drop-db:  ## Drop all database tables (use with caution!)
	uv run python -m src.utils.database drop

clean:  ## Clean up generated files and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .uv_cache 2>/dev/null || true
	@echo "Cleaned up all cache and generated files"

run:  ## Run the CLI (use: make run ARGS="command args")
	uv run python -m src.cli $(ARGS)

config:  ## Show current configuration
	uv run python -m src.cli config

# Example usage commands
example-add:  ## Example: Add a paper
	@echo "Usage: make run ARGS='add-paper path/to/paper.pdf'"
	@echo "   or: make run ARGS='add-paper https://arxiv.org/abs/2301.00001'"

example-search:  ## Example: Search papers
	@echo "Usage: make run ARGS='search \"your search query\"'"

example-summarize:  ## Example: Summarize a paper
	@echo "Usage: make run ARGS='summarize <paper_id>'"

setup: sync init-db  ## Complete setup (sync deps + init database)
	@echo "Setup complete! Don't forget to:"
	@echo "1. Copy .env.example to .env"
	@echo "2. Add your API keys to .env"
	@echo "3. You're ready to go! Use 'make run' to execute commands"

dev-setup: sync init-db  ## Complete development setup
	@echo "Development setup complete!"
	@echo "Run 'make test' to verify everything works"

# uv-specific commands
uv-upgrade:  ## Upgrade uv to latest version
	pip install --upgrade uv

uv-tree:  ## Show dependency tree
	uv tree

uv-outdated:  ## Check for outdated dependencies
	uv pip list --outdated

# Demo and examples
demo-pdf:  ## Run PDF extraction demo
	uv run python tests/demo_pdf_extraction.py
