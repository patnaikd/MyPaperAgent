"""Quiz generation agent for academic papers."""
import logging
from typing import Literal, Optional

from pydantic import BaseModel

try:
    from pydantic_ai import Agent, ModelSettings
except ImportError:  # pragma: no cover - supports older pydantic_ai versions
    from pydantic_ai import Agent
    from pydantic_ai.models import ModelSettings

from src.agents.base import BaseAgent
from src.core.paper_manager import PaperManager
from src.utils.database import QuizQuestion, QuestionDifficulty, get_session

logger = logging.getLogger(__name__)


class QuizQuestionOutput(BaseModel):
    """Structured quiz question output."""

    question: str
    answer: str
    explanation: str = ""
    difficulty: Literal["easy", "medium", "hard", "adaptive"] = "medium"


class QuizGenerator(BaseAgent):
    """Agent for generating quiz questions about papers."""

    def __init__(self):
        """Initialize quiz generator."""
        super().__init__(temperature=0.7)  # Higher temperature for diverse questions
        self.paper_manager = PaperManager()
        self.session = get_session()

    def generate_quiz(
        self,
        paper_id: int,
        num_questions: int = 10,
        difficulty: Literal["easy", "medium", "hard", "adaptive"] = "adaptive",
        save_to_db: bool = True,
    ) -> list[dict[str, any]]:
        """Generate quiz questions for a paper.

        Args:
            paper_id: Paper ID
            num_questions: Number of questions to generate
            difficulty: Question difficulty level
            save_to_db: Whether to save questions to database

        Returns:
            List of question dictionaries

        Raises:
            AgentError: If generation fails
        """
        logger.info(
            f"Generating {num_questions} {difficulty} questions for paper {paper_id}"
        )

        # Get paper
        paper = self.paper_manager.get_paper(paper_id)

        # Prepare context
        context = self._prepare_context(paper)

        # Generate questions
        system_prompt = self._get_system_prompt(difficulty)
        prompt = self._generate_prompt(num_questions, difficulty)

        full_prompt = f"""Context:
{context}

---

{prompt}"""

        model_settings = ModelSettings(
            temperature=self.temperature,
            max_tokens=4000,
        )
        agent = Agent(
            self.model,
            system_prompt=system_prompt,
            model_settings=model_settings,
            output_type=list[QuizQuestionOutput],
        )
        result = agent.run_sync(full_prompt)
        logger.debug("Quiz generator output: %s", result.output)

        questions = [
            {
                "question": item.question,
                "answer": item.answer,
                "explanation": item.explanation,
                "difficulty": item.difficulty or difficulty,
            }
            for item in result.output
        ]

        # Save to database if requested
        if save_to_db:
            self._save_questions(paper_id, questions)

        return questions

    def _get_system_prompt(self, difficulty: str) -> str:
        """Get system prompt for question generation.

        Args:
            difficulty: Question difficulty

        Returns:
            System prompt
        """
        return """You are an expert at creating quiz questions to test understanding of academic papers.

Your questions should:
- Test genuine understanding, not just recall
- Cover key concepts, methodology, and findings
- Be clear and unambiguous
- Have definitive correct answers
- Include helpful explanations
- Set difficulty to one of: easy, medium, hard, adaptive

Return data that matches the provided output schema. Do not wrap the response in markdown,
code fences, or extra text.

Example (schema-shaped, not JSON):
question: "What is the main contribution of this paper?"
answer: "The paper introduces ..."
explanation: "This is correct because ..."
difficulty: "medium"
"""

    def _generate_prompt(self, num_questions: int, difficulty: str) -> str:
        """Generate prompt for quiz generation.

        Args:
            num_questions: Number of questions
            difficulty: Difficulty level

        Returns:
            Prompt string
        """
        difficulty_guides = {
            "easy": "- Focus on main ideas and definitions\n- Test basic comprehension\n- Questions answerable from abstract/introduction",
            "medium": "- Test understanding of methodology and key findings\n- Require synthesis of multiple sections\n- Questions about 'how' and 'why'",
            "hard": "- Test deep understanding and critical thinking\n- Require connecting multiple concepts\n- Questions about implications and limitations\n- Comparison with other approaches",
            "adaptive": "- Mix of easy (30%), medium (50%), and hard (20%) questions\n- Cover breadth and depth of the paper",
        }

        return f"""Generate {num_questions} quiz questions about this paper.

Difficulty Level: {difficulty}
{difficulty_guides[difficulty]}

Question Types to Include:
1. Conceptual understanding questions
2. Methodology questions
3. Results/findings questions
4. Limitations/implications questions
5. Comparison/analysis questions

Return ONLY a valid JSON array of questions with no additional text."""

    def _prepare_context(self, paper: any) -> str:
        """Prepare paper context for quiz generation.

        Args:
            paper: Paper object

        Returns:
            Context string
        """
        context_parts = [
            f"Title: {paper.title}",
            f"Authors: {paper.authors}",
        ]

        if paper.abstract:
            context_parts.append(f"\nAbstract:\n{paper.abstract}")

        # Use substantial portion of paper for good questions
        if paper.full_text:
            context_parts.append(f"\nPaper Content:\n{paper.full_text[:12000]}")

        return "\n".join(context_parts)

    def _save_questions(self, paper_id: int, questions: list[dict[str, any]]) -> None:
        """Save questions to database.

        Args:
            paper_id: Paper ID
            questions: List of question dictionaries
        """
        existing = {
            (q.question, q.answer)
            for q in self.session.query(QuizQuestion)
            .filter(QuizQuestion.paper_id == paper_id)
            .all()
        }
        new_count = 0

        for q in questions:
            key = (q.get("question", ""), q.get("answer", ""))
            if key in existing:
                continue
            quiz_question = QuizQuestion(
                paper_id=paper_id,
                question=q["question"],
                answer=q["answer"],
                explanation=q.get("explanation", ""),
                difficulty=q.get("difficulty", QuestionDifficulty.MEDIUM.value),
            )
            self.session.add(quiz_question)
            existing.add(key)
            new_count += 1

        self.session.commit()
        logger.info("Saved %s new quiz questions to database", new_count)

    def get_quiz_questions(
        self, paper_id: int, limit: Optional[int] = None
    ) -> list[QuizQuestion]:
        """Get existing quiz questions for a paper.

        Args:
            paper_id: Paper ID
            limit: Optional limit on number of questions

        Returns:
            List of QuizQuestion objects
        """
        query = self.session.query(QuizQuestion).filter(QuizQuestion.paper_id == paper_id)

        if limit:
            query = query.limit(limit)

        return query.all()


def generate_quiz(
    paper_id: int,
    num_questions: int = 10,
    difficulty: Literal["easy", "medium", "hard", "adaptive"] = "adaptive",
) -> list[dict[str, any]]:
    """Convenience function to generate a quiz.

    Args:
        paper_id: Paper ID
        num_questions: Number of questions
        difficulty: Difficulty level

    Returns:
        List of question dictionaries
    """
    generator = QuizGenerator()
    return generator.generate_quiz(paper_id, num_questions, difficulty)
