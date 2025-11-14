"""Q&A agent for answering questions about papers."""
import logging
from typing import Optional

from src.agents.base import BaseAgent
from src.core.paper_manager import PaperManager
from src.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)


class QAAgent(BaseAgent):
    """Agent for answering questions about academic papers using RAG."""

    def __init__(self):
        """Initialize Q&A agent."""
        super().__init__(temperature=0.2)  # Low temperature for factual answers
        self.paper_manager = PaperManager()
        self.retriever = RAGRetriever()

    def answer_question(
        self,
        question: str,
        paper_id: Optional[int] = None,
        n_contexts: int = 5,
    ) -> dict[str, any]:
        """Answer a question about a paper or papers.

        Args:
            question: Question to answer
            paper_id: Optional paper ID to search within
            n_contexts: Number of context chunks to retrieve

        Returns:
            Dictionary with 'answer', 'sources', and 'confidence'

        Raises:
            AgentError: If answer generation fails
        """
        logger.info(
            f"Answering question: '{question}'" + (f" (paper {paper_id})" if paper_id else "")
        )

        # Get relevant context using RAG
        context = self.retriever.get_context_for_query(
            query=question, n_results=n_contexts, paper_id=paper_id
        )

        # Get paper info if specific paper
        paper_info = ""
        if paper_id:
            paper = self.paper_manager.get_paper(paper_id)
            paper_info = f"\nPaper: {paper.title}\nAuthors: {paper.authors}\n"

        # Generate answer
        system_prompt = """You are a helpful research assistant answering questions about academic papers.

Guidelines:
- Base your answers ONLY on the provided context
- Be precise and factual
- If the context doesn't contain enough information, say so
- Cite relevant parts of the context
- Use clear, accessible language
- If asked about methodology, explain it clearly
- If asked about results, provide specific findings"""

        prompt = f"""Question: {question}

Context from the paper(s):
{context}

Please answer the question based on the context provided. If the answer is not in the context, say "I don't have enough information in the provided context to answer this question."

Structure your answer as:
- Direct answer to the question
- Supporting evidence from the context
- Any relevant caveats or limitations"""

        answer = self.generate(prompt=prompt, system=system_prompt, max_tokens=2000)

        # Extract sources from context
        sources = self._extract_sources(context)

        return {
            "answer": answer,
            "sources": sources,
            "question": question,
            "paper_id": paper_id,
        }

    def _extract_sources(self, context: str) -> list[dict[str, any]]:
        """Extract source information from context.

        Args:
            context: Context string

        Returns:
            List of source dictionaries
        """
        sources = []
        # Context format: [Paper X: Title]\nText\n---\n
        parts = context.split("\n---\n")

        for part in parts:
            if part.strip():
                lines = part.split("\n", 1)
                if len(lines) >= 2:
                    header = lines[0]
                    # Extract paper ID and title from [Paper X: Title]
                    if header.startswith("[Paper"):
                        try:
                            paper_info = header[1:-1]  # Remove brackets
                            paper_id_str, title = paper_info.split(": ", 1)
                            paper_id = int(paper_id_str.split()[1])

                            sources.append({"paper_id": paper_id, "title": title})
                        except (ValueError, IndexError):
                            pass

        return sources

    def ask_followup(
        self,
        question: str,
        previous_qa: list[dict[str, any]],
        paper_id: Optional[int] = None,
    ) -> dict[str, any]:
        """Ask a follow-up question with conversation history.

        Args:
            question: Follow-up question
            previous_qa: List of previous Q&A dictionaries
            paper_id: Optional paper ID

        Returns:
            Answer dictionary

        Raises:
            AgentError: If answer generation fails
        """
        # Get context for new question
        context = self.retriever.get_context_for_query(
            query=question, n_results=5, paper_id=paper_id
        )

        # Build conversation history
        history = "\n\n".join(
            [
                f"Previous Question: {qa['question']}\nPrevious Answer: {qa['answer']}"
                for qa in previous_qa[-3:]  # Last 3 Q&As
            ]
        )

        system_prompt = """You are a helpful research assistant in a conversation about academic papers.
Use the conversation history to provide context-aware answers."""

        prompt = f"""Conversation History:
{history}

New Question: {question}

Relevant Context:
{context}

Answer the new question, taking into account the conversation history. Be concise and direct."""

        answer = self.generate(prompt=prompt, system=system_prompt, max_tokens=2000)

        sources = self._extract_sources(context)

        return {
            "answer": answer,
            "sources": sources,
            "question": question,
            "paper_id": paper_id,
        }


def answer_question(
    question: str, paper_id: Optional[int] = None, n_contexts: int = 5
) -> dict[str, any]:
    """Convenience function to answer a question.

    Args:
        question: Question to answer
        paper_id: Optional paper ID
        n_contexts: Number of context chunks

    Returns:
        Answer dictionary
    """
    agent = QAAgent()
    return agent.answer_question(question, paper_id, n_contexts)
