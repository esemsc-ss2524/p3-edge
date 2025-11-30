"""
User preference data models.

Defines data structures for user settings and preferences.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ApprovalMode(str, Enum):
    """Order approval mode."""
    ALWAYS = "always"  # Always require approval
    THRESHOLD = "threshold"  # Require approval above threshold
    NEVER = "never"  # Never require approval (auto-approve all)


class UserPreferences(BaseModel):
    """User preferences and configuration."""

    # Budget constraints
    spend_cap_weekly: Optional[float] = Field(None, ge=0.0)
    spend_cap_monthly: Optional[float] = Field(None, ge=0.0)

    # Vendor preferences
    approved_vendors: List[str] = Field(default_factory=lambda: ["amazon", "walmart"])
    preferred_vendor: Optional[str] = None  # Default vendor for orders

    # Approval settings
    approval_mode: ApprovalMode = Field(default=ApprovalMode.THRESHOLD)
    approval_threshold: float = Field(default=50.0, ge=0.0)  # Dollar amount

    # Brand preferences (category -> list of preferred brands)
    brand_preferences: Dict[str, List[str]] = Field(default_factory=dict)

    # Dietary restrictions
    dietary_restrictions: List[str] = Field(default_factory=list)

    # Household info
    household_size: int = Field(default=1, ge=1, le=20)
    household_members: List[str] = Field(default_factory=list)  # Names for personalization

    # Notification preferences
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "low_stock": True,
            "forecast_ready": True,
            "order_placed": True,
            "order_delivered": True,
            "expiring_items": True
        }
    )

    # Shopping preferences
    delivery_preference: str = Field(default="fastest")  # fastest, cheapest, eco-friendly
    preferred_delivery_days: List[str] = Field(default_factory=list)  # Mon, Tue, etc.

    # Privacy settings
    data_retention_days: int = Field(default=365, ge=30, le=3650)
    conversation_auto_purge_days: int = Field(default=30, ge=1, le=365)

    # Advanced settings
    forecast_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    auto_reorder_enabled: bool = Field(default=False)

    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator('approved_vendors')
    @classmethod
    def validate_vendors(cls, v: List[str]) -> List[str]:
        """Validate vendor list."""
        valid_vendors = ["amazon", "walmart"]
        for vendor in v:
            if vendor not in valid_vendors:
                raise ValueError(f"Invalid vendor: {vendor}. Must be one of {valid_vendors}")
        return v

    @field_validator('preferred_vendor')
    @classmethod
    def validate_preferred_vendor(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure preferred vendor is in approved list."""
        if v is not None:
            approved = info.data.get('approved_vendors', [])
            if v not in approved:
                raise ValueError(f"Preferred vendor must be in approved vendors list")
        return v

    def is_vendor_approved(self, vendor: str) -> bool:
        """Check if a vendor is approved."""
        return vendor in self.approved_vendors

    def requires_approval(self, order_total: float) -> bool:
        """
        Check if an order requires approval based on preferences.

        Args:
            order_total: Total cost of the order

        Returns:
            True if approval is required
        """
        if self.approval_mode == ApprovalMode.ALWAYS:
            return True
        elif self.approval_mode == ApprovalMode.NEVER:
            return False
        else:  # THRESHOLD
            return order_total > self.approval_threshold

    def is_within_budget(self, order_total: float, current_weekly_spend: float = 0.0,
                        current_monthly_spend: float = 0.0) -> bool:
        """
        Check if an order is within budget constraints.

        Args:
            order_total: Total cost of the order
            current_weekly_spend: Already spent this week
            current_monthly_spend: Already spent this month

        Returns:
            True if within budget
        """
        if self.spend_cap_weekly is not None:
            if current_weekly_spend + order_total > self.spend_cap_weekly:
                return False

        if self.spend_cap_monthly is not None:
            if current_monthly_spend + order_total > self.spend_cap_monthly:
                return False

        return True

    def get_preferred_brands(self, category: str) -> List[str]:
        """Get preferred brands for a category."""
        return self.brand_preferences.get(category, [])

    def add_brand_preference(self, category: str, brand: str) -> None:
        """Add a brand preference for a category."""
        if category not in self.brand_preferences:
            self.brand_preferences[category] = []
        if brand not in self.brand_preferences[category]:
            self.brand_preferences[category].append(brand)
        self.updated_at = datetime.now()

    def remove_brand_preference(self, category: str, brand: str) -> None:
        """Remove a brand preference."""
        if category in self.brand_preferences:
            if brand in self.brand_preferences[category]:
                self.brand_preferences[category].remove(brand)
                self.updated_at = datetime.now()

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "spend_cap_weekly": 150.0,
                "spend_cap_monthly": 600.0,
                "approved_vendors": ["amazon", "walmart"],
                "approval_mode": "threshold",
                "approval_threshold": 50.0,
                "household_size": 4,
                "dietary_restrictions": ["vegetarian", "gluten-free"],
                "brand_preferences": {
                    "dairy": ["Organic Valley", "Horizon"],
                    "bread": ["Dave's Killer Bread"]
                }
            }
        }


class PreferenceKey(str, Enum):
    """Standard preference keys for storage."""
    USER_PREFERENCES = "user_preferences"
    ONBOARDING_COMPLETE = "onboarding_complete"
    LAST_SYNC_TIME = "last_sync_time"
    DATABASE_VERSION = "database_version"


class Preference(BaseModel):
    """Generic preference storage."""

    key: str = Field(..., max_length=100)
    value: Any  # Can be any JSON-serializable value
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "key": "user_preferences",
                "value": {"household_size": 4, "approval_mode": "threshold"}
            }
        }
