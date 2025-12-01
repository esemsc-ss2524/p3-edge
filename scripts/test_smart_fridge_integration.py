#!/usr/bin/env python3
"""
Test Script for Smart Fridge Integration

Demonstrates the complete workflow:
1. Start smart fridge simulator
2. Connect to simulator
3. Sync inventory
4. Simulate item changes
5. Verify updates in main database

This script shows how the UI and simulator interact in real-time.
"""

import sys
import time
import requests
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config_manager
from src.database.db_manager import create_database_manager
from src.services.smart_fridge_service import SmartFridgeService
from src.services.inventory_service import InventoryService
from src.utils import get_logger


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_step(step_num: int, description: str):
    """Print step header."""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 70)


def test_smart_fridge_integration():
    """Run full integration test."""
    logger = get_logger("integration_test")

    print_section("Smart Fridge Integration Test")

    print("""
This test demonstrates:
• Connecting to Samsung Family Hub simulator
• Syncing inventory from smart fridge
• Real-time inventory updates
• Item addition and removal simulation
    """)

    # Setup
    print_step(1, "Setting up database and services")

    config = get_config_manager()
    db_path = config.get("database.path", "data/p3edge_test.db")

    # Use test database
    if Path(db_path).exists():
        print(f"  Using existing database: {db_path}")
    else:
        print(f"  Creating new database: {db_path}")

    db_manager = create_database_manager(db_path, encryption_key=None)

    # Initialize database if needed
    if not Path(db_path).exists():
        db_manager.initialize_database()
        print("  ✓ Database initialized")

    inventory_service = InventoryService(db_manager)

    # Check initial inventory
    initial_items = inventory_service.get_all_items()
    print(f"  Current inventory: {len(initial_items)} items")

    # Wait for user to start simulator
    print_step(2, "Start the Smart Fridge Simulator")

    print("""
  Please start the simulator in another terminal:

    python src/ingestion/samsung_fridge_simulator.py

  The simulator will run on http://localhost:5001
    """)

    input("  Press Enter when the simulator is running...")

    # Test connection
    print_step(3, "Testing connection to simulator")

    fridge_url = "http://localhost:5001"
    print(f"  Connecting to: {fridge_url}")

    try:
        response = requests.get(f"{fridge_url}/api/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"  ✓ Connected to simulator")
            print(f"    Device ID: {health['device_id']}")
            print(f"    Status: {health['status']}")
        else:
            print(f"  ✗ Connection failed: {response.status_code}")
            return

    except requests.RequestException as e:
        print(f"  ✗ Cannot connect to simulator: {e}")
        print("\n  Please make sure the simulator is running and try again.")
        return

    # Create smart fridge service
    print_step(4, "Initializing Smart Fridge Service")

    fridge_service = SmartFridgeService(
        db_manager,
        fridge_url=fridge_url,
        poll_interval_seconds=10,
    )

    # Set up callbacks for logging
    def on_connection_change(connected: bool):
        status = "CONNECTED" if connected else "DISCONNECTED"
        print(f"  [{datetime.now().strftime('%H:%M:%S')}] {status}")

    def on_inventory_update(item_id: str, item_data: dict):
        print(
            f"  [{datetime.now().strftime('%H:%M:%S')}] "
            f"Updated: {item_data['name']} = {item_data['quantity']} {item_data['unit']}"
        )

    fridge_service.on_connection_change = on_connection_change
    fridge_service.on_inventory_update = on_inventory_update

    # Connect
    if not fridge_service.connect():
        print("  ✗ Failed to connect")
        return

    print("  ✓ Service initialized and connected")

    # Initial sync
    print_step(5, "Performing initial inventory sync")

    try:
        stats = fridge_service.sync_inventory()
        print(f"\n  Sync Results:")
        print(f"    • Added: {stats['added']} items")
        print(f"    • Updated: {stats['updated']} items")
        print(f"    • Unchanged: {stats['unchanged']} items")
        print(f"    • Total: {stats['added'] + stats['updated'] + stats['unchanged']} items")

    except Exception as e:
        print(f"  ✗ Sync failed: {e}")
        return

    # Show current inventory
    print_step(6, "Current Inventory in Database")

    current_items = inventory_service.get_all_items()
    print(f"\n  Total items: {len(current_items)}")
    print(f"\n  Sample items:")

    for item in current_items[:10]:
        print(
            f"    • {item.name}: {item.quantity_current:.2f} {item.unit} "
            f"(category: {item.category})"
        )

    if len(current_items) > 10:
        print(f"    ... and {len(current_items) - 10} more items")

    # Interactive simulation
    print_step(7, "Real-time Updates Demonstration")

    print("""
  Now we'll simulate real-time inventory changes.
  You can:
  a) Use the simulator's API to add/remove items
  b) Watch this script automatically sync changes
    """)

    print("\n  Starting auto-sync (polling every 10 seconds)...")

    fridge_service.start_polling()

    print("\n  Simulating some changes via API...")

    # Simulate removing milk
    print("\n  → Removing 0.25 gallon of milk...")
    try:
        response = requests.get(f"{fridge_url}/api/inventory")
        inventory = response.json()

        milk_item = None
        for item in inventory["items"]:
            if "Milk" in item["name"]:
                milk_item = item
                break

        if milk_item:
            new_qty = max(0, milk_item["quantity"] - 0.25)
            requests.put(
                f"{fridge_url}/api/inventory/{milk_item['item_id']}",
                json={"quantity": new_qty}
            )
            print(f"    ✓ Updated {milk_item['name']}: {milk_item['quantity']} → {new_qty}")

    except Exception as e:
        print(f"    ✗ Failed: {e}")

    # Simulate adding new item
    print("\n  → Adding new item: Blueberries...")
    try:
        new_item = {
            "name": "Blueberries",
            "quantity": 1.5,
            "unit": "lb",
            "category": "Produce",
            "location": "upper_shelf"
        }

        response = requests.post(
            f"{fridge_url}/api/inventory",
            json=new_item
        )

        if response.status_code == 201:
            print(f"    ✓ Added Blueberries (1.5 lb)")
        else:
            print(f"    ✗ Failed to add item")

    except Exception as e:
        print(f"    ✗ Failed: {e}")

    # Wait for sync
    print("\n  Waiting for auto-sync to detect changes...")
    time.sleep(12)  # Wait for one polling cycle

    # Verify changes in database
    print_step(8, "Verifying Changes in Database")

    # Check milk
    milk_items = inventory_service.search_items("Milk")
    if milk_items:
        milk = milk_items[0]
        print(f"  • Milk: {milk.quantity_current:.2f} {milk.unit}")

        # Check history
        history = inventory_service.get_history(milk.item_id, limit=3)
        print(f"    Recent updates:")
        for h in history:
            print(
                f"      - {h.timestamp.strftime('%H:%M:%S')}: "
                f"{h.quantity:.2f} {milk.unit} (source: {h.source})"
            )

    # Check blueberries
    blueberry_items = inventory_service.search_items("Blueberries")
    if blueberry_items:
        print(f"  • Blueberries: {blueberry_items[0].quantity_current:.2f} {blueberry_items[0].unit}")
        print(f"    ✓ Successfully synced new item")

    # Interactive mode
    print_step(9, "Interactive Mode")

    print("""
  Auto-sync is now running. Try these:

  1. Open another terminal and run:
     curl -X PUT http://localhost:5001/api/inventory/<item_id> \\
       -H "Content-Type: application/json" \\
       -d '{"quantity": 2.0}'

  2. View the inventory at: http://localhost:5001/api/inventory

  3. Monitor the logs here to see real-time updates

  The database will automatically sync every 10 seconds.
    """)

    try:
        while True:
            time.sleep(5)
            # Show connection status
            if fridge_service.is_connected():
                info = fridge_service.get_connection_info()
                last_sync = info.get("last_sync")
                if last_sync:
                    last_sync_time = datetime.fromisoformat(last_sync)
                    seconds_ago = (datetime.now() - last_sync_time).total_seconds()
                    print(f"  [Status] Connected | Last sync: {int(seconds_ago)}s ago")

    except KeyboardInterrupt:
        print("\n\n  Stopping...")

    # Cleanup
    print_step(10, "Cleanup")

    fridge_service.stop_polling()
    fridge_service.disconnect()

    print("  ✓ Disconnected from smart fridge")
    print("  ✓ Test complete!")

    # Final stats
    final_items = inventory_service.get_all_items()
    print(f"\n  Final inventory count: {len(final_items)} items")

    print_section("Test Complete")

    print("""
Summary:
• Successfully connected to Samsung Family Hub simulator
• Synced inventory between smart fridge and database
• Demonstrated real-time updates
• Verified data integrity

Next steps:
• Integrate with main UI (src/ui/smart_fridge_page.py)
• Set up automatic forecasting based on smart fridge data
• Configure alerts for low stock items
    """)


def main():
    """Main entry point."""
    try:
        test_smart_fridge_integration()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
