"""Base agent class for Claude-powered agents."""
import logging
from typing import Any, Optional

from anthropic import Anthropic

from src.utils.config import get_config

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent errors."""

    pass


class BaseAgent:
    """Base class for Claude-powered agents."""

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
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize Claude client
        try:
            self.client = Anthropic(api_key=self.config.anthropic_api_key)
            logger.info(f"Initialized {self.__class__.__name__} with model {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
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
            logger.debug(f"Generating response with {self.model}")

            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # Make API call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                system=system or "",
                messages=messages,
            )

            # Extract text from response
            text = response.content[0].text

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

    def extract_json(self, text: str) -> dict[str, Any]:
        """Extract JSON from response text.

        Looks for JSON blocks in markdown code fences or raw JSON.

        Args:
            text: Response text potentially containing JSON

        Returns:
            Parsed JSON dictionary

        Raises:
            AgentError: If JSON cannot be extracted or parsed
        """
        import json
        import re

        # Try to find JSON in code fence
        json_match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise AgentError(f"Failed to parse JSON from response: {str(e)}") from e
