"""Command-line interface for MyPaperAgent."""
import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.agents.qa_agent import QAAgent
from src.agents.quiz_generator import QuizGenerator
from src.agents.summarizer import SummarizationAgent
from src.core.note_manager import NoteManager
from src.core.paper_manager import PaperManager, PaperManagerError, PaperNotFoundError
from src.discovery.arxiv_search import ArxivSearch
from src.rag.retriever import RAGRetriever, index_all_papers
from src.utils.config import get_config


logger = logging.getLogger(__name__)

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """MyPaperAgent - Intelligent paper reading and comprehension assistant."""
    pass


@cli.command()
@click.argument("source", type=str)
@click.option("--collection", "-c", help="Add to collection")
@click.option("--tags", "-t", multiple=True, help="Add tags to paper")
@click.option("--no-index", is_flag=True, help="Skip RAG indexing")
def add_paper(
    source: str, collection: Optional[str], tags: tuple[str, ...], no_index: bool
) -> None:
    """Add a paper from PDF file or URL.

    SOURCE can be:
    - Path to a PDF file
    - arXiv URL (https://arxiv.org/abs/...)
    - DOI (will attempt to fetch)
    - Any other academic paper URL
    """
    try:
        console.print(f"\n[bold cyan]Adding paper from:[/bold cyan] {source}\n")

        manager = PaperManager()
        tags_list = list(tags) if tags else None

        # Check if source is a file or URL
        if Path(source).exists():
            # Add from PDF file
            with console.status("[bold yellow]Extracting text..."):
                paper_id = manager.add_paper_from_pdf(
                    Path(source), tags=tags_list, collection_name=collection
                )
        else:
            # Add from URL
            with console.status("[bold yellow]Fetching metadata and processing PDF..."):
                paper_id = manager.add_paper_from_url(
                    source, tags=tags_list, collection_name=collection
                )

        # Get paper details
        paper = manager.get_paper(paper_id)

        console.print(f"[bold green]✓ Successfully added paper![/bold green]\n")
        console.print(f"[cyan]ID:[/cyan] {paper.id}")
        console.print(f"[cyan]Title:[/cyan] {paper.title or 'Unknown'}")
        console.print(f"[cyan]Authors:[/cyan] {paper.authors or 'Unknown'}")
        console.print(f"[cyan]Year:[/cyan] {paper.year or 'Unknown'}")
        console.print(f"[cyan]Pages:[/cyan] {paper.page_count}")

        # Index for semantic search
        if not no_index:
            try:
                console.print()
                with console.status("[bold yellow]Indexing paper for semantic search..."):
                    retriever = RAGRetriever()
                    chunk_count = retriever.index_paper(paper_id)

                console.print(
                    f"[bold green]✓ Indexed {chunk_count} chunks for semantic search[/bold green]"
                )
            except Exception as e:
                console.print(f"[yellow]⚠ Warning: Failed to index paper: {e}[/yellow]")

        console.print(
            f"\n[dim]Use 'mypaperagent summarize {paper_id}' to generate a summary[/dim]\n"
        )

    except PaperManagerError as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]✗ Unexpected error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.argument("paper_id", type=int)
