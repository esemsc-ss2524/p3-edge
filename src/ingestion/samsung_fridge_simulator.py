"""
Samsung Smart Refrigerator Simulator (SmartThings API)

Simulates a Samsung Family Hub smart refrigerator using the SmartThings API protocol.
Implements realistic refrigerator capabilities including:
- Temperature monitoring
- Door sensor (open/closed)
- Inventory tracking (simulated AI Vision Inside)
- Ice maker status
- Energy monitoring

Based on Samsung SmartThings API v1 specifications.
"""

import json
import random
import threading
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from flask import Flask, jsonify, request

from src.utils import get_logger


class FridgeMode(Enum):
    """Refrigerator operating modes."""
    NORMAL = "normal"
    POWER_COOL = "powerCool"
    POWER_FREEZE = "powerFreeze"
    VACATION = "vacation"


class DoorStatus(Enum):
    """Door sensor status."""
    OPEN = "open"
    CLOSED = "closed"


class IceMakerStatus(Enum):
    """Ice maker status."""
    RUNNING = "running"
    IDLE = "idle"
    OFF = "off"


@dataclass
class FridgeItem:
    """Represents an item detected by AI Vision Inside camera."""
    item_id: str
    name: str
    quantity: float
    unit: str
    location: str  # "upper_shelf", "lower_shelf", "door", "crisper", "freezer"
    confidence: float
    last_seen: str  # ISO timestamp
    category: str


