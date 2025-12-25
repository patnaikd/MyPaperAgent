# MyPaperAgent Streamlit UI

A modern web interface for MyPaperAgent, providing an intuitive way to manage your academic paper library with AI-powered features.

## Features

### 📚 Library Management
- View all papers in an organized, searchable list
- Filter by reading status (unread, reading, completed, archived)
- Search papers by title or author
- Update paper status with one click

### ➕ Add Papers
- Upload PDF files directly
- Add papers from URLs (arXiv, DOI, direct PDF links)
- Automatic text extraction and metadata parsing
- Optional tagging and collection organization
- Automatic RAG indexing for semantic search

### 📖 Paper Details
Four powerful features for each paper:

#### 💭 Summarize
- Generate AI summaries at three levels:
  - **Quick**: 2-3 paragraph overview
  - **Detailed**: Key findings and methodology
  - **Full**: Comprehensive analysis
- View and compare previous summaries
- Auto-save summaries as AI-generated notes

#### ❓ Ask Questions
- Ask natural language questions about the paper
- RAG-powered answers with source citations
- Question history tracking
- Context-aware responses

#### 📝 Quiz Generation
- Generate quiz questions to test understanding
- Multiple difficulty levels (easy, medium, hard, adaptive)
- Configurable question count
- View saved questions for review
- Questions saved to database

#### 📔 Personal Notes
- Add personal notes with sections
- View all notes with timestamps
- Delete notes when no longer needed
- Separate from AI-generated content

### 🔍 Semantic Search
- Natural language search across all papers
- RAG-powered semantic similarity
- Relevance scoring for results
- Search within specific papers
- View context and source papers

### 🌐 Paper Discovery
- Search arXiv by topic, author, or category
- Browse recent papers by field
- View abstracts and metadata
- One-click add to library
- Direct arXiv links

### ⚙️ Settings
- View configuration and API key status
- Database statistics
- System information
- API setup guide
- Cache management

## Quick Start

### Prerequisites
1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set up environment variables in `.env`:
   ```bash
   ANTHROPIC_API_KEY=your_key_here
   VOYAGE_API_KEY=your_key_here  # or OPENAI_API_KEY
   ```

### Launch the UI

**Option 1: Using the launch script (recommended)**
```bash
python run_ui.py
```

**Option 2: Direct uv run command**
```bash
uv run streamlit run src/ui/app.py
```

The UI will open in your browser at http://localhost:8501

## Architecture

```
src/ui/
├── app.py              # Main application with navigation
├── pages/              # Individual page modules
│   ├── library.py      # Paper library view
│   ├── add_paper.py    # PDF upload and URL input
│   ├── paper_detail.py # Paper details with AI features
│   ├── search.py       # Semantic search interface
│   ├── discover.py     # arXiv paper discovery
│   └── settings.py     # Configuration and stats
└── README.md           # This file
```

## Usage Guide

### Adding Your First Paper

1. Click "➕ Add Paper" in the sidebar
2. Choose upload method:
   - **Upload PDF**: Drag and drop or select a PDF file
   - **From URL**: Paste arXiv URL, DOI, or direct PDF link
3. Optionally add tags and collection
4. Click "Add Paper"
5. Paper is automatically indexed for search

### Exploring a Paper

1. Go to "🏠 Library"
2. Click "📖 View" on any paper
3. Use the tabs to:
   - Generate summaries
   - Ask questions
   - Create quizzes
   - Add personal notes

### Searching Your Library

1. Go to "🔍 Search"
2. Enter a natural language query
3. View relevant chunks with relevance scores
4. Click "View Paper" to see full details

### Discovering New Papers

1. Go to "🌐 Discover"
2. Choose search method:
   - By Topic: Enter keywords
   - By Author: Enter author name
   - Recent Papers: Browse by category
3. View results and abstracts
4. Click "Add to Library" for interesting papers

## Tips

### Best Practices
- Index papers immediately after adding for best search results
- Use descriptive tags for easier organization
- Save summaries at different levels for different needs
- Ask specific questions for better answers

### Search Tips
- Use natural language questions, not just keywords
- Be specific about what you're looking for
- Include technical terms when relevant
- Try different phrasings if results aren't relevant

### Quiz Tips
- Use adaptive difficulty for mixed question types
- Generate quizzes after reading to test understanding
- Review saved questions periodically for retention

## Troubleshooting

### UI won't start
- Check that Streamlit is installed: `uv sync`
- Verify no other process is using port 8501
- Check for Python syntax errors in page files

### Papers not showing
- Verify database exists: `data/database/papers.db`
- Check database permissions
- Try adding a test paper

### Search returns no results
- Ensure papers are indexed (check during add)
- Verify ChromaDB is working
- Check embedding API keys in settings

### AI features not working
- Verify `ANTHROPIC_API_KEY` in `.env`
- Check API key validity in Settings page
- Ensure network connectivity

## Development

### Adding New Pages
1. Create new file in `src/ui/pages/`
2. Implement `show_<page>_page()` function
3. Add navigation button in `app.py`
4. Add route in main() function

### Styling
- Custom CSS in `app.py` `st.markdown()` blocks
- Use Streamlit's built-in themes
- Maintain consistent layout across pages

### Testing
- Test each feature with real papers
- Verify error handling with invalid inputs
- Check mobile responsiveness
- Test with different paper types (scanned, text-based, etc.)

## Known Limitations

- File upload limited by Streamlit's default (200MB)
- Large papers may take time to process
- OCR quality depends on PDF scan quality
- Embedding generation requires API calls (costs/limits apply)

## Future Enhancements

Potential improvements:
- Dark mode toggle
- Batch operations (delete, tag multiple papers)
- Export functionality (markdown, PDF reports)
- Advanced filtering and sorting
- Visualization of paper relationships
- Reading progress tracking
- Annotation support

## Support

For issues or questions:
1. Check this README
2. Review main project README
3. Check [CLAUDE.md](../../CLAUDE.md) for development info
4. Open an issue on GitHub
