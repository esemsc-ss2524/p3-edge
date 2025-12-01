# Smart Refrigerator Integration Guide

## Overview

P3-Edge now supports integration with Samsung Family Hub smart refrigerators through the SmartThings API. This allows automatic inventory tracking using the refrigerator's AI Vision Inside camera and real-time synchronization with your grocery management system.

## Features

### 1. **Real-Time Inventory Tracking**
- Automatic detection of items using AI Vision Inside camera
- Real-time synchronization between smart fridge and database
- Support for multiple item categories (Dairy, Produce, Protein, etc.)

### 2. **Connection Management**
- Easy connect/disconnect from UI
- Health monitoring and connection status display
- Automatic reconnection on connection loss

### 3. **Automatic Synchronization**
- Configurable polling intervals (5-300 seconds)
- Manual sync option
- Event-driven updates for item changes

### 4. **Comprehensive Logging**
- Activity log for all sync operations
- Audit trail integration
- Debug logging for troubleshooting

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    P3-Edge Application                   │
│                                                           │
│  ┌────────────────┐         ┌──────────────────┐        │
│  │  Smart Fridge  │◄───────►│  Inventory       │        │
│  │  Service       │  Sync   │  Service         │        │
│  └────────────────┘         └──────────────────┘        │
│         │                            │                   │
│         │                            ▼                   │
│         │                   ┌──────────────────┐        │
│         │                   │  Database        │        │
│         │                   │  (SQLite)        │        │
│         │                   └──────────────────┘        │
└─────────┼─────────────────────────────────────────────┘
          │ REST API
          │ (HTTP)
          ▼
┌──────────────────────────────────────────────────────────┐
│     Samsung Family Hub / Simulator (SmartThings API)     │
│                                                           │
│  • AI Vision Inside (Inventory Detection)                │
│  • Temperature Sensors                                    │
│  • Door Contact Sensor                                    │
│  • Ice Maker Status                                       │
└──────────────────────────────────────────────────────────┘
```

## Samsung SmartThings API

### Capabilities Supported

| Capability | Description | Used For |
|------------|-------------|----------|
| `custom.aiVisionInside` | AI-powered item detection | Inventory tracking |
| `temperatureMeasurement` | Fridge temperature | Monitoring |
| `custom.freezerTemperature` | Freezer temperature | Monitoring |
| `contactSensor` | Door open/closed | Event detection |
| `custom.fridgeMode` | Operating mode | Status display |
| `custom.iceMaker` | Ice maker status | Status display |
| `powerConsumptionReport` | Energy usage | Monitoring |

### API Endpoints

The simulator (and real Samsung fridges via SmartThings) expose these endpoints:

```
GET  /api/devices/{device_id}              # Device information
GET  /api/devices/{device_id}/status       # Current status
POST /api/devices/{device_id}/commands     # Execute commands
GET  /api/inventory                        # Get all items
GET  /api/inventory/{item_id}              # Get specific item
PUT  /api/inventory/{item_id}              # Update item
POST /api/inventory                        # Add new item
DELETE /api/inventory/{item_id}            # Remove item
GET  /api/health                           # Health check
```

## Setup Instructions

### 1. Running the Simulator (for Testing)

Start the Samsung Family Hub simulator:

```bash
cd /home/user/p3-edge
python src/ingestion/samsung_fridge_simulator.py
```

The simulator will start on `http://localhost:5001` with sample vegetarian inventory items.

### 2. Connecting from the UI

1. Launch the P3-Edge application:
   ```bash
   python src/main.py
   ```

2. Navigate to **Settings → Smart Refrigerator**

3. Configure connection:
   - **Fridge URL**: `http://localhost:5001` (for simulator)
   - **Poll Interval**: 30 seconds (recommended)

4. Click **Connect**

5. Click **Start Auto-Sync** to enable automatic polling

### 3. Connecting to a Real Samsung Fridge

For production use with a real Samsung Family Hub:

1. Set up Samsung SmartThings integration:
   - Install SmartThings app on your phone
   - Add your Family Hub refrigerator to SmartThings
   - Enable SmartThings API access

2. Get your Personal Access Token (PAT):
   - Visit: https://account.smartthings.com/tokens
   - Create a new token with `r:devices:*` scope

3. Find your device ID:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.smartthings.com/v1/devices
   ```

4. Use SmartThings API URL in P3-Edge:
   - URL: `https://api.smartthings.com/v1`
   - Configure authentication in settings

## Using the Test Script

Run the comprehensive integration test:

```bash
python scripts/test_smart_fridge_integration.py
```

This script demonstrates:
- Connecting to the simulator
- Initial inventory sync
- Real-time updates
- Item addition/removal
- Database verification

## Data Flow

### Initial Sync

```
1. User clicks "Connect" in UI
2. SmartFridgeService establishes connection
3. GET /api/inventory → fetch all items
4. For each item:
   - Match with existing DB items by name
   - Update quantity if exists
   - Create new item if doesn't exist
5. Record sync timestamp
6. Display results in UI
```

### Real-Time Updates (Polling Mode)

