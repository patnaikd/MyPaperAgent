"""Add paper page - upload PDFs or add from URL."""
import logging

import streamlit as st
import tempfile
from pathlib import Path

from src.core.paper_manager import PaperManager
from src.rag.retriever import RAGRetriever
from src.ui.ui_helpers import render_footer


logger = logging.getLogger(__name__)


def show_add_paper_page():
    """Display add paper page."""
    st.title("➕ Add Paper")

    st.markdown("""
    Add papers to your library by uploading a PDF file or providing a URL.
    Papers will be automatically indexed for semantic search.
    """)

    # Tab selection for different input methods
    tab1, tab2 = st.tabs(["📄 Upload PDF", "🔗 From URL"])

    with tab1:
        show_upload_section()

    with tab2:
        show_url_section()

    render_footer()


def _render_added_paper_summary(paper_id: int, source: str) -> None:
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
        if st.button("📖 View Paper", width="stretch", key=f"view_{source}_{paper_id}"):
            st.session_state.selected_paper_id = paper_id
            st.session_state.current_page = "paper_detail"
            st.rerun()
    with col2:
        if st.button("➕ Add Another", width="stretch", key=f"add_another_{source}"):
            st.session_state.pop("last_added_paper_id", None)
            st.session_state.pop("last_added_source", None)
            st.rerun()


def show_upload_section():
    """Show PDF upload section."""
    st.markdown("### Upload PDF File")

    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        help="Upload a PDF file of an academic paper"
    )

    # Optional metadata
    with st.expander("📝 Optional: Add metadata"):
        tags = st.text_input(
            "Tags",
            placeholder="machine-learning, transformers, nlp",
            help="Comma-separated tags"
        )
        collection = st.text_input("Collection", help="Add to a collection")
        skip_index = st.checkbox("Skip automatic indexing", value=False)

    if uploaded_file is not None:
        st.info(f"**File:** {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

        if st.button("✅ Add Paper", type="primary", width="stretch"):
            with st.spinner("Processing PDF..."):
                try:
                    # Save uploaded file to temporary location
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = Path(tmp_file.name)

                    # Process tags
                    tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else None

                    # Add paper
                    manager = PaperManager()
                    paper_id = manager.add_paper_from_pdf(
                        tmp_path,
                        tags=tags_list,
                        collection_name=collection if collection else None
                    )

                    # Clean up temp file
                    tmp_path.unlink()

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
                    st.session_state.last_added_source = "upload"

                except Exception as e:
                    st.error(f"❌ Error adding paper: {e}")
                    st.exception(e)

    if (
        st.session_state.get("last_added_paper_id")
        and st.session_state.get("last_added_source") == "upload"
    ):
        _render_added_paper_summary(
            st.session_state["last_added_paper_id"],
            "upload",
        )


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
            with st.spinner("Downloading and processing paper..."):
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
                    st.session_state.last_added_source = "url"

                except Exception as e:
                    st.error(f"❌ Error adding paper: {e}")
                    st.exception(e)

    if (
        st.session_state.get("last_added_paper_id")
        and st.session_state.get("last_added_source") == "url"
    ):
        _render_added_paper_summary(
            st.session_state["last_added_paper_id"],
            "url",
        )
