"""
Vendor integration models for e-commerce.

Defines product, pricing, and order structures for vendor integrations.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class VendorProduct(BaseModel):
    """Product from a vendor."""

    product_id: str = Field(..., description="Vendor-specific product ID")
    name: str = Field(..., description="Product name")
    brand: Optional[str] = Field(None, description="Product brand")
    category: Optional[str] = Field(None, description="Product category")
    price: float = Field(..., ge=0, description="Current price")
    currency: str = Field(default="USD", description="Currency code")
    unit: Optional[str] = Field(None, description="Unit (oz, lb, count, etc.)")
    quantity_available: Optional[int] = Field(None, description="Available quantity")
    image_url: Optional[str] = Field(None, description="Product image URL")
    url: Optional[str] = Field(None, description="Product page URL")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Customer rating (0-5)")
    reviews_count: Optional[int] = Field(None, ge=0, description="Number of reviews")
    vendor: str = Field(..., description="Vendor name (amazon, walmart, etc.)")
    in_stock: bool = Field(default=True, description="Whether item is in stock")
    prime_eligible: bool = Field(default=False, description="Amazon Prime eligible")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "product_id": "B07X6C9RMF",
                "name": "Organic Whole Milk, 1 Gallon",
                "brand": "Organic Valley",
                "category": "Dairy",
                "price": 5.99,
                "currency": "USD",
                "unit": "gallon",
                "vendor": "amazon",
                "in_stock": True,
                "prime_eligible": True
            }
        }


class SearchResult(BaseModel):
    """Search results from vendor."""

    query: str = Field(..., description="Search query")
    products: List[VendorProduct] = Field(default_factory=list, description="Found products")
    total_results: int = Field(default=0, ge=0, description="Total number of results")
    vendor: str = Field(..., description="Vendor name")


class CartItem(BaseModel):
    """Item in shopping cart."""

    product_id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    price: float = Field(..., ge=0, description="Price per unit")
    quantity: float = Field(..., gt=0, description="Quantity to order")
    unit: Optional[str] = Field(None, description="Unit")
    vendor: str = Field(..., description="Vendor name")
    image_url: Optional[str] = Field(None, description="Product image URL")

    @property
    def subtotal(self) -> float:
        """Calculate subtotal for this item."""
        return self.price * self.quantity


class ShoppingCart(BaseModel):
    """Shopping cart."""

    cart_id: str = Field(..., description="Cart ID")
    vendor: str = Field(..., description="Vendor name")
    items: List[CartItem] = Field(default_factory=list, description="Cart items")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")

    @property
    def total(self) -> float:
        """Calculate cart total."""
        return sum(item.subtotal for item in self.items)

    @property
    def item_count(self) -> int:
        """Get number of items in cart."""
        return len(self.items)

    def add_item(self, item: CartItem) -> None:
        """Add item to cart."""
        # Check if item already exists
        for existing_item in self.items:
            if existing_item.product_id == item.product_id:
                # Update quantity
                existing_item.quantity += item.quantity
                self.updated_at = datetime.now()
                return

        # Add new item
        self.items.append(item)
        self.updated_at = datetime.now()

    def remove_item(self, product_id: str) -> bool:
        """Remove item from cart."""
        for i, item in enumerate(self.items):
            if item.product_id == product_id:
                self.items.pop(i)
                self.updated_at = datetime.now()
                return True
        return False

    def update_quantity(self, product_id: str, quantity: float) -> bool:
        """Update item quantity."""
        for item in self.items:
            if item.product_id == product_id:
                item.quantity = quantity
                self.updated_at = datetime.now()
                return True
        return False

    def clear(self) -> None:
        """Clear all items from cart."""
        self.items = []
        self.updated_at = datetime.now()


class OrderStatus:
    """Order status constants."""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PLACED = "placed"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"
