"""
Audit log data models.

Defines data structures for system action logging and transparency.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of actions that can be logged."""
    # Inventory actions
    INVENTORY_CREATED = "inventory_created"
    INVENTORY_UPDATED = "inventory_updated"
    INVENTORY_DELETED = "inventory_deleted"
    INVENTORY_MANUAL_ADJUSTMENT = "inventory_manual_adjustment"

    # Forecast actions
    FORECAST_GENERATED = "forecast_generated"
    FORECAST_UPDATED = "forecast_updated"

    # Order actions
    ORDER_CREATED = "order_created"
    ORDER_APPROVED = "order_approved"
    ORDER_PLACED = "order_placed"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"

    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_PREFERENCE_UPDATE = "user_preference_update"

    # System actions
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    DATABASE_BACKUP = "database_backup"
    MODEL_TRAINED = "model_trained"
    MODEL_UPDATED = "model_updated"

    # Data ingestion
    DATA_SMART_FRIDGE = "data_smart_fridge"
    DATA_RECEIPT_SCANNED = "data_receipt_scanned"
    DATA_EMAIL_PARSED = "data_email_parsed"

    # LLM actions
    LLM_CONVERSATION = "llm_conversation"
    LLM_SUGGESTION = "llm_suggestion"
    LLM_FEATURE_ENGINEERING = "llm_feature_engineering"


class Actor(str, Enum):
    """Who performed the action."""
    USER = "user"
    SYSTEM = "system"
    LLM = "llm"


class Outcome(str, Enum):
    """Result of the action."""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


class AuditLog(BaseModel):
    """Represents a single audit log entry."""

    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    action_type: ActionType
    actor: Actor
    details: Dict[str, Any] = Field(default_factory=dict)
    outcome: Outcome = Field(default=Outcome.SUCCESS)
    item_id: Optional[str] = None  # Reference to inventory item
    order_id: Optional[str] = None  # Reference to order
    error_message: Optional[str] = None

    def set_success(self, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark action as successful."""
        self.outcome = Outcome.SUCCESS
        if details:
            self.details.update(details)

    def set_failure(self, error_message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Mark action as failed."""
        self.outcome = Outcome.FAILURE
        self.error_message = error_message
        if details:
            self.details.update(details)

    def to_readable_string(self) -> str:
        """Convert log entry to human-readable string."""
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        actor_str = self.actor.value.upper()
        action_str = self.action_type.value.replace("_", " ").title()
        outcome_str = self.outcome.value.upper()

        base = f"[{timestamp_str}] {actor_str}: {action_str} - {outcome_str}"

        if self.error_message:
            base += f" - Error: {self.error_message}"

        return base

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "action_type": "order_placed",
                "actor": "system",
                "details": {
                    "vendor": "amazon",
                    "total_cost": 45.99,
                    "item_count": 5
                },
                "outcome": "success",
                "order_id": "order-123"
            }
        }


def create_audit_log(
    action_type: ActionType,
    actor: Actor,
    details: Optional[Dict[str, Any]] = None,
    item_id: Optional[str] = None,
    order_id: Optional[str] = None
) -> AuditLog:
    """
    Factory function to create audit log entries.

    Args:
        action_type: Type of action
        actor: Who performed the action
        details: Additional details
        item_id: Related inventory item ID
        order_id: Related order ID

    Returns:
        AuditLog instance
    """
    return AuditLog(
        action_type=action_type,
        actor=actor,
        details=details or {},
        item_id=item_id,
        order_id=order_id
    )
