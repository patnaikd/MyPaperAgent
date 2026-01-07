"""Shared component for rendering the paper table."""
import streamlit as st
from src.core.paper_manager import PaperManager
from src.core.project_manager import ProjectManager
from src.utils.database import ReadingStatus
from src.ui.ui_helpers import build_paper_detail_query

def render_paper_table(
    papers: list, 
    paper_manager: PaperManager, 
    project_manager: ProjectManager,
    show_selection: bool = True,
    project_context_id: int = None
):
    """
    Render a consistent paper table.
    
    Args:
        papers: List of paper objects or dicts (must have id, title, authors, year, page_count, status)
        paper_manager: Instance of PaperManager
        project_manager: Instance of ProjectManager
        show_selection: Whether to show checkboxes for bulk actions
        project_context_id: If set, adds a 'Remove from Project' button
    """
    if not papers:
        st.info("No papers found matching your criteria.")
        return

    # Status options
    status_options = [
        ("unread", "🔵 unread"),
        ("reading", "🟡 reading"),
        ("completed", "🟢 completed"),
        ("archived", "⚫ archived"),
    ]
    status_labels = [label for _, label in status_options]
    status_to_label = {value: label for value, label in status_options}
    label_to_status = {label: value for value, label in status_options}

    # Inject CSS for more compact rows
    st.markdown("""
        <style>
            [data-testid="stVerticalBlock"] > div {
                padding-top: 0.1rem !important;
                padding-bottom: 0.1rem !important;
            }
            [data-testid="stHorizontalBlock"] {
                gap: 0.5rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Define columns
    col_widths = [0.4, 3.1, 2, 2, 0.8, 0.8, 1.4, 0.8]
    if project_context_id:
        col_widths.append(0.8) # For remove button

    header = st.columns(col_widths)
    start_idx = 0
    if show_selection:
        # header[0] is for checkbox
        start_idx = 1

    header[start_idx].markdown("**Title**")
    header[start_idx+1].markdown("**Authors**")
    header[start_idx+2].markdown("**Projects**")
    header[start_idx+3].markdown("**Year**")
    header[start_idx+4].markdown("**Pages**")
    header[start_idx+5].markdown("**Status**")
    header[start_idx+6].markdown("**Open**")
    if project_context_id:
        header[start_idx+7].markdown("**Unlink**")
    
    st.markdown("<hr style='margin: 0.2rem 0; border: none; border-top: 1px solid #ddd;'>", unsafe_allow_html=True)

    for paper in papers:
        authors = ""
        if paper.authors:
            authors = paper.authors if len(paper.authors) <= 60 else paper.authors[:57] + "..."

        # Get projects for this paper
        paper_projects = project_manager.get_projects_for_paper(paper.id)
        project_names = ", ".join([p.name for p in paper_projects]) if paper_projects else ""
        if len(project_names) > 40:
            project_names = project_names[:37] + "..."

        cols = st.columns(col_widths)
        
        # Checkbox
        if show_selection:
            is_selected = paper.id in st.session_state.get("selected_paper_ids", set())
            if cols[0].checkbox(f"Select {paper.title[:20]}...", value=is_selected, key=f"select_{paper.id}", label_visibility="collapsed"):
                if "selected_paper_ids" not in st.session_state:
                    st.session_state.selected_paper_ids = set()
                if paper.id not in st.session_state.selected_paper_ids:
                    st.session_state.selected_paper_ids.add(paper.id)
                    st.rerun()
            else:
                if "selected_paper_ids" in st.session_state and paper.id in st.session_state.selected_paper_ids:
                    st.session_state.selected_paper_ids.remove(paper.id)
                    st.rerun()

        cols[start_idx].write(paper.title or "Untitled Paper")
        cols[start_idx+1].write(authors)
        cols[start_idx+2].write(project_names)
        cols[start_idx+3].write(paper.year or "")
        cols[start_idx+4].write(paper.page_count or "")

        # Status dropdown
        current_label = status_to_label.get(paper.status, "🔵 unread")
        selected_label = cols[start_idx+5].selectbox(
            "Status",
            status_labels,
            index=status_labels.index(current_label),
            key=f"status_{paper.id}_{project_context_id or 'lib'}", # Add context to key
            label_visibility="collapsed",
        )
        new_status = label_to_status[selected_label]
        if new_status != paper.status:
            try:
                paper_manager.update_paper(paper.id, status=new_status)
                st.success("Status updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update: {e}")

        # Open button
        cols[start_idx+6].link_button(
            "Open",
            build_paper_detail_query(paper.id),
            use_container_width=True,
        )

        # Remove button (optional)
        if project_context_id:
            if cols[start_idx+7].button("❌", key=f"remove_p_{paper.id}_{project_context_id}"):
                project_manager.remove_paper_from_project(paper.id, project_context_id)
                st.success("Paper removed from project.")
                st.rerun()

        st.markdown("<hr style='margin: 0.1rem 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