@click.option("--level", type=click.Choice(["quick", "detailed", "full"]), default="detailed")
@click.option("--no-save", is_flag=True, help="Don't save summary as note")
def summarize(paper_id: int, level: str, no_save: bool) -> None:
    """Generate AI summary of a paper.

    Levels:
    - quick: Abstract-level summary (2-3 paragraphs)
    - detailed: Key findings and methodology
    - full: Comprehensive analysis
    """
    try:
        console.print(f"\n[bold cyan]Generating {level} summary for paper {paper_id}[/bold cyan]\n")

        # Initialize agent
        agent = SummarizationAgent()

        # Generate summary
        with console.status(f"[bold yellow]Generating {level} summary with Claude..."):
            summary = agent.summarize_paper(paper_id, level=level, save_as_note=not no_save)

        # Display summary
        console.print(Panel(summary, title=f"[bold green]{level.title()} Summary[/bold green]", border_style="green"))

        if not no_save:
            console.print(f"\n[dim]✓ Summary saved as AI-generated note[/dim]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.argument("query", type=str)
@click.option("--collection", "-c", help="Search within collection")
@click.option("--limit", "-l", default=5, help="Number of results")
@click.option("--paper-id", "-p", type=int, help="Search within specific paper")
def search(
    query: str, collection: Optional[str], limit: int, paper_id: Optional[int]
) -> None:
    """Semantic search across your paper library."""
    try:
        console.print(f"\n[bold cyan]Searching for:[/bold cyan] {query}\n")

        retriever = RAGRetriever()

        # Perform search
        with console.status("[bold yellow]Searching..."):
            results = retriever.search(query, n_results=limit, paper_id=paper_id)

        if not results:
            console.print("[yellow]No results found.[/yellow]\n")
            return

        console.print(f"[bold green]Found {len(results)} results:[/bold green]\n")

        # Display results
        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            title = metadata.get("title", "Unknown")
            paper_id_res = metadata.get("paper_id", "Unknown")
            relevance = result["relevance_score"]

            # Create result panel
            console.print(f"[bold cyan]{i}. Paper {paper_id_res}:[/bold cyan] {title}")
            console.print(f"[dim]Relevance: {relevance:.2%}[/dim]")
            console.print(Panel(result["text"][:500] + "...", border_style="blue"))
            console.print()

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.argument("paper_id", type=int)
@click.argument("question", type=str)
def ask(paper_id: int, question: str) -> None:
    """Ask a question about a specific paper."""
    try:
        console.print(f"\n[bold cyan]Question:[/bold cyan] {question}\n")

        # Initialize Q&A agent
        agent = QAAgent()

        # Get answer
        with console.status("[bold yellow]Generating answer with Claude..."):
            result = agent.answer_question(question, paper_id=paper_id)

        # Display answer
        console.print(Panel(result["answer"], title="[bold green]Answer[/bold green]", border_style="green"))

        # Show sources
        if result["sources"]:
            console.print("\n[bold]Sources:[/bold]")
            for source in result["sources"]:
                console.print(f"  • Paper {source['paper_id']}: {source['title']}")

        if result.get("saved"):
            console.print("[dim]✓ Question saved to history[/dim]")
        else:
            console.print("[dim]ℹ Question already saved[/dim]")

        console.print()

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.argument("paper_id", type=int)
@click.option("--length", "-l", default=5, help="Number of questions")
@click.option("--difficulty", type=click.Choice(["easy", "medium", "hard", "adaptive"]), default="adaptive")
def quiz(paper_id: int, length: int, difficulty: str) -> None:
    """Generate and display quiz questions for a paper.

    Questions are saved to the database for future review.
    """
    try:
        console.print(f"\n[bold cyan]Generating {length} {difficulty} quiz questions for paper {paper_id}[/bold cyan]\n")

        # Initialize generator
        generator = QuizGenerator()

        # Generate questions
        with console.status(f"[bold yellow]Generating {length} questions with Claude..."):
            questions = generator.generate_quiz(paper_id, num_questions=length, difficulty=difficulty)

        if not questions:
            console.print("[yellow]Failed to generate questions. Please try again.[/yellow]\n")
            return

        console.print(f"[bold green]Generated {len(questions)} questions![/bold green]\n")

        # Display questions
        for i, q in enumerate(questions, 1):
            console.print(f"[bold cyan]Question {i}:[/bold cyan] {q['question']}")
            console.print(f"[bold green]Answer:[/bold green] {q['answer']}")
            if q.get('explanation'):
                console.print(f"[dim]Explanation: {q['explanation']}[/dim]")
            console.print(f"[dim]Difficulty: {q.get('difficulty', 'medium')}[/dim]")
            console.print()

        console.print(f"[dim]✓ Questions stored in database (skips duplicates)[/dim]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.argument("paper_id", type=int)
@click.argument("content", type=str)
@click.option("--section", "-s", help="Paper section")
def note(paper_id: int, content: str, section: Optional[str]) -> None:
    """Add a personal note to a paper."""
    try:
        console.print(f"\n[bold cyan]Adding note to paper {paper_id}[/bold cyan]\n")

        note_manager = NoteManager()
        note_id, created = note_manager.add_note_if_new(paper_id, content, section=section)

        if created:
            console.print(f"[bold green]✓ Note added successfully![/bold green]")
        else:
            console.print(f"[bold yellow]ℹ Note already exists.[/bold yellow]")
        console.print(f"[cyan]Note ID:[/cyan] {note_id}\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.option("--topic", "-t", help="Topic to search for")
@click.option("--author", "-a", help="Search by author name")
@click.option("--category", "-c", help="arXiv category (e.g., cs.AI, cs.LG)")
@click.option("--limit", "-l", default=10, help="Number of papers to find")
def discover(
    topic: Optional[str],
    author: Optional[str],
    category: Optional[str],
    limit: int,
) -> None:
    """Discover papers on arXiv."""
    if not any([topic, author, category]):
        console.print("[red]Error: Provide --topic, --author, or --category[/red]\n")
        return

    try:
        console.print("\n[bold cyan]Discovering papers on arXiv...[/bold cyan]\n")

        # Initialize search
        searcher = ArxivSearch(max_results=limit)

        # Perform search
        with console.status("[bold yellow]Searching arXiv..."):
            if topic:
                results = searcher.search_by_topic(topic)
            elif author:
                results = searcher.search_by_author(author)
            else:  # category
                results = searcher.search_recent(category=category)

        if not results:
            console.print("[yellow]No papers found.[/yellow]\n")
            return

        console.print(f"[bold green]Found {len(results)} papers![/bold green]\n")

        # Display results in table
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="bold", max_width=40)
        table.add_column("Authors", style="cyan", max_width=25)
        table.add_column("Year", width=6)
        table.add_column("arXiv ID", style="green", width=12)

        for i, paper in enumerate(results, 1):
            title = paper["title"]
            if len(title) > 40:
                title = title[:37] + "..."

            authors = paper["authors"]
            if len(authors) > 25:
                authors = authors[:22] + "..."

            year = paper["published"][:4] if paper.get("published") else "-"

            table.add_row(
                str(i),
                title,
                authors,
                year,
                paper["arxiv_id"]
            )

        console.print(table)

        # Show how to add papers
        console.print(f"\n[dim]To add a paper, use:[/dim]")
        console.print(f"[dim]  uv run python -m src.cli add-paper <PDF_URL>[/dim]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.option("--collection", "-c", help="List papers in collection")
@click.option("--status", type=click.Choice(["unread", "reading", "completed", "archived"]))
@click.option("--tag", "-t", multiple=True, help="Filter by tags")
@click.option("--limit", "-l", default=50, help="Number of papers to show")
def list(
    collection: Optional[str], status: Optional[str], tag: tuple[str, ...], limit: int
) -> None:
    """List papers in your library."""
    try:
        console.print("\n[bold cyan]Paper Library[/bold cyan]\n")

        manager = PaperManager()

        # Get papers
        papers = manager.list_papers(status=status, limit=limit)

        if not papers:
            console.print("[yellow]No papers in library yet.[/yellow]")
            console.print(
                "[dim]Use 'uv run python -m src.cli add-paper <source>' to add papers[/dim]\n"
            )
            return

        # Create table
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("ID", style="dim", width=6)
        table.add_column("Title", style="bold", max_width=50)
        table.add_column("Authors", style="cyan", max_width=30)
        table.add_column("Year", width=6)
        table.add_column("Pages", justify="right", width=6)
        table.add_column("Status", justify="center", width=10)

        # Add rows
        for paper in papers:
            # Truncate long fields
            title = paper.title or "Unknown"
            if len(title) > 50:
                title = title[:47] + "..."

            authors = paper.authors or "Unknown"
            if len(authors) > 30:
                authors = authors[:27] + "..."

            # Status with color
            status_str = paper.status
            if paper.status == "completed":
                status_str = f"[green]{paper.status}[/green]"
            elif paper.status == "reading":
                status_str = f"[yellow]{paper.status}[/yellow]"
            elif paper.status == "unread":
                status_str = f"[dim]{paper.status}[/dim]"

            table.add_row(
                str(paper.id),
                title,
                authors,
                str(paper.year) if paper.year else "-",
                str(paper.page_count) if paper.page_count else "-",
                status_str,
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(papers)} papers[/dim]")

        # Show statistics
        total_count = manager.get_paper_count()
        if total_count > limit:
            console.print(f"[dim]Showing {limit} of {total_count} papers (use --limit to show more)[/dim]")

        console.print()

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.argument("paper_ids", nargs=-1, required=True)
def compare(paper_ids: tuple[str, ...]) -> None:
    """Compare multiple papers."""
    console.print(f"[yellow]Comparing {len(paper_ids)} papers[/yellow]")

    # TODO: Implement comparison
    # - Retrieve papers
    # - Use Claude Agent to compare
    # - Display comparison table

    console.print("[red]Not implemented yet[/red]")


@cli.group()
def collection() -> None:
    """Manage paper collections."""
    pass


@collection.command("create")
@click.argument("name", type=str)
@click.option("--description", "-d", help="Collection description")
def create_collection(name: str, description: Optional[str]) -> None:
    """Create a new collection."""
    console.print(f"[yellow]Creating collection: {name}[/yellow]")

    # TODO: Implement collection creation
    console.print("[red]Not implemented yet[/red]")


@collection.command("list")
def list_collections() -> None:
    """List all collections."""
    console.print("[yellow]Collections[/yellow]\n")

    # TODO: Implement collection listing
    console.print("[red]No collections yet[/red]")


@cli.command()
def config() -> None:
    """Show current configuration."""
    try:
        cfg = get_config()

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value")

        table.add_row("Database Path", str(cfg.database_path))
        table.add_row("Vector DB Path", str(cfg.vector_db_path))
        table.add_row("PDF Storage", str(cfg.pdf_storage_path))
        table.add_row("Embedding Model", cfg.embedding_model)
        table.add_row("Embedding Provider", cfg.get_embedding_provider())
        table.add_row("Chunk Size", str(cfg.chunk_size))
        table.add_row("Max PDF Size", f"{cfg.max_pdf_size_mb} MB")

        console.print(table)

    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("[yellow]Make sure you have created a .env file with required API keys[/yellow]")
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
