# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MyPaperAgent is an agentic application for managing academic paper reading and comprehension. It uses the Claude Agent SDK to provide AI-powered features for reading, understanding, and retaining knowledge from research papers.

### Core Goals
- Read and understand content of papers with AI assistance
- Maintain summaries and notes for future reference
- Discover new papers related to topics of interest
- Test understanding through AI-generated quizzes
- Store PDFs and online links to papers
- Combine AI-generated insights with personal notes
- Use local RAG for semantic search across papers

## Architecture

### Technology Stack
- **Language**: Python 3.11+
- **AI Framework**: Claude Agent SDK for agentic workflows
- **Vector Database**: ChromaDB (local, embedded)
- **Embeddings**: Voyage AI or OpenAI embeddings API
- **PDF Processing**: PyMuPDF (fitz) for text extraction
- **OCR**: Tesseract for scanned PDFs
- **Database**: SQLite for metadata and notes
- **CLI**: Click for command-line interface
- **Testing**: pytest

### Project Structure

```
src/
├── agents/              # Claude Agent SDK agents (core AI workflows)
│   ├── reading_assistant.py    # Guides through complex papers
│   ├── quiz_generator.py       # Generates adaptive quizzes
│   ├── paper_discovery.py      # Finds related papers
│   ├── summarizer.py           # Multi-level summarization
│   └── literature_review.py    # Synthesizes multiple papers
├── core/
│   ├── paper_manager.py        # Paper CRUD operations
│   ├── note_manager.py         # Note-taking system
│   └── collection_manager.py   # Organize papers into collections
├── rag/
│   ├── embeddings.py           # Generate and manage embeddings
│   ├── vector_store.py         # ChromaDB interface
│   └── retriever.py            # RAG retrieval logic
├── processing/
│   ├── pdf_extractor.py        # Extract text/metadata from PDFs
│   ├── metadata_parser.py      # Parse academic metadata
│   └── ocr_processor.py        # OCR for scanned PDFs
├── discovery/
│   ├── arxiv_search.py         # arXiv API integration
│   ├── semantic_scholar.py     # Semantic Scholar API
│   └── paper_recommender.py    # ML-based recommendations
├── quiz/
│   ├── question_generator.py   # Generate questions from papers
│   ├── assessment.py           # Track quiz performance
│   └── spaced_repetition.py    # Schedule review quizzes
└── utils/
    ├── config.py               # Configuration management
    └── database.py             # SQLite database interface

data/                   # Gitignored - local data storage
├── papers/            # PDF storage
├── vector_db/         # ChromaDB persistence
└── database/          # SQLite database files
```

### Key Design Patterns

**Agent-First Architecture**: The application is built around Claude Agent SDK agents that handle complex workflows. Each agent is responsible for a specific domain (reading, summarizing, quiz generation, etc.).

**RAG Pipeline**: All papers are chunked and embedded into ChromaDB. When users ask questions or agents need context, relevant chunks are retrieved to provide grounded responses.

**Dual Note System**:
- AI-generated notes are stored separately from user notes
- Both can be merged for comprehensive paper understanding
- User notes always take precedence in displays

**Database Schema**:
- `papers`: Core paper metadata (title, authors, DOI, file_path, url, status)
- `notes`: Both AI and personal notes with paper_id foreign key
- `collections`: Grouping mechanism for papers
- `quiz_questions`: Generated questions with performance tracking
- `tags`: Flexible tagging system
- `embeddings`: Links to vector store chunks

## Development Commands

### Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# or: pip install uv

# Sync dependencies (uv handles venv automatically)
uv sync --all-extras

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys (ANTHROPIC_API_KEY, VOYAGE_API_KEY, etc.)

# Initialize database
uv run python -m src.utils.database init
```

### Running the Application
```bash
# CLI commands (using uv run)
uv run python -m src.cli add-paper path/to/paper.pdf
uv run python -m src.cli add-paper https://arxiv.org/abs/2301.00001
uv run python -m src.cli summarize <paper_id>
uv run python -m src.cli quiz <paper_id>
uv run python -m src.cli search "transformer architecture"
uv run python -m src.cli discover --topic "reinforcement learning"
uv run python -m src.cli config  # Show current configuration

