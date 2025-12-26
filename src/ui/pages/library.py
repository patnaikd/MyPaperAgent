"""Library page - view and manage papers."""
import logging

import streamlit as st
from datetime import datetime

from src.core.paper_manager import PaperManager
from src.utils.database import ReadingStatus
from src.ui.ui_helpers import render_footer


logger = logging.getLogger(__name__)


def show_library_page():
    """Display library page with all papers."""
    st.title("📚 Paper Library")

    # Initialize manager
    try:
        manager = PaperManager()
    except Exception as e:
        st.error(f"Failed to initialize Paper Manager: {e}")
        render_footer()
        return

    # Filters
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

    with col1:
        status_options = ["All", "Unread", "Reading", "Completed"]
        if (
            "library_status_filter" in st.session_state
            and st.session_state["library_status_filter"] not in status_options
        ):
            st.session_state["library_status_filter"] = "All"

        status_filter = st.selectbox(
            "Filter by status",
            status_options,
            key="library_status_filter",
        )

        include_archived = st.checkbox(
            "Include archived",
            value=False,
            key="library_include_archived",
        )

        if include_archived:
            status_options.append("Archived")

    with col2:
        search_query = st.text_input("Search papers", placeholder="Search by title or author...")

    with col3:
        limit = st.number_input("Show", min_value=10, max_value=200, value=50, step=10)

    with col4:
        st.empty()

    st.markdown("---")

    # Quick stats
    try:
        total_papers = manager.get_paper_count()
        papers_for_stats = manager.list_papers(limit=1000)
        completed = sum(1 for p in papers_for_stats if p.status == ReadingStatus.COMPLETED.value)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Papers", total_papers)
        with col2:
            st.metric("Completed", completed)
        st.markdown("---")
    except Exception:
        st.metric("Total Papers", "N/A")
        st.markdown("---")

    # Get papers
    try:
        status_map = {
            "All": None,
            "Unread": ReadingStatus.UNREAD.value,
            "Reading": ReadingStatus.READING.value,
            "Completed": ReadingStatus.COMPLETED.value,
            "Archived": ReadingStatus.ARCHIVED.value,
        }

        papers = manager.list_papers(status=status_map[status_filter], limit=limit)

        if not include_archived and status_filter == "All":
            papers = [paper for paper in papers if paper.status != ReadingStatus.ARCHIVED.value]

        # Apply search filter if provided
        if search_query:
            search_lower = search_query.lower()
            papers = [
                p for p in papers
                if (p.title and search_lower in p.title.lower()) or
                   (p.authors and search_lower in p.authors.lower())
            ]

        if not papers:
            st.info("No papers found. Add your first paper using the 'Add Paper' page!")
            if st.button("➕ Go to Add Paper"):
                st.session_state.current_page = "add_paper"
                st.rerun()
            render_footer()
            return

        # Display count
        st.markdown(f"**Found {len(papers)} paper(s)**")
        st.markdown("")

        # Display papers in cards
        for paper in papers:
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    # Title
                    st.markdown(f"### {paper.title or 'Untitled Paper'}")

                    # Metadata
                    metadata_parts = []
                    if paper.authors:
                        authors = paper.authors if len(paper.authors) <= 100 else paper.authors[:97] + "..."
                        metadata_parts.append(f"👤 {authors}")
                    if paper.year:
                        metadata_parts.append(f"📅 {paper.year}")
                    if paper.page_count:
                        metadata_parts.append(f"📄 {paper.page_count} pages")

                    if metadata_parts:
                        st.markdown(" • ".join(metadata_parts))

                    # Abstract preview
                    if paper.abstract:
                        abstract_preview = paper.abstract[:200] + "..." if len(paper.abstract) > 200 else paper.abstract
                        st.caption(abstract_preview)

                with col2:
                    # Status badge
                    status_colors = {
                        "unread": "🔵",
                        "reading": "🟡",
                        "completed": "🟢",
                        "archived": "⚫"
                    }
                    st.markdown(f"{status_colors.get(paper.status, '⚪')} {paper.status.upper()}")

                    # Actions
                    if st.button("📖 View", key=f"view_{paper.id}", use_container_width=True):
                        st.session_state.selected_paper_id = paper.id
                        st.session_state.current_page = "paper_detail"
                        st.rerun()

                    # Status update
                    new_status = st.selectbox(
                        "Status",
                        ["unread", "reading", "completed", "archived"],
                        index=["unread", "reading", "completed", "archived"].index(paper.status),
                        key=f"status_{paper.id}",
                        label_visibility="collapsed"
                    )

                    if new_status != paper.status:
                        try:
                            manager.update_paper(paper.id, status=new_status)
                            st.success("Status updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update: {e}")

                st.markdown("---")

    except Exception as e:
        st.error(f"Error loading papers: {e}")
        st.exception(e)

    render_footer()