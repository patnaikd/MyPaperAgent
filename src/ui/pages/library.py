"""Library page - view and manage papers."""
import streamlit as st

from src.core.paper_manager import PaperManager
from src.utils.database import ReadingStatus
from src.ui.ui_helpers import render_footer


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

        # Display count and stats
        try:
            total_papers = manager.get_paper_count()
            papers_for_stats = manager.list_papers(limit=1000)
            completed = sum(
                1 for p in papers_for_stats if p.status == ReadingStatus.COMPLETED.value
            )
        except Exception:
            total_papers = "N/A"
            completed = "N/A"
        col1, col2, col3 = st.columns([2.5, 1, 1])
        with col1:
            st.markdown(f"**Found {len(papers)} paper(s)**")
        with col2:
            st.metric("Total Papers", total_papers)
        with col3:
            st.metric("Completed", completed)
        st.markdown("")

        # Display papers in a table-like layout with actions
        status_options = [
            ("unread", "🔵 unread"),
            ("reading", "🟡 reading"),
            ("completed", "🟢 completed"),
            ("archived", "⚫ archived"),
        ]
        status_labels = [label for _, label in status_options]
        status_to_label = {value: label for value, label in status_options}
        label_to_status = {label: value for value, label in status_options}

        header = st.columns([3.5, 2.5, 1, 1, 1.5, 1])
        header[0].markdown("**Title**")
        header[1].markdown("**Authors**")
        header[2].markdown("**Year**")
        header[3].markdown("**Pages**")
        header[4].markdown("**Status**")
        header[5].markdown("**Open**")
        st.markdown("---")

        for paper in papers:
            authors = ""
            if paper.authors:
                authors = paper.authors if len(paper.authors) <= 100 else paper.authors[:97] + "..."

            cols = st.columns([3.5, 2.5, 1, 1, 1.5, 1])
            cols[0].write(paper.title or "Untitled Paper")
            cols[1].write(authors)
            cols[2].write(paper.year or "")
            cols[3].write(paper.page_count or "")

            current_label = status_to_label.get(paper.status, "🔵 unread")
            selected_label = cols[4].selectbox(
                "Status",
                status_labels,
                index=status_labels.index(current_label),
                key=f"status_{paper.id}",
                label_visibility="collapsed",
            )
            new_status = label_to_status[selected_label]
            if new_status != paper.status:
                try:
                    manager.update_paper(paper.id, status=new_status)
                    st.success("Status updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update: {e}")

            if cols[5].button("Open", key=f"open_{paper.id}"):
                st.session_state.selected_paper_id = paper.id
                st.session_state.current_page = "paper_detail"
                st.rerun()

        st.markdown("---")

    except Exception as e:
        st.error(f"Error loading papers: {e}")
        st.exception(e)

    render_footer()
