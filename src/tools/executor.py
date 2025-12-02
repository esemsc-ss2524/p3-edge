"""
Tool executor for safe execution of agent tools.

Handles tool invocation with error handling, validation, logging,
and safety checks.
"""

import time
import traceback
from typing import Optional
from ..models.tool_models import (
    ToolCall,
    ToolResult,
    ToolResultStatus,
)
from ..models.audit_log import AuditLog, ActionType, Actor, Outcome
from .registry import ToolRegistry, get_registry
from ..database.db_manager import DatabaseManager
from ..utils import get_logger

logger = get_logger("tool_executor")


class ToolExecutor:
    """
    Executes tools with safety checks and logging.

    The executor handles validation, error handling, and audit logging
    for all tool executions requested by the LLM agent.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize tool executor.

        Args:
            db_manager: Database manager for audit logging (optional)
        """
        self.db_manager = db_manager
        self.registry: ToolRegistry = get_registry()

    def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call with full safety checks.

        Args:
            tool_call: ToolCall object with tool name and arguments

        Returns:
            ToolResult with execution outcome
        """
        start_time = time.time()

        # Get tool from registry
        tool = self.registry.get_tool(tool_call.tool_name)

        if not tool:
            error_msg = f"Tool '{tool_call.tool_name}' not found in registry"
            logger.error(error_msg)
            self._log_execution(
                tool_call=tool_call,
                success=False,
                result=error_msg,
                execution_time_ms=0,
            )
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                status=ToolResultStatus.ERROR,
                error=error_msg,
                execution_time_ms=0,
            )

        # Check if tool is blocked
        if tool.blocked:
            error_msg = f"Tool '{tool_call.tool_name}' is blocked for safety reasons"
            logger.warning(f"Blocked tool call: {tool_call.tool_name}")
            self._log_blocked_call(tool_call)
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                status=ToolResultStatus.BLOCKED,
                error=error_msg,
                execution_time_ms=0,
            )

        # Check if approval is required
        if tool.requires_approval:
            error_msg = f"Tool '{tool_call.tool_name}' requires human approval"
            logger.warning(f"Approval required for: {tool_call.tool_name}")
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                status=ToolResultStatus.REQUIRES_APPROVAL,
                error=error_msg,
                execution_time_ms=0,
            )

        # Validate parameters
        try:
            tool.validate_parameters(**tool_call.arguments)
        except ValueError as e:
            error_msg = f"Parameter validation failed: {str(e)}"
            logger.error(f"Validation error for {tool_call.tool_name}: {e}")
            execution_time = (time.time() - start_time) * 1000
            self._log_execution(
                tool_call=tool_call,
                success=False,
                result=error_msg,
                execution_time_ms=execution_time,
            )
            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                status=ToolResultStatus.ERROR,
                error=error_msg,
                execution_time_ms=execution_time,
            )

        # Execute tool
        try:
            logger.info(f"Executing tool: {tool_call.tool_name} with args: {tool_call.arguments}")
            result = tool.execute(**tool_call.arguments)
            execution_time = (time.time() - start_time) * 1000

            logger.info(f"Tool {tool_call.tool_name} executed successfully in {execution_time:.2f}ms")

            # Log success
            self._log_execution(
                tool_call=tool_call,
                success=True,
                result=result,
                execution_time_ms=execution_time,
            )

            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                status=ToolResultStatus.SUCCESS,
                result=result,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"

            logger.error(
                f"Tool {tool_call.tool_name} execution failed: {error_msg}",
                exc_info=True,
            )

            # Log failure with stack trace
            self._log_execution(
                tool_call=tool_call,
                success=False,
                result=error_msg,
                execution_time_ms=execution_time,
                stack_trace=traceback.format_exc(),
            )

            return ToolResult(
                tool_name=tool_call.tool_name,
                call_id=tool_call.call_id,
                status=ToolResultStatus.ERROR,
                error=error_msg,
                execution_time_ms=execution_time,
            )

    def execute_multiple(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """
        Execute multiple tool calls in sequence.

        Args:
            tool_calls: List of ToolCall objects

        Returns:
            List of ToolResult objects
        """
        results = []
        for tool_call in tool_calls:
            result = self.execute(tool_call)
            results.append(result)

            # Stop executing if a critical tool fails
            if result.status == ToolResultStatus.ERROR:
                logger.warning(
                    f"Stopping execution chain due to error in {tool_call.tool_name}"
                )
                # Could optionally continue executing other tools

        return results

    def _log_execution(
        self,
        tool_call: ToolCall,
        success: bool,
        result: any,
        execution_time_ms: float,
        stack_trace: Optional[str] = None,
    ) -> None:
        """
        Log tool execution to audit log.

        Args:
            tool_call: The tool call that was executed
            success: Whether execution succeeded
            result: Result or error message
            execution_time_ms: Execution time in milliseconds
            stack_trace: Stack trace if error occurred
        """
        if not self.db_manager:
            return

        try:
            # Truncate result for storage
            result_str = str(result)
            if len(result_str) > 1000:
                result_str = result_str[:1000] + "... (truncated)"

            details = {
                "tool_name": tool_call.tool_name,
                "arguments": tool_call.arguments,
                "result": result_str,
                "execution_time_ms": execution_time_ms,
            }

            if stack_trace:
                details["stack_trace"] = stack_trace[:2000]  # Truncate

            audit = AuditLog(
                action_type=ActionType.SYSTEM_EVENT,
                actor=Actor.LLM,
                outcome=Outcome.SUCCESS if success else Outcome.FAILURE,
                details=details,
            )

            # Save to database
            query = """
                INSERT INTO audit_log (timestamp, action_type, actor, outcome, details)
                VALUES (?, ?, ?, ?, ?)
            """
            params = (
                audit.timestamp.isoformat(),
                audit.action_type.value,
                audit.actor.value,
                audit.outcome.value,
                str(audit.details),
            )

            self.db_manager.execute_update(query, params)

        except Exception as e:
            logger.error(f"Failed to log tool execution: {e}")

    def _log_blocked_call(self, tool_call: ToolCall) -> None:
        """
        Log blocked tool call attempt.

        Args:
            tool_call: The blocked tool call
        """
        if not self.db_manager:
            return

        try:
            audit = AuditLog(
                action_type=ActionType.SYSTEM_EVENT,
                actor=Actor.LLM,
                outcome=Outcome.FAILURE,
                details={
                    "tool_name": tool_call.tool_name,
                    "arguments": tool_call.arguments,
                    "reason": "Tool is blocked for safety",
                },
            )

            query = """
                INSERT INTO audit_log (timestamp, action_type, actor, outcome, details)
                VALUES (?, ?, ?, ?, ?)
            """
            params = (
                audit.timestamp.isoformat(),
                audit.action_type.value,
                audit.actor.value,
                audit.outcome.value,
                str(audit.details),
            )

            self.db_manager.execute_update(query, params)

        except Exception as e:
            logger.error(f"Failed to log blocked call: {e}")

    def get_available_tools(self) -> list[str]:
        """
        Get list of available (non-blocked) tool names.

        Returns:
            List of tool names
        """
        return [tool.name for tool in self.registry.get_available_tools()]

    def get_tool_definitions(self) -> list:
        """
        Get all tool definitions for LLM.

        Returns:
            List of ToolDefinition objects
        """
        return self.registry.get_all_definitions(include_blocked=False)
