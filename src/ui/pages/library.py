"""Library page - view and manage papers."""
import streamlit as st

from src.core.paper_manager import PaperManager
from src.core.project_manager import ProjectManager, ProjectError
from src.utils.database import ReadingStatus
from src.ui.ui_helpers import build_paper_detail_query, render_footer


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

        status_priority = {
            ReadingStatus.READING.value: 0,
            ReadingStatus.UNREAD.value: 1,
            ReadingStatus.COMPLETED.value: 2,
            ReadingStatus.ARCHIVED.value: 3,
        }
        papers = sorted(
            papers,
            key=lambda paper: (
                status_priority.get(paper.status, 4),
                -(paper.year or -1),
                (paper.title or "").lower(),
            ),
        )

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
            st.markdown("---")

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

        header = st.columns([0.4, 3.1, 2, 2, 0.8, 0.8, 1.4, 0.8])
        # header[0] is for checkbox
        header[1].markdown("**Title**")
        header[2].markdown("**Authors**")
        header[3].markdown("**Projects**")
        header[4].markdown("**Year**")
        header[5].markdown("**Pages**")
        header[6].markdown("**Status**")
        header[7].markdown("**Open**")
        st.markdown("---")

        for paper in papers:
            authors = ""
            if paper.authors:
                authors = paper.authors if len(paper.authors) <= 60 else paper.authors[:57] + "..."

            # Get projects for this paper
            paper_projects = project_manager.get_projects_for_paper(paper.id)
            project_names = ", ".join([p.name for p in paper_projects]) if paper_projects else ""
            if len(project_names) > 40:
                project_names = project_names[:37] + "..."

            cols = st.columns([0.4, 3.1, 2, 2, 0.8, 0.8, 1.4, 0.8])
            
            # Checkbox
            is_selected = paper.id in st.session_state.selected_paper_ids
            if cols[0].checkbox(f"Select {paper.title[:20]}...", value=is_selected, key=f"select_{paper.id}", label_visibility="collapsed"):
                if paper.id not in st.session_state.selected_paper_ids:
                    st.session_state.selected_paper_ids.add(paper.id)
                    st.rerun()
            else:
                if paper.id in st.session_state.selected_paper_ids:
                    st.session_state.selected_paper_ids.remove(paper.id)
                    st.rerun()

            cols[1].write(paper.title or "Untitled Paper")
            cols[2].write(authors)
            cols[3].write(project_names)
            cols[4].write(paper.year or "")
            cols[5].write(paper.page_count or "")

            current_label = status_to_label.get(paper.status, "🔵 unread")
            selected_label = cols[6].selectbox(
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

            cols[7].link_button(
                "Open",
                build_paper_detail_query(paper.id),
                use_container_width=True,
            )

        st.markdown("---")

    except Exception as e:
        st.error(f"Error loading papers: {e}")
        st.exception(e)

    render_footer()