@dataclass
class TemperatureReading:
    """Temperature measurement from fridge sensors."""
    value: float  # Celsius
    unit: str = "C"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class SamsungFridgeSimulator:
    """
    Simulates a Samsung Family Hub refrigerator with SmartThings API.

    Provides RESTful endpoints compatible with SmartThings device capabilities:
    - temperatureMeasurement
    - contactSensor (door)
    - custom.fridgeMode
    - custom.iceMaker
    - powerConsumptionReport
    - custom.aiVisionInside (inventory tracking)
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        device_name: str = "Samsung Family Hub",
        port: int = 5001,
    ):
        """
        Initialize Samsung fridge simulator.

        Args:
            device_id: Unique device identifier (auto-generated if None)
            device_name: Human-readable device name
            port: Port for REST API server
        """
        self.device_id = device_id or str(uuid.uuid4())
        self.device_name = device_name
        self.port = port
        self.logger = get_logger("samsung_fridge_sim")

        # Device state
        self.connected = False
        self.mode = FridgeMode.NORMAL
        self.door_status = DoorStatus.CLOSED
        self.ice_maker_status = IceMakerStatus.IDLE

        # Temperature settings and readings
        self.fridge_temp_setpoint = 3.0  # Celsius
        self.freezer_temp_setpoint = -18.0  # Celsius
        self.fridge_temp = TemperatureReading(value=3.2, unit="C")
        self.freezer_temp = TemperatureReading(value=-17.8, unit="C")

        # Inventory (AI Vision Inside)
        self.inventory: Dict[str, FridgeItem] = {}
        self._initialize_sample_inventory()

        # Power consumption (watts)
        self.power_consumption = 120.0

        # Flask app for REST API
        self.app = Flask(__name__)
        self._setup_routes()

        # Background thread for state updates
        self._running = False
        self._update_thread = None

        # Event callbacks
        self.on_inventory_change = None  # Callback: fn(item_id, item_data, event_type)
        self.on_door_open = None  # Callback: fn()
        self.on_door_close = None  # Callback: fn()

    def _initialize_sample_inventory(self):
        """Initialize with sample vegetarian items."""
        sample_items = [
            {"name": "Whole Milk", "quantity": 3.75, "unit": "gallon", "location": "door", "category": "Dairy"},
            {"name": "Greek Yogurt", "quantity": 64, "unit": "oz", "location": "upper_shelf", "category": "Dairy"},
            {"name": "Cheddar Cheese", "quantity": 5.5, "unit": "lb", "location": "upper_shelf", "category": "Dairy"},
            {"name": "Baby Spinach", "quantity": 4.0, "unit": "lb", "location": "crisper", "category": "Produce"},
            {"name": "Romaine Lettuce", "quantity": 3, "unit": "head", "location": "crisper", "category": "Produce"},
            {"name": "Baby Carrots", "quantity": 4.5, "unit": "lb", "location": "crisper", "category": "Produce"},
            {"name": "Bell Peppers", "quantity": 6, "unit": "count", "location": "crisper", "category": "Produce"},
            {"name": "Strawberries", "quantity": 4.0, "unit": "lb", "location": "upper_shelf", "category": "Produce"},
            {"name": "Orange Juice", "quantity": 68, "unit": "oz", "location": "door", "category": "Beverages"},
            {"name": "Almond Milk", "quantity": 64, "unit": "oz", "location": "door", "category": "Beverages"},
            {"name": "Tofu Extra Firm", "quantity": 3.0, "unit": "lb", "location": "lower_shelf", "category": "Protein"},
            {"name": "Hummus", "quantity": 36, "unit": "oz", "location": "upper_shelf", "category": "Condiments"},
            {"name": "Eggs Large", "quantity": 2.0, "unit": "dozen", "location": "door", "category": "Protein"},
        ]

        for item in sample_items:
            item_id = str(uuid.uuid4())
            self.inventory[item_id] = FridgeItem(
                item_id=item_id,
                name=item["name"],
                quantity=item["quantity"],
                unit=item["unit"],
                location=item["location"],
                category=item["category"],
                confidence=random.uniform(0.85, 0.98),
                last_seen=datetime.now().isoformat(),
            )

        self.logger.info(f"Initialized with {len(self.inventory)} items")

    def _setup_routes(self):
        """Setup Flask REST API routes (SmartThings compatible)."""

        @self.app.route("/api/devices/<device_id>", methods=["GET"])
        def get_device_status(device_id):
            """Get complete device status (SmartThings device endpoint)."""
            if device_id != self.device_id:
                return jsonify({"error": "Device not found"}), 404

            return jsonify({
                "deviceId": self.device_id,
                "name": self.device_name,
                "label": self.device_name,
                "manufacturerName": "Samsung",
                "presentationId": "samsung-family-hub",
                "deviceManufacturerCode": "Samsung",
                "components": [
                    {
                        "id": "main",
                        "label": "Main",
                        "capabilities": self._get_capabilities()
                    }
                ]
            })

        @self.app.route("/api/devices/<device_id>/status", methods=["GET"])
        def get_status(device_id):
            """Get device status (all capabilities)."""
            if device_id != self.device_id:
                return jsonify({"error": "Device not found"}), 404

            return jsonify({
                "components": {
                    "main": self._get_capabilities()
                }
            })

        @self.app.route("/api/devices/<device_id>/commands", methods=["POST"])
        def execute_command(device_id):
            """Execute device command (SmartThings command endpoint)."""
            if device_id != self.device_id:
                return jsonify({"error": "Device not found"}), 404

            commands = request.json.get("commands", [])
            results = []

            for cmd in commands:
                capability = cmd.get("capability")
                command = cmd.get("command")
                arguments = cmd.get("arguments", [])

                result = self._handle_command(capability, command, arguments)
                results.append(result)

            return jsonify({"results": results})

        @self.app.route("/api/inventory", methods=["GET"])
        def get_inventory():
            """Get current inventory (AI Vision Inside)."""
            items = [asdict(item) for item in self.inventory.values()]
            return jsonify({
                "count": len(items),
                "items": items,
                "last_updated": datetime.now().isoformat()
            })

        @self.app.route("/api/inventory/<item_id>", methods=["GET"])
        def get_item(item_id):
            """Get specific inventory item."""
            if item_id not in self.inventory:
                return jsonify({"error": "Item not found"}), 404

            return jsonify(asdict(self.inventory[item_id]))

        @self.app.route("/api/inventory/<item_id>", methods=["PUT"])
        def update_item(item_id):
            """Update inventory item (simulates manual adjustment or removal)."""
            if item_id not in self.inventory:
                return jsonify({"error": "Item not found"}), 404

            data = request.json
            item = self.inventory[item_id]

            # Update quantity
            if "quantity" in data:
                old_qty = item.quantity
                item.quantity = data["quantity"]
                item.last_seen = datetime.now().isoformat()

                self.logger.info(
                    f"Updated {item.name}: {old_qty} -> {item.quantity} {item.unit}"
                )

                # Trigger callback
                if self.on_inventory_change:
                    self.on_inventory_change(item_id, asdict(item), "updated")

            return jsonify(asdict(item))

        @self.app.route("/api/inventory/<item_id>", methods=["DELETE"])
        def remove_item(item_id):
            """Remove item from inventory (item consumed or removed)."""
            if item_id not in self.inventory:
                return jsonify({"error": "Item not found"}), 404

            item = self.inventory.pop(item_id)
            self.logger.info(f"Removed item: {item.name}")

            # Trigger callback
            if self.on_inventory_change:
                self.on_inventory_change(item_id, asdict(item), "removed")

            return jsonify({"message": "Item removed", "item": asdict(item)})

        @self.app.route("/api/inventory", methods=["POST"])
        def add_item():
            """Add new item to inventory (item placed in fridge)."""
            data = request.json

            item_id = str(uuid.uuid4())
            item = FridgeItem(
                item_id=item_id,
                name=data.get("name"),
                quantity=data.get("quantity", 1.0),
                unit=data.get("unit", "count"),
                location=data.get("location", "upper_shelf"),
                category=data.get("category", "Other"),
                confidence=data.get("confidence", 0.90),
                last_seen=datetime.now().isoformat(),
            )

            self.inventory[item_id] = item
            self.logger.info(f"Added item: {item.name} ({item.quantity} {item.unit})")

            # Trigger callback
            if self.on_inventory_change:
                self.on_inventory_change(item_id, asdict(item), "added")

            return jsonify(asdict(item)), 201

        @self.app.route("/api/door", methods=["POST"])
        def simulate_door():
            """Simulate door open/close events."""
            data = request.json
            action = data.get("action")  # "open" or "close"

            if action == "open":
                self._open_door()
            elif action == "close":
                self._close_door()
            else:
                return jsonify({"error": "Invalid action. Use 'open' or 'close'"}), 400

            return jsonify({"door_status": self.door_status.value})

        @self.app.route("/api/health", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                "status": "ok",
                "device_id": self.device_id,
                "connected": self.connected,
                "uptime_seconds": time.time() - self._start_time if hasattr(self, '_start_time') else 0
            })

    def _get_capabilities(self) -> Dict[str, Any]:
        """Get current device capabilities and states (SmartThings format)."""
        return {
            "temperatureMeasurement": {
                "temperature": {
                    "value": self.fridge_temp.value,
                    "unit": self.fridge_temp.unit,
                    "timestamp": self.fridge_temp.timestamp
                }
            },
            "custom.freezerTemperature": {
                "temperature": {
                    "value": self.freezer_temp.value,
                    "unit": self.freezer_temp.unit,
                    "timestamp": self.freezer_temp.timestamp
                }
            },
            "contactSensor": {
                "contact": {
                    "value": self.door_status.value,
                    "timestamp": datetime.now().isoformat()
                }
            },
            "custom.fridgeMode": {
                "mode": {
                    "value": self.mode.value,
                    "timestamp": datetime.now().isoformat()
                }
            },
            "custom.iceMaker": {
                "status": {
                    "value": self.ice_maker_status.value,
                    "timestamp": datetime.now().isoformat()
                }
            },
            "powerConsumptionReport": {
                "powerConsumption": {
                    "value": self.power_consumption,
                    "unit": "W",
                    "timestamp": datetime.now().isoformat()
                }
            },
            "custom.aiVisionInside": {
                "inventoryCount": {
                    "value": len(self.inventory),
                    "timestamp": datetime.now().isoformat()
                }
            }
        }

    def _handle_command(
        self,
        capability: str,
        command: str,
        arguments: List[Any]
    ) -> Dict[str, Any]:
        """Handle SmartThings device command."""
        self.logger.info(f"Command: {capability}.{command}({arguments})")

        if capability == "custom.fridgeMode":
            if command == "setMode":
                try:
                    mode = FridgeMode(arguments[0])
                    self.mode = mode
                    return {"status": "success", "mode": mode.value}
                except ValueError:
                    return {"status": "error", "message": "Invalid mode"}

        elif capability == "refresh":
            if command == "refresh":
                self._update_temperatures()
                return {"status": "success", "message": "Refreshed"}

        return {"status": "error", "message": "Unknown command"}

    def _open_door(self):
        """Simulate door opening."""
        self.door_status = DoorStatus.OPEN
        self.logger.info("Door OPENED")

        # Temperature rises when door is open
        self.fridge_temp.value += random.uniform(0.5, 1.5)

        if self.on_door_open:
            self.on_door_open()

    def _close_door(self):
        """Simulate door closing."""
        self.door_status = DoorStatus.CLOSED
        self.logger.info("Door CLOSED")

        if self.on_door_close:
            self.on_door_close()

    def _update_temperatures(self):
        """Update temperature readings (simulates sensor drift)."""
        # Fridge temperature fluctuates slightly
        if self.door_status == DoorStatus.CLOSED:
            self.fridge_temp.value = self.fridge_temp_setpoint + random.uniform(-0.5, 0.5)
            self.freezer_temp.value = self.freezer_temp_setpoint + random.uniform(-1.0, 1.0)
        else:
            # Door open - temperature rises
            self.fridge_temp.value = min(
                self.fridge_temp.value + random.uniform(0.2, 0.5),
                15.0  # Max temp
            )

        self.fridge_temp.timestamp = datetime.now().isoformat()
        self.freezer_temp.timestamp = datetime.now().isoformat()

    def _background_updates(self):
        """Background thread for periodic state updates."""
        self._start_time = time.time()

        while self._running:
            # Update temperatures every 30 seconds
            self._update_temperatures()

            # Randomly simulate door events (rare)
            if random.random() < 0.05:  # 5% chance per minute
                if self.door_status == DoorStatus.CLOSED:
                    self._open_door()
                    time.sleep(random.uniform(5, 15))  # Keep open 5-15 seconds
                    self._close_door()

            time.sleep(30)  # Update every 30 seconds

    def start(self):
        """Start the fridge simulator server."""
        self.connected = True
        self._running = True

        # Start background updates
        self._update_thread = threading.Thread(target=self._background_updates, daemon=True)
        self._update_thread.start()

        self.logger.info(f"Samsung Fridge Simulator starting on port {self.port}")
        self.logger.info(f"Device ID: {self.device_id}")
        self.logger.info(f"Inventory: {len(self.inventory)} items")

        # Run Flask app
        self.app.run(host="0.0.0.0", port=self.port, debug=False)

    def stop(self):
        """Stop the simulator."""
        self.connected = False
        self._running = False
        self.logger.info("Simulator stopped")

    def get_inventory_snapshot(self) -> List[Dict[str, Any]]:
        """Get current inventory as list of dicts."""
        return [asdict(item) for item in self.inventory.values()]

    def simulate_item_removal(self, item_name: str, quantity: float):
        """Simulate removing quantity from an item."""
        for item_id, item in self.inventory.items():
            if item.name == item_name:
                old_qty = item.quantity
                item.quantity = max(0, item.quantity - quantity)
                item.last_seen = datetime.now().isoformat()

                self.logger.info(
                    f"Removed {quantity} {item.unit} from {item_name}: "
                    f"{old_qty} -> {item.quantity}"
                )

                # Remove item if quantity is 0
                if item.quantity == 0:
                    del self.inventory[item_id]
                    self.logger.info(f"Item {item_name} depleted and removed")

                    if self.on_inventory_change:
                        self.on_inventory_change(item_id, asdict(item), "removed")
                else:
                    if self.on_inventory_change:
                        self.on_inventory_change(item_id, asdict(item), "updated")

                break

    def simulate_item_addition(self, name: str, quantity: float, unit: str, category: str = "Other"):
        """Simulate adding a new item or increasing existing item quantity."""
        # Check if item already exists
        for item in self.inventory.values():
            if item.name == name:
                old_qty = item.quantity
                item.quantity += quantity
                item.last_seen = datetime.now().isoformat()

                self.logger.info(
                    f"Added {quantity} {unit} to {name}: "
                    f"{old_qty} -> {item.quantity}"
                )

                if self.on_inventory_change:
                    self.on_inventory_change(item.item_id, asdict(item), "updated")
                return

        # Create new item
        item_id = str(uuid.uuid4())
        item = FridgeItem(
            item_id=item_id,
            name=name,
            quantity=quantity,
            unit=unit,
            location="upper_shelf",
            category=category,
            confidence=0.92,
            last_seen=datetime.now().isoformat(),
        )

        self.inventory[item_id] = item
        self.logger.info(f"Added new item: {name} ({quantity} {unit})")

        if self.on_inventory_change:
            self.on_inventory_change(item_id, asdict(item), "added")


def main():
    """Run standalone simulator for testing."""
    print("=" * 70)
    print("Samsung Family Hub Smart Refrigerator Simulator")
    print("=" * 70)
    print("\nStarting simulator...")

    simulator = SamsungFridgeSimulator(
        device_name="Samsung Family Hub (Test)",
        port=5001
    )

    # Set up callbacks
    def on_inventory_change(item_id, item_data, event_type):
        print(f"\n[INVENTORY {event_type.upper()}] {item_data['name']}: "
              f"{item_data['quantity']} {item_data['unit']}")

    def on_door_open():
        print("\n[DOOR] Opened")

    def on_door_close():
        print("\n[DOOR] Closed")

    simulator.on_inventory_change = on_inventory_change
    simulator.on_door_open = on_door_open
    simulator.on_door_close = on_door_close

    print(f"\nAPI Endpoints:")
    print(f"  - Device Status: http://localhost:5001/api/devices/{simulator.device_id}/status")
    print(f"  - Inventory: http://localhost:5001/api/inventory")
    print(f"  - Health: http://localhost:5001/api/health")
    print("\nPress Ctrl+C to stop\n")

    try:
        simulator.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        simulator.stop()


if __name__ == "__main__":
    main()
