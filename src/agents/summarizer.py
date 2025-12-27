"""Summarization agent for academic papers."""
import logging
from typing import Literal

from pydantic import BaseModel

try:
    from pydantic_ai import Agent, ModelSettings
except ImportError:  # pragma: no cover - supports older pydantic_ai versions
    from pydantic_ai import Agent
    from pydantic_ai.models import ModelSettings

from src.agents.base import BaseAgent
from src.core.note_manager import NoteManager
from src.core.paper_manager import PaperManager
from src.rag.retriever import RAGRetriever
from src.utils.database import NoteType

logger = logging.getLogger(__name__)


class SummaryOutput(BaseModel):
    """Structured summary output."""

    summary: str


class SummarizationAgent(BaseAgent):
    """Agent for generating paper summaries at different levels."""

    def __init__(self):
        """Initialize summarization agent."""
        super().__init__(temperature=0.3)  # Lower temperature for more focused summaries
        self.paper_manager = PaperManager()
        self.note_manager = NoteManager()
        self.retriever = RAGRetriever()

    def summarize_paper(
        self,
        paper_id: int,
        level: Literal["quick", "detailed", "full"] = "detailed",
        save_as_note: bool = True,
    ) -> str:
        """Generate a summary of a paper.

        Args:
            paper_id: Paper ID
            level: Summary level (quick, detailed, or full)
            save_as_note: Whether to save summary as an AI note

        Returns:
            Generated summary

        Raises:
            AgentError: If summarization fails
        """
        logger.info(f"Generating {level} summary for paper {paper_id}")

        # Get paper
        paper = self.paper_manager.get_paper(paper_id)

        # Get system prompt for level
        system_prompt = self._get_system_prompt(level)

        # Prepare context
        context = self._prepare_context(paper, level)

        # Generate prompt
        prompt = self._generate_prompt(paper, level)

        full_prompt = f"""Context:
{context}

---

{prompt}"""

        model_settings = ModelSettings(
            temperature=self.temperature,
            max_tokens=self._get_max_tokens(level),
        )
        agent = Agent(
            self.model,
            system_prompt=system_prompt,
            model_settings=model_settings,
            output_type=SummaryOutput,
        )
        result = agent.run_sync(full_prompt)
        logger.debug("Summarization agent output: %s", result.output)
        summary = result.output.summary

        # Save as note if requested
        if save_as_note:
            _, created = self.note_manager.add_note_if_new(
                paper_id=paper_id,
                content=summary,
                note_type=NoteType.AI_GENERATED.value,
                section=f"Summary ({level})",
            )
            if created:
                logger.info("Saved %s summary as AI note", level)
            else:
                logger.info("Skipped saving duplicate %s summary note", level)

        return summary

    def _get_system_prompt(self, level: str) -> str:
        """Get system prompt for summary level.

        Args:
            level: Summary level

        Returns:
            System prompt
        """
        base_prompt = """You are an expert at summarizing academic papers.
Your summaries are clear, accurate, and capture the essential points.
Focus on the key contributions, methodology, and findings."""

        schema_prompt = """Return data that matches the provided output schema. Put the entire summary in the
summary field. Do not wrap the response in markdown, code fences, or extra text.

Example (schema-shaped, not JSON):
summary: "## Main Contribution
...
"
"""

        level_prompts = {
            "quick": base_prompt
            + "\n\nGenerate a BRIEF summary (2-3 paragraphs) suitable for quickly understanding the paper's main point.\n\n"
            + schema_prompt,
            "detailed": base_prompt
            + "\n\nGenerate a DETAILED summary covering:\n- Main contribution\n- Methodology\n- Key findings\n- Limitations\n- Significance\n\n"
            + schema_prompt,
            "full": base_prompt
            + "\n\nGenerate a COMPREHENSIVE summary including:\n- Background and motivation\n- Detailed methodology\n- All key findings and results\n- Discussion and implications\n- Limitations and future work\n- How this relates to the broader field\n\n"
            + schema_prompt,
        }

        return level_prompts[level]

    def _prepare_context(self, paper: any, level: str) -> str:
        """Prepare paper context for summarization.

        Args:
            paper: Paper object
            level: Summary level

        Returns:
            Context string
        """
        context_parts = []

        # Add metadata
        context_parts.append(f"Title: {paper.title}")
        if paper.authors:
            context_parts.append(f"Authors: {paper.authors}")
        if paper.year:
            context_parts.append(f"Year: {paper.year}")
        if paper.journal:
            context_parts.append(f"Published in: {paper.journal}")

        context_parts.append("\n")

        # Add abstract if available
        if paper.abstract:
            context_parts.append(f"Abstract:\n{paper.abstract}\n")

        # For detailed/full summaries, add more content
        if level in ["detailed", "full"]:
            # Use first portion of full text
            if paper.full_text:
                # Take first 8000 characters for detailed, more for full
                char_limit = 8000 if level == "detailed" else 15000
                context_parts.append(f"\nPaper Content:\n{paper.full_text[:char_limit]}")

        return "\n".join(context_parts)

    def _generate_prompt(self, paper: any, level: str) -> str:
        """Generate the user prompt for summarization.

        Args:
            paper: Paper object
            level: Summary level

        Returns:
            Prompt string
        """
        prompts = {
            "quick": """Provide a concise summary of this academic paper in 2-3 paragraphs.
Focus on:
1. What is the main contribution or finding?
2. Why is it significant?

Keep it brief and accessible.""",
            "detailed": """Provide a detailed summary of this academic paper.
Structure your summary with these sections:

## Main Contribution
What is the key contribution or innovation?

## Methodology
How did they approach the problem?

## Key Findings
What were the main results?

## Limitations
What are the limitations or caveats?

## Significance
Why does this matter to the field?""",
            "full": """Provide a comprehensive summary of this academic paper.
Structure your summary with these sections:

## Background & Motivation
What problem does this address and why?

## Approach & Methodology
Describe the methods in detail.

## Results & Findings
What were all the key findings?

## Discussion & Implications
What do the results mean? How do they advance the field?

## Limitations & Future Work
What are the limitations? What future research is needed?

## Related Work
How does this fit into the broader research landscape?""",
        }

        return prompts[level]

    def _get_max_tokens(self, level: str) -> int:
        """Get maximum tokens for summary level.

        Args:
            level: Summary level

        Returns:
            Max tokens
        """
        return {"quick": 800, "detailed": 2000, "full": 4000}[level]


def summarize_paper(
    paper_id: int,
    level: Literal["quick", "detailed", "full"] = "detailed",
    save_as_note: bool = True,
) -> str:
    """Convenience function to summarize a paper.

    Args:
        paper_id: Paper ID
        level: Summary level
        save_as_note: Whether to save as AI note

    Returns:
        Generated summary
    """
    agent = SummarizationAgent()
    return agent.summarize_paper(paper_id, level, save_as_note)
