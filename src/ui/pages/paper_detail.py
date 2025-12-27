"""Paper detail page - view paper with AI features."""
import logging
from pathlib import Path

import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

from src.agents.qa_agent import QAAgent
from src.agents.quiz_generator import QuizGenerator
from src.agents.summarizer import SummarizationAgent
from src.core.note_manager import NoteManager
from src.core.paper_manager import PaperManager
from src.core.qa_manager import QAHistoryManager
from src.utils.database import NoteType
from src.ui.ui_helpers import render_footer


logger = logging.getLogger(__name__)
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
        paper = manager.get_paper(paper_id)
    except Exception as e:
        st.error(f"Failed to load paper: {e}")
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
    st.markdown(f"## {paper.title or 'Untitled Paper'}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Pages", paper.page_count or "N/A")
    with col2:
        st.metric("📅 Year", paper.year or "Unknown")
    with col3:
        status_colors = {"unread": "🔵", "reading": "🟡", "completed": "🟢", "archived": "⚫"}
        st.metric("Status", f"{status_colors.get(paper.status, '⚪')} {paper.status.title()}")

    if paper.authors:
        st.markdown(f"**Authors:** {paper.authors}")
    if paper.journal:
        st.markdown(f"**Published in:** {paper.journal}")
    if paper.doi:
        st.markdown(f"**DOI:** {paper.doi}")
    speechify_url = paper.speechify_url or ""
    listen_url = speechify_url or "https://app.speechify.com/"
    edit_key = f"edit_speechify_{paper_id}"
    speechify_key = f"speechify_url_{paper_id}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    if paper.url:
        listen_col, url_col = st.columns([1, 4])
        with url_col:
            st.markdown(f"**URL:** [{paper.url}]({paper.url})")
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["💭 Summarize", "📄 View PDF", "❓ Ask Questions", "📝 Quiz", "📔 Notes"]
    )

    with tab1:
        show_summarize_tab(paper_id)

    with tab2:
        show_pdf_tab(paper)

    with tab3:
        show_qa_tab(paper_id)

    with tab4:
        show_quiz_tab(paper_id)

    with tab5:
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
