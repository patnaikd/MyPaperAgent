# Contributing to MyPaperAgent

Thank you for your interest in contributing to MyPaperAgent! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Git
- Tesseract OCR (optional, for scanned PDFs)
- API keys (Anthropic, Voyage/OpenAI)

### Development Setup

1. **Install uv** (if not already installed)
```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

2. **Fork and clone the repository**
```bash
git clone https://github.com/yourusername/MyPaperAgent.git
cd MyPaperAgent
```

3. **Sync dependencies** (uv handles venv creation automatically)
```bash
uv sync --all-extras
# Or use make
make dev-setup
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. **Initialize the database**
```bash
uv run python -m src.utils.database init
# Or: make init-db
```

6. **Run tests to verify setup**
```bash
uv run pytest
# Or: make test
```

## Development Workflow

### Branching Strategy

- `main` - Stable production branch
- `develop` - Development branch (default for PRs)
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `docs/*` - Documentation updates

### Making Changes

1. **Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
- Write clean, readable code
- Follow the project's code style
- Add tests for new functionality
- Update documentation as needed

3. **Format and lint your code**
```bash
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
# Or use make
make format
make lint
make type-check
# Or all at once
make check-all
```

4. **Run tests**
```bash
uv run pytest
uv run pytest --cov=src tests/  # With coverage
# Or use make
make test
make test-cov
```

5. **Commit your changes**
```bash
git add .
git commit -m "feat: Add your feature description"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

6. **Push and create a pull request**
```bash
git push origin feature/your-feature-name
```

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/)
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Use `black` for formatting
- Use `ruff` for linting

### Code Organization

- One class per file (exceptions for small helper classes)
- Group imports: standard library, third-party, local
- Use descriptive variable and function names
- Add docstrings to all public functions and classes

### Example Function

```python
"""Module for paper processing."""
from pathlib import Path
from typing import Optional

def extract_text_from_pdf(pdf_path: Path, use_ocr: bool = False) -> Optional[str]:
    """Extract text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file
        use_ocr: Whether to use OCR for scanned PDFs

    Returns:
        Extracted text content, or None if extraction fails

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If file is not a valid PDF
    """
    # Implementation here
    pass
```

## Testing Guidelines

### Writing Tests

- Write tests for all new functionality
- Aim for >80% code coverage
- Use fixtures for common test data
- Mock external API calls

### Test Structure

```python
"""Tests for paper manager."""
import pytest
from src.core.paper_manager import PaperManager

class TestPaperManager:
    """Test suite for PaperManager."""

    @pytest.fixture
    def paper_manager(self):
        """Create a PaperManager instance for testing."""
        return PaperManager()

    def test_add_paper_from_pdf(self, paper_manager, sample_pdf):
        """Test adding a paper from PDF file."""
        paper_id = paper_manager.add_paper(sample_pdf)
        assert paper_id is not None
        # More assertions...
```

### Running Tests

```bash
# Run all tests
uv run pytest
# Or: make test

# Run specific test file
uv run pytest tests/test_paper_manager.py

# Run specific test
uv run pytest tests/test_paper_manager.py::TestPaperManager::test_add_paper_from_pdf

# Run with coverage
uv run pytest --cov=src tests/
# Or: make test-cov

# Run only fast tests (skip slow integration tests)
uv run pytest -m "not slow"
# Or: make test-fast
```

## Documentation

### Code Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style docstrings
- Include examples for complex functions

### README Updates

- Update README.md if you add new features
- Add usage examples for new CLI commands
- Update feature list if applicable

### CLAUDE.md Updates

- Update if you change architecture
- Add new development commands
- Document new patterns or conventions

## Adding New Features

### Adding a New Agent

1. Create file: `src/agents/new_agent.py`
2. Create prompt: `src/agents/prompts/new_agent_prompt.txt`
3. Implement agent using Claude Agent SDK
4. Add CLI command in `src/cli.py`
5. Write tests in `tests/test_agents/test_new_agent.py`
6. Update documentation

### Adding a New Paper Source

1. Create API client: `src/discovery/source_name.py`
2. Implement metadata parser
3. Add to paper discovery agent
4. Update CLI with new source option
5. Write integration tests

### Extending the Database

1. Create Alembic migration: `alembic revision -m "description"`
2. Update models in `src/utils/database.py`
3. Update relevant managers in `src/core/`
4. Write migration tests
5. Test upgrade and downgrade

## Pull Request Process

1. **Before submitting:**
   - Ensure all tests pass
   - Format code with `black`
   - Check with `ruff` and `mypy`
   - Update documentation
   - Add yourself to contributors if first contribution

2. **PR Description should include:**
   - What changes were made and why
   - How to test the changes
   - Any breaking changes
   - Related issue numbers (if applicable)

3. **Review process:**
   - Maintainers will review your PR
   - Address any requested changes
   - Once approved, your PR will be merged

## Code Review Guidelines

### For Contributors

- Be open to feedback
- Respond to comments promptly
- Make requested changes or discuss alternatives

### For Reviewers

- Be respectful and constructive
- Explain the "why" behind suggestions
- Approve when ready, request changes if needed

## Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- Ask questions if anything is unclear

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Features**: Open a GitHub Issue with "enhancement" label
- **Security**: Email security@example.com (do not open public issue)

## License

By contributing to MyPaperAgent, you agree that your contributions will be licensed under the GNU General Public License v3.0.

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- GitHub contributors page

Thank you for contributing to MyPaperAgent! 🎉
