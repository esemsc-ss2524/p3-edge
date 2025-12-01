# Forecasting System - User Guide

This guide explains how P3-Edge's consumption forecasting system works and how to use it effectively.

## Overview

P3-Edge uses state-of-the-art state space models (Linear Gaussian Models with Kalman filtering) to predict when your grocery items will run out. The system has three key features:

1. **Pre-trained Models**: Immediate forecasting from day one using synthetic data
2. **Online Learning**: Continuous adaptation to your actual usage patterns
3. **Automatic Training**: Scheduled training at 2 AM daily to improve accuracy

## Quick Start

### 1. Pre-train Models (One-time Setup)

Before using forecasts, pre-train the models on synthetic temporal data:

```bash
python scripts/pretrain_forecasting_models.py
```

This will:
- Generate 60 days of realistic consumption data for 5 categories
- Train state space models on this synthetic data
- Save trained models to `models/pretrained/`
- Take about 30-60 seconds to complete

Output:
```
======================================================================
  Forecasting Model Pre-Training
======================================================================

[1/3] Generating synthetic temporal data...
  Generated 60 observations for Dairy_Products
  Generated 60 observations for Fresh_Produce
  Generated 60 observations for Protein_Sources
  Generated 60 observations for Grains_Pasta
  Generated 60 observations for Beverages

[2/3] Training models...
  Training complete: MSE: 0.0234, RMSE: 0.1530

[3/3] Testing forecasts...
  Current quantity: 1.85 gallon
  7-day forecast: 0.42 gallon
  14-day forecast: 0.01 gallon
  Predicted runout: 12 days (confidence: 0.87)

Pre-training Complete!
```

### 2. Using Forecasts in the UI

#### Navigate to Forecasts Page

1. Open P3-Edge application
2. Click **"Forecasts"** in left navigation menu
3. You'll see the forecasts page with three buttons:
   - **Refresh**: Reload forecast data from database
   - **Train Models**: Manually trigger model training
   - **Generate All Forecasts**: Generate forecasts for all items

#### Generate Your First Forecasts

1. Click **"Generate All Forecasts"**
2. Confirm the action
3. Wait a few moments for processing
4. View forecasts in the table

The forecast table shows:
- **Item Name**: The grocery item
- **Current Qty**: Current inventory quantity
- **Consumption Rate**: Average consumption per day
- **Predicted Runout**: Date when item will run out
- **Days Until Runout**: Number of days remaining
- **Confidence**: Prediction confidence (0-100%)
- **Order Date**: Recommended date to reorder
- **Actions**: View detailed forecast chart

#### Understanding the Forecasts

**Color Coding:**
- 🔴 **Red**: Running out in 3 days or less (urgent)
- 🟡 **Yellow**: Running out in 4-7 days (plan ahead)
- 🟢 **Green**: More than 7 days remaining

**Confidence Levels:**
- 🟢 **≥80%**: High confidence (green)
- 🟡 **50-79%**: Medium confidence (yellow)
- 🔴 **<50%**: Low confidence (red)

Low confidence typically means:
- Not enough historical data yet
- Irregular consumption patterns
- Model is still learning

### 3. Manual Training

Train models manually when you want to incorporate recent data:

1. Navigate to **Forecasts** page
2. Click **"Train Models"** button
3. Review the training plan:
   ```
   Train forecasting models on historical data?

   This will:
   • Use pre-trained models as starting point when available
   • Train on your actual usage history
   • Improve forecast accuracy over time

   This may take a few moments.
   ```
4. Click **"Yes"** to start training
5. View results:
   ```
   Training Complete!

   • Trained: 12 models
   • Skipped: 3 (recently trained)
   • Failed: 0

   ✓ 8 models used pre-trained weights
   ```

**When to Train Manually:**
- After adding many new items
- After major changes in consumption patterns
- If forecasts seem inaccurate
- After importing historical data

### 4. Automatic Training

Models are automatically trained every night at 2 AM when usage is lowest.

**Configuration:**

To disable automatic training, add to your config:
```json
{
  "forecasting": {
    "auto_training": false
  }
}
```

**Checking Next Training:**

