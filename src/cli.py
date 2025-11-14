"""Command-line interface for MyPaperAgent."""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.core.note_manager import NoteManager
from src.core.paper_manager import PaperManager, PaperManagerError, PaperNotFoundError
from src.rag.retriever import RAGRetriever, index_all_papers
from src.utils.config import get_config

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
            with console.status("[bold yellow]Extracting text and metadata..."):
                paper_id = manager.add_paper_from_pdf(
                    Path(source), tags=tags_list, collection_name=collection
                )
        else:
            # Add from URL
            with console.status("[bold yellow]Downloading and processing PDF..."):
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
@click.argument("paper_id", type=str)
@click.option("--level", type=click.Choice(["quick", "detailed", "full"]), default="detailed")
def summarize(paper_id: str, level: str) -> None:
    """Generate AI summary of a paper.

    Levels:
    - quick: Abstract-level summary
    - detailed: Key findings and methodology
    - full: Comprehensive analysis
    """
    console.print(f"[yellow]Summarizing paper {paper_id} (level: {level})[/yellow]")

    # TODO: Implement summarization
    # - Retrieve paper from database
    # - Use Claude Agent to generate summary
    # - Store summary in database
    # - Display to user

    console.print("[red]Not implemented yet[/red]")


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
@click.argument("paper_id", type=str)
@click.argument("question", type=str)
def ask(paper_id: str, question: str) -> None:
    """Ask a question about a specific paper."""
    console.print(f"[yellow]Question: {question}[/yellow]")

    # TODO: Implement Q&A
    # - Retrieve paper
    # - Use RAG to find relevant sections
    # - Generate answer with Claude
    # - Display with citations

    console.print("[red]Not implemented yet[/red]")


@cli.command()
@click.argument("paper_id", type=str)
@click.option("--length", "-l", default=10, help="Number of questions")
@click.option("--difficulty", type=click.Choice(["easy", "medium", "hard", "adaptive"]))
def quiz(paper_id: str, length: int, difficulty: Optional[str]) -> None:
    """Take an AI-generated quiz on a paper."""
    console.print(f"[yellow]Starting quiz for paper {paper_id}[/yellow]")

    # TODO: Implement quiz
    # - Generate questions using Claude
    # - Present questions interactively
    # - Track answers
    # - Provide feedback
    # - Store results

    console.print("[red]Not implemented yet[/red]")


@cli.command()
@click.argument("paper_id", type=int)
@click.argument("content", type=str)
@click.option("--section", "-s", help="Paper section")
def note(paper_id: int, content: str, section: Optional[str]) -> None:
    """Add a personal note to a paper."""
    try:
        console.print(f"\n[bold cyan]Adding note to paper {paper_id}[/bold cyan]\n")

        note_manager = NoteManager()
        note_id = note_manager.add_note(paper_id, content, section=section)

        console.print(f"[bold green]✓ Note added successfully![/bold green]")
        console.print(f"[cyan]Note ID:[/cyan] {note_id}\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


@cli.command()
@click.option("--topic", "-t", help="Topic to search for")
@click.option("--similar-to", help="Find papers similar to this paper_id")
@click.option("--citations-of", help="Find papers citing this paper_id")
@click.option("--limit", "-l", default=10, help="Number of papers to find")
def discover(
    topic: Optional[str],
    similar_to: Optional[str],
    citations_of: Optional[str],
    limit: int,
) -> None:
    """Discover new papers."""
    if not any([topic, similar_to, citations_of]):
        console.print("[red]Error: Provide --topic, --similar-to, or --citations-of[/red]")
        return

    console.print("[yellow]Discovering papers...[/yellow]")

    # TODO: Implement paper discovery
    # - Search arXiv, Semantic Scholar, etc.
    # - Rank by relevance
    # - Display results
    # - Allow quick add to library

    console.print("[red]Not implemented yet[/red]")


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
