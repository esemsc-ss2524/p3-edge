"""
Tool models and schemas for LLM function calling.

This module defines the data structures for tool definitions, tool calls,
and tool results used in the agent's function calling framework.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class ToolParameterType(str, Enum):
    """Parameter types for tool definitions."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """
    Parameter definition for a tool.

    Defines the schema for a single parameter that a tool accepts,
    including its type, description, and constraints.
    """
    name: str = Field(..., description="Parameter name")
    type: ToolParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description for LLM")
    required: bool = Field(default=True, description="Whether parameter is required")
    enum: Optional[List[str]] = Field(None, description="List of allowed values")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    items: Optional[Dict[str, Any]] = Field(None, description="Item schema for array types")
    properties: Optional[Dict[str, Any]] = Field(None, description="Properties for object types")

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema format for Ollama."""
        schema = {
            "type": self.type.value,
            "description": self.description
        }

        if self.enum:
            schema["enum"] = self.enum

        if self.items:
            schema["items"] = self.items

        if self.properties:
            schema["properties"] = self.properties

        return schema


class ToolCategory(str, Enum):
    """Categories for organizing tools."""
    DATABASE = "database"
    FORECASTING = "forecasting"
    VENDOR = "vendor"
    TRAINING = "training"
    UTILITY = "utility"
    CART = "cart"
    SYSTEM = "system"


class ToolDefinition(BaseModel):
    """
    Complete tool definition for LLM function calling.

    This represents a tool that can be called by the LLM agent,
    including its signature, documentation, and execution constraints.
    """
    name: str = Field(..., description="Tool name (must be unique)")
    description: str = Field(..., description="What the tool does")
    category: ToolCategory = Field(..., description="Tool category")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    returns: str = Field(..., description="Description of return value")
    requires_approval: bool = Field(default=False, description="Requires human approval")
    blocked: bool = Field(default=False, description="Tool is blocked for safety")
    examples: Optional[List[str]] = Field(None, description="Usage examples")

    def to_ollama_tool(self) -> Dict[str, Any]:
        """
        Convert to Ollama tool format.

        Returns:
            Dictionary in Ollama's tool calling format
        """
        # Build parameters schema
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def to_prompt_format(self) -> str:
        """
        Convert to human-readable format for system prompts.

        Returns:
            Formatted string describing the tool
        """
        lines = [
            f"### {self.name}",
            f"Category: {self.category.value}",
            f"Description: {self.description}",
            f"Returns: {self.returns}",
        ]

        if self.parameters:
            lines.append("Parameters:")
            for param in self.parameters:
                required = "required" if param.required else "optional"
                lines.append(f"  - {param.name} ({param.type.value}, {required}): {param.description}")
        else:
            lines.append("Parameters: None")

        if self.blocked:
            lines.append("⚠️ BLOCKED: This tool cannot be executed")

        if self.requires_approval:
            lines.append("⚠️ Requires human approval before execution")

        if self.examples:
            lines.append("Examples:")
            for example in self.examples:
                lines.append(f"  {example}")

        return "\n".join(lines)


class ToolCall(BaseModel):
    """
    Parsed tool call from LLM.

    Represents a request from the LLM to execute a specific tool
    with given arguments.
    """
    tool_name: str = Field(..., description="Name of tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    call_id: Optional[str] = Field(None, description="Unique call ID for tracking")

    def __repr__(self) -> str:
        return f"ToolCall(tool={self.tool_name}, args={self.arguments})"


class ToolResultStatus(str, Enum):
    """Status codes for tool execution results."""
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"
    REQUIRES_APPROVAL = "requires_approval"


class ToolResult(BaseModel):
    """
    Result of tool execution.

    Contains the outcome of executing a tool, including success status,
    returned data, or error information.
    """
    tool_name: str = Field(..., description="Name of executed tool")
    call_id: Optional[str] = Field(None, description="Call ID for tracking")
    status: ToolResultStatus = Field(..., description="Execution status")
    result: Optional[Any] = Field(None, description="Tool result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: float = Field(default=0.0, description="Execution time in milliseconds")

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ToolResultStatus.SUCCESS

    def to_llm_format(self) -> str:
        """
        Format result for LLM consumption.

        Returns:
            Formatted string describing the tool result
        """
        if self.status == ToolResultStatus.SUCCESS:
            import json
            return json.dumps(self.result, indent=2) if self.result else "Success"
        elif self.status == ToolResultStatus.BLOCKED:
            return f"Tool '{self.tool_name}' is blocked for safety reasons: {self.error}"
        elif self.status == ToolResultStatus.REQUIRES_APPROVAL:
            return f"Tool '{self.tool_name}' requires human approval: {self.error}"
        else:
            return f"Error: {self.error}"

    def __repr__(self) -> str:
        if self.success:
            return f"ToolResult(tool={self.tool_name}, status=SUCCESS, time={self.execution_time_ms:.1f}ms)"
        else:
            return f"ToolResult(tool={self.tool_name}, status={self.status.value}, error={self.error})"


class AgentResponse(BaseModel):
    """
    Complete agent response with tool calls and final message.

    Represents the full interaction cycle including all tool calls
    made by the agent and the final response to the user.
    """
    response: str = Field(..., description="Final response to user")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tools that were called")
    tool_results: List[ToolResult] = Field(default_factory=list, description="Results of tool calls")
    iterations: int = Field(default=1, description="Number of reasoning iterations")
    total_time_ms: float = Field(default=0.0, description="Total processing time")

    @property
    def has_tool_calls(self) -> bool:
        """Check if any tools were called."""
        return len(self.tool_calls) > 0

    @property
    def all_tools_succeeded(self) -> bool:
        """Check if all tool calls succeeded."""
        return all(result.success for result in self.tool_results)

    def get_failed_tools(self) -> List[str]:
        """Get list of failed tool names."""
        return [
            result.tool_name
            for result in self.tool_results
            if not result.success
        ]
