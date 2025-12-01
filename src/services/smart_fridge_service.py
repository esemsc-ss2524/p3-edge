"""
Smart Fridge Integration Service

Connects to Samsung Family Hub simulator (or real device) and syncs inventory
with the main P3-Edge application database.

Supports:
- Real-time inventory sync
- Periodic polling for updates
- Event-based updates (door open/close, item changes)
- Connection status monitoring
"""

import json
import requests
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from urllib.parse import urljoin

from src.database.db_manager import DatabaseManager
from src.services.inventory_service import InventoryService
from src.utils import get_logger, get_audit_logger


class SmartFridgeConnectionError(Exception):
    """Raised when connection to smart fridge fails."""
    pass


class SmartFridgeService:
    """
    Service for integrating with Samsung Family Hub smart refrigerator.

    Manages connection, inventory synchronization, and real-time updates.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        fridge_url: str = "http://localhost:5001",
        poll_interval_seconds: int = 30,
    ):
        """
        Initialize smart fridge service.

        Args:
            db_manager: Database manager instance
            fridge_url: Base URL of smart fridge API
            poll_interval_seconds: Interval for polling updates
        """
        self.db_manager = db_manager
        self.fridge_url = fridge_url
        self.poll_interval = poll_interval_seconds

        self.logger = get_logger("smart_fridge_service")
        self.audit_logger = get_audit_logger(db_manager)
        self.inventory_service = InventoryService(db_manager)

        # Connection state
        self.connected = False
        self.device_id: Optional[str] = None
        self.device_name: Optional[str] = None
        self.last_sync: Optional[datetime] = None

        # Polling thread
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None

        # Item mapping: fridge_item_id -> db_item_id
        self._item_mapping: Dict[str, str] = {}

        # Event callbacks
        self.on_connection_change: Optional[Callable[[bool], None]] = None
        self.on_inventory_update: Optional[Callable[[str, Dict], None]] = None

    def connect(self) -> bool:
        """
        Connect to smart fridge and verify connectivity.

        Returns:
            True if connection successful
        """
        self.logger.info(f"Connecting to smart fridge at {self.fridge_url}")

        try:
            # Health check
            response = requests.get(
                urljoin(self.fridge_url, "/api/health"),
                timeout=5
            )
            response.raise_for_status()

            health_data = response.json()
            self.connected = health_data.get("status") == "ok"
            self.device_id = health_data.get("device_id")

            if self.connected:
                # Get device info
                device_info = self._get_device_info()
                if device_info:
                    self.device_name = device_info.get("name", "Samsung Family Hub")

                self.logger.info(
                    f"Connected to {self.device_name} (ID: {self.device_id})"
                )

                # Audit log
                self.audit_logger.log_action(
                    action_type="smart_fridge_connected",
                    actor="system",
                    details={
                        "device_id": self.device_id,
                        "device_name": self.device_name,
                    }
                )

                # Trigger callback
                if self.on_connection_change:
                    self.on_connection_change(True)

                return True

        except requests.RequestException as e:
            self.logger.error(f"Failed to connect to smart fridge: {e}")
            self.connected = False

            if self.on_connection_change:
                self.on_connection_change(False)

            return False

        return False

    def disconnect(self):
        """Disconnect from smart fridge."""
        self.stop_polling()
        self.connected = False
        self.device_id = None
        self.device_name = None

        self.logger.info("Disconnected from smart fridge")

        # Audit log
        self.audit_logger.log_action(
            action_type="smart_fridge_disconnected",
            actor="system",
        )

        if self.on_connection_change:
            self.on_connection_change(False)

    def is_connected(self) -> bool:
        """Check if connected to smart fridge."""
        if not self.connected:
            return False

        # Verify with health check
        try:
            response = requests.get(
                urljoin(self.fridge_url, "/api/health"),
                timeout=3
            )
            return response.status_code == 200
        except requests.RequestException:
            self.connected = False
            return False

    def _get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get device information."""
        if not self.device_id:
            return None

        try:
            response = requests.get(
                urljoin(self.fridge_url, f"/api/devices/{self.device_id}"),
                timeout=5
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"Failed to get device info: {e}")
            return None

    def sync_inventory(self) -> Dict[str, int]:
        """
        Sync inventory from smart fridge to local database.

        Returns:
            Dict with counts: {added, updated, removed, unchanged}
        """
        if not self.connected:
            raise SmartFridgeConnectionError("Not connected to smart fridge")

        self.logger.info("Syncing inventory from smart fridge...")

        try:
            # Get inventory from fridge
            response = requests.get(
                urljoin(self.fridge_url, "/api/inventory"),
                timeout=10
            )
            response.raise_for_status()

            fridge_data = response.json()
            fridge_items = fridge_data.get("items", [])

            # Track changes
            stats = {
                "added": 0,
                "updated": 0,
                "removed": 0,
                "unchanged": 0,
            }

            # Get current DB items
            db_items = {item.name: item for item in self.inventory_service.get_all_items()}

            # Sync each fridge item
            for fridge_item in fridge_items:
                item_name = fridge_item["name"]

                if item_name in db_items:
                    # Update existing item
                    db_item = db_items[item_name]
                    old_qty = db_item.quantity_current
                    new_qty = fridge_item["quantity"]

                    if abs(old_qty - new_qty) > 0.01:  # Changed
                        self.inventory_service.update_quantity(
                            db_item.item_id,
                            new_qty,
                            source="smart_fridge",
                            notes=f"Synced from smart fridge (was: {old_qty})"
                        )
                        stats["updated"] += 1

                        self.logger.info(
                            f"Updated {item_name}: {old_qty} -> {new_qty} {fridge_item['unit']}"
                        )

                        # Trigger callback
                        if self.on_inventory_update:
                            self.on_inventory_update(db_item.item_id, fridge_item)

                    else:
                        stats["unchanged"] += 1

                    # Update mapping
                    self._item_mapping[fridge_item["item_id"]] = db_item.item_id

                else:
                    # Add new item
                    from src.models import InventoryItem

                    new_item = InventoryItem(
                        name=item_name,
                        category=fridge_item.get("category", "Other"),
                        unit=fridge_item["unit"],
                        quantity_current=fridge_item["quantity"],
                        quantity_min=self._estimate_min_quantity(fridge_item),
                        quantity_max=self._estimate_max_quantity(fridge_item),
                        location=fridge_item["location"],
                        perishable=self._is_perishable(fridge_item["category"]),
                        consumption_rate=None,  # Will be learned
                    )

                    db_item_id = self.inventory_service.create_item(new_item)
                    self._item_mapping[fridge_item["item_id"]] = db_item_id

                    stats["added"] += 1
                    self.logger.info(
                        f"Added new item: {item_name} ({fridge_item['quantity']} {fridge_item['unit']})"
                    )

            self.last_sync = datetime.now()

            self.logger.info(
                f"Sync complete: {stats['added']} added, {stats['updated']} updated, "
                f"{stats['unchanged']} unchanged"
            )

            # Audit log
            self.audit_logger.log_action(
                action_type="smart_fridge_sync",
                actor="system",
                details=stats,
            )

            return stats

        except requests.RequestException as e:
            self.logger.error(f"Failed to sync inventory: {e}")
            raise SmartFridgeConnectionError(f"Sync failed: {e}")

    def _estimate_min_quantity(self, fridge_item: Dict) -> float:
        """Estimate minimum quantity threshold."""
        qty = fridge_item["quantity"]
        unit = fridge_item["unit"]

        # Use 30% of current quantity as min
        if unit in ["gallon", "lb", "dozen", "head", "jar", "loaf"]:
            return max(0.3, qty * 0.3)
        elif unit in ["oz"]:
            return max(4.0, qty * 0.3)
        else:  # count, can
            return max(1, int(qty * 0.3))

    def _estimate_max_quantity(self, fridge_item: Dict) -> float:
        """Estimate maximum quantity threshold."""
        qty = fridge_item["quantity"]
        unit = fridge_item["unit"]

        # Use 3x current quantity as max
        if unit in ["gallon", "lb", "dozen", "head", "jar", "loaf"]:
            return qty * 3.0
        elif unit in ["oz"]:
            return qty * 3.0
        else:  # count, can
            return int(qty * 3)

    def _is_perishable(self, category: str) -> bool:
        """Determine if item is perishable based on category."""
        perishable_categories = [
            "Dairy",
            "Produce",
            "Protein",
            "Beverages",
        ]
        return category in perishable_categories

    def start_polling(self) -> bool:
        """
        Start periodic polling for inventory updates.

        Returns:
            True if polling started successfully
        """
        if not self.connected:
            self.logger.error("Cannot start polling: not connected")
            return False

        if self._polling:
            self.logger.warning("Polling already running")
            return True

        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

        self.logger.info(f"Started polling (interval: {self.poll_interval}s)")
        return True

    def stop_polling(self):
        """Stop periodic polling."""
        if not self._polling:
            return

        self._polling = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
            self._poll_thread = None

        self.logger.info("Stopped polling")

    def _poll_loop(self):
        """Background polling loop."""
        while self._polling:
            try:
                # Check connection
                if not self.is_connected():
                    self.logger.warning("Lost connection to smart fridge")
                    self.connected = False
                    if self.on_connection_change:
                        self.on_connection_change(False)
                    break

                # Sync inventory
                self.sync_inventory()

            except Exception as e:
                self.logger.error(f"Polling error: {e}")

            # Sleep until next poll
            time.sleep(self.poll_interval)

    def get_device_status(self) -> Optional[Dict[str, Any]]:
        """Get current device status (temperature, door, etc.)."""
        if not self.connected or not self.device_id:
            return None

        try:
            response = requests.get(
                urljoin(self.fridge_url, f"/api/devices/{self.device_id}/status"),
                timeout=5
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            self.logger.error(f"Failed to get device status: {e}")
            return None

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for UI display."""
        return {
            "connected": self.connected,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "fridge_url": self.fridge_url,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "polling": self._polling,
            "poll_interval": self.poll_interval,
        }


# Singleton instance
_smart_fridge_service: Optional[SmartFridgeService] = None


def get_smart_fridge_service(
    db_manager: Optional[DatabaseManager] = None,
    fridge_url: str = "http://localhost:5001",
) -> SmartFridgeService:
    """
    Get global smart fridge service instance.

    Args:
        db_manager: Database manager (required for first call)
        fridge_url: Smart fridge API URL

    Returns:
        SmartFridgeService instance
    """
    global _smart_fridge_service

    if _smart_fridge_service is None:
        if db_manager is None:
            raise ValueError("db_manager required for first initialization")

        _smart_fridge_service = SmartFridgeService(
            db_manager,
            fridge_url=fridge_url,
        )

    return _smart_fridge_service


def reset_smart_fridge_service():
    """Reset global service instance (for testing)."""
    global _smart_fridge_service
    if _smart_fridge_service:
        _smart_fridge_service.stop_polling()
    _smart_fridge_service = None
