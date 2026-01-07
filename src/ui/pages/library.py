"""Library page - view and manage papers."""
import streamlit as st

from src.core.paper_manager import PaperManager
from src.core.project_manager import ProjectManager, ProjectError
from src.utils.database import ReadingStatus
from src.ui.ui_helpers import build_paper_detail_query, render_footer, sort_papers
from src.ui.components.paper_table import render_paper_table


def show_library_page():
    """Display library page with all papers."""
    st.title("📚 Paper Library")

    # Initialize managers
    try:
        manager = PaperManager()
        project_manager = ProjectManager()
    except Exception as e:
        st.error(f"Failed to initialize managers: {e}")
        render_footer()
        return

    # Bulk actions state
    if "selected_paper_ids" not in st.session_state:
        st.session_state.selected_paper_ids = set()

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

        # Apply sorting
        papers = sort_papers(papers)

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

        # Bulk Action Bar
        selected_ids = st.session_state.get("selected_paper_ids", set())
        if selected_ids:
            with st.container():
                st.markdown(f"**With {len(selected_ids)} selected paper(s):**")
                col_proj, col_btn, col_clr = st.columns([3, 1, 1])
                
                projects = project_manager.list_projects()
                if not projects:
                    col_proj.warning("Create a project first to use bulk actions.")
                else:
                    target_project = col_proj.selectbox(
                        "Target Project",
                        options=projects,
                        format_func=lambda p: p.name,
                        key="bulk_project_select",
                        label_visibility="collapsed"
                    )
                    if col_btn.button("Add to Project", type="primary", use_container_width=True):
                        try:
                            for paper_id in selected_ids:
                                project_manager.add_paper_to_project(paper_id, target_project.id)
                                key = f"select_{paper_id}"
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.success(f"Added {len(selected_ids)} papers to '{target_project.name}'!")
                            st.session_state.selected_paper_ids = set()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                if col_clr.button("Clear Selection", use_container_width=True):
                    for paper_id in list(st.session_state.selected_paper_ids):
                        key = f"select_{paper_id}"
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state.selected_paper_ids = set()
                    st.rerun()
            st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

        # Display papers using shared component
        render_paper_table(
            papers=papers,
            paper_manager=manager,
            project_manager=project_manager,
            show_selection=True
        )

    except Exception as e:
        st.error(f"Error loading papers: {e}")
        st.exception(e)

    render_footer()
