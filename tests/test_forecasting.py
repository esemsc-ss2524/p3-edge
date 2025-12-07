#!/usr/bin/env python3
"""
Test script for the forecasting engine

This script:
1. Creates sample inventory items
2. Simulates consumption over time
3. Generates forecasts
4. Displays results

Run with: python scripts/test_forecasting.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import uuid

from src.database.db_manager import create_database_manager
from src.services.inventory_service import InventoryService
from src.services.forecast_service import ForecastService
from src.models.inventory import InventoryItem


def create_sample_items(inventory_service: InventoryService) -> list:
    """Create sample inventory items."""
    print("Creating sample inventory items...")

    items = [
        {
            "name": "Milk",
            "category": "dairy",
            "brand": "Organic Valley",
            "unit": "gallon",
            "quantity_current": 2.0,
            "quantity_min": 0.5,
            "quantity_max": 3.0,
            "location": "fridge",
            "perishable": True,
            "expiry_date": (datetime.now() + timedelta(days=7)).date(),
        },
        {
            "name": "Eggs",
            "category": "dairy",
            "brand": "Farm Fresh",
            "unit": "dozen",
            "quantity_current": 1.5,
            "quantity_min": 0.5,
            "quantity_max": 2.0,
            "location": "fridge",
            "perishable": True,
            "expiry_date": (datetime.now() + timedelta(days=14)).date(),
        },
        {
            "name": "Bread",
            "category": "bakery",
            "brand": "Wonder",
            "unit": "loaf",
            "quantity_current": 2.0,
            "quantity_min": 1.0,
            "quantity_max": 3.0,
            "location": "pantry",
            "perishable": True,
            "expiry_date": (datetime.now() + timedelta(days=5)).date(),
        },
        {
            "name": "Rice",
            "category": "grains",
            "brand": "Basmati",
            "unit": "lb",
            "quantity_current": 5.0,
            "quantity_min": 2.0,
            "quantity_max": 10.0,
            "location": "pantry",
            "perishable": False,
            "expiry_date": None,
        },
        {
            "name": "Chicken Breast",
            "category": "meat",
            "brand": "Perdue",
            "unit": "lb",
            "quantity_current": 3.0,
            "quantity_min": 1.0,
            "quantity_max": 5.0,
            "location": "freezer",
            "perishable": True,
            "expiry_date": (datetime.now() + timedelta(days=30)).date(),
        },
    ]

    created_items = []
    for item_data in items:
        item = InventoryItem(
            item_id=str(uuid.uuid4()),
            **item_data,
            last_updated=datetime.now(),
            consumption_rate=0.0,
        )
        inventory_service.create_item(item)
        created_items.append(item)
        print(f"  ✓ Created: {item.name}")

    return created_items


def simulate_consumption(
    inventory_service: InventoryService,
    forecast_service: ForecastService,
    items: list,
    days: int = 14,
):
    """Simulate consumption over time."""
    print(f"\nSimulating consumption over {days} days...")

    # Define consumption patterns (units per day)
    consumption_patterns = {
        "Milk": 0.25,  # 1/4 gallon per day
        "Eggs": 0.15,  # ~2 eggs per day
        "Bread": 0.2,   # 1/5 loaf per day
        "Rice": 0.1,    # 0.1 lb per day
        "Chicken Breast": 0.2,  # 0.2 lb per day
    }

    for day in range(days):
        current_date = datetime.now() - timedelta(days=days - day)

        for item in items:
            consumption_rate = consumption_patterns.get(item.name, 0.1)

            # Add some randomness
            import random
            actual_consumption = consumption_rate * random.uniform(0.8, 1.2)

            # Update quantity
            new_quantity = max(0, item.quantity_current - actual_consumption)

            # Update inventory
            inventory_service.update_quantity(
                item.item_id,
                new_quantity,
                source="manual",
                notes=f"Day {day + 1} consumption",
            )

            # Update forecast model with observation
            forecast_service.update_with_observation(
                item.item_id,
                new_quantity,
                source="manual",
                timestamp=current_date,
            )

            # Update local item for next iteration
            item.quantity_current = new_quantity

        if (day + 1) % 7 == 0:
            print(f"  Day {day + 1}: Updated all items")

    print("  ✓ Simulation complete")


def generate_and_display_forecasts(
    forecast_service: ForecastService,
    items: list,
):
    """Generate and display forecasts."""
    print("\nGenerating forecasts...")

    forecasts = []
    for item in items:
        forecast = forecast_service.generate_forecast(
            item.item_id,
            n_days=14,
            save_to_db=True,
        )

        if forecast:
            forecasts.append(forecast)
            print(f"  ✓ Generated forecast for: {item.name}")

    print("\n" + "=" * 80)
    print("FORECAST RESULTS")
    print("=" * 80)

    for item, forecast in zip(items, forecasts):
        if not forecast:
            continue

        print(f"\n{item.name} ({item.unit})")
        print("-" * 40)
        print(f"  Current Quantity: {item.quantity_current:.2f}")
        print(f"  Min Threshold: {item.quantity_min:.2f}")

        if forecast.predicted_runout_date:
            days_until = (forecast.predicted_runout_date - datetime.now().date()).days
            print(f"  Predicted Runout: {forecast.predicted_runout_date} ({days_until} days)")
            print(f"  Confidence: {forecast.confidence * 100:.1f}%")

            if forecast.recommended_order_date:
                print(f"  Recommended Order Date: {forecast.recommended_order_date}")
        else:
            print("  No runout predicted within 14 days")

        # Get model performance
        performance = forecast_service.get_model_performance(item.item_id)
        if performance:
            print(f"  Model MAE: {performance['mae']:.3f}")
            print(f"  Model RMSE: {performance['rmse']:.3f}")
            print(f"  Observations Used: {performance['n_observations']}")

    print("\n" + "=" * 80)


def test_low_stock_predictions(forecast_service: ForecastService):
    """Test low stock prediction filtering."""
    print("\nLow Stock Predictions (Next 7 Days):")
    print("-" * 40)

    low_stock = forecast_service.get_low_stock_predictions(days_ahead=7)

    if not low_stock:
        print("  ✓ No items predicted to run low in the next 7 days")
    else:
        for forecast in low_stock:
            days_until = (forecast.predicted_runout_date - datetime.now().date()).days
            print(f"  ⚠️  Item {forecast.item_id}: {days_until} days until runout")


def main():
    """Main test function."""
    print("=" * 80)
    print("FORECASTING ENGINE TEST")
    print("=" * 80)

    # Clean up any existing test database
    test_db_path = Path("data/p3edge_test.db")
    if test_db_path.exists():
        print("\nCleaning up existing test database...")
        test_db_path.unlink()
        print("  ✓ Old database removed")

    # Initialize database (unencrypted for testing)
    print("\nInitializing test database...")
    db_manager = create_database_manager(
        db_path=str(test_db_path),
        encryption_key=None  # Unencrypted for testing
    )
    db_manager.initialize_database()
    print("  ✓ Database initialized")

    # Create services with test model directory
    test_model_dir = Path("data/test_models")
    if test_model_dir.exists():
        import shutil
        shutil.rmtree(test_model_dir)
        print("  ✓ Old models removed")

    inventory_service = InventoryService(db_manager)
    forecast_service = ForecastService(db_manager, model_dir=test_model_dir)

    # Create sample items
    items = create_sample_items(inventory_service)

    # Simulate consumption
    simulate_consumption(
        inventory_service,
        forecast_service,
        items,
        days=14,
    )

    # Generate and display forecasts
    generate_and_display_forecasts(forecast_service, items)

    # Test low stock predictions
    test_low_stock_predictions(forecast_service)

    # Save models
    print("\nSaving forecast models...")
    forecast_service.save_all_models()
    print("  ✓ Models saved")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nYou can now run the main application to view forecasts in the UI:")
    print("  python src/main.py")


if __name__ == "__main__":
    main()
