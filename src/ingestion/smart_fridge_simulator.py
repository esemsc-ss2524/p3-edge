"""
Smart fridge API simulator for testing data ingestion.

Generates realistic mock data simulating a smart refrigerator.
"""

import random
from datetime import date, datetime, timedelta
from typing import Dict, List

from src.models import InventoryItem
from src.utils import get_logger


class SmartFridgeSimulator:
    """Simulates a smart refrigerator providing inventory data."""

    def __init__(self, seed: int = 42):
        """
        Initialize smart fridge simulator.

        Args:
            seed: Random seed for reproducible data
        """
        self.logger = get_logger("smart_fridge")
        random.seed(seed)

        # Sample grocery items commonly found in refrigerators
        self.sample_items = [
            {
                "name": "Whole Milk",
                "category": "Dairy",
                "brand": "Organic Valley",
                "unit": "gallon",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 7,
            },
            {
                "name": "Large Eggs",
                "category": "Dairy",
                "brand": "Happy Hen",
                "unit": "dozen",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 21,
            },
            {
                "name": "Cheddar Cheese",
                "category": "Dairy",
                "brand": "Tillamook",
                "unit": "lb",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 30,
            },
            {
                "name": "Greek Yogurt",
                "category": "Dairy",
                "brand": "Chobani",
                "unit": "oz",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 14,
            },
            {
                "name": "Baby Carrots",
                "category": "Produce",
                "brand": "Bolthouse Farms",
                "unit": "lb",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 10,
            },
            {
                "name": "Romaine Lettuce",
                "category": "Produce",
                "brand": "Fresh Harvest",
                "unit": "head",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 5,
            },
            {
                "name": "Strawberries",
                "category": "Produce",
                "brand": "Driscoll's",
                "unit": "lb",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 3,
            },
            {
                "name": "Orange Juice",
                "category": "Beverages",
                "brand": "Tropicana",
                "unit": "oz",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 10,
            },
            {
                "name": "Chicken Breast",
                "category": "Meat & Seafood",
                "brand": "Tyson",
                "unit": "lb",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 2,
            },
            {
                "name": "Ground Beef",
                "category": "Meat & Seafood",
                "brand": "Angus",
                "unit": "lb",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 2,
            },
            {
                "name": "Butter",
                "category": "Dairy",
                "brand": "Land O'Lakes",
                "unit": "lb",
                "location": "Fridge",
                "perishable": True,
                "shelf_life_days": 90,
            },
            {
                "name": "Ketchup",
                "category": "Condiments",
                "brand": "Heinz",
                "unit": "oz",
                "location": "Fridge",
                "perishable": False,
                "shelf_life_days": 365,
            },
        ]

    def get_initial_inventory(self) -> List[InventoryItem]:
        """
        Get initial inventory snapshot.

        Returns:
            List of InventoryItems
        """
        self.logger.info("Generating initial smart fridge inventory")

        items = []
        for template in self.sample_items:
            # Random initial quantity
            if template["unit"] in ["gallon", "dozen", "head", "lb"]:
                qty = round(random.uniform(0.5, 3.0), 2)
            else:  # oz
                qty = round(random.uniform(4, 32), 1)

            # Calculate expiry date for perishables
            expiry = None
            if template["perishable"]:
                days_until_expiry = random.randint(
                    1, template["shelf_life_days"]
                )
                expiry = date.today() + timedelta(days=days_until_expiry)

            # Create inventory item
            item = InventoryItem(
                name=template["name"],
                category=template["category"],
                brand=template["brand"],
                unit=template["unit"],
                quantity_current=qty,
                quantity_min=0.5 if template["unit"] in ["gallon", "dozen", "head", "lb"] else 4,
                quantity_max=5.0 if template["unit"] in ["gallon", "dozen", "head", "lb"] else 64,
                location=template["location"],
                perishable=template["perishable"],
                expiry_date=expiry,
                consumption_rate=self._estimate_consumption_rate(template),
            )
            items.append(item)

        self.logger.info(f"Generated {len(items)} initial inventory items")
        return items

    def simulate_consumption(
        self, current_items: List[InventoryItem], days: int = 1
    ) -> Dict[str, float]:
        """
        Simulate consumption over specified days.

        Args:
            current_items: Current inventory items
            days: Number of days to simulate

        Returns:
            Dictionary of {item_id: new_quantity}
        """
        updates = {}

        for item in current_items:
            if item.consumption_rate and item.consumption_rate > 0:
                # Calculate consumption with some randomness
                base_consumption = item.consumption_rate * days
                variation = random.uniform(0.8, 1.2)  # ±20% variation
                consumption = base_consumption * variation

                # New quantity (cannot go below 0)
                new_qty = max(0, item.quantity_current - consumption)
                updates[item.item_id] = round(new_qty, 2)

        self.logger.info(f"Simulated {days} days of consumption for {len(updates)} items")
        return updates

    def _estimate_consumption_rate(self, template: Dict) -> float:
        """
        Estimate consumption rate for an item.

        Args:
            template: Item template

        Returns:
            Consumption rate in units per day
        """
        # Consumption patterns (units per day for household of 4)
        patterns = {
            "Whole Milk": 0.15,  # gallon/day
            "Large Eggs": 0.2,  # dozen/day
            "Cheddar Cheese": 0.05,  # lb/day
            "Greek Yogurt": 2.0,  # oz/day
            "Baby Carrots": 0.1,  # lb/day
            "Romaine Lettuce": 0.15,  # head/day
            "Strawberries": 0.2,  # lb/day
            "Orange Juice": 4.0,  # oz/day
            "Chicken Breast": 0.3,  # lb/day
            "Ground Beef": 0.25,  # lb/day
            "Butter": 0.02,  # lb/day
            "Ketchup": 0.5,  # oz/day
        }

        return patterns.get(template["name"], 0.1)

    def add_random_items(self, count: int = 3) -> List[InventoryItem]:
        """
        Add random new items (simulating grocery delivery).

        Args:
            count: Number of items to add

        Returns:
            List of new InventoryItems
        """
        self.logger.info(f"Generating {count} random new items")

        selected = random.sample(self.sample_items, min(count, len(self.sample_items)))
        items = []

        for template in selected:
            # Full quantity for new items
            if template["unit"] in ["gallon", "dozen", "head", "lb"]:
                qty = round(random.uniform(1.5, 4.0), 2)
            else:
                qty = round(random.uniform(16, 64), 1)

            # Fresh expiry date
            expiry = None
            if template["perishable"]:
                expiry = date.today() + timedelta(days=template["shelf_life_days"])

            item = InventoryItem(
                name=template["name"],
                category=template["category"],
                brand=template["brand"],
                unit=template["unit"],
                quantity_current=qty,
                quantity_min=0.5 if template["unit"] in ["gallon", "dozen", "head", "lb"] else 4,
                quantity_max=5.0 if template["unit"] in ["gallon", "dozen", "head", "lb"] else 64,
                location=template["location"],
                perishable=template["perishable"],
                expiry_date=expiry,
                consumption_rate=self._estimate_consumption_rate(template),
            )
            items.append(item)

        return items


# Convenience function
def get_mock_inventory() -> List[InventoryItem]:
    """
    Get mock inventory for testing.

    Returns:
        List of mock InventoryItems
    """
    simulator = SmartFridgeSimulator()
    return simulator.get_initial_inventory()
