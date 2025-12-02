"""
Factory for creating LLM service instances.

Provides a factory function to instantiate the appropriate LLM service
based on configuration, supporting multiple providers (Ollama, Gemini, etc.).
"""

from typing import Optional
from ..utils import get_logger
from ..tools.executor import ToolExecutor
from .base_llm_service import BaseLLMService

logger = get_logger("llm_factory")


class LLMProvider:
    """Enum for supported LLM providers."""
    OLLAMA = "ollama"
    GEMINI = "gemini"


def create_llm_service(
    provider: str = "ollama",
    model_name: Optional[str] = None,
    tool_executor: Optional[ToolExecutor] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> BaseLLMService:
    """
    Factory function to create an LLM service instance.

    Args:
        provider: LLM provider to use ("ollama" or "gemini")
        model_name: Model name (provider-specific)
        tool_executor: Optional ToolExecutor for function calling
        api_key: API key for cloud providers (Gemini)
        **kwargs: Additional provider-specific arguments

    Returns:
        BaseLLMService instance

    Raises:
        ValueError: If provider is not supported
        ImportError: If required dependencies are not installed

    Examples:
        # Create Ollama service
        service = create_llm_service(
            provider="ollama",
            model_name="gemma3n:e2b-it-q4_K_M",
            tool_executor=executor
        )

        # Create Gemini service
        service = create_llm_service(
            provider="gemini",
            model_name="gemini-2.0-flash-exp",
            api_key="your-api-key",
            tool_executor=executor
        )
    """
    provider = provider.lower()

    logger.info(f"Creating LLM service with provider: {provider}")

    if provider == LLMProvider.OLLAMA:
        from .ollama_llm_service import OllamaLLMService

        if model_name is None:
            model_name = "gemma3n:e2b-it-q4_K_M"

        logger.info(f"Initializing Ollama service with model: {model_name}")
        return OllamaLLMService(
            model_name=model_name,
            tool_executor=tool_executor,
        )

    elif provider == LLMProvider.GEMINI:
        from .gemini_llm_service import GeminiLLMService

        if model_name is None:
            model_name = "gemini-2.0-flash-exp"

        logger.info(f"Initializing Gemini service with model: {model_name}")
        return GeminiLLMService(
            model_name=model_name,
            api_key=api_key,
            tool_executor=tool_executor,
            temperature=kwargs.get("temperature", 0.7),
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: {LLMProvider.OLLAMA}, {LLMProvider.GEMINI}"
        )


def get_available_providers() -> list[str]:
    """
    Get list of available LLM providers based on installed dependencies.

    Returns:
        List of available provider names
    """
    available = [LLMProvider.OLLAMA]  # Ollama is always available

    try:
        import langchain_google_genai
        available.append(LLMProvider.GEMINI)
    except ImportError:
        pass

    return available


def is_provider_available(provider: str) -> bool:
    """
    Check if a specific provider is available.

    Args:
        provider: Provider name to check

    Returns:
        True if provider is available
    """
    return provider.lower() in get_available_providers()
