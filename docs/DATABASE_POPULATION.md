# Database Population Guide

## Overview

The database population script (`scripts/populate_db_vegetarian.py`) generates 2 months of realistic grocery shopping and consumption data for a vegetarian family. This is useful for:

- Testing forecasting algorithms
- Demonstrating the application with realistic data
- Training machine learning models
- Performance testing with substantial historical data

## Features

### Realistic Simulation

The script simulates:

1. **Weekly Shopping Patterns**
   - Main shopping trips every Saturday
   - Mid-week restocking on Wednesdays for highly perishable items
   - Special occasion purchases (30% chance on weekends)

2. **Daily Consumption**
   - Realistic consumption rates based on household size (4 people: 2 adults, 2 kids)
   - Higher consumption on weekends (30% more)
   - Friday evening increase (10% more)
   - Day-to-day variation (±20%)

3. **Item Lifecycle**
   - Perishables: shorter shelf life, frequent restocking
   - Non-perishables: bulk buying, less frequent purchases
   - Expiry date tracking for all perishable items

4. **Comprehensive Vegetarian Items**
   - 35+ different grocery items
   - Categories: Dairy, Produce, Protein, Grains, Beverages, Condiments
   - Realistic prices, units, and consumption rates

## Item Categories

### Dairy (6 items)
- Whole Milk, Greek Yogurt, Cheddar Cheese, Butter, Mozzarella, Cream Cheese
- Weekly consumption: ~10-15 items
- High perishability, frequent restocking

### Fresh Produce (12 items)
- Leafy Greens: Baby Spinach, Romaine Lettuce
- Vegetables: Baby Carrots, Bell Peppers, Broccoli, Tomatoes, Cucumbers, Mushrooms
- Fruits: Avocados, Bananas, Apples, Strawberries, Blueberries
- Weekly consumption: ~20-30 items
- Highest perishability (3-7 day shelf life)

### Protein Sources (6 items)
- Plant-based: Tofu, Tempeh, Lentils
- Canned: Black Beans, Chickpeas
- Eggs
- Weekly consumption: ~15-20 items

### Grains & Pasta (5 items)
- Brown Rice, Quinoa, Whole Wheat Pasta, Whole Wheat Bread, Oatmeal
- Lower consumption rate, bulk purchasing
- Long shelf life

### Beverages (2 items)
- Orange Juice, Almond Milk
- Medium perishability, moderate consumption

### Condiments & Sauces (5 items)
- Olive Oil, Soy Sauce, Marinara Sauce, Peanut Butter, Hummus
- Low consumption, long shelf life (except Hummus)

## Usage

### Basic Usage

```bash
cd /home/user/p3-edge
python scripts/populate_db_vegetarian.py
```

### Output

```
======================================================================
  Starting 2-Month Vegetarian Family Data Population
======================================================================

[1/4] Creating initial inventory items...
  Created: Whole Milk - 1.23 gallon
  Created: Greek Yogurt - 18.50 oz
  Created: Baby Spinach - 0.85 lb
  ...
Created 35 inventory items

[2/4] Simulating 60 days of consumption and shopping...
  Day 1: Daily consumption
  Day 6: MAIN SHOPPING TRIP #1
  Day 10: Mid-week restock
  ...
Simulated 9 shopping trips and 2100 consumption updates

[3/4] Generating statistics...
  Total items: 35
  Low stock items: 3
  Expired items: 0
  Total history entries: 2135

  Current inventory levels (sample):
    Whole Milk: 0.67 gallon
    Greek Yogurt: 12.30 oz
    ...

[4/4] Verifying data integrity...
  ✓ All 35 items present
  ✓ History entries present

======================================================================
Database population complete!
======================================================================

✓ Database successfully populated with 2 months of vegetarian family data!
Database location: data/p3edge.db
```

## Data Structure

### Inventory Items

Each item includes:

```python
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
    "price": 4.99
}
```

### Shopping Patterns

#### Main Shopping Trip (Saturday)

