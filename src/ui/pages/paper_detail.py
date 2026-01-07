"""Paper detail page - view paper with AI features."""
import json
import re
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from streamlit_pdf_viewer import pdf_viewer

from src.agents.author_info import AuthorInfoAgent
from src.agents.qa_agent import QAAgent
from src.agents.quiz_generator import QuizGenerator
from src.agents.summarizer import SummarizationAgent
from src.core.note_manager import NoteManager
from src.core.paper_manager import PaperManager
from src.core.project_manager import ProjectManager
from src.core.qa_manager import QAHistoryManager
from src.utils.database import NoteType, ReadingStatus
from src.ui.ui_helpers import build_paper_detail_query, render_footer
SPEECHIFY_ICON_URL = "https://cdn.speechify.com/web/assets/favicon.png"


def show_paper_detail_page():
    """Display detailed paper view with AI features."""
    paper_id = st.session_state.get("selected_paper_id")

    if not paper_id:
        st.warning("No paper selected. Please go to the library and select a paper.")
        if st.button("🏠 Go to Library"):
            st.session_state.current_page = "library"
            st.rerun()
        render_footer()
        return

    try:
        manager = PaperManager()
        project_manager = ProjectManager()
        paper = manager.get_paper(paper_id)
    except Exception as e:
        st.error(f"Failed to load paper or initialize project manager: {e}")
        render_footer()
        return

    # Header
    st.title("📖 Paper Details")

    # Back button
    if st.button("⬅️ Back to Library"):
        st.session_state.current_page = "library"
        st.rerun()

    st.markdown("---")

    # Paper metadata
    title_col, link_col = st.columns([4, 1])
    with title_col:
        st.markdown(f"## {paper.title or 'Untitled Paper'}")
    with link_col:
        st.link_button(
            "🔗 Permalink",
            build_paper_detail_query(paper_id),
            use_container_width=True,
        )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Pages", paper.page_count or "N/A")
    with col2:
        st.metric("📅 Year", paper.year or "Unknown")
    with col3:
        status_colors = {"unread": "🔵", "reading": "🟡", "completed": "🟢", "archived": "⚫"}
        st.metric("Status", f"{status_colors.get(paper.status, '⚪')} {paper.status.title()}")
        status_options = [
            (ReadingStatus.UNREAD.value, "🔵 unread"),
            (ReadingStatus.READING.value, "🟡 reading"),
            (ReadingStatus.COMPLETED.value, "🟢 completed"),
            (ReadingStatus.ARCHIVED.value, "⚫ archived"),
        ]
        status_labels = [label for _, label in status_options]
        status_to_label = {value: label for value, label in status_options}
        label_to_status = {label: value for value, label in status_options}
        current_label = status_to_label.get(
            paper.status,
            status_to_label[ReadingStatus.UNREAD.value],
        )
        selected_label = st.selectbox(
            "Update status",
            status_labels,
            index=status_labels.index(current_label),
            key=f"detail_status_{paper_id}",
        )
        new_status = label_to_status[selected_label]
        if new_status != paper.status:
            try:
                manager.update_paper_status(paper_id, new_status)
                st.success("Status updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update status: {e}")

    # Project Management
    st.markdown("---")
    show_project_management(paper_id, project_manager)

    if paper.authors:
        st.markdown(f"**Authors:** {paper.authors}")
    if paper.journal:
        st.markdown(f"**Published in:** {paper.journal}")
    if paper.doi:
        st.markdown(f"**DOI:** {paper.doi}")
    speechify_url = paper.speechify_url or ""
    listen_url = speechify_url or "https://app.speechify.com/?folder=69c666f7-edff-4893-84fc-28bed5a7b430"
    edit_key = f"edit_speechify_{paper_id}"
    speechify_key = f"speechify_url_{paper_id}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    if paper.url:
        listen_col, copy_col, url_col  = st.columns([1, 1, 4])
        with url_col:
            st.markdown(f"**URL:** [{paper.url}]({paper.url})")
        with copy_col:
            arxiv_pdf_url = _get_arxiv_pdf_url(paper)
            if arxiv_pdf_url:
                _render_copy_button(
                    arxiv_pdf_url,
                    key=f"copy_arxiv_{paper_id}",
                    label="Copy PDF URL",
                )
        with listen_col:
            st.markdown(
                f"""
                <a href="{listen_url}" target="_blank"
                   style="display:inline-flex; align-items:center; gap:0.4rem;
                          text-decoration:none; border:1px solid #d0d7de;
                          padding:0.25rem 0.6rem; border-radius:0.5rem;
                          background:#ffffff;">
                    <img src="{SPEECHIFY_ICON_URL}" alt="Speechify" width="18" height="18" />
                    <span style="color:#111111; font-size:0.9rem;">Listen</span>
                </a>
                """,
                unsafe_allow_html=True,
            )

    if speechify_url and not st.session_state[edit_key]:
        if st.button("✏️ Edit Speechify URL", key=f"edit_speechify_btn_{paper_id}"):
            st.session_state[speechify_key] = speechify_url
            st.session_state[edit_key] = True
            st.rerun()

    show_form = not speechify_url or st.session_state[edit_key]
    if show_form:
        if speechify_key not in st.session_state:
            st.session_state[speechify_key] = speechify_url
        st.markdown("**Speechify URL:**")
        speechify_input = st.text_input(
            "Speechify URL",
            placeholder="https://app.speechify.com/...",
            key=speechify_key,
            help="Optional link to a Speechify version of this paper.",
            label_visibility="collapsed",
        )
        form_col1, form_col2 = st.columns([1, 1])
        with form_col1:
            save_speechify = st.button("💾 Save", key=f"save_speechify_{paper_id}")
        with form_col2:
            cancel_edit = False
            if speechify_url:
                cancel_edit = st.button(
                    "Cancel",
                    key=f"cancel_speechify_{paper_id}",
                )
        if save_speechify:
            try:
                manager.update_speechify_url(paper_id, speechify_input.strip())
                st.session_state[edit_key] = False
                st.success("Speechify URL updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update Speechify URL: {e}")
        if cancel_edit:
            st.session_state[edit_key] = False
            st.rerun()

    # Abstract
    if paper.abstract:
        with st.expander("📝 Abstract", expanded=True):
            st.write(paper.abstract)

    st.markdown("---")

    # Tabs for different features
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "💭 Summarize",
            "👥 About Authors",
            "📚 References",
            "🧾 Citations",
            "📄 View PDF",
            "❓ Ask Questions",
            "📝 Quiz",
            "📔 Notes",
        ]
    )

    with tab1:
        show_summarize_tab(paper_id)

    with tab2:
        show_author_info_tab(paper)

    with tab3:
        show_references_tab(paper.id)

    with tab4:
        show_citations_tab(paper.id)

    with tab5:
        show_pdf_tab(paper)

    with tab6:
        show_qa_tab(paper_id)

    with tab7:
        show_quiz_tab(paper_id)

    with tab8:
        show_notes_tab(paper_id)

    render_footer()


