"""Settings page - view and manage configuration."""
import streamlit as st

from src.utils.config import get_config


def show_settings_page():
    """Display settings page."""
    st.title("⚙️ Settings")

    st.markdown("""
    View your MyPaperAgent configuration and system information.
    """)

    st.markdown("---")

    # Configuration
    st.markdown("### 📋 Configuration")

    try:
        config = get_config()

        # Display config in columns
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Paths")
            st.text(f"Database: {config.database_path}")
            st.text(f"Vector DB: {config.vector_db_path}")
            st.text(f"PDF Storage: {config.pdf_storage_path}")

        with col2:
            st.markdown("#### API Settings")
            st.text(f"Embedding Model: {config.embedding_model}")
            st.text(f"Embedding Provider: {config.get_embedding_provider()}")
            has_anthropic = "✅" if config.anthropic_api_key else "❌"
            st.text(f"Anthropic API Key: {has_anthropic}")
            has_voyage = "✅" if config.voyage_api_key else "❌"
            st.text(f"Voyage API Key: {has_voyage}")

        # Processing settings
        st.markdown("#### Processing Settings")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Chunk Size", config.chunk_size)

        with col2:
            st.metric("Chunk Overlap", config.chunk_overlap)

        with col3:
            st.metric("Max PDF Size", f"{config.max_pdf_size_mb} MB")

    except ValueError as e:
        st.error(f"Configuration error: {e}")
        st.warning("Make sure you have created a .env file with required API keys")

    st.markdown("---")

    # Database info
    st.markdown("### 🗄️ Database Statistics")

    try:
        from src.core.paper_manager import PaperManager
        from src.rag.retriever import RAGRetriever

        manager = PaperManager()
        retriever = RAGRetriever()

        col1, col2, col3 = st.columns(3)

        with col1:
            total_papers = manager.get_paper_count()
            st.metric("Total Papers", total_papers)

        with col2:
            # Count by status
            papers = manager.list_papers(limit=1000)
            completed = sum(1 for p in papers if p.status == "completed")
            st.metric("Completed Papers", completed)

        with col3:
            try:
                vector_store = retriever.vector_store
                collection = vector_store.collection
                indexed_chunks = collection.count()
                st.metric("Indexed Chunks", indexed_chunks)
            except Exception:
                st.metric("Indexed Chunks", "N/A")

    except Exception as e:
        st.error(f"Failed to load statistics: {e}")

    st.markdown("---")

    # Environment variables guide
    with st.expander("🔑 API Keys Setup"):
        st.markdown("""
        ### Required API Keys

        MyPaperAgent requires API keys for Claude and embeddings. Create a `.env` file in the project root with:

        ```bash
        # Required
        ANTHROPIC_API_KEY=your_anthropic_api_key

        # For embeddings (choose one)
        VOYAGE_API_KEY=your_voyage_api_key
        # OR
        OPENAI_API_KEY=your_openai_api_key
        ```

        ### Getting API Keys

        - **Anthropic (Claude)**: Get from [console.anthropic.com](https://console.anthropic.com)
        - **Voyage AI**: Get from [voyage.ai](https://www.voyageai.com/)
        - **OpenAI**: Get from [platform.openai.com](https://platform.openai.com/)

        ### Optional Settings

        You can also configure these in your `.env`:

        ```bash
        # Processing
        CHUNK_SIZE=800
        CHUNK_OVERLAP=100
        MAX_PDF_SIZE_MB=50

        # Embeddings
        EMBEDDING_MODEL=voyage-2
        ```
        """)

    # System info
    with st.expander("💻 System Information"):
        import sys
        import platform

        st.markdown(f"""
        **Python Version:** {sys.version}
        **Platform:** {platform.platform()}
        **Processor:** {platform.processor()}
        """)

    # Actions
    st.markdown("---")
    st.markdown("### 🔧 Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Refresh Configuration", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("🗑️ Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache cleared!")

    # Danger zone
    with st.expander("⚠️ Danger Zone", expanded=False):
        st.warning("**Warning:** These actions cannot be undone!")

        if st.button("🗑️ Delete All Papers", type="secondary"):
            st.error("This feature is disabled for safety. Use the CLI or database directly if needed.")

        if st.button("🔄 Reset Vector Database", type="secondary"):
            st.error("This feature is disabled for safety. Delete the vector_db directory manually if needed.")
