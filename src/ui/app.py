"""Main Streamlit application for MyPaperAgent."""
import logging
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.utils.config import get_config


config = get_config()
config.ensure_directories()

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(filename)s:%(lineno)d %(message)s"
_LOG_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
_LOG_FILE = config.log_file.parent / f"mypaperagent_{_LOG_TIMESTAMP}.log"

root_logger = logging.getLogger()
log_level = getattr(logging, config.log_level.upper(), logging.INFO)
logging_configured = False

if not root_logger.handlers:
    logging.basicConfig(
        level=log_level,
        format=_LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(_LOG_FILE),
        ],
    )
    logging_configured = True
else:
    root_logger.setLevel(log_level)
    has_console = any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        for handler in root_logger.handlers
    )
    if not has_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root_logger.addHandler(console_handler)
        logging_configured = True
    has_log_file = any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", None) == str(_LOG_FILE)
        for handler in root_logger.handlers
    )
    if not has_log_file:
        file_handler = logging.FileHandler(_LOG_FILE)
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root_logger.addHandler(file_handler)
        logging_configured = True

logger = logging.getLogger(__name__)
if logging_configured:
    logger.info("Logging configured: level=%s file=%s", config.log_level.upper(), _LOG_FILE)

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
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600&family=Source+Serif+4:wght@600&display=swap');

    :root {
        --ink: #1b1f23;
        --muted: #5b6670;
        --accent: #1a4e8a;
        --accent-soft: #e7eef7;
        --surface: #ffffff;
        --surface-muted: #f6f7f9;
        --border: #d8dde3;
    }

    /* Remove blank space at top and bottom */ 
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 0rem;
    }

    html, body, [class*="css"]  {
        font-family: 'Source Sans 3', sans-serif;
        color: var(--ink);
        background-color: var(--surface);
        font-size: 16px;
    }

    .stApp {
        background-color: var(--surface);
    }
            
    .stAppToolbar {
        # background-image: url('https://picsum.photos/1024/64');
        # background-image: url('https://fastly.picsum.photos/id/560/1024/64.jpg?hmac=ZWRIwsI-S1oDpkzWzcUmgKWyHp-nhIGRaYp518iH3Yk');
        # background-image: url('/app/static/header.jpg');
        background-image: url('/app/static/my-paper-agent.png');
        background-repeat: no-repeat;
        background-size: contain;
        background-position: left center;
        background-color: black;
        color: gray;
    }

    .main {
        padding: 0.5rem 1.2rem;
    }

    [data-testid="stAppHeader"] {
        background-color: var(--surface);
        border-bottom: 1px solid var(--border);
    }

    h1, h2, h3, h4, h5 {
        font-family: 'Source Serif 4', serif;
        color: var(--ink);
        letter-spacing: -0.01em;
    }

    .stButton>button {
        width: 100%;
        background-color: var(--accent);
        color: #ffffff;
        border: 1px solid var(--accent);
        border-radius: 6px;
        padding: 0.45rem 0.8rem;
        font-weight: 600;
    }

    .stButton>button:hover {
        background-color: #153e6d;
        border-color: #153e6d;
    }

    .paper-card {
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid var(--border);
        margin-bottom: 1rem;
        background-color: var(--surface);
    }

    .metric-card {
        background-color: var(--surface-muted);
        padding: 1rem;
        border-radius: 6px;
        text-align: center;
        border: 1px solid var(--border);
    }

    [data-testid="stSidebar"] {
        background-color: var(--surface-muted);
        border-right: 1px solid var(--border);
        min-width: 80px;
        max-width: 80px;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label {
        color: var(--ink);
    }

    [data-testid="stSidebar"] .stButton>button {
        width: 60px;
        height: 60px;
        padding: 0;
        border-radius: 5px;
        margin: 0.25rem auto;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: var(--surface);
        color: var(--accent);
        border: 1px solid var(--border);
        line-height: 1;
    }

    [data-testid="stSidebar"] .stButton>button:hover {
        background-color: var(--accent-soft);
        border-color: var(--accent);
    }

    [data-testid="stSidebarContent"] [data-testid="stBaseButton-secondary"] {
        width: 60px;
    }

    [data-testid="stMetric"] {
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 0.6rem 0.8rem;
    }

    [data-testid="stMetric"] label {
        color: var(--muted);
        font-weight: 600;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div,
    .stNumberInput input {
        border-radius: 6px;
        border: 1px solid var(--border);
        background-color: var(--surface);
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "Library"
if "selected_paper_id" not in st.session_state:
    st.session_state.selected_paper_id = None
if "session_started" not in st.session_state:
    st.session_state.session_started = True
    logger.info("Streamlit UI session started")

# Sidebar navigation
with st.sidebar:
    pages = {
        "🏠": ("Library", "library"),
        "➕": ("Add Paper", "add_paper"),
        "🔍": ("Search", "search"),
        "🌐": ("Discover", "discover"),
        "⚙️": ("Settings", "settings"),
    }

    for icon, (label, page_id) in pages.items():
        if st.button(icon, key=f"nav_{page_id}", help=label):
            previous_page = st.session_state.current_page
            st.session_state.current_page = page_id
            logger.info("Navigation: %s -> %s", previous_page, page_id)
            st.rerun()

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
        logger.warning("Unknown page '%s', defaulting to library", current_page)
        from src.ui.pages.library import show_library_page
        show_library_page()

if __name__ == "__main__":
    main()
