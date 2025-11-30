"""
Inventory data models.

Defines data structures for household inventory items and history tracking.
"""

import uuid
from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class InventoryItem(BaseModel):
    """Represents a single item in household inventory."""

    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = Field(None, max_length=100)
    brand: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)  # oz, lb, count, etc.
    quantity_current: float = Field(default=0.0, ge=0.0)
    quantity_min: float = Field(default=1.0, ge=0.0)
    quantity_max: float = Field(default=10.0, ge=0.0)
    last_updated: datetime = Field(default_factory=datetime.now)
    location: Optional[str] = Field(None, max_length=50)  # fridge, pantry, freezer
    perishable: bool = Field(default=False)
    expiry_date: Optional[date] = None
    consumption_rate: Optional[float] = Field(None, ge=0.0)  # units per day
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('quantity_max')
    @classmethod
    def validate_max_greater_than_min(cls, v: float, info) -> float:
        """Ensure max quantity is greater than or equal to min quantity."""
        if 'quantity_min' in info.data and v < info.data['quantity_min']:
            raise ValueError('quantity_max must be >= quantity_min')
        return v

    @field_validator('expiry_date')
    @classmethod
    def validate_expiry_date(cls, v: Optional[date], info) -> Optional[date]:
        """Ensure expiry date is in the future for perishables."""
        if v is not None and 'perishable' in info.data:
            if info.data['perishable'] and v < date.today():
                raise ValueError('Expiry date must be in the future for perishable items')
        return v

    def is_low_stock(self) -> bool:
        """Check if item is below minimum threshold."""
        return self.quantity_current < self.quantity_min

    def is_expired(self) -> bool:
        """Check if item is past expiry date."""
        return self.expiry_date is not None and self.expiry_date < date.today()

    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until expiry."""
        if self.expiry_date is None:
            return None
        delta = self.expiry_date - date.today()
        return delta.days

    def estimated_days_remaining(self) -> Optional[float]:
        """Estimate days until item runs out based on consumption rate."""
        if self.consumption_rate is None or self.consumption_rate == 0:
            return None
        return self.quantity_current / self.consumption_rate

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "name": "Milk",
                "category": "Dairy",
                "brand": "Organic Valley",
                "unit": "gallon",
                "quantity_current": 1.5,
                "quantity_min": 0.5,
                "quantity_max": 2.0,
                "location": "fridge",
                "perishable": True,
                "consumption_rate": 0.25
            }
        }


class InventoryHistory(BaseModel):
    """Represents a snapshot of inventory quantity at a point in time."""

    history_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str
    quantity: float = Field(..., ge=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = Field(..., max_length=50)  # smart_fridge, receipt, manual, system
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate data source."""
        valid_sources = ['smart_fridge', 'receipt', 'manual', 'system', 'email']
        if v not in valid_sources:
            raise ValueError(f'Source must be one of {valid_sources}')
        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "item_id": "abc-123",
                "quantity": 2.0,
                "source": "smart_fridge",
                "notes": "Automatic update from smart refrigerator"
            }
        }


class Forecast(BaseModel):
    """Represents a forecast for when an item will run out."""

    forecast_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_id: str
    predicted_runout_date: Optional[date] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommended_order_date: Optional[date] = None
    recommended_quantity: float = Field(..., ge=0.0)
    model_version: str = Field(..., max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)
    features_used: List[str] = Field(default_factory=list)
    actual_runout_date: Optional[date] = None  # Filled in after observation

    def is_accurate(self, tolerance_days: int = 3) -> Optional[bool]:
        """
        Check if forecast was accurate within tolerance.

        Args:
            tolerance_days: Acceptable error margin in days

        Returns:
            True if accurate, False if not, None if not yet observed
        """
        if self.actual_runout_date is None or self.predicted_runout_date is None:
            return None

        delta = abs((self.actual_runout_date - self.predicted_runout_date).days)
        return delta <= tolerance_days

    def forecast_error_days(self) -> Optional[int]:
        """
        Calculate forecast error in days.

        Returns:
            Positive if overestimated, negative if underestimated, None if not observed
        """
        if self.actual_runout_date is None or self.predicted_runout_date is None:
            return None

        delta = (self.predicted_runout_date - self.actual_runout_date).days
        return delta

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "item_id": "abc-123",
                "predicted_runout_date": "2025-12-15",
                "confidence": 0.85,
                "recommended_order_date": "2025-12-12",
                "recommended_quantity": 2.0,
                "model_version": "v1.0",
                "features_used": ["consumption_rate", "days_since_last_purchase", "household_size"]
            }
        }
