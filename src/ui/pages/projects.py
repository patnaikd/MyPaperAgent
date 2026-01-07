"""Projects page - organize and manage papers in projects."""
import streamlit as st
from src.core.project_manager import ProjectManager, ProjectError
from src.core.paper_manager import PaperManager
from src.ui.ui_helpers import build_paper_detail_query, render_footer, sort_papers
from src.ui.components.paper_table import render_paper_table

def show_projects_page():
    """Display projects page."""
    st.title("📁 Projects")

    # Initialize manager
    try:
        project_manager = ProjectManager()
        paper_manager = PaperManager()
    except Exception as e:
        st.error(f"Failed to initialize Project Manager: {e}")
        render_footer()
        return

    # Check for selected project in session state
    if "selected_project_id" not in st.session_state:
        st.session_state.selected_project_id = None
    
    # Bulk actions state
    if "selected_paper_ids" not in st.session_state:
        st.session_state.selected_paper_ids = set()

    if st.session_state.selected_project_id:
        show_project_detail(project_manager, paper_manager)
    else:
        show_project_list(project_manager)

    render_footer()

def show_project_list(project_manager: ProjectManager):
    """List all projects and allow creating new ones."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Your Projects")
    with col2:
        if st.button("➕ New Project"):
            st.session_state.show_create_project = True

    if st.session_state.get("show_create_project"):
        with st.form("create_project_form"):
            name = st.text_input("Project Name", placeholder="e.g., LLM Research")
            description = st.text_area("Description (Markdown)", placeholder="Focusing on...")
            submit = st.form_submit_button("Create Project")
            
            if submit:
                if not name:
                    st.error("Project name is required.")
                else:
                    try:
                        project_id = project_manager.create_project(name, description)
                        st.success(f"Project '{name}' created!")
                        st.session_state.show_create_project = False
                        st.session_state.selected_project_id = project_id
                        st.rerun()
                    except ProjectError as e:
                        st.error(f"Error creating project: {e}")

    projects = project_manager.list_projects()
    
    if not projects:
        st.info("No projects yet. Create one to start organizing your papers!")
        return

    # Display projects in a grid or list
    for project in projects:
        with st.container():
            col_icon, col_info, col_action = st.columns([0.5, 4, 1])
            col_icon.markdown("### 📁")
            col_info.markdown(f"**{project.name}**")
            if project.description:
                # Truncate description for list view
                desc = project.description[:100] + "..." if len(project.description) > 100 else project.description
                col_info.markdown(f"_{desc}_")
            
            if col_action.button("Open", key=f"open_{project.id}"):
                st.session_state.selected_project_id = project.id
                st.rerun()
            st.divider()

def show_project_detail(project_manager: ProjectManager, paper_manager: PaperManager):
    """Show detailed view of a project."""
    project_id = st.session_state.selected_project_id
    try:
        project = project_manager.get_project(project_id)
    except Exception as e:
        st.error(f"Project not found: {e}")
        st.session_state.selected_project_id = None
        st.rerun()
        return

    # Header with Back button
    col_back, col_title, col_del = st.columns([0.5, 4, 1])
    if col_back.button("⬅️"):
        st.session_state.selected_project_id = None
        st.rerun()
    
    col_title.subheader(f"Project: {project.name}")
    
    if col_del.button("🗑️ Delete Project", type="secondary"):
        if st.session_state.get(f"confirm_delete_{project.id}"):
            project_manager.delete_project(project.id)
            st.session_state.selected_project_id = None
            st.rerun()
        else:
            st.session_state[f"confirm_delete_{project.id}"] = True
            st.warning("Click again to confirm deletion.")

    # Tabs for Description, Notes, and Papers
    tab1, tab2, tab3 = st.tabs(["📄 Description", "📓 Notes", "📚 Papers"])

    with tab1:
        st.markdown(project.description or "*No description provided.*")
        if st.button("Edit Description"):
            st.session_state.editing_desc = True
        
        if st.session_state.get("editing_desc"):
            new_desc = st.text_area("Edit Description (Markdown)", value=project.description or "", height=200)
            if st.button("Save Description"):
                project_manager.update_project(project.id, description=new_desc)
                st.session_state.editing_desc = False
                st.success("Description updated!")
                st.rerun()

    with tab2:
        st.markdown("### Project Notes")
        st.info("Markdown is supported here too. Use it for your research observations.")
        
        # Display existing notes
        st.markdown(project.notes or "*No notes yet.*")
        
        if st.button("Edit Notes"):
            st.session_state.editing_notes = True
            
        if st.session_state.get("editing_notes"):
            new_notes = st.text_area("Write Notes", value=project.notes or "", height=300)
            if st.button("Save Notes"):
                project_manager.update_project(project.id, notes=new_notes)
                st.session_state.editing_notes = False
                st.success("Notes saved!")
                st.rerun()

    with tab3:
        st.markdown("### Papers in this Project")
        
        # Add Paper to Project
        with st.expander("➕ Add Paper to Project"):
            all_papers = paper_manager.list_papers()
            # Filter out papers already in project
            current_papers = project_manager.get_papers_in_project(project.id)
            current_paper_ids = {p.id for p in current_papers}
            available_papers = [p for p in all_papers if p.id not in current_paper_ids]
            
            if not available_papers:
                st.warning("No new papers available in library to add. Add more papers first.")
            else:
                paper_to_add = st.selectbox(
                    "Select Paper", 
                    options=available_papers,
                    format_func=lambda p: f"{p.title[:60]}... ({p.year or 'N/A'})"
                )
                if st.button("Add to Project"):
                    project_manager.add_paper_to_project(paper_to_add.id, project.id)
                    st.success(f"Added '{paper_to_add.title}' to project!")
                    st.rerun()
        
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
                        options=[p for p in projects if p.id != project.id],
                        format_func=lambda p: p.name,
                        key="bulk_project_select_proj_view",
                        label_visibility="collapsed"
                    )
                    if col_btn.button("Add to Project", type="primary", use_container_width=True, key="bulk_add_btn_proj"):
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
                
                if col_clr.button("Clear Selection", use_container_width=True, key="bulk_clr_btn_proj"):
                    for paper_id in list(st.session_state.selected_paper_ids):
                        key = f"select_{paper_id}"
                        if key in st.session_state:
                            del st.session_state[key]
                    st.session_state.selected_paper_ids = set()
                    st.rerun()
            st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)

        # List papers using shared component
        papers = project_manager.get_papers_in_project(project.id)
        if not papers:
            st.info("This project has no papers yet.")
        else:
            # Sort papers consistently
            papers = sort_papers(papers)
            
            render_paper_table(
                papers=papers,
                paper_manager=paper_manager,
                project_manager=project_manager,
                show_selection=True,
                project_context_id=project.id
            )
