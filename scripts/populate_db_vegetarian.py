#!/usr/bin/env python3
"""
Database Population Script - 2 Months of Vegetarian Family Data

Generates realistic grocery shopping, consumption, and restocking patterns
for a vegetarian family over a 2-month period.

Simulates:
- Weekly shopping trips (usually Saturdays)
- Daily consumption patterns (more on weekends)
- Mid-week restocking for perishables
- Seasonal variations in produce consumption
- Special occasions (extra guests on weekends)
"""

import sys
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config_manager
from src.database.db_manager import create_database_manager
from src.models import InventoryItem, InventoryHistory
from src.services.inventory_service import InventoryService
from src.utils import get_logger


# Comprehensive vegetarian grocery items
VEGETARIAN_ITEMS = [
    # Dairy
    {
        "name": "Whole Milk",
        "category": "Dairy",
        "brand": "Organic Valley",
        "unit": "gallon",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 7,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,  # ~2 gallons/week
        "price": 6.99,
    },
    {
        "name": "Greek Yogurt",
        "category": "Dairy",
        "brand": "Chobani",
        "unit": "oz",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 14,
        "base_weekly_qty": 32.0,
        "consumption_per_day": 4.5,  # ~32oz/week
        "price": 5.49,
    },
    {
        "name": "Cheddar Cheese",
        "category": "Dairy",
        "brand": "Tillamook",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 30,
        "base_weekly_qty": 1.0,
        "consumption_per_day": 0.14,
        "price": 8.99,
    },
    {
        "name": "Butter",
        "category": "Dairy",
        "brand": "Land O'Lakes",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 90,
        "base_weekly_qty": 0.5,
        "consumption_per_day": 0.07,
        "price": 5.99,
    },
    {
        "name": "Mozzarella Cheese",
        "category": "Dairy",
        "brand": "Galbani",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 21,
        "base_weekly_qty": 0.75,
        "consumption_per_day": 0.11,
        "price": 7.49,
    },
    {
        "name": "Cream Cheese",
        "category": "Dairy",
        "brand": "Philadelphia",
        "unit": "oz",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 30,
        "base_weekly_qty": 8.0,
        "consumption_per_day": 1.1,
        "price": 3.99,
    },

    # Fresh Produce
    {
        "name": "Baby Spinach",
        "category": "Produce",
        "brand": "Organic Girl",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 5,
        "base_weekly_qty": 1.5,
        "consumption_per_day": 0.21,
        "price": 4.99,
    },
    {
        "name": "Romaine Lettuce",
        "category": "Produce",
        "brand": "Fresh Harvest",
        "unit": "head",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 7,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 2.99,
    },
    {
        "name": "Baby Carrots",
        "category": "Produce",
        "brand": "Bolthouse Farms",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 10,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 3.49,
    },
    {
        "name": "Bell Peppers",
        "category": "Produce",
        "brand": "Local Farms",
        "unit": "count",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 7,
        "base_weekly_qty": 5.0,
        "consumption_per_day": 0.7,
        "price": 1.49,
    },
    {
        "name": "Broccoli",
        "category": "Produce",
        "brand": "Fresh Express",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 5,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 2.99,
    },
    {
        "name": "Tomatoes",
        "category": "Produce",
        "brand": "Greenhouse",
        "unit": "lb",
        "location": "pantry",
        "perishable": True,
        "shelf_life_days": 5,
        "base_weekly_qty": 2.5,
        "consumption_per_day": 0.35,
        "price": 3.99,
    },
    {
        "name": "Cucumbers",
        "category": "Produce",
        "brand": "Fresh Farms",
        "unit": "count",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 7,
        "base_weekly_qty": 3.0,
        "consumption_per_day": 0.42,
        "price": 0.99,
    },
    {
        "name": "Mushrooms",
        "category": "Produce",
        "brand": "Monterey",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 5,
        "base_weekly_qty": 1.5,
        "consumption_per_day": 0.21,
        "price": 4.99,
    },
    {
        "name": "Avocados",
        "category": "Produce",
        "brand": "Mexico Fresh",
        "unit": "count",
        "location": "pantry",
        "perishable": True,
        "shelf_life_days": 4,
        "base_weekly_qty": 6.0,
        "consumption_per_day": 0.85,
        "price": 1.99,
    },
    {
        "name": "Bananas",
        "category": "Produce",
        "brand": "Chiquita",
        "unit": "lb",
        "location": "pantry",
        "perishable": True,
        "shelf_life_days": 5,
        "base_weekly_qty": 3.0,
        "consumption_per_day": 0.42,
        "price": 0.59,
    },
    {
        "name": "Apples",
        "category": "Produce",
        "brand": "Honeycrisp",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 14,
        "base_weekly_qty": 3.0,
        "consumption_per_day": 0.42,
        "price": 2.99,
    },
    {
        "name": "Strawberries",
        "category": "Produce",
        "brand": "Driscoll's",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 3,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 4.99,
    },
    {
        "name": "Blueberries",
        "category": "Produce",
        "brand": "Driscoll's",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 5,
        "base_weekly_qty": 1.0,
        "consumption_per_day": 0.14,
        "price": 5.99,
    },

    # Protein Sources
    {
        "name": "Tofu Extra Firm",
        "category": "Protein",
        "brand": "Nasoya",
        "unit": "lb",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 14,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 3.99,
    },
    {
        "name": "Tempeh",
        "category": "Protein",
        "brand": "Lightlife",
        "unit": "oz",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 10,
        "base_weekly_qty": 16.0,
        "consumption_per_day": 2.3,
        "price": 4.49,
    },
    {
        "name": "Black Beans Canned",
        "category": "Protein",
        "brand": "Goya",
        "unit": "can",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 4.0,
        "consumption_per_day": 0.57,
        "price": 1.29,
    },
    {
        "name": "Chickpeas Canned",
        "category": "Protein",
        "brand": "Goya",
        "unit": "can",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 4.0,
        "consumption_per_day": 0.57,
        "price": 1.29,
    },
    {
        "name": "Lentils Dried",
        "category": "Protein",
        "brand": "Bob's Red Mill",
        "unit": "lb",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 1.0,
        "consumption_per_day": 0.14,
        "price": 3.99,
    },
    {
        "name": "Eggs Large",
        "category": "Protein",
        "brand": "Happy Hen",
        "unit": "dozen",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 21,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 4.99,
    },

    # Grains & Pasta
    {
        "name": "Brown Rice",
        "category": "Grains",
        "brand": "Lundberg",
        "unit": "lb",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 4.99,
    },
    {
        "name": "Quinoa",
        "category": "Grains",
        "brand": "Ancient Harvest",
        "unit": "lb",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 1.0,
        "consumption_per_day": 0.14,
        "price": 6.99,
    },
    {
        "name": "Whole Wheat Pasta",
        "category": "Grains",
        "brand": "Barilla",
        "unit": "lb",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 2.99,
    },
    {
        "name": "Whole Wheat Bread",
        "category": "Grains",
        "brand": "Dave's Killer Bread",
        "unit": "loaf",
        "location": "pantry",
        "perishable": True,
        "shelf_life_days": 7,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 5.99,
    },
    {
        "name": "Oatmeal",
        "category": "Grains",
        "brand": "Quaker",
        "unit": "lb",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 1.0,
        "consumption_per_day": 0.14,
        "price": 4.49,
    },

    # Beverages
    {
        "name": "Orange Juice",
        "category": "Beverages",
        "brand": "Tropicana",
        "unit": "oz",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 7,
        "base_weekly_qty": 64.0,
        "consumption_per_day": 9.1,
        "price": 4.99,
    },
    {
        "name": "Almond Milk",
        "category": "Beverages",
        "brand": "Silk",
        "unit": "oz",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 7,
        "base_weekly_qty": 64.0,
        "consumption_per_day": 9.1,
        "price": 3.99,
    },

    # Condiments & Sauces
    {
        "name": "Olive Oil",
        "category": "Condiments",
        "brand": "Bertolli",
        "unit": "oz",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 16.0,
        "consumption_per_day": 2.3,
        "price": 12.99,
    },
    {
        "name": "Soy Sauce",
        "category": "Condiments",
        "brand": "Kikkoman",
        "unit": "oz",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 10.0,
        "consumption_per_day": 1.4,
        "price": 3.99,
    },
    {
        "name": "Marinara Sauce",
        "category": "Condiments",
        "brand": "Rao's",
        "unit": "jar",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 365,
        "base_weekly_qty": 2.0,
        "consumption_per_day": 0.28,
        "price": 7.99,
    },
    {
        "name": "Peanut Butter",
        "category": "Condiments",
        "brand": "Jif Natural",
        "unit": "oz",
        "location": "pantry",
        "perishable": False,
        "shelf_life_days": 180,
        "base_weekly_qty": 16.0,
        "consumption_per_day": 2.3,
        "price": 5.99,
    },
    {
        "name": "Hummus",
        "category": "Condiments",
        "brand": "Sabra",
        "unit": "oz",
        "location": "fridge",
        "perishable": True,
        "shelf_life_days": 7,
        "base_weekly_qty": 16.0,
        "consumption_per_day": 2.3,
        "price": 4.99,
    },
]


