"""
Base LLM service interface for multiple providers.

Defines the common interface that all LLM service implementations must follow,
enabling easy switching between providers (Ollama, Gemini, etc.).
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ..models.tool_models import AgentResponse, ToolDefinition
from ..tools.executor import ToolExecutor


class BaseLLMService(ABC):
    """
    Abstract base class for LLM services.

    All LLM service implementations (Ollama, Gemini, etc.) must inherit
    from this class and implement the required methods.
    """

    def __init__(self, tool_executor: Optional[ToolExecutor] = None):
        """
        Initialize base LLM service.

        Args:
            tool_executor: Optional ToolExecutor for function calling
        """
        self.tool_executor = tool_executor
        self.conversation_history: List[Dict[str, Any]] = []

    @abstractmethod
    def chat(
        self,
        message: str,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        keep_history: bool = True,
    ) -> str:
        """
        Send a chat message to the LLM.

        Args:
            message: User message to send
            images: Optional list of image paths (for multimodal input)
            system_prompt: Optional system prompt to set context
            stream: Whether to stream the response
            keep_history: Whether to keep message in conversation history

        Returns:
            LLM response as string
        """
        pass

    @abstractmethod
    def chat_with_tools(
        self,
        message: str,
        tool_definitions: Optional[List[ToolDefinition]] = None,
        max_iterations: int = 5,
        images: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
    ) -> AgentResponse:
        """
        Chat with tool calling support.

        Args:
            message: User message
            tool_definitions: List of available tools (if None, uses all from executor)
            max_iterations: Maximum number of tool calling iterations
            images: Optional images for multimodal input
            system_prompt: Optional system prompt

        Returns:
            AgentResponse with final response, tool calls, and results
        """
        pass

    @abstractmethod
    def generate_questions(self, num_questions: int = 10) -> List[str]:
        """
        Generate setup questions for initial user onboarding.

        Args:
            num_questions: Number of questions to generate

        Returns:
            List of questions
        """
        pass

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []

    def get_history(self) -> List[Dict[str, Any]]:
        """Get current conversation history."""
        return self.conversation_history.copy()

    def set_history(self, history: List[Dict[str, Any]]) -> None:
        """Set conversation history."""
        self.conversation_history = history

    def set_tool_executor(self, tool_executor: ToolExecutor) -> None:
        """
        Set or update the tool executor.

        Args:
            tool_executor: ToolExecutor instance
        """
        self.tool_executor = tool_executor

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of the LLM provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the name of the model being used."""
        pass

    @property
    @abstractmethod
    def supports_images(self) -> bool:
        """Check if the model supports image inputs."""
        pass

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Check if the model supports function calling."""
        pass
