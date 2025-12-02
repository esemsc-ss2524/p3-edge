"""
Base vendor interface for e-commerce integrations.

Defines the abstract interface that all vendor clients must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from .models import VendorProduct, SearchResult, ShoppingCart


class VendorClient(ABC):
    """Abstract base class for vendor integrations."""

    def __init__(self, vendor_name: str):
        """
        Initialize vendor client.

        Args:
            vendor_name: Name of the vendor (e.g., "amazon", "walmart")
        """
        self.vendor_name = vendor_name

    @abstractmethod
    def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 10,
        **kwargs
    ) -> SearchResult:
        """
        Search for products.

        Args:
            query: Search query
            category: Optional category filter
            max_results: Maximum number of results to return
            **kwargs: Additional vendor-specific parameters

        Returns:
            SearchResult with found products
        """
        pass

    @abstractmethod
    def get_product_details(self, product_id: str) -> Optional[VendorProduct]:
        """
        Get detailed information about a product.

        Args:
            product_id: Vendor-specific product ID

        Returns:
            VendorProduct or None if not found
        """
        pass

    @abstractmethod
    def get_product_price(self, product_id: str) -> Optional[float]:
        """
        Get current price for a product.

        Args:
            product_id: Vendor-specific product ID

        Returns:
            Current price or None if not found
        """
        pass

    @abstractmethod
    def check_availability(self, product_id: str) -> bool:
        """
        Check if product is available for purchase.

        Args:
            product_id: Vendor-specific product ID

        Returns:
            True if available, False otherwise
        """
        pass

    @abstractmethod
    def create_cart(self) -> ShoppingCart:
        """
        Create a new shopping cart.

        Returns:
            New ShoppingCart instance
        """
        pass

    @abstractmethod
    def place_order(
        self,
        cart: ShoppingCart,
        shipping_address: Optional[Dict[str, str]] = None,
        payment_method: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Place an order with the vendor.

        Args:
            cart: Shopping cart to order
            shipping_address: Shipping address details
            payment_method: Payment method details
            **kwargs: Additional vendor-specific parameters

        Returns:
            Dictionary with order details including order_id, status, etc.
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get status of an order.

        Args:
            order_id: Vendor-specific order ID

        Returns:
            Dictionary with order status and details
        """
        pass

    def is_authenticated(self) -> bool:
        """
        Check if client is authenticated with vendor.

        Returns:
            True if authenticated, False otherwise
        """
        # Default implementation - can be overridden
        return True
