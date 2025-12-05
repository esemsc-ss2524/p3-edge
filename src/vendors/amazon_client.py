"""
Amazon vendor client for product search and ordering.

NOTE: This is a simulated implementation for MVP demonstration.
In production, this would use Amazon SP-API with OAuth 2.0 credentials.

For real implementation, you would need:
1. Amazon Seller Central account
2. SP-API credentials (LWA credentials)
3. OAuth 2.0 token management
4. Region-specific endpoints
"""

import uuid
import csv
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from ..utils import get_logger
from .base import VendorClient
from .models import VendorProduct, SearchResult, ShoppingCart, CartItem, OrderStatus


def load_products_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    """
    Load products from a CSV file.

    Args:
        csv_path: Path to the CSV file

    Returns:
        List of product dictionaries
    """
    products = []

    if not os.path.exists(csv_path):
        logger = get_logger("amazon_client")
        logger.warning(f"CSV file not found: {csv_path}")
        return products

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert data types
            product = {
                "product_id": row["product_id"],
                "name": row["name"],
                "brand": row["brand"],
                "category": row["category"],
                "price": float(row["price"]),
                "unit": row["unit"],
                "rating": float(row["rating"]),
                "reviews_count": int(row["reviews_count"]),
                "prime_eligible": row["prime_eligible"].lower() == "true",
                "in_stock": row["in_stock"].lower() == "true"
            }
            products.append(product)

    return products


# Load products from CSV file
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'amazon_grocery_items.csv')
SIMULATED_PRODUCTS = load_products_from_csv(CSV_PATH)


class AmazonClient(VendorClient):
    """Amazon vendor client (simulated for MVP)."""

    def __init__(self, api_key: Optional[str] = None, region: str = "us-east-1"):
        """
        Initialize Amazon client.

        Args:
            api_key: API key (not used in simulation)
            region: AWS region (not used in simulation)
        """
        super().__init__("amazon")
        self.logger = get_logger("amazon_client")
        self.api_key = api_key
        self.region = region
        self.logger.info(f"Initialized Amazon client (simulated mode)")

    def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 10,
        **kwargs
    ) -> SearchResult:
        """
        Search for products on Amazon.

        Args:
            query: Search query
            category: Optional category filter
            max_results: Maximum number of results
            **kwargs: Additional parameters

        Returns:
            SearchResult with found products
        """
        self.logger.info(f"Searching Amazon for: '{query}'")

        # Normalize query
        query_lower = query.lower()
        query_terms = query_lower.split()

        # Find matching products
        found_products = []
        scored_matches = []

        # Search through all products
        for product_data in SIMULATED_PRODUCTS:
            # Apply category filter if provided
            if category and product_data["category"].lower() != category.lower():
                continue

            # Calculate match score
            score = 0
            searchable_text = f"{product_data['name']} {product_data['brand']} {product_data['category']}".lower()

            # Exact phrase match in name (highest priority)
            if query_lower in product_data["name"].lower():
                score += 100

            # Exact phrase match in brand
            if query_lower in product_data["brand"].lower():
                score += 50

            # Exact phrase match in category
            if query_lower in product_data["category"].lower():
                score += 30

            # Individual term matches
            for term in query_terms:
                if len(term) >= 2:  # Skip very short terms
                    if term in product_data["name"].lower():
                        score += 20
                    if term in product_data["brand"].lower():
                        score += 10
                    if term in product_data["category"].lower():
                        score += 5

            # If we have any match, add to results
            if score > 0:
                scored_matches.append((score, product_data))

        # Sort by score (descending) and limit results
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        found_products = [
            VendorProduct(vendor=self.vendor_name, **product_data)
            for score, product_data in scored_matches[:int(max_results)]
        ]

        self.logger.info(f"Found {len(found_products)} products")

        return SearchResult(
            query=query,
            products=found_products,
            total_results=len(found_products),
            vendor=self.vendor_name
        )

    def get_product_details(self, product_id: str) -> Optional[VendorProduct]:
        """
        Get product details by ID.

        Args:
            product_id: Product ID

        Returns:
            VendorProduct or None
        """
        self.logger.info(f"Getting product details for: {product_id}")

        # Search all products
        for product_data in SIMULATED_PRODUCTS:
            if product_data["product_id"] == product_id:
                return VendorProduct(
                    vendor=self.vendor_name,
                    **product_data
                )

        self.logger.warning(f"Product not found: {product_id}")
        return None

    def get_product_price(self, product_id: str) -> Optional[float]:
        """
        Get current price for a product.

        Args:
            product_id: Product ID

        Returns:
            Price or None
        """
        product = self.get_product_details(product_id)
        return product.price if product else None

    def check_availability(self, product_id: str) -> bool:
        """
        Check if product is available.

        Args:
            product_id: Product ID

        Returns:
            True if available
        """
        product = self.get_product_details(product_id)
        return product.in_stock if product else False

    def create_cart(self) -> ShoppingCart:
        """
        Create a new shopping cart.

        Returns:
            New ShoppingCart
        """
        cart_id = f"amazon-cart-{uuid.uuid4().hex[:8]}"
        self.logger.info(f"Created cart: {cart_id}")

        return ShoppingCart(
            cart_id=cart_id,
            vendor=self.vendor_name
        )

    def place_order(
        self,
        cart: ShoppingCart,
        shipping_address: Optional[Dict[str, str]] = None,
        payment_method: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Place an order (simulated).

        Args:
            cart: Shopping cart
            shipping_address: Shipping address
            payment_method: Payment method
            **kwargs: Additional parameters

        Returns:
            Order details
        """
        order_id = f"amazon-order-{uuid.uuid4().hex[:8]}"

        self.logger.info(f"Placing order: {order_id}")
        self.logger.info(f"Cart total: ${cart.total:.2f}")
        self.logger.info(f"Items: {cart.item_count}")

        # Simulate order placement
        order_details = {
            "order_id": order_id,
            "vendor": self.vendor_name,
            "status": OrderStatus.PLACED,
            "cart": cart.dict(),
            "total": cart.total,
            "placed_at": datetime.now().isoformat(),
            "estimated_delivery": None,  # Would be calculated in real implementation
            "tracking_number": None,  # Would come from vendor
            "shipping_address": shipping_address,
            "payment_method": payment_method
        }

        self.logger.info(f"Order placed successfully: {order_id}")
        return order_details

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get order status (simulated).

        Args:
            order_id: Order ID

        Returns:
            Order status details
        """
        self.logger.info(f"Getting status for order: {order_id}")

        # In real implementation, this would query the API
        return {
            "order_id": order_id,
            "status": OrderStatus.PLACED,
            "status_updated_at": datetime.now().isoformat(),
            "message": "Order is being processed"
        }
