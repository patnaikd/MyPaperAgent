"""Shared UI helpers for Streamlit pages."""
import logging
from typing import Any

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


def get_query_param(key: str) -> str | None:
    """Return a single query param value when present."""
    params: dict[str, Any]
    try:
        params = dict(st.query_params)
    except Exception:
        params = st.experimental_get_query_params()
    value = params.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, str):
        return value
    return None


def set_query_params(**params: str | int | None) -> None:
    """Set query params, dropping None values."""
    cleaned = {key: str(value) for key, value in params.items() if value is not None}
    try:
        st.query_params.clear()
        st.query_params.update(cleaned)
    except Exception:
        st.experimental_set_query_params(**cleaned)


def build_paper_detail_query(paper_id: int | str) -> str:
    """Build a relative permalink for a paper detail page."""
    return f"?page=paper_detail&paper_id={paper_id}"
