"""
Database query tools for LLM agent.

These tools provide read-only access to the database for querying
inventory, forecasts, and orders.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .base import BaseTool
from ..models.tool_models import (
    ToolParameter,
    ToolParameterType,
    ToolCategory,
)
from ..database.db_manager import DatabaseManager


class GetInventoryItemsTool(BaseTool):
    """Get all inventory items with optional filters."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "get_inventory_items"

    @property
    def description(self) -> str:
        return "Get all inventory items with optional filters for category and stock level"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="category",
                type=ToolParameterType.STRING,
                description="Filter by category (e.g., 'dairy', 'produce', 'meat')",
                required=False,
            ),
            ToolParameter(
                name="low_stock_only",
                type=ToolParameterType.BOOLEAN,
                description="Return only items below minimum stock level",
                required=False,
                default=False,
            ),
        ]

    @property
    def returns(self) -> str:
        return "List of inventory items with name, quantity, unit, location, and expiry date"

    def execute(
        self, category: Optional[str] = None, low_stock_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Execute the tool."""
        query = """
            SELECT item_id, name, category, brand, quantity_current, quantity_min,
                   unit, location, expiry_date, consumption_rate, perishable
            FROM inventory
            WHERE 1=1
        """
        params = []

        if category:
            query += " AND LOWER(category) = LOWER(?)"
            params.append(category)

        if low_stock_only:
            query += " AND quantity_current <= quantity_min"

        query += " ORDER BY name"

        results = self.db_manager.execute_query(query, tuple(params))

        items = []
        for row in results:
            item = {
                "item_id": row['item_id'],
                "name": row['name'],
                "category": row['category'],
                "brand": row['brand'],
                "quantity_current": row['quantity_current'],
                "quantity_min": row['quantity_min'],
                "unit": row['unit'],
                "location": row['location'],
                "expiry_date": row['expiry_date'],
                "consumption_rate": row['consumption_rate'],
                "perishable": bool(row['perishable']),
            }
            items.append(item)

        return items


class SearchInventoryTool(BaseTool):
    """Search inventory by item name."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "search_inventory"

    @property
    def description(self) -> str:
        return "Search for inventory items by name (partial match supported)"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="search_term",
                type=ToolParameterType.STRING,
                description="Search term to match against item names (case-insensitive)",
                required=True,
            ),
        ]

    @property
    def returns(self) -> str:
        return "List of matching inventory items"

    def execute(self, search_term: str) -> List[Dict[str, Any]]:
        """Execute search."""
        query = """
            SELECT item_id, name, category, quantity_current, unit, location, expiry_date
            FROM inventory
            WHERE LOWER(name) LIKE LOWER(?)
            ORDER BY name
        """
        results = self.db_manager.execute_query(query, (f"%{search_term}%",))

        items = []
        for row in results:
            item = {
                "item_id": row['item_id'],
                "name": row['name'],
                "category": row['category'],
                "quantity_current": row['quantity_current'],
                "unit": row['unit'],
                "location": row['location'],
                "expiry_date": row['expiry_date'],
            }
            items.append(item)

        return items


