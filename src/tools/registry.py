"""
Tool registry for managing available tools.

The registry maintains a central collection of all tools that can be
invoked by the LLM agent, providing lookup and enumeration capabilities.
"""

from typing import Dict, List, Optional
from .base import BaseTool
from ..models.tool_models import ToolDefinition, ToolCategory
from ..utils import get_logger

logger = get_logger("tool_registry")


class ToolRegistry:
    """
    Central registry for all agent tools.

    Maintains a collection of registered tools and provides methods
    for tool lookup, filtering, and definition retrieval.
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._initialized = False

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool name already registered
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")

        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} ({tool.category.value})")

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool from the registry.

        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Get tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance, or None if not found
        """
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """
        Check if tool is registered.

        Args:
            name: Tool name

        Returns:
            True if tool exists
        """
        return name in self._tools

    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools.

        Returns:
            List of all tool instances
        """
        return list(self._tools.values())

    def get_all_definitions(self, include_blocked: bool = False) -> List[ToolDefinition]:
        """
        Get all tool definitions for LLM.

        Args:
            include_blocked: Whether to include blocked tools (default: False)

        Returns:
            List of ToolDefinition objects
        """
        definitions = []
        for tool in self._tools.values():
            if not tool.blocked or include_blocked:
                definitions.append(tool.to_definition())

        return definitions

    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Get tools by category.

        Args:
            category: Tool category to filter by

        Returns:
            List of tools in the category
        """
        return [
            tool
            for tool in self._tools.values()
            if tool.category == category
        ]

    def get_available_tools(self) -> List[BaseTool]:
        """
        Get all non-blocked tools.

        Returns:
            List of available tools
        """
        return [
            tool
            for tool in self._tools.values()
            if not tool.blocked
        ]

    def get_tool_count(self) -> int:
        """
        Get number of registered tools.

        Returns:
            Count of registered tools
        """
        return len(self._tools)

    def get_categories(self) -> List[ToolCategory]:
        """
        Get list of categories with registered tools.

        Returns:
            List of unique categories
        """
        return list(set(tool.category for tool in self._tools.values()))

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._initialized = False
        logger.info("Registry cleared")

    def mark_initialized(self) -> None:
        """Mark registry as initialized."""
        self._initialized = True
        logger.info(f"Registry initialized with {len(self._tools)} tools")

    @property
    def initialized(self) -> bool:
        """Check if registry has been initialized."""
        return self._initialized

    def get_summary(self) -> Dict[str, any]:
        """
        Get summary of registered tools.

        Returns:
            Dictionary with registry statistics
        """
        category_counts = {}
        for category in ToolCategory:
            category_counts[category.value] = len(self.get_tools_by_category(category))

        return {
            "total_tools": len(self._tools),
            "available_tools": len(self.get_available_tools()),
            "blocked_tools": sum(1 for t in self._tools.values() if t.blocked),
            "requires_approval": sum(1 for t in self._tools.values() if t.requires_approval),
            "by_category": category_counts,
            "initialized": self._initialized,
        }

    def __repr__(self) -> str:
        return f"<ToolRegistry: {len(self._tools)} tools registered>"


# Global singleton registry
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry singleton.

    Returns:
        Global ToolRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        logger.debug("Created global tool registry")
    return _registry


def register_tool(tool_class):
    """
    Decorator to automatically register a tool.

    Usage:
        @register_tool
        class MyTool(BaseTool):
            ...

    Args:
        tool_class: Tool class to register

    Returns:
        The original class (for chaining)
    """
    # This is a decorator that will be called during import
    # The actual instantiation happens during initialization
    return tool_class


def reset_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _registry
    if _registry:
        _registry.clear()
    _registry = None
    logger.debug("Global registry reset")
