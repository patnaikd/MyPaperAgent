"""Discover page - find papers on arXiv."""
import streamlit as st

from src.discovery.arxiv_search import ArxivSearch
from src.core.paper_manager import PaperManager
from src.rag.retriever import RAGRetriever


def show_discover_page():
    """Display paper discovery page."""
    st.title("🌐 Discover Papers")

    st.markdown("""
    Search for academic papers on arXiv. Find papers by topic, author, or browse recent publications.
    """)

    # Search method tabs
    tab1, tab2, tab3 = st.tabs(["🔍 By Topic", "👤 By Author", "📅 Recent Papers"])

    with tab1:
        show_topic_search()

    with tab2:
        show_author_search()

    with tab3:
        show_recent_papers()


def show_topic_search():
    """Show topic-based search."""
    st.markdown("### 🔍 Search by Topic")

    topic = st.text_input(
        "Topic or Keywords",
        placeholder="e.g., transformers, reinforcement learning, computer vision",
        help="Enter keywords or topics to search"
    )

    max_results = st.slider("Number of results", min_value=5, max_value=50, value=10)

    if st.button("🔍 Search", type="primary", disabled=not topic, use_container_width=True):
        search_and_display(topic=topic, max_results=max_results)


def show_author_search():
    """Show author-based search."""
    st.markdown("### 👤 Search by Author")

    author = st.text_input(
        "Author Name",
        placeholder="e.g., Yoshua Bengio, Geoffrey Hinton",
        help="Enter author name"
    )

    max_results = st.slider("Number of results", min_value=5, max_value=50, value=10, key="author_limit")

    if st.button("🔍 Search", type="primary", disabled=not author, use_container_width=True, key="author_search"):
        search_and_display(author=author, max_results=max_results)


def show_recent_papers():
    """Show recent papers."""
    st.markdown("### 📅 Recent Papers")

    category = st.selectbox(
        "Category",
        [
            "All",
            "cs.AI - Artificial Intelligence",
            "cs.LG - Machine Learning",
            "cs.CL - Computation and Language",
            "cs.CV - Computer Vision",
            "cs.NE - Neural and Evolutionary Computing",
            "cs.RO - Robotics",
            "stat.ML - Machine Learning (Statistics)",
        ]
    )

    # Extract category code
    category_code = None if category == "All" else category.split(" - ")[0]

    max_results = st.slider("Number of results", min_value=5, max_value=50, value=10, key="recent_limit")

    if st.button("📅 Get Recent Papers", type="primary", use_container_width=True):
        search_and_display(category=category_code, max_results=max_results, recent=True)


def search_and_display(topic=None, author=None, category=None, max_results=10, recent=False):
    """Perform search and display results."""
    with st.spinner("Searching arXiv..."):
        try:
            searcher = ArxivSearch(max_results=max_results)

            # Perform appropriate search
            if topic:
                results = searcher.search_by_topic(topic)
            elif author:
                results = searcher.search_by_author(author)
            elif recent:
                results = searcher.search_recent(category=category)
            else:
                st.error("No search criteria provided")
                return

            if not results:
                st.warning("No papers found. Try different search terms.")
                return

            st.success(f"✅ Found {len(results)} papers")
            st.markdown("---")

            # Display results
            for i, paper in enumerate(results, 1):
                with st.container():
                    # Header
                    st.markdown(f"### {i}. {paper['title']}")

                    # Metadata
                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        st.markdown(f"**Authors:** {paper['authors'][:100]}...")

                    with col2:
                        if paper.get('published'):
                            year = paper['published'][:4]
                            st.markdown(f"**Year:** {year}")

                    with col3:
                        st.markdown(f"**arXiv ID:** {paper['arxiv_id']}")

                    # Categories
                    if paper.get('categories'):
                        categories = ", ".join(paper['categories'][:3])
                        st.caption(f"📑 Categories: {categories}")

                    # Abstract
                    with st.expander("📝 Abstract"):
                        st.write(paper['abstract'])

                    # Actions
                    col1, col2, col3 = st.columns([1, 1, 2])

                    with col1:
                        # Add to library button
                        if st.button("➕ Add to Library", key=f"add_{i}_{paper['arxiv_id']}"):
                            add_paper_to_library(paper)

                    with col2:
                        # View on arXiv
                        if paper.get('url'):
                            st.link_button("🔗 View on arXiv", paper['url'])

                    st.markdown("---")

        except Exception as e:
            st.error(f"Search failed: {e}")
            st.exception(e)


def add_paper_to_library(paper_info: dict):
    """Add a discovered paper to the library."""
    with st.spinner("Adding paper to library..."):
        try:
            # Use PDF URL to add paper
            pdf_url = paper_info.get('pdf_url')
            if not pdf_url:
                st.error("No PDF URL available for this paper")
                return

            manager = PaperManager()

            # Add paper from URL
            paper_id = manager.add_paper_from_url(pdf_url)

            st.success(f"✅ Paper added successfully! (ID: {paper_id})")

            # Offer to index
            if st.button("Index for search?", key=f"index_{paper_id}"):
                with st.spinner("Indexing paper..."):
                    try:
                        retriever = RAGRetriever()
                        chunk_count = retriever.index_paper(paper_id)
                        st.success(f"✅ Indexed {chunk_count} chunks")
                    except Exception as e:
                        st.warning(f"⚠️ Failed to index: {e}")

            # Offer to view
            if st.button("📖 View Paper", key=f"view_{paper_id}"):
                st.session_state.selected_paper_id = paper_id
                st.session_state.current_page = "paper_detail"
                st.rerun()

        except Exception as e:
            st.error(f"Failed to add paper: {e}")
            st.exception(e)


# Search tips
    st.markdown("---")
    with st.expander("💡 Discovery Tips"):
        st.markdown("""
        **Finding papers effectively:**

        - **By Topic**: Use specific technical terms and keywords
        - **By Author**: Use full names or last names for better results
        - **Recent Papers**: Browse latest submissions by category

        **Popular arXiv categories:**
        - `cs.AI` - Artificial Intelligence
        - `cs.LG` - Machine Learning
        - `cs.CL` - NLP and Computational Linguistics
        - `cs.CV` - Computer Vision
        - `cs.RO` - Robotics

        **Example searches:**
        - "attention mechanism transformer"
        - "few-shot learning"
        - "graph neural networks"
        - "reinforcement learning robotics"
        """)