class GetExpiringItemsTool(BaseTool):
    """Get items expiring within specified days."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "get_expiring_items"

    @property
    def description(self) -> str:
        return "Get items that will expire within the specified number of days"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="days",
                type=ToolParameterType.INTEGER,
                description="Number of days to check ahead (default: 7)",
                required=False,
                default=7,
            ),
        ]

    @property
    def returns(self) -> str:
        return "List of items expiring soon with expiry dates"

    def execute(self, days: int = 7) -> List[Dict[str, Any]]:
        """Execute query."""
        cutoff_date = (datetime.now() + timedelta(days=days)).isoformat()

        query = """
            SELECT item_id, name, category, quantity_current, unit, expiry_date
            FROM inventory
            WHERE expiry_date IS NOT NULL
              AND expiry_date <= ?
              AND expiry_date > ?
            ORDER BY expiry_date ASC
        """
        results = self.db_manager.execute_query(
            query, (cutoff_date, datetime.now().isoformat())
        )

        items = []
        for row in results:
            expiry = datetime.fromisoformat(row['expiry_date'])
            days_until_expiry = (expiry - datetime.now()).days

            item = {
                "item_id": row['item_id'],
                "name": row['name'],
                "category": row['category'],
                "quantity_current": row['quantity_current'],
                "unit": row['unit'],
                "expiry_date": row['expiry_date'],
                "days_until_expiry": days_until_expiry,
            }
            items.append(item)

        return items


class GetForecastsTool(BaseTool):
    """Get forecasts for inventory items."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "get_forecasts"

    @property
    def description(self) -> str:
        return "Get runout forecasts for inventory items, optionally filtered by item name"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="item_name",
                type=ToolParameterType.STRING,
                description="Filter by item name (partial match)",
                required=False,
            ),
        ]

    @property
    def returns(self) -> str:
        return "List of forecasts with predicted runout dates and confidence scores"

    def execute(self, item_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute query."""
        query = """
            SELECT f.forecast_id, i.name, f.predicted_runout_date,
                   f.confidence, f.recommended_order_date,
                   f.recommended_quantity, f.created_at
            FROM forecasts f
            JOIN inventory i ON f.item_id = i.item_id
            WHERE 1=1
        """
        params = []

        if item_name:
            query += " AND LOWER(i.name) LIKE LOWER(?)"
            params.append(f"%{item_name}%")

        query += " ORDER BY f.predicted_runout_date ASC"

        results = self.db_manager.execute_query(query, tuple(params))

        forecasts = []
        for row in results:
            forecast = {
                "forecast_id": row['forecast_id'],
                "item_name": row['name'],
                "predicted_runout_date": row['predicted_runout_date'],
                "confidence": row['confidence'],
                "recommended_order_date": row['recommended_order_date'],
                "recommended_quantity": row['recommended_quantity'],
                "created_at": row['created_at'],
            }
            forecasts.append(forecast)

        return forecasts


class GetOrderHistoryTool(BaseTool):
    """Get past orders."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "get_order_history"

    @property
    def description(self) -> str:
        return "Get past orders with optional status filter"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="limit",
                type=ToolParameterType.INTEGER,
                description="Maximum number of orders to return (default: 10)",
                required=False,
                default=10,
            ),
            ToolParameter(
                name="status",
                type=ToolParameterType.STRING,
                description="Filter by order status (e.g., 'DELIVERED', 'PLACED')",
                required=False,
            ),
        ]

    @property
    def returns(self) -> str:
        return "List of past orders with items, status, and timestamps"

    def execute(
        self, limit: int = 10, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute query."""
        query = """
            SELECT order_id, vendor, status, items, total_cost,
                   created_at, placed_at, delivered_at
            FROM orders
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = self.db_manager.execute_query(query, tuple(params))

        orders = []
        for row in results:
            order = {
                "order_id": row['order_id'],
                "vendor": row['vendor'],
                "status": row['status'],
                "items": row['items'],  # JSON string
                "total_cost": row['total_cost'],
                "created_at": row['created_at'],
                "placed_at": row['placed_at'],
                "delivered_at": row['delivered_at'],
            }
            orders.append(order)

        return orders


class GetPendingOrdersTool(BaseTool):
    """Get orders awaiting approval."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @property
    def name(self) -> str:
        return "get_pending_orders"

    @property
    def description(self) -> str:
        return "Get orders that are pending approval from the user"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATABASE

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @property
    def returns(self) -> str:
        return "List of orders awaiting approval"

    def execute(self) -> List[Dict[str, Any]]:
        """Execute query."""
        query = """
            SELECT order_id, vendor, items, total_cost, created_at
            FROM orders
            WHERE status = 'PENDING_APPROVAL'
            ORDER BY created_at DESC
        """
        results = self.db_manager.execute_query(query)

        orders = []
        for row in results:
            order = {
                "order_id": row['order_id'],
                "vendor": row['vendor'],
                "items": row['items'],
                "total_cost": row['total_cost'],
                "created_at": row['created_at'],
            }
            orders.append(order)

        return orders