class VegetarianDataSimulator:
    """Simulates 2 months of realistic vegetarian family grocery data."""

    def __init__(self, db_manager, logger):
        self.db_manager = db_manager
        self.logger = logger
        self.inventory_service = InventoryService(db_manager)

        # Family parameters
        self.household_size = 4  # 2 adults, 2 kids
        self.start_date = datetime.now() - timedelta(days=60)  # 2 months ago
        self.end_date = datetime.now()

        # Shopping patterns
        self.main_shopping_day = 5  # Saturday (0=Monday)
        self.midweek_shopping_day = 2  # Wednesday for perishables

        # Consumption multipliers by day
        self.daily_multipliers = {
            0: 1.0,  # Monday
            1: 1.0,  # Tuesday
            2: 1.0,  # Wednesday
            3: 1.0,  # Thursday
            4: 1.1,  # Friday (eat more)
            5: 1.3,  # Saturday (home all day)
            6: 1.3,  # Sunday (home all day)
        }

        # Item registry
        self.items: Dict[str, InventoryItem] = {}

    def populate_database(self):
        """Main function to populate database with 2 months of data."""
        self.logger.info("=" * 70)
        self.logger.info("Starting 2-Month Vegetarian Family Data Population")
        self.logger.info("=" * 70)

        # Step 1: Create initial inventory items
        self.logger.info("\n[1/4] Creating initial inventory items...")
        self._create_initial_items()

        # Step 2: Simulate daily consumption and shopping
        self.logger.info("\n[2/4] Simulating 60 days of consumption and shopping...")
        self._simulate_60_days()

        # Step 3: Generate statistics
        self.logger.info("\n[3/4] Generating statistics...")
        self._print_statistics()

        # Step 4: Verify data integrity
        self.logger.info("\n[4/4] Verifying data integrity...")
        self._verify_data()

        self.logger.info("\n" + "=" * 70)
        self.logger.info("Database population complete!")
        self.logger.info("=" * 70)

    def _create_initial_items(self):
        """Create all inventory items with initial quantities."""
        for template in VEGETARIAN_ITEMS:
            # Determine initial quantity (simulate half-full pantry)
            if template["unit"] in ["gallon", "dozen", "loaf", "head", "jar"]:
                initial_qty = round(random.uniform(0.5, template["base_weekly_qty"]), 2)
            elif template["unit"] in ["lb"]:
                initial_qty = round(random.uniform(0.3, template["base_weekly_qty"] * 0.8), 2)
            elif template["unit"] == "can":
                initial_qty = random.randint(1, int(template["base_weekly_qty"] * 2))
            elif template["unit"] == "count":
                initial_qty = random.randint(1, int(template["base_weekly_qty"]))
            else:  # oz
                initial_qty = round(random.uniform(8, template["base_weekly_qty"] * 0.8), 1)

            # Calculate expiry date for perishables
            expiry_date = None
            if template["perishable"]:
                days_until_expiry = random.randint(
                    max(1, template["shelf_life_days"] // 2),
                    template["shelf_life_days"]
                )
                expiry_date = (self.start_date + timedelta(days=days_until_expiry)).date()

            # Create inventory item
            item = InventoryItem(
                name=template["name"],
                category=template["category"],
                brand=template["brand"],
                unit=template["unit"],
                quantity_current=initial_qty,
                quantity_min=template["base_weekly_qty"] * 0.3,
                quantity_max=template["base_weekly_qty"] * 3,
                location=template["location"],
                perishable=template["perishable"],
                expiry_date=expiry_date,
                consumption_rate=template["consumption_per_day"],
                last_updated=self.start_date,
                created_at=self.start_date,
                metadata={"price": template["price"]},
            )

            # Save to database
            item_id = self.inventory_service.create_item(item)
            self.items[template["name"]] = item

            self.logger.info(
                f"  Created: {template['name']} - {initial_qty:.2f} {template['unit']}"
            )

        self.logger.info(f"\nCreated {len(self.items)} inventory items")

    def _simulate_60_days(self):
        """Simulate 60 days of daily consumption and weekly shopping."""
        current_date = self.start_date
        shopping_trips = 0
        consumption_events = 0

        while current_date <= self.end_date:
            day_of_week = current_date.weekday()

            # Simulate daily consumption
            consumption_events += self._simulate_daily_consumption(current_date, day_of_week)

            # Main shopping trip (Saturdays)
            if day_of_week == self.main_shopping_day:
                shopping_trips += 1
                self._simulate_main_shopping(current_date)
                self.logger.info(
                    f"  Day {(current_date - self.start_date).days + 1}: "
                    f"MAIN SHOPPING TRIP #{shopping_trips}"
                )

            # Mid-week perishables restock (Wednesdays)
            elif day_of_week == self.midweek_shopping_day:
                self._simulate_midweek_shopping(current_date)
                self.logger.debug(f"  Day {(current_date - self.start_date).days + 1}: Mid-week restock")

            current_date += timedelta(days=1)

        self.logger.info(
            f"\nSimulated {shopping_trips} shopping trips and "
            f"{consumption_events} consumption updates"
        )

    def _simulate_daily_consumption(
        self,
        current_date: datetime,
        day_of_week: int
    ) -> int:
        """Simulate daily consumption for all items."""
        multiplier = self.daily_multipliers[day_of_week]
        updates = 0

        for template in VEGETARIAN_ITEMS:
            item = self.items[template["name"]]

            if item.quantity_current <= 0:
                continue

            # Calculate consumption with variation
            base_consumption = template["consumption_per_day"] * multiplier
            variation = random.uniform(0.8, 1.2)  # ±20% variation
            consumption = base_consumption * variation

            # Apply consumption
            new_qty = max(0, item.quantity_current - consumption)
            item.quantity_current = round(new_qty, 2)
            item.last_updated = current_date

            # Update in database
            self.inventory_service.update_quantity(
                item.item_id,
                item.quantity_current,
                source="system",
                notes=f"Daily consumption on {current_date.date()}"
            )

            updates += 1

        return updates

    def _simulate_main_shopping(self, shop_date: datetime):
        """Simulate main weekly shopping trip (Saturdays)."""
        # Check if special occasion (30% chance on weekends)
        has_guests = random.random() < 0.3
        guest_multiplier = 1.5 if has_guests else 1.0

        for template in VEGETARIAN_ITEMS:
            item = self.items[template["name"]]

            # Decide if item needs restocking
            threshold = item.quantity_min * 1.5

            if item.quantity_current < threshold or template["perishable"]:
                # Calculate restock quantity
                target_qty = template["base_weekly_qty"] * guest_multiplier

                if not template["perishable"]:
                    # Stock up more for non-perishables
                    target_qty *= random.uniform(2.0, 3.0)

                # Round based on unit
                if template["unit"] in ["can", "count", "dozen", "loaf", "jar", "head"]:
                    restock_qty = int(round(target_qty))
                else:
                    restock_qty = round(target_qty, 2)

                # Add to inventory
                new_qty = item.quantity_current + restock_qty
                item.quantity_current = round(new_qty, 2)
                item.last_updated = shop_date

                # Update expiry for perishables
                if template["perishable"]:
                    item.expiry_date = (shop_date + timedelta(days=template["shelf_life_days"])).date()

                # Update in database
                self.inventory_service.update_quantity(
                    item.item_id,
                    item.quantity_current,
                    source="receipt",
                    notes=f"Main shopping trip - restocked {restock_qty:.2f} {template['unit']}"
                )

    def _simulate_midweek_shopping(self, shop_date: datetime):
        """Simulate mid-week perishables restock (Wednesdays)."""
        for template in VEGETARIAN_ITEMS:
            # Only restock perishables that are running low
            if not template["perishable"]:
                continue

            # Only restock highly perishable items (shelf life < 7 days)
            if template["shelf_life_days"] > 7:
                continue

            item = self.items[template["name"]]

            # Restock if below 50% of min threshold
            if item.quantity_current < item.quantity_min * 0.5:
                # Small restock to last until Saturday
                restock_qty = template["base_weekly_qty"] * 0.5

                if template["unit"] in ["count", "head"]:
                    restock_qty = int(round(restock_qty))
                else:
                    restock_qty = round(restock_qty, 2)

                new_qty = item.quantity_current + restock_qty
                item.quantity_current = round(new_qty, 2)
                item.last_updated = shop_date
                item.expiry_date = (shop_date + timedelta(days=template["shelf_life_days"])).date()

                # Update in database
                self.inventory_service.update_quantity(
                    item.item_id,
                    item.quantity_current,
                    source="receipt",
                    notes=f"Mid-week restock - {restock_qty:.2f} {template['unit']}"
                )

    def _print_statistics(self):
        """Print statistics about generated data."""
        stats = self.inventory_service.get_stats()

        self.logger.info(f"  Total items: {stats['total_items']}")
        self.logger.info(f"  Low stock items: {stats['low_stock_items']}")
        self.logger.info(f"  Expired items: {stats['expired_items']}")

        # Count history entries
        total_history = 0
        for template in VEGETARIAN_ITEMS:
            item = self.items[template["name"]]
            history = self.inventory_service.get_history(item.item_id, limit=1000)
            total_history += len(history)

        self.logger.info(f"  Total history entries: {total_history}")

        # Show current inventory levels
        self.logger.info("\n  Current inventory levels (sample):")
        for i, template in enumerate(VEGETARIAN_ITEMS[:10]):
            item = self.items[template["name"]]
            self.logger.info(
                f"    {template['name']}: {item.quantity_current:.2f} {template['unit']}"
            )

    def _verify_data(self):
        """Verify data integrity."""
        all_items = self.inventory_service.get_all_items()

        if len(all_items) != len(VEGETARIAN_ITEMS):
            self.logger.error(
                f"  ✗ Item count mismatch: expected {len(VEGETARIAN_ITEMS)}, "
                f"got {len(all_items)}"
            )
        else:
            self.logger.info(f"  ✓ All {len(all_items)} items present")

        # Check history
        has_history = True
        for item in all_items[:5]:  # Check first 5
            history = self.inventory_service.get_history(item.item_id, limit=10)
            if len(history) == 0:
                self.logger.warning(f"  ⚠ No history for {item.name}")
                has_history = False

        if has_history:
            self.logger.info("  ✓ History entries present")


def main():
    """Main entry point."""
    logger = get_logger("populate_db")

    # Get configuration
    config = get_config_manager()
    db_path = config.get("database.path", "data/p3edge.db")
    encrypted = config.get("database.encrypted", False)  # Use unencrypted for easier testing

    # Create database manager
    encryption_key = None
    if encrypted:
        encryption_key = config.get_database_encryption_key()

    logger.info(f"Using database: {db_path}")
    logger.info(f"Encryption: {'ENABLED' if encrypted else 'DISABLED'}")

    db_manager = create_database_manager(db_path, encryption_key)

    # Initialize database if needed
    if not Path(db_path).exists():
        logger.info("Database not found, initializing...")
        db_manager.initialize_database()

    # Run simulator
    simulator = VegetarianDataSimulator(db_manager, logger)

    try:
        simulator.populate_database()
        logger.info("\n✓ Database successfully populated with 2 months of vegetarian family data!")
        logger.info(f"Database location: {db_path}")

    except Exception as e:
        logger.error(f"\n✗ Failed to populate database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
