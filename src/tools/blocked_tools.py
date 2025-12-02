"""
Blocked tools for safety.

These tools are registered but blocked from execution to prevent
unauthorized actions. They serve as documentation of what the LLM
cannot do.
"""

from typing import List, Any
from .base import BaseTool
from ..models.tool_models import (
    ToolParameter,
    ToolParameterType,
    ToolCategory,
)


class PlaceOrderTool(BaseTool):
    """BLOCKED: Place an order (requires human approval)."""

    @property
    def name(self) -> str:
        return "place_order"

    @property
    def description(self) -> str:
        return "Place an order with a vendor (BLOCKED - requires human approval)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CART

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="order_id",
                type=ToolParameterType.STRING,
                description="Order ID to place",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Order placement status"

    @property
    def blocked(self) -> bool:
        return True

    def execute(self, **kwargs) -> Any:
        """This will never execute."""
        raise PermissionError("Order placement requires human approval via UI")


class ApproveOrderTool(BaseTool):
    """BLOCKED: Approve an order (requires human approval)."""

    @property
    def name(self) -> str:
        return "approve_order"

    @property
    def description(self) -> str:
        return "Approve a pending order (BLOCKED - requires human approval)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.CART

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="order_id",
                type=ToolParameterType.STRING,
                description="Order ID to approve",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Approval status"

    @property
    def blocked(self) -> bool:
        return True

    def execute(self, **kwargs) -> Any:
        """This will never execute."""
        raise PermissionError("Order approval requires human interaction via UI")


class DeleteInventoryItemTool(BaseTool):
    """BLOCKED: Delete inventory item (dangerous operation)."""

    @property
    def name(self) -> str:
        return "delete_inventory_item"

    @property
    def description(self) -> str:
        return "Delete an item from inventory (BLOCKED - use UI for deletions)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="item_id",
                type=ToolParameterType.STRING,
                description="Item ID to delete",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Deletion status"

    @property
    def blocked(self) -> bool:
        return True

    def execute(self, **kwargs) -> Any:
        """This will never execute."""
        raise PermissionError("Inventory deletion requires human approval via UI")


class ModifyPreferencesTool(BaseTool):
    """BLOCKED: Modify user preferences (sensitive operation)."""

    @property
    def name(self) -> str:
        return "modify_preferences"

    @property
    def description(self) -> str:
        return "Modify user preferences (BLOCKED - use settings UI)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SYSTEM

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="key",
                type=ToolParameterType.STRING,
                description="Preference key",
                required=True,
            ),
            ToolParameter(
                name="value",
                type=ToolParameterType.STRING,
                description="New value",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "Modification status"

    @property
    def blocked(self) -> bool:
        return True

    def execute(self, **kwargs) -> Any:
        """This will never execute."""
        raise PermissionError("Preference modification requires human approval via UI")


class ClearDatabaseTool(BaseTool):
    """BLOCKED: Clear database (extremely dangerous)."""

    @property
    def name(self) -> str:
        return "clear_database"

    @property
    def description(self) -> str:
        return "Clear all database data (BLOCKED - extremely dangerous operation)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SYSTEM

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @property
    def returns(self) -> str:
        return "Deletion status"

    @property
    def blocked(self) -> bool:
        return True

    def execute(self, **kwargs) -> Any:
        """This will never execute."""
        raise PermissionError("Database clearing is permanently blocked")
