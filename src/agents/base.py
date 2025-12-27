"""Base agent class for PydanticAI-powered agents."""
import logging
from typing import Optional

try:
    from pydantic_ai import Agent, ModelSettings
except ImportError:  # pragma: no cover - supports older pydantic_ai versions
    from pydantic_ai import Agent
    from pydantic_ai.models import ModelSettings
from pydantic_ai.models.anthropic import AnthropicModel

from src.utils.config import get_config

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent errors."""

    pass


class BaseAgent:
    """Base class for PydanticAI-powered agents."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Initialize agent.

        Args:
            model: Claude model to use
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
        """
        self.config = get_config()
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize PydanticAI model
        try:
            self.model = AnthropicModel(
                self.model_name, api_key=self.config.anthropic_api_key
            )
            logger.info(f"Initialized {self.__class__.__name__} with model {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize PydanticAI model: {e}")
            raise AgentError(f"Failed to initialize agent: {str(e)}") from e

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response from Claude.

        Args:
            prompt: User prompt
            system: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override

        Returns:
            Generated text

        Raises:
            AgentError: If generation fails
        """
        try:
            logger.debug(f"Generating response with {self.model_name}")

            model_settings = ModelSettings(
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
            agent = Agent(self.model, system_prompt=system or "", model_settings=model_settings)
            result = agent.run_sync(prompt)

            text = result.data
            if not isinstance(text, str):
                text = str(text)

            logger.debug(f"Generated {len(text)} characters")
            return text

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise AgentError(f"Failed to generate response: {str(e)}") from e

    def generate_with_context(
        self,
        prompt: str,
        context: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response with additional context.

        Args:
            prompt: User prompt
            context: Context to include (e.g., paper excerpts)
            system: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Optional max_tokens override

        Returns:
            Generated text

        Raises:
            AgentError: If generation fails
        """
        # Combine context and prompt
        full_prompt = f"""Context:
{context}

---

{prompt}"""

        return self.generate(
            prompt=full_prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
