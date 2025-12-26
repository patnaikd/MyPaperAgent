# MyPaperAgent

An intelligent agentic application for managing academic paper reading and comprehension, powered by Claude Agent SDK.

## Overview

MyPaperAgent helps researchers, students, and academics efficiently read, understand, and retain knowledge from research papers. It combines AI-powered analysis with personal note-taking and uses local RAG (Retrieval-Augmented Generation) to create a searchable knowledge base of your paper library.

## Features

### 📚 Paper Management
- **Import PDFs** and online paper links (arXiv, PubMed, ACM, IEEE, etc.)
- **Automatic metadata extraction** (title, authors, abstract, DOI, publication date)
- **OCR support** for scanned PDFs
- **Organize papers** into collections and tag them for easy retrieval

### 🤖 AI-Powered Analysis
- **Multi-level summaries**: Quick overviews, detailed summaries, and key findings
- **Methodology breakdown**: Understand research methods and experimental design
- **Strengths & limitations**: Critical analysis of papers
- **Citation analysis**: Extract and organize references

### 🔍 Local RAG & Semantic Search
- **Vector database** with semantic search across all papers
- **Cross-paper references**: Find related content in your library
- **Context-aware Q&A**: Ask questions and get answers grounded in paper content
- **Citation graph**: Visualize connections between papers

### 🧭 Research Synthesis
- **Paper story timeline**: Trace citations and citations-of-citations to build a human-readable research timeline
- **Survey paper builder**: Generate structured survey drafts for a given research area

### ✍️ Dual Note-Taking System
- **AI-generated notes**: Automatic extraction of key concepts
- **Personal annotations**: Add your own insights and observations
- **Rich text support**: Markdown, code snippets, equations
- **Hierarchical organization**: Notes organized by paper sections

### 🎯 AI-Generated Quizzes
- **Adaptive testing**: Questions tailored to paper difficulty
- **Multiple question types**: Multiple choice, short answer, conceptual
- **Spaced repetition**: Schedule reviews to improve retention
- **Progress tracking**: Monitor understanding over time

### 🔎 Paper Discovery
- **Topic-based search**: Find papers in specific research areas
- **Smart recommendations**: Discover papers related to your library
- **Citation crawling**: Find citing and cited papers
- **Multi-source integration**: arXiv, Semantic Scholar, PubMed, Google Scholar

## Installation

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/MyPaperAgent.git
cd MyPaperAgent
```

2. **Run the bootstrap script (installs dependencies, initializes DB, and launches UI)**
```bash
./run_my_paper_agent.sh
```

The script will install `uv` if needed, sync dependencies, create `.env` from
`.env.example`, initialize the database, and start Streamlit.

## Quick Start

### Web UI

**Launch the Streamlit web interface:**

```bash
./run_my_paper_agent.sh
```

The UI provides:
- 📚 Visual paper library with filtering and search
- ➕ Easy PDF upload and URL import
- 📖 Interactive paper viewer with AI features (summarize, Q&A, quiz)
- 🔍 Semantic search interface
- 🌐 Paper discovery from arXiv
- ⚙️ Settings and configuration viewer

See [src/ui/README.md](src/ui/README.md) for detailed UI documentation.

## Usage Examples

### Workflow 1: Reading a New Paper

```bash
# Add the paper
uv run python -m src.cli add-paper paper.pdf

# Get AI summary
uv run python -m src.cli summarize paper-123

# Ask questions about it
uv run python -m src.cli ask paper-123 "What is the main contribution?"

# Add personal notes
uv run python -m src.cli note paper-123 "Could apply this to my research on..."

# Test understanding
uv run python -m src.cli quiz paper-123
```

### Workflow 2: Literature Review

```bash
# Create a collection
uv run python -m src.cli collection create "My Literature Review"

# Add multiple papers
uv run python -m src.cli add-paper paper1.pdf --collection "My Literature Review"
uv run python -m src.cli add-paper paper2.pdf --collection "My Literature Review"

# Generate comparative analysis
uv run python -m src.cli compare paper-123 paper-456 paper-789

# Search across collection
uv run python -m src.cli search "methodology" --collection "My Literature Review"
```

### Workflow 3: Discovering New Papers

```bash
# Find papers on a topic
uv run python -m src.cli discover --topic "graph neural networks"

# Find papers related to one in your library
uv run python -m src.cli discover --similar-to paper-123

# Find papers citing a specific paper
uv run python -m src.cli discover --citations-of paper-123
```

## Architecture

MyPaperAgent uses a modular architecture:

- **Agents** (`src/agents/`): Claude Agent SDK-based agents for complex workflows
- **Core** (`src/core/`): Paper, note, and collection management
- **RAG** (`src/rag/`): Vector database and semantic search
- **Processing** (`src/processing/`): PDF extraction and metadata parsing
- **Discovery** (`src/discovery/`): Paper search and recommendations
- **Quiz** (`src/quiz/`): Question generation and assessment

Data is stored locally in:
- **SQLite database**: Metadata, notes, quiz performance
- **ChromaDB**: Vector embeddings for semantic search
- **File system**: PDF files

## Configuration

Edit `.env` to configure:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Embedding provider (choose one)
VOYAGE_API_KEY=pa-...
OPENAI_API_KEY=sk-...

# Optional
SEMANTIC_SCHOLAR_API_KEY=...  # For higher rate limits
MAX_PDF_SIZE_MB=50            # Maximum PDF file size
CHUNK_SIZE=800                # RAG chunk size in tokens
CHUNK_OVERLAP=100             # Overlap between chunks
```

## Development

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines and [COMMANDS.md](docs/COMMANDS.md) for a complete command reference.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing --cov-report=html tests/

# Run fast tests only (skip slow/integration tests)
uv run pytest -m "not slow"
```

### Code Formatting

```bash
# Format code
uv run black src/ tests/

# Check formatting
uv run black --check src/ tests/

# Lint code
uv run ruff check src/ tests/
```

### Type Checking

```bash
uv run mypy src/
```

## API Keys

You'll need:

1. **Anthropic API Key** (required): Get from [console.anthropic.com](https://console.anthropic.com/)
2. **Voyage AI API Key** OR **OpenAI API Key** (required for embeddings):
   - Voyage: [dash.voyageai.com](https://dash.voyageai.com/)
   - OpenAI: [platform.openai.com](https://platform.openai.com/)
3. **Semantic Scholar API Key** (optional): [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)

## Roadmap

- [x] Project setup and architecture
- [x] Core paper management (add, list, delete)
- [x] PDF text extraction and metadata parsing
- [x] RAG system with ChromaDB
- [x] Summarization agent (3 levels)
- [x] Q&A agent with RAG
- [x] Quiz generation and assessment
- [x] Paper discovery (arXiv integration)
- [x] Note-taking system
- [x] Web UI (Streamlit)
- [x] CLI interface
- [ ] Literature review agent
- [ ] Reading assistant agent
- [ ] Semantic Scholar integration
- [ ] Paper comparison features
- [ ] Collection management
- [ ] Export functionality (markdown, PDF)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed guidelines.

Quick steps:
1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python)
- Vector search powered by [ChromaDB](https://www.trychroma.com/)
- PDF processing with [PyMuPDF](https://pymupdf.readthedocs.io/)

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check [CLAUDE.md](CLAUDE.md) for development guidelines

---

**Happy Paper Reading! 📖✨**
