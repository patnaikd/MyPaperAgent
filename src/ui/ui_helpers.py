"""Shared UI helpers for Streamlit pages."""
import logging

import streamlit as st


logger = logging.getLogger(__name__)


def render_footer() -> None:
    """Render a minimal footer for each page."""
    st.markdown(
        '<div style="height: 4rem;"></div>'
        '<div style="text-align: center; color: #5b6670; font-size: 0.85rem; '
        'position: fixed; left: 0; right: 0; bottom: 0; '
        'background: #ffffff; border-top: 1px solid #d8dde3; '
        'padding: 0.4rem 0; z-index: 999;">'
        "© 2026 MyPaperAgent - Debprakash Patnaik"
        "</div>",
        unsafe_allow_html=True,
    )