```
1. Timer triggers every N seconds (configurable)
2. GET /api/inventory
3. Compare with last sync
4. Apply changes:
   - Updated quantities → update_quantity()
   - New items → create_item()
   - Removed items → (keep in DB, set to 0)
5. Trigger UI callbacks
6. Update last_sync timestamp
```

### Item Change Detection

```python
# Simplified algorithm
current_items = fridge_api.get_inventory()
db_items = inventory_service.get_all_items()

for fridge_item in current_items:
    db_item = find_by_name(fridge_item.name)

    if db_item:
        if abs(db_item.quantity - fridge_item.quantity) > 0.01:
            # Quantity changed
            inventory_service.update_quantity(
                db_item.id,
                fridge_item.quantity,
                source="smart_fridge"
            )
    else:
        # New item detected
        inventory_service.create_item(fridge_item)
```

## Configuration

### Environment Variables

```bash
# Optional: Override default fridge URL
export P3_FRIDGE_URL="http://localhost:5001"

# Optional: Set poll interval (seconds)
export P3_FRIDGE_POLL_INTERVAL=30
```

### Application Config

Edit `config/app_config.json`:

```json
{
  "data_sources": {
    "smart_fridge_enabled": true,
    "smart_fridge_api_url": "http://localhost:5001",
    "smart_fridge_poll_interval": 30
  }
}
```

## Troubleshooting

### Connection Issues

**Problem**: "Could not connect to smart fridge"

**Solutions**:
1. Verify simulator is running: `curl http://localhost:5001/api/health`
2. Check firewall settings
3. Ensure port 5001 is not in use by another application

### Sync Failures

**Problem**: "Sync failed" error

**Solutions**:
1. Check logs: `tail -f logs/p3edge.log`
2. Verify fridge is responding: `curl http://localhost:5001/api/inventory`
3. Restart the simulator
4. Disconnect and reconnect from UI

### Item Not Updating

**Problem**: Item quantity doesn't update in database

**Solutions**:
1. Check item name matches exactly (case-sensitive)
2. Verify quantity difference is > 0.01
3. Enable debug logging to see sync details
4. Manually trigger sync with "Sync Now" button

### Duplicate Items

**Problem**: Same item appears multiple times

**Solutions**:
1. Ensure consistent naming (e.g., "Milk" vs "Whole Milk")
2. Check category matching logic
3. Use item matching service to consolidate duplicates

## API Reference

### SmartFridgeService

```python
from src.services.smart_fridge_service import SmartFridgeService

# Initialize
service = SmartFridgeService(
    db_manager=db_manager,
    fridge_url="http://localhost:5001",
    poll_interval_seconds=30
)

# Connect
success = service.connect()

# Manual sync
stats = service.sync_inventory()
# Returns: {"added": 5, "updated": 3, "unchanged": 7}

# Start automatic polling
service.start_polling()

# Stop polling
service.stop_polling()

# Disconnect
service.disconnect()

# Check status
is_connected = service.is_connected()
info = service.get_connection_info()
```

### Event Callbacks

```python
# Set callbacks
def on_connection_change(connected: bool):
    print(f"Connection status: {connected}")

def on_inventory_update(item_id: str, item_data: dict):
    print(f"Updated: {item_data['name']}")

service.on_connection_change = on_connection_change
service.on_inventory_update = on_inventory_update
```

## Performance Considerations

### Polling Intervals

| Interval | Use Case | Pros | Cons |
|----------|----------|------|------|
| 5-10s | Real-time updates, testing | Very responsive | High API usage |
| 30s | Normal usage (recommended) | Balanced | Slight delay |
| 60-120s | Low-frequency updates | Low overhead | Noticeable lag |

### Database Impact

- Each sync performs N queries (N = number of items)
- Use batch operations for large inventories (>100 items)
- Enable indexing on `name` column for faster lookups

### Network Usage

- Each poll: ~5-10 KB (for 20 items)
- Hourly usage (30s interval): ~600 KB
- Recommended: Use on stable Wi-Fi connection

## Future Enhancements

### Planned Features

1. **WebSocket Support**: Replace polling with real-time push notifications
2. **Image Recognition**: Store item images from AI Vision Inside
3. **Expiry Tracking**: Sync expiration dates from product barcodes
4. **Temperature Alerts**: Notify when fridge temperature is too high
5. **Door Alerts**: Alert if door left open >5 minutes
6. **Smart Suggestions**: Recommend items based on fridge contents

### Integration with Other Components

- **Forecasting**: Use smart fridge data to improve consumption predictions
- **Shopping Lists**: Auto-generate based on fridge inventory
- **Recipes**: Suggest recipes based on available ingredients

## Sources

For more information about Samsung SmartThings API:

- [SmartThings API Documentation](https://developer.smartthings.com/docs/api/public)
- [Samsung Family Hub Developer Portal](https://developer.samsung.com/family-hub)
- [SmartThings Community Forums](https://community.smartthings.com/)
- [Samsung Family Hub 2024 Update](https://news.samsung.com/us/samsung-most-intelligent-fridge-getting-smarter-family-hub-2024-update/)

---

**Last Updated**: November 2024
**Version**: 1.0
**Maintainer**: P3-Edge Development Team