# Web UI (Streamlit)
python run_ui.py
# Or: uv run streamlit run src/ui/app.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_paper_manager.py

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing --cov-report=html tests/

# Run specific test
uv run pytest tests/test_paper_manager.py::test_add_paper

# Run fast tests only
uv run pytest -m "not slow"
```

### Linting and Formatting
```bash
# Format code
uv run black src/ tests/

# Check formatting
uv run black --check src/ tests/

# Lint
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

### UV Commands
```bash
# Update dependencies
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

## Important Implementation Notes

### Claude Agent SDK Integration
- All agents should be in `src/agents/` and inherit from base agent patterns
- Use structured outputs for agent responses to ensure consistency
- Agents should use the RAG system for grounding in paper content
- Keep agent prompts in separate files under `src/agents/prompts/`

### RAG System
- **Chunking Strategy**: Use semantic chunking (paragraph-based) with overlap
- **Chunk Size**: 500-1000 tokens per chunk with 100 token overlap
- **Embedding Model**: Voyage AI `voyage-2` or OpenAI `text-embedding-3-small`
- **Retrieval**: Top-k=5 for most queries, top-k=10 for literature review
- All paper content must be embedded before summarization or quiz generation

### PDF Processing
- Always attempt text extraction first with PyMuPDF
- Fall back to OCR (Tesseract) if text extraction yields <100 words
- Store both raw text and cleaned text in database
- Extract metadata using regex patterns for common academic formats

### Database Migrations
- Use Alembic for schema migrations (not raw SQL)
- Never modify the database schema directly in production
- All migrations must be reversible

### API Keys and Configuration
- Never commit API keys
- Use `python-dotenv` to load from `.env`
- Required keys: `ANTHROPIC_API_KEY` (required), `VOYAGE_API_KEY` or `OPENAI_API_KEY` (for embeddings)
- Optional: `SEMANTIC_SCHOLAR_API_KEY` for rate limit increases

### Error Handling
- PDF processing: Handle corrupted PDFs gracefully, log errors
- Network requests: Implement retry logic with exponential backoff
- RAG queries: Fallback to direct LLM if retrieval fails
- Agent failures: Always provide user-friendly error messages

## Testing Guidelines

### Unit Tests
- Mock external APIs (Anthropic, Voyage, arXiv)
- Test all CRUD operations in managers
- Test chunking and embedding logic independently
- Use fixtures for sample PDFs and paper metadata

### Integration Tests
- Test full workflows: PDF upload → extraction → embedding → search
- Test agent workflows end-to-end with mock Claude responses
- Test database transactions and rollbacks

### Test Data
- Sample PDFs are in `tests/fixtures/papers/`
- Use deterministic random seeds for reproducible tests
- Mock API responses are in `tests/fixtures/api_responses/`

## Common Patterns

### Adding a New Agent
1. Create file in `src/agents/new_agent.py`
2. Define prompt in `src/agents/prompts/new_agent_prompt.txt`
3. Implement using Claude Agent SDK patterns
4. Add CLI command in `src/cli.py`
5. Write tests in `tests/test_agents/test_new_agent.py`

### Adding a New Paper Source
1. Create API client in `src/discovery/source_name.py`
2. Implement standardized metadata parser
3. Add to paper discovery agent
4. Update CLI with new source option

### Extending the Database
1. Create Alembic migration: `alembic revision -m "description"`
2. Update models in `src/utils/database.py`
3. Update relevant managers in `src/core/`
4. Write migration tests

## Performance Considerations

- **Batch Embedding**: Always embed papers in batches (16-32 chunks at a time)
- **Connection Pooling**: Reuse ChromaDB client connections
- **Lazy Loading**: Don't load full PDF text unless needed
- **Caching**: Cache frequently accessed summaries and embeddings
- **Async Operations**: Use `asyncio` for multiple API calls (agent workflows)

## Security Notes

- PDFs are stored locally - validate file types before processing
- Sanitize user input before database queries (use parameterized queries)
- Limit PDF file size to prevent DoS (default: 50MB max)
- Validate URLs before fetching to prevent SSRF attacks