def show_summarize_tab(paper_id: int):
    """Show summarization interface."""
    st.markdown("### 💭 Generate AI Summary")

    col1, col2 = st.columns([2, 1])

    with col1:
        summary_level = st.selectbox(
            "Summary Level",
            ["quick", "detailed", "full"],
            format_func=lambda x: {
                "quick": "Quick (2-3 paragraphs)",
                "detailed": "Detailed (key findings)",
                "full": "Full (comprehensive analysis)"
            }[x]
        )

    with col2:
        save_as_note = st.checkbox("Save as note", value=True)

    if st.button("✨ Generate Summary", type="primary", width="stretch"):
        with st.spinner(f"Generating {summary_level} summary with Claude..."):
            try:
                agent = SummarizationAgent()
                summary = agent.summarize_paper(
                    paper_id,
                    level=summary_level,
                    save_as_note=save_as_note
                )

                st.success("✅ Summary generated!")
                st.markdown("---")
                st.markdown(summary)

                if save_as_note:
                    st.info("💾 Summary stored in notes (skips duplicates)")

            except Exception as e:
                st.error(f"Failed to generate summary: {e}")
                st.exception(e)

    # Show existing summaries
    st.markdown("---")
    st.markdown("#### Previous Summaries")

    try:
        note_manager = NoteManager()
        summaries = note_manager.get_notes(
            paper_id,
            note_type=NoteType.AI_GENERATED.value
        )

        # Filter for summaries
        summary_notes = [n for n in summaries if "Summary" in (n.section or "")]

        if summary_notes:
            for note in summary_notes[:3]:  # Show last 3
                with st.expander(f"📄 {note.section} - {note.created_at.strftime('%Y-%m-%d %H:%M')}"):
                    st.markdown(note.content)
        else:
            st.info("No previous summaries. Generate one above!")

    except Exception as e:
        st.warning(f"Could not load previous summaries: {e}")


