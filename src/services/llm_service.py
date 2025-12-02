"""
LLM Service - Backwards compatible wrapper.

This module provides backwards compatibility by wrapping the factory pattern.
New code should use create_llm_service() from llm_factory directly.
"""

from typing import Optional
from ..tools.executor import ToolExecutor
from .llm_factory import create_llm_service
from .base_llm_service import BaseLLMService


class LLMService:
    """
    Backwards compatible LLM service wrapper.

    This class maintains compatibility with existing code while using
    the new factory pattern underneath. It defaults to Ollama for
    backwards compatibility.

    For new code, prefer using create_llm_service() from llm_factory directly.
    """

    def __new__(
        cls,
        model_name: str = "orieg/gemma3-tools:4b",
        tool_executor: Optional[ToolExecutor] = None,
        provider: str = "ollama",
        **kwargs
    ):
        """
        Create an LLM service instance using the factory.

        Args:
            model_name: Model name (provider-specific)
            tool_executor: Optional ToolExecutor for function calling
            provider: LLM provider to use ("ollama" or "gemini")
            **kwargs: Additional provider-specific arguments

        Returns:
            BaseLLMService instance
        """
        return create_llm_service(
            provider=provider,
            model_name=model_name,
            tool_executor=tool_executor,
            **kwargs
        )