```python
# For each item:
if item.quantity_current < threshold or item.perishable:
    # Restock amount
    restock_qty = base_weekly_qty * guest_multiplier

    # Non-perishables: stock up more (2-3x)
    if not perishable:
        restock_qty *= random.uniform(2.0, 3.0)

    # Add to inventory
    item.quantity_current += restock_qty

    # Update expiry for perishables
    if perishable:
        item.expiry_date = today + shelf_life_days
```

#### Mid-Week Restock (Wednesday)

```python
# Only highly perishable items (shelf life < 7 days)
if perishable and shelf_life_days <= 7:
    if item.quantity_current < item.quantity_min * 0.5:
        # Small restock to last until Saturday
        restock_qty = base_weekly_qty * 0.5
        item.quantity_current += restock_qty
```

#### Daily Consumption

```python
# Apply daily multiplier (weekends = more consumption)
multiplier = daily_multipliers[day_of_week]

# Calculate consumption with variation
base_consumption = consumption_per_day * multiplier
variation = random.uniform(0.8, 1.2)  # ±20%
consumption = base_consumption * variation

# Apply consumption
new_qty = max(0, item.quantity_current - consumption)
```

## Database Schema

### Tables Populated

1. **`inventory`**: 35 items with current state
2. **`inventory_history`**: ~2,100+ entries (60 days × 35 items)
3. **`audit_log`**: All creation and update events

### History Entries

Each inventory change is recorded:

```sql
INSERT INTO inventory_history (
    history_id,
    item_id,
    quantity,
    timestamp,
    source,  -- 'system', 'receipt', 'manual'
    notes
)
```

Example:
```
| history_id | item_id | quantity | timestamp           | source  | notes                |
|------------|---------|----------|---------------------|---------|----------------------|
| uuid-1     | item-1  | 1.75     | 2024-09-01 08:00:00 | system  | Initial creation     |
| uuid-2     | item-1  | 1.47     | 2024-09-02 00:00:00 | system  | Daily consumption    |
| uuid-3     | item-1  | 3.22     | 2024-09-07 10:00:00 | receipt | Main shopping trip   |
```

## Consumption Patterns

### Daily Multipliers

```python
{
    0: 1.0,   # Monday (normal)
    1: 1.0,   # Tuesday (normal)
    2: 1.0,   # Wednesday (normal)
    3: 1.0,   # Thursday (normal)
    4: 1.1,   # Friday (10% more - dinner out)
    5: 1.3,   # Saturday (30% more - home all day)
    6: 1.3,   # Sunday (30% more - home all day)
}
```

### Special Occasions

30% chance on weekends of having guests:
- Guest multiplier: 1.5x
- Affects shopping quantities
- Simulates entertaining, parties, etc.

## Realistic Quantities

### Unit-Based Rounding

```python
# Gallons, dozens, loaves, jars, heads
restock_qty = int(round(target_qty))  # Whole units

# Pounds, ounces
restock_qty = round(target_qty, 2)    # Two decimals

# Cans, counts
restock_qty = int(round(target_qty))  # Whole numbers
```

### Example Weekly Consumption (4-person family)

| Item | Unit | Weekly | Daily | Notes |
|------|------|--------|-------|-------|
| Whole Milk | gallon | 2.0 | 0.28 | ~1 cup per person/day |
| Eggs | dozen | 2.0 | 0.28 | ~4 eggs/day |
| Bananas | lb | 3.0 | 0.42 | ~6 bananas/week |
| Spinach | lb | 1.5 | 0.21 | Salads, smoothies |
| Rice | lb | 2.0 | 0.28 | Side dish most days |
| Yogurt | oz | 32 | 4.5 | ~1 cup per person/day |

## Customization

### Adjust Household Size

Edit the script:

```python
class VegetarianDataSimulator:
    def __init__(self, db_manager, logger):
        # Change household size
        self.household_size = 6  # Default: 4

        # Adjust consumption rates proportionally
        for template in VEGETARIAN_ITEMS:
            template["consumption_per_day"] *= (6 / 4)
```

### Change Time Period

```python
# Modify start and end dates
self.start_date = datetime.now() - timedelta(days=90)  # 3 months
self.end_date = datetime.now()
```

