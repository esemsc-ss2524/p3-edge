"""
Vendor integrations for e-commerce.

Provides interfaces for Amazon, Walmart, and other grocery vendors.
"""

from .base import VendorClient
from .models import (
    VendorProduct,
    SearchResult,
    CartItem,
    ShoppingCart,
    OrderStatus
)
from .amazon_client import AmazonClient

__all__ = [
    "VendorClient",
    "VendorProduct",
    "SearchResult",
    "CartItem",
    "ShoppingCart",
    "OrderStatus",
    "AmazonClient"
]