The scheduler logs show:
```
Training scheduler started. Models will train daily at 02:00
```

**What Happens During Training:**
1. System wakes at 2 AM
2. Checks which models need retraining (7-day interval by default)
3. Trains models on accumulated history
4. Saves updated models
5. Logs results to audit log

## How It Works

### Pre-trained Models (Warm Start)

**Problem**: Without historical data, models have nothing to learn from.

**Solution**: Pre-train on synthetic temporal data that simulates realistic consumption patterns.

**Benefits**:
- Forecasts available from day one
- Reasonable predictions without user history
- Models understand typical consumption dynamics
- Adapts to actual patterns over time

**The Pre-training Process**:

1. **Generate Synthetic Data** (60 days):
   - Weekly shopping patterns (Saturdays)
   - Mid-week restocking (Wednesdays for perishables)
   - Daily consumption with variations
   - Weekend effects (30% more consumption)
   - Proper timestamps starting 60 days in the past

2. **Train State Space Models**:
   - One model per category (Dairy, Produce, Protein, Grains, Beverages)
   - 60 training steps on temporal sequences
   - Learn consumption rates and trends
   - Capture seasonal patterns

3. **Save Model Checkpoints**:
   - Model parameters (transition matrices, noise parameters)
   - Final state (for initialization)
   - Training metadata
   - Saved to `models/pretrained/pretrained_{Category}_Products.pt`

**Category Matching**:

When creating a forecast for a new item:
1. Check item's category (e.g., "Dairy")
2. Look for pre-trained model: `pretrained_Dairy_Products.pt`
3. Load pre-trained parameters if available
4. Initialize with current item quantity
5. Adapt to actual consumption as data arrives

### Online Learning

As actual inventory data arrives, models continuously adapt:

**Incremental Updates**:
- Each observation updates the model immediately
- Uses Kalman filter for optimal state estimation
- EWMA (Exponential Weighted Moving Average) for stability
- No need to retrain from scratch

**State Tracking**:
- Current quantity
- Consumption rate (items/day)
- Trend (acceleration/deceleration)
- Seasonal component

**Continuous Improvement**:
- Prediction error tracked
- Model parameters adjusted
- Confidence improves with more data
- Adapts to changing patterns

### Periodic Retraining

Full retraining from scratch every 7 days:

**Why Retrain?**
- Correct accumulated drift
- Incorporate long-term patterns
- Handle major consumption changes
- Improve parameter estimates

**What Happens**:
1. Collect all observations since model creation
2. Create fresh model (or reload pre-trained)
3. Train sequentially on full history
4. Replace old model with retrained version
5. Continue online learning

**Benefits**:
- Better long-term accuracy
- Captures seasonal changes
- Prevents overfitting to recent data
- Maintains stability

## Advanced Features

### Viewing Forecast Charts

1. In the forecasts table, click **"View Chart"** for any item
2. Interactive chart shows:
   - **Blue line**: Predicted quantity trajectory
   - **Blue shaded area**: 95% confidence interval
   - **Green dashed line**: Current quantity
   - **Red dashed line**: Minimum threshold
   - **Red dot**: Predicted runout point

3. Controls:
   - **Forecast Days**: Choose 7, 14, 30, or 60 days
   - **Regenerate Forecast**: Update with latest data
   - **Close**: Return to forecast table

### Low Stock Alerts

The forecast page automatically shows alerts for items running out soon:

```
⚠️ Low Stock Alerts (Next 7 Days)

⚠️ Whole Milk: Running out in 3 days (Confidence: 85%)
⚠️ Fresh Spinach: Running out in 5 days (Confidence: 72%)
⚠️ Ground Beef: Running out in 6 days (Confidence: 91%)
```

### Statistics

The stats bar shows key metrics:

```
Total Forecasts: 35 | Low Stock (Next 7 Days): 3 | High Confidence (≥80%): 28
```

## Troubleshooting

### No Forecasts Available

**Problem**: "No forecasts available" message

**Solutions**:
1. Generate forecasts: Click **"Generate All Forecasts"**
2. Check inventory: Ensure you have items in inventory
3. Train models: Click **"Train Models"** if no pre-trained models exist
4. Run pre-training script if needed