def show_author_info_tab(paper) -> None:
    """Show author information gathered from web sources."""
    st.markdown("### 👥 About Authors")
    st.caption("Author profiles are collected when the paper is added from a URL.")

    can_refresh = bool(
        paper.arxiv_id
        or paper.doi
        or _extract_arxiv_id_from_url(paper.url or "")
        or _extract_doi_from_url(paper.url or "")
    )
    if can_refresh:
        if st.button("🔁 Refresh from Semantic Scholar", width="stretch"):
            with st.spinner("Refreshing Semantic Scholar metadata..."):
                try:
                    manager = PaperManager()
                    manager.refresh_semantic_scholar_metadata(paper.id)
                    st.success("Semantic Scholar metadata updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to refresh Semantic Scholar metadata: {e}")
    else:
        st.info("Semantic Scholar refresh requires a DOI or arXiv ID.")

    author_infos, author_ts = AuthorInfoAgent.load_author_infos_with_timestamp(paper.id)
    paper_meta, meta_ts = AuthorInfoAgent.load_paper_metadata_with_timestamp(paper.id)

    if not author_infos and not paper_meta:
        st.info("No author metadata available for this paper yet.")
        return

    if author_ts:
        st.caption(f"Cached author info updated: {_format_timestamp(author_ts)}")

    if paper_meta:
        if meta_ts:
            st.caption(f"Cached paper metadata updated: {_format_timestamp(meta_ts)}")
        _render_paper_metadata(paper_meta)

    if not author_infos:
        st.info("No author profiles available yet.")
        return

    for info in author_infos:
        name = info.get("name", "Author")
        with st.expander(name, expanded=True):
            if isinstance(name, str) and name.strip():
                linkedin_url = _linkedin_search_url(name)
                st.markdown(
                    f"""
                    <a href="{linkedin_url}" target="_blank"
                       style="display:inline-flex; align-items:center; gap:0.4rem;
                              text-decoration:none; border:1px solid #d0d7de;
                              padding:0.25rem 0.6rem; border-radius:0.5rem;
                              background:#ffffff; color:#111111; font-size:0.9rem;">
                        🔗 LinkedIn
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
            if info.get("error"):
                st.warning(info["error"])
            introduction = info.get("introduction")
            if introduction:
                st.write(introduction)

            affiliation = info.get("affiliation")
            if affiliation:
                st.markdown(f"**Affiliation:** {affiliation}")

            homepage = info.get("homepage")
            if homepage:
                st.markdown(f"**Homepage:** [{homepage}]({homepage})")

            semantic_url = info.get("semantic_scholar_url")
            if semantic_url:
                st.markdown(f"**Semantic Scholar:** [{semantic_url}]({semantic_url})")

            dblp_url = info.get("dblp_url")
            if dblp_url:
                st.markdown(f"**DBLP:** [{dblp_url}]({dblp_url})")

            top_papers = info.get("top_cited_papers") or []
            if top_papers:
                st.markdown("**Top cited papers:**")
                for paper_info in top_papers:
                    title = paper_info.get("title", "Untitled")
                    citations = paper_info.get("citation_count")
                    year = paper_info.get("year")
                    label_parts = [title]
                    if year:
                        label_parts.append(str(year))
                    if citations is not None:
                        label_parts.append(f"{citations} citations")
                    label = " · ".join(label_parts)
                    url = paper_info.get("url")
                    if url:
                        st.markdown(f"- [{label}]({url})")
                    else:
                        st.markdown(f"- {label}")

            coauthors = info.get("coauthors") or []
            if coauthors:
                st.markdown(f"**Top co-authors:** {', '.join(coauthors)}")

            interests = info.get("research_interests") or []
            if interests:
                st.markdown(f"**Research interests:** {', '.join(interests)}")


def show_pdf_tab(paper) -> None:
    """Show PDF viewer for the selected paper."""
    st.markdown("### 📄 View PDF")

    if not paper.file_path:
        st.info("No local PDF available for this paper.")
        return

    pdf_path = Path(paper.file_path)
    if not pdf_path.exists():
        st.warning(f"PDF file not found at {pdf_path}")
        return

    try:
        pdf_bytes = pdf_path.read_bytes()
    except Exception as e:
        st.error(f"Failed to load PDF: {e}")
        return

    st.download_button(
        "Download PDF",
        data=pdf_bytes,
        file_name=pdf_path.name,
        mime="application/pdf",
        width="stretch",
    )

    pdf_viewer(pdf_bytes, height=800)


def show_qa_tab(paper_id: int):
    """Show Q&A interface."""
    st.markdown("### ❓ Ask Questions About This Paper")

    qa_manager = QAHistoryManager()

    # Question input
    question = st.text_area(
        "Your Question",
        placeholder="What is the main contribution of this paper?",
        height=100
    )

    if st.button("🔍 Get Answer", type="primary", disabled=not question, width="stretch"):
        with st.spinner("Generating answer with Claude..."):
            try:
                agent = QAAgent()
                result = agent.answer_question(question, paper_id=paper_id)

                st.success("✅ Answer generated!")
                st.markdown("---")

                # Display answer
                st.markdown("#### Answer")
                st.markdown(result["answer"])

                # Display sources
                if result.get("sources"):
                    st.markdown("#### Sources")
                    for source in result["sources"]:
                        st.caption(f"📄 Paper {source['paper_id']}: {source['title']}")

                if result.get("saved"):
                    st.info("💾 Question saved to history")
                else:
                    st.info("ℹ️ Question already saved")
            except Exception as e:
                st.error(f"Failed to generate answer: {e}")
                st.exception(e)

    # Q&A history
    st.markdown("---")
    st.markdown("#### Recent Questions")

    # Show history
    try:
        history_entries = qa_manager.get_entries(paper_id, limit=5)
        if history_entries:
            for entry in history_entries:
                with st.expander(f"Q: {entry.question[:100]}..."):
                    st.markdown(f"**Q:** {entry.question}")
                    st.markdown(f"**A:** {entry.answer}")
                    sources = qa_manager.deserialize_sources(entry.sources)
                    if sources:
                        st.markdown("**Sources:**")
                        seen = set()
                        for source in sources:
                            key = (source.get("paper_id"), source.get("title"))
                            if key in seen:
                                continue
                            seen.add(key)
                            st.caption(
                                f"📄 Paper {source.get('paper_id')}: {source.get('title')}"
                            )
        else:
            st.info("No questions asked yet. Ask your first question above!")
    except Exception as e:
        st.warning(f"Could not load question history: {e}")


def show_quiz_tab(paper_id: int):
    """Show quiz generation interface."""
    st.markdown("### 📝 Generate Quiz Questions")

    col1, col2 = st.columns(2)

    with col1:
        num_questions = st.slider("Number of questions", min_value=3, max_value=20, value=5)

    with col2:
        difficulty = st.selectbox(
            "Difficulty",
            ["easy", "medium", "hard", "adaptive"],
            index=3
        )

    if st.button("✨ Generate Quiz", type="primary", width="stretch"):
        with st.spinner(f"Generating {num_questions} questions with Claude..."):
            try:
                generator = QuizGenerator()
                questions = generator.generate_quiz(
                    paper_id,
                    num_questions=num_questions,
                    difficulty=difficulty
                )

                if questions:
                    st.success(f"✅ Generated {len(questions)} questions!")
                    st.markdown("---")

                    # Display questions
                    for i, q in enumerate(questions, 1):
                        with st.expander(f"Question {i}: {q['question'][:80]}..."):
                            st.markdown(f"**Question:** {q['question']}")
                            st.markdown(f"**Answer:** {q['answer']}")
                            if q.get('explanation'):
                                st.info(q['explanation'])
                            st.caption(f"Difficulty: {q.get('difficulty', 'medium')}")

                    st.info("💾 Questions stored in database (skips duplicates)")

                else:
                    st.warning("Failed to generate questions. Please try again.")

            except Exception as e:
                st.error(f"Failed to generate quiz: {e}")
                st.exception(e)

    # Show existing quiz questions
    st.markdown("---")
    st.markdown("#### Saved Quiz Questions")

    try:
        generator = QuizGenerator()
        existing_questions = generator.get_quiz_questions(paper_id, limit=10)

        if existing_questions:
            st.info(f"Found {len(existing_questions)} saved questions")
            for i, q in enumerate(existing_questions[:5], 1):
                with st.expander(f"Q{i}: {q.question[:80]}..."):
                    st.markdown(f"**Question:** {q.question}")
                    st.markdown(f"**Answer:** {q.answer}")
                    if q.explanation:
                        st.info(q.explanation)
                    st.caption(f"Difficulty: {q.difficulty}")
        else:
            st.info("No saved questions yet. Generate some above!")

    except Exception as e:
        st.warning(f"Could not load quiz questions: {e}")


def show_notes_tab(paper_id: int):
    """Show notes interface."""
    st.markdown("### 📔 Personal Notes")

    # Add new note
    with st.expander("➕ Add New Note", expanded=True):
        note_content = st.text_area(
            "Note Content",
            placeholder="Write your thoughts about this paper...",
            height=150
        )

        section = st.text_input(
            "Section (optional)",
            placeholder="e.g., Methodology, Results, Ideas"
        )

        if st.button("💾 Save Note", disabled=not note_content, width="stretch"):
            try:
                note_manager = NoteManager()
                _, created = note_manager.add_note_if_new(
                    paper_id,
                    note_content,
                    section=section if section else None
                )
                if created:
                    st.success("✅ Note saved successfully!")
                else:
                    st.info("ℹ️ That note is already saved.")
                st.rerun()

            except Exception as e:
                st.error(f"Failed to save note: {e}")

    # Display existing notes
    st.markdown("---")
    st.markdown("#### Your Notes")

    try:
        note_manager = NoteManager()
        notes = note_manager.get_notes(paper_id, note_type=NoteType.PERSONAL.value)

        if notes:
            for note in notes:
                with st.container():
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        if note.section:
                            st.markdown(f"**{note.section}**")
                        st.write(note.content)
                        st.caption(f"📅 {note.created_at.strftime('%Y-%m-%d %H:%M')}")

                    with col2:
                        if st.button("🗑️", key=f"delete_note_{note.id}"):
                            note_manager.delete_note(note.id)
                            st.success("Note deleted")
                            st.rerun()

                    st.markdown("---")
        else:
            st.info("No notes yet. Add your first note above!")

    except Exception as e:
        st.error(f"Failed to load notes: {e}")


def show_references_tab(paper_id: int) -> None:
    """Show Semantic Scholar references."""
    st.markdown("### 📚 References")

    paper_meta, meta_ts = AuthorInfoAgent.load_paper_metadata_with_timestamp(paper_id)
    if not paper_meta:
        st.info("No Semantic Scholar metadata available. Refresh in the Authors tab.")
        return

    references = paper_meta.get("references") or []
    if meta_ts:
        st.caption(f"Cached metadata updated: {_format_timestamp(meta_ts)}")

    if not references:
        st.info("No references available for this paper.")
        return

    st.caption(f"Loaded {len(references)} references from Semantic Scholar.")

    manager = PaperManager()
    related_map = _get_related_paper_map()
    for index, ref in enumerate(references, start=1):
        title = ref.get("title") or "Untitled"
        year = ref.get("year")
        authors = _format_reference_authors(ref.get("authors"))
        ref_id = ref.get("paperId") or ref.get("paper_id")
        semantic_url = _semantic_scholar_paper_url(ref_id) if ref_id else None
        existing_paper = _resolve_related_paper(manager, related_map, ref_id)

        with st.container():
            cols = st.columns([4, 1.2])
            with cols[0]:
                st.markdown(f"**{index}. {title}**")
                details = []
                if authors:
                    details.append(authors)
                if year:
                    details.append(str(year))
                if details:
                    st.caption(" · ".join(details))
                if semantic_url:
                    st.markdown(f"[View on Semantic Scholar]({semantic_url})")
            with cols[1]:
                if existing_paper:
                    if st.button(
                        "📖 Open Paper",
                        key=f"open_ref_{paper_id}_{ref_id}_{index}",
                    ):
                        st.session_state.selected_paper_id = existing_paper.id
                        st.session_state.current_page = "paper_detail"
                        st.rerun()
                elif ref_id:
                    if st.button(
                        "➕ Add Paper",
                        key=f"add_ref_{paper_id}_{ref_id}_{index}",
                    ):
                        _add_related_paper(str(ref_id))
                else:
                    st.caption("No ID available")

        st.markdown("---")


def show_citations_tab(paper_id: int) -> None:
    """Show Semantic Scholar citations."""
    st.markdown("### 🧾 Citations")

    paper_meta, meta_ts = AuthorInfoAgent.load_paper_metadata_with_timestamp(paper_id)
    if not paper_meta:
        st.info("No Semantic Scholar metadata available. Refresh in the Authors tab.")
        return

    citations = paper_meta.get("citations") or []
    if meta_ts:
        st.caption(f"Cached metadata updated: {_format_timestamp(meta_ts)}")

    if not citations:
        st.info("No citations available for this paper.")
        return

    st.caption(f"Loaded {len(citations)} citations from Semantic Scholar.")

    manager = PaperManager()
    related_map = _get_related_paper_map()
    for index, citation in enumerate(citations, start=1):
        title = citation.get("title") or "Untitled"
        year = citation.get("year")
        authors = _format_reference_authors(citation.get("authors"))
        cite_id = citation.get("paperId") or citation.get("paper_id")
        semantic_url = _semantic_scholar_paper_url(cite_id) if cite_id else None
        existing_paper = _resolve_related_paper(manager, related_map, cite_id)

        with st.container():
            cols = st.columns([4, 1.2])
            with cols[0]:
                st.markdown(f"**{index}. {title}**")
                details = []
                if authors:
                    details.append(authors)
                if year:
                    details.append(str(year))
                if details:
                    st.caption(" · ".join(details))
                if semantic_url:
                    st.markdown(f"[View on Semantic Scholar]({semantic_url})")
            with cols[1]:
                if existing_paper:
                    if st.button(
                        "📖 Open Paper",
                        key=f"open_cite_{paper_id}_{cite_id}_{index}",
                    ):
                        st.session_state.selected_paper_id = existing_paper.id
                        st.session_state.current_page = "paper_detail"
                        st.rerun()
                elif cite_id:
                    if st.button(
                        "➕ Add Paper",
                        key=f"add_cite_{paper_id}_{cite_id}_{index}",
                    ):
                        _add_related_paper(str(cite_id))
                else:
                    st.caption("No ID available")

        st.markdown("---")


def _extract_arxiv_id_from_url(url: str) -> str | None:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#]+)", url)
    if not match:
        return None
    arxiv_id = match.group(1)
    if arxiv_id.endswith(".pdf"):
        arxiv_id = arxiv_id[:-4]
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
    return arxiv_id or None


def _extract_doi_from_url(url: str) -> str | None:
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", url, re.IGNORECASE)
    if not match:
        return None
    return match.group(0).rstrip(").,;")


def _extract_arxiv_id_from_external_ids(external_ids: dict[str, Any]) -> str | None:
    if not external_ids:
        return None
    for key in ("arxiv", "ArXiv", "ARXIV"):
        value = external_ids.get(key)
        if value:
            return str(value)
    for key, value in external_ids.items():
        if key.lower() == "arxiv" and value:
            return str(value)
    return None


def _semantic_scholar_paper_url(paper_id: str | None) -> str | None:
    if not paper_id:
        return None
    return f"https://www.semanticscholar.org/paper/{paper_id}"


def _get_related_paper_map() -> dict[str, int]:
    stored = st.session_state.get("related_paper_map")
    if isinstance(stored, dict):
        return stored
    return {}


def _remember_related_paper(semantic_id: str, paper_id: int) -> None:
    related_map = _get_related_paper_map()
    related_map[str(semantic_id)] = paper_id
    st.session_state["related_paper_map"] = related_map


def _resolve_related_paper(
    manager: PaperManager,
    related_map: dict[str, int],
    semantic_id: str | None,
) -> Any:
    if not semantic_id:
        return None

    mapped_id = related_map.get(str(semantic_id))
    if mapped_id:
        try:
            return manager.get_paper(mapped_id)
        except Exception:
            return None

    return manager.get_paper_by_semantic_scholar_id(str(semantic_id))


def _format_reference_authors(authors: Any) -> str | None:
    if not authors:
        return None
    if isinstance(authors, str):
        return authors
    if isinstance(authors, list):
        names = []
        for author in authors:
            if isinstance(author, dict):
                name = author.get("name")
            else:
                name = author
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        if names:
            return ", ".join(names)
    return None


def _add_related_paper(reference_id: str) -> None:
    with st.spinner("Fetching Semantic Scholar metadata..."):
        try:
            agent = AuthorInfoAgent()
            paper_meta = agent.fetch_paper_metadata(reference_id)
            if not paper_meta:
                st.warning("No Semantic Scholar metadata returned for this reference.")
                return
            manager = PaperManager()
            semantic_id = paper_meta.get("paperId") or paper_meta.get("paper_id")
            if semantic_id:
                existing_paper = manager.get_paper_by_semantic_scholar_id(str(semantic_id))
                if existing_paper:
                    st.info(f"Paper already in library (ID {existing_paper.id}).")
                    return
            external_ids = paper_meta.get("externalIds") or {}
            arxiv_id = _extract_arxiv_id_from_external_ids(external_ids)
            if not arxiv_id:
                st.info("No arXiv ID found for this reference.")
                return
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            new_paper_id = manager.add_paper_from_url(pdf_url)
            if semantic_id:
                _remember_related_paper(str(semantic_id), new_paper_id)
            st.success(f"Added paper {new_paper_id} from arXiv {arxiv_id}.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to add reference: {e}")


def _linkedin_search_url(name: str) -> str:
    return f"https://www.linkedin.com/search/results/people/?keywords={quote(name)}"


def _get_arxiv_pdf_url(paper) -> str | None:
    arxiv_id = _extract_arxiv_id_from_url(paper.url or "") or paper.arxiv_id
    if not arxiv_id:
        return None
    return f"https://arxiv.org/pdf/{arxiv_id}.pdf"


def _render_copy_button(text: str, key: str, label: str = "Copy") -> None:
    safe_text = json.dumps(text)
    button_id = f"copy-btn-{key}"
    html = f"""
        <button id="{button_id}"
            style="width:100%; padding:0.25rem 0.6rem; border-radius:0.5rem;
                   border:1px solid #d0d7de; background:#ffffff; cursor:pointer;">
            {label}
        </button>
        <script>
            const btn = document.getElementById("{button_id}");
            if (btn) {{
                btn.addEventListener("click", () => {{
                    navigator.clipboard.writeText({safe_text});
                    const original = btn.textContent;
                    btn.textContent = "Copied";
                    setTimeout(() => btn.textContent = original, 1500);
                }});
            }}
        </script>
    """
    components.html(html, height=42)


def _render_paper_metadata(paper_meta: dict[str, Any]) -> None:
    st.markdown("#### Semantic Scholar paper metadata")
    title = paper_meta.get("title")
    if title:
        st.markdown(f"**Title:** {title}")
    citation_count = paper_meta.get("citationCount")
    reference_count = paper_meta.get("referenceCount")
    counts = []
    if citation_count is not None:
        counts.append(f"{citation_count} citations")
    if reference_count is not None:
        counts.append(f"{reference_count} references")
    if counts:
        st.markdown(f"**Counts:** {' · '.join(counts)}")
    is_open_access = paper_meta.get("isOpenAccess")
    if isinstance(is_open_access, bool):
        st.markdown(f"**Open access:** {'Yes' if is_open_access else 'No'}")
    open_access_pdf = paper_meta.get("openAccessPdf")
    if isinstance(open_access_pdf, dict):
        pdf_url = open_access_pdf.get("url")
        if pdf_url:
            st.markdown(f"**Open access PDF:** [{pdf_url}]({pdf_url})")

    with st.expander("Raw Semantic Scholar response"):
        st.json(paper_meta)


def _format_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def show_project_management(paper_id: int, project_manager: ProjectManager):
    """Show and manage project associations for the paper."""
    st.markdown("### 📁 Projects")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        current_projects = project_manager.get_projects_for_paper(paper_id)
        if current_projects:
            st.write("**Current Projects:**")
            for project in current_projects:
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"📁 **{project.name}**")
                if c2.button("Remove", key=f"remove_proj_{project.id}_{paper_id}"):
                    project_manager.remove_paper_from_project(paper_id, project.id)
                    st.success(f"Removed from '{project.name}'")
                    st.rerun()
        else:
            st.info("No projects yet.")

    with col_right:
        st.write("**Add to Project:**")
        all_projects = project_manager.list_projects()
        current_ids = {p.id for p in current_projects}
        available_projects = [p for p in all_projects if p.id not in current_ids]

        if not available_projects:
            if not all_projects:
                st.warning("No projects found.")
            else:
                st.success("Associated with all projects!")
        else:
            c1, c2 = st.columns([3, 1])
            target_project = c1.selectbox(
                "Select Project",
                options=available_projects,
                format_func=lambda p: p.name,
                key=f"add_to_proj_select_detail_{paper_id}",
                label_visibility="collapsed"
            )
            if c2.button("Add", key=f"add_to_proj_btn_detail_{paper_id}", type="primary", use_container_width=True):
                project_manager.add_paper_to_project(paper_id, target_project.id)
                st.success(f"Added to '{target_project.name}'!")
                st.rerun()
