"""Add paper page - add from URL."""

import streamlit as st

from src.core.paper_manager import PaperManager
from src.rag.retriever import RAGRetriever
from src.ui.ui_helpers import render_footer


def show_add_paper_page():
    """Display add paper page."""
    st.title("➕ Add Paper")

    st.markdown("""
    Add papers to your library by providing a URL.
    We'll fetch metadata from external APIs and index the paper for search.
    Papers will be automatically indexed for semantic search.
    """)

    show_url_section()

    render_footer()


def _render_added_paper_summary(paper_id: int) -> None:
    """Render summary/actions for the last added paper."""
    manager = PaperManager()
    paper = manager.get_paper(paper_id)

    st.success("✅ Paper added successfully!")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Paper ID", paper_id)
        st.write(f"**Title:** {paper.title or 'Unknown'}")
        st.write(f"**Authors:** {paper.authors or 'Unknown'}")
    with col2:
        st.metric("Pages", paper.page_count or "N/A")
        st.write(f"**Year:** {paper.year or 'Unknown'}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📖 View Paper", width="stretch", key=f"view_{paper_id}"):
            st.session_state.selected_paper_id = paper_id
            st.session_state.current_page = "paper_detail"
            st.rerun()
    with col2:
        if st.button("➕ Add Another", width="stretch", key=f"add_another_{paper_id}"):
            st.session_state.pop("last_added_paper_id", None)
            st.rerun()


def show_url_section():
    """Show URL input section."""
    st.markdown("### Add from URL")

    url = st.text_input(
        "Paper URL",
        placeholder="https://arxiv.org/abs/2301.00001",
        help="arXiv URL, DOI, or direct PDF link"
    )

    # Optional metadata
    with st.expander("📝 Optional: Add metadata"):
        tags = st.text_input(
            "Tags",
            placeholder="machine-learning, transformers, nlp",
            help="Comma-separated tags",
            key="url_tags"
        )
        collection = st.text_input("Collection", help="Add to a collection", key="url_collection")
        skip_index = st.checkbox("Skip automatic indexing", value=False, key="url_skip_index")

    if url:
        if st.button("✅ Add Paper from URL", type="primary", width="stretch"):
            with st.spinner("Fetching metadata and processing paper..."):
                try:
                    # Process tags
                    tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None

                    # Add paper
                    manager = PaperManager()
                    paper_id = manager.add_paper_from_url(
                        url,
                        tags=tags_list,
                        collection_name=collection if collection else None
                    )

                    # Index for search
                    if not skip_index:
                        with st.spinner("Indexing for semantic search..."):
                            try:
                                retriever = RAGRetriever()
                                chunk_count = retriever.index_paper(paper_id)
                                st.success(f"✅ Indexed {chunk_count} chunks for semantic search")
                            except Exception as e:
                                st.warning(f"⚠️ Failed to index paper: {e}")

                    st.session_state.last_added_paper_id = paper_id

                except Exception as e:
                    st.error(f"❌ Error adding paper: {e}")
                    st.exception(e)

    if st.session_state.get("last_added_paper_id"):
        _render_added_paper_summary(st.session_state["last_added_paper_id"])
