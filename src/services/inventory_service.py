"""
Inventory service for managing household items.

Handles CRUD operations, history tracking, and inventory queries.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.database.db_manager import DatabaseManager
from src.models import InventoryHistory, InventoryItem
from src.utils import get_audit_logger, get_logger


class InventoryService:
    """Service for managing inventory items and history."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize inventory service.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.logger = get_logger("inventory_service")
        self.audit_logger = get_audit_logger(db_manager)

    def create_item(self, item: InventoryItem) -> str:
        """
        Create a new inventory item.

        Args:
            item: InventoryItem to create

        Returns:
            Item ID
        """
        query = """
            INSERT INTO inventory (
                item_id, name, category, brand, unit,
                quantity_current, quantity_min, quantity_max,
                last_updated, location, perishable, expiry_date,
                consumption_rate, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        self.db_manager.execute_update(
            query,
            (
                item.item_id,
                item.name,
                item.category,
                item.brand,
                item.unit,
                item.quantity_current,
                item.quantity_min,
                item.quantity_max,
                item.last_updated.isoformat(),
                item.location,
                1 if item.perishable else 0,
                item.expiry_date.isoformat() if item.expiry_date else None,
                item.consumption_rate,
                json.dumps(item.metadata),
                item.created_at.isoformat(),
            ),
        )

        # Log to audit trail
        self.audit_logger.log_action(
            action_type="inventory_created",
            actor="user",
            details={"item_id": item.item_id, "name": item.name},
            item_id=item.item_id,
        )

        # Add to history
        self.add_history(
            item_id=item.item_id,
            quantity=item.quantity_current,
            source="manual",
            notes="Initial creation",
        )

        self.logger.info(f"Created inventory item: {item.name} ({item.item_id})")
        return item.item_id

    def get_item(self, item_id: str) -> Optional[InventoryItem]:
        """
        Get an inventory item by ID.

        Args:
            item_id: Item ID

        Returns:
            InventoryItem or None if not found
        """
        query = "SELECT * FROM inventory WHERE item_id = ?"
        rows = self.db_manager.execute_query(query, (item_id,))

        if not rows:
            return None

        return self._row_to_item(rows[0])

    def get_all_items(self) -> List[InventoryItem]:
        """
        Get all inventory items.

        Returns:
            List of InventoryItems
        """
        query = "SELECT * FROM inventory ORDER BY name"
        rows = self.db_manager.execute_query(query)
        return [self._row_to_item(row) for row in rows]

    def get_items_by_category(self, category: str) -> List[InventoryItem]:
        """
        Get items by category.

        Args:
            category: Category name

        Returns:
            List of InventoryItems
        """
        query = "SELECT * FROM inventory WHERE category = ? ORDER BY name"
        rows = self.db_manager.execute_query(query, (category,))
        return [self._row_to_item(row) for row in rows]

    def get_low_stock_items(self) -> List[InventoryItem]:
        """
        Get items below minimum threshold.

        Returns:
            List of low-stock InventoryItems
        """
        query = """
            SELECT * FROM inventory
            WHERE quantity_current < quantity_min
            ORDER BY quantity_current ASC
        """
        rows = self.db_manager.execute_query(query)
        return [self._row_to_item(row) for row in rows]

    def update_item(self, item: InventoryItem) -> bool:
        """
        Update an existing inventory item.

        Args:
            item: InventoryItem with updated data

        Returns:
            True if updated successfully
        """
        query = """
            UPDATE inventory SET
                name = ?, category = ?, brand = ?, unit = ?,
                quantity_current = ?, quantity_min = ?, quantity_max = ?,
                last_updated = ?, location = ?, perishable = ?,
                expiry_date = ?, consumption_rate = ?, metadata = ?
            WHERE item_id = ?
        """

        count = self.db_manager.execute_update(
            query,
            (
                item.name,
                item.category,
                item.brand,
                item.unit,
                item.quantity_current,
                item.quantity_min,
                item.quantity_max,
                item.last_updated.isoformat(),
                item.location,
                1 if item.perishable else 0,
                item.expiry_date.isoformat() if item.expiry_date else None,
                item.consumption_rate,
                json.dumps(item.metadata),
                item.item_id,
            ),
        )

        if count > 0:
            # Log to audit trail
            self.audit_logger.log_action(
                action_type="inventory_updated",
                actor="user",
                details={"item_id": item.item_id, "name": item.name},
                item_id=item.item_id,
            )

            self.logger.info(f"Updated inventory item: {item.name} ({item.item_id})")
            return True

        return False

    def update_quantity(
        self, item_id: str, new_quantity: float, source: str = "manual", notes: Optional[str] = None
    ) -> bool:
        """
        Update item quantity and add history entry.

        Args:
            item_id: Item ID
            new_quantity: New quantity value
            source: Source of update (manual, smart_fridge, receipt, etc.)
            notes: Optional notes

        Returns:
            True if updated successfully
        """
        query = """
            UPDATE inventory SET
                quantity_current = ?,
                last_updated = ?
            WHERE item_id = ?
        """

        now = datetime.now().isoformat()
        count = self.db_manager.execute_update(query, (new_quantity, now, item_id))

        if count > 0:
            # Add to history
            self.add_history(item_id, new_quantity, source, notes)

            # Log to audit trail
            self.audit_logger.log_action(
                action_type="inventory_manual_adjustment",
                actor=source,
                details={"item_id": item_id, "new_quantity": new_quantity},
                item_id=item_id,
            )

            self.logger.info(f"Updated quantity for item {item_id}: {new_quantity}")
            return True

        return False

    def delete_item(self, item_id: str) -> bool:
        """
        Delete an inventory item.

        Args:
            item_id: Item ID

        Returns:
            True if deleted successfully
        """
        # Get item name for logging
        item = self.get_item(item_id)
        if not item:
            return False

        query = "DELETE FROM inventory WHERE item_id = ?"
        count = self.db_manager.execute_update(query, (item_id,))

        if count > 0:
            # Log to audit trail
            self.audit_logger.log_action(
                action_type="inventory_deleted",
                actor="user",
                details={"item_id": item_id, "name": item.name},
            )

            self.logger.info(f"Deleted inventory item: {item.name} ({item_id})")
            return True

        return False

    def add_history(
        self,
        item_id: str,
        quantity: float,
        source: str,
        notes: Optional[str] = None
    ) -> str:
        """
        Add an inventory history entry.

        Args:
            item_id: Item ID
            quantity: Quantity at this time
            source: Source of data (manual, smart_fridge, receipt, etc.)
            notes: Optional notes

        Returns:
            History entry ID
        """
        history = InventoryHistory(
            item_id=item_id,
            quantity=quantity,
            source=source,
            notes=notes,
        )

        query = """
            INSERT INTO inventory_history
            (history_id, item_id, quantity, timestamp, source, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """

        self.db_manager.execute_update(
            query,
            (
                history.history_id,
                history.item_id,
                history.quantity,
                history.timestamp.isoformat(),
                history.source,
                history.notes,
            ),
        )

        return history.history_id

    def get_history(self, item_id: str, limit: int = 100) -> List[InventoryHistory]:
        """
        Get history for an item.

        Args:
            item_id: Item ID
            limit: Maximum number of entries

        Returns:
            List of InventoryHistory entries
        """
        query = """
            SELECT * FROM inventory_history
            WHERE item_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """

        rows = self.db_manager.execute_query(query, (item_id, limit))
        return [self._row_to_history(row) for row in rows]

    def search_items(self, search_term: str) -> List[InventoryItem]:
        """
        Search items by name, category, or brand.

        Args:
            search_term: Search string

        Returns:
            List of matching InventoryItems
        """
        query = """
            SELECT * FROM inventory
            WHERE name LIKE ? OR category LIKE ? OR brand LIKE ?
            ORDER BY name
        """

        pattern = f"%{search_term}%"
        rows = self.db_manager.execute_query(query, (pattern, pattern, pattern))
        return [self._row_to_item(row) for row in rows]

    def get_stats(self) -> Dict[str, int]:
        """
        Get inventory statistics.

        Returns:
            Dictionary with stats
        """
        total_query = "SELECT COUNT(*) as count FROM inventory"
        low_stock_query = """
            SELECT COUNT(*) as count FROM inventory
            WHERE quantity_current < quantity_min
        """
        expired_query = """
            SELECT COUNT(*) as count FROM inventory
            WHERE perishable = 1 AND expiry_date < date('now')
        """

        total = self.db_manager.execute_query(total_query)[0]["count"]
        low_stock = self.db_manager.execute_query(low_stock_query)[0]["count"]
        expired = self.db_manager.execute_query(expired_query)[0]["count"]

        return {
            "total_items": total,
            "low_stock_items": low_stock,
            "expired_items": expired,
        }

    def _row_to_item(self, row) -> InventoryItem:
        """Convert database row to InventoryItem."""
        return InventoryItem(
            item_id=row["item_id"],
            name=row["name"],
            category=row["category"],
            brand=row["brand"],
            unit=row["unit"],
            quantity_current=row["quantity_current"],
            quantity_min=row["quantity_min"],
            quantity_max=row["quantity_max"],
            last_updated=datetime.fromisoformat(row["last_updated"]),
            location=row["location"],
            perishable=bool(row["perishable"]),
            expiry_date=datetime.fromisoformat(row["expiry_date"]).date()
            if row["expiry_date"]
            else None,
            consumption_rate=row["consumption_rate"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def _row_to_history(self, row) -> InventoryHistory:
        """Convert database row to InventoryHistory."""
        return InventoryHistory(
            history_id=row["history_id"],
            item_id=row["item_id"],
            quantity=row["quantity"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            source=row["source"],
            notes=row["notes"],
        )
