"""Main Streamlit application for MyPaperAgent."""
import streamlit as st
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="MyPaperAgent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .paper-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "Library"
if "selected_paper_id" not in st.session_state:
    st.session_state.selected_paper_id = None

# Sidebar navigation
with st.sidebar:
    st.title("📚 MyPaperAgent")
    st.markdown("---")

    # Navigation menu
    st.subheader("Navigation")

    pages = {
        "🏠 Library": "library",
        "➕ Add Paper": "add_paper",
        "🔍 Search": "search",
        "🌐 Discover": "discover",
        "⚙️ Settings": "settings",
    }

    for label, page_id in pages.items():
        if st.button(label, key=f"nav_{page_id}", use_container_width=True):
            st.session_state.current_page = page_id
            st.rerun()

    st.markdown("---")

    # Quick stats
    st.subheader("Quick Stats")
    try:
        from src.core.paper_manager import PaperManager
        manager = PaperManager()
        total_papers = manager.get_paper_count()
        st.metric("Total Papers", total_papers)
    except Exception:
        st.metric("Total Papers", "N/A")

    st.markdown("---")
    st.caption("Built with Claude Agent SDK")

# Main content area
def main():
    """Main application logic."""
    current_page = st.session_state.current_page

    if current_page == "library":
        from src.ui.pages.library import show_library_page
        show_library_page()
    elif current_page == "add_paper":
        from src.ui.pages.add_paper import show_add_paper_page
        show_add_paper_page()
    elif current_page == "search":
        from src.ui.pages.search import show_search_page
        show_search_page()
    elif current_page == "discover":
        from src.ui.pages.discover import show_discover_page
        show_discover_page()
    elif current_page == "settings":
        from src.ui.pages.settings import show_settings_page
        show_settings_page()
    elif current_page == "paper_detail":
        from src.ui.pages.paper_detail import show_paper_detail_page
        show_paper_detail_page()
    else:
        # Default to library
        from src.ui.pages.library import show_library_page
        show_library_page()

if __name__ == "__main__":
    main()