### Low Confidence Forecasts

**Problem**: Confidence below 50%

**Reasons**:
- Not enough historical data (< 10 observations)
- Irregular consumption patterns
- Recent changes in usage
- Model still learning

**Solutions**:
- Wait for more data to accumulate
- Use manual observations to help model learn
- Train models after adding substantial history
- Consider if item usage is truly unpredictable

### Inaccurate Predictions

**Problem**: Forecasts don't match actual runout

**Solutions**:
1. **Train models**: Click "Train Models" to incorporate recent data
2. **Check data quality**: Ensure inventory updates are accurate
3. **Wait for adaptation**: Models need time to learn your patterns
4. **Review consumption rate**: Check if it matches your actual usage
5. **Consider external factors**: Holidays, guests, etc. affect consumption

### Training Fails

**Problem**: "Failed to train models" error

**Common Causes**:
- Insufficient historical data (need at least 5 observations per item)
- Database issues
- Corrupted model files

**Solutions**:
1. Check logs: `logs/p3edge.log`
2. Ensure database is accessible
3. Try deleting model files and retraining
4. Run pre-training script again

### Scheduler Not Running

**Problem**: Automatic training not happening

**Check**:
1. Look for log message: "Training scheduler started"
2. Verify scheduler is enabled in config
3. Check application was running at 2 AM
4. Review audit log for training events

**Enable Scheduler**:
```python
# In config or code
enable_scheduler = True
```

## Performance Tips

### Initial Setup

1. **Pre-train first**: Always run pre-training script before first use
2. **Populate history**: Use `populate_db_vegetarian.py` for sample data
3. **Train after import**: After importing data, train models once

### Ongoing Usage

1. **Keep app running overnight**: For scheduled training at 2 AM
2. **Train after bulk updates**: If you add many items or history
3. **Check forecasts weekly**: Review accuracy and adjust as needed
4. **Update inventory regularly**: More frequent updates = better forecasts

### Resource Usage

- **Pre-training**: ~1 minute, uses CPU and memory temporarily
- **Manual training**: ~10-30 seconds depending on data volume
- **Automatic training**: ~10-30 seconds at 2 AM
- **Forecast generation**: ~1-2 seconds for 30+ items
- **Model storage**: ~1-5 MB per model

## Technical Details

### Model Architecture

**State Space Model**:
```
State: [quantity, consumption_rate, trend, seasonal]
Features: [day_of_week, weekend, is_restocking_day, ...]
```

**Kalman Filter**:
- Prediction step: Project state forward
- Update step: Correct with observation
- Optimal for linear Gaussian models

**Learning**:
- Gradient descent on transition matrix
- Adaptive noise covariance
- EWMA for stability

### Files and Directories

```
models/
  pretrained/              # Pre-trained models
    pretrained_Dairy_Products.pt
    pretrained_Fresh_Produce.pt
    pretrained_Protein_Sources.pt
    pretrained_Grains_Pasta.pt
    pretrained_Beverages.pt

~/.p3edge/
  models/                  # User-specific trained models
    {item_id}.pt          # Model checkpoint
    {item_id}_meta.json   # Training metadata
```

### Configuration

```json
{
  "forecasting": {
    "auto_training": true,
    "training_hour": 2,
    "training_minute": 0,
    "retrain_interval_days": 7,
    "ewma_alpha": 0.3,
    "default_confidence": 0.95
  }
}
```

## Next Steps

1. **Pre-train models**: Run the pre-training script
2. **Populate database**: Add inventory items and history
3. **Generate forecasts**: Use UI to create initial forecasts
4. **Review predictions**: Check accuracy and confidence
5. **Train manually**: After a week, train on actual data
6. **Enable scheduler**: Let automatic training maintain accuracy

For more details, see:
- **Technical Plan**: `plan/TECHNICAL_PLAN.md`
- **Pre-training Script**: `scripts/pretrain_forecasting_models.py`
- **State Space Model**: `src/forecasting/state_space_model.py`
- **Online Trainer**: `src/forecasting/online_trainer.py`

---

**Version**: 1.0
**Last Updated**: December 2024
