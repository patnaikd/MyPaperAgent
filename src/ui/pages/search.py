"""Search page - semantic search across papers."""
import streamlit as st

from src.rag.retriever import RAGRetriever
from src.core.paper_manager import PaperManager


def show_search_page():
    """Display semantic search page."""
    st.title("🔍 Semantic Search")

    st.markdown("""
    Search across all your papers using natural language. The search uses RAG (Retrieval-Augmented Generation)
    to find the most relevant content based on semantic similarity.
    """)

    # Search input
    query = st.text_input(
        "Search Query",
        placeholder="What are the latest advances in transformer architectures?",
        help="Enter a natural language query to search across all papers"
    )

    # Search options
    col1, col2 = st.columns([2, 1])

    with col1:
        num_results = st.slider(
            "Number of results",
            min_value=3,
            max_value=20,
            value=5,
            help="How many relevant chunks to retrieve"
        )

    with col2:
        specific_paper = st.checkbox("Search in specific paper")

    paper_id = None
    if specific_paper:
        try:
            manager = PaperManager()
            papers = manager.list_papers(limit=100)

            paper_options = {f"{p.id}: {p.title or 'Untitled'}": p.id for p in papers}

            if paper_options:
                selected = st.selectbox("Select Paper", options=list(paper_options.keys()))
                paper_id = paper_options[selected]
            else:
                st.warning("No papers in library yet!")
                return

        except Exception as e:
            st.error(f"Failed to load papers: {e}")
            return

    # Search button
    if st.button("🔍 Search", type="primary", disabled=not query, use_container_width=True):
        with st.spinner("Searching..."):
            try:
                retriever = RAGRetriever()
                results = retriever.search(
                    query=query,
                    n_results=num_results,
                    paper_id=paper_id
                )

                if not results:
                    st.warning("No results found. Try a different query or make sure papers are indexed.")
                    return

                st.success(f"✅ Found {len(results)} results")
                st.markdown("---")

                # Display results
                for i, result in enumerate(results, 1):
                    metadata = result.get("metadata", {})
                    title = metadata.get("title", "Unknown Paper")
                    result_paper_id = metadata.get("paper_id", "Unknown")
                    chunk_index = metadata.get("chunk_index", "?")
                    relevance = result.get("relevance_score", 0.0)

                    # Result card
                    with st.container():
                        # Header
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            st.markdown(f"### {i}. {title}")
                            st.caption(f"Paper ID: {result_paper_id} • Chunk {chunk_index}")

                        with col2:
                            # Relevance score
                            relevance_pct = relevance * 100
                            if relevance_pct >= 70:
                                color = "🟢"
                            elif relevance_pct >= 50:
                                color = "🟡"
                            else:
                                color = "🔴"

                            st.metric("Relevance", f"{color} {relevance_pct:.1f}%")

                        # Content
                        text = result.get("text", "")
                        st.markdown(text)

                        # View paper button
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            if st.button("📖 View Paper", key=f"view_{i}"):
                                st.session_state.selected_paper_id = result_paper_id
                                st.session_state.current_page = "paper_detail"
                                st.rerun()

                        st.markdown("---")

            except Exception as e:
                st.error(f"Search failed: {e}")
                st.exception(e)

    # Search tips
    with st.expander("💡 Search Tips"):
        st.markdown("""
        **Semantic search works best when you:**
        - Use natural language questions
        - Be specific about what you're looking for
        - Include technical terms when relevant
        - Ask about concepts, not just keywords

        **Examples:**
        - "How do transformers handle long-range dependencies?"
        - "What are the main limitations of BERT?"
        - "Methods for reducing model size while maintaining performance"
        - "Comparison of different attention mechanisms"
        """)

    # Quick stats
    st.markdown("---")
    st.markdown("### 📊 Search Statistics")

    try:
        retriever = RAGRetriever()
        manager = PaperManager()

        col1, col2 = st.columns(2)

        with col1:
            total_papers = manager.get_paper_count()
            st.metric("Total Papers", total_papers)

        with col2:
            # Get indexed chunks count
            try:
                vector_store = retriever.vector_store
                collection = vector_store.collection
                indexed_chunks = collection.count()
                st.metric("Indexed Chunks", indexed_chunks)
            except Exception:
                st.metric("Indexed Chunks", "N/A")

    except Exception as e:
        st.warning(f"Could not load statistics: {e}")