### Add Custom Items

```python
VEGETARIAN_ITEMS.append({
    "name": "Coconut Milk",
    "category": "Beverages",
    "brand": "Thai Kitchen",
    "unit": "oz",
    "location": "pantry",
    "perishable": False,
    "shelf_life_days": 365,
    "base_weekly_qty": 16.0,
    "consumption_per_day": 2.3,
    "price": 2.99,
})
```

### Modify Shopping Days

```python
# Change main shopping day
self.main_shopping_day = 6  # Sunday (0=Monday, 6=Sunday)

# Change mid-week restock day
self.midweek_shopping_day = 1  # Tuesday
```

## Validation

The script includes built-in validation:

### Data Integrity Checks

```python
def _verify_data(self):
    """Verify data integrity."""

    # Check item count
    all_items = self.inventory_service.get_all_items()
    assert len(all_items) == len(VEGETARIAN_ITEMS)

    # Check history exists
    for item in all_items:
        history = self.inventory_service.get_history(item.item_id)
        assert len(history) > 0

    # Check quantities are non-negative
    for item in all_items:
        assert item.quantity_current >= 0
```

## Performance

### Execution Time

- **Small dataset** (35 items, 60 days): ~5-10 seconds
- **Large dataset** (100 items, 180 days): ~30-45 seconds

### Database Size

- **2 months, 35 items**: ~500 KB
- **6 months, 100 items**: ~5-10 MB
- Includes all history entries and audit logs

### Memory Usage

- Peak memory: ~50-100 MB
- Mostly in-memory processing
- Batch commits to database

## Use Cases

### 1. Testing Forecasting Models

```bash
# Populate database
python scripts/populate_db_vegetarian.py

# Train forecasting models
python scripts/test_forecasting.py
```

### 2. Demo Mode

```bash
# Create demo database
export P3_DATABASE_PATH=data/demo.db
python scripts/populate_db_vegetarian.py

# Launch UI with demo data
python src/main.py
```

### 3. Performance Testing

```python
# Modify script for stress testing
self.household_size = 10
self.start_date = datetime.now() - timedelta(days=365)  # 1 year

# Add 100+ items
VEGETARIAN_ITEMS.extend(generate_random_items(100))
```

## Troubleshooting

### Database Already Exists

**Problem**: Script won't overwrite existing database

**Solution**:
```bash
# Backup existing database
mv data/p3edge.db data/p3edge_backup.db

# Or delete
rm data/p3edge.db

# Run script
python scripts/populate_db_vegetarian.py
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Ensure you're in the project root
cd /home/user/p3-edge

# Run with python path
PYTHONPATH=/home/user/p3-edge python scripts/populate_db_vegetarian.py
```

### Negative Quantities

**Problem**: Some items have quantity = 0

**Solution**: This is expected! Items can run out between shopping trips. The script simulates realistic depletion.

## Advanced Features

### Seasonal Variations

Future enhancement: Adjust consumption based on season

```python
def get_seasonal_multiplier(date: datetime, item: str) -> float:
    """Adjust consumption by season."""
    month = date.month

    if item in ["Strawberries", "Blueberries"]:
        # More in summer (June-August)
        if 6 <= month <= 8:
            return 1.5

    if item == "Hot Beverages":
        # More in winter
        if month in [12, 1, 2]:
            return 1.3

    return 1.0
```

### Holiday Events

Simulate holiday shopping:

```python
def is_holiday_week(date: datetime) -> bool:
    """Check if date is near major holiday."""
    holidays = [
        datetime(date.year, 12, 25),  # Christmas
        datetime(date.year, 11, 25),  # Thanksgiving (approx)
        datetime(date.year, 7, 4),    # July 4th
    ]

    for holiday in holidays:
        if abs((date - holiday).days) <= 3:
            return True
    return False

# In shopping logic:
if is_holiday_week(shop_date):
    restock_qty *= 2.0  # Double up for holiday meals
```

---

**Last Updated**: November 2024
**Version**: 1.0
**Script Location**: `scripts/populate_db_vegetarian.py`
