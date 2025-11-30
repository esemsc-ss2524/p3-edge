"""
Order data models.

Defines data structures for shopping orders and cart management.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PLACED = "placed"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Vendor(str, Enum):
    """Supported vendors."""
    AMAZON = "amazon"
    WALMART = "walmart"


class OrderItem(BaseModel):
    """Represents a single item in an order."""

    item_id: str  # Reference to inventory item
    product_id: Optional[str] = None  # Vendor's product ID
    name: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0.0)
    price: float = Field(..., ge=0.0)
    unit: Optional[str] = None
    brand: Optional[str] = None

    def total_price(self) -> float:
        """Calculate total price for this item."""
        return self.quantity * self.price

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "item_id": "abc-123",
                "product_id": "B08XYZ123",
                "name": "Organic Milk",
                "quantity": 2.0,
                "price": 5.99,
                "unit": "gallon",
                "brand": "Organic Valley"
            }
        }


class Order(BaseModel):
    """Represents a shopping order."""

    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vendor: Vendor
    status: OrderStatus = Field(default=OrderStatus.PENDING_APPROVAL)
    items: List[OrderItem] = Field(default_factory=list)
    total_cost: float = Field(default=0.0, ge=0.0)
    created_at: datetime = Field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    placed_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    user_notes: Optional[str] = Field(None, max_length=1000)
    auto_generated: bool = Field(default=True)
    vendor_order_id: Optional[str] = None  # External order ID

    @field_validator('items')
    @classmethod
    def validate_items_not_empty(cls, v: List[OrderItem]) -> List[OrderItem]:
        """Ensure order has at least one item."""
        if len(v) == 0:
            raise ValueError('Order must have at least one item')
        return v

    def calculate_total(self) -> float:
        """Calculate total cost of all items."""
        return sum(item.total_price() for item in self.items)

    def add_item(self, item: OrderItem) -> None:
        """Add an item to the order."""
        self.items.append(item)
        self.total_cost = self.calculate_total()

    def remove_item(self, item_id: str) -> bool:
        """
        Remove an item from the order.

        Args:
            item_id: ID of the item to remove

        Returns:
            True if item was removed, False if not found
        """
        original_length = len(self.items)
        self.items = [item for item in self.items if item.item_id != item_id]
        if len(self.items) < original_length:
            self.total_cost = self.calculate_total()
            return True
        return False

    def approve(self) -> None:
        """Mark order as approved."""
        if self.status != OrderStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot approve order with status {self.status}")
        self.status = OrderStatus.APPROVED
        self.approved_at = datetime.now()

    def place(self) -> None:
        """Mark order as placed."""
        if self.status != OrderStatus.APPROVED:
            raise ValueError(f"Cannot place order with status {self.status}")
        self.status = OrderStatus.PLACED
        self.placed_at = datetime.now()

    def deliver(self) -> None:
        """Mark order as delivered."""
        if self.status != OrderStatus.PLACED:
            raise ValueError(f"Cannot deliver order with status {self.status}")
        self.status = OrderStatus.DELIVERED
        self.delivered_at = datetime.now()

    def cancel(self) -> None:
        """Cancel the order."""
        if self.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel order with status {self.status}")
        self.status = OrderStatus.CANCELLED

    def get_item_count(self) -> int:
        """Get total number of items in order."""
        return len(self.items)

    def get_total_quantity(self) -> float:
        """Get total quantity across all items."""
        return sum(item.quantity for item in self.items)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "vendor": "amazon",
                "status": "pending_approval",
                "items": [
                    {
                        "item_id": "abc-123",
                        "product_id": "B08XYZ123",
                        "name": "Organic Milk",
                        "quantity": 2.0,
                        "price": 5.99,
                        "unit": "gallon"
                    }
                ],
                "total_cost": 11.98,
                "auto_generated": True
            }
        }


class ShoppingCart(BaseModel):
    """Represents a temporary shopping cart before order creation."""

    cart_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vendor: Vendor
    items: List[OrderItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_item(self, item: OrderItem) -> None:
        """Add item to cart."""
        self.items.append(item)
        self.updated_at = datetime.now()

    def remove_item(self, item_id: str) -> bool:
        """Remove item from cart."""
        original_length = len(self.items)
        self.items = [item for item in self.items if item.item_id != item_id]
        if len(self.items) < original_length:
            self.updated_at = datetime.now()
            return True
        return False

    def clear(self) -> None:
        """Clear all items from cart."""
        self.items.clear()
        self.updated_at = datetime.now()

    def to_order(self) -> Order:
        """Convert cart to an order."""
        order = Order(
            vendor=self.vendor,
            items=self.items.copy(),
            status=OrderStatus.PENDING_APPROVAL
        )
        order.total_cost = order.calculate_total()
        return order

    def get_total(self) -> float:
        """Calculate cart total."""
        return sum(item.total_price() for item in self.items)

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "vendor": "walmart",
                "items": []
            }
        }
