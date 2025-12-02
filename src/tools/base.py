"""
Base tool class for LLM agent function calling.

All tools must inherit from BaseTool and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from typing import List, Any, Optional
from ..models.tool_models import (
    ToolDefinition,
    ToolParameter,
    ToolCategory,
)


class BaseTool(ABC):
    """
    Base class for all agent tools.

    Tools are functions that the LLM agent can call to interact with
    the system, access data, or perform actions. Each tool must define
    its signature and implement execution logic.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool name used by LLM for calling.

        Should be descriptive and follow snake_case convention.
        Example: 'get_inventory_items', 'search_products'
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human-readable description of what the tool does.

        This is shown to the LLM to help it understand when to use the tool.
        Should be clear, concise, and actionable.
        """
        pass

    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """Tool category for organization."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """
        List of parameters this tool accepts.

        Returns:
            List of ToolParameter objects defining the tool's signature
        """
        pass

    @property
    @abstractmethod
    def returns(self) -> str:
        """
        Description of what the tool returns.

        Should describe the format and content of the return value.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.

        Args:
            **kwargs: Tool parameters as keyword arguments

        Returns:
            Tool result (will be serialized to JSON for LLM)

        Raises:
            Exception: If execution fails
        """
        pass

    @property
    def requires_approval(self) -> bool:
        """
        Whether this tool requires human approval before execution.

        Default: False
        Override to True for sensitive operations.
        """
        return False

    @property
    def blocked(self) -> bool:
        """
        Whether this tool is completely blocked from execution.

        Default: False
        Override to True for tools that should never execute (e.g., place_order).
        """
        return False

    @property
    def examples(self) -> Optional[List[str]]:
        """
        Optional usage examples for the tool.

        Returns:
            List of example invocations, or None
        """
        return None

    def to_definition(self) -> ToolDefinition:
        """
        Convert tool to ToolDefinition for registration.

        Returns:
            ToolDefinition object
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters=self.parameters,
            returns=self.returns,
            requires_approval=self.requires_approval,
            blocked=self.blocked,
            examples=self.examples,
        )

    def validate_parameters(self, **kwargs) -> None:
        """
        Validate parameters before execution.

        Args:
            **kwargs: Parameters to validate

        Raises:
            ValueError: If parameters are invalid
        """
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                raise ValueError(f"Required parameter '{param.name}' missing")

        # Check for unknown parameters
        valid_param_names = {p.name for p in self.parameters}
        for key in kwargs:
            if key not in valid_param_names:
                raise ValueError(f"Unknown parameter '{key}'")

    def __repr__(self) -> str:
        return f"<Tool: {self.name} ({self.category.value})>"
