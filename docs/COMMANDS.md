# MyPaperAgent Commands Reference

Quick reference for common development and usage commands with `uv`.

## Setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# Or: pip install uv

# Sync all dependencies (creates venv automatically)
uv sync --all-extras

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Initialize database
uv run python -m src.utils.database init
```

## Running the Application

### Web UI (Streamlit)

```bash
# Launch web interface (recommended)
python run_ui.py

# Or directly with uv
uv run streamlit run src/ui/app.py
```

### CLI Commands

```bash
# Add a paper
uv run python -m src.cli add-paper path/to/paper.pdf
uv run python -m src.cli add-paper https://arxiv.org/abs/2301.00001

# List papers
uv run python -m src.cli list
uv run python -m src.cli list --status reading

# Summarize a paper
uv run python -m src.cli summarize <paper_id>
uv run python -m src.cli summarize <paper_id> --level detailed

# Ask questions
uv run python -m src.cli ask <paper_id> "What is the main contribution?"

# Generate quiz
uv run python -m src.cli quiz <paper_id>
uv run python -m src.cli quiz <paper_id> --length 10 --difficulty hard

# Search papers
uv run python -m src.cli search "transformer architecture"

# Discover papers
uv run python -m src.cli discover --topic "machine learning"
uv run python -m src.cli discover --author "Geoffrey Hinton"

# Add notes
uv run python -m src.cli note <paper_id> "My note here"

# Show configuration
uv run python -m src.cli config
```

## Development

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing --cov-report=html tests/

# Run fast tests only (skip slow/integration tests)
uv run pytest -m "not slow"

# Run specific test file
uv run pytest tests/test_paper_manager.py

# Run specific test
uv run pytest tests/test_paper_manager.py::test_add_paper
```

### Code Quality

```bash
# Format code with black
uv run black src/ tests/

# Check formatting without changes
uv run black --check src/ tests/

# Lint with ruff
uv run ruff check src/ tests/

# Type check with mypy
uv run mypy src/
```

### Database Management

```bash
# Initialize database
uv run python -m src.utils.database init

# Drop all tables (CAUTION!)
uv run python -m src.utils.database drop
```

## UV Package Management

```bash
# Sync dependencies from pyproject.toml
uv sync --all-extras

# Update lock file
uv lock

# Show dependency tree
uv tree

# Check for outdated dependencies
uv pip list --outdated

# Upgrade uv itself
pip install --upgrade uv
```

## Cleanup

```bash
# Clean Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name ".coverage" -delete 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
rm -rf .uv_cache 2>/dev/null || true
```

## Shortcuts

For convenience, you can create shell aliases:

```bash
# Add to your ~/.bashrc or ~/.zshrc
alias mpa='uv run python -m src.cli'
alias mpa-ui='python run_ui.py'
alias mpa-test='uv run pytest'

# Then use:
mpa add-paper paper.pdf
mpa-ui
mpa-test
```

## Quick Examples

### Complete Workflow Example

```bash
# 1. Add a paper
uv run python -m src.cli add-paper https://arxiv.org/abs/2301.00001

# 2. Get a summary (assuming paper_id is 1)
uv run python -m src.cli summarize 1 --level detailed

# 3. Ask a question
uv run python -m src.cli ask 1 "What datasets were used?"

# 4. Add personal notes
uv run python -m src.cli note 1 "Interesting approach to attention mechanism"

# 5. Test understanding
uv run python -m src.cli quiz 1 --length 5
```

### Development Workflow Example

```bash
# 1. Make code changes
# ... edit files ...

# 2. Format and lint
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy src/

# 3. Run tests
uv run pytest

# 4. Run with coverage
uv run pytest --cov=src tests/

# 5. Commit changes
git add .
git commit -m "feat: Add new feature"
```

## Tips

- **All commands use `uv run`** to ensure they run in the correct virtual environment
- **Paper IDs** can be found using `uv run python -m src.cli list`
- **Web UI** is recommended for most users - it's easier to use than CLI
- **Environment variables** in `.env` are required for API features
- **Tests** should pass before committing code

## Getting Help

```bash
# Show CLI help
uv run python -m src.cli --help

# Show help for specific command
uv run python -m src.cli add-paper --help
uv run python -m src.cli summarize --help
```

## Troubleshooting

**Command not found: uv**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv
```

**Database not initialized**
```bash
uv run python -m src.utils.database init
```

**API key errors**
```bash
# Check your .env file has:
ANTHROPIC_API_KEY=your_key_here
VOYAGE_API_KEY=your_key_here  # or OPENAI_API_KEY
```

**Import errors**
```bash
# Resync dependencies
uv sync --all-extras
```

## See Also

- [README.md](../README.md) - Project overview and features
- [CLAUDE.md](../CLAUDE.md) - Development guidelines for contributors
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
- [src/ui/README.md](../src/ui/README.md) - Web UI documentation
