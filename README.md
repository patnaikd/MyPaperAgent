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

### Prerequisites
- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- Tesseract OCR (for scanned PDFs)

### Setup

1. **Install uv** (if not already installed)
```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

2. **Clone the repository**
```bash
git clone https://github.com/yourusername/MyPaperAgent.git
cd MyPaperAgent
```

3. **Sync dependencies** (uv handles venv creation automatically)
```bash
uv sync --all-extras
```

4. **Set up environment variables**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_key_here
VOYAGE_API_KEY=your_voyage_key_here  # or OPENAI_API_KEY for embeddings
```

5. **Initialize the database**
```bash
uv run python -m src.utils.database init
```

6. **Install Tesseract (optional, for OCR)**
- **macOS**: `brew install tesseract`
- **Ubuntu**: `sudo apt-get install tesseract-ocr`
- **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Quick Start

### Add a Paper

**From PDF:**
```bash
uv run python -m src.cli add-paper path/to/paper.pdf
```

**From URL:**
```bash
uv run python -m src.cli add-paper https://arxiv.org/abs/2301.00001
```

### Summarize a Paper

```bash
uv run python -m src.cli summarize <paper_id>
```

### Search Your Library

```bash
uv run python -m src.cli search "transformer architecture"
```

### Take a Quiz

```bash
uv run python -m src.cli quiz <paper_id>
```

### Add Personal Notes

```bash
uv run python -m src.cli note <paper_id> "My observation about the methodology..."
```

### Discover Related Papers

```bash
uv run python -m src.cli discover --topic "reinforcement learning" --limit 10
```

### List All Papers

```bash
uv run python -m src.cli list
```

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

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines.

### Running Tests

```bash
uv run pytest
# Or use make
make test
```

### Code Formatting

```bash
uv run black src/ tests/
uv run ruff check src/ tests/
# Or use make
make format
make lint
```

### Type Checking

```bash
uv run mypy src/
# Or use make
make type-check
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
- [ ] Core paper management (add, list, delete)
- [ ] PDF text extraction and metadata parsing
- [ ] RAG system with ChromaDB
- [ ] Reading assistant agent
- [ ] Summarization agent
- [ ] Note-taking system
- [ ] Quiz generation and assessment
- [ ] Paper discovery and recommendations
- [ ] Web UI (future)

## Contributing

Contributions are welcome! Please:

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
